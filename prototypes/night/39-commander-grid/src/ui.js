// 39 Commander grid as a game screen against the Expert. Each action is animated from the state
// before and the state after; the win tally is kept in this browser and decides who goes first.

import { CARDS, COLS, ROWS, MAX_MANA, newMatch, act, legalActions, pieceById, round, BLEED_FROM } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-39-tally';
const expert = expertBot({ ...EXPERT, playouts: 1600, timeMs: 1300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const TXT = { LIN: 'Moves up to 2', LAN: 'Hits 2 away in a line', H3: 'Within 2 of your Commander', RAL: 'A piece acts again', COIN: '+1 mana this turn' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art;
  if (c.kind === 'unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'hit') art = `<span class="big">${c.dmg}</span>`;
  else if (c.kind === 'rally') art = `<span class="big">↻</span>`;
  else art = `<span class="big">+1</span>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${TXT[id] ? `<div class="tx">${TXT[id]}</div>` : ''}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
// for the selection: cells to move or deploy to, pieces to attack or target
function targetsNow() {
  const out = { cells: new Set(), pieces: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id) { if (a.cell !== undefined) out.cells.add(a.cell); if (a.tgt) out.pieces.add(a.tgt); }
    if (ui.sel.kind === 'piece' && a.from === ui.sel.uid) { if (a.t === 'move') out.cells.add(a.to); if (a.t === 'attack') out.pieces.add(a.to); }
  }
  return out;
}
const canActNow = (uid) => myTurn() && legalActions(ui.view).some(a => (a.t === 'move' || a.t === 'attack') && a.from === uid);

// ------------------------------------------------------------------ rendering
// my side (0) at the bottom: row 0 is drawn last
function boardHTML(T) {
  const s = ui.view, at = new Map();
  for (const u of s.pieces) at.set(u.cell, u);
  let h = '';
  for (let r = ROWS - 1; r >= 0; r--) for (let c = 0; c < COLS; c++) {
    const cell = r * COLS + c, u = at.get(cell);
    let inner = '';
    if (u) {
      let cls = '';
      if (u.side === ME && ui.sel && ui.sel.kind === 'piece' && ui.sel.uid === u.uid) cls += ' sel';
      else if (u.side === ME && !ui.sel && canActNow(u.uid)) cls += ' can';
      if (T.pieces.has(u.uid)) cls += ' tgt';
      if (u.side === s.turn && (u.acted || u.fresh || (u.moved && !canActNow(u.uid)))) cls += ' spent';
      if (ui.fx['u' + u.uid]) cls += ' ' + ui.fx['u' + u.uid];
      const cmd = u.card === 'CMD';
      inner = `<div class="pc s${u.side}${cmd ? ' cmd' : ''}${cls}" id="u${u.uid}" data-uid="${u.uid}">${cmd ? '' : `<span class="un">${CARDS[u.card].name}</span>`}<span class="stat a">${u.atk}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span></div>`;
    }
    h += `<div class="cell${T.cells.has(cell) ? ' dest' : ''}" data-cell="${cell}">${inner}</div>`;
  }
  return h;
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { coin: 0, unit: 1, hit: 2, rally: 3 };
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost; });
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
const histHTML = (h) => `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
function render() {
  const s = ui.view, T = targetsNow();
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="cb"></i>'.repeat(s.p[BOT].hand.length);
  $('board').innerHTML = boardHTML(T);
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, canAct = mine && !ui.busy && legalActions(s).some(a => a.t !== 'end');
  const r = round(s), bleed = r >= BLEED_FROM - 1 ? `<div class="bleed">${r >= BLEED_FROM ? '−' + (r - BLEED_FROM + 1) : ''}<small>round ${r}</small></div>` : '';
  $('turnbox').innerHTML = `${bleed}<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.pc').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(700);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl, lance) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  if (lance) {
    const g = $('game').getBoundingClientRect(), d = document.createElement('div');
    d.className = 'shot'; d.style.left = (a.left - g.left + a.width / 2) + 'px'; d.style.top = (a.top - g.top + a.height / 2) + 'px';
    $('game').appendChild(d);
    await d.animate([{ transform: 'translate(-50%,-50%)' }, { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))` }], { duration: 320, easing: 'ease-in' }).finished;
    d.remove(); return;
  }
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .6}px, ${dy * .6}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out' }).finished;
}
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  d.style.width = snap.rect.width + 'px'; d.style.height = snap.rect.height + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack'), mvE = ev.find(e => e.t === 'move');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind !== 'unit')) await spotlight(playE.card, playE.side);
  if (atkE) await lunge($('u' + atkE.uid), $('u' + atkE.to), atkE.lance);
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['u' + e.uid] = 'new';
    if ((e.t === 'hit' || e.t === 'bleed') && e.hp > 0) ui.fx['u' + e.uid] = 'shake';
    if (e.t === 'rally') ui.fx['u' + e.uid] = 'new';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.view = next; render();
  if (mvE) {
    const el = $('u' + mvE.uid), was = before['u' + mvE.uid];
    if (el && was) { const r = el.getBoundingClientRect(); el.style.zIndex = 10; await el.animate([{ transform: `translate(${was.rect.left - r.left}px, ${was.rect.top - r.top}px)` }, { transform: 'translate(0,0)' }], { duration: 300, easing: 'ease-out' }).finished; }
  }
  for (const e of ev) {
    if (e.t === 'hit' || e.t === 'bleed') { const p = before['u' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
  }
  if (playE) {
    const c = CARDS[playE.card], died = ev.some(e => e.t === 'die');
    if (c.kind === 'unit') ui.hist.push({ side: playE.side, kind: 'unit', chip: `${c.atk}/${c.hp}` });
    else if (c.kind === 'hit') ui.hist.push({ side: playE.side, kind: 'hit', chip: c.dmg, out: died ? '✕' : '−' + c.dmg, cls: died ? 'kill' : 'dmg' });
    else if (c.kind === 'rally') ui.hist.push({ side: playE.side, kind: 'rally', chip: '↻' });
    else ui.hist.push({ side: playE.side, kind: 'coin', chip: '+1' });
  }
  if (atkE) {
    const u = pieceById(prev, atkE.uid), d = pieceById(prev, atkE.to), killed = ev.some(e => e.t === 'die' && e.side !== atkE.side);
    ui.hist.push({ side: atkE.side, kind: 'atk', chip: '⚔' + u.atk, out: d.card === 'CMD' ? '−' + u.atk + ' Cmdr' : killed ? '✕' : '−' + u.atk, cls: d.card === 'CMD' ? 'face' : killed ? 'kill' : 'dmg' });
  }
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 600 : 250);
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
  if (ui.s.turn === BOT) await botTurn(tok); else { ui.busy = false; render(); }
}
async function botTurn(tok) {
  ui.busy = true; render();
  await wait(350);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) break;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 300 : 200);
    if (tok !== ui.token) return;
    await apply(a);
    if (a.t === 'end') break;
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  ui.busy = true; ui.sel = null;
  await apply(a);
  ui.busy = false; render();
}
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply({ t: 'end' });
  if (tok !== ui.token || ui.over) return;
  await botTurn(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.add('show'); return; }
  if (e.target.closest('#rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (myTurn()) {
    const pc = e.target.closest('.pc'), cellEl = e.target.closest('.cell');
    if (pc) {
      const uid = +pc.dataset.uid, u = pieceById(ui.view, uid);
      if (ui.sel && pc.classList.contains('tgt')) {
        if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, tgt: uid });
        return doAct({ t: 'attack', from: ui.sel.uid, to: uid });
      }
      if (u && u.side === ME && canActNow(uid)) { ui.sel = ui.sel && ui.sel.kind === 'piece' && ui.sel.uid === uid ? null : { kind: 'piece', uid }; render(); return; }
    } else if (cellEl && cellEl.classList.contains('dest') && ui.sel) {
      const cell = +cellEl.dataset.cell;
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, cell });
      return doAct({ t: 'move', from: ui.sel.uid, to: cell });
    }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i];
    if (id === 'COIN') return doAct({ t: 'play', card: id });
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled) {
    if (b.id === 'rematch' || b.id === 'newgame') return startMatch();
    if (b.id === 'endturn') return myEndTurn();
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.__game = { state: () => ui.s, busy: () => ui.busy, act: (a) => doAct(a), end: () => myEndTurn(), legal: () => legalActions(ui.s) };
startMatch();
