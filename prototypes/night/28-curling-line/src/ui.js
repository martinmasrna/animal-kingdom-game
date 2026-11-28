// Curling line as a game screen against the Expert. Every throw goes through legalActions/act; each
// throw slides and pushes step by step. The win tally is kept in this browser and decides who holds
// the hammer in end 1 (alternating).

import { CARDS, CELLS, MARK, HOUSE, ENDS, ENERGY, LAG, newMatch, act, legalActions, slide } from './engine.js';
import { makeRng, expertBot } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-28-curling-tally';
const expert = expertBot({ budget: 2000 });
const ui = { s: null, view: null, busy: false, over: false, sel: null, ends: [], fresh: 0, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const xOf = (cell) => ((cell - 0.5) / CELLS * 100) + '%';

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = id ? CARDS[id] : { name: 'Lag', cost: 0, d: LAG };
  const big = c.d ? c.d : '4–12';
  return `<button class="card${id ? '' : ' lag'}${id === 'Any' ? ' any' : ''} ${cls}" ${attrs}>${c.cost ? `<span class="cgem">${c.cost}</span>` : ''}<div class="art"><span class="big">${big}</span></div><div class="nm">${c.name}</div></button>`;
}

// ------------------------------------------------------------------ rendering
const myTurn = () => !ui.busy && !ui.over && ui.view.toMove === ME && ui.view.winner === null;
const thrownBy = (s, side) => side === s.hammer ? Math.floor(s.throwNo / 2) : Math.ceil(s.throwNo / 2);
function boardHTML() {
  const s = ui.view, n = Math.max(ENDS, s.end, ui.ends.length);
  let html = '<table>';
  for (const side of [BOT, ME]) {
    html += `<tr class="s${side}"><td class="dot"><i></i></td>`;
    for (let e = 1; e <= n; e++) { const r = ui.ends[e - 1]; const v = r === undefined ? '' : r && r[0] === side ? r[1] : r ? '' : '·'; html += `<td class="${e === s.end && !ui.over ? 'now' : ''}">${v}</td>`; }
    html += `<td class="tot pt">${s.score[side]}</td></tr>`;
  }
  return html + '</table>';
}
function infoHTML(side) {
  const s = ui.view, P = s.p[side], left = 4 - thrownBy(s, side);
  let stones = ''; for (let i = 0; i < 4; i++) stones += `<i class="${i < left ? '' : 'gone'}"></i>`;
  let gems = ''; for (let i = 0; i < ENERGY; i++) gems += `<i class="gemc${i < s.energy[side] ? ' on' : ''}"></i>`;
  const backs = side === BOT ? `<div class="backs">${'<i class="back"></i>'.repeat(P.hand.length)}</div>` : '';
  return `${s.hammer === side ? '<span class="hammer">🔨</span>' : ''}<div class="left s${side}">${stones}</div><div class="energy"><b>${s.energy[side]}</b>${gems}</div><span class="pile s${side}">${P.deck.length}</span>${backs}`;
}
function sheetHTML(stones) {
  const tg = ui.sel && myTurn() ? new Set(legalActions(ui.view).filter(a => a.card === ui.sel).map(a => a.d)) : new Set();
  let cells = '';
  for (let c = 1; c <= CELLS; c++) {
    const d = Math.abs(c - MARK), house = d <= HOUSE ? (d === 0 ? ' house h1 mark' : d === 1 ? ' house h1' : d === 2 ? ' house h2' : ' house') : '';
    cells += `<div class="cell${house}${tg.has(c) ? ' tgt' : ''}" data-cell="${c}">${c}</div>`;
  }
  const st = stones.map(x => `<div class="stone s${x.owner}" id="st${x.uid}" style="left:${xOf(x.cell)}"></div>`).join('');
  return `<div class="cells">${cells}</div><div class="stones">${st}</div>`;
}
function handHTML() {
  const s = ui.view, can = myTurn(), L = can ? legalActions(s) : [];
  const ok = (id) => L.some(a => a.card === id);
  let html = cardHTML(null, { cls: can ? 'ok' : '', attrs: `data-card=""${can ? '' : ' disabled'}` });
  const H = s.p[ME].hand.map((id, i) => i).sort((a, b) => (CARDS[s.p[ME].hand[a]].d || 99) - (CARDS[s.p[ME].hand[b]].d || 99));
  for (const i of H) { const id = s.p[ME].hand[i], k = ok(id); html += cardHTML(id, { cls: (k ? 'ok' : '') + (ui.sel === id ? ' sel' : '') + (ui.fresh ? ' drawn' : ''), attrs: `data-card="${id}"${k ? '' : ' disabled'}` }); }
  return html;
}
function render() {
  const s = ui.view, t = loadTally();
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('board').innerHTML = boardHTML();
  $('info1').innerHTML = infoHTML(BOT); $('info0').innerHTML = infoHTML(ME);
  $('sheet').innerHTML = sheetHTML(s.stones);
  $('hand').innerHTML = handHTML();
  ui.fresh = 0;
}
function banner(text, side) { const b = $('banner'); b.textContent = text; b.className = side === undefined ? '' : 's' + side; void b.offsetWidth; b.classList.add('show'); }

// ------------------------------------------------------------------ playback
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const th = ev.find(e => e.t === 'throw'), sc = ev.find(e => e.t === 'score');
  // the throw, then each push, on the table as it was
  const layer = document.querySelector('#sheet .stones');
  for (const m of th.moves) {
    let el = $('st' + m.uid);
    if (m.thrown) { el = document.createElement('div'); el.className = 'stone s' + th.side; el.id = 'st' + m.uid; el.style.left = '-6%'; layer.appendChild(el); void el.offsetWidth; }
    if (!el) continue;
    if (m.out || m.to > CELLS) { el.style.left = m.out ? '2%' : '106%'; el.classList.add('out'); }
    else el.style.left = xOf(m.to);
    await wait(300);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  }
  if (sc) {
    // the end's last table: the counting stones glow, the scoreboard fills, then the next end
    ui.ends[sc.end - 1] = sc.result;
    if (sc.result) {
      // the end's final stones, as the engine had them before clearing (the thrown stone keeps its uid)
      const w = sc.result[0], after = prev.stones.map(x => ({ ...x }));
      slide(after, prev.toMove, a.d, prev.uid);
      const opp = Math.min(99, ...after.filter(x => x.owner !== w && Math.abs(x.cell - MARK) <= HOUSE).map(x => Math.abs(x.cell - MARK)));
      for (const x of after) if (x.owner === w && Math.abs(x.cell - MARK) <= HOUSE && Math.abs(x.cell - MARK) < opp) { const el = $('st' + x.uid); if (el) el.classList.add('count'); }
      banner((w === ME ? 'You +' : '+') + sc.result[1], w);
    } else banner('No score');
    $('board').innerHTML = boardHTML();
    await wait(1700);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    if (next.winner !== null) { ui.view = next; finish(); render(); return; }
    ui.fresh = 1;
  }
  ui.view = next; render();
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
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, hammer: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.sel = null; ui.ends = [];
  $('over').classList.remove('show');
  ui.busy = true; render();
  await wait(700);
  if (tok !== ui.token) return;
  await run(tok);
}
async function run(tok) {
  while (tok === ui.token && !ui.over && ui.s.toMove === BOT && ui.s.winner === null) {
    ui.busy = true; render();
    await wait(500);
    if (tok !== ui.token) return;
    const a = expert(ui.s, ui.rng);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
  }
  if (tok !== ui.token) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
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
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (!myTurn()) return;
  const cell = e.target.closest('.cell.tgt');
  if (cell && ui.sel) return doAct({ t: 'throw', card: ui.sel, d: +cell.dataset.cell });
  if (b && !b.disabled && b.dataset.card !== undefined) {
    const id = b.dataset.card || null;
    if (!id) return doAct({ t: 'throw', card: null, d: LAG });
    if (!CARDS[id].d) { ui.sel = ui.sel === id ? null : id; render(); return; }
    return doAct({ t: 'throw', card: id, d: CARDS[id].d });
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (ui.sel) { ui.sel = null; render(); } $('rules').classList.remove('show'); } });
startMatch();
