// Supply grid as a game screen against the Expert. Your Base is drawn at the bottom. The bot's
// turn plays out one action at a time; the win tally is kept in this browser and decides who goes
// first (alternating).

import { CARDS, N, MAX_MANA, ROUNDS, newMatch, act, legalActions } from './engine.js';
import { makeRng, mcExpert, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-19-supply-grid-tally';
const expert = mcExpert({ ...EXPERT, timeMs: 900, minPlayouts: 300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, fresh: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

// my Base at the bottom: screen row = 4 - engine row
const toScreen = (i) => (N - 1 - Math.floor(i / N)) * N + (i % N);

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'Unit' ? `<span class="big">${c.power}</span>` : c.kind === 'Spell' ? `<span class="big sm">≤${c.max}</span>` : `<span class="big">+1</span>`;
  return `<button class="card ${c.kind}${c.wall ? ' Wall' : ''} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div></button>`;
}

const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
function targetsNow() {
  const out = new Set();
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'place' && a.card === ui.sel.id) out.add(a.cell);
    if (ui.sel.kind === 'card' && a.t === 'cut' && ui.sel.id === 'CUT') out.add(a.to);
    if (ui.sel.kind === 'piece' && a.t === 'strike' && a.from === ui.sel.cell) out.add(a.to);
  }
  return out;
}
const canStrike = (cell) => myTurn() && legalActions(ui.view).some(a => a.t === 'strike' && a.from === cell);

function gridHTML(T) {
  const s = ui.view, cells = Array(N * N);
  for (let i = 0; i < N * N; i++) {
    const x = s.cells[i];
    let cls = 'cell' + (T.has(i) ? ' tgt' : '');
    let inner = '';
    if (x) {
      let pc = `piece s${x.side}${x.base ? ' base' : ''}${x.wall ? ' wall' : ''}`;
      if (x.side === s.turn && (x.struck || x.wall) && !x.base) pc += ' spent';
      if (x.side === s.turn && x.base && x.struck) pc += ' spent';
      if (x.side === ME && ui.sel && ui.sel.kind === 'piece' && ui.sel.cell === i) pc += ' sel';
      else if (x.side === ME && !ui.sel && canStrike(i)) pc += ' can';
      if (ui.fx['p' + x.uid]) pc += ' ' + ui.fx['p' + x.uid];
      inner = `<div class="${pc}" id="p${x.uid}">${x.power}</div>`;
    }
    cells[toScreen(i)] = `<div class="${cls}" data-cell="${i}" id="c${i}">${inner}</div>`;
  }
  return cells.join('');
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { Coin: 0, Unit: 1, Spell: 2 };
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost || (A.wall ? 1 : 0) - (B.wall ? 1 : 0); });
  return order.map(i => {
    const id = p.hand[i], c = CARDS[id];
    const ok = legal.some(a => (a.t === 'place' && a.card === id) || (a.t === 'cut' && id === 'CUT') || (a.t === 'coin' && id === 'COIN'));
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function roundsHTML() {
  const r = Math.ceil(ui.view.turnNo / 2);
  let h = '';
  for (let i = 1; i <= ROUNDS; i++) h += `<i class="${i < r ? 'done' : i === r ? 'now' : ''}"></i>`;
  return h;
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('grid').innerHTML = gridHTML(T);
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('rounds').innerHTML = roundsHTML();
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, left = mine && !ui.busy && legalActions(s).some(a => a.t !== 'end');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !left ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {}; ui.fresh = 0;
}

function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function ghost(el, cls = 'ghost') {
  if (!el) return;
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), d = document.createElement('div');
  d.className = cls; d.innerHTML = el.outerHTML; d.style.left = (r.left - g.left) + 'px'; d.style.top = (r.top - g.top) + 'px'; d.style.width = r.width + 'px'; d.style.height = r.height + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 600);
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .6}px, ${dy * .6}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 380, easing: 'ease-in-out' }).finished;
}
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('grid').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(600);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const pl = ev.find(e => e.t === 'place'), st = ev.find(e => e.t === 'strike'), cu = ev.find(e => e.t === 'cut'), co = ev.find(e => e.t === 'coin');
  if ((pl && pl.side === BOT) || cu || (co && co.side === BOT)) await spotlight(pl ? pl.card : cu ? 'CUT' : 'COIN', (pl || cu || co).side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (st) await lunge($('p' + st.uid), $('p' + st.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  for (const e of ev) {
    if (e.t === 'die') ghost($('p' + e.uid));
    if (e.t === 'cutoff') ghost($('p' + e.uid), 'ghost cutoff');
    if (e.t === 'place') ui.fx['p' + e.uid] = 'new';
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.view = next; render();
  const lost = (side) => ev.filter(e => (e.t === 'die' || e.t === 'cutoff') && e.side === side).length;
  if (pl) ui.hist.push({ side: pl.side, kind: 'Place', chip: CARDS[pl.card].power, out: '' });
  if (st) { const k = lost(1 - st.side), l = lost(st.side); ui.hist.push({ side: st.side, kind: 'Strike', chip: `${st.p1}›${st.p2}`, out: (k ? '✕' + (k > 1 ? k : '') : '') + (l ? ' −' + l : ''), cls: 'kill' }); }
  if (cu) { const k = lost(1 - cu.side); ui.hist.push({ side: cu.side, kind: 'Spell', chip: '≤2', out: '✕' + (k > 1 ? k : ''), cls: 'kill' }); }
  if (co) ui.hist.push({ side: co.side, kind: 'Coin', chip: '+1', out: '' });
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 500 : 250);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (next.winner !== null) finish(ev.find(e => e.t === 'end'));
  render();
}
function finish(e) {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  const sub = e && e.by === 'count' ? `<p class="sub">${e.counts[ME]} – ${e.counts[BOT]}</p>` : '';
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2>${sub}<button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(300);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) return;
    const a = expert(ui.s, ui.rng);
    await wait(250);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
    if (a.t === 'end') break;
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) { if (!myTurn()) return; ui.busy = true; ui.sel = null; await apply(a); ui.busy = false; render(); }
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply({ t: 'end' });
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { if (e.target.closest('#closerules')) $('rules').classList.remove('show'); return; }
  const cellEl = e.target.closest('.cell');
  if (cellEl && myTurn()) {
    const i = +cellEl.dataset.cell, x = ui.view.cells[i];
    if (ui.sel && cellEl.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct(ui.sel.id === 'CUT' ? { t: 'cut', to: i } : { t: 'place', card: ui.sel.id, cell: i });
      return doAct({ t: 'strike', from: ui.sel.cell, to: i });
    }
    if (x && x.side === ME && canStrike(i)) { ui.sel = ui.sel && ui.sel.kind === 'piece' && ui.sel.cell === i ? null : { kind: 'piece', cell: i }; render(); return; }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i];
    if (id === 'COIN') return doAct({ t: 'coin' });
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled) {
    if (b.id === 'rematch' || b.id === 'newmatch') return startMatch();
    if (b.id === 'endturn') return myEndTurn();
    if (b.id === 'openrules') { $('rules').classList.add('show'); return; }
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('rules').classList.remove('show'); if (ui.sel) { ui.sel = null; render(); } } });
startMatch();
