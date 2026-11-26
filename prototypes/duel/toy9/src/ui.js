// Toy 9 as a page: stripped-down Star Realms against the expert bot.
import { CARD, sr } from './sr.js';
import { makeRng, pimcTimed } from './bots.js';

const HPS = [30, 40, 50];
const bot = pimcTimed(600, 12);
const ui = { hp: 40, g: null, s: null, me: 0, games: 0, busy: false, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const SHOP = ['E', 'F', 'H', 'X', 'O'];
const COLOR = { C: '#b9a46a', V: '#c0563f', E: '#d1a52a', F: '#d2483c', H: '#9e2328', X: '#5f8f6a', O: '#6c5fa8' };
const TEXT = { C: '+1 trade', V: '+1 combat', E: '+2 trade', F: '+3 combat', H: '+6 combat', X: '+1 trade. Remove a card from your deck.', O: 'Base. Defense 5. +2 combat every turn.' };

function card(c, { cls = '', attrs = '' } = {}) {
  const d = CARD[c];
  const big = d.base ? '5' : d.combat ? '+' + d.combat : '+' + d.trade;
  return `<button class="card sr ${cls}" ${attrs}>${d.cost ? `<span class="cost">${d.cost}</span>` : ''}<div class="art" style="background:${COLOR[c]}"><b>${big}</b></div><div class="nm">${d.name}</div><div class="tx">${TEXT[c]}</div></button>`;
}
function counts(arr) { const m = {}; for (const x of arr) m[x] = (m[x] || 0) + 1; return m; }

function render() {
  const s = ui.s, me = ui.me, him = 1 - me, myTurn = s.turn === me && !ui.busy && ui.g.winner(s) === null;
  const ms = myTurn ? ui.g.moves(s) : [];
  // his side
  const hisBases = Array.from({ length: s.bases[him] }, (_, i) => `<button class="base${ms.includes('AO') ? ' target' : ''}" data-m="AO"${ms.includes('AO') ? '' : ' disabled'}>5</button>`).join('');
  $('his').innerHTML = `<div class="who him"><div class="hero him">${Math.max(0, s.hp[him])}</div><div class="bases">${hisBases}</div></div>`;
  // market
  const buying = myTurn && s.phase === 'buy';
  $('market').innerHTML = `<div class="pools"><span class="pool trade">${s.turn === me ? s.trade : '·'}</span><span class="pool combat">${s.turn === me ? s.combat : '·'}</span></div>
    <div class="row">${SHOP.map(c => card(c, { cls: buying && ms.includes('B' + c) ? 'ok' : (buying ? 'spent' : ''), attrs: `data-m="B${c}"${buying && ms.includes('B' + c) ? '' : ' disabled'}` })).join('')}</div>
    <div class="acts">${buying ? '<button class="act" data-m="B-">Done buying</button>' : ''}${myTurn && s.phase === 'attack' ? `<button class="act hot" data-m="A-">Hit him for ${s.combat}</button>` : ''}${myTurn && s.phase === 'scrap' ? '<button class="act" data-m="X-">Keep everything</button>' : ''}</div>`;
  // my side
  const myBases = Array.from({ length: s.bases[me] }, () => '<div class="base mine">5</div>').join('');
  const scrapping = myTurn && s.phase === 'scrap';
  const hand = s.turn === me ? s.hand[me] : [];
  const disc = counts(s.disc[me]);
  const scrapRow = scrapping ? `<div class="scraprow">${[...new Set(s.hand[me].concat(s.disc[me]))].map(c => `<button class="chip" data-m="X${c}">${CARD[c].name}</button>`).join('')}</div>` : '';
  $('mine').innerHTML = `${scrapRow}<div class="row hand">${hand.map(c => card(c)).join('')}</div>
    <div class="who me"><div class="hero me">${Math.max(0, s.hp[me])}</div><div class="bases">${myBases}</div></div>`;
  // decks
  const all = counts(s.hand[me].concat(s.deck[me], s.disc[me]));
  const hisAll = counts(s.hand[him].concat(s.deck[him], s.disc[him]));
  const list = (m, cls) => `<div class="deck ${cls}">${Object.keys(CARD).filter(c => m[c]).map(c => `<span style="background:${COLOR[c]}">${CARD[c].name} ×${m[c]}</span>`).join('')}</div>`;
  $('decks').innerHTML = list(hisAll, 'him') + list(all, 'me');
  $('levels').innerHTML = HPS.map(h => `<button data-hp="${h}" class="${h === ui.hp ? 'on' : ''}">${h}</button>`).join('');
  $('history').innerHTML = ui.hist.slice(-24).map(h => h.sep ? '<div class="hist sep"></div>' : `<div class="hist ${h.who}"><span class="hn">${h.text}</span></div>`).join('');
}

function describe(m, s) {
  if (m === 'B-' || m === 'X-') return null;
  if (m[0] === 'B') return 'Buys ' + CARD[m[1]].name;
  if (m[0] === 'X') return 'Scraps ' + CARD[m[1]].name;
  if (m === 'AO') return 'Destroys an Outpost';
  if (m === 'A-') return `Hits for ${s.combat}`;
}
function apply(m) {
  const prev = ui.s, side = prev.turn;
  const d = describe(m, prev);
  if (d) ui.hist.push({ who: side === ui.me ? 'me' : 'him', text: d });
  ui.s = ui.g.play(prev, m);
  if (ui.s.turn !== side) ui.hist.push({ sep: true });
  render();
  if (ui.g.winner(ui.s) !== null) finish();
}
function finish() {
  const w = ui.g.winner(ui.s);
  const t = w === 'draw' ? ['Draw', ''] : w === ui.me ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="again">Play again</button>`;
  $('over').classList.add('show');
}
async function botTurn() {
  const tok = ui.token;
  ui.busy = true; render();
  while (ui.g.winner(ui.s) === null && ui.s.turn !== ui.me) {
    await wait(250);
    const m = bot(ui.g, ui.s, ui.rng);
    if (tok !== ui.token) return;
    apply(m);
  }
  ui.busy = false; render();
}
function start() {
  ui.token++;
  ui.g = sr({ hp: ui.hp });
  ui.me = ui.games++ % 2;
  ui.s = ui.g.init(ui.rng); ui.hist = []; ui.busy = false;
  $('over').classList.remove('show');
  render();
  if (ui.s.turn !== ui.me) setTimeout(botTurn, 400);
}
document.addEventListener('click', (e) => {
  const t = e.target.closest('button');
  if (!t) return;
  if (t.id === 'restart' || t.id === 'again') { start(); return; }
  if (t.dataset.hp) { ui.hp = +t.dataset.hp; start(); return; }
  if (t.disabled || ui.busy || !t.dataset.m) return;
  if (!ui.g.moves(ui.s).includes(t.dataset.m)) return;
  apply(t.dataset.m);
  if (ui.s.turn !== ui.me && ui.g.winner(ui.s) === null) setTimeout(botTurn, 300);
});
start();
