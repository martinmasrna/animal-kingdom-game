// 15 Key pieces as a game screen against Expert. Each action is animated from the state before
// and the state after; the win tally is kept in this browser and decides who goes first.

import { CARDS, MAX_MANA, KEYS, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-15-tally';
const expert = expertBot({ ...EXPERT, timeMs: 1300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }
const letter = (id) => CARDS[id].name.slice(-1);

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'key') art = `<span class="big">${letter(id)}</span><span class="stat h">${c.hp}</span>`;
  else if (c.kind === 'spell') art = `<span class="big">${c.dmg}</span>`;
  else if (c.kind === 'fetch') art = `<span class="big">⌕</span>`;
  else art = `<span class="big">+1</span>`;
  return `<button class="card ${c.kind}${c.guard ? ' guard' : ''} s${side} ${cls}" ${attrs}>${c.kind === 'coin' ? '' : `<span class="cgem">${c.cost}</span>`}<div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.toAct === ME && ui.view.winner === null;
function targetsNow() {
  const out = { pieces: new Set(), board: false, keys: [] };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id) {
      if (a.tgt) out.pieces.add(a.tgt.uid); else if (a.key) out.keys.push(a.key); else out.board = true;
    }
    if (ui.sel.kind === 'unit' && a.t === 'attack' && a.from === ui.sel.uid) out.pieces.add(a.to);
  }
  return out;
}
const canAttack = (uid) => myTurn() && legalActions(ui.view).some(a => a.t === 'attack' && a.from === uid);

// ------------------------------------------------------------------ rendering
function boardHTML(side, T) {
  const B = ui.view.p[side].board.slice().sort((a, b) => (CARDS[a.card].kind === 'key' ? 0 : 1) - (CARDS[b.card].kind === 'key' ? 0 : 1) || (a.card < b.card ? -1 : a.card > b.card ? 1 : a.uid - b.uid));
  return B.map(u => {
    const c = CARDS[u.card];
    let cls = c.kind === 'key' ? ' key' : '';
    if (c.guard) cls += ' guard';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === u.uid) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(u.uid)) cls += ' can';
    if (T.pieces.has(u.uid)) cls += ' tgt';
    if (side === ui.view.toAct && !u.ready && c.kind === 'unit') cls += ' sleep';
    if (ui.fx['u' + u.uid]) cls += ' ' + ui.fx['u' + u.uid];
    const face = c.kind === 'key' ? `<span class="kl">${letter(u.card)}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span>` : `<span class="stat a">${u.atk}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span>`;
    return `<div class="unit s${side}${cls}" id="u${u.uid}" data-side="${side}" data-uid="${u.uid}">${face}</div>`;
  }).join('');
}
function keyRow(side) {
  const P = ui.view.p[side];
  return KEYS.map(k => `<i class="kdot${P.board.some(u => u.card === k) ? ' on' : ''}">${letter(k)}</i>`).join('');
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML(T) {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { coin: 0, key: 1, fetch: 2, unit: 3, spell: 4 };
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost; });
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('keys' + side).innerHTML = keyRow(side); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); }
  $('board0').classList.toggle('tgt', T.board);
  $('hand').innerHTML = handHTML(T);
  $('chooser').innerHTML = T.keys.length ? T.keys.map(k => cardHTML(k, ME, { cls: 'ok pickkey', attrs: `data-key="${k}"` })).join('') : '';
  $('chooser').classList.toggle('show', T.keys.length > 0);
  $('turnbox').innerHTML = `<button id="endturn"${!ui.over && s.toAct === ME && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side, extra = '') {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side) + extra;
  await wait(700);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
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
  ui.s = next;
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'spell')) await spotlight(playE.card, playE.side);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (atkE) await lunge($('u' + atkE.from), $('u' + atkE.to));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['u' + e.uid] = 'new';
    if (e.t === 'hit' && e.hp > 0) ui.fx['u' + e.uid] = 'shake';
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['u' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
  }
  if (playE) {
    const c = CARDS[playE.card], died = ev.some(e => e.t === 'die');
    const chip = c.kind === 'unit' ? c.atk + '/' + c.hp : c.kind === 'key' ? letter(playE.card) : c.kind === 'spell' ? c.dmg : c.kind === 'fetch' ? '⌕' : '+1';
    ui.hist.push({ side: playE.side, kind: c.kind, chip, out: c.kind === 'spell' ? (died ? '✕' : '−' + c.dmg) : c.kind === 'fetch' ? letter(playE.key) : '', cls: died ? 'kill' : 'dmg' });
  }
  if (atkE) { const died = ev.filter(e => e.t === 'die' && e.side !== atkE.side).length; ui.hist.push({ side: atkE.side, kind: 'attack', chip: atkE.atk, out: died ? '✕' : '−' + atkE.atk, cls: died ? 'kill' : 'dmg' }); }
  if (ev.some(e => e.t === 'turn')) await wait(next.toAct === ME ? 600 : 250);
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
  const why = ui.s.why === 'keys' ? (w === ME ? 'Three Keys held' : 'He held three Keys') : ui.s.why === 'deck' ? (w === ME ? 'His deck ran out' : 'Your deck ran out') : '';
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p>${why}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.toAct === BOT) await botTurn(tok); else { ui.busy = false; render(); }
}
async function botTurn(tok) {
  ui.busy = true; render();
  await wait(300);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.toAct !== BOT) break;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 300 : 200);
    if (tok !== ui.token) return;
    await apply(a);
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  if (tok !== ui.token) return;
  if (!ui.over && ui.s.toAct === BOT) return botTurn(tok);
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (!myTurn()) return;
  const T = targetsNow();
  const pk = e.target.closest('[data-key]');
  if (pk && ui.sel) return doAct({ t: 'play', card: ui.sel.id, key: pk.dataset.key });
  const tgt = e.target.closest('.unit');
  if (tgt) {
    const side = +tgt.dataset.side, uid = +tgt.dataset.uid;
    if (ui.sel && T.pieces.has(uid)) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, tgt: { side, uid } });
      return doAct({ t: 'attack', from: ui.sel.uid, to: uid });
    }
    if (side === ME && canAttack(uid)) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === uid ? null : { kind: 'unit', uid }; render(); return; }
  }
  if (ui.sel && ui.sel.kind === 'card' && T.board && e.target.closest('#board0')) return doAct({ t: 'play', card: ui.sel.id });
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], c = CARDS[id];
    if (c.kind === 'coin' || c.kind === 'unit' || c.kind === 'key') return doAct({ t: 'play', card: id });
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled && b.id === 'endturn') return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.__game = { get s() { return ui.s; }, get busy() { return ui.busy; }, get over() { return ui.over; } };
startMatch();
