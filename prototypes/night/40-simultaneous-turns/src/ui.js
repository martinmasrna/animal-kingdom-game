// 40 Simultaneous turns as a game screen against Expert. You plan the round (cards, spell
// targets, each unit's attack), press Go; Expert plans without seeing yours; both plans are
// shown, then the round resolves step by step: spells, new units, all attacks at once.

import { CARDS, BOARD, MAX_MANA, newMatch, act, planError } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-40-tally';
const expert = expertBot({ ...EXPERT, timeMs: 1500 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, plan: null, shown: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'unit' ? `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>` : `<span class="big">${c.dmg}</span>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ the plan being made
const planning = () => !ui.busy && !ui.over && ui.s.winner === null && ui.s.toAct === ME;
const newPlan = () => ({ plays: [], attacks: new Map() });
function planObj() { return { t: 'plan', plays: ui.plan.plays.map(x => x.tgt ? { card: x.card, tgt: x.tgt } : { card: x.card }), attacks: [...ui.plan.attacks].map(([from, to]) => ({ from, to })) }; }
function manaLeft() { return ui.s.p[ME].mana - ui.plan.plays.reduce((x, p) => x + CARDS[p.card].cost, 0); }
function slotsLeft() { return BOARD - ui.s.p[ME].board.length - ui.plan.plays.filter(p => CARDS[p.card].kind === 'unit').length; }
const plannedIdx = (i) => ui.plan.plays.findIndex(p => p.hand === i);
function canAdd(id) { const c = CARDS[id]; return c.cost <= manaLeft() && (c.kind !== 'unit' || slotsLeft() > 0); }

// ------------------------------------------------------------------ rendering
function heroHTML(side) {
  const p = ui.view.p[side];
  const tgt = ui.sel && planning() && (ui.sel.kind === 'card' || (ui.sel.kind === 'unit' && side === BOT));
  const marks = ui.shown ? '' : spellMarks(side, -1);
  return `<div class="hero s${side}${tgt ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-uid="-1"><span class="hp">${p.life}</span>${marks}</div>`;
}
function spellMarks(side, uid) {
  if (!ui.plan || ui.over) return '';
  const d = ui.plan.plays.filter(p => p.tgt && p.tgt.side === side && p.tgt.uid === uid).map(p => CARDS[p.card].dmg);
  return d.length ? `<span class="mark">−${d.reduce((a, b) => a + b, 0)}</span>` : '';
}
function boardHTML(side) {
  const P = ui.view.p[side];
  let html = P.board.map(u => {
    let cls = '';
    if (planning()) {
      if (side === ME && ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === u.uid) cls += ' sel';
      else if (side === ME && !ui.sel && u.ready) cls += ' can';
      if (ui.sel && (ui.sel.kind === 'card' || (ui.sel.kind === 'unit' && side === BOT))) cls += ' tgt';
    }
    if (!u.ready) cls += ' sleep';
    if (ui.fx['u' + u.uid]) cls += ' ' + ui.fx['u' + u.uid];
    return `<div class="unit s${side}${cls}" id="u${u.uid}" data-side="${side}" data-uid="${u.uid}"><span class="stat a">${u.atk}</span><span class="stat h${u.hp < u.max ? ' hurt' : ''}">${u.hp}</span>${ui.shown ? '' : spellMarks(side, u.uid)}</div>`;
  }).join('');
  // units planned to enter: ghosts on my side while planning
  if (side === ME && ui.plan && !ui.shown && planning()) html += ui.plan.plays.filter(p => CARDS[p.card].kind === 'unit').map(p => `<div class="unit s0 planned" data-hand="${p.hand}"><span class="stat a">${CARDS[p.card].atk}</span><span class="stat h">${CARDS[p.card].hp}</span></div>`).join('');
  return html;
}
function resHTML(side) {
  const p = ui.view.p[side], left = side === ME && ui.plan && planning() ? manaLeft() : p.mana;
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < left ? ' on' : i < p.mana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${left}/${Math.min(MAX_MANA, ui.view.round)}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], can = planning();
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return (A.kind === B.kind ? 0 : A.kind === 'unit' ? -1 : 1) || A.cost - B.cost; });
  return order.map(i => {
    const id = p.hand[i], planned = can && plannedIdx(i) >= 0;
    let cls = planned ? 'planned' : can && canAdd(id) ? 'ok' : can ? 'no' : '';
    if (can && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${can && (planned || canAdd(id)) ? '' : ' disabled'}` });
  }).join('');
}
function revealHTML() {
  if (!ui.shown) return '';
  return ui.shown.plays.map(x => cardHTML(x.card, BOT, { cls: 'mini' })).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function render() {
  const s = ui.view, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side); $('board' + side).innerHTML = boardHTML(side); $('res' + side).innerHTML = resHTML(side); }
  $('reveal').innerHTML = revealHTML();
  $('hand').innerHTML = handHTML();
  $('turnbox').innerHTML = `<button id="endturn"${planning() ? '' : ' disabled'}>Go</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fx = {};
  requestAnimationFrame(drawArrows);
}
// arrows: my planned attacks while planning; both sides' attacks once revealed
function drawArrows() {
  const svg = $('arrows'), g = $('game').getBoundingClientRect();
  svg.setAttribute('width', g.width); svg.setAttribute('height', g.height);
  const lines = [];
  const at = (el) => { const r = el.getBoundingClientRect(); return [r.left - g.left + r.width / 2, r.top - g.top + r.height / 2]; };
  const add = (from, to, side) => {
    const a = $('u' + from), b = to === -1 ? $('hero' + (1 - side) + 'x') : $('u' + to);
    if (!a || !b) return;
    const [x1, y1] = at(a), [x2, y2] = at(b), dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    const ex = x2 - dx / L * 34, ey = y2 - dy / L * 34;
    lines.push(`<line x1="${x1}" y1="${y1}" x2="${ex}" y2="${ey}" class="ar s${side}" marker-end="url(#head${side})"/>`);
  };
  if (ui.plan && !ui.shown && planning()) for (const [from, to] of ui.plan.attacks) add(from, to, ME);
  if (ui.shown) { for (const a of ui.shown.mine) add(a.from, a.to, ME); for (const a of ui.shown.attacks) add(a.from, a.to, BOT); }
  svg.innerHTML = `<defs><marker id="head0" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" class="hd s0"/></marker><marker id="head1" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" class="hd s1"/></marker></defs>` + lines.join('');
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit[id], .hero').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}
function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return Promise.resolve();
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  return fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .7}px, ${dy * .7}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 480, easing: 'ease-in-out' }).finished;
}
function floatsAndDeaths(evs, before) {
  for (const e of evs) {
    if (e.t === 'hit') { const id = e.uid === -1 ? 'hero' + e.side + 'x' : 'u' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'fatigue') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
  }
}

// ------------------------------------------------------------------ a round: my plan, his plan, the resolution
async function go() {
  if (!planning()) return;
  const mine = planObj();
  if (planError(ui.s, ME, mine)) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  const s1 = act(ui.s, mine);
  await wait(60);
  const theirs = expert(s1, ui.rng);
  if (tok !== ui.token) return;
  const ev = [];
  const s2 = act(s1, theirs, ev);
  // reveal both plans
  ui.shown = { plays: theirs.plays, attacks: theirs.attacks, mine: mine.attacks };
  const ph = ev.filter(e => e.t === 'phase');
  ui.view = ph[0].snap; ui.plan = null; render();
  await wait(1500);
  if (tok !== ui.token) return;
  // spells, then units entering, then attacks; each step from the snapshot before it
  let i = ev.indexOf(ph[0]) + 1;
  for (let k = 1; k < ph.length; k++) {
    const j = ev.indexOf(ph[k]), evs = ev.slice(i, j); i = j + 1;
    if (ph[k].name === 'attacks') {
      const L = evs.find(e => e.t === 'attacks');
      if (L) { await Promise.all(L.list.map(a => lunge($('u' + a.from), a.to === -1 ? $('hero' + (1 - a.side) + 'x') : $('u' + a.to)))); }
      if (tok !== ui.token) return; // a new game started meanwhile
      ui.shown = null;
    }
    const before = snapshot();
    for (const e of evs) { if (e.t === 'summon') ui.fx['u' + e.uid] = 'new'; if (e.t === 'hit' && e.uid !== -1 && e.hp > 0) ui.fx['u' + e.uid] = 'shake'; if (e.t === 'hit' && e.uid === -1) ui.fx['hero' + e.side] = 'shake'; }
    for (const e of evs) {
      if (e.t === 'spell') ui.hist.push({ side: e.side, kind: 'spell', chip: CARDS[e.card].dmg, out: e.tgt.uid === -1 ? '−' + CARDS[e.card].dmg + ' life' : '', cls: 'face' });
      if (e.t === 'summon') ui.hist.push({ side: e.side, kind: 'unit', chip: CARDS[e.card].atk + '/' + CARDS[e.card].hp });
    }
    const L = evs.find(e => e.t === 'attacks');
    if (L) for (const side of [0, 1]) { const mine2 = L.list.filter(a => a.side === side); if (mine2.length) ui.hist.push({ side, kind: 'attack', chip: mine2.length, out: '−' + mine2.filter(a => a.to === -1).reduce((x, a) => x + a.atk, 0) + ' life', cls: 'face' }); }
    ui.view = ph[k].snap; render();
    floatsAndDeaths(evs, before);
    if (evs.some(e => e.t === 'hit' || e.t === 'summon' || e.t === 'die')) await wait(750);
    if (tok !== ui.token) return;
  }
  ui.shown = null;
  // the next round starts (draws, fatigue)
  const before = snapshot();
  ui.s = s2; ui.view = s2; ui.plan = newPlan(); render();
  floatsAndDeaths(ev.slice(i), before);
  if (s2.winner !== null) return finish();
  banner('Round ' + s2.round);
  await wait(500);
  if (tok !== ui.token) return;
  ui.busy = false; render();
}

function finish() {
  if (ui.over) return;
  ui.over = true; ui.busy = false;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
  render();
}
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null; ui.plan = newPlan(); ui.shown = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner('Round 1');
  await wait(700);
  if (tok !== ui.token) return;
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if (e.target.closest('#rulesbtn')) { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (!planning()) return;
  const tgt = e.target.closest('.unit[data-uid], .hero');
  if (tgt) {
    const side = +tgt.dataset.side, uid = +tgt.dataset.uid;
    if (ui.sel && ui.sel.kind === 'card' && tgt.classList.contains('tgt')) {
      ui.plan.plays.push({ card: ui.sel.id, hand: ui.sel.hand, tgt: { side, uid } }); ui.sel = null; render(); return;
    }
    if (ui.sel && ui.sel.kind === 'unit' && side === BOT && tgt.classList.contains('tgt')) { ui.plan.attacks.set(ui.sel.uid, uid); ui.sel = null; render(); return; }
    if (side === ME && uid !== -1) {
      if (ui.sel && ui.sel.kind === 'unit' && ui.sel.uid === uid) { ui.plan.attacks.delete(uid); ui.sel = null; }
      else ui.sel = { kind: 'unit', uid };
      render(); return;
    }
  }
  const pl = e.target.closest('.unit.planned');
  if (pl) { const k = plannedIdx(+pl.dataset.hand); if (k >= 0) ui.plan.plays.splice(k, 1); render(); return; }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.s.p[ME].hand[i], k = plannedIdx(i);
    if (k >= 0) { ui.plan.plays.splice(k, 1); ui.sel = null; render(); return; }
    if (CARDS[id].kind === 'unit') { if (canAdd(id)) ui.plan.plays.push({ card: id, hand: i }); ui.sel = null; render(); return; }
    ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return;
  }
  if (b && !b.disabled && b.id === 'endturn') return go();
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
window.addEventListener('resize', () => requestAnimationFrame(drawArrows));
window.__game = { get s() { return ui.s; }, get busy() { return ui.busy; }, get over() { return ui.over; }, get plan() { return ui.plan; } };
startMatch();
