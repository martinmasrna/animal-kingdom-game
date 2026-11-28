// Bust duel as a game screen against Expert. Every action goes through legalActions/act and is
// animated from the events it emits; the bot acts one action at a time.

import { CARDS, BUST, ROUNDS, BUST_COIN, newMatch, act, legalActions, linePower } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-27-tally';
const expert = expertBot({ iters: 1500 });
const ui = { s: null, busy: false, over: false, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, newCard: [null, null] };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const SHORT = { SP: 'Their line +1 strain.', PE: 'See your top card.', TR: 'Bought: remove a discard.' };
const strainHTML = (n) => n > 0 ? `<span class="str">${'<i></i>'.repeat(n)}</span>` : n < 0 ? `<span class="str calm">${'<i></i>'.repeat(-n)}</span>` : '';
function cardHTML(id, { cls = '', attrs = '', cost = false, tag = 'div' } = {}) {
  const c = CARDS[id];
  const tx = SHORT[id] ? `<div class="tx">${SHORT[id]}</div>` : '';
  return `<${tag} class="card ${cls}" ${attrs}>${cost ? `<span class="cgem">${c.cost}</span>` : ''}<div class="art"><span class="big">${c.pow}</span>${strainHTML(c.str)}</div><div class="nm">${c.name}</div>${tx}</${tag}>`;
}
function mini(id) { const c = CARDS[id]; return `<span class="mini${c.str > 0 ? ' risk' : c.str < 0 ? ' calm' : ''}">${c.pow}${c.str > 0 ? '<b>' + '•'.repeat(c.str) + '</b>' : ''}</span>`; }
const order = (ids) => ids.slice().sort((a, b) => CARDS[b].str - CARDS[a].str || CARDS[a].pow - CARDS[b].pow);

// ------------------------------------------------------------------ rendering
const myMove = () => !ui.busy && !ui.over && ui.s.turn === ME;
function sideHTML(side) {
  const s = ui.s, P = s.p[side];
  const peek = side === ME && P.peek !== null && P.deck.length ? `<div class="peek">${cardHTML(P.peek, { cls: 'small' })}</div>` : '';
  return `<div class="life s${side} ${ui.fx['life' + side] || ''}" id="life${side}">${P.life}</div>
    <div class="piles"><div class="pile s${side}">${P.deck.length}${peek}</div><div class="pile disc">${P.disc.length}</div></div>
    <div class="comp">${order(P.deck).map(mini).join('')}</div>`;
}
function lineHTML(side) {
  const s = ui.s, P = s.p[side];
  const cards = P.line.map((id, k) => cardHTML(id, { cls: (k === P.line.length - 1 && ui.newCard[side] === P.line.length ? 'new ' : '') + 's' + side })).join('');
  let pips = ''; for (let i = 0; i < BUST; i++) pips += `<i class="${i < P.strain ? 'on' : ''}"></i>`;
  const state = P.bust ? ' bust' : P.stop ? ' stopped' : (s.phase === 'line' && s.turn === side && s.winner === null ? ' active' : '');
  const won = s.phase !== 'line' && s.last && s.last.loser === 1 - side ? ' won' : '';
  return `<div class="tot${state}${won}"><b>${linePower(P)}</b><span class="pips">${pips}</span></div><div class="cards">${cards}</div>`;
}
function marketHTML() {
  const s = ui.s, L = myMove() ? legalActions(s) : [];
  const cards = s.market.map((id, i) => { const ok = L.some(a => a.t === 'buy' && a.i === i); return cardHTML(id, { cost: true, tag: 'button', cls: 'mk' + (ok ? ' ok' : ''), attrs: `data-buy="${i}"${ok ? '' : ' disabled'}` }); }).join('');
  let rounds = ''; for (let i = 1; i <= ROUNDS; i++) rounds += `<i class="${i < s.round ? 'past' : i === s.round ? 'now' : ''}"></i>`;
  return `<div class="rounds">${rounds}</div><div class="mcards">${cards}<div class="pile mdeck">${s.mdeck.length}</div></div>`;
}
function controlsHTML() {
  const s = ui.s, L = myMove() ? legalActions(s) : [];
  if (s.phase === 'line') {
    const d = L.some(a => a.t === 'draw'), st = L.some(a => a.t === 'stop');
    return `<button id="draw"${d ? '' : ' disabled'}>Draw</button><button id="stop"${st ? '' : ' disabled'}>Stop</button>`;
  }
  if (s.phase === 'buy') {
    const P = s.p[s.turn], coin = P.bust ? BUST_COIN : P.pow;
    return `<span class="coin s${s.turn}">${coin}</span><button id="pass"${L.length ? '' : ' disabled'}>Pass</button>`;
  }
  return '';
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  for (const side of [0, 1]) { $('side' + side).innerHTML = sideHTML(side); $('line' + side).innerHTML = lineHTML(side); }
  $('market').innerHTML = marketHTML();
  $('controls').innerHTML = controlsHTML();
  const trim = s.phase === 'trim' && s.turn === ME && !ui.busy && !ui.over;
  $('trim').innerHTML = trim ? `<div class="trimbox">${[...new Set(s.p[ME].disc)].map(id => cardHTML(id, { tag: 'button', cls: 'ok', attrs: `data-trim="${id}"` })).join('')}</div>` : '';
  $('trim').classList.toggle('show', trim);
  $('history').innerHTML = ui.hist.slice(-16).map(h => `<div class="hist s${h.side}">${h.html}</div>`).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
async function spotlight(id) {
  const g = $('game').getBoundingClientRect(), b = $('market').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(id, { cost: true });
  await wait(800);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const buyE = ev.find(e => e.t === 'buy');
  if (buyE && buyE.side === BOT) await spotlight(buyE.card);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  ui.newCard = [null, null];
  for (const e of ev) if (e.t === 'reveal') ui.newCard[e.side] = next.p[e.side].line.length || prev.p[e.side].line.length + 1;
  const clashE = ev.find(e => e.t === 'clash'), roundE = ev.find(e => e.t === 'round');
  // a clash: show the finished lines first, then the hit
  if (roundE) {
    const view = { ...next, p: next.p.map((P, k) => ({ ...P, line: prev.p[k].line.slice(), pow: prev.p[k].pow, strain: prev.p[k].strain, bust: prev.p[k].bust, stop: prev.p[k].stop })) };
    ui.s = view; render(); await wait(200);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  }
  ui.s = next;
  if (clashE && clashE.loser !== null) ui.fx['life' + clashE.loser] = 'shake';
  render();
  for (const e of ev) {
    if (e.t === 'clash' && e.loser !== null) floatAt(centerOf($('life' + e.loser)), '−' + e.n);
    if (e.t === 'bust') floatAt(centerOf($('line' + e.side).querySelector('.tot')), '✕', 'bad');
  }
  // history
  const side = prev.turn;
  for (const e of ev) {
    if (e.t === 'reveal') ui.hist.push({ side: e.side, html: `<span class="chip">${CARDS[e.card].pow}${CARDS[e.card].str > 0 ? '•'.repeat(CARDS[e.card].str) : ''}</span>` });
    if (e.t === 'stop') ui.hist.push({ side: e.side, html: `<span class="chip stopc">■</span>` });
    if (e.t === 'bust') ui.hist.push({ side: e.side, html: `<span class="chip bustc">✕</span>` });
    if (e.t === 'clash') ui.hist.push({ side: e.loser === null ? 2 : 1 - e.loser, html: `<span class="ho">${e.pow[0]} : ${e.pow[1]}</span>${e.loser !== null ? `<span class="ho dmg">−${e.n}</span>` : ''}` });
    if (e.t === 'buy') ui.hist.push({ side: e.side, html: `<span class="chip buyc">${CARDS[e.card].name}</span>` });
    if (e.t === 'trim') ui.hist.push({ side: e.side, html: `<span class="chip">✂ ${CARDS[e.card].name}</span>` });
  }
  if (next.winner !== null) { await wait(500); finish(); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  else if (clashE || roundE) await wait(700);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
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
  ui.over = false; ui.hist = []; ui.newCard = [null, null];
  $('over').classList.remove('show');
  ui.busy = true; render();
  await wait(600);
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
  if (!b || b.disabled) return;
  if (b.id === 'rematch' || b.id === 'newmatch') return startMatch();
  if (!myMove()) return;
  if (b.id === 'draw') return doAct({ t: 'draw' });
  if (b.id === 'stop') return doAct({ t: 'stop' });
  if (b.id === 'pass') return doAct({ t: 'pass' });
  if (b.dataset.buy !== undefined) return doAct({ t: 'buy', i: +b.dataset.buy });
  if (b.dataset.trim !== undefined) return doAct({ t: 'trim', card: b.dataset.trim });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rulesbox').classList.remove('show'); });
startMatch();
