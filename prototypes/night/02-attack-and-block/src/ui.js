// 02 Attack and block as a page: you against Expert. Every change goes through the engine's
// act() with the same actions the bots use; the bot's turn is played one action at a time.

import { CARDS, newMatch, act, legalActions, canAttackWith, canBlockWith, unitAt } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-02-tally';
const expert = expertBot({ playouts: 3000, timeMs: 1500 });
const MARKS = ['#f2b632', '#5fdc6f', '#ff6a4d', '#5ad1f0', '#ff7ad9', '#ffffff'];
const ui = { s: null, busy: false, over: false, sel: null, chosen: new Set(), pairs: [], pick: null, show: null, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  let body = '';
  if (c.kind === 'unit') body = `<div class="stats"><span class="a">${c.atk}</span><span class="h">${c.hp}</span></div>`;
  else if (c.kind === 'hit') body = `<div class="tx">${c.dmg} damage to an enemy unit</div>`;
  else if (c.kind === 'draw') body = `<div class="tx">Draw ${c.n}</div>`;
  else body = `<div class="tx">+1 mana this turn</div>`;
  return `<button class="card ${cls}" ${attrs}><span class="cost">${c.cost}</span><div class="nm">${c.name}</div>${body}</button>`;
}

const myMove = () => !ui.busy && !ui.over && ui.s.toAct === ME;
const legal = () => (myMove() && ui.s.phase === 'main') ? legalActions(ui.s) : [];

function unitHTML(side, u) {
  const s = ui.s; let cls = '', mark = '';
  if (u.fresh && side === s.turn) cls += ' fresh';
  if (u.ex) cls += ' ex';
  const phase = s.phase;
  if (phase === 'block' && side === s.turn && s.attackers.includes(u.uid)) {
    cls = cls.replace(' ex', '') + ' attacking';
    mark = `<i class="mark" style="background:${MARKS[s.attackers.indexOf(u.uid) % MARKS.length]}"></i>`;
    if (myMove() && ui.pick !== null) cls += ' tgt';
  }
  const pairs = ui.show || ui.pairs;
  if (phase === 'block' && side !== s.turn) {
    const pr = pairs.find(p => p[0] === u.uid);
    if (pr) mark = `<i class="mark" style="background:${MARKS[s.attackers.indexOf(pr[1]) % MARKS.length]}"></i>`;
    if (myMove() && canBlockWith(u)) cls += ui.pick === u.uid ? ' picked' : ' can';
  }
  if (phase === 'main' && myMove() && side === ME) {
    if (ui.chosen.has(u.uid)) cls += ' chosen';
    else if (!s.attacked && canAttackWith(u) && u.atk > 0 && !ui.sel) cls += ' can';
  }
  if (phase === 'main' && side === BOT && ui.sel && legal().some(a => a.card === ui.sel && a.tgt === u.uid)) cls += ' tgt';
  if (ui.fx && ui.fx[u.uid]) cls += ' ' + ui.fx[u.uid];
  return `<div class="unit s${side}${cls}" id="u${u.uid}" data-side="${side}" data-uid="${u.uid}"><span class="nm">${CARDS[u.card].name}</span>${mark}<span class="st a">${u.atk}</span><span class="st h${u.dmg ? ' hurt' : ''}">${u.hp - u.dmg}</span></div>`;
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  for (const side of [0, 1]) {
    const P = s.p[side];
    $('life' + side).textContent = P.life;
    $('board' + side).innerHTML = P.board.map(u => unitHTML(side, u)).join('');
    $('res' + side).innerHTML = `<span class="manaval">${P.mana}/${P.maxMana}</span><span class="pile s${side}">${P.deck.length}</span>`;
  }
  const L = legal();
  const P = s.p[ME];
  $('hand').innerHTML = P.hand.map((id, i) => ({ id, i })).sort((a, b) => CARDS[a.id].cost - CARDS[b.id].cost).map(({ id, i }) => {
    const ok = L.some(a => a.t === 'play' && a.card === id);
    return cardHTML(id, { cls: (ok ? 'ok' : (myMove() ? 'no' : '')) + (ui.sel === id ? ' sel' : ''), attrs: `data-card="${id}"${ok ? '' : ' disabled'}` });
  }).join('');
  let ctl = '';
  if (myMove() && s.phase === 'main') {
    if (ui.chosen.size) ctl += `<button id="attack" class="go">Attack</button>`;
    ctl += `<button id="end">End turn</button>`;
  } else if (myMove() && s.phase === 'block') {
    ctl += `<button id="block" class="go">${ui.pairs.length ? 'Block' : 'No block'}</button>`;
  } else ctl += `<button disabled>End turn</button>`;
  $('controls').innerHTML = ctl;
  $('history').innerHTML = ui.hist.slice(-16).map(h => `<div class="hist s${h.side}"><span>${h.txt}</span><span class="o">${h.out || ''}</span></div>`).join('');
  ui.fx = null;
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text) { const f = document.createElement('div'); f.className = 'float'; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.unit, .lifebox').forEach(el => { const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); out[el.id] = { c: centerOf(el), html: el.outerHTML, x: r.left - g.left, y: r.top - g.top }; }); return out; }
function ghost(sn) { const d = document.createElement('div'); d.className = 'ghost'; d.innerHTML = sn.html; d.style.left = sn.x + 'px'; d.style.top = sn.y + 'px'; $('game').appendChild(d); setTimeout(() => d.remove(), 550); }
async function spotlight(id) { $('spot').innerHTML = cardHTML(id); await wait(800); $('spot').innerHTML = ''; }

async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [], side = prev.toAct;
  if (a.t === 'play' && side === BOT) await spotlight(a.card);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (a.t === 'block') { ui.show = a.pairs; render(); await wait(side === BOT ? 900 : 300); }
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const before = snapshot();
  const next = act(prev, a, ev);
  ui.s = next; ui.show = null; ui.fx = {};
  for (const e of ev) {
    if (e.t === 'summon') ui.fx[e.uid] = 'new';
    if (e.t === 'hit') ui.fx[e.uid] = 'shake';
  }
  render();
  for (const e of ev) {
    if (e.t === 'hit') { const p = before['u' + e.uid]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['u' + e.uid]; if (p) ghost(p); }
    if (e.t === 'life' || e.t === 'fatigue') { const p = before['life' + e.side]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'turn' && e.side === ME) banner('Your turn');
  }
  // history
  if (a.t === 'play') {
    const c = CARDS[a.card], died = ev.some(e => e.t === 'die');
    ui.hist.push({ side, txt: c.name, out: c.kind === 'hit' ? (died ? '✕' : '−' + c.dmg) : '' });
  } else if (a.t === 'attack') ui.hist.push({ side, txt: `Attack ×${a.units.length}` });
  else if (a.t === 'block') {
    const face = ev.filter(e => e.t === 'life').reduce((x, e) => x + e.n, 0), dead = ev.filter(e => e.t === 'die');
    ui.hist.push({ side, txt: a.pairs.length ? `Block ×${a.pairs.length}` : 'No block', out: [face ? '−' + face : '', dead.length ? '✕' + dead.length : ''].filter(Boolean).join(' ') });
  }
  if (next.winner !== null) finish();
  await wait(ev.some(e => e.t === 'hit' || e.t === 'life') ? 700 : 250);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
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
async function advance(tok) {
  while (!ui.over && ui.s.toAct === BOT) {
    ui.busy = true; render();
    await wait(450);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token) return;
    await apply(a);
    if (tok !== ui.token) return;
  }
  ui.busy = false; ui.sel = null; ui.chosen.clear(); ui.pairs = []; ui.pick = null; render();
}
async function mine(a) {
  if (!myMove()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; ui.chosen.clear(); ui.pairs = []; ui.pick = null;
  await apply(a);
  if (tok !== ui.token) return;
  await advance(tok);
}
async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.hist = []; ui.sel = null; ui.chosen.clear(); ui.pairs = []; ui.pick = null; ui.show = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(700);
  if (tok !== ui.token) return;
  await advance(tok);
}

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if (b && b.id === 'rulesclose') { $('rules').classList.remove('show'); return; }
  if (e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'newgame' || b.id === 'rematch')) return startMatch();
  if (!myMove()) return;
  const s = ui.s;
  const uel = e.target.closest('.unit');
  if (s.phase === 'block') {
    if (b && b.id === 'block') return mine({ t: 'block', pairs: ui.pairs.map(p => p.slice()) });
    if (uel) {
      const side = +uel.dataset.side, uid = +uel.dataset.uid;
      if (side === ME && canBlockWith(unitAt(s.p[ME], uid))) {
        const had = ui.pairs.findIndex(p => p[0] === uid);
        if (had >= 0) { ui.pairs.splice(had, 1); ui.pick = null; } else ui.pick = ui.pick === uid ? null : uid;
        render(); return;
      }
      if (side === BOT && ui.pick !== null && s.attackers.includes(uid)) {
        ui.pairs = ui.pairs.filter(p => p[1] !== uid); ui.pairs.push([ui.pick, uid]); ui.pick = null; render(); return;
      }
    }
    if (ui.pick !== null) { ui.pick = null; render(); }
    return;
  }
  if (b && b.id === 'end') return mine({ t: 'end' });
  if (b && b.id === 'attack') return mine({ t: 'attack', units: [...ui.chosen] });
  if (b && b.dataset.card) {
    const id = b.dataset.card, c = CARDS[id];
    if (c.kind === 'hit') { ui.sel = ui.sel === id ? null : id; ui.chosen.clear(); render(); return; }
    return mine({ t: 'play', card: id });
  }
  if (uel) {
    const side = +uel.dataset.side, uid = +uel.dataset.uid;
    if (ui.sel && side === BOT) { const a = legal().find(x => x.card === ui.sel && x.tgt === uid); if (a) return mine(a); }
    if (side === ME && !ui.sel) { const u = unitAt(s.p[ME], uid); if (!s.attacked && canAttackWith(u) && u.atk > 0) { if (ui.chosen.has(uid)) ui.chosen.delete(uid); else ui.chosen.add(uid); render(); return; } }
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; ui.pick = null; $('rules').classList.remove('show'); render(); } });
startMatch();
