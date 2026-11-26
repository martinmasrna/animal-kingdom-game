// Toy 7 as a page: you against the expert bot. Draw 3, play 1. Strike hits him or one of his Powers.
import { GAME } from './minimal.js';
import { makeRng, pimcTimed } from './bots.js';

const g = GAME;
const bot = pimcTimed(1200, 16);
const ui = { s: null, me: 0, games: 0, busy: false, aiming: false, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, pop: [-1, -1] };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const DECK = { S: 3, I: 3 };

const ICON = {
  S: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z"/></svg>',
  I: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2l3 7h7l-5.5 4.5 2 7.5L12 16.5 5.5 21l2-7.5L2 9h7z"/></svg>',
};
const NAME = { S: 'Strike', I: 'Power' };

function cardHTML(c, { cls = '', attrs = '', dmg = 1 } = {}) {
  const tx = c === 'S' ? `Deal ${dmg} to him, or destroy one of his Powers.` : 'Stays on the table. Your Strikes deal 1 more.';
  return `<button class="card ${c === 'S' ? 'S' : 'P'} ${cls}" ${attrs}><div class="art">${ICON[c]}${c === 'S' ? `<b>${dmg}</b>` : '<b>+1</b>'}</div><div class="nm">${NAME[c]}</div><div class="tx">${tx}</div></button>`;
}
function powersHTML(side, n) {
  const target = ui.aiming && side !== ui.me;
  let out = '';
  for (let i = 0; i < n; i++) out += `<button class="power${target ? ' target' : ''}${ui.pop[side] === i ? ' pop' : ''}" data-power="${side}"${target ? '' : ' disabled'}>${ICON.I}</button>`;
  return out;
}
function pileHTML(side) {
  // what is still to come before the next reshuffle: yours exactly, his as everything he has not played
  const s = ui.s, p = side === ui.me;
  const left = { S: 0, I: 0 };
  if (p) for (const c of s.deck[side]) left[c]++;
  else { left.S = DECK.S; left.I = DECK.I; for (const c of s.disc[side]) left[c]--; }
  const row = (c) => `<span class="pc ${c === 'S' ? 'S' : 'P'}">${ICON[c]}<b>${left[c]}</b></span>`;
  return `<div class="pile-row ${p ? 'me' : 'him'}">${row('S')}${row('I')}</div>`;
}

function render() {
  const s = ui.s, me = ui.me, him = 1 - me;
  const myTurn = !ui.busy && g.winner(s) === null && s.turn === me;
  const dmg = 1 + s.inv[me];
  $('myhand').innerHTML = (s.turn === me ? s.hand[me] : []).map((c, i) => cardHTML(c, { dmg, cls: (myTurn ? 'ok' : '') + (ui.aiming && c === 'S' && i === ui.aimIdx ? ' picked' : ''), attrs: `data-i="${i}"${myTurn ? '' : ' disabled'}` })).join('');
  $('opphand').innerHTML = s.turn === him ? '<i class="back"></i>'.repeat(s.hand[him].length) : '';
  const row = (side) => {
    const target = ui.aiming && side === him;
    return `<div class="row ${side === me ? 'mine' : 'his'}">
      <button class="hero ${side === me ? 'me' : 'him'}${s.turn === side && g.winner(s) === null ? ' turn' : ''}${target ? ' target' : ''}" id="h${side}" data-hero="${side}"${target ? '' : ' disabled'}>${Math.max(0, s.hp[side])}</button>
      <div class="powers">${powersHTML(side, s.inv[side])}</div></div>`;
  };
  $('board').innerHTML = row(him) + row(me);
  $('history').innerHTML = ui.hist.slice(-22).map(h => h.sep ? '<div class="hist sep"></div>' : `<div class="hist ${h.who}"><span class="hn">${h.name}</span><span class="ho ${h.cls}">${h.out}</span></div>`).join('');
  $('piles').innerHTML = pileHTML(him) + pileHTML(me);
  ui.pop = [-1, -1];
}

function floatAt(el, text, cls) {
  if (!el) return;
  const a = $('board').getBoundingClientRect(), r = el.getBoundingClientRect();
  const f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text;
  f.style.left = (r.left - a.left + r.width / 2) + 'px'; f.style.top = (r.top - a.top) + 'px';
  $('board').appendChild(f);
  setTimeout(() => f.remove(), 1200);
}

function apply(m) {
  const prev = ui.s, side = prev.turn, op = 1 - side;
  const next = g.play(prev, m);
  ui.s = next;
  const who = side === ui.me ? 'me' : 'him';
  if (m === 'S') ui.hist.push({ who, name: 'Strike', out: '−' + (prev.hp[op] - next.hp[op]), cls: 'dmg' });
  else if (m === 'S>I') ui.hist.push({ who, name: 'Strike', out: 'Power down', cls: 'block' });
  else { ui.hist.push({ who, name: 'Power', out: '+1', cls: 'gold' }); ui.pop[side] = next.inv[side] - 1; }
  if (next.turn !== side) ui.hist.push({ sep: true });
  render();
  if (m === 'S') { const h = $('h' + op); floatAt(h, '−' + (prev.hp[op] - next.hp[op]), 'dmg'); h.classList.add('hit'); }
  if (m === 'S>I') floatAt($('h' + op), 'Power destroyed', 'block');
  if (g.winner(next) !== null) finish();
}

function finish() {
  const w = g.winner(ui.s);
  const t = w === 'draw' ? ['Draw', ''] : w === ui.me ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="again">Play again</button>`;
  $('over').classList.add('show');
}

async function botTurn() {
  const tok = ui.token;
  while (g.winner(ui.s) === null && ui.s.turn !== ui.me) {
    ui.busy = true; render();
    await wait(450);
    const m = bot(g, ui.s, ui.rng);
    if (tok !== ui.token) return;
    ui.busy = false;
    apply(m);
    await wait(500);
  }
  ui.busy = false; render();
}

function start() {
  ui.token++;
  ui.me = ui.games++ % 2; // who goes first alternates
  ui.s = g.init(ui.rng); ui.hist = []; ui.busy = false; ui.aiming = false;
  $('over').classList.remove('show');
  render();
  if (ui.s.turn !== ui.me) setTimeout(botTurn, 500);
}

document.addEventListener('click', async (e) => {
  const t = e.target.closest('button');
  if (!t) { if (ui.aiming) { ui.aiming = false; render(); } return; }
  if (t.id === 'restart' || t.id === 'again') { start(); return; }
  if (t.disabled || ui.busy) return;
  const s = ui.s;
  if (t.dataset.i !== undefined) {
    const c = s.hand[ui.me][+t.dataset.i];
    if (c === 'I') { ui.aiming = false; apply('I'); await wait(300); botTurn(); return; }
    if (s.inv[1 - ui.me] > 0) { ui.aiming = !ui.aiming; ui.aimIdx = +t.dataset.i; render(); return; } // choose a target
    apply('S'); await wait(300); botTurn(); return;
  }
  if (ui.aiming && t.dataset.hero !== undefined) { ui.aiming = false; apply('S'); await wait(300); botTurn(); return; }
  if (ui.aiming && t.dataset.power !== undefined) { ui.aiming = false; apply('S>I'); await wait(300); botTurn(); return; }
});
start();
