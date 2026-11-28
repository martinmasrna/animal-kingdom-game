// Junk war as a game screen against the Expert. Every move goes through legalActions/act; the
// bot's moves play out one at a time. The win tally is kept in this browser and decides who goes
// first (alternating).

import { CARDS, TARGET, newMatch, act, legalActions, owned } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-48-junk-tally';
const expert = expertBot({ budget: 2000 });
const ui = { s: null, view: null, busy: false, over: false, fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const KIND = { Coin: 'coin', Coin2: 'coin', Coin3: 'coin', Score: 'pts', Score2: 'pts', Score4: 'pts', Foul: 'atk', Foul2: 'atk', Thief: 'atk', Draw: 'util', Purge: 'util', Clean: 'util', Junk: 'junk' };
const BIG = { Coin: '+1', Coin2: '+2', Coin3: '+3', Score: '+1', Score2: '+2', Score4: '+4', Foul: '+1', Foul2: '+1', Thief: '+2', Draw: '+2', Purge: '✕2', Clean: '+1', Junk: '' };
const TEXT = { Coin: '+1 coin', Coin2: '+2 coin', Coin3: '+3 coin', Score: '+1 point', Score2: '+2 points', Score4: '+4 points', Draw: 'Draw 2 cards and play them',
  Foul: '+1 coin. A Junk on top of their deck', Foul2: '+1 point. 2 Junk into their discard', Purge: 'Remove up to 2 other cards in your hand', Clean: '+1 coin. Remove a Junk you own',
  Thief: '+2 coin. Take 1 of their points', Junk: '' };
function cardHTML(id, { cls = '', attrs = '', tag = 'button' } = {}) {
  const c = CARDS[id];
  const gem = c.cost ? `<span class="cgem">${c.cost}</span>` : '';
  return `<${tag} class="card k-${KIND[id]} ${cls}" ${attrs}>${gem}<div class="art"><span class="big">${BIG[id]}</span></div><div class="nm">${c.name}</div><div class="tx">${TEXT[id]}</div></${tag}>`;
}

// ------------------------------------------------------------------ rendering
const mine = () => !ui.busy && !ui.over && ui.view.toMove === ME && ui.view.winner === null;
function infoHTML(side) {
  const p = ui.view.p[side], junk = owned(p).filter(x => x === 'Junk').length;
  const backs = side === BOT ? `<div class="backs">${'<i class="back"></i>'.repeat(p.hand.length)}</div>` : '';
  return `<div class="pts s${side}" id="pts${side}">${p.points}</div><div class="track s${side}"><i style="width:${Math.min(100, p.points / TARGET * 100)}%"></i></div>
    <div class="piles"><span class="pile s${side}" id="deck${side}">${p.deck.length}</span><span class="pile disc" id="disc${side}">${p.discard.length}</span>${junk ? `<span class="junkin">Junk <b>${junk}</b></span>` : ''}${backs}</div>`;
}
function marketHTML() {
  const s = ui.view, canBuy = mine() && s.phase === 'buy';
  const row = s.row.map((id, i) => {
    if (!id) return `<div class="slot"></div>`;
    const ok = canBuy && CARDS[id].cost <= s.coin;
    return cardHTML(id, { cls: (ok ? 'ok' : canBuy ? 'no' : '') + (ui.fx['row' + i] ? ' ' + ui.fx['row' + i] : ''), attrs: `data-row="${i}" id="row${i}"${ok ? '' : ' disabled'}` });
  }).join('');
  return `<div class="row">${row}</div><div class="mpiles"><span class="pile mkt">${s.market.length}</span><span class="pile junkp">${s.junk}</span></div>`;
}
function tableHTML() {
  const s = ui.view, P = s.p[s.turn];
  return `<div class="played">${P.played.map(id => cardHTML(id, { tag: 'div' })).join('')}</div><div class="pool${s.coin ? '' : ' zero'}" id="pool">${s.coin}</div>`;
}
function handHTML() {
  const s = ui.view, H = s.p[ME].hand, can = mine();
  return H.map((id, i) => {
    const cls = can && s.phase === 'play' ? 'ok' : can && s.phase === 'purge' ? 'purge' : '';
    return cardHTML(id, { cls: cls + (ui.fresh && i >= H.length - ui.fresh ? ' drawn' : ''), attrs: `data-hand="${i}"${cls ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.view, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('info1').innerHTML = infoHTML(BOT); $('info0').innerHTML = infoHTML(ME);
  $('market').innerHTML = marketHTML(); $('table').innerHTML = tableHTML(); $('hand').innerHTML = handHTML();
  const can = mine();
  const buyMore = can && s.phase === 'buy' && legalActions(s).some(a => a.t === 'buy');
  $('side').innerHTML = s.phase === 'purge' && can ? `<button id="stop">Done</button>` : `<button id="endturn" class="${can && s.phase === 'buy' && !buyMore ? 'done' : ''}"${can && s.phase === 'buy' ? '' : ' disabled'}>End turn</button>`;
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(el, text, cls = '') { if (!el) return; const p = centerOf(el), f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function fly(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const g = $('game').getBoundingClientRect(), a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const d = document.createElement('div'); d.className = 'flyer'; d.innerHTML = fromEl.outerHTML; d.style.left = (a.left - g.left) + 'px'; d.style.top = (a.top - g.top) + 'px';
  $('game').appendChild(d);
  const dx = b.left + b.width / 2 - (a.left + a.width / 2), dy = b.top + b.height / 2 - (a.top + a.height / 2);
  await d.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: `translate(${dx}px, ${dy}px) scale(.3)`, opacity: .6 }], { duration: 450, easing: 'ease-in' }).finished;
  d.remove();
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const buyE = ev.find(e => e.t === 'buy');
  if (buyE) { await fly($('row' + buyE.i), $('disc' + buyE.side)); ui.fx['row' + buyE.i] = 'new'; }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  for (const e of ev) { if (e.t === 'draw' && e.side === ME) ui.fresh++; if (e.t === 'turn' && e.side === ME) banner('Your turn'); }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'points') floatAt($('pts' + e.side), (e.n > 0 ? '+' : '−') + Math.abs(e.n), e.n > 0 ? '' : 'bad');
    if (e.t === 'junk') floatAt($(e.where === 'top' ? 'deck' + e.side : 'disc' + e.side), '+Junk', 'junk');
  }
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
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  await run(tok);
}
async function run(tok) {
  while (tok === ui.token && !ui.over && ui.s.toMove === BOT) {
    ui.busy = true; render();
    await wait(ui.s.phase === 'play' ? 420 : 650);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
    if (a.t === 'end') await wait(300);
  }
  if (tok !== ui.token) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (ui.busy || ui.over || ui.s.toMove !== ME) return;
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
  if (!mine() || !b || b.disabled) return;
  const s = ui.view;
  if (b.dataset.hand !== undefined) { const id = s.p[ME].hand[+b.dataset.hand]; return doAct(s.phase === 'purge' ? { t: 'purge', card: id } : { t: 'play', card: id }); }
  if (b.dataset.row !== undefined) return doAct({ t: 'buy', i: +b.dataset.row });
  if (b.id === 'stop') return doAct({ t: 'stop' });
  if (b.id === 'endturn') return doAct({ t: 'end' });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
startMatch();
