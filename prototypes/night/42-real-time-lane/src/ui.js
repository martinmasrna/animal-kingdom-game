// 42 Real-time lane as a page: you (base at 0) against Expert, in real time. Every half second
// the page calls the engine's step() with your queued action and Expert's, the same API the sim uses.

import { CARDS, LEN, TICKS, OVERTIME, MANA_MAX, MANA_EVERY, BLAST_R, HAND, newMatch, step, hand, nextCard, canPlay } from './engine.js';
import { makeRng, expertBot, DECIDE_EVERY } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-42-tally', TICK_MS = 500, W = { t: 'wait' };
const expert = expertBot({ playouts: 600, horizon: 40, timeMs: 220 });
const ui = { s: null, over: false, paused: false, sel: null, pending: null, hist: [], els: new Map(), timer: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let body = '';
  if (c.kind === 'unit') body = `<div class="stats"><span class="h">${c.hp}${c.n ? '×' + c.n : ''}</span> · <span class="a">${c.atk}</span></div>`;
  else if (c.kind === 'wall') body = `<div class="stats"><span class="h">${c.hp}</span></div><div class="tx">in your half</div>`;
  else body = `<div class="tx">8 to enemy units within 1.5</div>`;
  return `<button class="card ${cls}" ${attrs}><span class="cost">${c.cost}</span><div class="nm">${c.name}</div>${body}</button>`;
}

// ------------------------------------------------------------------ geometry
const vertical = () => window.innerHeight > window.innerWidth;
function lanePos(x, track) {
  const L = $('lane'), w = L.clientWidth, h = L.clientHeight, pad = vertical() ? 44 : 58;
  if (!vertical()) return { left: pad + (x / LEN) * (w - 2 * pad), top: h / 2 + track * Math.min(48, h / 6) };
  return { left: w / 2 + track * Math.min(46, w / 6), top: h - pad - (x / LEN) * (h - 2 * pad) };
}
function laneX(ev) {
  const L = $('lane'), r = L.getBoundingClientRect(), pad = vertical() ? 44 : 58;
  const f = vertical() ? (r.bottom - pad - ev.clientY) / (r.height - 2 * pad) : (ev.clientX - r.left - pad) / (r.width - 2 * pad);
  return Math.max(0.5, Math.min(11.5, Math.round(f * LEN * 2) / 2));
}
const trackOf = (u) => u.wall ? 0 : [0, -1, 1, -2, 2][u.uid % 5] * (u.side === ME ? 1 : 1);

// ------------------------------------------------------------------ rendering
function render(fx = {}) {
  const s = ui.s, t = loadTally();
  $('lane').className = (vertical() ? 'v' : 'h') + (ui.sel ? ' aiming' + (CARDS[ui.sel].kind === 'wall' ? ' wall' : '') : '');
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opp').innerHTML = '<i class="back"></i>'.repeat(HAND) + `<span class="oppmana">${s.mana[BOT]}</span>`;
  const left = s.tick < TICKS ? TICKS - s.tick : TICKS + OVERTIME - s.tick, sec = Math.ceil(left / 2);
  $('clock').textContent = `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`;
  $('clock').className = s.tick >= TICKS ? 'ot' : '';
  $('base0').textContent = Math.max(0, s.base[0]); $('base1').textContent = Math.max(0, s.base[1]);
  // units, one element each so they glide
  const box = $('units'), alive = new Set();
  for (const u of s.units) {
    alive.add(u.uid);
    let el = ui.els.get(u.uid);
    const c = CARDS[u.card];
    if (!el) { el = document.createElement('div'); el.className = `u s${u.side}${u.wall ? ' wall' : ''}${u.card === 'TAN' || u.card === 'BRU' ? ' big' : ''}${u.card === 'SWA' ? ' small' : ''}`; box.appendChild(el); ui.els.set(u.uid, el); const p = lanePos(u.x, trackOf(u)); el.style.left = p.left + 'px'; el.style.top = p.top + 'px'; void el.offsetWidth; }
    el.innerHTML = u.wall ? `<span class="hp">${u.hp}</span>` : `<span class="n">${c.name}</span><span class="hp">${u.hp}</span>`;
    el.classList.toggle('hit', !!fx[u.uid]);
    const p = lanePos(u.x, trackOf(u)); el.style.left = p.left + 'px'; el.style.top = p.top + 'px';
  }
  for (const [uid, el] of ui.els) if (!alive.has(uid)) { el.remove(); ui.els.delete(uid); }
  // mana and hand
  let m = '';
  for (let i = 0; i < MANA_MAX; i++) { const f = i < s.mana[ME] ? 100 : i === s.mana[ME] ? 100 * (s.tick % MANA_EVERY) / MANA_EVERY : 0; m += `<span class="seg"><i style="width:${f}%"></i></span>`; }
  $('mana').innerHTML = `<span class="num">${s.mana[ME]}</span>${m}`;
  $('hand').innerHTML = hand(s, ME).map(id => {
    const ok = !ui.over && CARDS[id].cost <= s.mana[ME];
    const on = ui.sel === id || (ui.pending && ui.pending.card === id);
    return cardHTML(id, { cls: (ok ? 'ok' : 'no') + (on ? ' sel' : ''), attrs: `data-card="${id}"` });
  }).join('') + cardHTML(nextCard(s, ME), { cls: 'next', attrs: 'disabled' });
  $('history').innerHTML = ui.hist.slice(-16).map(h => `<div class="hist s${h.side}"><span>${h.txt}</span><span class="t">${h.time}</span></div>`).join('');
}
function floatAt(x, y, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = x + 'px'; f.style.top = y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1100); }
function centerIn(el) { const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - g.left + r.width / 2, y: r.top - g.top + r.height / 2 }; }
function boom(x) {
  const L = $('lane'), p = lanePos(x, 0), span = Math.abs(lanePos(x + BLAST_R, 0)[vertical() ? 'top' : 'left'] - p[vertical() ? 'top' : 'left']) * 2;
  const d = document.createElement('div'); d.className = 'boom'; d.style.width = d.style.height = span + 'px'; d.style.left = (p.left - span / 2) + 'px'; d.style.top = (p.top - span / 2) + 'px'; L.appendChild(d); setTimeout(() => d.remove(), 650);
}
function popCard(id) {
  const b = centerIn($('base1')), d = document.createElement('div'); d.className = 'pop';
  d.innerHTML = cardHTML(id); d.style.left = (vertical() ? b.x + 80 : b.x - 80) + 'px'; d.style.top = (vertical() ? b.y + 70 : b.y) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 1150);
}
const clockText = (tick) => { const sec = Math.floor(tick / 2); return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`; };

// ------------------------------------------------------------------ the clock
function tickOnce(tok) {
  if (tok !== ui.token || ui.over || ui.paused) return;
  const s = ui.s;
  const mine = ui.pending && canPlay(s, ME, ui.pending) ? ui.pending : W;
  ui.pending = null;
  const bot = s.tick % DECIDE_EVERY === 0 ? expert(s, BOT, ui.rng) : W;
  const ev = [];
  ui.s = step(s, [mine, bot], ev);
  const fx = {};
  for (const e of ev) {
    if (e.t === 'hit') fx[e.uid] = 1;
    if (e.t === 'play') { ui.hist.push({ side: e.side, txt: CARDS[e.card].name, time: clockText(s.tick) }); if (e.side === BOT) popCard(e.card); }
  }
  render(fx);
  for (const e of ev) {
    if (e.t === 'boom') boom(e.x);
    if (e.t === 'base') { const p = centerIn($('base' + e.side)); floatAt(p.x, p.y - 30, '−' + e.n); }
  }
  if (ui.s.winner !== null) finish();
}
function finish() {
  if (ui.over) return;
  ui.over = true; clearInterval(ui.timer);
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
  render();
}
function startMatch() {
  const tok = ++ui.token;
  clearInterval(ui.timer);
  for (const el of ui.els.values()) el.remove();
  ui.els.clear();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.over = false; ui.hist = []; ui.sel = null; ui.pending = null;
  $('over').classList.remove('show');
  render();
  const b = $('banner'); b.textContent = 'Go'; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show');
  setTimeout(() => { if (tok === ui.token) ui.timer = setInterval(() => tickOnce(tok), TICK_MS); }, 800);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); ui.paused = true; return; }
  if ((b && b.id === 'rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); ui.paused = false; return; }
  if (b && (b.id === 'newgame' || b.id === 'rematch')) return startMatch();
  if (ui.over || ui.paused) return;
  if (b && b.dataset.card) {
    const id = b.dataset.card, c = CARDS[id];
    if (c.cost > ui.s.mana[ME]) return;
    if (c.kind === 'unit') { ui.pending = { t: 'play', card: id }; ui.sel = null; }
    else { ui.sel = ui.sel === id ? null : id; ui.pending = null; }
    render(); return;
  }
  if (ui.sel && e.target.closest('#lane')) {
    const x = laneX(e), a = { t: 'play', card: ui.sel, x };
    if (canPlay(ui.s, ME, a)) { ui.pending = a; ui.sel = null; $('aim').style.display = 'none'; render(); }
    return;
  }
  if (ui.sel) { ui.sel = null; $('aim').style.display = 'none'; render(); }
});
document.addEventListener('pointermove', (e) => {
  const aim = $('aim');
  if (!ui.sel || CARDS[ui.sel].kind !== 'blast' || !e.target.closest('#lane')) { aim.style.display = 'none'; return; }
  const x = laneX(e), p = lanePos(x, 0), q = lanePos(x + BLAST_R, 0), span = Math.abs((vertical() ? q.top - p.top : q.left - p.left)) * 2;
  aim.style.display = 'block'; aim.style.width = aim.style.height = span + 'px'; aim.style.left = (p.left - span / 2) + 'px'; aim.style.top = (p.top - span / 2) + 'px';
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); ui.paused = false; render(); } });
window.addEventListener('resize', () => { if (ui.s) render(); });
startMatch();
