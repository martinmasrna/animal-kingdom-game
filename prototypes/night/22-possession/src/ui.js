// Possession as a game screen against the Expert. Every play you pick one option; the Expert has
// already picked its own without seeing yours; both are revealed and the ball moves. You attack to
// the right. The win tally is kept in this browser and decides who has the ball at kickoff.

import { OPTS, TABLE, ATT, DEF, ZONES, PLAYS, HALF, STAMINA, newMatch, play, options, role, inRange } from './engine.js';
import { makeRng, matrixExpert, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-22-possession-tally';
const expert = matrixExpert(EXPERT);
const ui = { s: null, busy: false, over: false, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, reveal: null, log: [] };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

// a card's own rules: what it gains, and what it is stopped by or stops
const names = (ids) => ids.map(id => OPTS[id].name).join(', ');
function text(id) {
  if (OPTS[id].side === 'att') {
    const row = TABLE[id], stop = DEF.filter(d => row[d] === 'T');
    const gain = id === 'SHOOT' ? 'goal' : '+' + Math.max(...DEF.map(d => typeof row[d] === 'number' ? row[d] : 0));
    const zero = DEF.filter(d => row[d] === 0);
    return { big: gain, line: (stop.length ? 'stopped by ' + names(stop) : '') + (zero.length ? `; 0 vs ${names(zero)}` : '') };
  }
  const stops = ATT.filter(a => TABLE[a][id] === 'T');
  return { big: stops.length ? '✕' : '–', line: stops.length ? 'stops ' + names(stops) : 'stops nothing' };
}
function optHTML(id, { cls = '', attrs = '' } = {}) {
  const o = OPTS[id], t = text(id);
  return `<button class="opt ${o.side} ${o.basic ? 'basic' : 'card'} ${cls}" ${attrs}><span class="cost">${'●'.repeat(o.cost) || '○'}</span><span class="big${String(t.big).length > 2 ? ' long' : ''}">${t.big}</span><span class="nm">${o.name}</span><span class="tx">${t.line}</span></button>`;
}

function render() {
  const s = ui.s, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('goals').innerHTML = `<b class="g0">${s.goals[0]}</b><b class="g1">${s.goals[1]}</b>`;
  let pips = ''; for (let i = 0; i < PLAYS; i++) pips += `<i class="${i < s.play ? 'done' : ''}${i === HALF ? ' half' : ''}"></i>`;
  $('plays').innerHTML = pips;
  let z = '';
  for (let i = 0; i < ZONES; i++) {
    const rng0 = i >= ZONES - 3, rng1 = i <= 2;
    z += `<div class="zone${rng0 ? ' r0' : ''}${rng1 ? ' r1' : ''}" data-z="${i}">${s.ball === i ? `<div id="ball" class="ball s${s.poss}"></div>` : ''}</div>`;
  }
  $('pitch').innerHTML = `<div class="goal g1"></div>${z}<div class="goal g0"></div>`;
  for (const side of [0, 1]) {
    const p = s.p[side];
    let bar = ''; for (let i = 0; i < STAMINA; i++) bar += `<i class="${i < p.stamina ? 'on' : ''}"></i>`;
    $('stam' + side).innerHTML = `<span class="sn">${p.stamina}</span><span class="bar">${bar}</span><span class="pile">${p.deck.length}</span>`;
  }
  $('opphand').innerHTML = s.p[BOT].hand.map(() => '<i class="back"></i>').join('');
  const mine = s.winner === null ? options(s, ME) : [], r = role(s, ME);
  const free = !ui.busy && !ui.over;
  const basics = (r === 'att' ? ['WALK', 'SHOOT'] : ['STAND', 'BLOCK']);
  $('basics').innerHTML = basics.map(id => { const ok = free && mine.includes(id); return optHTML(id, { cls: ok ? 'ok' : 'no', attrs: `data-opt="${id}"${ok ? '' : ' disabled'}` }); }).join('');
  const order = { att: 0, def: 1 };
  $('hand').innerHTML = s.p[ME].hand.map((id, i) => ({ id, i })).sort((a, b) => order[OPTS[a.id].side] - order[OPTS[b.id].side] || OPTS[a.id].cost - OPTS[b.id].cost)
    .map(({ id }) => { const ok = free && mine.includes(id); return optHTML(id, { cls: (ok ? 'ok' : 'no') + (OPTS[id].side !== r ? ' off' : ''), attrs: `data-opt="${id}"${ok ? '' : ' disabled'}` }); }).join('');
  $('role').className = 'role ' + r;
  const rv = ui.reveal;
  $('reveal').innerHTML = rv ? `<div class="rv s0">${optHTML(rv.c[0])}</div><div class="out ${rv.cls}">${rv.out}</div><div class="rv s1">${optHTML(rv.c[1])}</div>` : '';
  $('log').innerHTML = ui.log.slice(-12).map(l => `<div class="hist">${l}</div>`).join('');
}

async function choose(id) {
  if (ui.busy || ui.over) return;
  const tok = ui.token;
  ui.busy = true; ui.reveal = null; render();
  const his = expert(ui.s, BOT, ui.rng); // chosen without looking at mine
  const ch = [id, his], ev = [];
  ui.reveal = { c: ch, out: '', cls: '' }; render();
  $('reveal').classList.remove('show'); void $('reveal').offsetWidth; $('reveal').classList.add('show');
  await wait(700);
  if (tok !== ui.token) return;
  const next = play(ui.s, ch, ev), e = ev.find(x => x.t === 'play');
  const out = e.out === 'goal' ? 'Goal' : e.out === 'turnover' ? '⇄' : '+' + e.out;
  ui.reveal = { c: ch, out, cls: e.out === 'goal' ? 'goal' : e.out === 'turnover' ? 'turn' : 'gain' };
  ui.log.push(`<span class="lc s${e.att}">${OPTS[e.a].name}</span><span class="lc s${1 - e.att}">${OPTS[e.d].name}</span><span class="lo ${ui.reveal.cls}">${out}</span>`);
  // the ball travels zone by zone, then the new state shows
  const from = ui.s.ball, to = e.out === 'goal' ? (e.att === 0 ? ZONES : -1) : next.ball;
  render();
  const step = to > from ? 1 : -1;
  for (let zz = from; zz !== to && Math.abs(to - from) > 0; zz += step) {
    await wait(140); if (tok !== ui.token) return;
    const ball = $('ball'), target = document.querySelector(`.zone[data-z="${zz + step}"]`) || document.querySelector(`.goal.g${e.att === 0 ? 0 : 1}`);
    if (ball && target) target.appendChild(ball);
  }
  if (e.out === 'goal') { $('banner').textContent = e.att === ME ? 'Goal!' : 'Goal'; $('banner').classList.remove('show'); void $('banner').offsetWidth; $('banner').classList.add('show'); await wait(900); }
  else await wait(350);
  if (tok !== ui.token) return;
  ui.s = next;
  if (next.winner !== null) finish();
  ui.busy = false; render();
}
function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p class="sub">${ui.s.goals[ME]} – ${ui.s.goals[BOT]}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}
function startMatch() {
  ui.token++;
  const t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.over = false; ui.busy = false; ui.reveal = null; ui.log = [];
  $('over').classList.remove('show');
  render();
}

document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { if (e.target.closest('#closerules')) $('rules').classList.remove('show'); return; }
  const b = e.target.closest('button');
  if (!b || b.disabled) return;
  if (b.dataset.opt) return choose(b.dataset.opt);
  if (b.id === 'rematch' || b.id === 'newmatch') return startMatch();
  if (b.id === 'openrules') $('rules').classList.add('show');
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
startMatch();
