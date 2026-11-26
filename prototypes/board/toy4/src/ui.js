// Board Toy 1 as a game screen. Drives the engine through its transitions; each
// play or turn change is animated from the state before and the state after.

import { CARDS, TILES, POS, GOAL, MAX_MANA, REGIONS, FULL_HAND, setFullHand, newMatch, playAction, endTurn, canPlay, targets, heldRegions } from './engine.js';
import { makeRng, botTurn } from './bot.js';

const ME = 0, BOT = 1;
const ui = { s: null, view: null, busy: false, over: false, sel: null, food: [0, 0], hist: [], fresh: new Set(), fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));


function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}>
    <span class="cgem">${c.cost}</span>
    <div class="art"><span class="big">${c.n}</span></div>
    <div class="nm">${c.kind}</div>
    ${c.kind === 'Strike' ? `<div class="tx">Deal ${c.n} damage to an enemy unit.</div>` : ''}
  </button>`;
}

// ------------------------------------------------------------------ rendering
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  const food = `<div class="food s${side}${!ui.over && ui.view.turn === side ? ' active' : ''}${ui.fx['food' + side] ? ' bump' : ''}" id="food${side}"><b>${ui.food[side]}</b><small>/${GOAL}</small></div>`;
  return `${food}<div class="stack"><div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div>${FULL_HAND ? '' : `<div class="pile s${side}">${p.deck.length}</div>`}</div>`;
}
function histHTML(h) {
  const chip = h.food ? `<span class="chip coin"></span>` : `<span class="chip ${CARDS[h.card].kind} s${h.side}">${CARDS[h.card].n}</span>`;
  return `<div class="hist s${h.side}">${chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
}

// tile and marker places, in percent of the board: four tile widths across, the hex 1.1547 times as tall as wide
const TW = 25, ROWSTEP = 18.75;
const tileBox = (i) => ({ left: (POS[i].x + 1.5) * TW, top: POS[i].r * ROWSTEP });
const markAt = (rg) => {
  const cs = rg.map(i => { const b = tileBox(i); return { x: b.left + TW / 2, y: b.top + TW / 2 }; });
  return { x: cs.reduce((a, c) => a + c.x, 0) / 3, y: cs.reduce((a, c) => a + c.y, 0) / 3 };
};

function boardHTML() {
  const s = ui.view, myTurn = !ui.busy && !ui.over && s.turn === ME;
  const live = ui.sel && myTurn ? new Set(targets(s, ui.sel)) : new Set();
  const kind = ui.sel && CARDS[ui.sel].kind;
  const win = {};
  for (const side of [0, 1]) for (const k of heldRegions(s, side)) win[k] = side;
  let h = '';
  for (let i = 0; i < TILES; i++) {
    const u = s.board[i], t = live.has(i), b = tileBox(i);
    const cls = t ? (kind === 'Unit' ? ' can' : ' aim') : '';
    let inner = '';
    if (u) inner = `<div class="unit s${u.side} ${ui.fx['t' + i] || ''}" id="u${i}"><span class="hp${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span></div>`;
    else if (ui.fx['dead' + i]) inner = `<div class="unit s${ui.fx['dead' + i].side} dying" id="u${i}"><span class="hp hurt">0</span></div>`;
    h += `<div class="tile${cls}" id="tile${i}" data-tile="${i}" style="left:${b.left}%;top:${b.top}%">${inner}</div>`;
  }
  REGIONS.forEach((rg, k) => {
    const m = markAt(rg);
    h += `<div class="mark${win[k] === undefined ? '' : ' m' + win[k]}${ui.fx['m' + k] ? ' pop' : ''}" id="mark${k}" style="left:${m.x}%;top:${m.y}%"></div>`;
  });
  return h;
}

function handHTML() {
  const s = ui.view, p = s.p[ME];
  const counts = {};
  for (const id of p.hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts).sort((a, b) => {
    const A = CARDS[a], B = CARDS[b];
    return (A.kind === B.kind ? 0 : A.kind === 'Unit' ? -1 : 1) || A.cost - B.cost;
  });
  const myTurn = !ui.busy && !ui.over && s.turn === ME;
  const newest = p.hand[p.hand.length - 1];
  return ids.map(id => {
    const ok = myTurn && canPlay(s, id);
    let cls = ok ? 'ok' : (myTurn ? 'no' : '');
    if (ok && ui.sel === id) cls += ' sel';
    if (ui.fresh.size && id === newest) cls += ' drawn';
    if (counts[id] > 1) cls += ' copies';
    const n = counts[id] > 1 ? `<span class="count">${counts[id]}</span>` : '';
    return cardHTML(id, ME, { cls, attrs: `data-card="${id}"${ok ? '' : ' disabled'}` }).replace('</button>', n + '</button>');
  }).join('');
}

function render() {
  const s = ui.view;
  const own = REGIONS.map((_, k) => heldRegions(s, 0).includes(k) ? 0 : heldRegions(s, 1).includes(k) ? 1 : -1);
  if (ui.own) own.forEach((o, k) => { if (o !== ui.own[k] && o >= 0) ui.fx['m' + k] = 1; });
  ui.own = own;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) {
    $('res' + side).innerHTML = resHTML(side);
  }
  $('board').innerHTML = boardHTML();
  $('hand').innerHTML = handHTML();
  const myTurn = !ui.over && s.turn === ME;
  const canAct = myTurn && !ui.busy && s.p[ME].hand.some(id => canPlay(s, id));
  $('turnbox').innerHTML = `<button id="endturn" class="${myTurn && !canAct ? 'done' : ''}"${myTurn && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.filter(h => !h.sep).slice(-14).map(histHTML).join('');
  ui.fresh.clear(); ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) {
  const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 };
}
function floater(el, text, cls, dy = 0) {
  if (!el) return;
  const c = centerOf(el), f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text;
  f.style.left = c.x + 'px'; f.style.top = (c.y + dy) + 'px';
  $('game').appendChild(f);
  setTimeout(() => f.remove(), 1200);
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(card, side) {
  const t = centerOf($('board'));
  $('spot').style.left = t.x + 'px'; $('spot').style.top = t.y + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(750);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180);
  $('spot').innerHTML = '';
}

// ------------------------------------------------------------------ playback
async function apply(fn) {
  const prev = ui.s, ev = [];
  const next = fn(prev, ev);
  ui.s = next;
  for (const e of ev) {
    if (e.t === 'turn') {
      ui.view = next; ui.sel = null;
      ui.hist.push({ sep: 1, side: e.side });
      render();
      if (e.side === ME) { banner('Your turn'); await wait(650); } else await wait(300);
    } else if (e.t === 'food') {
      for (const k of e.regions) for (const i of REGIONS[k]) if (prev.board[i] && prev.board[i].side === e.side) ui.fx['t' + i] = 'scored';
      ui.food[e.side] = e.food; ui.fx['food' + e.side] = 1;
      render();
      for (const k of e.regions) floater($('mark' + k), '+1', 'gain', -20);
      floater($('food' + e.side), '+' + e.n, 'gainbig', -46);
      ui.hist.push({ side: e.side, food: 1, out: '+' + e.n, cls: 'gain' });
      await wait(750);
    } else if (e.t === 'play') {
      if (e.side === BOT || CARDS[e.card].kind === 'Strike') await spotlight(e.card, e.side);
    } else if (e.t === 'place') {
      ui.view = next; ui.fx['t' + e.tile] = 'new';
      ui.hist.push({ side: e.side, card: ev.find(x => x.t === 'play').card });
      render();
    } else if (e.t === 'hit') {
      const died = ev.some(x => x.t === 'die');
      ui.view = next;
      if (died) ui.fx['dead' + e.tile] = { side: e.side };
      else ui.fx['t' + e.tile] = 'shake';
      ui.hist.push({ side: 1 - e.side, card: ev.find(x => x.t === 'play').card, out: died ? '✕' : '−' + e.dmg, cls: died ? 'kill' : 'dmg' });
      render();
      floater($('tile' + e.tile), '−' + e.dmg, 'dmg');
      await wait(died ? 450 : 250);
      if (died) render();
    } else if (e.t === 'start') {
      ui.view = next;
      if (e.drew && e.side === ME) ui.fresh.add(next.p[ME].hand.length - 1);
      render();
    }
  }
  ui.view = next;
  ui.food = [next.p[0].food, next.p[1].food];
  if (next.winner !== null) finish();
  render();
}

function finish() {
  ui.over = true;
  const w = ui.s.winner;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null; ui.food = [0, 0];
  $('over').classList.remove('show');
  ui.busy = true; render();
  ui.hist.push({ sep: 1, side: ui.s.first });
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok);
  else { ui.busy = false; render(); }
}

async function botMove(tok) {
  ui.busy = true; render();
  await wait(450);
  const moves = botTurn(ui.s, ui.rng);
  for (const m of moves) {
    if (tok !== ui.token || ui.over) return;
    await wait(200);
    await apply((s, ev) => playAction(s, m.card, m.tile, ev));
  }
  if (tok !== ui.token || ui.over) return;
  await wait(350);
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}

async function myPlay(card, tile) {
  if (ui.busy || ui.over || ui.s.turn !== ME || !canPlay(ui.s, card, tile)) return;
  ui.busy = true; ui.sel = null;
  await apply((s, ev) => playAction(s, card, tile, ev));
  ui.busy = false; render();
}

async function myEndTurn() {
  if (ui.busy || ui.over || ui.s.turn !== ME) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const tile = e.target.closest('.tile');
  if (tile && ui.sel) { myPlay(ui.sel, +tile.dataset.tile); return; }
  const t = e.target.closest('button');
  if (!t || t.disabled) { if (ui.sel) { ui.sel = null; render(); } return; }
  if (t.dataset.card) { ui.sel = ui.sel === t.dataset.card ? null : t.dataset.card; render(); return; }
  switch (t.id) {
    case 'rematch': case 'newmatch': startMatch(); return;
    case 'endturn': myEndTurn(); return;
  }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.sel) { ui.sel = null; render(); } });
/*BOOT*/
startMatch();
