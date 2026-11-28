// Response duel as a game screen against Expert. A cast spell waits in the middle while the other
// side may answer it; stored mana shows as amber gems beside each life total.

import { CARDS, MAX_MANA, LIFE, newMatch, act, isLegal } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-14-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, hist: [], fresh: 0, stack: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const big = c.kind === 'Spell' ? (id === 'ST' ? '+2' : id === 'SG' ? '2×3' : c.dmg) : c.kind === 'Coin' ? '+1' : { CA: '✕', WA: '−3', MI: '↺' }[id];
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="big">${big}</span></div><div class="nm">${c.name}</div><div class="tx">${c.text}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myMove = () => !ui.busy && !ui.over && ui.s.toMove === ME;
const responding = () => myMove() && !!ui.s.pending;
const canUse = (id) => myMove() && (ui.s.pending ? isLegal(ui.s, { t: 'respond', card: id }) : isLegal(ui.s, { t: 'cast', card: id }));

// ------------------------------------------------------------------ rendering
function whoHTML(side) {
  const p = ui.s.p[side];
  let st = ''; for (let i = 0; i < p.stored; i++) st += '<i class="sgem"></i>';
  const sg = p.sieges.map(g => `<span class="siege">${g.dmg}<small>×${g.ticks}</small></span>`).join('');
  return `<div class="life s${side}" id="life${side}"><span class="n">${p.life}</span></div><div class="stored">${st}</div><div class="sieges">${sg}</div>`;
}
function stackHTML() {
  if (!ui.stack) return '';
  const k = ui.stack;
  return `<div class="pair">${cardHTML(k.card, k.side, { cls: 'big' + (k.cancelled ? ' gone' : '') })}${k.resp ? cardHTML(k.resp, 1 - k.side, { cls: 'big resp' }) : ''}</div>`;
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME];
  const R = { Coin: 0, Spell: 1, Response: 2 };
  const order = p.hand.map((_, i) => i).sort((a, b) => R[CARDS[p.hand[a]].kind] - R[CARDS[p.hand[b]].kind] || CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost || (p.hand[a] < p.hand[b] ? -1 : 1));
  return order.map(i => {
    const id = p.hand[i], ok = canUse(id);
    let cls = ok ? 'ok' : (myMove() ? 'no' : '');
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind}">${h.name}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('who' + side).innerHTML = whoHTML(side); $('res' + side).innerHTML = resHTML(side); }
  $('stack').innerHTML = stackHTML();
  $('hand').innerHTML = handHTML();
  const mine = myMove();
  if (s.pending && s.toMove === ME) $('turnbox').innerHTML = `<button id="allow" class="allow"${mine ? '' : ' disabled'}>Allow</button>`;
  else {
    const canAct = mine && s.p[ME].hand.some(canUse);
    $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && s.turn === ME ? '' : ' disabled'}>End turn</button>`;
  }
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0;
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function shake(side) { const el = $('life' + side); if (el) { el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake'); } }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const castE = ev.find(e => e.t === 'cast'), respE = ev.find(e => e.t === 'respond');
  if (castE && CARDS[castE.card].kind !== 'Coin') { ui.stack = { card: castE.card, side: castE.side }; render(); await wait(castE.side === BOT ? 900 : 450); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (respE) { ui.stack.resp = respE.card; render(); await wait(800); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (ev.some(e => e.t === 'cancelled')) { ui.stack.cancelled = true; render(); await wait(450); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  // the damage, heals and draws land with the new state
  ui.fresh = ev.filter(e => e.t === 'draw' && e.side === ME).length;
  if (!next.pending) ui.stack = null;
  ui.s = next; render();
  for (const e of ev) {
    if (e.t === 'dmg') { const el = $('life' + e.side); if (el) floatAt(centerOf(el), '−' + e.n); shake(e.side); }
    if (e.t === 'heal') { const el = $('life' + e.side); if (el) floatAt(centerOf(el), '+' + e.n, 'heal'); }
  }
  // history: one line per spell once it has resolved
  const spell = castE && !next.pending ? castE : (respE || ev.some(e => e.t === 'allow')) ? { card: prev.pending.card, side: prev.turn } : null;
  if (spell && CARDS[spell.card].kind !== 'Coin') {
    const dmg = ev.filter(e => e.t === 'dmg' && e.why === spell.card);
    let out = '', cls = '';
    if (ev.some(e => e.t === 'cancelled')) { out = '✕'; cls = 'kill'; }
    else if (dmg.length) { out = (dmg[0].side === spell.side ? '↺ ' : '') + '−' + dmg[0].n; cls = dmg[0].side === spell.side ? 'back' : 'face'; }
    else if (spell.card === 'ST') out = '+2';
    else if (spell.card === 'SG') out = ev.find(e => e.t === 'siege').dmg + '×3';
    else out = '0';
    ui.hist.push({ side: spell.side, kind: 'Spell', name: CARDS[spell.card].name + (respE ? ' · ' + CARDS[respE.card].name : ''), out, cls });
  }
  if (ev.some(e => e.t === 'turn')) { const t = ev.find(e => e.t === 'turn'); if (t.side === ME) banner('Your turn'); await wait(t.side === ME ? 600 : 250); }
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
  ui.over = false; ui.hist = []; ui.stack = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  await botLoop(tok);
}
// the bot moves whenever it has the move; a response window for me with nothing to answer
// with is allowed at once
async function botLoop(tok) {
  ui.busy = true; render();
  for (;;) {
    if (tok !== ui.token || ui.over) return;
    const s = ui.s;
    if (s.toMove === ME && s.pending && !s.p[ME].hand.some(id => isLegal(s, { t: 'respond', card: id }))) { await wait(300); await apply({ t: 'allow' }); continue; }
    if (s.toMove !== BOT) break;
    await wait(420);
    if (tok !== ui.token || ui.over) return;
    const t0 = performance.now(), a = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(a);
  }
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myMove() || !isLegal(ui.s, a)) return;
  const tok = ui.token;
  ui.busy = true;
  await apply(a);
  if (tok !== ui.token) return;
  await botLoop(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (b0 && b0.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  if (!b0 || b0.disabled) return;
  if (b0.dataset.hand !== undefined) { const id = ui.s.p[ME].hand[+b0.dataset.hand]; return doAct(ui.s.pending ? { t: 'respond', card: id } : { t: 'cast', card: id }); }
  if (b0.id === 'allow') return doAct({ t: 'allow' });
  if (b0.id === 'endturn') return doAct({ t: 'end' });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
startMatch();
