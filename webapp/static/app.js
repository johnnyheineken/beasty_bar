/* Beasty Bar web client — full-screen mobile layout with outcome previews. */

const EMOJI = {
  Lion: '🦁', Hippo: '🦛', Croc: '🐊', Snake: '🐍', Gazelle: '🦒', Zebra: '🦓',
  Seal: '🦭', Chameleon: '🦎', Monkey: '🐒', Kangaroo: '🦘', Parrot: '🦜', Skunk: '🦨',
  Rhino: '🦏', Bear: '🐻', Tiger: '🐯', Cheetah: '🐆', Llama: '🦙', Porcupine: '🦔',
  Ostrich: '🦤', Penguin: '🐧', Dog: '🐕', Peacock: '🦚', Vulture: '🦅', Bat: '🦇',
};
const LABEL = { Gazelle: 'Giraffe' };

/* 🔁 recurring · 🛡 protects · 🎭 copies · → toward the gate
   ↷ jumps · 🚮 throws out · 😋 eats  (plain arrows render cleanly
   on iOS — the blue-button emoji variants don't) */
const ICONS = {
  Lion:      '🐒→🚮 · №1🚪',
  Hippo:     '🔁 →🚪 ✗🦁🦓🦛',
  Croc:      '🔁 😋← ✗🦁🦛🦓',
  Snake:     '⇅ 💪→🚪',
  Gazelle:   '🔁 ↷🐭',
  Zebra:     '🛡 ✗🦛🐊',
  Seal:      '⇆ 🚪⛔',
  Chameleon: '🎭 ↓line',
  Monkey:    '🐒+🐒 🦛🐊→🚮',
  Kangaroo:  '↷ 1·2',
  Parrot:    '👆→🚮',
  Skunk:     '💪💪→🚮',
  Rhino:     '💪→🚮 ⊕',
  Bear:      '🐭🐭→end',
  Tiger:     '🔁 ↷↷ 😋🐭',
  Cheetah:   '😋🐭 ⊕',
  Llama:     '🔁 💦←end',
  Porcupine: '🛡 ⟲🦏🐯🐆',
  Ostrich:   '🏃 2·4·6 ∕ 1·3·5',
  Penguin:   '🎭 ✋hand',
  Dog:       '⇅ 🐭→🚪',
  Peacock:   '→front of 💪',
  Vulture:   '♻ 🚮top',
  Bat:       '👆⊕ 🚪=💥',
};
const HINTS = {
  Lion: 'Monkeys out, then goes first. A 2nd lion is thrown out itself.',
  Hippo: 'Every turn: pushes forward. Stopped by lion, zebra, hippo.',
  Croc: 'Every turn: eats all weaker ahead. Stopped by stronger & zebra.',
  Snake: 'Sorts the line — strongest at the gate.',
  Gazelle: 'Every turn: steps over one weaker animal.',
  Zebra: 'Wall for hippos & crocs — protects everyone ahead of it.',
  Seal: 'Gate and exit swap — the line reverses.',
  Chameleon: 'Acts as a species from the line, then is a 5 again.',
  Monkey: '2+ monkeys: hippos & crocs out, monkeys storm the gate.',
  Kangaroo: 'Jumps over the last 1 or 2 animals.',
  Parrot: 'Throws out any one animal you pick.',
  Skunk: 'Throws out the two strongest species (never skunks).',
  Rhino: 'Rams the strongest animal & takes its spot.',
  Bear: 'The two weakest ranks go to the back of the line.',
  Tiger: 'Every turn: leaps 2 ahead, eats it if weaker.',
  Cheetah: 'Eats the weakest animal & takes its spot.',
  Llama: 'Every turn: spits the animal ahead (≤7) to the back.',
  Porcupine: 'Rhino/tiger/cheetah attacks bounce back at the attacker.',
  Ostrich: 'Runs past all even OR all odd values — you pick.',
  Penguin: 'Acts as another card from your hand (it stays in hand).',
  Dog: 'Sorts the line — weakest at the gate.',
  Peacock: 'Steps right in front of the strongest animal.',
  Vulture: 'Brings the top trash card back to life, then lands on the trash.',
  Bat: 'Replaces any animal — but burns up whenever it is first in line!',
};
const TRAIT = {
  Hippo: '🔁', Croc: '🔁', Gazelle: '🔁', Tiger: '🔁', Llama: '🔁',
  Zebra: '🛡️', Porcupine: '🛡️', Chameleon: '🎭', Penguin: '🎭',
  Bat: '💥', Vulture: '♻️', Seal: '🔄', Snake: '↕️', Dog: '↕️',
};
const DECK_HINTS = {
  classic: 'The original 12 animals · most 🍸 wins',
  new_beasts: 'The 12 expansion animals · 🏅 points win',
  mixed: 'Random mix of both sets · 🏅 points win',
};

const $ = (sel) => document.querySelector(sel);
const POLL_MS = 1100;

let state = null;
let flow = null;       // pending multi-step choice
let inspect = null;    // card shown in the action bar
let preview = null;    // {card, params, data} — outcome waiting for confirm
let pollTimer = null;
let lastLogLen = null;
let session = null;
let revealedSeat = null;   // hotseat: whose hand is currently visible
let prevCounts = { bar: 0, trash: 0 };
const ui = {
  deck: 'classic', total: 4, local: 1, ai: 3, joinLocal: 1,
  aiLevels: ['medium', 'medium', 'medium'],   // per-AI difficulty
};
const LEVEL_FACE = { easy: '🐣', medium: '🙂', hard: '🧠' };

function label(name) { return LABEL[name] || name; }
function cardKey(c) { return `${c.name}-${c.player}`; }

function mySeats() { return (state && state.you_seats) || []; }
function isHotseat() { return mySeats().length > 1; }
function activeLocalSeat() {
  return !state.finished && mySeats().includes(state.current_player)
    ? state.current_player : null;
}
function playerName(id) {
  if (!state) return `Player ${id + 1}`;
  if (!isHotseat() && state.you === id) return 'You';
  return state.players[id].name;
}
function myHand() {
  // the hand the dock should show (only revealed hands in hotseat mode)
  if (!state || !mySeats().length) return null;
  if (!isHotseat()) return { seat: state.you, cards: state.hands[state.you] || [] };
  const seat = activeLocalSeat();
  if (seat !== null && revealedSeat === seat) return { seat, cards: state.hands[seat] || [] };
  return null;
}

/* ---------- session / routing ---------- */

function roomFromUrl() {
  const m = location.hash.match(/r=([\w-]+)/);
  return m ? m[1] : null;
}
function saveSession(s) {
  session = s;
  localStorage.setItem('beasty_' + s.room, JSON.stringify(s));
  location.hash = 'r=' + s.room;
}
function loadSession(room) {
  try { return JSON.parse(localStorage.getItem('beasty_' + room)); }
  catch { return null; }
}

/* ---------- api ---------- */

async function api(path, body) {
  const opts = body !== undefined
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : {};
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) { const e = new Error(data.error || 'request failed'); e.status = res.status; throw e; }
  return data;
}

function show(screen) {
  for (const s of document.querySelectorAll('.screen')) s.classList.add('hidden');
  $('#screen-' + screen).classList.remove('hidden');
}

/* ---------- menu ---------- */

function segInit(sel, key, dataAttr) {
  $(sel).addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    for (const x of $(sel).querySelectorAll('button')) x.classList.remove('on');
    b.classList.add('on');
    ui[key] = dataAttr ? b.dataset[dataAttr] : parseInt(b.dataset.n, 10);
    if (key === 'deck') $('#deck-hint').textContent = DECK_HINTS[ui.deck];
    refreshHomeForm();
  });
}

function nameInputs(boxSel, count, prefix) {
  const box = $(boxSel);
  const existing = [...box.querySelectorAll('input')].map(i => i.value);
  box.innerHTML = '';
  for (let i = 0; i < count; i++) {
    const input = document.createElement('input');
    input.maxLength = 20;
    input.placeholder = i === 0 ? '😎 Your name' : `😎 Player ${i + 1}'s name`;
    input.value = existing[i] ?? (i === 0 ? (localStorage.getItem('beasty_name') || '') : '');
    input.style.marginTop = '6px';
    box.appendChild(input);
  }
}

function names(boxSel) {
  return [...$(boxSel).querySelectorAll('input')].map(i => i.value);
}

function refreshHomeForm() {
  // keep local + ai within the table size
  ui.local = Math.min(ui.local, ui.total);
  for (const b of $('#local-select').querySelectorAll('button')) {
    const n = parseInt(b.dataset.n, 10);
    b.style.display = n <= ui.total ? '' : 'none';
    b.classList.toggle('on', n === ui.local);
  }
  const maxAi = ui.total - ui.local;
  ui.ai = Math.min(ui.ai, maxAi);
  for (const b of $('#ai-select').querySelectorAll('button')) {
    const n = parseInt(b.dataset.n, 10);
    b.style.display = n <= maxAi ? '' : 'none';
    b.classList.toggle('on', n === ui.ai);
  }
  renderAiLevels();
  nameInputs('#local-names', ui.local);
  const friends = ui.total - ui.local - ui.ai;
  $('#seats-hint').textContent = friends > 0
    ? `🔗 ${friends} seat${friends > 1 ? 's' : ''} for friends' phones (share the link after creating)`
    : '✅ The table is complete — the game starts right away';
}

function renderAiLevels() {
  const box = $('#ai-levels');
  box.innerHTML = '';
  for (let i = 0; i < ui.ai; i++) {
    const row = document.createElement('div');
    row.className = 'seg ai-level-row';
    const tag = document.createElement('span');
    tag.className = 'ai-tag';
    tag.textContent = `🤖 ${i + 1}`;
    row.appendChild(tag);
    for (const lvl of ['easy', 'medium', 'hard']) {
      const b = document.createElement('button');
      b.innerHTML = `${LEVEL_FACE[lvl]}<small>${lvl === 'medium' ? 'normal' : lvl}</small>`;
      b.classList.toggle('on', ui.aiLevels[i] === lvl);
      b.onclick = () => { ui.aiLevels[i] = lvl; renderAiLevels(); };
      row.appendChild(b);
    }
    box.appendChild(row);
  }
}

segInit('#deck-select', 'deck', 'deck');
segInit('#total-select', 'total');
segInit('#local-select', 'local');
segInit('#ai-select', 'ai');
$('#join-local-select').addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  for (const x of $('#join-local-select').querySelectorAll('button')) x.classList.remove('on');
  b.classList.add('on');
  ui.joinLocal = parseInt(b.dataset.n, 10);
  nameInputs('#join-names', ui.joinLocal);
});

async function guarded(btn, fn, errBox) {
  btn.disabled = true;
  try { await fn(); }
  catch (e) { $(errBox).textContent = '⚠️ ' + e.message; }
  finally { btn.disabled = false; }
}

$('#create-btn').onclick = (e) => guarded(e.target, async () => {
  const local = names('#local-names');
  const res = await api('/api/room', {
    players: ui.total, local, ai: ui.aiLevels.slice(0, ui.ai), deck: ui.deck,
  });
  localStorage.setItem('beasty_name', local[0] || '');
  saveSession(res);
  startPolling();
}, '#home-error');

$('#join-btn').onclick = (e) => guarded(e.target, async () => {
  const local = names('#join-names');
  const res = await api('/api/join', { room: roomFromUrl(), local });
  localStorage.setItem('beasty_name', local[0] || '');
  saveSession(res);
  startPolling();
}, '#join-error');

$('#again-btn').onclick = () => {
  stopPolling();
  $('#end-overlay').classList.add('hidden');
  location.hash = '';
  state = session = flow = inspect = preview = null;
  lastLogLen = null;
  show('home');
};

/* ---------- leaderboard & game history ---------- */

let boardMonth = new Date().toISOString().slice(0, 7);

function shiftMonth(ym, delta) {
  const [y, m] = ym.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

async function showBoard() {
  $('#board-overlay').classList.remove('hidden');
  $('#board-month').textContent = '🏆 ' + boardMonth;
  try {
    const data = await api(`/api/leaderboard?month=${boardMonth}`);
    const rows = data.rows.map((r, i) => {
      const medal = ['🥇', '🥈', '🥉'][i] || `${i + 1}.`;
      return `<tr><td>${medal}</td><td>${r.name}</td>` +
        `<td>🏆${r.wins}</td><td>🏅${r.points}</td><td>🎲${r.games}</td></tr>`;
    });
    $('#board-table').innerHTML = rows.join('') ||
      '<tr><td>No finished games this month — go play! 🍹</td></tr>';
  } catch (e) {
    $('#board-table').innerHTML = `<tr><td>⚠️ ${e.message}</td></tr>`;
  }
}

$('#board-btn').onclick = showBoard;
$('#board-prev').onclick = () => { boardMonth = shiftMonth(boardMonth, -1); showBoard(); };
$('#board-next').onclick = () => { boardMonth = shiftMonth(boardMonth, 1); showBoard(); };
$('#board-close').onclick = () => $('#board-overlay').classList.add('hidden');

$('#games-btn').onclick = async () => {
  $('#games-overlay').classList.remove('hidden');
  try {
    const data = await api('/api/games');
    const items = data.games.map((g) => {
      const when = new Date(g.finished_at * 1000).toLocaleString(undefined,
        { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      const deck = g.deck === 'classic' ? '🦁' : g.deck === 'new_beasts' ? '🦏' : '🔀';
      const unit = g.scoring === 'points' ? '🏅' : '🍸';
      const players = g.players.map(p =>
        `${p.won ? '🏆' : ''}${p.name} ${unit}${p.score}`).join(' · ');
      return `<div class="game-row"><span class="game-when">${deck} ${when}</span><br>${players}</div>`;
    });
    $('#games-list').innerHTML = items.join('') ||
      '<div class="game-row">No games yet 🍹</div>';
  } catch (e) {
    $('#games-list').innerHTML = `<div class="game-row">⚠️ ${e.message}</div>`;
  }
};
$('#games-close').onclick = () => $('#games-overlay').classList.add('hidden');

$('#help-btn').onclick = () => $('#help-overlay').classList.remove('hidden');
$('#help-close').onclick = () => {
  localStorage.setItem('beasty_seen', '1');
  $('#help-overlay').classList.add('hidden');
  if (state && state.started) renderGame();
};
$('#log-btn').onclick = () => { $('#log-sheet').classList.remove('hidden'); };
$('#log-close').onclick = () => { $('#log-sheet').classList.add('hidden'); };

/* ---------- lobby ---------- */

function renderLobby() {
  show('lobby');
  const seats = $('#lobby-seats');
  seats.innerHTML = '';
  state.players.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'seat' + (p.claimed ? '' : ' open');
    div.innerHTML = `<span class="who"><span class="chip p${i}"></span>${p.claimed ? p.name : 'waiting…'}</span>` +
      `<span>${p.is_ai ? '🤖' : (p.claimed ? '✅' : '⏳')}</span>`;
    seats.appendChild(div);
  });
  $('#invite-link').value = location.origin + '/#r=' + session.room;
}

$('#copy-btn').onclick = async () => {
  try { await navigator.clipboard.writeText($('#invite-link').value); $('#copy-btn').textContent = '✅'; }
  catch { $('#invite-link').select(); document.execCommand('copy'); }
  setTimeout(() => { $('#copy-btn').textContent = '📋'; }, 1200);
};
$('#share-btn').onclick = () => {
  const url = $('#invite-link').value;
  if (navigator.share) navigator.share({ title: 'Beasty Bar', text: 'Join my Beasty Bar game! 🍹', url });
  else $('#copy-btn').click();
};

/* ---------- polling ---------- */

/* Polling is the main running cost of the system, so it adapts:
   fast only while waiting for someone else's move, slow on our own
   turn and in the lobby, paused while the app is in the background,
   and stopped entirely once the game is over. */
function pollDelay() {
  if (!state) return 1500;
  if (state.finished) return null;                 // game over: stop
  if (!state.started) return 3000;                 // lobby
  if (activeLocalSeat() !== null) return 8000;     // our move: nothing changes without us
  return POLL_MS;                                  // someone else is thinking
}

function startPolling() {
  stopPolling();
  const poll = async () => {
    pollTimer = null;
    try {
      const v = state && state.started ? `&v=${state.version}` : '';
      const data = await api(`/api/state?room=${session.room}&token=${session.token}${v}`);
      if (!data.unchanged) {
        state = data;
        onState();
      }
    } catch (e) {
      if (e.status === 404) { $('#again-btn').click(); alert(e.message); return; }
    }
    const delay = pollDelay();
    if (delay !== null && !document.hidden) pollTimer = setTimeout(poll, delay);
  };
  poll();
}
function stopPolling() { clearTimeout(pollTimer); pollTimer = null; }

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopPolling();
  } else if (session && !(state && state.finished)) {
    startPolling();
  }
});

function onState() {
  if (!state.started) { renderLobby(); return; }
  if ($('#screen-game').classList.contains('hidden')) {
    show('game');
    if (!localStorage.getItem('beasty_seen')) $('#help-overlay').classList.remove('hidden');
  }
  if (!isHotseat()) {
    revealedSeat = state.you;
  } else if (activeLocalSeat() === null) {
    revealedSeat = null;        // hide hands again between local turns
    cancelAll0();
  }
  renderGame();
}

function cancelAll0() { flow = null; preview = null; inspect = null; }

function renderPassOverlay() {
  const overlay = $('#pass-overlay');
  const seat = activeLocalSeat();
  const needsPass = isHotseat() && seat !== null && revealedSeat !== seat
    && $('#help-overlay').classList.contains('hidden') && !state.finished;
  if (!needsPass) { overlay.classList.add('hidden'); return; }
  overlay.classList.remove('hidden');
  $('#pass-emoji').textContent = '📱➡️';
  $('#pass-title').innerHTML =
    `<span class="chip p${seat}"></span>${state.players[seat].name}'s turn`;
  $('#pass-confirm').onclick = () => {
    revealedSeat = seat;
    overlay.classList.add('hidden');
    renderGame();
  };
}

/* ---------- rendering ---------- */

function qcardEl(card) {
  const el = document.createElement('div');
  el.className = `qcard p${card.player}`;
  el.dataset.key = cardKey(card);
  el.innerHTML = `
    <span class="emoji">${EMOJI[card.name] || '❓'}</span>
    <span class="qname">${label(card.name)}<small>${ICONS[card.name] || ''}</small></span>
    <span class="qvalue">${card.animal}</span>`;
  return el;
}

function handCardEl(card) {
  const el = document.createElement('div');
  el.className = `card p${card.player}`;
  el.dataset.key = cardKey(card);
  el.innerHTML = `
    <div class="cvalue">${card.animal}</div>
    <div class="emoji">${EMOJI[card.name] || '❓'}</div>
    <div class="cname">${label(card.name)}</div>
    ${TRAIT[card.name] ? `<div class="ctrait">${TRAIT[card.name]}</div>` : ''}`;
  return el;
}

/* ---------- seal: the table turns around ---------- */

function spinTable() {
  if (navigator.vibrate) navigator.vibrate(80);
  const table = $('#table');
  table.classList.remove('seal-spin');
  void table.offsetWidth;
  table.classList.add('seal-spin');
  setTimeout(() => table.classList.remove('seal-spin'), 1300);

  const layer = $('#fly-layer');
  const banner = document.createElement('div');
  banner.className = 'gate-banner seal-banner';
  banner.innerHTML = '<div class="gb-top">🦭</div><div class="gb-who">🚪 ⇄ ⛔</div>';
  layer.appendChild(banner);
  setTimeout(() => banner.remove(), 1500);

  const rect = table.getBoundingClientRect();
  for (let i = 0; i < 10; i++) {
    const drop = document.createElement('div');
    drop.className = 'splash';
    drop.textContent = '💦';
    const angle = (i / 10) * 2 * Math.PI;
    drop.style.left = (rect.left + rect.width / 2 - 12) + 'px';
    drop.style.top = (rect.top + rect.height / 2 - 12) + 'px';
    drop.style.setProperty('--dx', `${Math.cos(angle) * rect.width * 0.55}px`);
    drop.style.setProperty('--dy', `${Math.sin(angle) * rect.height * 0.45}px`);
    drop.style.animationDelay = `${Math.random() * 0.12}s`;
    layer.appendChild(drop);
    setTimeout(() => drop.remove(), 1400);
  }
}

/* ---------- gate celebration ---------- */

const CONFETTI_COLORS = ['#f5b942', '#ff8e3c', '#3b82f6', '#22c55e', '#ef4444', '#fff'];

function celebrateGate(entry) {
  if (navigator.vibrate) navigator.vibrate([60, 40, 120]);
  const layer = $('#fly-layer');

  const flash = document.createElement('div');
  flash.id = 'gate-flash';
  layer.appendChild(flash);
  setTimeout(() => flash.remove(), 1000);

  const banner = document.createElement('div');
  banner.className = 'gate-banner';
  const who = entry.to_bar.map(c => EMOJI[c.name]).join(' ');
  banner.innerHTML = `<div class="gb-top">🚪✨</div><div class="gb-who">${who} → 🍸</div>`;
  layer.appendChild(banner);
  setTimeout(() => banner.remove(), 1700);

  const table = $('#table').getBoundingClientRect();
  for (let i = 0; i < 30; i++) {
    const c = document.createElement('div');
    c.className = 'confetto';
    c.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length];
    c.style.left = (table.left + table.width / 2) + 'px';
    c.style.top = (table.top + table.height * 0.18) + 'px';
    c.style.setProperty('--dx', `${(Math.random() - 0.5) * table.width * 1.4}px`);
    c.style.setProperty('--dy', `${table.height * (0.5 + Math.random() * 0.5)}px`);
    c.style.setProperty('--rot', `${(Math.random() - 0.5) * 900}deg`);
    c.style.animationDelay = `${Math.random() * 0.15}s`;
    layer.appendChild(c);
    setTimeout(() => c.remove(), 1800);
  }
}

function renderGame() {
  renderPlayers();
  renderPiles();
  renderQueue();
  renderHand();
  renderActionBar();
  renderChoices();
  renderLog();
  renderPassOverlay();
  renderEnd();
}

function renderPlayers() {
  const strip = $('#players-strip');
  strip.innerHTML = '';
  state.players.forEach((p, i) => {
    const el = document.createElement('div');
    el.className = 'pchip';
    el.dataset.id = i;
    el.style.borderTopColor = getComputedStyle(document.documentElement).getPropertyValue(`--p${i}`);
    if (!state.finished && state.current_player === i) el.classList.add('active');
    const score = state.scoring === 'points' ? `🏅${p.score}` : `🍸${p.in_bar}`;
    const tag = p.is_ai ? '' : (p.mine && isHotseat() ? '📱' : '');
    el.innerHTML = `<span class="pname">${playerName(i)}${tag}</span><br>` +
      `<span class="pmeta">✋${p.hand_count} ${score}</span>`;
    strip.appendChild(el);
  });
}

function renderPiles() {
  $('#bar-count').textContent = state.bar_count;
  $('#trash-count').textContent = state.trash_count;
  $('#trash-top').textContent = state.trash_top
    ? `${EMOJI[state.trash_top.name]}${state.trash_top.animal}` : '';
  if (state.bar_count !== prevCounts.bar) bumpPile('#bar-pile');
  if (state.trash_count !== prevCounts.trash) bumpPile('#trash-pile');
  prevCounts = { bar: state.bar_count, trash: state.trash_count };
}

function bumpPile(sel) {
  const el = $(sel);
  el.classList.remove('bump');
  void el.offsetWidth;
  el.classList.add('bump');
}

function renderQueue() {
  const box = $('#queue');
  const strip = $('#preview-strip');

  if (preview) {        // ----- show the future, not the present -----
    box.innerHTML = '';
    const oldIndex = {};
    state.queue.forEach((c, i) => { oldIndex[cardKey(c)] = i; });
    preview.data.queue.forEach((card, i) => {
      const el = qcardEl(card);
      el.classList.add('ghost');
      const was = oldIndex[cardKey(card)];
      const delta = document.createElement('span');
      delta.className = 'qdelta';
      delta.textContent = was === undefined ? '✨'
        : was > i ? '⬆︎' + (was - i) : was < i ? '⬇︎' + (i - was) : '·';
      el.appendChild(delta);
      box.appendChild(el);
    });
    for (let i = preview.data.queue.length; i < 5; i++) {
      const slot = document.createElement('div');
      slot.className = 'qslot';
      box.appendChild(slot);
    }
    const bits = [];
    if (preview.data.to_bar.length) {
      bits.push(`<span class="pv bar">→🍸 ${preview.data.to_bar.map(c => EMOJI[c.name]).join(' ')}</span>`);
    }
    if (preview.data.to_trash.length) {
      bits.push(`<span class="pv trash">→🚮 ${preview.data.to_trash.map(c => EMOJI[c.name]).join(' ')}</span>`);
    }
    strip.innerHTML = bits.join(' ') || '<span class="pv">no one moves</span>';
    strip.classList.remove('hidden');
    lastLogLen = state.log_total ?? state.log.length;
    return;
  }
  strip.classList.add('hidden');

  // FLIP step 1: remember where each card was
  const oldRects = {};
  for (const el of box.querySelectorAll('.qcard')) {
    oldRects[el.dataset.key] = el.getBoundingClientRect();
  }

  box.innerHTML = '';
  const total = state.log_total ?? state.log.length;
  const newCount = lastLogLen === null ? 0 : Math.max(0, total - lastLogLen);
  const freshEntries = newCount ? state.log.slice(-Math.min(newCount, state.log.length)) : [];
  const lastEntry = state.log[state.log.length - 1];

  state.queue.forEach((card, i) => {
    const el = qcardEl(card);
    decorateQueueCard(el, card, i);
    box.appendChild(el);
  });
  for (let i = state.queue.length; i < 5; i++) {
    const slot = document.createElement('div');
    slot.className = 'qslot';
    box.appendChild(slot);
  }

  // a seal swaps the gate and the exit: spin the whole table instead of
  // sliding cards past each other — like turning the real table around
  const sealEntry = freshEntries.find(e => e.played.name === 'Seal' || e.as === 'Seal');
  if (sealEntry) {
    spinTable();
  } else {
  // FLIP step 2: slide moved cards; let the just-played card arrive
  // visibly from its owner's chip
  requestAnimationFrame(() => {
    for (const el of box.querySelectorAll('.qcard')) {
      const old = oldRects[el.dataset.key];
      if (old) {
        const now = el.getBoundingClientRect();
        const dx = old.left - now.left, dy = old.top - now.top;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
          el.style.transform = `translate(${dx}px, ${dy}px)`;
          void el.offsetWidth;
          el.classList.add('moving');
          el.style.transform = '';
          el.addEventListener('transitionend', () => el.classList.remove('moving'), { once: true });
        }
      } else if (freshEntries.length && lastEntry &&
                 el.dataset.key === cardKey(lastEntry.played)) {
        const chip = $(`#players-strip .pchip[data-id="${lastEntry.player}"]`);
        if (chip) {
          const from = chip.getBoundingClientRect();
          const now = el.getBoundingClientRect();
          el.style.transform =
            `translate(${from.left - now.left}px, ${from.top - now.top}px) scale(.3)`;
          void el.offsetWidth;
          el.classList.add('moving');
          el.style.transform = '';
          el.addEventListener('transitionend', () => el.classList.remove('moving'), { once: true });
        } else {
          el.classList.add('entering');
        }
      }
    }
  });
  }

  // fly outgoing animals to the piles; celebrate when the gate opens
  for (const entry of freshEntries) {
    flyCards(entry.to_bar, oldRects, '#bar-pile');
    flyCards(entry.to_trash, oldRects, '#trash-pile');
    if (entry.gate_opened) {
      const gate = $('#gate-in');
      gate.classList.remove('open');
      void gate.offsetWidth;
      gate.classList.add('open');
      celebrateGate(entry);
    }
  }
  lastLogLen = total;
}

function flyCards(cards, oldRects, pileSel) {
  const pile = $(pileSel).getBoundingClientRect();
  for (const c of cards) {
    const from = oldRects[cardKey(c)];
    if (!from) continue;
    const ghost = document.createElement('div');
    ghost.className = 'fly';
    ghost.textContent = EMOJI[c.name];
    ghost.style.left = (from.left + 8) + 'px';
    ghost.style.top = (from.top + from.height / 2 - 15) + 'px';
    $('#fly-layer').appendChild(ghost);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      ghost.style.left = (pile.left + pile.width / 2 - 15) + 'px';
      ghost.style.top = (pile.top + pile.height / 2 - 15) + 'px';
      ghost.style.transform = 'scale(.4) rotate(10deg)';
      ghost.style.opacity = '0';
    }));
    setTimeout(() => ghost.remove(), 900);
  }
}

function decorateQueueCard(el, card, index) {
  if (flow) {
    const step = flow.steps[0];
    const pickable = step && (step.type === 'pick-queue' ||
      (step.type === 'pick-species' && card.name !== 'Chameleon'));
    if (pickable) {
      el.classList.add('selectable');
      if (step.badge) {
        const b = document.createElement('span');
        b.className = 'qbadge';
        b.textContent = step.badge;
        el.appendChild(b);
      }
      el.onclick = () => onQueuePick(card, index);
    } else {
      el.classList.add('dimmed');
    }
    return;
  }
  el.classList.add('clickable');
  el.onclick = () => { inspect = { card, inHand: false }; renderGame(); };
}

function renderHand() {
  const box = $('#hand');
  box.innerHTML = '';
  const hand = myHand();
  if (!hand) {
    // hotseat: hands stay hidden between local turns
    const seats = mySeats();
    if (seats.length) {
      const count = Math.max(...seats.map(s => state.players[s].hand_count));
      for (let i = 0; i < count; i++) {
        const back = document.createElement('div');
        back.className = 'card back';
        back.innerHTML = '<div class="emoji">🐾</div>';
        box.appendChild(back);
      }
    }
    return;
  }
  const myTurn = !state.finished && state.current_player === hand.seat;
  const step = flow && flow.steps[0];
  for (const card of hand.cards) {
    const el = handCardEl(card);
    if (step && step.type === 'pick-hand') {
      if (card.animal === flow.card) { el.classList.add('selected'); el.onclick = cancelAll; }
      else { el.classList.add('selectable', 'clickable'); el.onclick = () => onHandPick(card); }
    } else if (flow || preview) {
      const active = card.animal === (flow ? flow.card : preview.card);
      el.classList.toggle('selected', active);
      el.classList.toggle('dimmed', !active);
      if (active) el.onclick = cancelAll;
    } else {
      el.classList.add('clickable');
      if (inspect && inspect.inHand && inspect.card.animal === card.animal) el.classList.add('selected');
      el.onclick = () => { inspect = { card, inHand: true, playable: myTurn }; renderGame(); };
    }
    box.appendChild(el);
  }
}

function renderActionBar() {
  const bar = $('#action-bar');
  const btns = $('#action-buttons');

  if (preview) {        // confirm step: the board already SHOWS the outcome
    bar.classList.remove('hidden');
    const c = preview.cardInfo;
    $('#action-emoji').textContent = EMOJI[c.name];
    $('#action-title').textContent = `${label(c.name)} · ${c.animal}`;
    $('#action-icons').textContent = ICONS[c.name] || '';
    $('#action-text').textContent = '';
    btns.innerHTML = '';
    const ok = document.createElement('button');
    ok.className = 'primary';
    ok.textContent = '▶ Play';
    ok.onclick = commitPreview;
    const no = document.createElement('button');
    no.textContent = '✕';
    no.onclick = cancelAll;
    btns.append(ok, no);
    return;
  }

  if (!inspect || flow) { bar.classList.add('hidden'); return; }
  const c = inspect.card;
  bar.classList.remove('hidden');
  $('#action-emoji').textContent = EMOJI[c.name];
  $('#action-title').textContent = `${label(c.name)} · ${c.animal}`;
  $('#action-icons').textContent = ICONS[c.name] || '';
  $('#action-text').textContent = HINTS[c.name] || '';
  btns.innerHTML = '';
  if (inspect.inHand && inspect.playable) {
    const play = document.createElement('button');
    play.className = 'primary';
    play.textContent = '👁 Preview';
    play.onclick = () => { const card = inspect.card; inspect = null; startFlow(card); };
    btns.appendChild(play);
  }
  const close = document.createElement('button');
  close.textContent = '✕';
  close.onclick = () => { inspect = null; renderGame(); };
  btns.appendChild(close);
}

function showStatus(msg) { $('#status').textContent = msg; }

function renderChoices() {
  const buttons = $('#choice-buttons');
  buttons.innerHTML = '';
  if (state.finished) { showStatus('🏁'); return; }

  if (preview) { showStatus('✨ This is what will happen'); return; }

  if (flow) {
    const step = flow.steps[0];
    showStatus(step.prompt);
    if (step.type === 'jump') {
      for (const n of [1, 2]) {
        if (n > state.queue.length) continue;
        const b = document.createElement('button');
        b.className = 'primary';
        b.textContent = `↷ ${n}`;
        b.onclick = () => answerStep({ [step.param || 'jump']: n });
        buttons.appendChild(b);
      }
    }
    if (step.type === 'parity') {
      for (const par of ['even', 'odd']) {
        const b = document.createElement('button');
        b.className = 'primary';
        b.textContent = par === 'even' ? '2️⃣ 4️⃣ 6️⃣' : '1️⃣ 3️⃣ 5️⃣';
        b.onclick = () => answerStep({ [step.param || 'parity']: par });
        buttons.appendChild(b);
      }
    }
    const cancel = document.createElement('button');
    cancel.textContent = '✕';
    cancel.onclick = cancelAll;
    buttons.appendChild(cancel);
    return;
  }

  if (!mySeats().length) { showStatus('👀'); return; }
  const seat = activeLocalSeat();
  if (seat !== null) {
    const hand = myHand();
    showStatus(hand && hand.cards.length
      ? (isHotseat() ? `🫵 ${state.players[seat].name} — tap a card` : '🫵 Tap a card')
      : '✅');
  } else {
    showStatus(`⏳ ${playerName(state.current_player)}`);
  }
}

/* ---------- choice flow ---------- */

function stepsFor(kindName, opts) {
  const into = opts.prefix === 'revive';
  const q = state.queue.length;
  const steps = [];
  const e = EMOJI[kindName];
  if (kindName === 'Parrot' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', badge: '🚮', prompt: `${e} Tap who flies out` });
  } else if (kindName === 'Kangaroo' && q >= 2) {
    steps.push({ type: 'jump', into, param: 'jump', prompt: `${e} Jump how far?` });
  } else if (kindName === 'Bat' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', badge: '🚮', prompt: `${e} Tap whose spot to take` });
  } else if (kindName === 'Ostrich' && q) {
    steps.push({ type: 'parity', into, param: 'parity', prompt: `${e} Run past which values?` });
  } else if (kindName === 'Chameleon' && state.queue.some(c => c.name !== 'Chameleon')) {
    steps.push({ type: 'pick-species', into, param: 'imitate', badge: '🎭', prompt: `${e} Tap the species to copy` });
  } else if (kindName === 'Penguin' && opts.hand && opts.hand.length) {
    steps.push({ type: 'pick-hand', into, param: 'imitate_value', prompt: `${e} Tap a hand card to copy 🎭` });
  }
  return steps;
}

function startFlow(card) {
  const hand = myHand();
  const others = hand ? hand.cards.filter(c => c.animal !== card.animal) : [];
  flow = { card: card.animal, cardInfo: card, params: {}, steps: [] };
  if (card.name === 'Vulture') {
    if (state.trash_top && state.trash_top.name !== 'Vulture') {
      flow.params.revive = {};
      flow.steps = stepsFor(state.trash_top.name, { prefix: 'revive', hand: others });
    }
  } else {
    flow.steps = stepsFor(card.name, { hand: others });
  }
  advanceFlow();
}

function answerStep(answer) {
  const step = flow.steps.shift();
  Object.assign(step.into ? flow.params.revive : flow.params, answer);
  advanceFlow();
}

function onQueuePick(card, index) {
  const step = flow.steps[0];
  if (step.type === 'pick-queue') {
    answerStep({ [step.param]: index });
  } else if (step.type === 'pick-species') {
    flow.steps.shift();
    (step.into ? flow.params.revive : flow.params)[step.param] = card.animal;
    const nested = stepsFor(card.name, { prefix: step.into ? 'revive' : '', hand: [] });
    nested.forEach(s => { s.into = step.into; });
    flow.steps = nested.concat(flow.steps);
    advanceFlow();
  }
}

function onHandPick(card) {
  const step = flow.steps[0];
  flow.steps.shift();
  (step.into ? flow.params.revive : flow.params)[step.param] = card.animal;
  const nested = stepsFor(card.name, { prefix: step.into ? 'revive' : '', hand: [] });
  nested.forEach(s => { s.into = step.into; });
  flow.steps = nested.concat(flow.steps);
  advanceFlow();
}

async function advanceFlow() {
  if (flow.steps.length > 0) { renderGame(); return; }
  // all decisions made: fetch the dry-run and SHOW the outcome
  const { card, cardInfo, params } = flow;
  flow = null;
  try {
    const data = await api('/api/preview', { room: session.room, token: session.token, card, params });
    preview = { card, cardInfo, params, data };
  } catch (e) {
    showStatus(`⚠️ ${e.message}`);
    return;
  }
  renderGame();
}

async function commitPreview() {
  const { card, params } = preview;
  preview = null;
  inspect = null;
  try {
    state = await api('/api/play', { room: session.room, token: session.token, card, params });
    onState();
    startPolling();   // switch to the fast schedule while others respond
  } catch (e) {
    showStatus(`⚠️ ${e.message}`);
  }
}

function cancelAll() {
  flow = null; preview = null; inspect = null;
  renderGame();
}

/* ---------- log & end ---------- */

function renderLog() {
  const box = $('#log');
  box.innerHTML = '';
  for (const e of state.log) {
    const div = document.createElement('div');
    div.className = 'log-entry';
    const played = `<span class="chip p${e.player}"></span><b>${playerName(e.player)}</b> ▶ ` +
      `${EMOJI[e.played.name]} ${label(e.played.name)}` +
      (e.as ? ` 🎭${EMOJI[e.as] || label(e.as)}` : '');
    const parts = [played];
    if (e.to_trash.length) {
      parts.push(`<span class="trash-note">🚮 ${e.to_trash.map(c => EMOJI[c.name]).join(' ')}</span>`);
    }
    if (e.to_bar.length) {
      const note = e.gate_opened ? '<span class="gate-note">🚪✨</span> ' : '';
      parts.push(note + `<span class="bar-note">🍸 ${e.to_bar.map(c => EMOJI[c.name]).join(' ')}</span>`);
    }
    div.innerHTML = parts.join(' &nbsp;');
    box.appendChild(div);
  }
  box.scrollTop = box.scrollHeight;
}

function renderEnd() {
  const overlay = $('#end-overlay');
  if (!state.finished) { overlay.classList.add('hidden'); return; }
  overlay.classList.remove('hidden');
  const winners = state.winners || [];
  const mineWin = winners.filter(w => mySeats().includes(w));
  $('#end-title').textContent = mineWin.length && !isHotseat()
    ? (winners.length === 1 ? '🏆 You win!' : '🤝 Shared win!')
    : `🏆 ${winners.map(playerName).join(' & ')}`;
  const unit = state.scoring === 'points' ? '🏅' : '🍸';
  const rows = state.players.map((p, i) => {
    const score = (state.results && state.results[i]) || 0;
    return `<tr><td><span class="chip p${i}"></span>${playerName(i)}</td><td>${unit} ${score}</td></tr>`;
  });
  $('#end-table').innerHTML = rows.join('');
}

/* ---------- boot ---------- */

(function boot() {
  refreshHomeForm();
  nameInputs('#join-names', ui.joinLocal);

  const room = roomFromUrl();
  if (!room) { show('home'); return; }
  const saved = loadSession(room);
  if (saved && saved.token) {
    session = saved;
    startPolling();
    show('lobby');
  } else {
    show('join');
  }
})();
