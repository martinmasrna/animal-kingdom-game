// Score-or-fight as a game screen against the Expert. Each action is animated from the state
// before and the state after; the win tally is kept in this browser and decides who goes first
// (alternating). The bot's turn plays out one action at a time.

import { CARDS, MAX_MANA, TARGET, newMatch, act, legalActions } from './engine.js';
import { makeRng, mcExpert, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-01-score-or-fight-tally';
const expert = mcExpert({ ...EXPERT, timeMs: 1200, minPlayouts: 300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art;
  if (c.kind === 'Unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'Spell') art = `<span class="big">${c.dmg}</span>`;
  else art = `<span class="big">+1</span>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
function targetsNow() {
  const out = { score: false, units: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.to !== undefined) out.units.add(BOT + ':' + a.to);
    if (ui.sel.kind === 'unit' && a.t === 'attack' && a.from === ui.sel.i) out.units.add(BOT + ':' + a.to);
    if (ui.sel.kind === 'unit' && a.t === 'score' && a.from === ui.sel.i) out.score = true;
  }
  return out;
}
const canAct = (i) => myTurn() && legalActions(ui.view).some(a => a.t === 'score' && a.from === i);

// ------------------------------------------------------------------ rendering
function scoreHTML(side, T) {
  const p = ui.view.p[side], f = Math.min(1, p.score / TARGET);
  return `<div class="score s${side}${side === ME && T.score ? ' tgt' : ''}" id="score${side}" style="--f:${f}"><span class="pts">${p.score}</span><span class="of">${TARGET}</span></div>`;
}
function boardHTML(side, T) {
  return ui.view.p[side].board.map((m, i) => {
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAct(i)) cls += ' can';
    if (T.units.has(side + ':' + i)) cls += ' tgt';
    if (side === ui.view.turn && !m.ready) cls += ' sleep';
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="minion s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}"><span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div>`;
  }).join('');
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
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost; });
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) {
  const chip = h.kind === 'Attack' ? `<span class="chip Attack s${h.side}">${h.atk}</span>`
    : h.kind === 'Score' ? `<span class="chip Score s${h.side}">+</span>`
    : h.kind === 'Coin' ? `<span class="chip Coin"></span>`
    : h.kind === 'Unit' ? `<span class="chip Minion s${h.side}">${CARDS[h.card].atk}/${CARDS[h.card].hp}</span>`
    : `<span class="chip Spell">${CARDS[h.card].dmg}</span>`;
  return `<div class="hist s${h.side}">${chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
}
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = scoreHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, left = mine && !ui.busy && legalActions(s).some(a => a.t !== 'end');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !left ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.minion, .score').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(650);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl, k = 0.8) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * k}px, ${dy * k}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out' }).finished;
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
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack'), scE = ev.find(e => e.t === 'score');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'Spell')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('m' + atkE.uid), $('m' + atkE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (scE) await lunge($('m' + scE.uid), $('score' + scE.side), 0.35);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
    if (e.t === 'gain') ui.fx['score' + e.side] = 'bump';
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['m' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'gain') { const p = before['score' + e.side]; if (p) floatAt(p.c, '+' + e.n, 'plus'); }
  }
  if (playE) {
    const c = CARDS[playE.card], died = ev.some(e => e.t === 'die');
    ui.hist.push({ side: playE.side, kind: c.kind, card: playE.card, out: c.kind === 'Spell' ? (died ? '✕' : '−' + c.dmg) : '', cls: died ? 'kill' : 'dmg' });
  }
  if (atkE) {
    const atk = prev.p[atkE.side].board[atkE.from].atk, died = ev.filter(e => e.t === 'die' && e.side !== atkE.side).length;
    ui.hist.push({ side: atkE.side, kind: 'Attack', atk, out: died ? '✕' : '−' + atk, cls: died ? 'kill' : 'dmg' });
  }
  if (scE) ui.hist.push({ side: scE.side, kind: 'Score', out: '+' + scE.n, cls: 'gain' });
  const fat = ev.find(e => e.t === 'fatigue');
  if (fat) ui.hist.push({ side: 1 - fat.side, kind: 'Score', out: '+' + fat.n, cls: 'gain' });
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 600 : 250);
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
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(350);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) return;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 300 : 250);
    if (tok !== ui.token || ui.over) return;
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
  await botMove(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { if (e.target.closest('#closerules')) $('rules').classList.remove('show'); return; }
  const tgt = e.target.closest('.minion, .score');
  if (tgt && myTurn()) {
    if (tgt.classList.contains('score')) { if (ui.sel && ui.sel.kind === 'unit' && tgt.classList.contains('tgt')) return doAct({ t: 'score', from: ui.sel.i }); }
    else {
      const side = +tgt.dataset.side, i = +tgt.dataset.i;
      if (ui.sel && tgt.classList.contains('tgt')) {
        if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, to: i });
        return doAct({ t: 'attack', from: ui.sel.i, to: i });
      }
      if (side === ME && canAct(i)) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i ? null : { kind: 'unit', i }; render(); return; }
    }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], c = CARDS[id];
    if (c.kind === 'Spell') { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
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
