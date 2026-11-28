// 32 Hidden contracts as a game screen against the Expert. Each action is animated from the state
// before and the state after; the win tally is kept in this browser and decides who goes first.

import { CARDS, CONTRACTS, MAX_MANA, BOARD, TARGET, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-32-tally';
const expert = expertBot({ ...EXPERT, playouts: 2400, timeMs: 1300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'hit') { art = `<span class="big">${c.dmg}</span>`; tx = `<div class="tx">${c.dmg} damage to an enemy unit</div>`; }
  else { art = `<span class="big">+1</span>`; tx = `<div class="tx">+1 mana this turn</div>`; }
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}
function contractHTML(c, { cls = '', swap = false } = {}) {
  const k = CONTRACTS[c];
  return `<div class="contract ${cls}"><span class="pts">${k.pts}</span><b>${k.name}</b><span class="ct">${k.text}</span>${swap ? `<button class="swap" data-c="${c}">↻ 1</button>` : ''}</div>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
function targetsNow() {
  const out = new Set();
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.tgt) out.add(a.tgt);
    if (ui.sel.kind === 'unit' && a.t === 'attack' && a.from === ui.sel.uid) out.add(a.to);
  }
  return out;
}
const canAttack = (uid) => myTurn() && legalActions(ui.view).some(a => a.t === 'attack' && a.from === uid);

// ------------------------------------------------------------------ rendering
function boardHTML(side, T) {
  const B = ui.view.p[side].board;
  let h = B.map(u => {
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === u.uid) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(u.uid)) cls += ' can';
    if (T.has(u.uid)) cls += ' tgt';
    if (side === ui.view.turn && !u.ready) cls += ' sleep';
    if (ui.fx['u' + u.uid]) cls += ' ' + ui.fx['u' + u.uid];
    return `<div class="unit s${side}${cls}" id="u${u.uid}" data-side="${side}" data-uid="${u.uid}"><span class="un">${CARDS[u.card].name}</span><span class="stat a">${u.atk}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span></div>`;
  }).join('');
  for (let i = B.length; i < BOARD; i++) h += '<div class="slot"></div>';
  return h;
}
function infoHTML(side) {
  const p = ui.view.p[side], legal = side === ME && myTurn() ? legalActions(ui.view) : [];
  let pips = '';
  for (let i = 0; i < TARGET; i++) pips += `<i class="pip${i < p.points ? ' on' : ''}"></i>`;
  const score = `<div class="score s${side} ${ui.fx['score' + side] || ''}" id="score${side}"><span class="pn">${p.points}</span><span class="pips">${pips}</span></div>`;
  const held = side === ME
    ? p.contracts.map(c => contractHTML(c, { swap: legal.some(a => a.t === 'swap' && a.c === c) })).join('')
    : p.contracts.map(() => '<div class="contract down">?</div>').join('');
  const left = `<span class="left" title="">${p.cdeck.length}</span>`;
  const done = p.revealed.map(c => `<span class="done">${CONTRACTS[c].name} ${CONTRACTS[c].pts}</span>`).join('');
  return `${score}<div class="held">${held}${left}</div><div class="dones">${done}</div>`;
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { coin: 0, unit: 1, hit: 2 };
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
  for (const side of [0, 1]) { $('board' + side).innerHTML = boardHTML(side, T); $('info' + side).innerHTML = infoHTML(side); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, canAct = mine && !ui.busy && legalActions(s).some(a => a.t === 'attack' || a.t === 'play');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(html) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = html;
  await wait(800);
  const c = $('spot').firstElementChild; if (c) c.classList.add('out');
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
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack'), swapE = ev.find(e => e.t === 'swap');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'hit')) await spotlight(cardHTML(playE.card, playE.side));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (swapE && swapE.side === BOT) await spotlight('<div class="contract down big">↻</div>');
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('u' + atkE.uid), $('u' + atkE.to));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['u' + e.uid] = 'new';
    if (e.t === 'hit' && e.hp > 0) ui.fx['u' + e.uid] = 'shake';
    if (e.t === 'score' || e.t === 'empty') ui.fx['score' + (e.t === 'score' ? e.side : 1 - e.side)] = 'pop';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  // a contract that scores is shown before the board moves on
  for (const e of ev) if (e.t === 'score') { ui.view = prev; await spotlight(contractHTML(e.c, { cls: 'big s' + e.side })); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['u' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
    if (e.t === 'score') { const el = $('score' + e.side); if (el) floatAt(centerOf(el), '+' + e.pts, 'gain'); }
    if (e.t === 'empty') { const el = $('score' + (1 - e.side)); if (el) floatAt(centerOf(el), '+1', 'gain'); }
  }
  if (playE) {
    const c = CARDS[playE.card], died = ev.some(e => e.t === 'die');
    if (c.kind === 'unit') ui.hist.push({ side: playE.side, kind: 'u', chip: `${c.atk}/${c.hp}` });
    else if (c.kind === 'hit') ui.hist.push({ side: playE.side, kind: 'hit', chip: c.dmg, out: died ? '✕' : '−' + c.dmg, cls: died ? 'kill' : 'dmg' });
    else ui.hist.push({ side: playE.side, kind: 'coin', chip: '+1' });
  }
  if (atkE) {
    const u = prev.p[atkE.side].board.find(x => x.uid === atkE.uid), killed = ev.some(e => e.t === 'die' && e.side !== atkE.side);
    ui.hist.push({ side: atkE.side, kind: 'atk', chip: '⚔' + u.atk, out: killed ? '✕' : '−' + u.atk, cls: killed ? 'kill' : 'dmg' });
  }
  if (swapE) ui.hist.push({ side: swapE.side, kind: 'swap', chip: '↻' });
  for (const e of ev) if (e.t === 'score') ui.hist.push({ side: e.side, kind: 'score', chip: '+' + e.pts, out: CONTRACTS[e.c].name, cls: 'face' });
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
  const his = ui.s.p[BOT].contracts.map(c => contractHTML(c)).join('');
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2>${his ? `<div class="reveal">${his}</div>` : ''}<button id="rematch">Play again</button>`;
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
  for (let k = 0; k < 40; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) break;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 300 : 250);
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
  const sw = e.target.closest('button.swap'); // not the swap chip in the history
  if (sw && myTurn()) return doAct({ t: 'swap', c: sw.dataset.c });
  const tgt = e.target.closest('.unit');
  if (tgt && myTurn()) {
    const side = +tgt.dataset.side, uid = +tgt.dataset.uid;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, tgt: uid });
      return doAct({ t: 'attack', from: ui.sel.uid, to: uid });
    }
    if (side === ME && canAttack(uid)) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === uid ? null : { kind: 'unit', uid }; render(); return; }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], c = CARDS[id];
    if (c.kind === 'hit') { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
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
