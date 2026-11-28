// Momentum rope as a game screen against Expert. Every action goes through legalActions/act and is
// animated from the events it emits; the bot plays one card at a time. The human is seat 0 and
// pushes toward the right end (+8).

import { CARDS, END, MAX_MANA, ROUNDS, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-09-tally';
const expert = expertBot({ iters: 1000 });
const ui = { s: null, busy: false, over: false, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const GLYPH = { SHO: '→1', JOL: '→2', HEA: '»1', BIG: '»2', CHK: '0', REV: '⇄', ANC: '▮', SUR: '»→', DR2: '+2', COIN: '+1' };
const KIND = { SHO: 'k-push', JOL: 'k-push', HEA: 'k-vel', BIG: 'k-vel', SUR: 'k-vel', CHK: 'k-stop', REV: 'k-stop', ANC: 'k-stop', DR2: 'k-draw', COIN: 'k-coin' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  return `<button class="card ${KIND[id]} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="big">${GLYPH[id]}</span></div><div class="nm">${c.name}</div><div class="tx">${id === 'ANC' ? 'Blocks moves toward you until your next turn.' : id === 'SUR' ? 'Marker moves by the velocity now.' : c.text}</div></button>`;
}

const myTurn = () => !ui.busy && !ui.over && ui.s.turn === ME;
const legal = () => myTurn() ? legalActions(ui.s) : [];

// ------------------------------------------------------------------ rendering
const xOf = (pos) => (100 * (pos + END) / (2 * END)) + '%';
function ropeHTML() {
  const s = ui.s;
  let h = '<div class="goal g1"></div><div class="goal g0"></div><div class="rail">';
  for (let x = -END; x <= END; x++) h += `<span class="sp${x === 0 ? ' mid' : ''}" style="left:${xOf(x)}"></span>`;
  h += '</div>';
  if (s.vel) {
    const a = Math.min(s.pos, s.pos + s.vel), b = Math.max(s.pos, s.pos + s.vel);
    h += `<div class="vel ${s.vel > 0 ? 'right' : 'left'}" style="left:${xOf(Math.max(-END, a))};right:calc(100% - ${xOf(Math.min(END, b))})"><b>${Math.abs(s.vel)}</b></div>`;
  }
  if (s.p[0].anchor) h += `<div class="anc s0" style="left:${xOf(s.pos)}"></div>`;
  if (s.p[1].anchor) h += `<div class="anc s1" style="left:${xOf(s.pos)}"></div>`;
  h += `<div class="marker ${ui.fx.marker || ''}" style="left:${xOf(s.pos)}">${s.pos > 0 ? '+' + s.pos : s.pos}</div>`;
  return h;
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME], L = legal();
  const R = { COIN: 0, SHO: 1, JOL: 2, HEA: 3, BIG: 4, SUR: 5, CHK: 6, REV: 7, ANC: 8, DR2: 9 };
  const order = p.hand.map((_, i) => i).sort((a, b) => R[p.hand[a]] - R[p.hand[b]]);
  return order.map(i => {
    const id = p.hand[i], ok = L.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('rope').innerHTML = ropeHTML();
  const round = Math.ceil(s.turnNo / 2);
  let r = ''; for (let i = 1; i <= ROUNDS; i++) r += `<i class="${i < round ? 'past' : i === round ? 'now' : ''}"></i>`;
  $('rounds').innerHTML = r;
  for (const side of [0, 1]) $('res' + side).innerHTML = resHTML(side);
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, more = legal().some(a => a.t !== 'end');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !more ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-12).map(h => `<div class="hist s${h.side}">${h.html}</div>`).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('rope').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top - 10) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(850);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play');
  if (playE && playE.side === BOT) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  // the end-of-turn move first, then the next turn's start
  const endE = ev.find(e => e.t === 'endturn');
  if (endE) {
    const mv = ev.find(e => e.t === 'move' && e.why === 'vel') || ev.find(e => e.t === 'blocked' && e.why === 'vel');
    if (mv) { ui.s = { ...prev, pos: mv.t === 'move' ? mv.to : prev.pos }; ui.fx.marker = mv.t === 'move' ? 'slide' : 'thud'; render(); await wait(650); }
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  }
  let drawn = 0;
  for (const e of ev) {
    if (e.t === 'turn' && e.side === ME) banner('Your turn');
    if (e.t === 'draw' && e.side === ME) drawn++;
    if (e.t === 'move' && e.why !== 'vel') ui.fx.marker = 'slide';
    if (e.t === 'blocked' && e.why !== 'vel') ui.fx.marker = 'thud';
  }
  ui.fresh = drawn;
  ui.s = next; render();
  if (playE) {
    const mv = ev.find(e => e.t === 'move'), bl = ev.find(e => e.t === 'blocked');
    const out = mv ? (mv.to - mv.from > 0 ? '+' : '') + (mv.to - mv.from) : bl ? '▮' : '';
    ui.hist.push({ side: playE.side, html: `<span class="chip ${KIND[playE.card]}">${GLYPH[playE.card]}</span><span class="ho">${CARDS[playE.card].name}</span><span class="ho mv">${out}</span>` });
  }
  if (endE) {
    const mv = ev.find(e => e.t === 'move' && e.why === 'vel');
    ui.hist.push({ side: endE.side, html: `<span class="chip end">⟳</span><span class="ho mv">${mv ? (mv.to - mv.from > 0 ? '+' : '') + (mv.to - mv.from) : ''}</span>` });
  }
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 500 : 250);
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
  ui.over = false; ui.hist = [];
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  return loop(tok);
}
async function loop(tok) {
  while (tok === ui.token && !ui.over && ui.s.turn === BOT) {
    ui.busy = true; render();
    await wait(400);
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
  if (!myTurn()) return;
  if (b.dataset.hand !== undefined) return doAct({ t: 'play', card: ui.s.p[ME].hand[+b.dataset.hand] });
  if (b.id === 'endturn') return doAct({ t: 'end' });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rulesbox').classList.remove('show'); });
startMatch();
