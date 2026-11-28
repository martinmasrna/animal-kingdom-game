// Claims as a game screen against the Expert. Every move goes through legalActions/act, the
// bot's moves play out one at a time; the win tally is kept in this browser and decides who
// goes first (alternating).

import { CARDS, LIST, MAX_MANA, BOARD, needsTarget, newMatch, act, legalActions } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-31-claims-tally';
const expert = expertBot({ budget: 6000, depth: 10 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, reveal: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '', tag = 'button' } = {}) {
  const c = CARDS[id];
  let art, tx = '';
  if (c.kind === 'Unit') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>`;
  else { art = `<span class="big">${c.dmg || '+' + c.draw}</span>`; tx = `<div class="tx">${c.dmg ? c.dmg + ' damage' : 'Draw 2 cards'}</div>`; }
  return `<${tag} class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</${tag}>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME && ui.view.toMove === ME && !ui.view.pending;
const legal = () => myTurn() ? legalActions(ui.view) : [];
function targetsNow() {
  const out = { lives: new Set(), units: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legal()) {
    if (ui.sel.kind === 'claim' && a.t === 'play' && a.card === ui.sel.id && a.name === ui.sel.name && a.target) { if (a.target.i < 0) out.lives.add(a.target.side); else out.units.add(a.target.side + ':' + a.target.i); }
    if (ui.sel.kind === 'unit' && a.t === 'attack' && a.from === ui.sel.i) { if (a.to < 0) out.lives.add(BOT); else out.units.add(BOT + ':' + a.to); }
  }
  return out;
}
const canAttack = (i) => legal().some(a => a.t === 'attack' && a.from === i);

// ------------------------------------------------------------------ rendering
function infoHTML(side, T) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += i < p.maxMana ? `<i class="gemc${i < p.mana ? ' on' : ''}"></i>` : '';
  const counts = {}; for (const id of p.discard) counts[id] = (counts[id] || 0) + 1;
  const disc = LIST.filter(id => counts[id]).map(id => `<span class="dc">${CARDS[id].name}${counts[id] > 1 ? ` <i>×${counts[id]}</i>` : ''}</span>`).join('');
  const coin = p.coin ? (side === ME && myTurn() ? `<button class="coin" id="coinbtn">+1</button>` : `<span class="coin">+1</span>`) : '';
  const backs = side === BOT ? `<div class="backs">${'<i class="back"></i>'.repeat(p.hand.length)}</div>` : '';
  return `<div class="life s${side}${T.lives.has(side) ? ' tgt' : ''} ${ui.fx['life' + side] || ''}" id="life${side}" data-side="${side}" data-i="-1">${p.life}</div>
    <div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div>${coin}<div class="pile s${side}">${p.deck.length}</div>${backs}<div class="disc">${disc}</div>`;
}
function boardHTML(side, T) {
  return ui.view.p[side].board.map((m, i) => {
    let cls = m.up ? '' : ' down';
    if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(i)) cls += ' can';
    if (T.units.has(side + ':' + i)) cls += ' tgt';
    if (side === ui.view.turn && !m.ready) cls += ' sleep';
    if (ui.fx['u' + m.uid]) cls += ' ' + ui.fx['u' + m.uid];
    const real = side === ME && !m.up && m.real !== m.name ? `<span class="real">${CARDS[m.real].name}</span>` : '';
    return `<div class="unit s${side}${cls}" id="u${m.uid}" data-side="${side}" data-i="${i}"><span class="un">${CARDS[m.name].name}</span>${real}<span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div>`;
  }).join('');
}
function handHTML() {
  const p = ui.view.p[ME], L = legal();
  const order = p.hand.map((_, i) => i).sort((a, b) => CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost || LIST.indexOf(p.hand[a]) - LIST.indexOf(p.hand[b]));
  return order.map(i => {
    const id = p.hand[i], ok = L.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && (ui.sel.kind === 'card' || ui.sel.kind === 'claim') && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function namesHTML() {
  if (!ui.sel || (ui.sel.kind !== 'card' && ui.sel.kind !== 'claim') || !myTurn()) return '';
  const L = legal();
  return LIST.map(name => {
    const ok = L.some(a => a.t === 'play' && a.card === ui.sel.id && a.name === name);
    let cls = (ok ? 'ok' : '') + (name === ui.sel.id ? ' truth' : '') + (ui.sel.kind === 'claim' && ui.sel.name === name ? ' sel' : '');
    return cardHTML(name, ME, { cls, attrs: `data-name="${name}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function spotHTML() {
  const pd = ui.view.pending, R = ui.reveal;
  if (!pd && !R) return '';
  const side = R ? R.side : pd.side, name = R ? R.name : pd.name;
  const c = CARDS[name];
  const claim = `<div class="claimback s${side}"><span class="q">?</span><span>${c.name}</span><span>${c.kind === 'Unit' ? c.atk + ' / ' + c.hp : c.dmg ? c.dmg + ' damage' : 'Draw 2'}</span></div>`;
  const real = R ? cardHTML(R.real, side, { tag: 'div', cls: 'flip ' + (R.real === R.name ? 'true' : 'lie') }) : '';
  const btns = pd && !R && pd.side === BOT && ui.view.toMove === ME && !ui.busy ? `<div class="btns"><button id="challenge">Challenge</button><button id="letpass">Let it stand</button></div>` : '';
  return `<div class="pair">${claim}${real}</div>${btns}`;
}
function histHTML(h) {
  const real = h.real && h.real !== h.name ? `<span class="chip real">${CARDS[h.real].name}</span>` : '';
  const mark = h.res === 'caught' ? '<span class="x">✗ −3</span>' : h.res === 'true' ? '<span class="v">✓</span>' : '';
  if (h.kind === 'attack') return `<div class="hist s${h.side}">⚔ ${h.atk} → ${h.to}</div>`;
  return `<div class="hist s${h.side}"><span class="chip">${CARDS[h.name].name}</span>${real}${mark}</div>`;
}
function render() {
  const s = ui.view, T = targetsNow();
  const t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  for (const side of [0, 1]) { $('info' + side).innerHTML = infoHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); }
  $('hand').innerHTML = handHTML();
  $('names').innerHTML = namesHTML();
  const sp = spotHTML(); $('spot').innerHTML = sp; $('spot').classList.toggle('show', !!sp);
  const mine = !ui.over && s.turn === ME && !s.pending, canAct = myTurn() && legal().some(a => a.t !== 'end');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${myTurn() ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-16).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit, .life').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
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
  const atkE = ev.find(e => e.t === 'attack'), chE = ev.find(e => e.t === 'challenge'), claimE = ev.find(e => e.t === 'claim');
  const revE = ev.find(e => e.t === 'reveal');
  if (atkE) await lunge($('u' + atkE.uid), atkE.to < 0 ? $('life' + (1 - atkE.side)) : $('u' + atkE.tuid));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const pd = prev.pending;
  if (chE) { ui.reveal = { side: pd.side, name: pd.name, real: pd.card }; render(); await wait(1300); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  else if (revE && pd && CARDS[pd.name].kind === 'Spell') { ui.reveal = { side: pd.side, name: pd.name, real: pd.card }; render(); await wait(pd.side === BOT ? 1000 : 600); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  ui.reveal = null;
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['u' + e.uid] = 'new';
    if (e.t === 'hit' && e.i >= 0) ui.fx['u' + e.uid] = 'shake';
    if ((e.t === 'hit' && e.i < 0) || e.t === 'penalty') ui.fx['life' + e.side] = 'shake';
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before[e.i < 0 ? 'life' + e.side : 'u' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'penalty' || e.t === 'fatigue') { const p = before['life' + e.side]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') {
      const p = before['u' + e.uid]; if (p) ghost(p);
      const h = ui.hist.find(x => x.uid === e.uid); if (h) h.real = e.real;
    }
  }
  // history: one line per claim (its fate filled in as it is learned), one per attack
  if (claimE) ui.hist.push({ side: claimE.side, kind: 'claim', name: claimE.name });
  if (pd && (chE || ev.some(e => e.t === 'pass'))) {
    const h = ui.hist[ui.hist.length - 1];
    if (h && h.kind === 'claim') {
      if (chE) { h.real = pd.card; h.res = chE.honest ? 'true' : 'caught'; }
      if (revE) h.real = revE.real;
      const sm = ev.find(e => e.t === 'summon'); if (sm) h.uid = sm.uid;
      if (pd.side === ME) h.real = pd.card;
    }
  }
  if (atkE) ui.hist.push({ side: atkE.side, kind: 'attack', atk: prev.p[atkE.side].board[atkE.from].atk, to: atkE.to < 0 ? '♥' : CARDS[prev.p[1 - atkE.side].board[atkE.to].name].name });
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
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null; ui.reveal = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  await run(tok);
}
// The bot moves while the move is its own; the page waits whenever the move is the player's.
async function run(tok) {
  while (tok === ui.token && !ui.over && ui.s.toMove === BOT) {
    ui.busy = true; render();
    await wait(ui.s.pending ? 700 : 450);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
  }
  if (tok !== ui.token) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (ui.busy || ui.over || ui.s.toMove !== ME) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  await apply(a);
  await run(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if (b && b.id === 'rulesclose') { $('rules').classList.remove('show'); return; }
  if (e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && !b.disabled && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (b && b.id === 'challenge') return doAct({ t: 'challenge' });
  if (b && b.id === 'letpass') return doAct({ t: 'pass' });
  if (!myTurn()) return;
  const tgt = e.target.closest('.unit, .life');
  if (tgt) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'claim') return doAct({ t: 'play', card: ui.sel.id, name: ui.sel.name, target: { side, i } });
      return doAct({ t: 'attack', from: ui.sel.i, to: i });
    }
    if (side === ME && i >= 0 && canAttack(i)) { ui.sel = ui.sel && ui.sel.kind === 'unit' && ui.sel.i === i ? null : { kind: 'unit', i }; render(); return; }
  }
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i];
    ui.sel = ui.sel && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled && b.dataset.name !== undefined && ui.sel && ui.sel.hand !== undefined) {
    const name = b.dataset.name;
    if (needsTarget(name)) { ui.sel = { kind: 'claim', id: ui.sel.id, hand: ui.sel.hand, name }; render(); return; }
    return doAct({ t: 'play', card: ui.sel.id, name });
  }
  if (b && b.id === 'coinbtn') return doAct({ t: 'coin' });
  if (b && b.id === 'endturn' && !b.disabled) return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
startMatch();
