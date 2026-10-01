// The board: one painted plate (kit2/plate_wide.webp, drawn under the stage by the game screen: ground, trails, clearings, blank stones and both dens), with the pieces,
// payouts and food drawn onto it from painted sprites. Draws in viewer space on the STAGE: the viewer is always 'A'
// (blue, den on the left), the opponent 'B' (red). What changed since the last view comes from turn.js; this file only
// draws it. Layout and look: the design sandbox's screen/plan.md and screen/kit/.
import { CROP, hasArt, artUrl } from './art.js';
import { KEYWORDS } from './card.js';
import { pitStates, heldRegions, boardChanges, incomeFlights } from './turn.js';

export const STAGE = { w: 1512, h: 800 };
// A window taller than wide (a phone held upright) gets its own board: a painting made upright (kit2/plate_port.webp,
// your den at the bottom, you attack upward) on a tall stage, with its own measured places for everything (PORT_AT);
// nothing is turned. setView picks the layout; every place below reads it.
export const LAND = { w: 1512, h: 800 }, PORT = { w: 720, h: 1440 };
export const VIEW = { port: false };
export function setView(port) { Object.assign(STAGE, port ? PORT : LAND); VIEW.port = port; }
const key = (c, r) => `${c},${r}`;
const BOARD_KW = ['Armor', 'Stealth'];   // the keywords a unit wears as a badge on the board
const kit = f => `/static/kit2/${f}`;
const team = side => (side === 'A' ? 'a' : 'b');

// Where things are painted on the plate (measured in plate pixels, 1672 wide), converted to stage pixels.
const PX = x => x / 1.10582, PY = y => y / 1.10582 - 25;
const CLEARINGS = [[282.3, 225.4], [558.4, 224.0], [831.6, 223.5], [1112.7, 222.8], [1382.6, 223.7],
  [288.2, 401.2], [559.6, 398.5], [834.1, 399.7], [1110.5, 396.6], [1384.7, 399.6],
  [288.1, 568.2], [557.0, 576.0], [835.9, 575.8], [1111.0, 572.9], [1379.8, 576.2]];
// Upright (stage px on the 720x1440 stage, measured on plate_port; the design sandbox's screen/kit/plate/port/): the
// clearings three across (row r left to right) and five up (column c from your den), each den's ridge across the top or
// bottom with its ten pits filling left to right toward the crown boulder at its right end, the cave mouth mid-ridge.
const PORT_AT = { cols: [150, 352, 550], rows: [1037, 853, 660, 469, 271],
  pits: { A: { x: [172, 544], y: 1208 }, B: { x: [172, 544], y: 98 } },
  crown: { A: [600, 1208], B: [600, 98] }, mouth: { A: [386, 1177], B: [356, 124] } };
const at = (c, r) => { if (VIEW.port) return [PORT_AT.cols[r - 1], PORT_AT.rows[c - 1]];
  const [x, y] = CLEARINGS[(r - 1) * 5 + c - 1]; return [PX(x), PY(y)]; };
// A crossroad's centre on the stage, for anything that travels to it.
export const crossroadAt = cr => at(...cr.split(',').map(Number));
// A den's cave mouth (its HQ) on the stage, and the gem on its crown.
export const denMouthAt = side => VIEW.port ? PORT_AT.mouth[side] : MOUTH[side];
export const gemAt = side => VIEW.port ? PORT_AT.crown[side] : CROWN[side];
// Each den's ten pits from the bottom of its ridge up, the gem on its crown boulder, its cave mouth (the HQ).
const PIT_Y = [690, 637, 584, 531, 478, 425, 372, 319, 266, 213], RIDGE = { A: 110, B: 1565 };
const PITS = side => { if (VIEW.port) { const { x: [x0, x1], y } = PORT_AT.pits[side];   // upright: left to right along the ridge
    return PIT_Y.map((_, i) => [x0 + (x1 - x0) * i / 9, y + (i % 2 ? 5 : -5)]); }
  return PIT_Y.map((y, i) => [PX(RIDGE[side] + (i % 2 ? 6 : -6)), PY(y)]); };
const CROWN = { A: [PX(118), PY(150)], B: [PX(1565), PY(150)] }, MOUTH = { A: [PX(176), PY(390)], B: [PX(1500), PY(378)] };
const FLY = 0.7, GAP = 0.035;   // seconds a fruit takes from its stone to its pit, and between two fruit leaving

// Numbers are painted digits: chalk on a boss (strength, payouts), bold numerals in the den's gem. Every count animates
// through all digits, so they load up front (a digit fetched mid-count shows as a gap).
const digits = (dir, n) => String(n).split('').map(d => `<img src="${kit(`${dir}/${d === '+' ? 'p' : d}.webp`)}" alt="${d}" draggable="false">`).join('');
export const chalk = n => `<span class="chalk">${digits('chalk', n)}</span>`;
export const gemDigits = n => `<span class="gemnum">${digits('gemnum', n)}</span>`;
if (typeof Image !== 'undefined') for (let d = 0; d < 10; d++) { new Image().src = kit(`gemnum/${d}.webp`); new Image().src = kit(`chalk/${d}.webp`); }
const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

const put = (cls, x, y, html = '', attrs = '') => `<div class="abs ${cls}" style="left:${x}px;top:${y}px" ${attrs}>${html}</div>`;

// A round crop of the card art, D stage pixels across.
export function portrait(id, D) {
  if (!hasArt(id)) return '';
  const [x, y, d] = CROP[id], w = D / d, h = w * 1.5;
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${D / 2 - x * w}px ${D / 2 - y * h}px`;
}

// A unit: portrait under its team rim, strength on the boss, buried units peeking out behind, timer and board keywords as badges.
function unit(u, under, cards) {
  // Board keywords: the card's own, plus Stealth whenever the enemy can't choose it (an adjacent Armadillo gives it).
  const c = cards[u.id], kws = (c.kw || []).filter(k => BOARD_KW.includes(k) && k !== 'Stealth').concat(u.hidden ? ['Stealth'] : []);
  // the animals underneath peek out behind, down and right: each a solid disc under its team rim, a step darker (at this
  // offset a portrait showed only as a sliver, which read as a gap)
  const peek = under.slice(0, 3).map((b, i) => `<div class="buried ${b.owner} seen" style="transform:translate(${22 + i * 7}px,${20 + i * 6}px) scale(.82);z-index:${-i - 1}">`
    + `<div class="fill"></div><img class="rimimg" src="${kit(`rim_${team(b.owner)}.webp`)}" alt="" draggable="false"></div>`).join('');
  return peek + `<div class="ring${hasArt(u.id) ? '' : ' noart'}" style="${portrait(u.id, 98)}">${hasArt(u.id) ? '' : `<span>${c.name}</span>`}</div>` +
    `<img class="rimimg" src="${kit(`rim_${team(u.owner)}.webp`)}" alt="" draggable="false"><div class="boss num">${chalk(u.str)}</div>` +
    (u.timer ? `<div class="timer" data-tip="Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}">${chalk(u.timer)}</div>` : '') +
    (kws.length ? `<div class="kws">${kws.map(k => `<div class="kw" data-tip="${k}: ${KEYWORDS[k]}"><img src="${kit(`kw_${k.toLowerCase()}.webp`)}" alt="${k}" draggable="false"></div>`).join('')}</div>` : '');
}

// `g` is a viewer-space game { board, food, income, winFood }. `ui`: { rings: [cr] legal targets, hqRing (the enemy den can
// be taken), preview: {cr, id, str} (the selected card under the pointer), anim: the previous view's { board, food, income,
// fx, fromStones } when this view follows one (so what changed animates; static/timeline.js plays one step per view), else null, capture: { side, id, owner, str } when a
// unit took a den, which ends the game (it stands in that den's mouth) }.
export function renderBoard(el, M, g, cards, ui) {
  const A = ui.anim, rings = new Set(ui.rings || []);
  // the tutorial shows a region: its four crossroads and its stone glow (not rings: rings mean a click acts there)
  const shown = new Set(ui.region || []), shownAt = ui.region && ui.region[0].split(',').map(Number);
  const { landed, covered, leaving, strength } = boardChanges(A && A.board, g.board, (A && A.fx) || []);
  const held = heldRegions(M.regions, g.board);
  const stoneAt = reg => { const [c, r] = reg.c, [x1, y1] = at(c, r), [x2, y2] = at(c + 1, r + 1); return [(x1 + x2) / 2, (y1 + y2) / 2]; };
  let s = '';   // the painted ground is the game screen's (kit2/plate_wide.webp, under the stage), wider than any window

  // Payout stones: the plate's stone with a small boss on it holding the payout, in the holder's colour when held.
  for (const reg of M.regions) {
    const [x, y] = stoneAt(reg), h = held.find(r => r.id === reg.id);
    s += put(`stone pboss ${h ? h.owner : ''}${reg.c.every((v, i) => shownAt && v === shownAt[i]) ? ' shown' : ''}`, x, y, chalk('+' + reg.food));
  }

  for (let c = 1; c <= M.cols; c++) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), st = g.board[cr] || [], [x, y] = at(c, r);
    const cls = (rings.has(cr) ? ' tgt' : '') + (shown.has(cr) ? ' shown' : '') + (landed.has(cr) ? ' land' : '') + (covered.has(cr) ? ' cover' : '');
    const pv = ui.preview && ui.preview.cr === cr ? ui.preview : null;
    if (pv) { s += put(`cr unit A ghost${cls}`, x, y, unit({ id: pv.id, owner: 'A', str: pv.str }, st.slice().reverse(), cards), `data-cr="${cr}"`); continue; }
    if (!st.length) { s += put(`cr clear${cls}`, x, y, '', `data-cr="${cr}"`); continue; }
    const u = st[st.length - 1], chg = strength.get(u.iid);
    s += put(`cr unit ${u.owner}${cls}${chg ? ' strchg ' + chg : ''}`, x, y, unit(u, st.slice(0, -1).reverse(), cards), `data-cr="${cr}" data-card="${u.id}"`);
  }

  // Removed units drain, sink and leave dust; returned ones lift and fly to their owner's side of the screen.
  for (const { cr, unit: u, how } of leaving) {
    // toward its owner's hand
    const [x, y] = at(...cr.split(',').map(Number)), hx = STAGE.w / 2 - x, hy = (u.owner === 'A' ? STAGE.h - 100 : -40) - y;
    s += `<div class="abs leave ${how} unit ${u.owner}" style="left:${x}px;top:${y}px;--hx:${hx}px;--hy:${hy}px">${unit(u, [], cards)}</div>`;
  }

  const stonesOf = side => A && A.fromStones === false ? [] : held.filter(r => r.owner === side)   // a card's food comes from no stone.map(r => { const [x, y] = stoneAt(r); return { x, y, food: r.food }; });
  for (const side of ['A', 'B']) s += den(side, g, A, stonesOf(side), ui);
  // The unit that took a den stands in its mouth: the game's last move, drawn where it won.
  if (ui.capture) { const [mx, my] = denMouthAt(ui.capture.side), x = VIEW.port ? mx : mx + (ui.capture.side === 'A' ? -22 : 22), y = VIEW.port ? my + (ui.capture.side === 'A' ? 22 : -22) : my;   // seated in the mouth, clear of the crossroad beside it
    s += put(`cr unit ${ui.capture.owner} capture${A ? ' land' : ''}`, x, y, unit(ui.capture, [], cards)); }
  el.innerHTML = s;

  // The gem counts up to its new total as the fruit arrive (with reduced motion, the new total simply shows).
  if (!reducedMotion()) el.querySelectorAll('.dcount.tick').forEach(gem => {
    const from = +gem.dataset.from, to = +gem.dataset.to, t0 = performance.now() + +gem.dataset.lag, dur = +gem.dataset.dur;
    const step = t => { const n = Math.round(from + (to - from) * Math.min(1, Math.max(0, (t - t0) / dur)));
      gem.innerHTML = gemDigits(n); if (n < to && gem.isConnected) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}

// A den: ten pits of fruit (one fruit per food, ghosts for next turn's income), the gem with the count, the cave mouth.
// When food came in since the last view, fruit fly in from the held stones and each changed pit ripens as they arrive.
function den(side, g, A, stones, ui) {
  const food = g.food[side], inc = g.income[side], win = g.winFood, pits = PITS(side);
  const now = pitStates(food, inc, win), gained = !!(A && A.food && food > A.food[side]);
  const before = gained ? pitStates(A.food[side], A.income[side], win) : null;
  const flights = gained ? incomeFlights(A.food[side], food, win, stones, { gap: GAP }) : [];
  const arrive = {};
  let s = '';
  flights.forEach(({ from, pit, delay }, j) => {
    const { x, y } = stones[from], [tx, ty] = pits[pit];
    arrive[pit] = delay + FLY;
    s += `<i class="flyfruit" style="left:${x}px;top:${y}px;--dx:${tx - x + (j % 3 - 1) * 8}px;--dy:${ty - y}px;animation-delay:${delay}s;` +
      `background-image:url(${kit(`fly_${team(side)}${j % 4}.webp`)})"></i>`;
  });
  const src = (p, i) => kit(`pits/${team(side)}pit${i % 3 + 1}_${p.ripe}_${p.ghost}.webp`);
  let k = 0;
  pits.forEach(([x, y], i) => {
    const changed = before && (before[i].ripe !== now[i].ripe || before[i].ghost !== now[i].ghost);
    const delay = changed ? `style="animation-delay:${i in arrive ? arrive[i] - 0.12 : 0.15 + 0.11 * k++}s"` : '';
    s += put(`pit${changed ? ' ripen' : ''}`, x, y, (changed ? `<img class="was" src="${src(before[i], i)}" alt="" draggable="false" ${delay}>` : '') +
      `<img class="now" src="${src(now[i], i)}" alt="" draggable="false" ${delay}>`);
  });
  const [kx, ky] = gemAt(side), [mx, my] = denMouthAt(side), counting = gained && !reducedMotion();
  const timing = flights.length ? `data-lag="${FLY * 1000}" data-dur="${flights.length * GAP * 1000}"`
    : `data-lag="150" data-dur="${300 + 110 * Math.ceil((food - (gained ? A.food[side] : food)) / 10)}"`;
  return s + put(`dcount ${side}${gained ? ' tick' : ''}`, kx, ky, gemDigits(counting ? A.food[side] : food),
    `data-from="${gained ? A.food[side] : food}" data-to="${food}" ${timing} data-tip="${food} / ${win}${inc ? ` · +${inc} next turn` : ''}"`) +
    put(`mouth${side === 'B' && ui.hqRing ? ' tgt' : ''}`, mx, my, '', `data-hq="${side}"`);
}
