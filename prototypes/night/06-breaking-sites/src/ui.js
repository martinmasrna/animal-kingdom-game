// Breaking sites as a game screen against the Expert. Three sites in a row: his units above each,
// yours below. The bot's turn plays out one card at a time; the win tally is kept in this browser
// and decides who goes first (alternating).

import { CARDS, MAX_MANA, TARGET, PER_SITE, newMatch, act, legalActions, power, total } from './engine.js';
import { makeRng, mcExpert, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-06-breaking-sites-tally';
const expert = mcExpert({ ...EXPERT, timeMs: 900, minPlayouts: 300 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, fresh: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const ART = { Move: '⇆', Strike: '≤3 ✕', Boost: '+3', Draw: '+2 ▭', Coin: '+1' };
function cardHTML(id, side, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id];
  const art = c.kind === 'Unit' ? `<span class="big">${c.power}</span>` : `<span class="big sm">${ART[c.kind]}</span>`;
  return `<button class="card ${c.kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div><div class="nm">${c.name}</div></button>`;
}

const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;
// what the current selection can be aimed at: sites (slot numbers) and units ('side:slot:i')
function targetsNow() {
  const out = { sites: new Set(), units: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    const sel = ui.sel;
    if (sel.card && CARDS[sel.card].kind === 'Unit' && a.t === 'unit' && a.card === sel.card) out.sites.add(a.slot);
    if (sel.card === 'STRIKE' && a.t === 'strike') out.units.add(`${BOT}:${a.slot}:${a.i}`);
    if (sel.card === 'BOOST' && a.t === 'boost') out.units.add(`${ME}:${a.slot}:${a.i}`);
    if (sel.card === 'MOVE' && !sel.from && a.t === 'move') out.units.add(`${ME}:${a.from[0]}:${a.from[1]}`);
    if (sel.card === 'MOVE' && sel.from && a.t === 'move' && a.from[0] === sel.from[0] && a.from[1] === sel.from[1]) out.sites.add(a.slot);
  }
  return out;
}

function unitsHTML(x, k, side, T) {
  let h = '';
  for (let i = 0; i < PER_SITE; i++) {
    const m = x.u[side][i];
    if (!m) { h += '<div class="slot"></div>'; continue; }
    let cls = `unit s${side}`;
    if (T.units.has(`${side}:${k}:${i}`)) cls += ' tgt';
    if (ui.sel && ui.sel.from && ui.sel.from[0] === k && ui.sel.from[1] === i && side === ME) cls += ' sel';
    if (m.power > CARDS[m.card].power) cls += ' boosted';
    if (ui.fx['u' + m.uid]) cls += ' ' + ui.fx['u' + m.uid];
    h += `<div class="${cls}" id="u${m.uid}" data-side="${side}" data-slot="${k}" data-i="${i}">${m.power}</div>`;
  }
  return h;
}
function sitesHTML(T) {
  return ui.view.sites.map((x, k) => {
    if (!x) return `<div class="site gone"></div>`;
    const a = power(x, ME), b = power(x, BOT), fa = Math.min(1, a / x.thr), fb = Math.min(1 - fa, b / x.thr);
    return `<div class="site${T.sites.has(k) ? ' tgt' : ''}${ui.fx['s' + x.uid] ? ' ' + ui.fx['s' + x.uid] : ''}" data-slot="${k}" id="s${x.uid}">
      <div class="units top">${unitsHTML(x, k, BOT, T)}</div>
      <div class="scard"><div class="thr"><span class="pw">${total(x)}</span><span class="of">${x.thr}</span></div>
        <div class="bar"><i class="b1" style="width:${fb * 100}%"></i><i class="b0" style="width:${fa * 100}%"></i></div>
        <div class="prize"><span class="w">${x.win}</span><span class="r">${x.run}</span></div></div>
      <div class="units bottom">${unitsHTML(x, k, ME, T)}</div></div>`;
  }).join('');
}
function scoreHTML(side) {
  const p = ui.view.p[side], f = Math.min(1, p.points / TARGET);
  return `<div class="score s${side}${ui.fx['score' + side] ? ' bump' : ''}" id="score${side}" style="--f:${f}"><span class="pts">${p.points}</span><span class="of">${TARGET}</span></div>`;
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = ''; for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div><div class="sitepile">${ui.view.sdeck.length}</div>`;
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { Coin: 0, Unit: 1, Strike: 2, Boost: 3, Move: 4, Draw: 5 };
  const usable = (id) => { const k = CARDS[id].kind; return legal.some(a => (k === 'Unit' && a.t === 'unit' && a.card === id) || (k === 'Strike' && a.t === 'strike') || (k === 'Boost' && a.t === 'boost') || (k === 'Move' && a.t === 'move') || (k === 'Draw' && a.t === 'draw') || (k === 'Coin' && a.t === 'coin')); };
  return p.hand.map((_, i) => i).sort((a, b) => { const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]]; return R[A.kind] - R[B.kind] || A.cost - B.cost; }).map(i => {
    const id = p.hand[i], ok = usable(id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i === p.hand.length - 1) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function render() {
  const s = ui.view, T = targetsNow(), t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('sites').innerHTML = sitesHTML(T);
  for (const side of [0, 1]) { $('score' + side + 'w').innerHTML = scoreHTML(side); $('res' + side).innerHTML = resHTML(side); }
  $('hand').innerHTML = handHTML();
  const mine = !ui.over && s.turn === ME, left = mine && !ui.busy && legalActions(s).some(a => a.t !== 'end');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !left ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(h => `<div class="hist s${h.side}"><span class="chip ${h.kind} s${h.side}">${h.chip}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  ui.fx = {}; ui.fresh = 0;
}

function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1300); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function ghost(el) {
  if (!el) return;
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = el.outerHTML; d.style.left = (r.left - g.left) + 'px'; d.style.top = (r.top - g.top) + 'px'; d.style.width = r.width + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 700);
}
async function spotlight(card, side) {
  const g = $('game').getBoundingClientRect(), b = $('sites').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.top - g.top + b.height / 2) + 'px';
  $('spot').innerHTML = cardHTML(card, side);
  await wait(600);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}

async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const pl = ev.find(e => e.t === 'play'), co = ev.find(e => e.t === 'coin');
  if ((pl && pl.side === BOT) || (co && co.side === BOT)) await spotlight(pl ? pl.card : 'COIN', BOT);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  const brk = ev.filter(e => e.t === 'break');
  for (const e of brk) { const el = $('s' + e.uid); if (el) { ghost(el); } }
  if (pl && pl.card === 'STRIKE') { const el = $('u' + pl.tuid); if (el) ghost(el); }
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'play' && e.uid) ui.fx['u' + e.uid] = 'new';
    if (e.t === 'play' && e.card === 'BOOST') ui.fx['u' + e.tuid] = 'new';
    if (e.t === 'site') ui.fx['s' + e.uid] = 'new';
    if (e.t === 'break') { if (e.gains[0]) ui.fx.score0 = 1; if (e.gains[1]) ui.fx.score1 = 1; }
    if (e.t === 'draw' && e.side === ME) ui.fresh = 1;
  }
  ui.view = next; render();
  for (const e of brk) for (const side of [0, 1]) if (e.gains[side]) floatAt(centerOf($('score' + side)), '+' + e.gains[side], 'plus');
  for (const e of ev) if (e.t === 'fatigue') floatAt(centerOf($('score' + e.to)), '+1', 'plus');
  if (pl) {
    const c = CARDS[pl.card];
    ui.hist.push({ side: pl.side, kind: c.kind, chip: c.kind === 'Unit' ? c.power : ART[c.kind], out: '' });
  }
  for (const e of brk) ui.hist.push({ side: e.gains[0] >= e.gains[1] ? 0 : 1, kind: 'Break', chip: `${e.pw[0]}:${e.pw[1]}`, out: `+${e.gains[0]} / +${e.gains[1]}`, cls: 'gain' });
  if (brk.length) await wait(500);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
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
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p class="sub">${ui.s.p[ME].points} – ${ui.s.p[BOT].points}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(300);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) return;
    const a = expert(ui.s, ui.rng);
    await wait(250);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
    if (a.t === 'end') break;
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) { if (!myTurn()) return; ui.busy = true; ui.sel = null; await apply(a); ui.busy = false; render(); }
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply({ t: 'end' });
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { if (e.target.closest('#closerules')) $('rules').classList.remove('show'); return; }
  if (myTurn() && ui.sel) {
    const u = e.target.closest('.unit.tgt');
    if (u) {
      const slot = +u.dataset.slot, i = +u.dataset.i;
      if (ui.sel.card === 'STRIKE') return doAct({ t: 'strike', slot, i });
      if (ui.sel.card === 'BOOST') return doAct({ t: 'boost', slot, i });
      if (ui.sel.card === 'MOVE') { ui.sel = { ...ui.sel, from: [slot, i] }; render(); return; }
    }
    const site = e.target.closest('.site.tgt');
    if (site) {
      const slot = +site.dataset.slot;
      if (ui.sel.card === 'MOVE') return doAct({ t: 'move', from: ui.sel.from, slot });
      return doAct({ t: 'unit', card: ui.sel.card, slot });
    }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], k = CARDS[id].kind;
    if (k === 'Coin') return doAct({ t: 'coin' });
    if (k === 'Draw') return doAct({ t: 'draw' });
    ui.sel = ui.sel && ui.sel.hand === i ? null : { card: id, hand: i }; render(); return;
  }
  if (b && !b.disabled) {
    if (b.id === 'rematch' || b.id === 'newmatch') return startMatch();
    if (b.id === 'endturn') return myEndTurn();
    if (b.id === 'openrules') { $('rules').classList.add('show'); return; }
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('rules').classList.remove('show'); if (ui.sel) { ui.sel = null; render(); } } });
startMatch();
