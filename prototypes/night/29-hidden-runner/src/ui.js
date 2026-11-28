// Hidden runner as a game screen against Expert. The human is seat 0 and alternates roles from game
// to game. As the Hunter the page shows only what a Hunter knows: announced kinds, reveals, Search
// answers; never the Runner. Every action goes through legalActions/act.

import { N, ADJ, DIST, ROUNDS, REVEALS, ECAP, RCARDS, HCARDS, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-29-tally';
const expert = expertBot({ iters: 1500 });
const ui = { s: null, busy: false, over: false, sel: null, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, flash: null };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const role = () => ui.s.seatR === ME ? 'R' : 'H';
const CARD = (id) => RCARDS[id] || HCARDS[id];
const SHORT = { SEA: 'Name a node: on it or next to it?', HIDE: 'Stay; Searches say no.', SMOK: 'Move 1 or stay; skip the next reveal.', SPR: 'A pawn moves up to 2.' };
const GLYPH = { STEP: '·', DASH: '⇉', SLIP: '⤡', HIDE: '◌', SMOK: '≋', DOUB: '⇶', SPR: '⇉', SEA: '?', FLA: '✦', BLO: '■' };
function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARD(id);
  return `<button class="card ${RCARDS[id] ? 'rc' : 'hc'} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="big">${GLYPH[id]}</span></div><div class="nm">${c.name}</div><div class="tx">${SHORT[id] || c.text}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myMove = () => !ui.busy && !ui.over && ui.s.turn === ME;
const legal = () => myMove() ? legalActions(ui.s) : [];
// node -> the action a click there does, given the selection
function clickMap() {
  const out = new Map(), L = legal(), sel = ui.sel;
  for (const a of L) {
    if (a.t === 'start') out.set(a.to, a);
    if (a.t === 'run' && sel && sel.card === a.card) out.set(a.to, a);
    if (a.t === 'move' && sel && sel.pawn === a.pawn && !sel.card) out.set(a.to, a);
    if (a.t === 'card' && sel && sel.card === a.card) {
      if (a.card === 'SPR' && sel.pawn === a.pawn) out.set(a.to, a);
      if (a.card === 'SEA' || a.card === 'BLO') out.set(a.node, a);
    }
  }
  return out;
}

// ------------------------------------------------------------------ rendering
const pct = (n) => ({ x: ((n % N) + 0.5) * 100 / N, y: (Math.floor(n / N) + 0.5) * 100 / N });
function boardHTML() {
  const s = ui.s, M = clickMap(), L = legal();
  let h = '<svg class="links" viewBox="0 0 100 100" preserveAspectRatio="none">';
  for (let n = 0; n < N * N; n++) for (const m of ADJ[n]) if (m > n) { const a = pct(n), b = pct(m); h += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`; }
  h += '</svg>';
  const srch = s.search ? [s.search.node, ...ADJ[s.search.node]] : [];
  for (let n = 0; n < N * N; n++) {
    const p = pct(n), blk = s.blocks.find(b => b.node === n);
    let cls = M.has(n) ? ' tgt' : '';
    if (s.phase === 'start' && Math.floor(n / N) === 0 && role() === 'H') cls += ' startrow';
    if (s.search && srch.includes(n)) cls += s.search.yes ? ' syes' : ' sno';
    h += `<div class="node${cls}" data-node="${n}" style="left:${p.x}%;top:${p.y}%">${blk ? `<span class="blk">${blk.until - s.round}</span>` : ''}${s.search && s.search.node === n ? `<b class="ans">${s.search.yes ? '✓' : '✕'}</b>` : ''}</div>`;
  }
  // the Runner: always for the Runner's own player; for the Hunter only the last sighting
  const showRunner = s.runner >= 0 && (role() === 'R' || ui.over || (ui.flash && ui.flash.node === s.runner));
  if (s.lastSeen && !showRunner) { const p = pct(s.lastSeen.node); h += `<div class="seen" style="left:${p.x}%;top:${p.y}%"><span>${s.lastSeen.round}</span></div>`; }
  if (showRunner) { const p = pct(s.runner); h += `<div class="runner s${s.seatR}${ui.flash ? ' flash' : ''}" style="left:${p.x}%;top:${p.y}%"></div>`; }
  const hs = 1 - s.seatR;
  s.pawns.forEach((n, i) => {
    const p = pct(n);
    const can = role() === 'H' && myMove() && s.phase === 'hunt' && L.some(a => (a.t === 'move' && a.pawn === i) || (a.card === 'SPR' && a.pawn === i));
    const sel = ui.sel && ui.sel.pawn === i;
    h += `<div class="pawn s${hs}${can && !sel && (!ui.sel || ui.sel.card === 'SPR') ? ' can' : ''}${sel ? ' sel' : ''}${s.phase === 'hunt' && s.moved[i] ? ' moved' : ''}" data-pawn="${i}" style="left:${p.x}%;top:${p.y}%"></div>`;
  });
  return h;
}
function energyHTML(P) { let g = ''; for (let i = 0; i < ECAP; i++) g += `<i class="${i < P.energy ? 'on' : ''}"></i>`; return `<span class="en">${g}</span>`; }
function sideHTML(seat) {
  const s = ui.s, P = seat === s.seatR ? s.R : s.H;
  return `<span class="who s${seat}">${seat === s.seatR ? '◆' : '●●'}</span>${energyHTML(P)}<span class="pile s${seat}">${P.deck.length}</span>${seat === BOT ? `<span class="backs">${'<i></i>'.repeat(P.hand.length)}</span>` : ''}`;
}
function handHTML() {
  const s = ui.s, L = legal(), mine = role() === 'R' ? s.R : s.H;
  const ids = role() === 'R' ? ['STEP', ...mine.hand.slice().sort()] : mine.hand.slice().sort();
  return ids.map((id, k) => {
    const ok = role() === 'R' ? L.some(a => a.t === 'run' && a.card === id) : L.some(a => a.t === 'card' && a.card === id);
    const sel = ui.sel && ui.sel.card === id && ui.sel.k === k;
    return cardHTML(id, { cls: (ok ? 'ok' : (myMove() ? 'no' : '')) + (sel ? ' sel' : '') + (id === 'STEP' ? ' basic' : ''), attrs: `data-card="${id}" data-k="${k}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('board').innerHTML = boardHTML();
  let r = ''; for (let i = 1; i <= ROUNDS; i++) r += `<i class="${i < s.round ? 'past' : i === s.round ? 'now' : ''}${REVEALS.includes(i) ? ' rev' : ''}"></i>`;
  $('rounds').innerHTML = r;
  $('side1').innerHTML = sideHTML(BOT); $('side0').innerHTML = sideHTML(ME);
  $('hand').innerHTML = handHTML();
  const canDone = legal().some(a => a.t === 'done');
  $('turnbox').innerHTML = role() === 'H' ? `<button id="done"${canDone ? '' : ' disabled'}>End round</button>` : '';
  $('history').innerHTML = ui.hist.slice(-14).map(h => `<div class="hist s${h.side}">${h.html}</div>`).join('');
}

// ------------------------------------------------------------------ effects
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(id) {
  const g = $('game').getBoundingClientRect(), b = $('board').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(id);
  await wait(850);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const actor = prev.turn;
  const runE = ev.find(e => e.t === 'run'), hcE = ev.find(e => e.t === 'hcard');
  if (actor === BOT && runE) await spotlight(runE.card);
  if (actor === BOT && hcE) await spotlight(hcE.card);
  ui.sel = null;
  // a reveal or flare or catch: show the Runner on the pre-round board for a moment
  const showE = ev.find(e => e.t === 'show') || ev.find(e => e.t === 'caught');
  if (showE) { ui.s = { ...next, round: prev.round, blocks: prev.blocks.length >= next.blocks.length ? next.blocks : prev.blocks, search: next.search ?? prev.search }; ui.flash = { node: showE.node }; render(); await wait(1100); ui.flash = null; }
  ui.s = next; render();
  // history
  const kindHTML = (id, side) => `<span class="chip ${RCARDS[id] ? 'rc' : 'hc'}">${GLYPH[id]}</span><span class="ho">${CARD(id).name}</span>`;
  if (runE) ui.hist.push({ side: actor, html: `<span class="rn">${prev.round}</span>` + kindHTML(runE.card) });
  if (hcE) ui.hist.push({ side: actor, html: kindHTML(hcE.card) + (hcE.card === 'SEA' ? `<span class="ho ${ev.find(e => e.t === 'search').yes ? 'yes' : 'no'}">${ev.find(e => e.t === 'search').yes ? '✓' : '✕'}</span>` : '') });
  for (const e of ev) {
    if (e.t === 'show') ui.hist.push({ side: next.seatR, html: `<span class="chip seenc">◆</span><span class="ho">${e.why === 'flare' ? 'Flare' : 'Shown'}</span>` });
    if (e.t === 'smoked') ui.hist.push({ side: next.seatR, html: `<span class="chip rc">≋</span><span class="ho">No reveal</span>` });
  }
  if (ev.some(e => e.t === 'round') && next.round > 1) await wait(400);
  if (next.winner !== null) finish();
  render();
}

function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  render();
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, seatR: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null; ui.flash = null;
  $('over').classList.remove('show');
  $('game').classList.toggle('asR', role() === 'R'); $('game').classList.toggle('asH', role() === 'H');
  ui.busy = true; render();
  banner(role() === 'R' ? 'You run' : 'You hunt');
  await wait(1000);
  if (tok !== ui.token) return;
  return loop(tok);
}
async function loop(tok) {
  while (tok === ui.token && !ui.over && ui.s.turn === BOT) {
    ui.busy = true; render();
    await wait(500);
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token) return;
    await apply(a);
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myMove()) return;
  const tok = ui.token;
  ui.busy = true;
  await apply(a);
  if (tok !== ui.token) return;
  return loop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { $('rulesbox').classList.toggle('show'); return; }
  if (e.target.closest('#rulesbox')) { $('rulesbox').classList.remove('show'); return; }
  const b = e.target.closest('button');
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (!myMove()) return;
  const s = ui.s;
  const nodeEl = e.target.closest('.node'), pawnEl = e.target.closest('.pawn');
  if (pawnEl && role() === 'H') {
    const i = +pawnEl.dataset.pawn;
    const L = legalActions(s);
    if (ui.sel && ui.sel.card === 'SPR' && ui.sel.pawn === undefined && L.some(a => a.card === 'SPR' && a.pawn === i)) { ui.sel = { ...ui.sel, pawn: i }; render(); return; }
    if (!ui.sel && L.some(a => a.t === 'move' && a.pawn === i)) { ui.sel = { pawn: i }; render(); return; }
    if (ui.sel && ui.sel.pawn === i && !ui.sel.card) { const a = clickMap().get(s.pawns[i]); if (a) return doAct(a); }
  }
  if (nodeEl || pawnEl) {
    const n = nodeEl ? +nodeEl.dataset.node : s.pawns[+pawnEl.dataset.pawn];
    const a = clickMap().get(n);
    if (a) return doAct(a);
  }
  if (b && !b.disabled && b.dataset.card) {
    const id = b.dataset.card, k = +b.dataset.k;
    if (ui.sel && ui.sel.card === id && ui.sel.k === k) { ui.sel = null; render(); return; }
    if (id === 'FLA') return doAct({ t: 'card', card: 'FLA' });
    ui.sel = { card: id, k }; render(); return;
  }
  if (b && !b.disabled && b.id === 'done') return doAct({ t: 'done' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rulesbox').classList.remove('show'); render(); } });
startMatch();
