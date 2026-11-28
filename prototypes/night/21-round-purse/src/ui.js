// Round purse as a game screen against the Expert. Every move goes through legalActions/act; the
// bot's moves play out one at a time. The win tally is kept in this browser and decides who starts
// round 1 (alternating).

import { CARDS, newMatch, act, legalActions, total } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-21-purse-tally';
const expert = expertBot({ budget: 3000 });
const ui = { s: null, view: null, busy: false, over: false, fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const TEXT = { Gift: '+4 to them, draw 2', Cut: 'Destroy their strongest' };
function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id], spell = !c.power;
  return `<button class="card${spell ? ' spell' : ''} ${cls}" ${attrs}>${c.cost ? `<span class="cgem">${c.cost}</span>` : ''}<div class="art"><span class="big">${spell ? (c.gift ? '+4' : '✕') : c.power}</span></div><div class="nm">${c.name}</div>${spell ? `<div class="tx">${TEXT[id]}</div>` : ''}</button>`;
}

// ------------------------------------------------------------------ rendering
const myTurn = () => !ui.busy && !ui.over && ui.view.toMove === ME && ui.view.winner === null;
function roundsHTML() {
  const s = ui.view;
  let h = '';
  for (let r = 1; r <= 3; r++) { const res = s.results[r - 1]; h += `<i class="${res ? (res.w === null ? 'tie' : 'w' + res.w) : r === s.round && !ui.over ? 'now' : ''}">${r}</i>`; }
  return h;
}
function infoHTML(side) {
  const s = ui.view, P = s.p[side];
  const wins = `<div class="wins s${side}"><i class="${s.wins[side] >= 1 ? 'on' : ''}"></i><i class="${s.wins[side] >= 2 ? 'on' : ''}"></i></div>`;
  const backs = side === BOT ? `<div class="backs">${'<i class="back"></i>'.repeat(P.hand.length)}</div>` : '';
  return `<div class="purse" id="purse${side}">${s.purse[side]}</div>${wins}<span class="pile s${side}">${P.deck.length}</span>${backs}`;
}
function rowHTML(side) {
  const s = ui.view, T = s.table[side], a = total(s, side), b = total(s, 1 - side);
  const cards = T.map(x => `<div class="unit s${x.owner}${CARDS[x.id].gift ? ' gift' : ''}${ui.fx['u' + x.uid] ? ' ' + ui.fx['u' + x.uid] : ''}" id="u${x.uid}"><span class="pw">${x.power}</span><span class="un">${CARDS[x.id].name}</span></div>`).join('');
  return `<div class="cards">${cards}</div><div class="total s${side}${a > b ? ' lead' : ''}">${a}</div>`;
}
function handHTML() {
  const s = ui.view, can = myTurn(), L = can ? legalActions(s) : [];
  const H = s.p[ME].hand.map((id, i) => i).sort((x, y) => CARDS[s.p[ME].hand[x]].cost - CARDS[s.p[ME].hand[y]].cost || CARDS[s.p[ME].hand[x]].power - CARDS[s.p[ME].hand[y]].power);
  return H.map((i) => { const id = s.p[ME].hand[i], ok = L.some(a => a.card === id); return cardHTML(id, { cls: (ok ? 'ok' : '') + (ui.fresh && i >= s.p[ME].hand.length - ui.fresh ? ' drawn' : ''), attrs: `data-card="${id}"${ok ? '' : ' disabled'}` }); }).join('');
}
function render() {
  const s = ui.view, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('rounds').innerHTML = roundsHTML();
  for (const side of [0, 1]) { $('info' + side).innerHTML = infoHTML(side); $('row' + side).innerHTML = rowHTML(side); $('row' + side).classList.toggle('passed', s.passed[side] && !ui.over); }
  $('hand').innerHTML = handHTML();
  $('side').innerHTML = `<button id="pass"${myTurn() ? '' : ' disabled'}>Pass</button>`;
  ui.fresh = 0; ui.fx = {};
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function ghost(el) {
  if (!el) return;
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = el.outerHTML; d.style.left = (r.left - g.left) + 'px'; d.style.top = (r.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 550);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const cutE = ev.find(e => e.t === 'cut'), roundE = ev.find(e => e.t === 'round');
  if (cutE) ghost($('u' + cutE.uid));
  // the round's last table stays up while its result shows
  if (roundE) {
    const place = ev.find(e => e.t === 'place');
    ui.view = { ...next, table: prev.table, passed: [true, true], results: next.results.slice(0, -1), wins: prev.wins };
    if (place) ui.fx['u' + place.uid] = 'new';
    render();
    await wait(500);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    banner(roundE.w === null ? 'Tie' : roundE.w === ME ? 'Round won' : 'Round lost');
    ui.view = { ...ui.view, results: next.results, wins: next.wins }; render();
    await wait(1500);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  }
  for (const e of ev) { if (e.t === 'place') ui.fx['u' + e.uid] = 'new'; if (e.t === 'draw' && e.side === ME) ui.fresh++; }
  ui.view = next; render();
  if (ev.some(e => e.t === 'start')) { banner('Round ' + next.round); await wait(700); }
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
  ui.view = ui.s; ui.over = false;
  $('over').classList.remove('show');
  ui.busy = true; render(); banner('Round 1');
  await wait(900);
  if (tok !== ui.token) return;
  await run(tok);
}
async function run(tok) {
  while (tok === ui.token && !ui.over && ui.s.toMove === BOT && ui.s.winner === null) {
    ui.busy = true; render();
    await wait(650);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
  }
  if (tok !== ui.token) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true;
  await apply(a);
  await run(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if (b && b.id === 'rulesclose') { $('rules').classList.remove('show'); return; }
  if (e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (!myTurn() || !b || b.disabled) return;
  if (b.id === 'pass') return doAct({ t: 'pass' });
  if (b.dataset.card) return doAct({ t: 'play', card: b.dataset.card });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
startMatch();
