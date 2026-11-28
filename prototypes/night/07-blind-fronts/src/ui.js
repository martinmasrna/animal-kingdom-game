// Blind fronts as a game screen against Expert. Your cards sit face-up on your side of each
// front, the bot's face-down with the energy it paid; at the reveal both sides turn over.

import { CARDS, CAP, TARGET, HAND_MAX, FRONTS, newMatch, act, isLegal, frontStrength } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-07-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, sel: null, hist: [], reveal: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, fresh: 0, popped: null };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '', tag = 'button' } = {}) {
  const c = CARDS[id];
  return `<${tag} class="card s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><span class="str">${c.str}</span><span class="nm">${c.name}</span>${c.text ? `<span class="tx">${c.text}</span>` : ''}</${tag}>`;
}
const backHTML = (cost, cls = '') => `<div class="fd ${cls}"><span class="cgem">${cost}</span></div>`;

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && !ui.reveal && ui.s.toMove === ME;
const discarding = () => myTurn() && ui.s.phase === 'discard';
const canPlace = (id) => myTurn() && ui.s.phase === 'place' && isLegal(ui.s, { t: 'place', card: id, front: 0 });

// ------------------------------------------------------------------ rendering
function frontsHTML() {
  const s = ui.s, R = ui.reveal;
  let h = '';
  for (let f = 0; f < FRONTS; f++) {
    const tgt = ui.sel && myTurn() && !discarding() ? ' tgt' : '';
    const his = R ? R.res[f].cards[BOT].map(id => cardHTML(id, BOT, { tag: 'div', cls: 'mini up' })).join('')
      : s.p[BOT].placed[f].map((id, i) => backHTML(CARDS[id].cost, ui.popped === `${f}:${i}` ? 'pop' : '')).join('');
    const mine = (R ? R.res[f].cards[ME] : s.p[ME].placed[f]).map(id => cardHTML(id, ME, { tag: 'div', cls: 'mini' })).join('');
    const val = R ? R.res[f].value : s.values[f];
    let mid = `<div class="val">${val}</div>`;
    if (R) {
      const r = R.res[f];
      mid = `<div class="tot s1${r.winner === BOT ? ' won' : ''}">${r.str[BOT]}</div><div class="val${r.winner === ME ? ' me' : r.winner === BOT ? ' him' : ' tie'}">${val}</div><div class="tot s0${r.winner === ME ? ' won' : ''}">${r.str[ME]}</div>`;
    }
    h += `<div class="front${tgt}" data-front="${f}"><div class="side s1">${his}</div><div class="mid">${mid}</div><div class="side s0">${mine}</div></div>`;
  }
  return h;
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < CAP; i++) gems += `<i class="gemc${i < p.energy ? ' on' : ''}"></i>`;
  return `<div class="mana${p.passed && !ui.reveal ? ' passed' : ''}"><span class="manatxt">${p.energy}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function scoresHTML() {
  const sc = ui.reveal ? ui.reveal.score : ui.s.p.map(p => p.score);
  const bar = (side) => `<div class="sc s${side}"><b>${sc[side]}</b><span class="bar"><i style="width:${Math.min(100, sc[side] / TARGET * 100)}%"></i></span></div>`;
  return bar(BOT) + bar(ME);
}
function handHTML() {
  const p = ui.s.p[ME];
  const order = p.hand.map((_, i) => i).sort((a, b) => CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost || CARDS[p.hand[a]].str - CARDS[p.hand[b]].str || (p.hand[a] < p.hand[b] ? -1 : 1));
  const toss = discarding();
  return order.map(i => {
    const id = p.hand[i], ok = toss || canPlace(id);
    let cls = toss ? 'toss' : ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist"><span class="rn">${h.round}</span><b class="p0">+${h.pts[ME]}</b><b class="p1">+${h.pts[BOT]}</b></div>`; }
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = `<div class="backs${s.p[BOT].passed && !ui.reveal ? ' passed' : ''}">${'<i class="back"></i>'.repeat(s.p[BOT].hand.length)}</div>`;
  $('fronts').innerHTML = frontsHTML();
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('scores').innerHTML = scoresHTML();
  $('hand').innerHTML = handHTML();
  const mine = myTurn() && s.phase === 'place';
  $('turnbox').innerHTML = `<button id="pass"${mine ? '' : ' disabled'}>Pass</button>`;
  $('history').innerHTML = ui.hist.slice(-12).map(histHTML).join('');
  ui.fresh = 0; ui.popped = null;
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1300); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const rev = ev.find(e => e.t === 'reveal');
  const placeE = ev.find(e => e.t === 'place');
  if (placeE && placeE.side === BOT) ui.popped = `${placeE.front}:${next.p[BOT].placed[placeE.front]?.length - 1}`;
  if (rev) {
    // a reveal always follows a pass: show the round as it stood, everything face-up with totals,
    // then the next round
    ui.s = prev; ui.reveal = rev; render();
    for (const r of rev.res) if (r.winner !== null) { const el = document.querySelector(`.front[data-front="${r.front}"] .val`); if (el) floatAt(centerOf(el), '+' + r.value, r.winner === ME ? 'mine' : 'his'); }
    ui.hist.push({ round: prev.round, pts: [0, 1].map(k => rev.res.reduce((n, r) => n + (r.winner === k ? r.value : 0), 0)) });
    await wait(2600);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    ui.reveal = null;
  }
  ui.fresh = ev.filter(e => e.t === 'draw' && e.side === ME).length;
  ui.s = next;
  const roundE = ev.find(e => e.t === 'round');
  if (next.winner !== null) { render(); finish(); return; }
  if (roundE) banner('Round ' + roundE.round);
  render();
}

function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="final">${ui.s.p[ME].score} – ${ui.s.p[BOT].score}</div><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null; ui.reveal = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner('Round 1');
  await wait(900);
  if (tok !== ui.token) return;
  await botLoop(tok);
}
async function botLoop(tok) {
  ui.busy = true; render();
  while (!ui.over && ui.s.toMove === BOT) {
    await wait(520);
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
  await botLoop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (b0 && b0.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const fr = e.target.closest('.front');
  if (fr && ui.sel && fr.classList.contains('tgt')) return doAct({ t: 'place', card: ui.sel.id, front: +fr.dataset.front });
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = ui.s.p[ME].hand[i];
    if (discarding()) return doAct({ t: 'discard', card: id });
    ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return;
  }
  if (b0 && !b0.disabled && b0.id === 'pass') return doAct({ t: 'pass' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
