// Time track as a game screen against Expert. Every action goes through legalActions/act and is
// animated from the events it emits; the bot acts one action at a time while it is behind.

import { CARDS, END, newMatch, act, legalActions, isReady } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-33-tally';
const expert = expertBot({ iters: 5000 });
const ui = { s: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'Unit') art = `<span class="rec">${c.rec}</span><span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'Hit') { art = `<span class="big">${c.dmg}</span>`; tx = `<div class="tx">To a unit or the enemy.</div>`; }
  else { art = `<span class="big">»</span>`; tx = `<div class="tx">Your unit is ready now.</div>`; }
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.time}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.s.turn === ME;
const legal = () => myTurn() ? legalActions(ui.s) : [];
function targetsNow() {
  const out = { heroes: new Set(), units: new Set() };
  if (!ui.sel) return out;
  for (const a of legal()) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.target) { if (a.target.i < 0) out.heroes.add(a.target.side); else out.units.add(a.target.side + ':' + a.target.i); }
    if (ui.sel.kind === 'unit' && a.t === 'atk' && a.i === ui.sel.i) { if (a.j < 0) out.heroes.add(BOT); else out.units.add(BOT + ':' + a.j); }
  }
  return out;
}

// ------------------------------------------------------------------ rendering
function trackHTML() {
  const s = ui.s, pct = (x) => (100 * Math.min(x, END) / END) + '%';
  let h = '<div class="bar">';
  for (let x = 0; x <= END; x += 10) h += `<span class="lab" style="left:${pct(x)}">${x}</span>`;
  for (let x = 0; x <= END; x += 5) h += `<span class="tick${x % 10 ? '' : ' big'}" style="left:${pct(x)}"></span>`;
  h += '</div>';
  for (const side of [0, 1]) {
    const P = s.p[side];
    for (const m of P.board) if (m.readyAt > P.pos) h += `<span class="rdy s${side}" style="left:${pct(m.readyAt)}"></span>`;
    const on = s.winner === null && s.turn === side ? ' on' : '', top = s.p[0].pos === s.p[1].pos && s.top === side ? ' top' : '';
    h += `<span class="mark s${side}${on}${top}" style="left:${pct(P.pos)}">${P.pos}</span>`;
  }
  return h;
}
function heroHTML(side, T) {
  const p = ui.s.p[side];
  return `<div class="hero s${side}${T.heroes.has(side) ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-i="-1"><span class="hp">${p.life}</span></div>`;
}
function boardHTML(side, T) {
  const s = ui.s;
  return s.p[side].board.map((m, i) => {
    const ready = isReady(s, side, m);
    let cls = ready ? '' : ' sleep';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && myTurn() && ready) cls += ' can';
    if (T.units.has(side + ':' + i)) cls += ' tgt';
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="unit s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}">${ready ? '' : `<span class="at s${side}">${m.readyAt}</span>`}<span class="rec">${m.rec}</span><span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div>`;
  }).join('');
}
function handHTML() {
  const p = ui.s.p[ME], L = legal();
  const R = { Unit: 1, Hit: 2, Haste: 3 };
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.time - B.time; });
  return order.map(i => {
    const id = p.hand[i], ok = L.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.s, T = targetsNow(), t = loadTally(), L = legal();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('track').innerHTML = trackHTML();
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); }
  const canDraw = L.some(a => a.t === 'draw'), mustWait = L.length === 1 && L[0].t === 'wait';
  $('res1').innerHTML = `<div class="pile s1">${s.p[BOT].deck.length}</div>`;
  $('res0').innerHTML = `<button class="pile s0${canDraw ? ' ok' : ''}" id="drawpile"${canDraw ? '' : ' disabled'}>${s.p[ME].deck.length}</button>`;
  $('turnbox').innerHTML = mustWait ? '<button id="wait">Wait</button>' : '';
  $('hand').innerHTML = handHTML();
  $('history').innerHTML = ui.hist.slice(-12).map(h => `<div class="hist s${h.side}">${h.chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function snapshot() { const out = {}; document.querySelectorAll('.unit, .hero').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
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
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'atk'), moveE = ev.find(e => e.t === 'move');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind !== 'Unit')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('m' + atkE.uid), atkE.j < 0 ? $('hero' + (1 - atkE.side) + 'x') : $('m' + atkE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.i >= 0 && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'hit' && e.i < 0) ui.fx['hero' + e.side] = 'shake';
    if (e.t === 'haste') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.s = next; ui.sel = null; render();
  for (const e of ev) {
    if (e.t === 'hit') { const id = e.i < 0 ? 'hero' + e.side + 'x' : 'm' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
  }
  const cost = moveE ? `<span class="tc">+${moveE.to - moveE.from}</span>` : '';
  if (playE) {
    const c = CARDS[playE.card], hits = ev.filter(e => e.t === 'hit'), died = ev.some(e => e.t === 'die');
    const chip = c.kind === 'Unit' ? `<span class="chip Unit s${playE.side}">${c.atk}/${c.hp}</span>` : `<span class="chip ${c.kind}">${c.kind === 'Hit' ? c.dmg : '»'}</span>`;
    const out = c.kind === 'Hit' ? (died ? '✕' : hits[0] && hits[0].i < 0 ? '−' + c.dmg + ' life' : '−' + c.dmg) : '';
    ui.hist.push({ side: playE.side, chip: chip + cost, out, cls: died ? 'kill' : 'dmg' });
  }
  if (atkE) {
    const m = prev.p[atkE.side].board.find(x => x.uid === atkE.uid), kill = ev.some(e => e.t === 'die' && e.uid === atkE.tuid);
    ui.hist.push({ side: atkE.side, chip: `<span class="chip Atk s${atkE.side}">${m.atk}</span>` + cost, out: atkE.j < 0 ? '−' + m.atk + ' life' : kill ? '✕' : '−' + m.atk, cls: kill ? 'kill' : 'dmg' });
  }
  if (a.t === 'draw') ui.hist.push({ side: prev.turn, chip: `<span class="chip Draw">+1</span>` + cost, out: '' });
  if (a.t === 'wait') ui.hist.push({ side: prev.turn, chip: `<span class="chip Draw">·</span>` + cost, out: '' });
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
  await wait(700);
  if (tok !== ui.token) return;
  return loop(tok);
}
// the bot acts while it is its move; then the human
async function loop(tok) {
  while (tok === ui.token && !ui.over && ui.s.turn === BOT) {
    ui.busy = true; render();
    await wait(450);
    const a = expert(ui.s, ui.rng);
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
  return loop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { $('rulesbox').classList.toggle('show'); return; }
  if (e.target.closest('#rulesbox')) { $('rulesbox').classList.remove('show'); return; }
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (!myTurn()) return;
  const tgt = e.target.closest('.unit, .hero');
  if (tgt) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, target: { side, i } });
      return doAct({ t: 'atk', i: ui.sel.i, j: i });
    }
    if (side === ME && i >= 0 && isReady(ui.s, ME, ui.s.p[ME].board[i])) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i ? null : { kind: 'unit', i }; render(); return; }
  }
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = ui.s.p[ME].hand[i], c = CARDS[id];
    if (c.kind !== 'Unit') { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b0 && !b0.disabled && b0.id === 'drawpile') return doAct({ t: 'draw' });
  if (b0 && !b0.disabled && b0.id === 'wait') return doAct({ t: 'wait' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rulesbox').classList.remove('show'); render(); } });
startMatch();
