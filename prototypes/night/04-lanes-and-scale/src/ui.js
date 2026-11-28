// Lanes and scale as a game screen against Expert. You sit at the bottom; the scale's bottom end
// is yours. The bot plays one action at a time, and each combat plays out lane by lane.

import { CARDS, MAX_MANA, LANES, WIN, newMatch, act, isLegal } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-04-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'Unit' ? `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>` : '';
  const tx = c.kind === 'Unit' ? '' : `<div class="tx">${c.text}</div>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.s.turn === ME;
// slots that the current selection can act on, as "side:lane"
function targetsNow() {
  const out = new Set();
  if (!ui.sel || !myTurn()) return out;
  const s = ui.s, id = ui.sel.id;
  for (const side of [0, 1]) for (let l = 0; l < LANES; l++) {
    if (CARDS[id].kind === 'Unit' && side === ME && isLegal(s, { t: 'play', card: id, lane: l })) out.add(side + ':' + l);
    if (id === 'H2' && isLegal(s, { t: 'play', card: id, side, lane: l })) out.add(side + ':' + l);
    if (id === 'SF' && side === ME) {
      if (ui.sel.from === undefined) { if (s.p[ME].slots[l] && [0, 1, 2, 3].some(t => isLegal(s, { t: 'play', card: id, from: l, to: t }))) out.add(side + ':' + l); }
      else if (isLegal(s, { t: 'play', card: id, from: ui.sel.from, to: l })) out.add(side + ':' + l);
    }
  }
  return out;
}
const canPlay = (id) => {
  if (!myTurn()) return false;
  const s = ui.s, c = CARDS[id];
  if (c.kind === 'Unit') return [0, 1, 2, 3].some(l => isLegal(s, { t: 'play', card: id, lane: l }));
  if (id === 'H2') return [0, 1].some(side => [0, 1, 2, 3].some(l => isLegal(s, { t: 'play', card: id, side, lane: l })));
  if (id === 'SF') return [0, 1, 2, 3].some(f => [0, 1, 2, 3].some(t => isLegal(s, { t: 'play', card: id, from: f, to: t })));
  return isLegal(s, { t: 'play', card: id });
};

// ------------------------------------------------------------------ rendering
function slotHTML(side, l, T) {
  const m = ui.s.p[side].slots[l];
  let cls = T.has(side + ':' + l) ? ' tgt' : '';
  if (ui.sel && ui.sel.id === 'SF' && ui.sel.from === l && side === ME) cls += ' sel';
  if (!m) return `<div class="slot empty s${side}${cls}" data-side="${side}" data-lane="${l}"></div>`;
  if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
  return `<div class="slot s${side}${cls}" data-side="${side}" data-lane="${l}"><div class="unit s${side}" id="m${m.uid}"><span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div></div>`;
}
function lanesHTML(T) {
  let h = '';
  for (let l = 0; l < LANES; l++) h += `<div class="lane">${slotHTML(BOT, l, T)}${slotHTML(ME, l, T)}</div>`;
  return h;
}
// the scale: the top end is the bot's, the bottom end yours; seat 0 wins at +WIN
function scaleHTML() {
  let cells = '';
  for (let v = -WIN; v <= WIN; v++) cells += `<i class="tick${v === -WIN ? ' endb' : v === WIN ? ' endm' : v === 0 ? ' mid' : ''}"></i>`;
  return `<div class="track">${cells}<div class="marker" id="marker" style="${markerPos(ui.s.scale)}">${Math.abs(ui.s.scale) || ''}</div></div>`;
}
const markerPos = (v) => `top: calc(${((v + WIN) / (2 * WIN)) * 100}% ); --lean: ${v > 0 ? 'var(--me)' : v < 0 ? 'var(--him)' : '#56616d'}`;
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME];
  const order = p.hand.map((_, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]], R = { Coin: 0, Unit: 1, Spell: 2 };
    return R[A.kind] - R[B.kind] || A.cost - B.cost || (A.id < B.id ? -1 : 1);
  });
  return order.map(i => {
    const id = p.hand[i], ok = canPlay(id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.s, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('lanes').innerHTML = lanesHTML(T);
  $('scale').innerHTML = scaleHTML();
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, canAct = mine && !ui.busy && s.p[ME].hand.some(canPlay);
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('field').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(750);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .75}px, ${dy * .75}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: FAST ? 1 : 380, easing: 'ease-in-out' }).finished;
}
function setMarker(v) { const m = $('marker'); if (m) { m.setAttribute('style', markerPos(v)); m.textContent = Math.abs(v) || ''; } }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind !== 'Unit')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  // combat and other in-place effects, on the board as it was
  for (const e of ev) {
    if (e.t === 'strike') {
      const from = $('m' + e.uid), to = e.tuid ? $('m' + e.tuid) : $('marker');
      await lunge(from, to);
      if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
      if (!e.tuid && e.n === 0 && to) floatAt(centerOf(to), '0', 'zero');
    }
    if (e.t === 'hit' && playE === undefined) { const el = $('m' + e.uid); if (el) { floatAt(centerOf(el), '−' + e.n); el.classList.add('shake'); } await wait(120); }
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    if (e.t === 'die' && playE === undefined) { const el = $('m' + e.uid); if (el) el.classList.add('dying'); await wait(260); }
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    if (e.t === 'scale') { const mk = $('marker'); if (mk) floatAt(centerOf(mk), '+' + e.n, e.side === ME ? 'mine' : 'his'); setMarker(e.scale); await wait(e.why === 'lane' ? 260 : 120); }
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    if (e.t === 'empty') { const el = $('res' + e.side); if (el) floatAt(centerOf(el), '∅'); }
  }
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'draw' && e.side === ME) ui.fresh++;
  }
  // a spell's hit shows after the state changes
  const before = {};
  if (playE) for (const e of ev) if (e.t === 'hit') { const el = $('m' + e.uid); if (el) before[e.uid] = centerOf(el); }
  ui.s = next; render();
  if (playE) for (const e of ev) if (e.t === 'hit' && before[e.uid]) floatAt(before[e.uid], '−' + e.n);
  if (playE) {
    const c = CARDS[playE.card];
    let chip = c.kind === 'Unit' ? `${c.atk}/${c.hp}` : c.kind === 'Coin' ? '' : c.name, out = '', cls = '';
    if (c.kind === 'Unit') out = 'L' + (playE.a.lane + 1);
    if (playE.card === 'H2') { out = ev.some(e => e.t === 'die') ? '✕' : '−2'; cls = 'kill'; }
    if (playE.card === 'SF') out = (playE.a.from + 1) + '→' + (playE.a.to + 1);
    if (playE.card === 'SV') { out = '+1'; cls = 'face'; }
    ui.hist.push({ side: playE.side, kind: c.kind, chip, out, cls });
  }
  if (a.t === 'end') {
    const tipN = ev.filter(e => e.t === 'scale' && e.why === 'lane').reduce((n, e) => n + e.n, 0), kills = ev.filter(e => e.t === 'die').length;
    ui.hist.push({ side: prev.turn, kind: 'Attack', chip: '', out: (tipN ? '+' + tipN : '') + (kills ? ' ' + '✕'.repeat(kills) : '') || '·', cls: tipN ? 'face' : 'kill' });
  }
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
  ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  while (!ui.over && ui.s.turn === BOT) {
    await wait(380);
    if (tok !== ui.token || ui.over) return;
    const t0 = performance.now(), a = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(a);
    if (tok !== ui.token) return;
  }
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn() || !isLegal(ui.s, a)) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  if (!ui.over && ui.s.turn === BOT) return botMove(tok);
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (b0 && b0.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const slot = e.target.closest('.slot');
  if (slot && myTurn() && ui.sel && slot.classList.contains('tgt')) {
    const side = +slot.dataset.side, l = +slot.dataset.lane, id = ui.sel.id;
    if (CARDS[id].kind === 'Unit') return doAct({ t: 'play', card: id, lane: l });
    if (id === 'H2') return doAct({ t: 'play', card: id, side, lane: l });
    if (id === 'SF') { if (ui.sel.from === undefined) { ui.sel.from = l; render(); return; } return doAct({ t: 'play', card: id, from: ui.sel.from, to: l }); }
  }
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = ui.s.p[ME].hand[i];
    if (CARDS[id].kind === 'Unit' || id === 'H2' || id === 'SF') { ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b0 && !b0.disabled && b0.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
