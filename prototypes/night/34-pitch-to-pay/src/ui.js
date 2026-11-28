// 34 Pitch to pay as a game screen against Expert. Each action is animated from the state
// before and the state after; the win tally is kept in this browser and decides who goes first.

import { CARDS, BOARD, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-34-tally';
const expert = expertBot({ ...EXPERT, playouts: 1500, timeMs: 1200 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'unit' ? `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>` : `<span class="big">${c.dmg}</span>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><span class="pgem">${c.pitch}</span><div class="art">${art}</div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function targetsNow() {
  const out = { heroes: new Set(), units: new Set(), pool: false, board: false };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.card === ui.sel.id) {
      if (a.t === 'pitch') out.pool = true;
      else if (a.t === 'play' && !a.tgt) out.board = true;
      else if (a.t === 'play') { if (a.tgt.i < 0) out.heroes.add(a.tgt.side); else out.units.add(a.tgt.side + ':' + a.tgt.i); }
    }
    if (ui.sel.kind === 'unit' && a.t === 'attack' && a.from === ui.sel.i) { if (a.to < 0) out.heroes.add(BOT); else out.units.add(BOT + ':' + a.to); }
  }
  return out;
}
const canAttack = (i) => myTurn() && legalActions(ui.view).some(a => a.t === 'attack' && a.from === i);

// ------------------------------------------------------------------ rendering
function heroHTML(side, T) {
  const p = ui.view.p[side];
  return `<div class="hero s${side}${T.heroes.has(side) ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-i="-1"><span class="hp">${p.life}</span></div>`;
}
function boardHTML(side, T) {
  return ui.view.p[side].board.map((u, i) => {
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(i)) cls += ' can';
    if (T.units.has(side + ':' + i)) cls += ' tgt';
    if (side === ui.view.toAct && !u.ready) cls += ' sleep';
    if (ui.fx['u' + u.uid]) cls += ' ' + ui.fx['u' + u.uid];
    return `<div class="unit s${side}${cls}" id="u${u.uid}" data-side="${side}" data-i="${i}"><span class="stat a">${u.atk}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span></div>`;
  }).join('');
}
function resHTML(side, T) {
  const p = ui.view.p[side], live = ui.view.toAct === side;
  const pool = `<div class="pool s${side}${side === ME && T.pool ? ' tgt' : ''}${live && p.pool ? ' on' : ''} ${ui.fx['pool' + side] || ''}" id="pool${side}" data-pool="${side}">${live ? p.pool : 0}</div>`;
  return `${pool}<div class="piles"><div class="pile s${side}" id="deck${side}">${p.deck.length}</div><div class="pile disc s${side}">${p.disc.length}</div></div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const order = p.hand.map((_, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]];
    return (A.kind === B.kind ? 0 : A.kind === 'unit' ? -1 : 1) || A.cost - B.cost;
  });
  return order.map(i => {
    const id = p.hand[i], playable = legal.some(a => a.t === 'play' && a.card === id), ok = myTurn();
    let cls = ok ? (playable ? 'ok' : 'pay') : '';
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fx['h' + i]) cls += ' ' + ui.fx['h' + i];
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) {
  const chip = h.kind === 'attack' ? `<span class="chip attack s${h.side}">${h.atk}</span>`
    : h.kind === 'pitch' ? `<span class="chip pitch">+${CARDS[h.card].pitch}</span>`
    : h.kind === 'unit' ? `<span class="chip unit s${h.side}">${CARDS[h.card].atk}/${CARDS[h.card].hp}</span>`
    : `<span class="chip spell">${CARDS[h.card].dmg}</span>`;
  return `<div class="hist s${h.side}">${chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
}
function render() {
  const s = ui.view, T = targetsNow();
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side, T); }
  $('board0').classList.toggle('tgt', T.board);
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.toAct === ME;
  $('turnbox').innerHTML = `<button id="endturn"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit, .hero, .pool').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side, pitch) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side, { cls: pitch ? 'pitched' : '' });
  await wait(pitch ? 520 : 700);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .8}px, ${dy * .8}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out' }).finished;
}
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
  ui.s = next;
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack'), pitE = ev.find(e => e.t === 'pitch');
  if (pitE && pitE.side === BOT) await spotlight(pitE.card, BOT, true);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'spell')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('u' + atkE.uid), atkE.to < 0 ? $('hero' + (1 - atkE.side) + 'x') : $('u' + atkE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['u' + e.uid] = 'new';
    if (e.t === 'hit' && e.i >= 0 && e.hp > 0) ui.fx['u' + e.uid] = 'shake';
    if (e.t === 'hit' && e.i < 0) ui.fx['hero' + e.side] = 'shake';
    if (e.t === 'bleed') ui.fx['hero' + e.side] = 'shake';
    if (e.t === 'pitch') ui.fx['pool' + e.side] = 'bump';
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const id = e.i < 0 ? 'hero' + e.side + 'x' : 'u' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'bleed') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
    if (e.t === 'pitch') { const p = before['pool' + e.side]; if (p) floatAt(p.c, '+' + CARDS[e.card].pitch, 'gain'); }
  }
  if (playE) {
    const c = CARDS[playE.card], hits = ev.filter(e => e.t === 'hit'), died = ev.some(e => e.t === 'die');
    const out = c.kind === 'spell' ? (died ? '✕' : hits[0] && hits[0].i < 0 ? '−' + c.dmg + ' life' : '−' + c.dmg) : '';
    ui.hist.push({ side: playE.side, kind: c.kind, card: playE.card, out, cls: died ? 'kill' : hits[0] && hits[0].i < 0 ? 'face' : 'dmg' });
  }
  if (pitE) ui.hist.push({ side: pitE.side, kind: 'pitch', card: pitE.card, out: '', cls: '' });
  if (atkE) {
    const died = ev.filter(e => e.t === 'die' && e.side !== atkE.side).length;
    ui.hist.push({ side: atkE.side, kind: 'attack', atk: atkE.atk, out: atkE.to < 0 ? '−' + atkE.atk + ' life' : died ? '✕' : '−' + atkE.atk, cls: atkE.to < 0 ? 'face' : died ? 'kill' : 'dmg' });
  }
  if (ev.some(e => e.t === 'turn')) await wait(next.toAct === ME ? 600 : 250);
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
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.toAct === BOT) await botTurn(tok); else { ui.busy = false; render(); }
}
async function botTurn(tok) {
  ui.busy = true; render();
  await wait(300);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.toAct !== BOT) break;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 300 : 200);
    if (tok !== ui.token) return;
    await apply(a);
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  if (!ui.over && ui.s.toAct === BOT) return botTurn(tok);
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (!myTurn()) return;
  const T = targetsNow();
  const tgt = e.target.closest('.unit, .hero');
  if (tgt) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, tgt: { side, i } });
      return doAct({ t: 'attack', from: ui.sel.i, to: i });
    }
    if (side === ME && i >= 0 && canAttack(i)) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i ? null : { kind: 'unit', i }; render(); return; }
  }
  if (ui.sel && ui.sel.kind === 'card') {
    if (e.target.closest('.pool') && T.pool) return doAct({ t: 'pitch', card: ui.sel.id });
    if (e.target.closest('#board0') && T.board) return doAct({ t: 'play', card: ui.sel.id });
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i];
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled && b.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
// for the headless check: the state and the action entry the clicks use
window.__game = { get s() { return ui.s; }, get busy() { return ui.busy; }, get over() { return ui.over; }, doAct, legalActions: () => legalActions(ui.s) };
startMatch();
