// Wave defense as a game screen. The player's moves go through legalActions/act; each round's threat
// phase plays back in steps from the engine's snapshots. The Expert plays the same seeded game in
// the background, one decision per idle moment, and the two results are compared at the end.

import { CARDS, THREATS, LANES, ROWS, WALL, newMatch, act, legalActions, lanesOf, rank } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const TALLY_KEY = 'night-41-wave-tally';
const expert = expertBot({ budget: 600 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, fresh: 0, fx: {}, exp: null, token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const TEXT = { Guard: 'Defender', Shooter: 'Defender, Shoot 1', Heavy: 'Defender', Cannon: 'Defender, Shoot 3', Twin: 'Defender, Shoot 2', Hit3: '3 damage to a threat', Hit6: '6 damage to a threat',
  Bomb: '2 damage to each threat in a lane', Freeze: 'A lane does not advance next round', Repair: 'Wall +4', Rebuild: 'Wall +8', Draw2: 'Draw 2 cards' };
const BIG = { Hit3: '3', Hit6: '6', Bomb: '2', Freeze: '❄', Repair: '+4', Rebuild: '+8', Draw2: '+2' };
function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id], def = c.kind === 'Defender';
  const art = def ? `<span class="stat a">${c.atk}</span>${c.shoot ? `<span class="stat s">${c.shoot}</span>` : ''}<span class="stat h">${c.hp}</span>` : `<span class="big">${BIG[id]}</span>`;
  return `<button class="card ${def ? 'Defender' : 'spell'} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div><div class="tx">${TEXT[id]}</div></button>`;
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view.phase === 'play' && !ui.view.result;
const legal = () => myTurn() ? legalActions(ui.view) : [];
function targetsNow() {
  const out = { lanes: new Set(), threats: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legal()) if (a.t === 'play' && a.card === ui.sel.id) { if (a.uid) out.threats.add(a.uid); else if (a.lane !== undefined) out.lanes.add(a.lane); }
  return out;
}

// ------------------------------------------------------------------ rendering
function threatHTML(t, T) {
  const cls = (THREATS[t.id].swift ? ' swift' : '') + (T.threats.has(t.uid) ? ' tgt' : '') + (ui.fx['t' + t.uid] ? ' ' + ui.fx['t' + t.uid] : '');
  return `<div class="threat${cls}" id="t${t.uid}" data-uid="${t.uid}" data-lane="${t.lane}">${t.id}<span class="stat a">${t.atk}</span><span class="stat h${t.hp < t.max ? ' hurt' : ''}">${t.hp}</span></div>`;
}
function fieldHTML(T) {
  const s = ui.view;
  let html = '';
  for (let l = 0; l < LANES; l++) {
    let cells = '';
    for (let r = ROWS; r >= 1; r--) cells += `<div class="cell"><span class="rn">${r}</span>${s.lanes[l].filter(t => t.row === r).map(t => threatHTML({ ...t, lane: l }, T)).join('')}</div>`;
    const d = s.slots[l];
    const dh = d ? `<div class="def${ui.fx['d' + d.uid] ? ' ' + ui.fx['d' + d.uid] : ''}" id="d${d.uid}">${CARDS[d.id].name}<span class="stat a">${d.atk}</span>${d.shoot ? `<span class="stat s">${d.shoot}</span>` : ''}<span class="stat h${d.hp < d.max ? ' hurt' : ''}">${d.hp}</span></div>` : '';
    cells += `<div class="cell slot">${dh}</div>`;
    const frozen = s.frozen[l] || s.freezeNext[l];
    html += `<div class="lane${T.lanes.has(l) ? ' tgt' : ''}${frozen ? ' frozen' : ''}" id="lane${l}" data-lane="${l}">${cells}</div>`;
  }
  return html;
}
function handHTML() {
  const s = ui.view, L = legal();
  const order = s.hand.map((_, i) => i).sort((a, b) => CARDS[s.hand[a]].cost - CARDS[s.hand[b]].cost || s.hand[a].localeCompare(s.hand[b]));
  return order.map(i => {
    const id = s.hand[i], ok = L.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= s.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('status').innerHTML = `<span class="round">Round ${s.round}</span><span class="tdeck"><span class="pile">${s.threatDeck.length}</span></span>`;
  $('field').innerHTML = fieldHTML(T);
  $('wall').innerHTML = `<div class="fill" style="width:${Math.max(0, s.wall) / WALL * 100}%"></div><div class="n">${Math.max(0, s.wall)}</div>`;
  $('wall').className = ui.fx.wall || '';
  $('hand').innerHTML = handHTML();
  let gems = ''; for (let i = 0; i < (s.flatMana || 8); i++) gems += `<i class="gemc${i < s.mana ? ' on' : ''}"></i>`;
  const canAct = myTurn() && legal().some(a => a.t === 'play');
  $('side').innerHTML = `<div class="mana"><span class="manatxt">${s.mana}</span>${gems}</div><div class="piles"><span class="pile mine">${s.deck.length}</span><span class="pile disc">${s.discard.length}</span></div>
    <button id="endturn" class="${myTurn() && !canAct ? 'done' : ''}"${myTurn() ? '' : ' disabled'}>End turn</button>`;
  const rw = s.phase === 'reward' && !ui.busy && !ui.over;
  $('reward').innerHTML = rw ? `<div class="opts">${s.offer.map((id, i) => cardHTML(id, { attrs: `data-reward="${i}"` })).join('')}</div><button class="none" data-reward="-1">None</button>` : '';
  $('reward').classList.toggle('show', rw);
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.threat, .def, #wall').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}
function shot(from, to) {
  const d = document.createElement('div'); d.className = 'shot'; $('game').appendChild(d);
  d.animate([{ left: from.x + 'px', top: from.y + 'px' }, { left: to.x + 'px', top: to.y + 'px' }], { duration: 260, easing: 'ease-in' }).finished.then(() => d.remove());
}
// threats that moved slide from where they were (FLIP)
function slide(before) {
  document.querySelectorAll('.threat').forEach(el => {
    const b = before[el.id]; if (!b) return;
    const r = el.getBoundingClientRect(), dx = b.rect.left - r.left, dy = b.rect.top - r.top;
    if (Math.abs(dx) + Math.abs(dy) > 2) el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: 'translate(0,0)' }], { duration: 380, easing: 'ease-out' });
  });
}

// ------------------------------------------------------------------ playback
// The events between two snapshots are shown on the table of the second.
async function show(seg, next) {
  const qtok = ui.token;
  const before = snapshot();
  for (const e of seg) {
    if (e.t === 'spawn') ui.fx['t' + e.uid] = 'new';
    if (e.t === 'place') ui.fx['d' + e.uid] = 'new';
    if (e.t === 'hit') ui.fx['t' + e.uid] = 'shake';
    if (e.t === 'dhit') ui.fx['d' + e.uid] = 'shake';
    if (e.t === 'wall') ui.fx.wall = 'shake';
    if (e.t === 'draw') ui.fresh++;
  }
  for (const e of seg) if (e.t === 'shoot') { const a = before['d' + e.duid], b = before['t' + e.uid]; if (a && b) shot(a.c, b.c); }
  if (seg.some(e => e.t === 'shoot')) await wait(260);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  ui.view = next; render(); slide(before);
  for (const e of seg) {
    if (e.t === 'hit') { const p = before['t' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'dhit') { const p = before['d' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'wall') { const p = before.wall; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'heal') { const p = before.wall; if (p) floatAt(p.c, '+' + e.n, 'heal'); }
    if (e.t === 'die' || e.t === 'fall') { const p = before[(e.t === 'die' ? 't' : 'd') + e.uid]; if (p) ghost(p); }
  }
}
async function apply(a, tok) {
  const ev = [], next = act(ui.s, a, ev);
  ui.s = next;
  let seg = [];
  for (const e of ev) {
    if (e.t === 'snap') {
      if (tok !== ui.token) return;
      await show(seg, e.s); seg = [];
      if (e.step === 'spawn') banner('Round ' + e.s.round);
      await wait(e.step === 'shoot' ? 450 : 650);
    } else seg.push(e);
  }
  if (tok !== ui.token) return;
  await show(seg, next);
  if (next.result) finish();
  render();
}

// the Expert's own run of the same game, a decision at a time while the page is idle
function expStep(tok) {
  if (tok !== ui.token || !ui.exp || ui.exp.s.result) return;
  if (!ui.busy || ui.over) { ui.exp.s = act(ui.exp.s, expert(ui.exp.s, ui.exp.rng)); if (ui.exp.s.result && ui.over) showOver(); }
  setTimeout(() => expStep(tok), ui.over ? 0 : 40);
}
function finish() { if (ui.over) return; ui.over = true; showOver(); }
function showOver() {
  const me = ui.s, ex = ui.exp.s, w = me.result === 'win';
  const line = (s) => s.result === 'win' ? `<span>${s.wall}</span>Wall` : `<span>${s.round}</span>rounds`;
  let vs = `<div class="${''}" id="youbox">You${line(me)}</div><div id="expbox">Expert${ex.result ? line(ex) : '<span>…</span>'}</div>`;
  if (ex.result && !ui.scored) {
    ui.scored = true;
    const d = Math.sign(rank(me) - rank(ex)), t = loadTally();
    if (d > 0) t[0]++; else if (d < 0) t[1]++;
    saveTally(t);
    vs = `<div class="${d > 0 ? 'best' : ''}">You${line(me)}</div><div class="${d < 0 ? 'best' : ''}">Expert${line(ex)}</div>`;
  }
  $('over').innerHTML = `<h2 class="${w ? 'win' : 'lose'}">${w ? 'Victory' : 'Defeat'}</h2><div class="vs">${vs}</div><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
  render();
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, seed = (Math.random() * 4294967296) >>> 0;
  ui.s = newMatch({ seed }); ui.view = ui.s; ui.over = false; ui.sel = null; ui.scored = false;
  ui.exp = { s: newMatch({ seed }), rng: makeRng(seed ^ 0x5bd1e995) };
  $('over').classList.remove('show');
  ui.busy = false; render(); banner('Round 1');
  setTimeout(() => expStep(tok), 1200);
}
async function doAct(a) {
  if (ui.busy || ui.over) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply(a, tok);
  if (tok !== ui.token) return;
  ui.busy = false; render();
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if (b && b.id === 'rulesclose') { $('rules').classList.remove('show'); return; }
  if (e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  const rw = e.target.closest('[data-reward]');
  if (rw && ui.view.phase === 'reward' && !ui.busy) { const i = +rw.dataset.reward; return doAct({ t: 'reward', card: i < 0 ? null : ui.view.offer[i] }); }
  if (!myTurn()) return;
  const th = e.target.closest('.threat.tgt');
  if (th && ui.sel) return doAct({ t: 'play', card: ui.sel.id, lane: +th.dataset.lane, uid: +th.dataset.uid });
  const ln = e.target.closest('.lane.tgt');
  if (ln && ui.sel) return doAct({ t: 'play', card: ui.sel.id, lane: +ln.dataset.lane });
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.hand[i], c = CARDS[id];
    if (c.kind === 'Hit' || lanesOf(id)) { ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b && b.id === 'endturn' && !b.disabled) return doAct({ t: 'end' });
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
startMatch();
