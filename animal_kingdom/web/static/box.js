// The game screen in the grey-box layout (design sandbox: screen/plan.md, screen/greybox.html): flat shapes and one font,
// every readout in the place and at the size the plan gives it, ready to be reskinned by the painted kit.
// Draws in viewer space on a 1512x800 stage: the viewer is always 'A' (light blue, den on the left), the opponent 'B' (deep red).
import { CROP, hasArt, artUrl } from './art.js';

export const STAGE = { w: 1512, h: 800 };
const key = (c, r) => `${c},${r}`;
const X = c => 256 + (c - 1) * 250, Y = r => 161 + (r - 1) * 164;
const DEN_EDGE = { A: 136, B: 1376 };
const BOARD_KW = { Immovable: '⛨', Stealth: '◐', Fragile: '✕' };
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
  return `${peek}<div class="ring${hasArt(u.id) ? '' : ' noart'}" style="${portrait(u.id, 108)}">${hasArt(u.id) ? '' : `<span>${c.name}</span>`}</div>` +
    `<div class="boss num">${u.str}</div>` + (u.timer ? `<div class="timer num" title="Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}">${u.timer}</div>` : '') +
    (kw.length ? `<div class="kw" title="${(c.keywords || []).filter(k => BOARD_KW[k]).join(', ')}">${kw.join('')}</div>` : '') + extra;
}

// The board band: paths, payout stones, crossroads, and the two dens that are also the food stores.
// `ui`: { rings: [cr], hqRing, preview: {cr, id, str}, recent: [cr] }.
export function renderBoard(el, M, g, cards, ui) {
  const topOf = cr => (g.board[cr] || []).slice(-1)[0], owner = cr => (topOf(cr) || {}).owner;
  const rings = new Set(ui.rings || []), recent = new Set(ui.recent || []);
  let p = '';
  const line = (x1, y1, x2, y2) => p += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
  for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) {
    if (c < M.cols) line(X(c), Y(r), X(c + 1), Y(r));
    if (r < M.rows) line(X(c), Y(r), X(c), Y(r + 1));
  }
  for (let r = 1; r <= M.rows; r++) { line(DEN_EDGE.A, Y(r), X(1), Y(r)); line(DEN_EDGE.B, Y(r), X(M.cols), Y(r)); }
  let s = `<div class="abs boardbg"></div><svg class="paths" width="${STAGE.w}" height="${STAGE.h}"><g>${p}</g></svg>`;

  for (const reg of M.regions) {
    const [c, r] = reg.c, cs = [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)], o = cs.map(owner);
    const held = o.every(x => x && x === o[0]) ? o[0] : '';
    s += put(`stone num ${held}`, (X(c) + X(c + 1)) / 2, (Y(r) + Y(r + 1)) / 2, `+${reg.food}`);
  }

  for (let c = 1; c <= M.cols; c++) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), st = g.board[cr] || [], cls = (rings.has(cr) ? ' tgt' : '') + (recent.has(cr) ? ' recent' : '');
    const pv = ui.preview && ui.preview.cr === cr ? ui.preview : null;
    if (pv) { s += put(`cr unit A ghost${cls}`, X(c), Y(r), unit({ id: pv.id, owner: 'A', str: pv.str }, st.slice().reverse(), cards), `data-cr="${cr}"`); continue; }
    if (!st.length) { s += put(`cr clear${cls}`, X(c), Y(r), '', `data-cr="${cr}"`); continue; }
    const u = st[st.length - 1];
    s += put(`cr unit ${u.owner}${cls}`, X(c), Y(r), unit(u, st.slice(0, -1).reverse(), cards), `data-cr="${cr}"`);
  }

  // Dens: the count on top, food filling from the bottom to food/win, next turn's income as a ghost band with its number.
  for (const side of ['A', 'B']) {
    const food = g.food[side], inc = g.income[side], H = 404, win = g.winFood;
    const fh = Math.min(food, win) / win * H, gh = Math.max(0, Math.min(inc, win - food)) / win * H;
    const ring = side === 'B' && ui.hqRing ? ' tgt' : '';
    s += `<div class="abs den ${side}${ui.current === side ? '' : ' off'}${ring}" data-hq="${side}" title="${food} / ${win}"><div class="count num">${food}</div>` +
      `<div class="bar"><div class="ghost${gh < 26 ? ' low' : ''}" style="bottom:${fh}px;height:${gh}px">${inc && gh > 0 ? `<span class="num">+${inc}</span>` : ''}</div>` +
      `<div class="fill" style="height:${fh}px"></div></div></div>`;
  }
  el.innerHTML = s;
}
