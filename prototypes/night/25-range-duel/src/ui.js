// 25 Range duel as a page: you (fighter A) against Expert. Expert picks its move from the turn's
// state before yours is in; both go to the engine's submit() and the turn plays out event by event.

import { CARDS, SPACES, TURNS, ENERGY_MAX, newMatch, submit, canSubmit } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-25-tally';
const expert = expertBot({ samples: 40, timeMs: 1200 });
const ui = { s: null, busy: false, over: false, sel: null, botMove: null, disp: null, shown: null, hist: [], rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

const BASICS = [{ t: 'move', card: 'STEP', dir: 1 }, { t: 'move', card: 'STEP', dir: -1 }, { t: 'move', card: 'REST' }];
function moveHTML(a, { cls = '', attrs = '', tag = 'div' } = {}) {
  const c = CARDS[a.card];
  const mv = c.dir ? (a.dir > 0 ? '→1' : '←1') : c.mv > 0 ? '→' + c.mv : c.mv < 0 ? '←' + (-c.mv) : '';
  const rg = c.rng ? (c.rng[0] === c.rng[1] ? c.rng[0] : c.rng[0] + '–' + c.rng[1]) : '';
  const tx = c.guard ? '−3 damage to you' : c.push ? 'push 1' : c.rest ? '+1 energy next turn' : '';
  return `<${tag} class="card${c.basic ? ' basic' : ''} ${cls}" ${attrs}>${c.basic ? '' : `<span class="cost">${c.cost}</span>`}<span class="spd">${c.speed}</span><div class="nm">${c.name}</div>${c.dmg ? `<div class="dmg">${c.dmg}</div>` : ''}<div class="rg">${[rg, mv].filter(Boolean).join(' · ')}</div>${tx ? `<div class="tx">${tx}</div>` : ''}</${tag}>`;
}
const myMove = () => !ui.busy && !ui.over && ui.s.need[ME];

function placeFighters() {
  const L = $('line'), A = $('arena'), la = L.getBoundingClientRect(), ar = A.getBoundingClientRect(), w = la.width / SPACES;
  for (const side of [0, 1]) { const el = $('f' + side); el.style.left = (la.left - ar.left + w * (ui.disp.pos[side] - 0.5)) + 'px'; el.textContent = Math.max(0, ui.disp.life[side]); }
}
function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  let tr = ''; for (let i = 1; i <= TURNS; i++) tr += `<i class="${i < s.turn ? 'done' : i === s.turn ? 'now' : ''}"></i>`;
  $('turns').innerHTML = tr;
  const pips = (e) => { let h = ''; for (let i = 0; i < ENERGY_MAX; i++) h += `<i class="${i < e ? 'on' : ''}"></i>`; return `<div class="energy">${h}</div>`; };
  const O = s.p[BOT], P = s.p[ME];
  $('opp').className = 'who'; $('me').className = 'who';
  $('opp').innerHTML = `<div class="backs">${'<i class="back"></i>'.repeat(O.hand.length)}</div>${pips(O.energy)}<span class="pile s1">${O.deck.length}</span><span class="pile disc">${O.discard.length}</span>`;
  $('me').innerHTML = `${pips(P.energy)}<span class="pile s0">${P.deck.length}</span><span class="pile disc">${P.discard.length}</span>`;
  $('line').innerHTML = '<div class="sp"></div>'.repeat(SPACES);
  placeFighters();
  $('shown').innerHTML = ui.shown ? ui.shown.map((a, side) => moveHTML(a, { cls: ui.shown.cancel && ui.shown.cancel[side] ? 'cancel' : '' })).join('') : '';
  const hand = P.hand.map((id, i) => ({ a: { t: 'move', card: id }, i })).sort((x, y) => CARDS[x.a.card].speed - CARDS[y.a.card].speed || CARDS[x.a.card].cost - CARDS[y.a.card].cost);
  const btn = (a, k) => { const ok = myMove() && canSubmit(s, ME, a); return moveHTML(a, { tag: 'button', cls: (ok ? 'ok' : 'no') + (ui.sel && ui.sel.k === k ? ' sel' : ''), attrs: `data-k="${k}"${ok ? '' : ' disabled'}` }); };
  $('hand').innerHTML = hand.map(({ a, i }) => btn(a, 'h' + i)).join('') + '<span class="gap"></span>' + BASICS.map((a, i) => btn(a, 'b' + i)).join('');
  $('controls').innerHTML = `<button id="go"${myMove() && ui.sel ? '' : ' disabled'}>Go</button>`;
  $('history').innerHTML = ui.hist.slice(-16).map(h => `<div class="hist"><span class="a">${h.m[0]}${h.d[0] ? ` <b class="d">−${h.d[0]}</b>` : ''}</span><span class="b">${h.m[1]}${h.d[1] ? ` <b class="d">−${h.d[1]}</b>` : ''}</span></div>`).join('');
}
function floatAt(el, text, cls = '') {
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = (r.left - g.left + r.width / 2) + 'px'; f.style.top = (r.top - g.top - 6) + 'px';
  $('game').appendChild(f); setTimeout(() => f.remove(), 1150);
}
const label = (a) => CARDS[a.card].name + (CARDS[a.card].dir ? (a.dir > 0 ? ' →' : ' ←') : '');

async function prepare(tok) {
  if (ui.over) return;
  ui.busy = true; render(); await wait(30);
  if (tok !== ui.token) return;
  ui.botMove = expert(ui.s, BOT, ui.rng);
  ui.busy = false; render();
}
async function go() {
  if (!myMove() || !ui.sel || !canSubmit(ui.s, ME, ui.sel.a)) return;
  const tok = ui.token, before = ui.s, mine = ui.sel.a, ev = [];
  ui.busy = true; ui.sel = null;
  let s = submit(before, ME, mine, ev);
  s = submit(s, BOT, ui.botMove, ev); ui.botMove = null;
  ui.shown = [mine, s.last.moves[BOT]]; ui.shown.cancel = [false, false];
  render();
  for (const side of [0, 1]) $('f' + side).classList.toggle('guard', !!CARDS[ui.shown[side].card].guard);
  await wait(900);
  const dmg = [0, 0];
  for (const e of ev) {
    if (tok !== ui.token) return;
    if (e.t === 'move' || e.t === 'push') { ui.disp.pos[e.side] = e.pos; placeFighters(); await wait(480); }
    if (e.t === 'hit') { ui.disp.life[e.target] = e.life; dmg[e.target] += e.n; const el = $('f' + e.target); el.classList.remove('hit'); void el.offsetWidth; el.classList.add('hit'); floatAt(el, e.n ? '−' + e.n : '0'); placeFighters(); await wait(650); }
    if (e.t === 'miss') { floatAt($('f' + e.side), 'miss', 'miss'); await wait(450); }
    if (e.t === 'cancel') { ui.shown.cancel[e.side] = true; render(); await wait(400); }
  }
  await wait(500);
  if (tok !== ui.token) return;
  for (const side of [0, 1]) $('f' + side).classList.remove('guard');
  ui.hist.push({ m: [label(mine), label(s.last.moves[BOT])], d: [dmg[BOT], dmg[ME]] }); // the damage each move dealt
  ui.s = s; ui.shown = null; ui.disp = { pos: [s.p[0].pos, s.p[1].pos], life: [s.p[0].life, s.p[1].life] };
  if (s.winner !== null) { finish(); render(); return; }
  await prepare(tok);
}
function finish() {
  if (ui.over) return;
  ui.over = true; ui.busy = false;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.disp = { pos: [ui.s.p[0].pos, ui.s.p[1].pos], life: [ui.s.p[0].life, ui.s.p[1].life] };
  ui.over = false; ui.hist = []; ui.sel = null; ui.botMove = null; ui.shown = null;
  $('over').classList.remove('show');
  await prepare(tok);
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && b.id === 'rulesbtn') { $('rules').classList.add('show'); return; }
  if ((b && b.id === 'rulesclose') || e.target.id === 'rules') { $('rules').classList.remove('show'); return; }
  if (b && (b.id === 'newgame' || b.id === 'rematch')) return startMatch();
  if (!myMove()) return;
  if (b && b.id === 'go') return go();
  if (b && b.dataset.k) {
    const k = b.dataset.k, P = ui.s.p[ME];
    const a = k[0] === 'b' ? BASICS[+k.slice(1)] : { t: 'move', card: P.hand[+k.slice(1)] };
    ui.sel = ui.sel && ui.sel.k === k ? null : { k, a };
    render(); return;
  }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.sel = null; $('rules').classList.remove('show'); render(); } if (e.key === 'Enter' && ui.sel) go(); });
window.addEventListener('resize', () => { if (ui.s) placeFighters(); });
startMatch();
