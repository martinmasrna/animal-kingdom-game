// 45 Swing neutrals as a game screen against Expert. Three Neutrals stand on loyalty tracks
// between the two players: a token low on its track leans your way, high leans his. Each action is
// animated from the state before and the state after; the win tally decides who goes first.

import { CARDS, MAX_MANA, newMatch, act, legalActions, toward } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-45-tally';
const expert = expertBot({ ...EXPERT, timeMs: 1300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const ART = { S1: '+1', S2: '+2', S3: '+3', SPR: '+1+1+1', EXI: '✕', SHD: '4', RAL: '!', DR2: '+2', COIN: '+1' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}>${c.kind === 'coin' ? '' : `<span class="cgem">${c.cost}</span>`}<div class="art"><span class="big${ART[id].length > 3 ? ' small' : ''}">${ART[id]}</span></div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function targetsNow() {
  const out = new Set();
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) if (a.t === 'play' && a.card === ui.sel.id && a.slot !== undefined) out.add(a.slot);
  return out;
}

// ------------------------------------------------------------------ rendering
function lifeHTML(side) {
  const p = ui.view.p[side];
  return `<div class="hero s${side} ${ui.fx['hero' + side] || ''}" id="hero${side}x"><span class="hp">${p.life}</span>${p.shield ? `<span class="shield">${p.shield}</span>` : ''}</div>`;
}
function fieldHTML(T) {
  return ui.view.slots.map((n, k) => {
    // row 0 at the top is 3 toward him; row 6 at the bottom is 3 toward me
    const pos = 3 + toward(n, ME);
    let cells = '';
    for (let r = 0; r < 7; r++) cells += `<i class="cell r${r}${r === 3 ? ' mid' : r < 3 ? ' his' : ' mine'}"></i>`;
    const cls = (T.has(k) ? ' tgt' : '') + (ui.fx['n' + k] ? ' ' + ui.fx['n' + k] : '') + (pos > 3 ? ' mine' : pos < 3 ? ' his' : '');
    return `<div class="track" data-slot="${k}">${cells}<div class="tok${cls}" id="n${k}" data-slot="${k}" style="--r:${pos}"><span>${n.atk}</span></div></div>`;
  }).join('');
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div><div class="pile nd">${ui.view.ndeck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const order = p.hand.map((_, i) => i).sort((a, b) => (p.hand[a] === 'COIN' ? -1 : 0) - (p.hand[b] === 'COIN' ? -1 : 0) || CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost || (p.hand[a] < p.hand[b] ? -1 : 1));
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = lifeHTML(side); $('res' + side).innerHTML = resHTML(side); }
  $('field').innerHTML = fieldHTML(T);
  $('hand').innerHTML = handHTML();
  $('turnbox').innerHTML = `<button id="endturn"${!ui.over && s.toAct === ME && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('field').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(650);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .6}px, ${dy * .6}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out', composite: 'add' }).finished;
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const playE = ev.find(e => e.t === 'play');
  if (playE && playE.side === BOT) await spotlight(playE.card, BOT);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  // the start-of-turn hits and Rally, one Neutral at a time, before the new state shows
  const hits = ev.filter(e => e.t === 'damage' && (e.src === 'neutral' || e.src === 'rally'));
  for (const e of hits) { await lunge($('n' + e.slot), $('hero' + e.side + 'x')); floatAt(centerOf($('hero' + e.side + 'x')), e.n ? '−' + e.n : '0', e.blocked ? 'blocked' : ''); ui.fx['hero' + e.side] = 'shake'; }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'loy' && e.from !== e.to) ui.fx['n' + e.slot] = 'moved';
    if (e.t === 'exile') ui.fx['n' + e.slot] = 'new';
    if (e.t === 'damage' && e.src === 'fatigue') ui.fx['hero' + e.side] = 'shake';
  }
  ui.view = next; render();
  for (const e of ev) if (e.t === 'damage' && e.src === 'fatigue') floatAt(centerOf($('hero' + e.side + 'x')), '−' + e.n);
  if (playE) {
    const c = CARDS[playE.card];
    ui.hist.push({ side: playE.side, kind: c.kind, chip: ART[playE.card], out: playE.slot !== undefined ? 'N' + (playE.slot + 1) : '' });
  }
  for (const side of [0, 1]) { const d = hits.filter(e => e.side === 1 - side); if (d.length) ui.hist.push({ side, kind: 'hit', chip: '⚔', out: '−' + d.reduce((x, e) => x + e.n, 0) + ' life', cls: 'face' }); }
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
  const tr = e.target.closest('.track');
  if (tr && ui.sel && T.has(+tr.dataset.slot)) return doAct({ t: 'play', card: ui.sel.id, slot: +tr.dataset.slot });
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], k = CARDS[id].kind;
    if (k === 'sway' || k === 'exile' || k === 'rally') { ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b && !b.disabled && b.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.__game = { get s() { return ui.s; }, get busy() { return ui.busy; }, get over() { return ui.over; } };
startMatch();
