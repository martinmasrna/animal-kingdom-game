// Siege clock as a game screen against Expert. You take the Attacker and the Defender in turn,
// game by game. The bot plays one action at a time so every step can be seen: its sends rise
// out of the Field, its blocks and shots are drawn as lunges.

import { CARDS, GATE, ROUNDS, MAX_MANA, newMatch, act, isLegal, canBlock, aimable } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-30-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, sel: null, sending: new Set(), hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const F = () => ui.s.p[ui.s.att].units, Wl = () => ui.s.p[ui.s.def].units;
const iAttack = () => ui.s.att === ME;
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'Unit' ? `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>` : '';
  const tx = c.text ? `<div class="tx">${c.text}</div>` : '';
  return `<button class="card ${c.kind === 'Unit' ? 'Minion' : 'Spell'} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div>${tx}</button>`;
}

// ------------------------------------------------------------------ what can be done now
const myMove = () => !ui.busy && !ui.over && ui.s.toMove === ME;
function targetsNow() {
  const out = new Set(), s = ui.s;
  if (!myMove()) return out;
  if (s.phase === 'block') { F().forEach((_, i) => { if (isLegal(s, { t: 'block', a: i })) out.add(s.att + ':' + i); }); return out; }
  if (s.phase === 'shoot') { F().forEach((_, i) => { if (isLegal(s, { t: 'shoot', i })) out.add(s.att + ':' + i); }); return out; }
  if (ui.sel) {
    const side = ui.sel.id === 'VO' ? s.def : s.att;
    s.p[side].units.forEach((_, i) => { if (isLegal(s, { t: 'play', card: ui.sel.id, i })) out.add(side + ':' + i); });
  }
  return out;
}
const canSend = (i) => myMove() && ui.s.phase === 'att' && isLegal(ui.s, { t: 'send', i });
function canPlay(id) {
  if (!myMove() || (ui.s.phase !== 'att' && ui.s.phase !== 'def')) return false;
  const s = ui.s, P = s.p[ME];
  if (id === 'VO') return Wl().some((_, i) => isLegal(s, { t: 'play', card: id, i }));
  if (id === 'RU') return P.units.some((_, i) => isLegal(s, { t: 'play', card: id, i }));
  if (id === 'SN') return F().some((_, i) => isLegal(s, { t: 'play', card: id, i }));
  return isLegal(s, { t: 'play', card: id });
}

// ------------------------------------------------------------------ rendering
function gateHTML() { return `<div class="gate${ui.s.gate <= 6 ? ' low' : ''} ${ui.fx.gate || ''}" id="gatex"><span class="n">${ui.s.gate}</span></div>`; }
function unitsHTML(side, T) {
  const s = ui.s, isWall = side === s.def;
  const curShooter = s.phase === 'shoot' ? Wl().filter(m => m.card === 'SO')[s.si] : null;
  return s.p[side].units.map((m, i) => {
    let cls = '';
    if (side === ME && !isWall && ui.sending.has(m.uid)) cls += ' pick';
    else if (side === ME && canSend(i)) cls += ' can';
    if (m.sent) cls += ' sent';
    if (T.has(side + ':' + i)) cls += ' tgt';
    if (!isWall && side === s.att && s.phase === 'att' && !m.ready && !m.sent) cls += ' sleep';
    if (isWall && !canBlock(s, m)) cls += ' tired';
    if (isWall && ((s.phase === 'block' && i === s.bi) || m === curShooter)) cls += ' cur';
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="minion s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}"><span class="uname">${CARDS[m.card].name}</span><span class="stat a">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : ''}">${m.hp}</span></div>`;
  }).join('');
}
function resHTML(side) {
  const p = ui.s.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < Math.min(MAX_MANA, ui.s.round) ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
function handHTML() {
  const p = ui.s.p[ME];
  const order = p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return (A.kind === 'Unit' ? 0 : 1) - (B.kind === 'Unit' ? 0 : 1) || A.cost - B.cost || (A.id < B.id ? -1 : 1); });
  return order.map(i => {
    const id = p.hand[i], ok = canPlay(id);
    let cls = ok ? 'ok' : (myMove() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
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
  for (const side of [0, 1]) {
    $('hero' + side).innerHTML = side === s.def ? gateHTML() : '';
    $('board' + side).innerHTML = unitsHTML(side, T);
    $('res' + side).innerHTML = resHTML(side);
  }
  $('hand').innerHTML = handHTML();
  let pips = '';
  for (let r = 1; r <= ROUNDS; r++) pips += `<i class="pip${r < s.round ? ' done' : r === s.round ? ' now' : ''}"></i>`;
  const mine = myMove();
  let btns = '';
  if (s.phase === 'block' && mine) btns = `<button id="pass">No block</button>`;
  else if (s.phase === 'shoot') btns = '';
  else {
    const label = s.phase === 'att' && s.toMove === ME && ui.sending.size ? 'Attack' : 'End turn';
    const idle = mine && !s.p[ME].hand.some(canPlay) && !s.p[ME].units.some((m, i) => canSend(i) && !ui.sending.has(m.uid));
    btns = `<button id="endturn" class="${idle ? 'done' : ''}"${mine ? '' : ' disabled'}>${label}</button>`;
  }
  $('turnbox').innerHTML = `<div class="rounds">${pips}</div>${btns}`;
  $('history').innerHTML = ui.hist.slice(-14).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.minion, .gate').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(700);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl, k = .8) {
  if (!fromEl || !toEl || FAST) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * k}px, ${dy * k}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 380, easing: 'ease-in-out' }).finished;
}
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}

// ------------------------------------------------------------------ playback
async function apply(a) {
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  const playE = ev.find(e => e.t === 'play');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind !== 'Unit')) await spotlight(playE.card, playE.side);
  // blocks are shown as they are chosen; the fight, strike by strike, before the board moves on
  for (const e of ev) {
    if (e.t === 'block') await lunge($('m' + e.uid), $('m' + e.tuid), .35);
    if (e.t === 'clash') await lunge($('m' + e.uid), $('m' + e.tuid));
    if (e.t === 'strike') await lunge($('m' + e.uid), $('gatex'));
    if (e.t === 'shot') await lunge($('m' + e.uid), $('m' + e.tuid), .5);
  }
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner(e.side === next.att ? 'Attack' : 'Hold'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'hit' && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'gate') ui.fx.gate = 'shake';
    if (e.t === 'draw' && e.side === ME) ui.fresh++;
  }
  ui.s = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['m' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'gate') { const p = before.gatex; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'repair' && e.n) { const p = before.gatex; if (p) floatAt(p.c, '+' + e.n, 'heal'); }
  }
  if (playE) {
    const c = CARDS[playE.card];
    ui.hist.push({ side: playE.side, kind: c.kind === 'Unit' ? 'Minion' : 'Spell', chip: c.kind === 'Unit' ? `${c.atk}/${c.hp}` : c.name, out: '' });
  }
  const g = ev.filter(e => e.t === 'gate').reduce((t, e) => t + e.n, 0);
  if (ev.some(e => e.t === 'combat')) ui.hist.push({ side: prev.att, kind: 'Attack', chip: ev.filter(e => e.t === 'clash' || e.t === 'strike').length, out: g ? '−' + g + ' gate' : '0', cls: g ? 'face' : 'dmg' });
  if (ev.some(e => e.t === 'turn')) await wait(next.toMove === ME ? 600 : 250);
  if (next.winner !== null) finish();
  render();
}

function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  const t = loadTally(); t[w === ME ? 0 : 1]++; saveTally(t);
  const txt = w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${txt[1]}">${txt[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, attacker: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null; ui.sending = new Set();
  $('over').classList.remove('show');
  ui.busy = true; render();
  banner(ui.s.att === ME ? 'Attack' : 'Hold');
  await wait(900);
  if (tok !== ui.token) return;
  await settle(tok);
}
// hand control to whoever moves now
async function settle(tok) {
  while (!ui.over && ui.s.toMove === BOT) {
    ui.busy = true; render();
    await wait(380);
    if (tok !== ui.token || ui.over) return;
    const t0 = performance.now(), a = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(a);
    if (tok !== ui.token) return;
  }
  ui.busy = false; render();
}
async function doActs(acts) {
  const tok = ui.token;
  ui.busy = true; ui.sel = null;
  for (const a of acts) { if (tok !== ui.token || ui.over || !isLegal(ui.s, a)) break; await apply(a); }
  if (tok !== ui.token) return;
  await settle(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b0 = e.target.closest('button');
  if (b0 && (b0.id === 'rematch' || b0.id === 'newmatch')) return startMatch();
  if (b0 && b0.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  if (!myMove()) return;
  const s = ui.s;
  const u = e.target.closest('.minion');
  if (u) {
    const side = +u.dataset.side, i = +u.dataset.i;
    if (u.classList.contains('tgt')) {
      if (s.phase === 'block') return doActs([{ t: 'block', a: i }]);
      if (s.phase === 'shoot') return doActs([{ t: 'shoot', i }]);
      if (ui.sel) return doActs([{ t: 'play', card: ui.sel.id, i }]);
    }
    if (side === ME && s.phase === 'att' && !ui.sel && canSend(i)) { const id = s.p[ME].units[i].uid; if (ui.sending.has(id)) ui.sending.delete(id); else ui.sending.add(id); render(); return; }
  }
  if (b0 && !b0.disabled && b0.dataset.hand !== undefined) {
    const i = +b0.dataset.hand, id = s.p[ME].hand[i];
    if (id === 'VO' || id === 'RU' || id === 'SN') { ui.sel = ui.sel && ui.sel.hand === i ? null : { id, hand: i }; render(); return; }
    return doActs([{ t: 'play', card: id }]);
  }
  if (b0 && b0.id === 'pass') return doActs([{ t: 'block', a: -1 }]);
  if (b0 && !b0.disabled && b0.id === 'endturn') {
    const sends = s.phase === 'att' ? s.p[ME].units.map((m, i) => ui.sending.has(m.uid) && canSend(i) ? { t: 'send', i } : null).filter(Boolean) : [];
    ui.sending = new Set();
    return doActs([...sends, { t: 'end' }]);
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } });
startMatch();
