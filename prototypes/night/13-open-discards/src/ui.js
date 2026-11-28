// Open discards as a game screen against Expert. Each action is animated from the events the
// engine emits; the bot plays one action at a time so every step can be seen. Both discard
// piles lie face-up beside the heroes; a card in the opponent's pile you can take now is lit,
// its gem showing what it costs you (its cost plus 1).

import { CARDS, MAX_MANA, TAX, newMatch, act, isLegal } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-13-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'Unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'Spell') art = `<span class="big">${c.dmg}</span>`;
  else { art = `<span class="big">+1</span>`; tx = `<div class="tx">+1 mana this turn.</div>`; }
  const kind = c.kind === 'Unit' ? 'Minion' : c.kind;
  return `<button class="card ${kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.s.turn === ME;
function targetsNow() {
  const out = { heroes: new Set(), minions: new Set() }, s = ui.s;
  if (!ui.sel || !myTurn()) return out;
  if (ui.sel.kind === 'card') for (const side of [0, 1]) for (let i = -1; i < s.p[side].board.length; i++) if (isLegal(s, { t: 'play', card: ui.sel.id, disc: ui.sel.disc, side, i })) { if (i < 0) out.heroes.add(side); else out.minions.add(side + ':' + i); }
  if (ui.sel.kind === 'minion') { out.heroes.add(BOT); s.p[BOT].board.forEach((_, i) => out.minions.add(BOT + ':' + i)); }
  return out;
}
const canAttack = (i) => myTurn() && isLegal(ui.s, { t: 'attack', from: i, to: -1 });
const canPlay = (id, disc = false) => myTurn() && (CARDS[id].kind === 'Spell' ? isLegal(ui.s, { t: 'play', card: id, disc, side: BOT, i: -1 }) : isLegal(ui.s, { t: 'play', card: id, disc }));

// ------------------------------------------------------------------ rendering
function heroHTML(side, T) {
  const p = ui.s.p[side];
  return `<div class="hero s${side}${T.heroes.has(side) ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-i="-1"><span class="hp">${p.hp}</span></div><div class="disc" id="disc${side}">${discHTML(side)}</div>`;
}
// a discard pile, one small card per kind with a count; in the opponent's pile, what you can take now is lit
function discHTML(side) {
  const pile = ui.s.p[side].discard, ids = [...new Set(pile)].sort((a, b) => CARDS[a].cost - CARDS[b].cost || (a < b ? -1 : 1));
  return ids.map(id => {
    const c = CARDS[id], n = pile.filter(x => x === id).length, theirs = side === BOT;
    const ok = theirs && canPlay(id, true), sel = ui.sel && ui.sel.kind === 'card' && ui.sel.disc && ui.sel.id === id;
    const face = c.kind === 'Unit' ? `${c.atk}/${c.hp}` : c.dmg;
    return `<button class="dcard ${c.kind}${ok ? ' ok' : ''}${sel ? ' sel' : ''}" data-disc="${id}"${ok ? '' : ' disabled'}><span class="dgem">${theirs ? c.cost + TAX : c.cost}</span><b>${face}</b>${n > 1 ? `<i class="dn">${n}</i>` : ''}</button>`;
  }).join('');
}
function boardHTML(side, T) {
  return ui.s.p[side].board.map((m, i) => {
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(i)) cls += ' can';
    if (T.minions.has(side + ':' + i)) cls += ' tgt';
    if (side === ui.s.turn && !m.ready) cls += ' sleep';
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="minion s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}"><span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div>`;
  }).join('');
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME];
  const order = p.hand.map((_, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]], R = { Coin: 0, Unit: 1, Spell: 2 };
    return R[A.kind] - R[B.kind] || A.cost - B.cost || (A.id < B.id ? -1 : 1);
  });
  return order.map(i => {
    const id = p.hand[i], ok = canPlay(id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && !ui.sel.disc && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.s, T = targetsNow();
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME;
  const canAct = mine && !ui.busy && (s.p[ME].hand.some(id => canPlay(id)) || s.p[BOT].discard.some(id => canPlay(id, true)) || s.p[ME].board.some((_, i) => canAttack(i)));
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.minion, .hero').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(700);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl || FAST) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .8}px, ${dy * .8}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out' }).finished;
}
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'Spell')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('m' + atkE.uid), atkE.to < 0 ? $('hero' + (1 - atkE.side) + 'x') : $('m' + atkE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.i >= 0 && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'hit' && e.i < 0) ui.fx['hero' + e.side] = 'shake';
    if (e.t === 'draw' && e.side === ME) ui.fresh++;
  }
  ui.s = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const id = e.i < 0 ? 'hero' + e.side + 'x' : 'm' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'fatigue') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '−' + e.n); }
  }
  if (playE) {
    const c = CARDS[playE.card], hits = ev.filter(e => e.t === 'hit'), died = ev.some(e => e.t === 'die');
    const out = (c.kind === 'Spell' ? (died ? '✕' : hits[0] && hits[0].i < 0 ? '−' + c.dmg + ' face' : '−' + c.dmg) : '') + (playE.disc ? ' ↺' : '');
    const chip = c.kind === 'Unit' ? `${c.atk}/${c.hp}` : c.kind === 'Spell' ? c.dmg : '';
    ui.hist.push({ side: playE.side, kind: c.kind === 'Unit' ? 'Minion' : c.kind, chip, out, cls: died ? 'kill' : hits[0] && hits[0].i < 0 ? 'face' : 'dmg' });
  }
  if (atkE) {
    const died = ev.filter(e => e.t === 'die' && e.side !== atkE.side).length;
    ui.hist.push({ side: atkE.side, kind: 'Attack', chip: atkE.atk, out: atkE.to < 0 ? '−' + atkE.atk + ' face' : died ? '✕' : '−' + atkE.atk, cls: atkE.to < 0 ? 'face' : died ? 'kill' : 'dmg' });
  }
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 600 : 250);
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
  ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  while (!ui.over && ui.s.turn === BOT) {
    await wait(380);
    if (tok !== ui.token || ui.over) return;
    const t0 = performance.now(), a = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(a);
    if (tok !== ui.token) return;
  }
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn() || !isLegal(ui.s, a)) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  if (!ui.over && ui.s.turn === BOT) return botMove(tok);
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (b0 && b0.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const tgt = e.target.closest('.minion, .hero');
  if (tgt && myTurn()) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, disc: ui.sel.disc, side, i });
      return doAct({ t: 'attack', from: ui.sel.i, to: i });
    }
    if (side === ME && i >= 0 && canAttack(i)) { ui.sel = ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i ? null : { kind: 'minion', i }; render(); return; }
  }
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = ui.s.p[ME].hand[i];
    if (CARDS[id].kind === 'Spell') { ui.sel = ui.sel && ui.sel.kind === 'card' && !ui.sel.disc && ui.sel.hand === i ? null : { kind: 'card', id, hand: i, disc: false }; render(); return; }
    return doAct({ t: 'play', card: id, disc: false });
  }
  if (b0 && !b0.disabled && b0.dataset.disc !== undefined) {
    const id = b0.dataset.disc;
    if (CARDS[id].kind === 'Spell') { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.disc && ui.sel.id === id ? null : { kind: 'card', id, disc: true }; render(); return; }
    return doAct({ t: 'play', card: id, disc: true });
  }
  if (b0 && !b0.disabled && b0.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
