// 18 Edge flip grid as a page: you against Expert. Every change goes through the engine's act()
// with the same actions the bots use; the bot's turn is played one placement at a time.

import { CARDS, CELLS, ROTS, newMatch, act, legalActions, edgesOf, count } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-18-tally';
const expert = expertBot({ playouts: 900, timeMs: 1400 });
const ui = { s: null, busy: false, over: false, sel: null, fx: {}, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const edgesHTML = (e) => `<span class="ed t">${e[0]}</span><span class="ed r">${e[1]}</span><span class="ed b">${e[2]}</span><span class="ed l">${e[3]}</span>`;
const myMove = () => !ui.busy && !ui.over && ui.s.turn === ME && ui.s.winner === null;

function render() {
  const s = ui.s, t = loadTally(), L = myMove() ? legalActions(s) : [];
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  const O = s.p[BOT], P = s.p[ME];
  $('opp').innerHTML = `<div class="backs">${'<i class="back"></i>'.repeat(O.hand.length)}</div><span class="manaval">${O.mana}/${O.maxMana}</span><span class="pile s1">${O.deck.length}</span>`;
  $('score0').textContent = count(s, 0); $('score1').textContent = count(s, 1);
  let g = '';
  for (let c = 0; c < CELLS; c++) {
    const x = s.grid[c];
    if (x) g += `<div class="cell"><div class="tile s${x.owner} ${ui.fx[c] || ''}"><span class="nm">${CARDS[x.card].name}</span>${edgesHTML(x.e)}</div></div>`;
    else { const can = ui.sel && L.some(a => a.t === 'place' && a.card === ui.sel.card && a.cell === c); g += `<div class="cell${can ? ' can' : ''}" data-cell="${c}"></div>`; }
  }
  $('grid').innerHTML = g;
  $('mine').innerHTML = `<span class="manaval">${P.mana}/${P.maxMana}</span><span class="pile s0">${P.deck.length}</span>`;
  $('hand').innerHTML = P.hand.map((id, i) => ({ id, i })).sort((a, b) => (CARDS[a.id].cost - CARDS[b.id].cost)).map(({ id, i }) => {
    if (id === 'COIN') { const ok = L.some(a => a.t === 'coin'); return `<button class="card coin ${ok ? 'ok' : 'no'}" data-i="${i}"${ok ? '' : ' disabled'}>+1</button>`; }
    const ok = L.some(a => a.t === 'place' && a.card === id), sel = ui.sel && ui.sel.i === i;
    const rot = sel ? ui.sel.rot : 0;
    return `<button class="card ${ok ? 'ok' : (myMove() ? 'no' : '')}${sel ? ' sel' : ''}" data-i="${i}"${ok ? '' : ' disabled'}><span class="cost">${CARDS[id].cost}</span><span class="nm">${CARDS[id].name}</span>${edgesHTML(edgesOf(id, rot))}</button>`;
  }).join('');
  const any = L.some(a => a.t === 'place');
  $('controls').innerHTML = `<button id="end" class="${myMove() && !any ? 'done' : ''}"${myMove() ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-18).map(h => `<div class="hist s${h.side}"><span>${h.txt}</span><span class="f">${h.f ? '+' + h.f : ''}</span></div>`).join('');
  ui.fx = {};
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }

async function apply(a) {
  const qtok = ui.token;
  const ev = [], side = ui.s.turn;
  ui.s = act(ui.s, a, ev);
  for (const e of ev) { if (e.t === 'place') ui.fx[e.cell] = 'new'; if (e.t === 'flip') ui.fx[e.cell] = 'flip'; }
  const pl = ev.find(e => e.t === 'place'), fl = ev.filter(e => e.t === 'flip').length;
  if (pl) ui.hist.push({ side, txt: CARDS[pl.card].name, f: fl });
  if (a.t === 'end' && ev.some(e => e.t === 'endturn' && e.pass)) ui.hist.push({ side, txt: 'Pass' });
  if (ev.some(e => e.t === 'turn' && e.side === ME)) banner('Your turn');
  render();
  if (ui.s.winner !== null) finish();
  await wait(pl ? 650 : 250);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
}
function finish() {
  if (ui.over) return;
  ui.over = true; ui.busy = false;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p>${count(ui.s, ME)} : ${count(ui.s, BOT)}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}
async function advance(tok) {
  while (!ui.over && ui.s.turn === BOT && ui.s.winner === null) {
    ui.busy = true; render();
    await wait(450);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token) return;
    await apply(a);
  }
  ui.busy = false; ui.sel = null; render();
}
async function mine(a) {
  if (!myMove()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  await advance(tok);
}
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(700);
  if (tok !== ui.token) return;
  await advance(tok);
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if ((b && b.id === 'rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'newgame' || b.id === 'rematch')) return startMatch();
  if (!myMove()) return;
  if (b && b.id === 'end') return mine({ t: 'end' });
  if (b && b.dataset.i !== undefined) {
    const i = +b.dataset.i, id = ui.s.p[ME].hand[i];
    if (id === 'COIN') return mine({ t: 'coin' });
    if (ui.sel && ui.sel.i === i) { const R = ROTS[id], k = R.indexOf(ui.sel.rot); ui.sel.rot = R[(k + 1) % R.length]; }
    else ui.sel = { i, card: id, rot: 0 };
    render(); return;
  }
  const cell = e.target.closest('.cell.can');
  if (cell && ui.sel) return mine({ t: 'place', card: ui.sel.card, cell: +cell.dataset.cell, rot: ui.sel.rot });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
