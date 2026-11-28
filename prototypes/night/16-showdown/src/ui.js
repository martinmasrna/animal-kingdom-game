// Showdown as a game screen against Expert. You pick up to 3 cards from your hand and buy them
// as your line; the bot's line lies face-down with the mana it cost beside it; then you bet.
// At a showdown both lines turn over with their totals before the next round is dealt.

import { CARDS, MANA, BET, ROUNDS, newMatch, act, isLegal, legalActions, lineCost, linePower, ante } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-16-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, pick: [], reveal: null, say: [null, null], hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, { cls = '', attrs = '', line = null } = {}) {
  const c = CARDS[id];
  const pw = id === 'MR' ? 'M' : id === 'SO' ? (line && line.length > 1 ? 0 : 4) : c.power;
  const tx = c.text ? `<div class="tx">${c.text}</div>` : '';
  return `<button class="card ${id} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="pw">${pw}</span></div><div class="nm">${c.name}</div>${tx}</button>`;
}
const down = (side) => `<div class="card down s${side}"></div>`;

const myMove = () => !ui.busy && !ui.over && ui.s.toMove === ME;
const pickCost = () => lineCost(ui.pick.map(i => ui.s.p[ME].hand[i]));

// ------------------------------------------------------------------ rendering
function lineHTML(side) {
  const s = ui.s, r = ui.reveal;
  if (r) {
    const line = r.lines[side];
    if (r.folder === side && side === BOT) return line.map(() => down(side)).join('');
    return `${r.shown ? `<span class="total">${r.power[side]}</span>` : ''}${line.map(id => cardHTML(id, { line, attrs: 'disabled' })).join('')}`;
  }
  const P = s.p[side];
  if (!P.line) return '';
  const spent = s.phase === 'bet' ? `<span class="spent">${P.spent}<i></i></span>` : '';
  if (side === BOT) return P.line.map(() => down(side)).join('') + spent;
  return P.line.map(id => cardHTML(id, { line: P.line, attrs: 'disabled' })).join('') + spent;
}
function handHTML() {
  const P = ui.s.p[ME], buying = myMove() && ui.s.phase === 'buy';
  const order = P.hand.map((_, i) => i).sort((a, b) => CARDS[P.hand[a]].cost - CARDS[P.hand[b]].cost || (P.hand[a] < P.hand[b] ? -1 : 1));
  return order.map(i => {
    const id = P.hand[i], on = ui.pick.includes(i);
    const ok = buying && (on || (ui.pick.length < 3 && pickCost() + CARDS[id].cost <= MANA));
    const cls = (on ? 'sel ' : '') + (ok ? 'ok' : buying ? 'no' : '');
    return cardHTML(id, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function controlsHTML() {
  const s = ui.s;
  if (!myMove()) return '';
  if (s.phase === 'buy') return `<button id="buy" class="main">Buy</button>`;
  const f = s.p[BOT].contrib - s.p[ME].contrib;
  const label = { check: 'Check', bet: 'Bet ' + BET, call: 'Call ' + Math.min(f, s.p[ME].chips), raise: 'Raise ' + (f + BET), fold: 'Fold' };
  return legalActions(s).map(a => `<button data-bet="${a.t}" class="${a.t === 'bet' || a.t === 'raise' ? 'main' : a.t === 'fold' ? 'fold' : ''}">${label[a.t]}</button>`).join('');
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  let pips = '';
  for (let r = 1; r <= ROUNDS; r++) pips += `<i class="pip a${ante(r)}${r < s.round ? ' done' : r === s.round ? ' now' : ''}"></i>`;
  $('rounds').innerHTML = pips;
  for (const side of [0, 1]) {
    $('chips' + side).textContent = s.p[side].chips;
    $('line' + side).innerHTML = lineHTML(side);
    $('line' + side).classList.toggle('won', !!ui.reveal && (ui.reveal.winner === side || ui.reveal.winner === 'split'));
    const say = ui.say[side], el = $('say' + side);
    el.className = 'say' + (say ? ' on ' + say : ''); el.textContent = say ? { check: 'Check', bet: 'Bet', call: 'Call', raise: 'Raise', fold: 'Fold' }[say] : '';
  }
  $('backs1').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('pot').textContent = ui.reveal ? ui.reveal.pot : s.pot;
  const buying = myMove() && s.phase === 'buy';
  let gems = '';
  if (buying) { const c = pickCost(); for (let i = 0; i < MANA; i++) gems += `<i class="gem${i < MANA - c ? '' : ' off'}"></i>`; }
  $('buybar').innerHTML = gems;
  $('hand').innerHTML = handHTML();
  $('controls').innerHTML = controlsHTML();
  $('history').innerHTML = ui.hist.slice(-16).map(h => `<div class="hist"><span class="r">${h.r}</span><span class="${h.cls}">${h.txt}</span></div>`).join('');
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function floatAt(el, text, neg) {
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), f = document.createElement('div');
  f.className = 'float' + (neg ? ' neg' : ''); f.textContent = text; f.style.left = (r.left - g.left + r.width / 2) + 'px'; f.style.top = (r.top - g.top + r.height / 2) + 'px';
  $('game').appendChild(f); setTimeout(() => f.remove(), 1200);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const side = prev.toMove;
  if (a.t !== 'buy') ui.say[side] = a.t;
  const st = ev.find(e => e.t === 'settle');
  if (st) {
    // the round's end: both lines (or the folded one face-down), the pot to the winner
    ui.s = next; ui.reveal = st; ui.say = st.how === 'fold' ? ui.say : [null, null];
    // each side's chips from before the round's bets to after the pot (and any Spike) was paid
    const fresh = ev.some(e => e.t === 'round');
    const net = [0, 1].map(k => (next.p[k].chips + (fresh ? next.p[k].contrib : 0)) - (prev.p[k].chips + prev.p[k].contrib));
    render();
    for (const k of [0, 1]) if (net[k]) floatAt($('chips' + k), (net[k] > 0 ? '+' : '−') + Math.abs(net[k]), net[k] < 0);
    ui.hist.push({ r: prev.round, txt: (net[ME] > 0 ? '+' : net[ME] < 0 ? '−' : '±') + Math.abs(net[ME]) + (st.how === 'fold' ? ' fold' : ''), cls: st.winner === ME ? 'w0' : st.winner === BOT ? 'w1' : 'sp' });
    await wait(st.how === 'show' ? 2200 : 1200);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    ui.reveal = null; ui.say = [null, null];
    if (next.winner !== null) return finish();
    if (next.round !== prev.round) banner('Round ' + next.round);
    render();
    return;
  }
  ui.s = next; render();
  if (ev.some(e => e.t === 'spent')) await wait(400);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (next.winner !== null) finish();
}

function finish() {
  if (ui.over) return;
  ui.over = true; render();
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
  ui.over = false; ui.hist = []; ui.pick = []; ui.reveal = null; ui.say = [null, null];
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner('Round 1');
  await wait(700);
  if (tok !== ui.token) return;
  await settleTurn(tok);
}
async function settleTurn(tok) {
  while (!ui.over && ui.s.toMove === BOT) {
    ui.busy = true; render();
    await wait(450);
    if (tok !== ui.token || ui.over) return;
    const t0 = performance.now(), a = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(a);
    if (tok !== ui.token) return;
  }
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myMove() || !isLegal(ui.s, a)) return;
  const tok = ui.token;
  ui.busy = true; ui.pick = [];
  await apply(a);
  if (tok !== ui.token) return;
  await settleTurn(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (b && b.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  if (!b || b.disabled || !myMove()) return;
  if (b.dataset.hand !== undefined) { const i = +b.dataset.hand, k = ui.pick.indexOf(i); if (k >= 0) ui.pick.splice(k, 1); else ui.pick.push(i); render(); return; }
  if (b.id === 'buy') return doAct({ t: 'buy', line: ui.pick.map(i => ui.s.p[ME].hand[i]) });
  if (b.dataset.bet) return doAct({ t: b.dataset.bet });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('rules').classList.remove('show'); } });
startMatch();
