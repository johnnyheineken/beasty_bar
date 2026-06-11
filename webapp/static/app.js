/* Beasty Bar web client: home -> lobby -> game, with multiplayer rooms. */

const EMOJI = {
  Lion: '🦁', Hippo: '🦛', Croc: '🐊', Snake: '🐍', Gazelle: '🦒', Zebra: '🦓',
  Seal: '🦭', Chameleon: '🦎', Monkey: '🐒', Kangaroo: '🦘', Parrot: '🦜', Skunk: '🦨',
  Rhino: '🦏', Bear: '🐻', Tiger: '🐯', Cheetah: '🐆', Llama: '🦙', Porcupine: '🦔',
  Ostrich: '🦤', Penguin: '🐧', Dog: '🐕', Peacock: '🦚', Vulture: '🦅', Bat: '🦇',
};
const LABEL = { Gazelle: 'Giraffe', Croc: 'Croc' };
const HINTS = {
  Lion: 'Throws out all monkeys, goes to the front. A second lion is thrown out itself.',
  Hippo: 'Recurring: pushes to the front; blocked by lions, zebras, hippos.',
  Croc: 'Recurring: eats all weaker animals ahead; blocked by stronger animals and zebras.',
  Snake: 'Sorts the queue, strongest at the gate.',
  Gazelle: 'Recurring: steps over one weaker animal per turn.',
  Zebra: 'Blocks hippos and crocs; protects everyone in front of it.',
  Seal: 'Reverses the whole queue.',
  Chameleon: 'Copies a species in the queue, with its strength, then is a 5 again.',
  Monkey: 'With another monkey present: throws out hippos & crocs, monkeys storm the gate.',
  Kangaroo: 'Jumps over the last one or two animals — your choice.',
  Parrot: 'Shoos one animal of your choice out of the queue.',
  Skunk: 'Throws out all animals of the two strongest species (never skunks).',
  Rhino: 'Rams the strongest animal out of the queue and takes its place.',
  Bear: 'Sends all animals of the two weakest strengths to the back of the line.',
  Tiger: 'Recurring: leaps two places ahead and eats that animal if weaker.',
  Cheetah: 'Eats the weakest animal in the line and takes its place.',
  Llama: 'Recurring: spits the animal in front of it (if ≤7) to the back of the line.',
  Porcupine: 'Reflects rhino/tiger/cheetah attacks back at the attacker. Permanent.',
  Ostrich: 'Runs past all even OR all odd animals — your choice.',
  Penguin: 'Acts as another animal from your hand (the card stays in your hand).',
  Dog: 'Sorts the queue, weakest at the gate.',
  Peacock: 'Stands directly in front of the strongest animal.',
  Vulture: 'Revives the top card of the trash pile, then lands on the trash itself.',
  Bat: 'Replaces any animal in the queue — but burns up if ever first in line.',
};
const DECK_HINTS = {
  classic: 'The original 12 animals. Most guests in the bar wins.',
  new_beasts: 'The 12 expansion animals. Card points decide the winner.',
  mixed: 'A random mix of both sets per player (one animal per value). Points win.',
};

const $ = (sel) => document.querySelector(sel);
const POLL_MS = 1100;

let state = null;
let flow = null;            // pending multi-step choice
let pollTimer = null;
let lastLogLen = 0;
let session = null;         // {room, token, seat}
const ui = { deck: 'classic', total: 4, humans: 1 };

function label(name) { return LABEL[name] || name; }
function playerName(id) {
  if (!state) return `Player ${id + 1}`;
  const p = state.players[id];
  return (state.you === id) ? 'You' : p.name;
}

/* ---------- session storage / routing ---------- */

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

$('#create-btn').onclick = async () => {
  try {
    const res = await api('/api/room', {
      players: ui.total, humans: ui.humans, deck: ui.deck,
      name: $('#player-name').value,
    });
    localStorage.setItem('beasty_name', $('#player-name').value);
    saveSession(res);
    startPolling();
  } catch (e) { $('#home-error').textContent = e.message; }
};

$('#join-btn').onclick = async () => {
  try {
    const res = await api('/api/join', { room: roomFromUrl(), name: $('#join-name').value });
    localStorage.setItem('beasty_name', $('#join-name').value);
    saveSession(res);
    startPolling();
  } catch (e) { $('#join-error').textContent = e.message; }
};

$('#again-btn').onclick = () => {
  stopPolling();
  $('#end-overlay').classList.add('hidden');
  location.hash = '';
  state = null; session = null; flow = null; lastLogLen = 0;
  show('home');
};

/* ---------- lobby ---------- */

function renderLobby() {
  show('lobby');
  const seats = $('#lobby-seats');
  seats.innerHTML = '';
  state.players.forEach((p, i) => {
    const div = document.createElement('div');
    div.className = 'seat' + (p.claimed ? '' : ' open');
    div.innerHTML = `<span class="who"><span class="chip p${i}"></span>${p.claimed ? p.name : 'waiting for a friend…'}</span>` +
      `<span>${p.is_ai ? '🤖' : (p.claimed ? '✅' : '⏳')}</span>`;
    seats.appendChild(div);
  });
  const link = location.origin + '/#r=' + session.room;
  $('#invite-link').value = link;
}

$('#copy-btn').onclick = async () => {
  try { await navigator.clipboard.writeText($('#invite-link').value); $('#copy-btn').textContent = '✅'; }
  catch { $('#invite-link').select(); document.execCommand('copy'); }
  setTimeout(() => { $('#copy-btn').textContent = 'Copy'; }, 1200);
};
$('#share-btn').onclick = () => {
  const url = $('#invite-link').value;
  if (navigator.share) navigator.share({ title: 'Beasty Bar', text: 'Join my Beasty Bar game!', url });
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
  if ($('#screen-game').classList.contains('hidden')) show('game');
  renderGame();
}

/* ---------- game rendering ---------- */

function cardEl(card, opts = {}) {
  const el = document.createElement('div');
  el.className = `card p${card.player}`;
  el.title = `${label(card.name)} (${card.animal}) — ${HINTS[card.name] || ''}`;
  el.innerHTML = `
    <div class="cvalue">${card.animal}</div>
    <div class="emoji">${EMOJI[card.name] || '❓'}</div>
    <div class="cname">${label(card.name)}</div>`;
  if (opts.entering) el.classList.add('entering');
  return el;
}

function renderGame() {
  $('#deck-badge').textContent =
    state.deck === 'classic' ? '🦁 classic' : state.deck === 'new_beasts' ? '🦏 new beasts' : '🔀 mixed';
  renderPlayers();
  renderPiles();
  renderQueue();
  renderHand();
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
    const score = state.scoring === 'points' ? `${p.score}pt` : `🍸${p.in_bar}`;
    el.innerHTML = `<span class="pname">${playerName(i)}${p.is_ai ? ' 🤖' : ''}</span><br>` +
      `<span class="pmeta">✋${p.hand_count} 🂠${p.deck_count} ${score}</span>`;
    strip.appendChild(el);
  });
}

function renderPiles() {
  $('#bar-count').textContent = state.bar_count;
  $('#trash-count').textContent = state.trash_count;
  $('#trash-top').textContent = state.trash_top
    ? `top: ${EMOJI[state.trash_top.name]} ${state.trash_top.animal}` : '';
}

function renderQueue() {
  const box = $('#queue');
  box.innerHTML = '';
  const lastEntry = state.log[state.log.length - 1];
  const fresh = state.log.length > lastLogLen ? lastEntry : null;
  state.queue.forEach((card, i) => {
    const entering = fresh && fresh.played.name === card.name && fresh.played.player === card.player;
    const el = cardEl(card, { entering });
    decorateQueueCard(el, card, i);
    box.appendChild(el);
  });
  for (let i = state.queue.length; i < 5; i++) {
    const slot = document.createElement('div');
    slot.className = 'slot';
    box.appendChild(slot);
  }
  lastLogLen = state.log.length;
}

function decorateQueueCard(el, card, index) {
  if (!flow) return;
  const step = flow.steps[0];
  if (!step) return;
  if (step.type === 'pick-queue' || (step.type === 'pick-species' && card.name !== 'Chameleon')) {
    el.classList.add('selectable');
    el.onclick = () => onQueuePick(card, index);
  } else {
    el.classList.add('dimmed');
  }
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
    } else if (myTurn) {
      el.classList.add('clickable');
      el.onclick = () => startFlow(card);
    } else {
      el.classList.add('dimmed');
    }
    box.appendChild(el);
  }
}

function showStatus(msg) { $('#status').textContent = msg; }

function renderChoices() {
  const buttons = $('#choice-buttons');
  buttons.innerHTML = '';
  if (state.finished) { showStatus('Game over.'); return; }

  if (flow) {
    const step = flow.steps[0];
    showStatus(step.prompt);
    if (step.type === 'jump') {
      for (const n of [1, 2]) {
        if (n > state.queue.length) continue;
        const b = document.createElement('button');
        b.className = 'primary';
        b.textContent = `Jump over ${n}`;
        b.onclick = () => answerStep({ [step.param || 'jump']: n });
        buttons.appendChild(b);
      }
    }
    if (step.type === 'parity') {
      for (const par of ['even', 'odd']) {
        const b = document.createElement('button');
        b.className = 'primary';
        b.textContent = par === 'even' ? 'Run past EVEN (2,4,6…)' : 'Run past ODD (1,3,5…)';
        b.onclick = () => answerStep({ [step.param || 'parity']: par });
        buttons.appendChild(b);
      }
    }
    const cancel = document.createElement('button');
    cancel.textContent = 'Cancel';
    cancel.onclick = cancelFlow;
    buttons.appendChild(cancel);
    return;
  }

  if (state.you === null) { showStatus('You are watching this game.'); return; }
  if (state.current_player === state.you) {
    showStatus(state.hand.length ? 'Your turn — tap a card.' : 'No cards left — waiting for the others.');
  } else {
    showStatus(`${playerName(state.current_player)} is thinking…`);
  }
}

/* ---------- choice flow ----------
   flow = { card: <hand card value>, params: {}, reviveMode: bool, steps: [...] } */

function stepsFor(kindName, opts) {
  // opts: {prefix: '' | 'revive', queueLen, hand}
  const into = opts.prefix === 'revive';
  const q = state.queue.length;
  const steps = [];
  const who = into ? `${label(kindName)} (revived)` : label(kindName);
  if (kindName === 'Parrot' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', prompt: `🦜 ${who}: tap the animal to throw out.` });
  } else if (kindName === 'Kangaroo' && q >= 2) {
    steps.push({ type: 'jump', into, param: 'jump', prompt: `🦘 ${who}: jump over how many animals?` });
  } else if (kindName === 'Bat' && q) {
    steps.push({ type: 'pick-queue', into, param: 'target_index', prompt: `🦇 ${who}: tap the animal to replace (first position burns the bat!).` });
  } else if (kindName === 'Ostrich' && q) {
    steps.push({ type: 'parity', into, param: 'parity', prompt: `🦤 ${who}: run past even or odd values?` });
  } else if (kindName === 'Chameleon' && state.queue.some(c => c.name !== 'Chameleon')) {
    steps.push({ type: 'pick-species', into, param: 'imitate', prompt: '🦎 Chameleon: tap the species to imitate.' });
  } else if (kindName === 'Penguin' && opts.hand && opts.hand.length) {
    steps.push({ type: 'pick-hand', into, param: 'imitate_value', prompt: '🐧 Penguin: tap the hand card to imitate.' });
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
    flow.steps = stepsFor(card.name, { hand: state.hand.filter(c => c !== card && c.animal !== card.animal) });
  }
  advanceFlow();
}

function answerStep(answer) {
  const step = flow.steps.shift();
  const bucket = step.into ? flow.params.revive : flow.params;
  Object.assign(bucket, answer);
  advanceFlow();
}

function onQueuePick(card, index) {
  const step = flow.steps[0];
  if (step.type === 'pick-queue') {
    answerStep({ [step.param]: index });
  } else if (step.type === 'pick-species') {
    flow.steps.shift();
    const bucket = step.into ? flow.params.revive : flow.params;
    bucket[step.param] = card.animal;
    // the imitated species may itself need a decision (e.g. parrot target)
    const nested = stepsFor(card.name, { prefix: step.into ? 'revive' : '', hand: [] });
    nested.forEach(s => { s.into = step.into; });
    flow.steps = nested.concat(flow.steps);
    advanceFlow();
  }
}

function onHandPick(card) {
  const step = flow.steps[0];
  flow.steps.shift();
  const bucket = step.into ? flow.params.revive : flow.params;
  bucket[step.param] = card.animal;
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

function cancelFlow() {
  flow = null;
  renderGame();
}

async function playCard(animal, params) {
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
    const played = `<span class="chip p${e.player}"></span><b>${playerName(e.player)}</b> played ` +
      `${EMOJI[e.played.name]} ${label(e.played.name)}` +
      (e.as ? ` as ${label(e.as)}` : '');
    const parts = [played];
    if (e.to_trash.length) {
      parts.push(`<span class="trash-note">🚮 out: ${e.to_trash.map(c => EMOJI[c.name] + ' P' + (c.player + 1)).join(', ')}</span>`);
    }
    if (e.to_bar.length) {
      const note = e.gate_opened ? '<span class="gate-note">🚪 Gate opened!</span> ' : '';
      parts.push(note + `<span class="bar-note">🍸 in: ${e.to_bar.map(c => EMOJI[c.name] + ' P' + (c.player + 1)).join(', ')}</span>`);
    }
    div.innerHTML = parts.join('<br>');
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
    ? (winners.length === 1 ? '🏆 You win!' : '🤝 You tie for the win!')
    : `🏆 ${winners.map(playerName).join(' & ')} win${winners.length === 1 ? 's' : ''}!`;
  const unit = state.scoring === 'points' ? 'points' : 'guests';
  const rows = state.players.map((p, i) => {
    const score = (state.results && state.results[i]) || 0;
    return `<tr><td><span class="chip p${i}"></span>${playerName(i)}</td><td>${score} ${unit}</td></tr>`;
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
