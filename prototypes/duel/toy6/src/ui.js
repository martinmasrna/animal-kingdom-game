// Toy 6 as a page: both pick one action at once; the round resolves (steps first, then blows).
import { R, setRules, newMatch, legal, resolve, COST } from './engine.js';
import { makeRng, mixBot } from './bot.js';

setRules({ recovery: true, grab: true, len: 4 });
const L = R.len, ME = 0, BOT = 1;
const bot = mixBot(2);
const ui = { s: null, busy: false, hist: [], shown: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, picks: [null, null] };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

const ORDER = ['F', 'B', 'S', 'G', 'T', 'Z'];
const ICON = {
  F: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M4 10h10V5l7 7-7 7v-5H4z"/></svg>',
  B: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M20 10H10V5l-7 7 7 7v-5h10z"/></svg>',
  S: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z"/></svg>',
  G: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
  T: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M7 3h3v8h1V2h3v9h1V4h3v11c0 4-3 7-7 7s-7-3-7-7v-4h3v3h1V3z"/></svg>',
  Z: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/></svg>',
};
const FACE = {
  F: ['Forward', 'Step 1 closer.'],
  B: ['Back', 'Step 1 away.'],
  S: ['Strike', `${R.strike} damage up close. Beats a grab.`],
  G: ['Guard', 'Stops his strike this round.'],
  T: ['Grab', `${R.grabDmg} damage up close. Beats a guard.`],
  Z: ['Rest', `Recover ${2 * R.regen} stamina instead of ${R.regen}.`],
};
const shieldSVG = '<svg class="shield" viewBox="0 0 46 54"><path d="M23 2 43 9v15c0 13-9 22-20 28C12 46 3 37 3 24V9Z" fill="#5f7891" stroke="#fff" stroke-width="3"/></svg>';

function cardHTML(a, { cls = '', attrs = '' } = {}) {
  const big = a === 'S' ? `<b>${R.strike}</b>` : a === 'T' ? `<b>${R.grabDmg}</b>` : '';
  return `<button class="card ${a} ${cls}" ${attrs}><span class="cost">${COST(a)}</span><div class="art">${ICON[a]}${big}</div><div class="nm">${FACE[a][0]}</div><div class="tx">${FACE[a][1]}</div></button>`;
}

function render() {
  const s = ui.shown;
  const mine = ui.busy || s.winner !== null ? [] : legal(s, ME);
  $('myhand').innerHTML = ORDER.map(a => cardHTML(a, { cls: (mine.includes(a) ? 'ok' : (ui.busy ? '' : 'spent')) + (ui.picks[ME] === a ? ' picked' : ''), attrs: `data-a="${a}"${mine.includes(a) ? '' : ' disabled'}` })).join('');
  $('opphand').innerHTML = ORDER.map(a => cardHTML(a, { cls: (ui.picks[BOT] === a ? 'picked' : ui.picks[BOT] ? 'spent' : (legal(s, BOT).includes(a) ? '' : 'spent')), attrs: 'disabled' })).join('');
  let line = '';
  for (let k = 0; k < L; k++) line += '<div class="cell"></div>';
  for (const side of [ME, BOT]) {
    const left = ((s.pos[side] + 0.5) / L) * 100;
    let gems = ''; for (let i = 0; i < R.cap; i++) gems += `<i class="${i < s.st[side] ? 'on' : ''}"></i>`;
    const off = s.off && s.off[side] ? ' off' : '';
    const guard = ui.guardUp && ui.guardUp[side] ? shieldSVG : '';
    line += `<div class="fighter ${side === ME ? 'me' : 'him'}${off}" id="f${side}" style="left:${left}%">${Math.max(0, s.hp[side])}${guard}<div class="stam">${gems}</div></div>`;
  }
  $('line').innerHTML = line;
  $('history').innerHTML = ui.hist.slice(-22).map(h => h.sep ? '<div class="hist sep"></div>' : `<div class="hist ${h.who}"><span class="hn">${FACE[h.a][0]}</span><span class="ho ${h.cls}">${h.out}</span></div>`).join('');
  $('levels').innerHTML = '';
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
function hit(side) { const f = $('f' + side); if (f) { f.classList.remove('hit'); void f.offsetWidth; f.classList.add('hit'); } }

async function play(a) {
  if (ui.busy || ui.s.winner !== null) return;
  const tok = ui.token;
  ui.busy = true; ui.picks = [a, null]; render();
  await wait(250);
  const b = bot(ui.s, BOT, ui.rng);
  if (tok !== ui.token) return;
  ui.picks = [a, b]; render();               // reveal
  await wait(700);
  const prev = ui.s, ev = [];
  const next = resolve(prev, [a, b], ev);
  // 1. steps
  ui.shown = { ...prev, pos: next.pos.slice(), st: prev.st.map((x, i) => x - COST([a, b][i])), off: [0, 0] };
  ui.guardUp = [a === 'G' ? 1 : 0, b === 'G' ? 1 : 0];
  render();
  for (const e of ev) if (e.t === 'clash') { floatAt(ME, 'Bump', 'miss'); floatAt(BOT, 'Bump', 'miss'); }
  await wait(450);
  // 2. blows
  const out = [{ out: '', cls: '' }, { out: '', cls: '' }];
  ui.shown = { ...ui.shown, hp: next.hp.slice() };
  render();
  for (const e of ev) {
    const o = 1 - e.side;
    if (e.t === 'hit' || e.t === 'grab') { floatAt(o, '−' + e.dmg, 'dmg'); hit(o); out[e.side] = { out: '−' + e.dmg, cls: 'dmg' }; }
    if (e.t === 'blocked') { floatAt(o, 'Blocked', 'block'); out[e.side] = { out: 'blocked', cls: 'block' }; }
    if (e.t === 'miss') { floatAt(o, 'Miss', 'miss'); out[e.side] = { out: 'miss', cls: 'miss' }; }
    if (e.t === 'grabfail') { floatAt(e.side, 'Grab stopped', 'miss'); out[e.side] = { out: 'stopped', cls: 'miss' }; }
    if (e.t === 'grabclash') out[e.side] = { out: 'clash', cls: 'miss' };
  }
  ui.hist.push({ who: 'me', a, ...out[ME] }, { who: 'him', a: b, ...out[BOT] }, { sep: true });
  await wait(900);
  // 3. recovery, next round
  ui.s = next; ui.shown = next; ui.picks = [null, null]; ui.guardUp = [0, 0];
  ui.busy = false;
  render();
  if (next.winner !== null) finish();
}

function finish() {
  const w = ui.s.winner;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="again">Play again</button>`;
  $('over').classList.add('show');
}

function start() {
  ui.token++;
  ui.s = newMatch(); ui.shown = ui.s; ui.hist = []; ui.busy = false; ui.picks = [null, null]; ui.guardUp = [0, 0];
  $('over').classList.remove('show');
  render();
}

document.addEventListener('click', (e) => {
  const t = e.target.closest('button');
  if (!t || t.disabled) return;
  if (t.dataset.a) { play(t.dataset.a); return; }
  if (t.id === 'restart' || t.id === 'again') start();
});
start();
