// Exert to score as a game screen against Expert. Every action, the bot's included, goes through
// legalActions/act and is animated from the events it emits; the bot plays one action at a time.

import { CARDS, MAX_MANA, TARGET, newMatch, act, legalActions, canAct } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-03-tally';
const expert = expertBot({ iters: 10000 });
const ui = { s: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'Unit') art = `<span class="sc">${c.sc}</span><span class="stat a">${c.str}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'Hit') { art = `<span class="big">${c.dmg}</span>`; tx = `<div class="tx">${c.dmg} damage to any unit.</div>`; }
  else if (c.kind === 'Draw') { art = `<span class="big">+2</span>`; tx = `<div class="tx">Draw 2 cards.</div>`; }
  else { art = `<span class="big">+1</span>`; tx = `<div class="tx">1 mana this turn.</div>`; }
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.s.turn === ME;
const legal = () => myTurn() ? legalActions(ui.s) : [];
function targetsNow() {
  const out = { score: false, units: new Set() };
  if (!ui.sel) return out;
  for (const a of legal()) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.target) out.units.add(a.target.side + ':' + a.target.i);
    if (ui.sel.kind === 'unit' && a.t === 'score' && a.i === ui.sel.i) out.score = true;
    if (ui.sel.kind === 'unit' && a.t === 'chal' && a.i === ui.sel.i) out.units.add(BOT + ':' + a.j);
  }
  return out;
}

// ------------------------------------------------------------------ rendering
function ptsHTML(side, T) {
  const p = ui.s.p[side];
  let pips = '';
  for (let i = 0; i < TARGET; i++) pips += `<i class="${i < p.pts ? 'on' : ''}"></i>`;
  const tgt = side === ME && T.score ? ' tgt' : '';
  return `<div class="pts s${side}${tgt} ${ui.fx['pts' + side] || ''}" id="pts${side}" data-pts="${side}"><b>${p.pts}</b><span class="pips">${pips}</span></div>`;
}
function boardHTML(side, T) {
  return ui.s.p[side].board.map((m, i) => {
    let cls = m.ex ? ' ex' : '';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && myTurn() && canAct(m)) cls += ' can';
    if (T.units.has(side + ':' + i)) cls += ' tgt';
    if (m.fresh) cls += ' sleep';
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="slot${m.ex ? ' ex' : ''}"><div class="unit s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}"><span class="sc">${m.sc}</span><span class="stat a">${m.str}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div></div>`;
  }).join('');
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME], L = legal();
  const R = { Coin: 0, Unit: 1, Hit: 2, Draw: 3 };
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost; });
  return order.map(i => {
    const id = p.hand[i], ok = L.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) {
  return `<div class="hist s${h.side}">${h.chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
}
function render() {
  const s = ui.s, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('pts' + side + 'row').innerHTML = ptsHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, L = legal(), more = L.some(a => a.t !== 'end' && !(a.target && a.target.side === ME));
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !more ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit, .pts').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(800);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .8}px, ${dy * .8}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 440, easing: 'ease-in-out' }).finished;
}
async function pulse(el) { if (el) await el.animate([{ transform: 'translateY(0)' }, { transform: 'translateY(-14px) scale(1.06)' }, { transform: 'translateY(0)' }], { duration: 380, easing: 'ease-out' }).finished; }
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play'), chalE = ev.find(e => e.t === 'chal'), scoreE = ev.find(e => e.t === 'score');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind !== 'Unit')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (chalE) await lunge($('m' + chalE.uid), $('m' + chalE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (scoreE) await pulse($('m' + scoreE.uid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  let drawn = 0;
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'score') ui.fx['pts' + e.side] = 'bump';
    if (e.t === 'dry') ui.fx['pts' + (1 - e.side)] = 'bump';
    if (e.t === 'draw' && e.side === ME) drawn++;
  }
  ui.fresh = drawn;
  ui.s = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['m' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'score') { const p = before['m' + e.uid]; if (p) floatAt(p.c, '+' + e.n, 'gain'); }
    if (e.t === 'dry') { const p = before['pts' + (1 - e.side)]; if (p) floatAt(p.c, '+' + e.n, 'gain'); }
  }
  // history
  if (playE) {
    const c = CARDS[playE.card], died = ev.some(e => e.t === 'die');
    const chip = c.kind === 'Unit' ? `<span class="chip Unit s${playE.side}">${c.str}/${c.hp}</span>` : `<span class="chip ${c.kind}">${c.kind === 'Hit' ? c.dmg : c.kind === 'Draw' ? '+2' : '+1'}</span>`;
    ui.hist.push({ side: playE.side, chip, out: c.kind === 'Hit' ? (died ? '✕' : '−' + c.dmg) : '', cls: died ? 'kill' : 'dmg' });
  }
  if (chalE) {
    const m = prev.p[chalE.side].board.find(x => x.uid === chalE.uid), kill = ev.some(e => e.t === 'die' && e.uid === chalE.tuid);
    ui.hist.push({ side: chalE.side, chip: `<span class="chip Atk s${chalE.side}">${m.str}</span>`, out: kill ? '✕' : '−' + m.str, cls: kill ? 'kill' : 'dmg' });
  }
  if (scoreE) ui.hist.push({ side: scoreE.side, chip: `<span class="chip Score">+${scoreE.n}</span>`, out: '', cls: '' });
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 500 : 250);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (next.winner !== null) finish();
  render();
}

function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botTurn(tok); else { ui.busy = false; render(); }
}
async function botTurn(tok) {
  ui.busy = true; render();
  await wait(400);
  while (tok === ui.token && !ui.over && ui.s.turn === BOT) {
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token) return;
    await wait(a.t === 'end' ? 350 : 300);
    await apply(a);
  }
  if (tok !== ui.token) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  if (!ui.over && ui.s.turn === BOT) return botTurn(tok);
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { $('rulesbox').classList.toggle('show'); return; }
  if (e.target.closest('#rulesbox')) { $('rulesbox').classList.remove('show'); return; }
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (!myTurn()) return;
  const pts = e.target.closest('.pts');
  if (pts && pts.classList.contains('tgt') && ui.sel && ui.sel.kind === 'unit') return doAct({ t: 'score', i: ui.sel.i });
  const u = e.target.closest('.unit');
  if (u) {
    const side = +u.dataset.side, i = +u.dataset.i;
    if (ui.sel && u.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, target: { side, i } });
      return doAct({ t: 'chal', i: ui.sel.i, j: i });
    }
    if (side === ME && canAct(ui.s.p[ME].board[i])) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i ? null : { kind: 'unit', i }; render(); return; }
  }
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = ui.s.p[ME].hand[i], c = CARDS[id];
    if (c.kind === 'Hit') { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b0 && !b0.disabled && b0.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rulesbox').classList.remove('show'); render(); } });
startMatch();
