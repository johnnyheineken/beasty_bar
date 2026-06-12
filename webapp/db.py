"""SQLite persistence for the Beasty Bar web app (stdlib only).

- `rooms` stores a full snapshot of every room, so sessions survive
  server restarts: players reconnect with the token in their browser.
- `games` + `game_players` archive finished games and feed the
  monthly leaderboard.

On Cloud Run the local filesystem is ephemeral, so when the GCS_BUCKET
env var is set the database file is restored from the bucket at boot
and backed up (debounced) after writes — using the metadata-server
token and the GCS JSON API, no client libraries needed.
"""
import json
import os
import sqlite3
import threading
import time
import urllib.request
from pathlib import Path

DB_PATH = os.environ.get("BEASTY_DB",
                         str(Path(__file__).resolve().parent / "beasty.db"))
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_OBJECT = os.environ.get("GCS_OBJECT", "beasty.db")
# Cloud Run throttles CPU outside of requests, so backups run inline
# during request handling, at most once per interval (the file is tiny)
BACKUP_INTERVAL = 30.0

_conn = None
_lock = threading.Lock()
_backup = {"dirty": False, "last": 0.0}
_token_cache = {"value": None, "expires": 0.0}


def init(path=None):
    global _conn, DB_PATH
    if path:
        DB_PATH = path
    _restore_from_gcs()
    _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    _conn.execute("PRAGMA journal_mode=WAL")
    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            doc TEXT NOT NULL,
            updated REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            deck TEXT,
            scoring TEXT,
            finished_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS game_players (
            game_id INTEGER NOT NULL REFERENCES games(id),
            seat INTEGER,
            name TEXT,
            is_ai INTEGER,
            difficulty TEXT,
            score INTEGER,
            won INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_games_time ON games(finished_at);
        CREATE INDEX IF NOT EXISTS idx_gp_name ON game_players(name);
    """)
    cols = [row[1] for row in _conn.execute("PRAGMA table_info(rooms)")]
    if "finished" not in cols:  # migration for databases from before TTLs split
        _conn.execute("ALTER TABLE rooms ADD COLUMN finished INTEGER DEFAULT 0")
    _conn.commit()


def _db():
    if _conn is None:
        init()
    return _conn


# ---------- rooms (persistent sessions) ----------

def save_room(room_id, doc, updated, finished=False):
    with _lock:
        _db().execute(
            "INSERT INTO rooms(id, doc, updated, finished) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET doc=excluded.doc, "
            "updated=excluded.updated, finished=excluded.finished",
            (room_id, json.dumps(doc), updated, int(finished)))
        _db().commit()
    _backup["dirty"] = True
    maybe_backup()


def load_room(room_id):
    with _lock:
        row = _db().execute("SELECT doc FROM rooms WHERE id=?", (room_id,)).fetchone()
    return json.loads(row[0]) if row else None


def prune_rooms(unfinished_cutoff, finished_cutoff):
    with _lock:
        _db().execute(
            "DELETE FROM rooms WHERE (finished = 0 AND updated < ?) "
            "OR (finished = 1 AND updated < ?)",
            (unfinished_cutoff, finished_cutoff))
        _db().commit()


# ---------- finished games & leaderboard ----------

def record_game(room_id, deck, scoring, players):
    """players: [{seat, name, is_ai, difficulty, score, won}]"""
    with _lock:
        cur = _db().execute(
            "INSERT INTO games(room_id, deck, scoring, finished_at) VALUES(?,?,?,?)",
            (room_id, deck, scoring, time.time()))
        game_id = cur.lastrowid
        _db().executemany(
            "INSERT INTO game_players(game_id, seat, name, is_ai, difficulty, score, won) "
            "VALUES(?,?,?,?,?,?,?)",
            [(game_id, p["seat"], p["name"], int(p["is_ai"]), p.get("difficulty"),
              p["score"], int(p["won"])) for p in players])
        _db().commit()
    _backup["dirty"] = True
    maybe_backup(force=True)  # finished games are precious — upload now
    return game_id


def recent_games(limit=30):
    with _lock:
        games = _db().execute(
            "SELECT id, deck, scoring, finished_at FROM games "
            "ORDER BY finished_at DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for gid, deck, scoring, ts in games:
            rows = _db().execute(
                "SELECT seat, name, is_ai, difficulty, score, won FROM game_players "
                "WHERE game_id=? ORDER BY seat", (gid,)).fetchall()
            out.append({
                "id": gid, "deck": deck, "scoring": scoring, "finished_at": ts,
                "players": [{"seat": s, "name": n, "is_ai": bool(a),
                             "difficulty": d, "score": sc, "won": bool(w)}
                            for s, n, a, d, sc, w in rows],
            })
    return out


def month_bounds(month):
    """month: 'YYYY-MM' -> (start_epoch, end_epoch)"""
    year, mon = (int(x) for x in month.split("-"))
    import calendar
    start = time.mktime((year, mon, 1, 0, 0, 0, 0, 0, -1))
    days = calendar.monthrange(year, mon)[1]
    end = time.mktime((year, mon, days, 23, 59, 59, 0, 0, -1)) + 1
    return start, end


def leaderboard(month, limit=20):
    start, end = month_bounds(month)
    with _lock:
        rows = _db().execute(
            "SELECT gp.name, COUNT(*) games, SUM(gp.won) wins, SUM(gp.score) points "
            "FROM game_players gp JOIN games g ON g.id = gp.game_id "
            "WHERE gp.is_ai = 0 AND g.finished_at >= ? AND g.finished_at < ? "
            "GROUP BY gp.name ORDER BY wins DESC, points DESC, games ASC LIMIT ?",
            (start, end, limit)).fetchall()
    return [{"name": n, "games": g, "wins": w or 0, "points": p or 0}
            for n, g, w, p in rows]


# ---------- optional GCS backup (Cloud Run survival) ----------

def _metadata_token():
    if not GCS_BUCKET:
        return None
    if _token_cache["value"] and time.time() < _token_cache["expires"]:
        return _token_cache["value"]
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/"
            "service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        _token_cache["value"] = data["access_token"]
        _token_cache["expires"] = time.time() + data.get("expires_in", 300) - 60
        return _token_cache["value"]
    except Exception:
        return None


def _restore_from_gcs():
    if not GCS_BUCKET or os.path.exists(DB_PATH):
        return
    token = _metadata_token()
    if not token:
        return
    try:
        from urllib.parse import quote
        url = (f"https://storage.googleapis.com/storage/v1/b/{GCS_BUCKET}"
               f"/o/{quote(GCS_OBJECT, safe='')}?alt=media")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            Path(DB_PATH).write_bytes(r.read())
        print(f"restored {GCS_OBJECT} from gs://{GCS_BUCKET}")
    except Exception as exc:
        print(f"no GCS restore ({exc})")


def maybe_backup(force=False):
    """Upload the database to GCS, at most once per BACKUP_INTERVAL."""
    if not GCS_BUCKET or not _backup["dirty"]:
        return
    now = time.time()
    if not force and now - _backup["last"] < BACKUP_INTERVAL:
        return
    _backup["last"] = now
    _backup["dirty"] = False
    _backup_now()


def _backup_now():
    token = _metadata_token()
    if not token:
        return
    try:
        with _lock:
            # fold the WAL into the main file so the snapshot is complete
            _db().execute("PRAGMA wal_checkpoint(TRUNCATE)")
            payload = Path(DB_PATH).read_bytes()
        from urllib.parse import quote
        url = (f"https://storage.googleapis.com/upload/storage/v1/b/{GCS_BUCKET}"
               f"/o?uploadType=media&name={quote(GCS_OBJECT, safe='')}")
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        })
        urllib.request.urlopen(req, timeout=30)
    except Exception as exc:
        print(f"GCS backup failed ({exc})")
