// Costed tricks as a game screen against Expert. The prize row shows what each trick is worth
// and who took it; pick a card, then play it face-up (paying its cost) or face-down.

import { SUITS, HAND, ENERGY, TARGET, suitOf, rankOf, costOf, newMatch, act, isLegal } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-38-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, sel: null, hist: [], table: null, won: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const suitIcon = { A: '●', B: '■', C: '▲', D: '◆' };
function cardHTML(c, { cls = '', attrs = '', tag = 'button' } = {}) {
  const trump = ui.s && suitOf(c) === ui.s.trump ? ' trump' : '';
  return `<${tag} class="card su${suitOf(c)}${trump} ${cls}" ${attrs}><span class="cgem">${costOf(c)}</span><span class="rk">${rankOf(c)}</span><span class="si">${suitIcon[suitOf(c)]}</span></${tag}>`;
}
const backHTML = (cls = '') => `<div class="card back ${cls}"></div>`;

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.s.toMove === ME;
const canUp = (c) => myTurn() && isLegal(ui.s, { t: 'play', card: c, up: true });
const canDown = (c) => myTurn() && isLegal(ui.s, { t: 'play', card: c, up: false });

// ------------------------------------------------------------------ rendering
function prizesHTML() {
  const s = ui.s;
  return `<div class="trumpbox su${s.trump}"><span class="si">${suitIcon[s.trump]}</span></div>` + s.prizes.map((v, i) => {
    const w = ui.won[i];
    const cls = w === ME ? ' w0' : w === BOT ? ' w1' : i === s.trick && !ui.over ? ' now' : i < s.trick ? ' gone' : '';
    return `<span class="prize${cls}">${v}</span>`;
  }).join('');
}
function trickHTML() {
  const T = ui.table;
  if (!T) return '';
  const one = (x) => !x ? '<div class="slotc"></div>' : x.up ? cardHTML(x.card, { tag: 'div', cls: 'big s' + x.side + (T.winner === x.side ? ' win' : T.winner !== undefined ? ' lose' : '') })
    : backHTML('big s' + x.side + (T.winner === x.side ? ' win' : T.winner !== undefined ? ' lose' : ''));
  // the bot's card above, mine below
  const his = T.led && T.led.side === BOT ? T.led : T.fol && T.fol.side === BOT ? T.fol : null;
  const mine = T.led && T.led.side === ME ? T.led : T.fol && T.fol.side === ME ? T.fol : null;
  return `<div class="tc">${one(his)}${one(mine)}</div>`;
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < ENERGY; i++) gems += `<i class="gemc${i < p.energy ? ' on' : ''}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.energy}</span>${gems}</div>`;
}
function scoresHTML() {
  const bar = (side) => { const v = ui.s.p[side].score; return `<div class="sc s${side}"><b>${v}</b><span class="bar"><i style="width:${Math.min(100, v / TARGET * 100)}%"></i></span></div>`; };
  return bar(BOT) + bar(ME);
}
function handHTML() {
  const p = ui.s.p[ME];
  const order = p.hand.slice().sort((a, b) => (suitOf(a) === ui.s.trump) - (suitOf(b) === ui.s.trump) || SUITS.indexOf(suitOf(a)) - SUITS.indexOf(suitOf(b)) || rankOf(a) - rankOf(b));
  return order.map(c => {
    const ok = canUp(c) || canDown(c);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ui.sel === c) cls += ' sel';
    return cardHTML(c, { cls, attrs: `data-card="${c}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist"><span class="rn">${h.hand}</span><b class="p0">+${h.pts[ME]}</b><b class="p1">+${h.pts[BOT]}</b></div>`; }
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="bk"></i>'.repeat(s.p[BOT].hand.length);
  $('prizes').innerHTML = prizesHTML();
  $('trick').innerHTML = trickHTML();
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('scores').innerHTML = scoresHTML();
  $('hand').innerHTML = handHTML();
  const c = ui.sel;
  $('turnbox').innerHTML = `<button id="up"${c && canUp(c) ? '' : ' disabled'}>Face up</button><button id="down"${c && canDown(c) ? '' : ' disabled'}>Face down</button>`;
  $('history').innerHTML = ui.hist.slice(-10).map(histHTML).join('');
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play'), trickE = ev.find(e => e.t === 'trick'), handE = ev.find(e => e.t === 'hand');
  const shown = { side: playE.side, card: playE.side === ME ? playE.own : playE.card, up: playE.up };
  if (!prev.led) { ui.table = { led: shown }; ui.s = next; render(); return finishCheck(next); }
  ui.table.fol = shown;
  if (trickE) {
    // the finished trick stays up a moment with its winner lit, the prize going to the winner
    ui.table.winner = trickE.winner;
    ui.s = { ...prev, p: prev.p.map((p, k) => ({ ...p, score: trickE.score[k], energy: k === playE.side ? p.energy - playE.cost : p.energy, hand: k === playE.side ? p.hand.filter(c => c !== playE.own) : p.hand })) };
    ui.won[trickE.trick] = trickE.winner;
    render();
    const pz = document.querySelectorAll('.prize')[trickE.trick];
    if (pz) floatAt(centerOf(pz), '+' + trickE.prize, trickE.winner === ME ? 'mine' : 'his');
    await wait(1100);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    ui.table = null;
  }
  if (handE) {
    ui.hist.push({ hand: prev.hand, pts: [0, 1].map(k => ui.won.reduce((n, w, i) => n + (w === k ? prev.prizes[i] : 0), 0)) });
    ui.won = [];
  }
  ui.s = next; render();
  if (handE) banner('Hand ' + handE.hand);
  finishCheck(next);
}
function finishCheck(next) { if (next.winner !== null) finish(); }

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
  ui.over = false; ui.hist = []; ui.sel = null; ui.table = null; ui.won = [];
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner('Hand 1');
  await wait(900);
  if (tok !== ui.token) return;
  await botLoop(tok);
}
async function botLoop(tok) {
  ui.busy = true; render();
  while (!ui.over && ui.s.toMove === BOT) {
    await wait(550);
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
  if (b0 && !b0.disabled && b0.dataset.card) {
    const c = b0.dataset.card;
    // a card with one way to play goes at once; otherwise it is picked and the two buttons decide
    if (canUp(c) !== canDown(c)) return doAct({ t: 'play', card: c, up: canUp(c) });
    ui.sel = ui.sel === c ? null : c; render(); return;
  }
  if (b0 && !b0.disabled && (b0.id === 'up' || b0.id === 'down') && ui.sel) return doAct({ t: 'play', card: ui.sel, up: b0.id === 'up' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
