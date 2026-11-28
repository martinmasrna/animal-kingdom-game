// 24 Rally as a game screen against the Expert. Each shot is animated onto the court; the point,
// game and match results show on the scoreboard; the win tally is kept in this browser and decides
// who serves the first game.

import { CARDS, STAMINA, newMatch, act, legalActions, lastShot } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-24-tally';
const expert = expertBot({ ...EXPERT, playouts: 1500, timeMs: 1200 });
const ui = { s: null, view: null, busy: false, over: false, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, lastRally: [] };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  return `<button class="card s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="pace">${c.pace}</span></div><div class="nm">${c.name}</div><div class="rch"><i></i>${c.reach}</div></button>`;
}
const shotHTML = (r, i, last) => `<div class="shot s${r.side}${last ? ' last' : ''}" id="shot${i}"><span class="pace">${CARDS[r.card].pace}</span><span class="rch">${CARDS[r.card].reach}</span><span class="snm">${CARDS[r.card].name}</span></div>`;

// ------------------------------------------------------------------ rendering
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function boardHTML() {
  const s = ui.view;
  const row = (side) => {
    const p = s.p[side];
    let st = '';
    for (let i = 0; i < STAMINA; i++) st += `<i class="${i < p.stamina ? 'on' : ''}"></i>`;
    return `<div class="srow s${side}"><span class="ball">${s.server === side ? '●' : ''}</span><span class="g ${ui.fx['g' + side] || ''}">${p.games}</span><span class="pt ${ui.fx['p' + side] || ''}">${p.points}</span><span class="stam">${st}</span><span class="stn">${p.stamina}</span></div>`;
  };
  return row(BOT) + row(ME);
}
function courtHTML(side) {
  const s = ui.view, R = s.rally.length ? s.rally : ui.lastRally;
  const fading = !s.rally.length && ui.lastRally.length ? ' fading' : '';
  return `<div class="lane${fading}">${R.map((r, i) => r.side === side ? shotHTML(r, i, i === R.length - 1 && !fading) : '<div class="gap"></div>').join('')}</div>`;
}
function handHTML() {
  const s = ui.view, p = s.p[ME], legal = myTurn() ? legalActions(s) : [];
  const order = p.hand.map((_, i) => i).sort((a, b) => CARDS[p.hand[a]].pace - CARDS[p.hand[b]].pace || CARDS[p.hand[a]].reach - CARDS[p.hand[b]].reach);
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'shot' && a.card === id);
    return cardHTML(id, ME, { cls: ok ? 'ok' : (myTurn() ? 'no' : ''), attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.view;
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="cb"></i>'.repeat(s.p[BOT].hand.length);
  $('board').innerHTML = boardHTML();
  $('half1').innerHTML = courtHTML(BOT); $('half0').innerHTML = courtHTML(ME);
  $('hand').innerHTML = handHTML();
  const l = lastShot(s), mine = myTurn();
  const need = l && s.toAct === ME && !ui.over ? `<div class="need"><span>${CARDS[l.card].pace}</span></div>` : '';
  $('turnbox').innerHTML = `${need}<button id="letgo"${mine && s.rally.length ? '' : ' disabled'}>Let it go</button>`;
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text, cls = '') { const b = $('banner'); b.textContent = text; b.className = cls; void b.offsetWidth; b.classList.add('show'); }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const shotE = ev.find(e => e.t === 'shot');
  // the court keeps the finished point's shots on screen until the next serve
  const pointE = ev.find(e => e.t === 'point');
  if (shotE) {
    const R = prev.rally.concat([{ card: shotE.card, side: shotE.side }]);
    ui.view = { ...next, rally: R, p: next.p, toAct: pointE ? -1 : next.toAct }; ui.lastRally = [];
    render();
    const el = $('shot' + (R.length - 1));
    if (el) el.animate([{ transform: `translateY(${shotE.side === ME ? 60 : -60}px) scale(.6)`, opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 260, easing: 'ease-out' });
    await wait(pointE ? 500 : 150);
    if (pointE) ui.lastRally = R;
  }
  if (a.t === 'concede') { ui.lastRally = prev.rally; }
  for (const e of ev) {
    if (e.t === 'point') ui.fx['p' + e.side] = 'pop';
    if (e.t === 'game') ui.fx['g' + e.side] = 'pop';
  }
  ui.view = next; render();
  const noR = ev.find(e => e.t === 'noreturn'), con = ev.find(e => e.t === 'concede'), noS = ev.find(e => e.t === 'noserve');
  for (const e of ev) if (e.t === 'point') {
    const why = noS && e.side !== noS.side ? 'no serve' : noR ? 'no return' : con ? 'let go' : '';
    floatAt(centerOf($('half' + e.side)), why ? `Point · ${why}` : 'Point', 'pt s' + e.side);
  }
  const gameE = ev.find(e => e.t === 'game');
  if (gameE && next.winner === null) { await wait(700); banner(gameE.side === ME ? 'Game' : 'Game lost', gameE.side === ME ? 'win' : 'lose'); ui.lastRally = []; await wait(900); render(); }
  else if (ev.some(e => e.t === 'point')) await wait(900);
  if (next.winner !== null) finish();
  render();
}

function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="final">${ui.s.p[ME].games} – ${ui.s.p[BOT].games}</div><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.lastRally = [];
  $('over').classList.remove('show');
  ui.busy = true; render();
  await wait(700);
  if (tok !== ui.token) return;
  await botLoop(tok);
}
async function botLoop(tok) {
  ui.busy = true; render();
  for (let k = 0; k < 400; k++) {
    if (tok !== ui.token || ui.over || ui.s.winner !== null || ui.s.toAct !== BOT) break;
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
  ui.busy = true;
  await apply(a);
  if (tok !== ui.token || ui.over) return;
  await botLoop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.add('show'); return; }
  if (e.target.closest('#rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  const b = e.target.closest('button');
  if (!b || b.disabled) return;
  if (b.id === 'rematch' || b.id === 'newgame') return startMatch();
  if (b.id === 'letgo') return doAct({ t: 'concede' });
  if (b.dataset.hand !== undefined) return doAct({ t: 'shot', card: ui.view.p[ME].hand[+b.dataset.hand] });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
window.__game = { state: () => ui.s, busy: () => ui.busy, act: (a) => doAct(a), legal: () => legalActions(ui.s) };
startMatch();
