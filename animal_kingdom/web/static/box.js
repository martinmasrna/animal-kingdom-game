// The game screen in the grey-box layout (design sandbox: screen/plan.md, screen/greybox.html): flat shapes and one font,
// every readout in the place and at the size the plan gives it, ready to be reskinned by the painted kit.
// Draws in viewer space on a 1512x800 stage: the viewer is always 'A' (light blue, den on the left), the opponent 'B' (deep red).
import { CROP, hasArt, artUrl } from './art.js';

export const STAGE = { w: 1512, h: 800 };
const key = (c, r) => `${c},${r}`;
const X = c => 256 + (c - 1) * 250, Y = r => 161 + (r - 1) * 164;
const DEN_EDGE = { A: 136, B: 1376 };
const BOARD_KW = { Immovable: '⛨', Stealth: '◐', Fragile: '✕' };
// Painted board (design sandbox screen/kit/): one plate carries the ground, trails, clearings, blank stones and both dens;
// code places the pieces on the clearings as painted (measured on the 1672x941 plate) and exactly one fruit per food in each den's
// ten pits. ?look=grey keeps the flat grey-box.
export const PAINT = new URLSearchParams(location.search).get('look') !== 'grey';
const PX = x => x / 1.10582, PY = y => y / 1.10582 - 25;   // plate pixels to stage pixels
const CLEAR = [[282.3, 225.4], [558.4, 224.0], [831.6, 223.5], [1112.7, 222.8], [1382.6, 223.7],
  [288.2, 401.2], [559.6, 398.5], [834.1, 399.7], [1110.5, 396.6], [1384.7, 399.6],
  [288.1, 568.2], [557.0, 576.0], [835.9, 575.8], [1111.0, 572.9], [1379.8, 576.2]];
const CX = (c, r) => PAINT ? PX(CLEAR[(r - 1) * 5 + c - 1][0]) : X(c), CY = (c, r) => PAINT ? PY(CLEAR[(r - 1) * 5 + c - 1][1]) : Y(r);
// Each den's ten pits from the bottom of its ridge to the top, its food count on the crown boulder, its cave mouth.
const RIDGE = { A: 110, B: 1565 }, PIT_Y = [690, 637, 584, 531, 478, 425, 372, 319, 266, 213];
const PITS = s => PIT_Y.map((y, i) => [PX(RIDGE[s] + (i % 2 ? 6 : -6)), PY(y)]);
const CROWN = { A: [PX(118), PY(150)], B: [PX(1565), PY(150)] }, MOUTH = { A: [PX(176), PY(390)], B: [PX(1500), PY(378)] };
const put = (cls, x, y, html = '', attrs = '') => `<div class="abs ${cls}" style="left:${x}px;top:${y}px" ${attrs}>${html}</div>`;

function portrait(id, D) {
  if (!hasArt(id)) return '';
  const [x, y, d] = CROP[id], w = D / d, h = w * 1.5;
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${D / 2 - x * w}px ${D / 2 - y * h}px`;
}

// A unit: portrait in a team rim, strength in the boss, buried units peeking out behind, timer and board keywords as badges.
function unit(u, under, cards, extra = '') {
  const c = cards[u.id], kw = (c.keywords || []).map(k => BOARD_KW[k]).filter(Boolean);
  const peek = under.slice(0, 3).map((b, i) => `<div class="buried ${b.owner}" style="transform:translate(${(i + 1) * 7}px,${(i + 1) * 8}px);z-index:${-i - 1}"></div>`).join('');
  const D = PAINT ? 98 : 108, rim = PAINT ? `<img class="rimimg" src="/static/kit2/rim_${u.owner === 'A' ? 'a' : 'b'}.webp" alt="" draggable="false">` : '';
  return `${peek}<div class="ring${hasArt(u.id) ? '' : ' noart'}" style="${portrait(u.id, D)}">${hasArt(u.id) ? '' : `<span>${c.name}</span>`}</div>` +
    rim + `<div class="boss num">${u.str}</div>` + (u.timer ? `<div class="timer num" title="Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}">${u.timer}</div>` : '') +
    (kw.length ? `<div class="kw" title="${(c.keywords || []).filter(k => BOARD_KW[k]).join(', ')}">${kw.join('')}</div>` : '') + extra;
}

// The board band: paths, payout stones, crossroads, and the two dens that are also the food stores.
// `ui`: { rings: [cr], hqRing, preview: {cr, id, str}, recent: [cr] }.
export function renderBoard(el, M, g, cards, ui) {
  const topOf = cr => (g.board[cr] || []).slice(-1)[0], owner = cr => (topOf(cr) || {}).owner;
  const rings = new Set(ui.rings || []), recent = new Set(ui.recent || []);
  let s = '';
  if (PAINT) s += `<img class="plate" src="/static/kit2/plate.webp" alt="" draggable="false">`;
  else {
    let p = '';
    const line = (x1, y1, x2, y2) => p += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
    for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) {
      if (c < M.cols) line(X(c), Y(r), X(c + 1), Y(r));
      if (r < M.rows) line(X(c), Y(r), X(c), Y(r + 1));
    }
    // The three front trails fan in to one point, the den's mouth, halfway down its inner edge.
    const mouthY = Y((M.rows + 1) / 2);
    for (let r = 1; r <= M.rows; r++) { line(DEN_EDGE.A, mouthY, X(1), Y(r)); line(DEN_EDGE.B, mouthY, X(M.cols), Y(r)); }
    s += `<div class="abs boardbg"></div><svg class="paths" width="${STAGE.w}" height="${STAGE.h}"><g>${p}</g></svg>`;
  }

  for (const reg of M.regions) {
    const [c, r] = reg.c, cs = [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)], o = cs.map(owner);
    const held = o.every(x => x && x === o[0]) ? o[0] : '';
    s += put(`stone num ${held}`, (CX(c, r) + CX(c + 1, r + 1)) / 2, (CY(c, r) + CY(c + 1, r + 1)) / 2, `+${reg.food}`);
  }

  for (let c = 1; c <= M.cols; c++) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), st = g.board[cr] || [], cls = (rings.has(cr) ? ' tgt' : '') + (recent.has(cr) ? ' recent' : '');
    const pv = ui.preview && ui.preview.cr === cr ? ui.preview : null, x = CX(c, r), y = CY(c, r);
    if (pv) { s += put(`cr unit A ghost${cls}`, x, y, unit({ id: pv.id, owner: 'A', str: pv.str }, st.slice().reverse(), cards), `data-cr="${cr}"`); continue; }
    if (!st.length) { s += put(`cr clear${cls}`, x, y, '', `data-cr="${cr}"`); continue; }
    const u = st[st.length - 1];
    s += put(`cr unit ${u.owner}${cls}`, x, y, unit(u, st.slice(0, -1).reverse(), cards), `data-cr="${cr}"`);
  }

  for (const side of ['A', 'B']) {
    const food = g.food[side], inc = g.income[side], win = g.winFood, ring = side === 'B' && ui.hqRing ? ' tgt' : '';
    if (PAINT) {
      // One fruit per food, ten to a pit from the bottom up: ripe for what is stored, ghosts for next turn's income.
      const ripe = Math.min(food, win), green = Math.max(0, Math.min(inc, win - ripe)), unit10 = win / PIT_Y.length;
      // Each pit shows one painted state: r ripe fruit and g ghost fruit for next turn's income (screen/kit/pits/build.py).
      let fruit = '';
      PITS(side).forEach(([px, py], i) => {
        const r = Math.max(0, Math.min(unit10, ripe - i * unit10)), t = Math.max(0, Math.min(unit10, ripe + green - i * unit10));
        fruit += put('pit', px, py, `<img src="/static/kit2/pits/${side === 'A' ? 'a' : 'b'}pit${i % 3 + 1}_${r}_${t - r}.webp" alt="" draggable="false">`);
      });
      const [mx, my] = MOUTH[side], [kx, ky] = CROWN[side];
      s += fruit + put(`dcount num ${side}`, kx, ky, food, `title="${food} / ${win}${inc ? ` · +${inc} next turn` : ''}"`) +
        put(`mouth${ring}`, mx, my, '', `data-hq="${side}" title="${side === 'A' ? 'Your den' : 'Their den'}"`);
      continue;
    }
    const H = 404, fh = Math.min(food, win) / win * H, gh = Math.max(0, Math.min(inc, win - food)) / win * H;
    s += `<div class="abs den ${side}${ui.current === side ? '' : ' off'}${ring}" data-hq="${side}" title="${food} / ${win}"><div class="count num">${food}</div>` +
      `<div class="bar"><div class="ghost${gh < 26 ? ' low' : ''}" style="bottom:${fh}px;height:${gh}px">${inc && gh > 0 ? `<span class="num">+${inc}</span>` : ''}</div>` +
      `<div class="fill" style="height:${fh}px"></div></div></div>`;
  }
  el.innerHTML = s;
}
