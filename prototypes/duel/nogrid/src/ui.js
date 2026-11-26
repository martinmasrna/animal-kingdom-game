// The page. Drives the engine through its exported transitions only.
import {
  CARDS, HEROES, KIND_LABEL, BASICS, SPEEDS, newMatch, openingEvents, validSet, seqCost,
  commitRound, resolveStep, canPlay, playAction, endTurn, deckSummary,
} from './engine.js';
import { makeRng, botHidden, botOpenAction } from './bot.js';

const ME = 0, BOT = 1;
const STEP_MS = 700, BOT_ACT_MS = 900;

const ui = {
  cfg: { version: 'hidden', me: 'Heavy', opp: 'Quick' },
  s: null, phase: 'start', sel: [], log: [], timers: [], showDecks: false,
  botRng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0),
  turnActs: [[], []], // Open: actions of the current/last turn per side
};

const $ = (id) => document.getElementById(id);
const esc = (t) => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function later(fn, ms) { const t = setTimeout(() => { ui.timers = ui.timers.filter(x => x !== t); fn(); }, ms); ui.timers.push(t); }
function clearTimers() { for (const t of ui.timers) clearTimeout(t); ui.timers = []; }

// ------------------------------------------------------------------ log text
function listAnd(xs) { return xs.length <= 1 ? (xs[0] || '') : xs.slice(0, -1).join(', ') + ' and ' + xs[xs.length - 1]; }
function fmt(e) {
  const Y = e.side === ME;
  const P = Y ? 'Your' : 'His', p = Y ? 'your' : 'his', him = Y ? 'him' : 'you';
  const hitNo = e.hits > 1 ? ` (hit ${e.hit + 1} of ${e.hits})` : '';
  const hidden = ui.s.version === 'hidden';
  const pre = hidden ? (e.step ? `Round ${e.round}, ${e.step}: ` : `Round ${e.round}: `) : `Turn ${e.round}: `;
  switch (e.t) {
    case 'round': return { sep: true, text: `Round ${e.round}` };
    case 'turn': return { sep: true, text: `Turn ${e.round} · ${Y ? 'your' : 'his'} turn` };
    case 'first': return { text: `${Y ? 'You go' : 'He goes'} first; ${Y ? 'he starts' : 'you start'} with one extra card.` };
    case 'start': {
      const drew = e.drew ? (Y ? 'draw a card' : 'draws a card') : `${Y ? 'your' : 'his'} deck is empty, no card drawn`;
      return { text: pre + `${Y ? 'you regain' : 'he regains'} ${e.gain} mana (now ${e.mana}/10), ${drew}.` };
    }
    case 'reveal': return { text: pre + `${Y ? 'you play' : 'he plays'} ${e.acts.length ? listAnd(e.acts) : 'nothing'}.` };
    case 'play': return { text: pre + `${Y ? 'you play' : 'he plays'} ${e.card}.` };
    case 'wind': return { text: pre + `${p} ${e.card} is winding up.` };
    case 'unwind': return { text: pre + `${p} winding ${e.card} resolves.` };
    case 'guard': return { text: pre + `${p} ${e.card} is up.` };
    case 'hit': return { text: pre + `${p} ${e.card}${hitNo} hits ${him} for ${e.dmg}.`, cls: Y ? 'me' : 'opp' };
    case 'stop': return { text: pre + `${p} ${e.guard} stops ${Y ? 'his' : 'your'} ${e.card}${hitNo}.` };
    case 'parry': return { text: pre + `${p} Parry deals 3 to ${him}.`, cls: Y ? 'me' : 'opp' };
    case 'cancel': return { text: pre + `${p} ${e.card} is cancelled and returns to ${p} hand.`, cls: 'warn' };
    case 'heal': return { text: pre + `${p} Bandage heals ${e.amount}.` };
    case 'meditate': return { text: pre + `${p} Meditate gains ${e.amount} mana (now ${e.mana}/10).` };
    case 'sharpen': return { text: pre + `${p} Sharpen: ${p} hits now deal ${e.total} more.` };
    case 'study': return { text: pre + `${p} Study draws ${e.drew} card${e.drew === 1 ? '' : 's'}.` };
    case 'end': return { sep: true, text: e.winner === 'draw' ? 'Draw: both heroes fall in the same step.' : e.winner === ME ? 'You win.' : 'He wins.' };
  }
  return { text: pre + JSON.stringify(e) };
}
function addEvents(ev) {
  for (const e of ev) ui.log.push(fmt(e));
}
// capitalise the first word after the prefix
function lineText(f) { return f.text.replace(/: ([a-z])/, (m, c) => ': ' + c.toUpperCase()); }

// ------------------------------------------------------------------ flow
function startMatch() {
  clearTimers();
  const c = ui.cfg;
  ui.s = newMatch({ version: c.version, heroes: [c.me, c.opp], seed: (Math.random() * 4294967296) >>> 0 });
  ui.sel = []; ui.log = []; ui.turnActs = [[], []];
  addEvents(openingEvents(ui.s));
  if (c.version === 'hidden') ui.phase = 'choose';
  else if (ui.s.turn === ME) ui.phase = 'mine';
  else { ui.phase = 'bot'; later(botStep, BOT_ACT_MS); }
  render();
}

function selNames() { return ui.sel.map(x => (typeof x === 'number' ? ui.s.p[ME].hand[x] : x)); }

function toggle(item) {
  const i = ui.sel.indexOf(item);
  if (i >= 0) ui.sel.splice(i, 1);
  else {
    const name = typeof item === 'number' ? ui.s.p[ME].hand[item] : item;
    if (ui.sel.length >= 2 || !validSet(ui.s, ME, selNames().concat([name]))) return;
    ui.sel.push(item);
  }
  render();
}

function commit() {
  if (ui.phase !== 'choose') return;
  const mine = selNames();
  if (!validSet(ui.s, ME, mine)) return;
  ui.phase = 'thinking'; render();
  later(() => {
    const his = botHidden(ui.s, BOT, ui.botRng); // decided without the player's choice
    const ev = [];
    ui.s = commitRound(ui.s, [mine, his], ev);
    ui.sel = [];
    addEvents(ev);
    ui.phase = 'resolving'; render();
    later(stepHidden, STEP_MS);
  }, 30);
}

function stepHidden() {
  if (ui.phase !== 'resolving') return;
  let ev = [];
  while (ui.s.stepIdx >= 0 && !ev.length) ui.s = resolveStep(ui.s, ev); // empty steps pass at once
  addEvents(ev);
  if (ui.s.winner !== null) { ui.phase = 'over'; render(); return; }
  if (ui.s.stepIdx < 0) { ui.phase = 'choose'; render(); return; }
  render();
  later(stepHidden, STEP_MS);
}
function skipHidden() {
  if (ui.phase !== 'resolving') return;
  clearTimers();
  const ev = [];
  while (ui.s.stepIdx >= 0) ui.s = resolveStep(ui.s, ev);
  addEvents(ev);
  ui.phase = ui.s.winner !== null ? 'over' : 'choose';
  render();
}

function playOpen(name) {
  if (ui.phase !== 'mine' || !canPlay(ui.s, name)) return;
  const ev = [];
  ui.s = playAction(ui.s, name, ev);
  ui.turnActs[ME].push(name);
  addEvents(ev);
  if (ui.s.winner !== null) ui.phase = 'over';
  render();
}
function endMyTurn() {
  if (ui.phase !== 'mine') return;
  const ev = [];
  ui.s = endTurn(ui.s, ev);
  ui.turnActs[BOT] = [];
  addEvents(ev);
  if (ui.s.winner !== null) { ui.phase = 'over'; render(); return; }
  ui.phase = 'bot'; render();
  later(botStep, BOT_ACT_MS);
}
function botStep() {
  if (ui.phase !== 'bot') return;
  const a = botOpenAction(ui.s, ui.botRng);
  const ev = [];
  if (a !== null) {
    ui.s = playAction(ui.s, a, ev);
    ui.turnActs[BOT].push(a);
    addEvents(ev);
    if (ui.s.winner !== null) { ui.phase = 'over'; render(); return; }
    render();
    later(botStep, BOT_ACT_MS);
    return;
  }
  ui.s = endTurn(ui.s, ev);
  ui.turnActs[ME] = [];
  addEvents(ev);
  ui.phase = ui.s.winner !== null ? 'over' : 'mine';
  render();
}

// ------------------------------------------------------------------ render
function effectText(name, p) {
  const c = CARDS[name];
  const sh = p.sharpen;
  if (sh && c.kind !== 'Defence' && c.kind !== 'Setup') return c.hits > 1 ? `Two hits of ${c.dmg}+${sh}.` : `${c.dmg}+${sh} damage.`;
  return c.text;
}
function cardHTML(name, attrs, { cost, disabled, selected, order, basic }) {
  const c = CARDS[name], p = ui.s.p[ME];
  const was = cost < c.cost ? `<s class="was">${c.cost}</s>` : '';
  return `<button class="card${basic ? ' basic' : ''}${selected ? ' sel' : ''}" ${attrs}${disabled ? ' disabled' : ''}>
    <span class="ct"><span class="cn">${name}${order ? ` <span class="ord">${order}</span>` : ''}</span>${was}<span class="cc">${cost}</span></span>
    <span class="cs">${c.speed} · ${c.kind}</span>
    <span class="ce">${esc(effectText(name, p))}</span></button>`;
}

function heroHTML(side) {
  const s = ui.s, p = s.p[side], mine = side === ME;
  const chips = [];
  if (p.sharpen) chips.push(`<span class="chip">Sharpen +${p.sharpen}</span>`);
  const guards = p.guards.filter(g => g.type === 'Brace' || !g.used).map(g => g.type);
  if (guards.length) chips.push(`<span class="chip guard">Guard: ${guards.join(', ')}</span>`);
  if (p.winding.length) chips.push(`<span class="chip wind">Winding: ${p.winding.join(', ')}</span>`);
  const pct = Math.max(0, p.hp) / p.maxHp * 100;
  return `<div class="hrow">
      <span class="hname">${mine ? 'You' : 'He'}: ${p.hero}</span>
      <span class="hp"><b>${Math.max(0, p.hp)}</b>/${p.maxHp} HP</span>
      <span class="mana"><b>${p.mana}</b>/10 mana</span>
    </div>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="hrow2"><span>Hand ${p.hand.length}</span><span>Deck ${p.deck.length}</span>${chips.join('')}</div>`;
}

function actChips(side) {
  const s = ui.s, p = s.p[side];
  if (s.version === 'open') {
    const acts = ui.turnActs[side];
    if (!acts.length) return '<span class="none">nothing yet</span>';
    return acts.map(n => `<span class="act${CARDS[n].speed === 'Slow' ? ' pend' : ''}">${n}${CARDS[n].speed === 'Slow' ? ' (winding)' : ''}</span>`).join('');
  }
  if (ui.phase === 'choose' || ui.phase === 'thinking') {
    if (side === BOT) return `<span class="none">${ui.phase === 'thinking' ? 'He is choosing…' : 'Hidden until both commit'}</span>`;
    const names = selNames();
    return names.length ? names.map((n, i) => `<span class="act pend">${i + 1}. ${n}</span>`).join('') : '<span class="none">nothing chosen</span>';
  }
  const list = s.stepIdx >= 0 ? p.committed : p.lastRound;
  if (!list.length) return '<span class="none">nothing</span>';
  return list.map(a => `<span class="act ${a.status === 'cancelled' ? 'cxl' : a.status === 'done' ? 'done' : 'pend'}">${a.name}<small>${CARDS[a.name].speed}${a.status === 'cancelled' ? ', cancelled' : ''}</small></span>`).join('');
}

function arenaHTML() {
  const s = ui.s;
  let head;
  if (s.version === 'hidden') {
    const cur = ui.phase === 'resolving' ? s.stepIdx : -1;
    head = `<div class="steps"><span>Round ${s.round}</span>` + SPEEDS.map((sp, i) => `<span class="${i === cur ? 'on' : i < cur ? 'past' : ''}">${sp}</span>`).join('') + '</div>';
  } else {
    head = `<div class="steps"><span>Turn ${s.turnNo}</span><span class="on">${s.turn === ME ? 'Your turn' : 'His turn'}</span></div>`;
  }
  return head + `<div class="acts opp"><span class="who">He</span>${actChips(BOT)}</div>
    <div class="acts me"><span class="who">You</span>${actChips(ME)}</div>`;
}

function handHTML() {
  const s = ui.s, p = s.p[ME];
  const out = [];
  const order = p.hand.map((n, i) => i).sort((a, b) => {
    const ca = CARDS[p.hand[a]], cb = CARDS[p.hand[b]];
    return SPEEDS.indexOf(ca.speed) - SPEEDS.indexOf(cb.speed) || ca.cost - cb.cost || p.hand[a].localeCompare(p.hand[b]) || a - b;
  });
  const items = BASICS.map(b => ({ key: b, name: b, attrs: `data-b="${b}"`, basic: true })).concat(order.map(i => ({ key: i, name: p.hand[i], attrs: `data-h="${i}"` })));
  for (const it of items) {
    let cost, disabled, selected = false, ord = 0;
    if (s.version === 'hidden') {
      const names = selNames();
      const si = ui.sel.indexOf(it.key);
      if (si >= 0) {
        selected = true; ord = si + 1;
        cost = seqCost(p, names.slice(0, si + 1), false) - seqCost(p, names.slice(0, si), false);
        disabled = ui.phase !== 'choose';
      } else {
        cost = seqCost(p, names.concat([it.name]), false) - seqCost(p, names, false);
        disabled = ui.phase !== 'choose' || ui.sel.length >= 2 || !validSet(s, ME, names.concat([it.name]));
      }
    } else {
      const myTurn = s.turn === ME;
      cost = myTurn ? seqCost(p, [it.name]) : CARDS[it.name].cost;
      disabled = ui.phase !== 'mine' || !canPlay(s, it.name);
    }
    out.push(cardHTML(it.name, it.attrs, { cost, disabled, selected, order: ord, basic: it.basic }));
  }
  return out.join('');
}

function controlsHTML() {
  const s = ui.s;
  if (ui.phase === 'over') {
    const w = s.winner === 'draw' ? 'Draw.' : s.winner === ME ? 'You win.' : 'He wins.';
    return `<span class="result ${s.winner === ME ? 'me' : s.winner === BOT ? 'opp' : ''}">${w}</span><button id="rematch" class="primary">Rematch</button><button id="newmatch2">New match</button>`;
  }
  if (s.version === 'hidden') {
    if (ui.phase === 'resolving') return `<span class="hint">Resolving… tap anywhere to skip</span>`;
    if (ui.phase === 'thinking') return `<span class="hint">He is choosing…</span>`;
    const names = selNames();
    const cost = seqCost(s.p[ME], names, false);
    return `<button id="clear"${names.length ? '' : ' disabled'}>Clear</button><button id="commit" class="primary">Commit ${names.length ? `${names.length} action${names.length > 1 ? 's' : ''} · ${cost} mana` : 'nothing'}</button>`;
  }
  if (ui.phase === 'bot') return `<span class="hint">His turn…</span>`;
  const left = 2 - s.p[ME].actions;
  return `<span class="hint">${left} action${left === 1 ? '' : 's'} left</span><button id="endturn" class="primary${left === 0 ? ' pulse' : ''}">End turn</button>`;
}

function deckTable(side) {
  const s = ui.s, p = s.p[side], mine = side === ME;
  const rows = deckSummary(s, side).map(r => {
    const c = CARDS[r.name];
    return mine
      ? `<tr><td>${r.name}</td><td>${c.cost}</td><td>${c.speed}</td><td>${r.total}</td><td>${r.played}</td><td>${r.inHand}</td><td>${r.inDeck}</td></tr>`
      : `<tr><td>${r.name}</td><td>${c.cost}</td><td>${c.speed}</td><td>${r.total}</td><td>${r.played}</td><td>${r.known}</td><td><b>${r.unseen}</b></td></tr>`;
  }).join('');
  const head = mine ? '<th>Card</th><th>Cost</th><th>Speed</th><th>List</th><th>Played</th><th>Hand</th><th>Deck</th>'
    : '<th>Card</th><th>Cost</th><th>Speed</th><th>List</th><th>Played</th><th>Known in hand</th><th>Unseen</th>';
  const passive = HEROES[p.hero].passive.replace(/his /, mine ? 'your ' : 'his ');
  return `<h3 class="${mine ? 'me' : 'opp'}">${mine ? 'Your' : 'His'} list: ${p.hero}</h3><p class="passive">${esc(passive)}</p>
    <table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}

function render() {
  document.body.dataset.screen = ui.phase === 'start' ? 'start' : 'game';
  if (ui.phase === 'start') { renderStart(); return; }
  const s = ui.s;
  $('title').textContent = `${s.version === 'hidden' ? 'Hidden' : 'Open'} · ${s.p[ME].hero} vs ${s.p[BOT].hero}`;
  $('opp').innerHTML = heroHTML(BOT);
  $('me').innerHTML = heroHTML(ME);
  $('arena').innerHTML = arenaHTML();
  $('hand').innerHTML = handHTML();
  $('ctrl').innerHTML = controlsHTML();
  $('decks').innerHTML = `<button id="closedecks" class="closer">Close</button>` + deckTable(BOT) + deckTable(ME);
  $('decks').classList.toggle('open', ui.showDecks);
  const log = $('log');
  if (log.childElementCount > ui.log.length) log.innerHTML = '';
  for (let i = log.childElementCount; i < ui.log.length; i++) {
    const f = ui.log[i], d = document.createElement('div');
    d.className = 'll' + (f.sep ? ' sep' : '') + (f.cls ? ' ' + f.cls : '');
    d.textContent = lineText(f);
    log.appendChild(d);
  }
  log.scrollTop = log.scrollHeight;
}

function renderStart() {
  const c = ui.cfg;
  const seg = (key, opts) => opts.map(([v, label]) => `<button data-cfg="${key}" data-v="${v}" class="${c[key] === v ? 'on' : ''}">${label}</button>`).join('');
  $('start').innerHTML = `<h1>Duel</h1>
    <div class="grp"><div class="lbl">Version</div><div class="seg">${seg('version', [['hidden', 'Hidden'], ['open', 'Open']])}</div></div>
    <div class="grp"><div class="lbl">Your hero</div><div class="seg">${seg('me', [['Heavy', 'Heavy'], ['Quick', 'Quick']])}</div></div>
    <div class="grp"><div class="lbl">His hero</div><div class="seg">${seg('opp', [['Heavy', 'Heavy'], ['Quick', 'Quick']])}</div></div>
    <p class="heroes">Heavy: ${HEROES.Heavy.hp} health, ${HEROES.Heavy.regen} mana a turn. ${esc(HEROES.Heavy.passive.replace('his', 'your'))}<br>Quick: ${HEROES.Quick.hp} health, ${HEROES.Quick.regen} mana a turn. ${esc(HEROES.Quick.passive.replace('his', 'your'))}</p>
    <button id="go" class="primary big">Start</button>`;
}

// ------------------------------------------------------------------ input
function onClick(e) {
  const t = e.target.closest('button');
  if (ui.phase === 'resolving' && !(t && (t.id === 'newmatch' || t.id === 'showdecks' || t.id === 'closedecks'))) { skipHidden(); return; }
  if (!t || t.disabled) return;
  if (t.dataset.cfg) { ui.cfg[t.dataset.cfg] = t.dataset.v; render(); return; }
  switch (t.id) {
    case 'go': case 'rematch': startMatch(); return;
    case 'newmatch': case 'newmatch2': clearTimers(); ui.phase = 'start'; ui.showDecks = false; render(); return;
    case 'showdecks': ui.showDecks = !ui.showDecks; render(); return;
    case 'closedecks': ui.showDecks = false; render(); return;
    case 'commit': commit(); return;
    case 'clear': ui.sel = []; render(); return;
    case 'endturn': endMyTurn(); return;
  }
  const item = t.dataset.h !== undefined ? Number(t.dataset.h) : t.dataset.b;
  if (item === undefined) return;
  if (ui.s.version === 'hidden') toggle(item);
  else playOpen(typeof item === 'number' ? ui.s.p[ME].hand[item] : item);
}

document.addEventListener('click', onClick);
render();
