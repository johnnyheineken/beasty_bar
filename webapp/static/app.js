const EMOJI = {
  12: '🦁', 11: '🦛', 10: '🐊', 9: '🐍', 8: '🦒', 7: '🦓',
  6: '🦭', 5: '🦎', 4: '🐒', 3: '🦘', 2: '🦜', 1: '🦨',
};
const NAMES = {
  12: 'Lion', 11: 'Hippo', 10: 'Croc', 9: 'Snake', 8: 'Giraffe', 7: 'Zebra',
  6: 'Seal', 5: 'Chameleon', 4: 'Monkey', 3: 'Kangaroo', 2: 'Parrot', 1: 'Skunk',
};
const HINTS = {
  12: 'Throws out all monkeys and goes to the front. A second lion is thrown out itself.',
  11: 'Recurring: pushes to the front, blocked by lions, zebras and other hippos.',
  10: 'Recurring: eats all weaker animals in front of it, blocked by stronger animals and zebras.',
  9: 'Sorts the whole queue by strength, strongest at the gate.',
  8: 'Recurring: steps over one weaker animal in front of it per turn.',
  7: 'Recurring: blocks hippos and crocs, protecting everyone in front of it.',
  6: 'Swaps Heaven’s Gate and the exclusion side: the queue reverses.',
  5: 'Copies the action (and strength) of a species in the queue, then is a 5 again.',
  4: 'With another monkey present: throws out all hippos & crocs, monkeys jump to the front.',
  3: 'Jumps over the last one or two animals in line — your choice.',
  2: 'Shoos one animal of your choice out of the queue.',
  1: 'Throws out all animals of the two strongest species (never skunks).',
};

const $ = (sel) => document.querySelector(sel);
const AI_DELAY = 850;

let state = null;
let pending = null;   // null | {type, ...}
let aiTimer = null;
let lastLogLen = 0;

function playerName(id) { return id === 0 ? 'You' : `Player ${id}`; }

async function api(path, body) {
  const opts = body !== undefined
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : {};
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'request failed');
  return data;
}

function setState(newState) {
  state = newState;
  render();
  scheduleAi();
}

function scheduleAi() {
  clearTimeout(aiTimer);
  if (!state || state.finished || state.current_player === 0) return;
  aiTimer = setTimeout(async () => {
    try { setState(await api('/api/step', {})); }
    catch (e) { showStatus(e.message); }
  }, AI_DELAY);
}

/* ---------- rendering ---------- */

function cardEl(card, opts = {}) {
  const el = document.createElement('div');
  el.className = `card p${card.player}`;
  el.title = `${NAMES[card.animal]} (${card.animal}) — ${HINTS[card.animal]}`;
  el.innerHTML = `
    <div class="cvalue">${card.animal}</div>
    <div class="emoji">${EMOJI[card.animal]}</div>
    <div class="cname">${NAMES[card.animal]}</div>`;
  if (opts.entering) el.classList.add('entering');
  return el;
}

function render() {
  renderPiles();
  renderOpponents();
  renderQueue();
  renderHand();
  renderLog();
  renderStatusAndChoices();
  renderEnd();
}

function breakdown(cards) {
  const counts = {};
  for (const c of cards) counts[c.player] = (counts[c.player] || 0) + 1;
  return Object.entries(counts)
    .map(([p, n]) => `<span class="chip p${p}"></span>${n}`)
    .join(' ');
}

function renderPiles() {
  $('#bar-count').textContent = state.bar.length;
  $('#bar-breakdown').innerHTML = breakdown(state.bar);
  $('#trash-count').textContent = state.trash.length;
  $('#trash-breakdown').innerHTML = breakdown(state.trash);
}

function renderOpponents() {
  const box = $('#opponents');
  box.innerHTML = '';
  for (const p of state.players) {
    const el = document.createElement('div');
    el.className = 'player-chip';
    el.style.borderTopColor = getComputedStyle(document.documentElement).getPropertyValue(`--p${p.id}`);
    if (!state.finished && state.current_player === p.id) el.classList.add('active');
    el.innerHTML = `
      <span class="pname">${playerName(p.id)}${p.is_human ? '' : ' 🤖'}</span>
      <span class="pmeta">✋ ${p.hand_count} &nbsp; 🂠 ${p.deck_count} &nbsp; 🍸 ${p.in_bar}</span>`;
    box.appendChild(el);
  }
}

function renderQueue() {
  const box = $('#queue');
  box.innerHTML = '';
  const lastPlayed = state.last_turn && state.log.length > lastLogLen ? state.last_turn.played : null;
  state.queue.forEach((card, i) => {
    const entering = lastPlayed && lastPlayed.animal === card.animal && lastPlayed.player === card.player;
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
  if (!pending) return;
  const wantsTarget = pending.type === 'parrot-target' || pending.type === 'chameleon-target';
  const wantsSpecies = pending.type === 'chameleon-species';
  if (wantsTarget || (wantsSpecies && card.animal !== 5)) {
    el.classList.add('selectable');
    el.onclick = () => onQueuePick(card, index);
  } else if (pending) {
    el.classList.add('dimmed');
  }
}

function renderHand() {
  const box = $('#hand');
  box.innerHTML = '';
  const myTurn = !state.finished && state.current_player === 0;
  for (const card of state.hand) {
    const el = cardEl(card);
    if (myTurn && !pending) {
      el.classList.add('clickable');
      el.onclick = () => onHandClick(card);
    } else if (pending && pending.card === card.animal) {
      el.classList.add('selected');
      el.onclick = cancelPending;
    } else {
      el.classList.add('dimmed');
    }
    box.appendChild(el);
  }
}

function renderStatusAndChoices() {
  const buttons = $('#choice-buttons');
  buttons.innerHTML = '';
  if (state.finished) { showStatus('Game over.'); return; }

  if (pending) {
    if (pending.type === 'parrot-target') showStatus('🦜 Pick the animal to throw out (click a card in the queue).');
    if (pending.type === 'chameleon-species') showStatus('🦎 Pick a species in the queue to imitate.');
    if (pending.type === 'chameleon-target') showStatus('🦎→🦜 Pick the animal to throw out.');
    if (pending.type === 'kangaroo-jump') {
      showStatus(pending.imitate ? '🦎→🦘 Jump over how many animals?' : '🦘 Jump over how many animals?');
      for (const n of [1, 2]) {
        if (n > state.queue.length) continue;
        const b = document.createElement('button');
        b.textContent = `Jump ${n}`;
        b.onclick = () => playCard(pending.card, withImitate({ jump: n }));
        buttons.appendChild(b);
      }
    }
    const cancel = document.createElement('button');
    cancel.textContent = 'Cancel';
    cancel.className = 'cancel';
    cancel.onclick = cancelPending;
    buttons.appendChild(cancel);
    return;
  }

  if (state.current_player === 0) {
    if (state.hand.length) showStatus('Your turn — click a card to play it.');
    else showStatus('No cards left — waiting for the others to finish.');
  } else {
    showStatus(`${playerName(state.current_player)} is thinking…`);
  }
}

function showStatus(msg) { $('#status').textContent = msg; }

function renderLog() {
  const box = $('#log');
  box.innerHTML = '';
  for (const e of state.log) {
    const div = document.createElement('div');
    div.className = 'log-entry';
    const played = `<span class="chip p${e.player}"></span><b>${playerName(e.player)}</b> played ` +
      `${EMOJI[e.played.animal]} ${NAMES[e.played.animal]}` +
      (e.as ? ` as ${e.as === 'Gazelle' ? 'Giraffe' : e.as}` : '');
    const parts = [played];
    if (e.to_trash.length) {
      parts.push(`<span class="trash-note">🚮 out: ${e.to_trash.map(c => EMOJI[c.animal] + ' P' + c.player).join(', ')}</span>`);
    }
    if (e.gate_opened && e.to_bar.length) {
      parts.push(`<span class="gate-note">🚪 Gate opened!</span> <span class="bar-note">🍸 in: ${e.to_bar.map(c => EMOJI[c.animal] + ' P' + c.player).join(', ')}</span>`);
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
  $('#end-title').textContent = winners.includes(0)
    ? (winners.length === 1 ? '🏆 You win!' : '🤝 You tie for the win!')
    : `🏆 ${winners.map(playerName).join(' & ')} win${winners.length === 1 ? 's' : ''}!`;
  const rows = state.players.map(p => {
    const guests = (state.results && state.results[p.id]) || 0;
    const valueSum = state.bar.filter(c => c.player === p.id).reduce((s, c) => s + c.animal, 0);
    return `<tr><td><span class="chip p${p.id}"></span>${playerName(p.id)}</td><td>${guests} guests</td><td>value ${valueSum}</td></tr>`;
  });
  $('#end-table').innerHTML = '<tr><th></th><th>In the bar</th><th>Tie-break</th></tr>' + rows.join('');
}

/* ---------- interactions ---------- */

function onHandClick(card) {
  const v = card.animal;
  if (v === 2 && state.queue.length) {
    pending = { type: 'parrot-target', card: v };
  } else if (v === 3 && state.queue.length >= 2) {
    pending = { type: 'kangaroo-jump', card: v };
  } else if (v === 5 && state.queue.some(c => c.animal !== 5)) {
    pending = { type: 'chameleon-species', card: v };
  } else {
    playCard(v, {});
    return;
  }
  render();
}

function onQueuePick(card, index) {
  if (pending.type === 'parrot-target') {
    playCard(pending.card, { target_index: index });
  } else if (pending.type === 'chameleon-target') {
    playCard(pending.card, { imitate: pending.imitate, target_index: index });
  } else if (pending.type === 'chameleon-species') {
    const species = card.animal;
    if (species === 2 && state.queue.length) {
      pending = { type: 'chameleon-target', card: 5, imitate: 2 };
      render();
    } else if (species === 3 && state.queue.length >= 2) {
      pending = { type: 'kangaroo-jump', card: 5, imitate: 3 };
      render();
    } else {
      playCard(5, { imitate: species });
    }
  }
}

function withImitate(params) {
  if (pending && pending.imitate) params.imitate = pending.imitate;
  return params;
}

function cancelPending() {
  pending = null;
  render();
}

async function playCard(animal, params) {
  pending = null;
  try {
    setState(await api('/api/play', { card: animal, params }));
  } catch (e) {
    showStatus(`⚠️ ${e.message}`);
    scheduleAi();
  }
}

async function newGame(players) {
  pending = null;
  lastLogLen = 0;
  try { setState(await api('/api/new', { players })); }
  catch (e) { showStatus(`⚠️ ${e.message}`); }
}

document.querySelectorAll('.new-game button').forEach(b => {
  b.onclick = () => newGame(parseInt(b.dataset.players, 10));
});

api('/api/state').then(setState).catch(e => showStatus(`⚠️ ${e.message}`));
