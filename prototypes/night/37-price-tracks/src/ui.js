// 37 Price tracks as a game screen against Expert. Three price tracks in the middle; tap goods
// cards of one type, then that track, to sell them; tap Boost or Crash, then a track. Each action
// is animated from the state before and the state after; the win tally decides who goes first.

import { CARDS, GOODS, TARGET, ROUNDS, COIN_CAP, PMAX, newMatch, act, legalActions, counts } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-37-tally';
const expert = expertBot({ ...EXPERT, timeMs: 1300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const ART = { BOO: '+2', CRA: '−3', SPY: '◉' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  if (c.kind === 'good') return `<button class="card good g${id} ${cls}" ${attrs}><div class="art"><span class="big">${id}</span></div></button>`;
  return `<button class="card ${c.kind} ${cls}" ${attrs}><span class="cgem coin">${c.cost}</span><div class="art"><span class="big">${ART[id]}</span></div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function selGood() { return ui.sel && ui.sel.kind === 'goods' ? ui.view.p[ME].hand[ui.sel.idx[0]] : null; }
function targetsNow() {
  const out = new Set();
  if (!ui.sel || !myTurn()) return out;
  const legal = legalActions(ui.view);
  if (ui.sel.kind === 'goods') { const g = selGood(); if (legal.some(a => a.t === 'sell' && a.good === g)) out.add(g); }
  else for (const a of legal) if (a.t === 'play' && a.card === ui.sel.id && a.good) out.add(a.good);
  return out;
}

// ------------------------------------------------------------------ rendering
function scoreHTML(side) {
  const p = ui.view.p[side];
  let coins = '';
  for (let i = 0; i < COIN_CAP; i++) coins += `<i class="coin${i < p.coin ? ' on' : ''}"></i>`;
  return `<div class="score s${side} ${ui.fx['pts' + side] || ''}" id="pts${side}"><b>${p.pts}</b><span class="bar"><i style="width:${Math.min(100, p.pts / TARGET * 100)}%"></i></span></div><div class="coins">${coins}</div>`;
}
function fieldHTML(T) {
  return GOODS.map(g => {
    const p = ui.view.price[g];
    let cells = '';
    for (let v = PMAX; v >= 1; v--) cells += `<i class="cell${v === 4 ? ' start' : ''}"></i>`;
    return `<div class="track g${g}${T.has(g) ? ' tgt' : ''}" data-good="${g}">${cells}<div class="tok g${g} ${ui.fx['p' + g] || ''}" id="p${g}" style="--r:${PMAX - p}"><span>${p}</span></div><div class="lbl g${g}">${g}</div></div>`;
  }).join('');
}
function oppHandHTML() {
  const O = ui.view.p[BOT], seen = O.seen.slice();
  return O.hand.map(id => { const k = seen.indexOf(id); if (k >= 0) { seen.splice(k, 1); return cardHTML(id, BOT, { cls: 'mini seen' }); } return '<i class="back"></i>'; }).join('');
}
function handHTML(T) {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const order = p.hand.map((_, i) => i).sort((a, b) => (p.hand[a] < p.hand[b] ? -1 : p.hand[a] > p.hand[b] ? 1 : a - b));
  return order.map(i => {
    const id = p.hand[i], c = CARDS[id];
    const ok = c.kind === 'good' ? legal.some(a => a.t === 'sell' && a.good === id) : legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ui.sel && ((ui.sel.kind === 'goods' && ui.sel.idx.includes(i)) || (ui.sel.kind === 'card' && ui.sel.hand === i))) cls += ' sel';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = oppHandHTML();
  for (const side of [0, 1]) $('hero' + side).innerHTML = scoreHTML(side);
  $('field').innerHTML = fieldHTML(T);
  $('res1').innerHTML = `<div class="pile s1">${s.p[BOT].deck.length}</div><div class="pile disc s1">${s.p[BOT].disc.length}</div>`;
  $('res0').innerHTML = `<div class="pile s0">${s.p[ME].deck.length}</div><div class="pile disc s0">${s.p[ME].disc.length}</div>`;
  $('round').innerHTML = `${s.round}<small>/${ROUNDS}</small>`;
  $('hand').innerHTML = handHTML(T);
  $('turnbox').innerHTML = `<button id="endturn"${!ui.over && s.toAct === ME && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(html) {
  const g = $('game').getBoundingClientRect(), b = $('field').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = `<div class="spotrow">${html}</div>`;
  await wait(750);
  const c = $('spot').querySelector('.spotrow'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const sellE = ev.find(e => e.t === 'sell'), playE = ev.find(e => e.t === 'play'), roundE = ev.find(e => e.t === 'round');
  if (sellE && sellE.side === BOT) await spotlight(Array.from({ length: sellE.n }, () => cardHTML(sellE.good, BOT)).join(''));
  if (playE && playE.side === BOT) await spotlight(cardHTML(playE.card, BOT));
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'price' || e.t === 'sell') ui.fx['p' + (e.good)] = 'moved';
    if (e.t === 'sell') ui.fx['pts' + e.side] = 'bump';
  }
  const before = { pts0: centerOf($('pts0')), pts1: centerOf($('pts1')) };
  ui.view = next; render();
  if (sellE) floatAt(before['pts' + sellE.side], '+' + sellE.gain, 'gain');
  if (sellE) ui.hist.push({ side: sellE.side, kind: 'g' + sellE.good, chip: sellE.n + '×' + sellE.good, out: '+' + sellE.gain, cls: 'gain' });
  if (playE) ui.hist.push({ side: playE.side, kind: CARDS[playE.card].kind, chip: ART[playE.card], out: playE.good || '' });
  if (roundE) { await wait(300); for (const g of GOODS) ui.fx['p' + g] = 'moved'; render(); }
  if (ev.some(e => e.t === 'turn')) await wait(next.toAct === ME ? 600 : 250);
  if (next.winner !== null) finish();
  render();
}
function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p>${ui.s.p[ME].pts} – ${ui.s.p[BOT].pts}</p><button id="rematch">Play again</button>`;
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
  for (let k = 0; k < 40; k++) {
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
  if (tr && T.has(tr.dataset.good)) {
    if (ui.sel.kind === 'goods') return doAct({ t: 'sell', good: tr.dataset.good, n: ui.sel.idx.length });
    return doAct({ t: 'play', card: ui.sel.id, good: tr.dataset.good });
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], c = CARDS[id];
    if (c.kind === 'spy') return doAct({ t: 'play', card: id });
    if (c.kind === 'good') {
      if (!ui.sel || ui.sel.kind !== 'goods' || selGood() !== id) {
        // the first tap on a type takes every card of it; later taps take one off or put one back
        ui.sel = { kind: 'goods', idx: ui.view.p[ME].hand.map((x, k) => x === id ? k : -1).filter(k => k >= 0) };
      } else {
        const k = ui.sel.idx.indexOf(i);
        if (k >= 0) ui.sel.idx.splice(k, 1); else ui.sel.idx.push(i);
        if (!ui.sel.idx.length) ui.sel = null;
      }
      render(); return;
    }
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled && b.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.__game = { get s() { return ui.s; }, get busy() { return ui.busy; }, get over() { return ui.over; } };
startMatch();
