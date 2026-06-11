/* Beasty Bar web client: home -> lobby -> game, with multiplayer rooms. */

const EMOJI = {
  Lion: '🦁', Hippo: '🦛', Croc: '🐊', Snake: '🐍', Gazelle: '🦒', Zebra: '🦓',
  Seal: '🦭', Chameleon: '🦎', Monkey: '🐒', Kangaroo: '🦘', Parrot: '🦜', Skunk: '🦨',
  Rhino: '🦏', Bear: '🐻', Tiger: '🐯', Cheetah: '🐆', Llama: '🦙', Porcupine: '🦔',
  Ostrich: '🦤', Penguin: '🐧', Dog: '🐕', Peacock: '🦚', Vulture: '🦅', Bat: '🦇',
};
const LABEL = { Gazelle: 'Giraffe' };

/* Pictogram language:
   🔁 recurring · ♾️ always on · 🛡️ protects · 🎭 copies · ↕️ sorts
   ⏩ pushes forward · 🔄 reverses · ↷ jumps · 🚮 throws out · 😋 eats */
const ICONS = {
  Lion:      '🚮🐒 ⏩🚪',
  Hippo:     '🔁 ⏩ ✋🦁🦓🦛',
  Croc:      '🔁 😋⬅️ ✋🦁🦛🦓',
  Snake:     '↕️ 💪→🚪',
  Gazelle:   '🔁 ↷1️⃣🐭',
  Zebra:     '♾️🛡️ ⛔🦛🐊',
  Seal:      '🔄 🚪⇄⛔',
  Chameleon: '🎭 ⬇️👀',
  Monkey:    '🐒🐒 🚮🦛🐊 ⏩🚪',
  Kangaroo:  '↷ 1️⃣/2️⃣',
  Parrot:    '🚮 👆',
  Skunk:     '🚮 💪💪',
  Rhino:     '🚮💪 📍',
  Bear:      '🐭🐭 ↩️',
  Tiger:     '🔁 ↷ 😋🐭 📍',
  Cheetah:   '😋🐭 📍',
  Llama:     '🔁 💦⬅️ ↩️',
  Porcupine: '♾️🛡️ 🪃🦏🐯🐆',
  Ostrich:   '🏃 2️⃣4️⃣6️⃣/1️⃣3️⃣5️⃣',
  Penguin:   '🎭 ✋👀',
  Dog:       '↕️ 🐭→🚪',
  Peacock:   '📍 ⬅️💪',
  Vulture:   '♻️ 🚮🔝',
  Bat:       '👆📍 🚪=💥',
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
const TRAIT = {   // mini icon shown on the card itself
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
let flow = null;            // pending multi-step choice
let inspect = null;         // card being looked at in the action bar
let pollTimer = null;
let lastLogLen = null;
let session = null;         // {room, token, seat}
let prevRects = {};         // queue card key -> DOMRect (for FLIP)
let prevCounts = { bar: 0, trash: 0 };
const ui = { deck: 'classic', total: 4, humans: 1 };

function label(name) { return LABEL[name] || name; }
function cardKey(c) { return `${c.name}-${c.player}`; }
function playerName(id) {
  if (!state) return `Player ${id + 1}`;
  return (state.you === id) ? 'You' : state.players[id].name;
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

/* ---------- home ---------- */

function segInit(sel, key, attr) {
  $(sel).addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    for (const x of $(sel).querySelectorAll('button')) x.classList.remove('on');
    b.classList.add('on');
    ui[key] = attr === 'deck' ? b.dataset.deck : parseInt(b.dataset.n, 10);
    if (key === 'deck') $('#deck-hint').textContent = DECK_HINTS[ui.deck];
    if (key === 'total') clampHumans();
  });
}

function clampHumans() {
  for (const b of $('#humans-select').querySelectorAll('button')) {
    const n = parseInt(b.dataset.n, 10);
    b.style.display = n <= ui.total ? '' : 'none';
    if (n > ui.total && b.classList.contains('on')) {
      b.classList.remove('on');
      $('#humans-select button[data-n="1"]').classList.add('on');
      ui.humans = 1;
    }
  }
}

segInit('#deck-select', 'deck', 'deck');
segInit('#total-select', 'total');
segInit('#humans-select', 'humans');

async function guarded(btn, fn, errBox) {
  btn.disabled = true;
  try { await fn(); }
  catch (e) { $(errBox).textContent = '⚠️ ' + e.message; }
  finally { btn.disabled = false; }
}

$('#create-btn').onclick = (e) => guarded(e.target, async () => {
  const res = await api('/api/room', {
    players: ui.total, humans: ui.humans, deck: ui.deck, name: $('#player-name').value,
  });
  localStorage.setItem('beasty_name', $('#player-name').value);
  saveSession(res);
  startPolling();
}, '#home-error');

$('#join-btn').onclick = (e) => guarded(e.target, async () => {
  const res = await api('/api/join', { room: roomFromUrl(), name: $('#join-name').value });
  localStorage.setItem('beasty_name', $('#join-name').value);
  saveSession(res);
  startPolling();
}, '#join-error');

$('#again-btn').onclick = () => {
  stopPolling();
  $('#end-overlay').classList.add('hidden');
  location.hash = '';
  state = null; session = null; flow = null; inspect = null; lastLogLen = null;
  show('home');
};

$('#help-btn').onclick = () => $('#help-overlay').classList.remove('hidden');
$('#help-close').onclick = () => {
  localStorage.setItem('beasty_seen', '1');
  $('#help-overlay').classList.add('hidden');
};

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

function startPolling() {
  stopPolling();
  const poll = async () => {
    try {
      state = await api(`/api/state?room=${session.room}&token=${session.token}`);
      onState();
    } catch (e) {
      if (e.status === 404) { $('#again-btn').click(); alert(e.message); return; }
    }
    pollTimer = setTimeout(poll, POLL_MS);
  };
  poll();
}
function stopPolling() { clearTimeout(pollTimer); pollTimer = null; }

function onState() {
  if (!state.started) { renderLobby(); return; }
  if ($('#screen-game').classList.contains('hidden')) {
    show('game');
    if (!localStorage.getItem('beasty_seen')) $('#help-overlay').classList.remove('hidden');
  }
  renderGame();
}

/* ---------- rendering ---------- */

function cardEl(card) {
  const el = document.createElement('div');
  el.className = `card p${card.player}`;
  el.dataset.key = cardKey(card);
  el.innerHTML = `
    <div class="cvalue">${card.animal}</div>
    <div class="emoji">${EMOJI[card.name] || '❓'}</div>
    ${TRAIT[card.name] ? `<div class="ctrait">${TRAIT[card.name]}</div>` : ''}`;
  return el;
}

function renderGame() {
  $('#deck-badge').textContent =
    state.deck === 'classic' ? '🦁' : state.deck === 'new_beasts' ? '🦏' : '🔀';
  renderPlayers();
  renderPiles();
  renderQueue();
  renderHand();
  renderActionBar();
  renderChoices();
  renderLog();
  renderEnd();
}

function renderPlayers() {
  const strip = $('#players-strip');
  strip.innerHTML = '';
  state.players.forEach((p, i) => {
    const el = document.createElement('div');
    el.className = 'pchip';
    el.style.borderTopColor = getComputedStyle(document.documentElement).getPropertyValue(`--p${i}`);
    if (!state.finished && state.current_player === i) el.classList.add('active');
    const score = state.scoring === 'points' ? `🏅${p.score}` : `🍸${p.in_bar}`;
    el.innerHTML = `<span class="pname">${playerName(i)}${p.is_ai ? '🤖' : ''}</span><br>` +
      `<span class="pmeta">✋${p.hand_count} ${score}</span>`;
    strip.appendChild(el);
  });
}

function renderPiles() {
  $('#bar-count').textContent = state.bar_count;
  $('#trash-count').textContent = state.trash_count;
  $('#trash-top').textContent = state.trash_top
    ? `${EMOJI[state.trash_top.name]}${state.trash_top.animal}` : '·';
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

  // FLIP step 1: remember where each card was
  const oldRects = {};
  for (const el of box.querySelectorAll('.card')) {
    oldRects[el.dataset.key] = el.getBoundingClientRect();
  }

  box.innerHTML = '';
  const total = state.log_total ?? state.log.length;
  const newCount = lastLogLen === null ? 0 : Math.max(0, total - lastLogLen);
  const freshEntries = newCount ? state.log.slice(-Math.min(newCount, state.log.length)) : [];
  const lastEntry = state.log[state.log.length - 1];
  const isFreshTurn = freshEntries.length > 0;
  state.queue.forEach((card, i) => {
    const el = cardEl(card);
    decorateQueueCard(el, card, i);
    box.appendChild(el);
  });
  for (let i = state.queue.length; i < 5; i++) {
    const slot = document.createElement('div');
    slot.className = 'slot';
    box.appendChild(slot);
  }

  // FLIP step 2: animate moved cards from old to new position
  requestAnimationFrame(() => {
    for (const el of box.querySelectorAll('.card')) {
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
      } else if (isFreshTurn && lastEntry &&
                 el.dataset.key === cardKey(lastEntry.played)) {
        el.classList.add('entering');
      }
    }
  });

  // fly removed cards to the piles
  for (const entry of freshEntries) {
    flyCards(entry.to_bar, oldRects, '#bar-pile');
    flyCards(entry.to_trash, oldRects, '#trash-pile');
  }
  lastLogLen = total;
}

function flyCards(cards, oldRects, pileSel) {
  const pile = $(pileSel).getBoundingClientRect();
  for (const c of cards) {
    const from = oldRects[cardKey(c)];
    if (!from) continue;   // wasn't visible in the line
    const ghost = cardEl(c);
    ghost.style.left = from.left + 'px';
    ghost.style.top = from.top + 'px';
    ghost.style.width = from.width + 'px';
    ghost.style.height = from.height + 'px';
    $('#fly-layer').appendChild(ghost);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      ghost.style.left = (pile.left + pile.width / 2 - from.width / 4) + 'px';
      ghost.style.top = pile.top + 'px';
      ghost.style.transform = 'scale(.4) rotate(8deg)';
      ghost.style.opacity = '0';
    }));
    setTimeout(() => ghost.remove(), 800);
  }
}

function decorateQueueCard(el, card, index) {
  if (flow) {
    const step = flow.steps[0];
    if (step && (step.type === 'pick-queue' || (step.type === 'pick-species' && card.name !== 'Chameleon'))) {
      el.classList.add('selectable');
      el.onclick = () => onQueuePick(card, index);
    } else {
      el.classList.add('dimmed');
    }
    return;
  }
  // no flow: tapping a queue card explains it
  el.classList.add('clickable');
  el.onclick = () => { inspect = { card, inHand: false }; renderGame(); };
}

function renderHand() {
  const box = $('#hand');
  box.innerHTML = '';
  const myTurn = !state.finished && state.you !== null && state.current_player === state.you;
  const step = flow && flow.steps[0];
  for (const card of state.hand) {
    const el = cardEl(card);
    if (step && step.type === 'pick-hand') {
      if (card.animal === flow.card) { el.classList.add('selected'); el.onclick = cancelFlow; }
      else { el.classList.add('selectable', 'clickable'); el.onclick = () => onHandPick(card); }
    } else if (flow) {
      el.classList.toggle('selected', card.animal === flow.card);
      el.classList.toggle('dimmed', card.animal !== flow.card);
      if (card.animal === flow.card) el.onclick = cancelFlow;
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
  if (!inspect || flow) { bar.classList.add('hidden'); return; }
  const c = inspect.card;
  bar.classList.remove('hidden');
  $('#action-emoji').textContent = EMOJI[c.name];
  $('#action-title').textContent = `${label(c.name)} · ${c.animal}`;
  $('#action-icons').textContent = ICONS[c.name] || '';
  $('#action-text').textContent = HINTS[c.name] || '';
  const btns = $('#action-buttons');
  btns.innerHTML = '';
  if (inspect.inHand && inspect.playable) {
    const play = document.createElement('button');
    play.className = 'primary';
    play.textContent = '▶ Play';
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
  if (state.finished) { showStatus('🏁 Game over'); return; }

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
    cancel.onclick = cancelFlow;
    buttons.appendChild(cancel);
    return;
  }

  if (state.you === null) { showStatus('👀 Watching'); return; }
  if (state.current_player === state.you) {
    showStatus(state.hand.length ? '🫵 Your turn — tap a card' : '✅ No cards left');
  } else {
    showStatus(`⏳ ${playerName(state.current_player)}…`);
  }
}

/* ---------- choice flow ---------- */

function stepsFor(kindName, opts) {
  const into = opts.prefix === 'revive';
  const q = state.queue.length;
  const steps = [];
  const e = EMOJI[kindName];
  if (kindName === 'Parrot' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', prompt: `${e} Tap who flies out 🚮` });
  } else if (kindName === 'Kangaroo' && q >= 2) {
    steps.push({ type: 'jump', into, param: 'jump', prompt: `${e} Jump over how many?` });
  } else if (kindName === 'Bat' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', prompt: `${e} Tap whose spot to take (🚪 = 💥!)` });
  } else if (kindName === 'Ostrich' && q) {
    steps.push({ type: 'parity', into, param: 'parity', prompt: `${e} Run past which values?` });
  } else if (kindName === 'Chameleon' && state.queue.some(c => c.name !== 'Chameleon')) {
    steps.push({ type: 'pick-species', into, param: 'imitate', prompt: `${e} Tap the species to copy 🎭` });
  } else if (kindName === 'Penguin' && opts.hand && opts.hand.length) {
    steps.push({ type: 'pick-hand', into, param: 'imitate_value', prompt: `${e} Tap a hand card to copy 🎭` });
  }
  return steps;
}

function startFlow(card) {
  flow = { card: card.animal, params: {}, steps: [] };
  if (card.name === 'Vulture') {
    if (state.trash_top && state.trash_top.name !== 'Vulture') {
      flow.params.revive = {};
      flow.steps = stepsFor(state.trash_top.name, {
        prefix: 'revive',
        hand: state.hand.filter(c => c.animal !== card.animal),
      });
    }
  } else {
    flow.steps = stepsFor(card.name, { hand: state.hand.filter(c => c.animal !== card.animal) });
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

function advanceFlow() {
  if (flow.steps.length === 0) {
    const { card, params } = flow;
    flow = null;
    playCard(card, params);
    return;
  }
  renderGame();
}

function cancelFlow() { flow = null; renderGame(); }

async function playCard(animal, params) {
  flow = null; inspect = null;
  try {
    state = await api('/api/play', { room: session.room, token: session.token, card: animal, params });
    onState();
  } catch (e) {
    showStatus(`⚠️ ${e.message}`);
  }
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
  const youWin = state.you !== null && winners.includes(state.you);
  $('#end-title').textContent = youWin
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
  const savedName = localStorage.getItem('beasty_name') || '';
  $('#player-name').value = savedName;
  $('#join-name').value = savedName;
  clampHumans();

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
