// The ladder game as a page: you against the bot at the level you pick.
import { GAME } from './game.js';
import { makeRng, greedyBot, depthBot, timedBot } from './bots.js';

const g = GAME, L = 4;
const CARDS = ['F', 'B', 'S', 'G'];
const LEVELS = { Weak: greedyBot, Normal: depthBot(4), Expert: timedBot(1500) };
const ui = { s: null, me: 0, level: 'Expert', busy: false, hist: [], played: [-1, -1], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, wins: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

const ICON = {
  F: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M4 10h10V5l7 7-7 7v-5H4z"/></svg>',
  B: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M20 10H10V5l-7 7 7 7v-5h10z"/></svg>',
  S: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z"/></svg>',
  G: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
};
const FACE = {
  F: ['Forward', 'Step 1 closer.'],
  B: ['Back', 'Step 1 away.'],
  S: ['Strike', '3 damage when next to him. A guard stops it.'],
  G: ['Guard', 'Stops his next strike, until your next turn.'],
};
const shieldSVG = '<svg class="shield" viewBox="0 0 46 54"><path d="M23 2 43 9v15c0 13-9 22-20 28C12 46 3 37 3 24V9Z" fill="#5f7891" stroke="#fff" stroke-width="3"/></svg>';

function cardHTML(i, { cls = '', attrs = '' } = {}) {
  const c = CARDS[i];
  return `<button class="card ${c} ${cls}" ${attrs}><div class="art">${ICON[c]}${c === 'S' ? '<b>3</b>' : ''}</div><div class="nm">${FACE[c][0]}</div><div class="tx">${FACE[c][1]}</div></button>`;
}

const disp = (p) => (ui.me === 0 ? p : L - 1 - p);
function render() {
  const s = ui.s, me = ui.me, him = 1 - me;
  const myTurn = !ui.busy && g.winner(s) === null && s.turn === me;
  $('myhand').innerHTML = CARDS.map((c, i) => {
    const have = s.hand[me] & (1 << i);
    const cls = (have ? (myTurn ? 'ok' : '') : 'spent') + (ui.played[me] === i ? ' played' : '');
    return cardHTML(i, { cls, attrs: `data-m="${i}"${myTurn && have ? '' : ' disabled'}` });
  }).join('');
  $('opphand').innerHTML = CARDS.map((c, i) => cardHTML(i, { cls: (s.hand[him] & (1 << i) ? '' : 'spent') + (ui.played[him] === i ? ' played' : ''), attrs: 'disabled' })).join('');
  let line = '';
  for (let k = 0; k < L; k++) line += '<div class="cell"></div>';
  for (const side of [me, him]) {
    const left = ((disp(s.pos[side]) + 0.5) / L) * 100;
    const turn = g.winner(s) === null && s.turn === side ? ' turn' : '';
    line += `<div class="fighter ${side === me ? 'me' : 'him'}${turn}" id="f${side}" style="left:${left}%">${Math.max(0, s.hp[side])}${s.guard[side] ? shieldSVG : ''}${side === him && ui.busy && s.turn === him ? '<div class="think"><i></i><i></i><i></i></div>' : ''}</div>`;
  }
  $('line').innerHTML = line;
  $('history').innerHTML = ui.hist.slice(-20).map(h => `<div class="hist ${h.who}"><span class="hn">${FACE[CARDS[h.m]][0]}</span><span class="ho ${h.cls}">${h.out}</span></div>`).join('');
  $('levels').innerHTML = Object.keys(LEVELS).map(l => `<button data-level="${l}" class="${l === ui.level ? 'on' : ''}">${l}</button>`).join('');
}

function floatAt(side, text, cls) {
  const f = $('f' + side); if (!f) return;
  const a = $('line').getBoundingClientRect(), r = f.getBoundingClientRect();
  const el = document.createElement('div');
  el.className = 'float ' + cls; el.textContent = text;
  el.style.left = (r.left - a.left + r.width / 2) + 'px'; el.style.top = (r.top - a.top - 10) + 'px';
  $('line').appendChild(el);
  setTimeout(() => el.remove(), 1200);
}

// Play move m for the side to move; show what it did.
function apply(m) {
  const prev = ui.s, side = prev.turn, op = 1 - side;
  const next = g.play(prev, m);
  ui.s = next; ui.played = [-1, -1]; ui.played[side] = m;
  const c = CARDS[m];
  let out = '', cls = '';
  const dmg = prev.hp[op] - next.hp[op];
  if (c === 'S') {
    if (dmg > 0) { out = '−' + dmg; cls = 'dmg'; }
    else if (prev.guard[op] && !next.guard[op] && Math.abs(prev.pos[0] - prev.pos[1]) === 1) { out = 'blocked'; cls = 'block'; }
    else { out = 'miss'; cls = 'miss'; }
  }
  ui.hist.push({ who: side === ui.me ? 'me' : 'him', m, out, cls });
  render();
  if (c === 'S') {
    if (cls === 'dmg') { floatAt(op, out, 'dmg'); const f = $('f' + op); f.classList.add('hit'); }
    else floatAt(op, out === 'blocked' ? 'Blocked' : 'Miss', cls);
  }
  if (g.winner(next) !== null) finish();
}

function finish() {
  const w = g.winner(ui.s);
  const t = w === 'draw' ? ['Draw', ''] : w === ui.me ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="again">Play again</button>`;
  $('over').classList.add('show');
}

async function botMove(tok) {
  ui.busy = true; render();
  await wait(350);
  if (tok !== ui.token) return;
  const t0 = Date.now();
  const m = LEVELS[ui.level](g, ui.s, ui.rng);
  await wait(Math.max(0, 500 - (Date.now() - t0)));
  if (tok !== ui.token) return;
  ui.busy = false;
  apply(m);
}

async function step() {
  const tok = ui.token;
  if (g.winner(ui.s) !== null) return;
  if (ui.s.turn !== ui.me) { await botMove(tok); if (tok !== ui.token) return; render(); }
}

function start() {
  ui.token++;
  ui.me = ui.wins++ % 2 === 0 ? 0 : 1; // sides swap every match, so who moves first alternates
  ui.s = g.init(ui.rng); ui.hist = []; ui.played = [-1, -1]; ui.busy = false;
  $('over').classList.remove('show');
  render();
  setTimeout(step, 400);
}

document.addEventListener('click', async (e) => {
  const t = e.target.closest('button');
  if (!t || t.disabled) return;
  if (t.dataset.m !== undefined) {
    if (ui.busy || ui.s.turn !== ui.me || g.winner(ui.s) !== null) return;
    apply(+t.dataset.m);
    await wait(250);
    step();
    return;
  }
  if (t.dataset.level) { ui.level = t.dataset.level; render(); return; }
  if (t.id === 'restart' || t.id === 'again') start();
});
start();
