// 44 Bump placement as a game screen against the Expert. Each action is animated from the state
// before and the state after; the round's payout plays space by space; the win tally is kept in
// this browser and decides who starts round 1.

import { CARDS, SPACES, TARGET, BASE_MANA, FUND, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-44-tally';
const expert = expertBot({ ...EXPERT, playouts: 2400, timeMs: 1200 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const TXT = { LOC: "Can't be bumped", SHO: 'Also bumps a 3 or less elsewhere' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  return `<button class="card s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="big">${c.str}</span></div><div class="nm">${c.name}</div>${TXT[id] ? `<div class="tx">${TXT[id]}</div>` : ''}</button>`;
}
const placedHTML = (x, k, cls = '') => `<div class="placed s${x.side} ${cls}" id="pl${k}" data-space="${k}"><span class="pstr">${CARDS[x.card].str}</span><span class="pnm">${CARDS[x.card].name}</span></div>`;

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function legalFor(sel) { return myTurn() && sel ? legalActions(ui.view).filter(a => a.t === 'place' && a.card === sel.id) : []; }

// ------------------------------------------------------------------ rendering
function spacesHTML() {
  const s = ui.view, L = legalFor(ui.sel);
  const open = new Set(L.map(a => a.space)), shove = ui.sel && ui.sel.space !== undefined ? new Set(L.filter(a => a.space === ui.sel.space).map(a => a.tgt)) : new Set();
  return SPACES.map((sp, k) => {
    const x = s.spaces[k];
    let cls = '';
    if (ui.sel && ui.sel.space === undefined && open.has(k)) cls += ' dest';
    if (ui.sel && ui.sel.space === k) cls += ' chosen';
    if (ui.fx['sp' + k]) cls += ' ' + ui.fx['sp' + k];
    const inner = x ? placedHTML(x, k, shove.has(k) ? 'tgt' : '') : '';
    return `<div class="space${cls}" data-space="${k}"><div class="sh"><b>${sp.name}</b><span>${sp.text}</span></div><div class="slot">${inner}</div></div>`;
  }).join('');
}
function infoHTML(side) {
  const s = ui.view, p = s.p[side];
  const pct = Math.min(100, p.points / TARGET * 100);
  let gems = '';
  const cap = BASE_MANA + FUND;
  for (let i = 0; i < cap; i++) gems += `<i class="gemc${i < p.mana ? ' on' : ''}${i >= BASE_MANA && !(p.mana > BASE_MANA) && i >= p.mana ? ' off' : ''}"></i>`;
  const passed = p.passed && s.phase === 'place' ? ' passed' : '';
  return `<div class="score s${side} ${ui.fx['score' + side] || ''}" id="score${side}"><span class="pn">${p.points}</span><span class="bar"><i style="width:${pct}%"></i></span></div>
    <div class="mana${passed}"><span class="manatxt">${p.mana}</span>${gems}</div>${p.fund ? '<span class="fund">+3</span>' : ''}
    <div class="piles"><div class="pile s${side}">${p.deck.length}</div><div class="pile disc">${p.discard.length}</div></div>`;
}
function handHTML() {
  const s = ui.view, p = s.p[ME], legal = myTurn() ? legalActions(s) : [];
  const order = p.hand.map((_, i) => i).sort((a, b) => CARDS[p.hand[a]].str - CARDS[p.hand[b]].str || CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost);
  return order.map(i => {
    const id = p.hand[i];
    const ok = s.phase === 'discard' ? myTurn() : legal.some(a => a.t === 'place' && a.card === id);
    let cls = ok ? (s.phase === 'discard' ? 'ok disc' : 'ok') : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    if (ui.fx['h' + i]) cls += ' ' + ui.fx['h' + i];
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
const histHTML = (h) => `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`;
function render() {
  const s = ui.view;
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="cb"></i>'.repeat(s.p[BOT].hand.length);
  $('spaces').innerHTML = spacesHTML();
  for (const side of [0, 1]) $('info' + side).innerHTML = infoHTML(side);
  $('hand').innerHTML = handHTML();
  const mine = myTurn();
  const roundBox = `<div class="round">${s.round}<small>/12</small></div>`;
  if (s.phase === 'discard' && s.toAct === ME) $('turnbox').innerHTML = `${roundBox}<div class="discn">−${s.p[ME].hand.length - 8}</div>`;
  else $('turnbox').innerHTML = `${roundBox}<button id="pass" class="${mine && !legalActions(s).some(a => a.t === 'place') ? 'done' : ''}"${mine ? '' : ' disabled'}>Pass</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
// a bumped card flies back toward its owner's side
function flyBack(fromEl, side) {
  if (!fromEl) return;
  const g = $('game').getBoundingClientRect(), r = fromEl.getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = fromEl.outerHTML; d.style.left = (r.left - g.left) + 'px'; d.style.top = (r.top - g.top) + 'px'; d.style.width = r.width + 'px'; d.style.height = r.height + 'px';
  $('game').appendChild(d);
  const to = side === ME ? $('hand') : $('opphand'), t = to.getBoundingClientRect();
  d.animate([{ transform: 'translate(0,0)', opacity: 1 }, { transform: `translate(${t.left + t.width / 2 - r.left - r.width / 2}px, ${t.top + t.height / 2 - r.top - r.height / 2}px) scale(.5)`, opacity: .2 }], { duration: 500, easing: 'ease-in' });
  setTimeout(() => d.remove(), 480);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const placeE = ev.find(e => e.t === 'place'), bumps = ev.filter(e => e.t === 'bump');
  // bumps: the old card leaves first
  for (const b of bumps) flyBack($('pl' + b.space), b.side);
  if (placeE) {
    const c = CARDS[placeE.card];
    ui.hist.push({ side: placeE.side, kind: 'pl', chip: c.str, out: SPACES[placeE.space].name + (bumps.length ? ' ✕' + bumps.map(b => CARDS[b.card].str).join(' ✕') : ''), cls: bumps.length ? 'kill' : '' });
    ui.fx['sp' + placeE.space] = 'land';
  }
  if (a.t === 'pass') ui.hist.push({ side: prev.toAct, kind: 'pass', chip: '–' });
  if (a.t === 'discard') ui.hist.push({ side: prev.toAct, kind: 'disc', chip: CARDS[a.card].str, out: '↓' });
  // the payout, space by space, on the board as it stood
  const payIdx = ev.findIndex(e => e.t === 'payout');
  if (payIdx >= 0) {
    const mid = { ...prev, spaces: prev.spaces.map(x => x), p: prev.p.map(p => ({ ...p })) };
    if (placeE) mid.spaces[placeE.space] = { card: placeE.card, side: placeE.side };
    mid.p[prev.toAct] = { ...mid.p[prev.toAct], passed: true };
    ui.view = mid; render();
    await wait(450);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    for (const e of ev.slice(payIdx)) {
      if (e.space === undefined) continue;
      const el = document.querySelector(`.space[data-space="${e.space}"]`);
      if (el) { el.classList.add('pay'); const txt = e.t === 'gain' ? '+' + e.n : e.t === 'study' ? '+2 cards' : e.t === 'fund' ? '+3 mana' : '−1 card'; floatAt(centerOf(el), txt, e.t === 'gain' ? 'gain' : 'meta'); }
      if (e.t === 'gain') { mid.p[e.side] = { ...mid.p[e.side], points: e.points }; ui.view = mid; render(); const el2 = document.querySelector(`.space[data-space="${e.space}"]`); if (el2) el2.classList.add('pay'); }
      if (e.t === 'gain' || e.t === 'study' || e.t === 'fund' || e.t === 'sabotage') ui.hist.push({ side: e.t === 'sabotage' ? 1 - e.side : e.side, kind: 'pay', chip: SPACES[e.space].name.replace('Score ', '+'), out: e.t === 'sabotage' ? '−' + CARDS[e.card].name : '', cls: 'face' });
      await wait(650);
      if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    }
  }
  ui.view = next; render();
  if (ev.some(e => e.t === 'round') && next.winner === null) { banner('Round ' + next.round); await wait(700); }
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
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="final">${ui.s.p[ME].points} – ${ui.s.p[BOT].points}</div><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner('Round 1');
  await wait(900);
  if (tok !== ui.token) return;
  await botLoop(tok);
}
// the bot acts while it is its move, one action at a time, each shown before the next is chosen
async function botLoop(tok) {
  ui.busy = true; render();
  for (let k = 0; k < 200; k++) {
    if (tok !== ui.token || ui.over || ui.s.winner !== null || ui.s.toAct !== BOT) break;
    await wait(300);
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
  if (tok !== ui.token || ui.over) return;
  await botLoop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.add('show'); return; }
  if (e.target.closest('#rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  const b = e.target.closest('button');
  if (b && !b.disabled && (b.id === 'rematch' || b.id === 'newgame')) return startMatch();
  if (!myTurn()) return;
  const s = ui.view;
  if (b && b.id === 'pass') return doAct({ t: 'pass' });
  if (b && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = s.p[ME].hand[i];
    if (s.phase === 'discard') return doAct({ t: 'discard', card: id });
    ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return;
  }
  // a Shove's target: an enemy card that glows
  const pl = e.target.closest('.placed.tgt');
  if (pl && ui.sel && ui.sel.space !== undefined) return doAct({ t: 'place', card: ui.sel.id, space: ui.sel.space, tgt: +pl.dataset.space });
  const sp = e.target.closest('.space.dest');
  if (sp && ui.sel) {
    const k = +sp.dataset.space, L = legalFor(ui.sel).filter(a => a.space === k);
    if (L.length === 1) return doAct(L[0]);
    if (L.length > 1) { ui.sel = { ...ui.sel, space: k }; render(); return; }
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.__game = { state: () => ui.s, busy: () => ui.busy, act: (a) => doAct(a), legal: () => legalActions(ui.s) };
startMatch();
