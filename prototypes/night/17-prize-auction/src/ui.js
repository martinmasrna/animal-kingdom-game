// 17 Prize auction as a page: you against Expert. Expert chooses its bid from the round's state
// before yours is in; both go to the engine's submit() and the round resolves on the reveal.

import { CARDS, HAND_MAX, NPRIZES, newMatch, submit, canSubmit, coinOf, pointsOf } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-17-tally';
const expert = expertBot({ worlds: 16, timeMs: 1500 });
const ui = { s: null, busy: false, over: false, sel: new Set(), botBid: null, reveal: null, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, { cls = '', attrs = '', tag = 'div' } = {}) {
  const c = CARDS[id];
  const big = c.pts > 0 ? `<div class="big pts">${c.pts}</div>` : c.pts < 0 ? `<div class="big debt">${c.pts}</div>` : `<div class="big coin">${c.coin}</div>`;
  return `<${tag} class="card ${cls}" ${attrs}>${big}<div class="nm">${c.name}</div>${c.text ? `<div class="tx">${c.text}</div>` : ''}</${tag}>`;
}
const chip = (id) => { const c = CARDS[id]; return `<span class="chip ${c.pts > 0 ? 'pts' : c.pts < 0 ? 'debt' : 'coin'}">${c.pts ? c.pts : c.coin}</span>`; };
const myMove = () => !ui.busy && !ui.over && ui.s.need[ME];

function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  let r = ''; for (let i = 1; i <= NPRIZES; i++) r += `<i class="${i < s.round ? 'done' : i === s.round ? 'now' : ''}"></i>`;
  $('round').innerHTML = r;
  for (const side of [0, 1]) {
    const P = s.p[side];
    const handPart = side === BOT ? `<div class="backs">${'<i class="back"></i>'.repeat(P.hand.length)}</div>` : '';
    $('side' + side).innerHTML = `<div class="score">${pointsOf(P)}</div><div class="piles"><span class="pile deck s${side}">${P.deck.length}</span><span class="pile disc">${P.discard.length}</span></div>${handPart}<div class="owned">${P.won.map(chip).join('')}</div>`;
  }
  // the pot, the next prize, the bids of the last reveal
  $('pot').innerHTML = (ui.reveal ? ui.reveal.pot : s.pot).map(id => cardHTML(id)).join('');
  $('pot').className = ui.reveal && ui.reveal.fly !== undefined ? 'fly' + ui.reveal.fly : '';
  $('next').innerHTML = s.prizes.length && s.winner === null ? cardHTML(s.prizes[0]) : '';
  for (const side of [0, 1]) {
    const R = ui.reveal;
    $('bid' + side).innerHTML = R ? R.bids[side].map(id => cardHTML(id, { cls: 'mini' })).join('') + `<span class="val">${R.values[side]}</span>` : '';
    $('bid' + side).className = 'bidrow' + (R && R.taker === side ? ' win' : '');
  }
  // hand and the button
  const P = s.p[ME], dropping = s.phase === 'discard' && s.need[ME];
  $('hand').innerHTML = P.hand.map((id, i) => ({ id, i })).sort((a, b) => (CARDS[b.id].coin - CARDS[a.id].coin) || (CARDS[b.id].pts - CARDS[a.id].pts)).map(({ id, i }) =>
    cardHTML(id, { tag: 'button', cls: (myMove() ? 'can' : '') + (ui.sel.has(i) ? ' sel' + (dropping ? ' drop' : '') : ''), attrs: `data-i="${i}"${myMove() ? '' : ' disabled'}` })).join('');
  let ctl = '';
  if (myMove() && dropping) { const k = P.hand.length - HAND_MAX; ctl = `<button id="go" class="drop"${ui.sel.size === k ? '' : ' disabled'}>Discard ${ui.sel.size}/${k}</button>`; }
  else if (myMove()) { const v = coinOf([...ui.sel].map(i => P.hand[i])); ctl = `<button id="go">Bid ${v}</button>`; }
  else ctl = `<button disabled>Bid</button>`;
  $('controls').innerHTML = ctl;
  $('history').innerHTML = ui.hist.slice(-18).map(h => `<div class="hist s${h.taker === null ? 'x' : h.taker}"><span>${h.pot.map(chip).join(' ')}</span><span class="v">${h.values[0]} : ${h.values[1]}</span><span>${h.taker === ME ? '◀' : h.taker === BOT ? '▶' : '='}</span></div>`).join('');
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }

// the bot submits what it must before you act; its bid waits, already chosen, for yours
async function prepare(tok) {
  while (!ui.over && ui.s.phase === 'discard' && ui.s.need[BOT]) {
    const a = expert(ui.s, BOT, ui.rng);
    ui.s = submit(ui.s, BOT, a);
  }
  if (tok !== ui.token) return;
  if (ui.s.phase === 'bid' && ui.s.need[BOT] && !ui.botBid) {
    ui.busy = true; render(); await wait(30);
    if (tok !== ui.token) return;
    ui.botBid = expert(ui.s, BOT, ui.rng);
  }
  ui.busy = false; render();
}
async function mine(a) {
  if (!myMove() || !canSubmit(ui.s, ME, a)) return;
  const tok = ui.token;
  ui.busy = true; ui.sel.clear();
  if (a.t === 'discard') { ui.s = submit(ui.s, ME, a); await prepare(tok); return; }
  const before = ui.s, ev = [];
  let s = submit(before, ME, a, ev);
  s = submit(s, BOT, ui.botBid, ev); ui.botBid = null;
  const R = s.last;
  ui.reveal = { pot: R.pot, bids: R.bids, values: R.values, taker: R.taker };
  render();
  await wait(1400);
  if (tok !== ui.token) return;
  ui.hist.push({ pot: R.pot, values: R.values, taker: R.taker });
  if (R.taker !== null) { ui.reveal.fly = R.taker; render(); await wait(700); }
  if (tok !== ui.token) return;
  ui.reveal = null; ui.s = s;
  if (s.winner !== null) { finish(); render(); return; }
  render();
  await prepare(tok);
}
function finish() {
  if (ui.over) return;
  ui.over = true; ui.busy = false;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p>${pointsOf(ui.s.p[ME])} : ${pointsOf(ui.s.p[BOT])}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.over = false; ui.hist = []; ui.sel.clear(); ui.botBid = null; ui.reveal = null;
  $('over').classList.remove('show');
  render();
  await prepare(tok);
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if ((b && b.id === 'rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'newgame' || b.id === 'rematch')) return startMatch();
  if (!myMove()) return;
  const s = ui.s, P = s.p[ME];
  if (b && b.dataset.i !== undefined) {
    const i = +b.dataset.i;
    if (ui.sel.has(i)) ui.sel.delete(i);
    else if (!(s.phase === 'discard' && ui.sel.size >= P.hand.length - HAND_MAX)) ui.sel.add(i);
    render(); return;
  }
  if (b && b.id === 'go') {
    const cards = [...ui.sel].map(i => P.hand[i]);
    return mine(s.phase === 'discard' ? { t: 'discard', cards } : { t: 'bid', cards });
  }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel.clear(); $('rules').classList.remove('show'); render(); } });
startMatch();
