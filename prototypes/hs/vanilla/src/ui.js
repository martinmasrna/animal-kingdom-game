// Vanilla HS as a game screen against the play-out Expert. Each action is animated from the
// state before and the state after; the win tally is kept in this browser and decides who
// goes first (alternating).

import { CARDS, MAX_MANA, BOARD, newMatch, act, endTurn, legalActions } from './engine.js';
import { makeRng, rolloutBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'vanilla-hs-tally';
const expert = rolloutBot(6, 4, 8);
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, nm, tx = '';
  if (c.kind === 'Minion') { art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`; nm = 'Minion'; }
  else if (c.kind === 'Spell') { art = `<span class="big">${c.dmg}</span>`; nm = 'Spell'; tx = `<div class="tx">Deal ${c.dmg} damage.</div>`; }
  else { art = `<span class="big">+1</span>`; nm = 'Coin'; tx = `<div class="tx">Gain 1 mana this turn.</div>`; }
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${nm}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
function targetsNow() {
  const out = { heroes: new Set(), minions: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.target) { if (a.target.i < 0) out.heroes.add(a.target.side); else out.minions.add(a.target.side + ':' + a.target.i); }
    if (ui.sel.kind === 'minion' && a.t === 'attack' && a.from === ui.sel.i) { if (a.to < 0) out.heroes.add(BOT); else out.minions.add(BOT + ':' + a.to); }
  }
  return out;
}
const canAttack = (i) => myTurn() && legalActions(ui.view).some(a => a.t === 'attack' && a.from === i);

// ------------------------------------------------------------------ rendering
function heroHTML(side, T) {
  const p = ui.view.p[side];
  return `<div class="hero s${side}${T.heroes.has(side) ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-i="-1"><span class="hp">${p.hp}</span></div>`;
}
function boardHTML(side, T) {
  return ui.view.p[side].board.map((m, i) => {
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(i)) cls += ' can';
    if (T.minions.has(side + ':' + i)) cls += ' tgt';
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
  const order = p.hand.map((_, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]], R = { Coin: 0, Minion: 1, Spell: 2 };
    return R[A.kind] - R[B.kind] || A.cost - B.cost;
  });
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
    : h.kind === 'Coin' ? `<span class="chip Coin"></span>`
    : h.kind === 'Minion' ? `<span class="chip Minion s${h.side}">${CARDS[h.card].atk}/${CARDS[h.card].hp}</span>`
    : `<span class="chip Spell">${CARDS[h.card].dmg}</span>`;
  return `<div class="hist s${h.side}">${chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
}
function render() {
  const s = ui.view, T = targetsNow();
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, canAct = mine && !ui.busy && legalActions(s).some(a => a.t === 'attack' || (a.t === 'play' && !(a.target && a.target.side === ME)));
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
const elOf = (side, i, uid) => i < 0 ? $('hero' + side + 'x') : $('m' + uid);
// where everything is now, so hits on things that die can still be shown in place
function snapshot() { const out = {}; document.querySelectorAll('.minion, .hero').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(700);
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
async function apply(fn) {
  const prev = ui.s, ev = [];
  const next = fn(prev, ev);
  ui.s = next;
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'Spell')) await spotlight(playE.card, playE.side);
  if (atkE) await lunge($('m' + atkE.uid), atkE.to < 0 ? $('hero' + (1 - atkE.side) + 'x') : $('m' + atkE.tuid));
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.i >= 0 && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'hit' && e.i < 0) ui.fx['hero' + e.side] = 'shake';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const id = e.i < 0 ? 'hero' + e.side + 'x' : 'm' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'fatigue') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '−' + e.n); }
  }
  // history
  if (playE) {
    const c = CARDS[playE.card], hits = ev.filter(e => e.t === 'hit'), died = ev.some(e => e.t === 'die');
    const out = c.kind === 'Spell' ? (died ? '✕' : hits[0] && hits[0].i < 0 ? '−' + c.dmg + ' face' : '−' + c.dmg) : '';
    ui.hist.push({ side: playE.side, kind: c.kind, card: playE.card, out, cls: died ? 'kill' : hits[0] && hits[0].i < 0 ? 'face' : 'dmg' });
  }
  if (atkE) {
    const atk = prev.p[atkE.side].board[atkE.from].atk, died = ev.filter(e => e.t === 'die' && e.side !== atkE.side).length;
    ui.hist.push({ side: atkE.side, kind: 'Attack', atk, out: atkE.to < 0 ? '−' + atk + ' face' : died ? '✕' : '−' + atk, cls: atkE.to < 0 ? 'face' : died ? 'kill' : 'dmg' });
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
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(350);
  const acts = expert(ui.s, ui.rng);
  for (const a of acts) {
    if (tok !== ui.token || ui.over) return;
    await wait(250);
    await apply((s, ev) => act(s, a, ev));
  }
  if (tok !== ui.token || ui.over) return;
  await wait(300);
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  ui.busy = true; ui.sel = null;
  await apply((s, ev) => act(s, a, ev));
  ui.busy = false; render();
}
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const tgt = e.target.closest('.minion, .hero');
  if (tgt && myTurn()) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, target: { side, i } });
      return doAct({ t: 'attack', from: ui.sel.i, to: i });
    }
    if (side === ME && i >= 0 && canAttack(i)) { ui.sel = ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i ? null : { kind: 'minion', i }; render(); return; }
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
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.sel) { ui.sel = null; render(); } });
startMatch();
