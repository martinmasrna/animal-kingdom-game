// Board renderer: the painted kit (static/kit/, from the design sandbox's board/r7) assembled over the plateau.
// Draws in viewer space and stage pixels (the 1672x941 stage in app.css): the viewer is always 'A'
// (bronze, den on the left), the opponent 'B' (iron, den on the right).
// `g` is a viewer-space game: { board: {cr: [{id, owner, str, timer}]}, food, income, winFood },
// `ui` carries what is interactive: { rings: [cr], hqRing: bool, preview: {cr, id, str} },
// plus `recent`: the crossroads the opponent placed on since your last move.
import { CROP, hasArt, artUrl } from './art.js';

const key = (c, r) => `${c},${r}`;
export const kit = n => `/static/kit/${n}.webp`;
export const kitImg = n => `<img src="${kit(n)}" alt="" draggable="false">`;
const OWN = { A: { rim: 'rim_a', gem: 'gem_a', token: 'token_a', den: 'den_a' }, B: { rim: 'rim_b', gem: 'gem_b', token: 'token_b', den: 'den_b' } };
// Crossroads span the plateau; each den stands off its edge, with its food silo and food plaque below it.
const HQX = { A: 150, B: 1522 }, DEN_Y = 290, PORTRAIT = 136;
// Keywords that change what can be done to a unit already on the board (Flight and Apex Predator only matter while placing).
const BOARD_KW = { Immovable: 'kw_immovable', Stealth: 'kw_stealth', Fragile: 'kw_fragile' };

// A round crop of the card art, `D` stage pixels across; the name stands in for missing art.
export function portrait(id, D, name) {
  if (!hasArt(id)) return `<div class="portrait noart"><span>${name}</span></div>`;
  const [x, y, d] = CROP[id], w = D / d, h = w * 1.5;
  return `<div class="portrait" style="background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${D / 2 - x * w}px ${D / 2 - y * h}px"></div>`;
}

export function renderBoard(el, M, g, cards, ui) {
  const topOf = cr => (g.board[cr] || []).slice(-1)[0], owner = cr => (topOf(cr) || {}).owner;
  const nb = cr => { const [c, r] = cr.split(',').map(Number), out = []; if (c > 1) out.push(key(c - 1, r)); if (c < M.cols) out.push(key(c + 1, r)); if (r > 1) out.push(key(c, r - 1)); if (r < M.rows) out.push(key(c, r + 1)); return out; };
  function connected(p) {
    const f = p === 'A' ? 1 : M.cols, seen = new Set(), q = [];
    for (let r = 1; r <= M.rows; r++) if (owner(key(f, r)) === p) { seen.add(key(f, r)); q.push(key(f, r)); }
    while (q.length) for (const n of nb(q.shift())) if (!seen.has(n) && owner(n) === p) { seen.add(n); q.push(n); }
    return seen;
  }
  function regionState(reg) {
    const [c, r] = reg.c, cs = [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)];
    for (const p of ['A', 'B']) { const n = cs.filter(x => owner(x) === p).length; if (n === 4) return { owner: p, full: true }; if (n === 3 && cs.every(x => owner(x) === p || !topOf(x))) return { owner: p, full: false }; }
    return null;
  }
  const X = c => 390 + (c - 1) * 930 / (M.cols - 1), Y = r => 190 + (r - 1) * 340 / (M.rows - 1);
  const conn = { A: connected('A'), B: connected('B') };
  const rings = new Set(ui.rings || []), recent = new Set(ui.recent || []);
  const put = (cls, x, y, html = '', style = '', attrs = '') => `<div class="sp ${cls}" style="left:${x}px;top:${y}px;${style}" ${attrs}>${html}</div>`;

  let s = '';
  // Region washes: the held area in the holder's colour, dashed while one corner is still open.
  for (const reg of M.regions) {
    const st = regionState(reg), [c, r] = reg.c; if (!st) continue;
    s += `<div class="wash ${st.owner}${st.full ? '' : ' part'}" style="left:${X(c)}px;top:${Y(r)}px;width:${X(c + 1) - X(c)}px;height:${Y(r + 1) - Y(r)}px"></div>`;
  }
  // Trails: lit in the owner's metal when both ends are theirs and chained back to their den.
  const trail = (x, y, w, h, deg, lit) => put(`trail${lit ? ' lit ' + lit : ''}`, x, y, kitImg('trail') + (lit ? `<img class="tint" src="${kit('trail')}" alt="" draggable="false">` : ''), `width:${w}px;height:${h}px;transform:translate(-50%,-50%) rotate(${deg}deg)`);
  const litOf = (a, b) => { const o = owner(a); return o && o === owner(b) && conn[o].has(a) && conn[o].has(b) ? o : ''; };
  for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) {
    if (c < M.cols) s += trail((X(c) + X(c + 1)) / 2, Y(r), 170, 60, 0, litOf(key(c, r), key(c + 1, r)));
    if (r < M.rows) s += trail(X(c), (Y(r) + Y(r + 1)) / 2, 110, 56, 90, litOf(key(c, r), key(c, r + 1)));
  }
  for (let r = 1; r <= M.rows; r++) for (const p of ['A', 'B']) {
    const front = key(p === 'A' ? 1 : M.cols, r), fx = X(p === 'A' ? 1 : M.cols), hx = HQX[p] + (p === 'A' ? 70 : -70);
    const dx = fx - hx, dy = Y(r) - DEN_Y;
    s += trail((fx + hx) / 2, (Y(r) + DEN_Y) / 2, Math.hypot(dx, dy) - 30, 58, Math.atan2(dy, dx) * 180 / Math.PI, owner(front) === p ? p : '');
  }
  for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) s += put('socket', X(c), Y(r), kitImg('socket'));

  // Regions: a stone token with the payout, set in the holder's metal (faint while one corner is still open).
  for (const reg of M.regions) {
    const st = regionState(reg), [c, r] = reg.c;
    s += put(`token lift${st ? (st.full ? '' : ' part') : ' idle'}`, (X(c) + X(c + 1)) / 2, (Y(r) + Y(r + 1)) / 2,
      kitImg(st ? OWN[st.owner].token : 'token') + `<span class="num">+${reg.food}</span>`);
  }

  // Dens (headquarters), each with its food silo filling toward the win threshold; the paler band is next turn's income.
  for (const p of ['A', 'B']) {
    const x = HQX[p], food = g.food[p], inc = g.income[p], win = g.winFood;
    const f1 = Math.min(1, food / win), f2 = Math.min(1, (food + inc) / win), target = p === 'B' && ui.hqRing;
    s += put(`den lift${target ? ' tgt legal' : ''}`, x, DEN_Y, kitImg(OWN[p].den), '', target ? 'data-hq="1"' : '');
    s += put('silo lift', x, 520, `<div class="win"><div class="inc" style="height:${f2 * 100}%"></div><div class="fill" style="height:${f1 * 100}%"></div></div>` + kitImg('silo'));
    s += put('plaque food lift', x, 655, kitImg('plaque') + `<span class="num">${food}<small>+${inc}</small></span>`);
  }

  // Crossroads: the hit area for everything placed on it.
  for (let c = M.cols; c >= 1; c--) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), stack = g.board[cr] || [];
    let h = '';
    if (ui.preview && ui.preview.cr === cr) h = unit({ id: ui.preview.id, owner: 'A', str: ui.preview.str }, stack.slice().reverse(), true);
    else if (stack.length) h = unit(stack[stack.length - 1], stack.slice(0, -1).reverse(), false);
    const cls = ['cr', rings.has(cr) ? 'tgt legal' : '', stack.length ? 'occ' : '', recent.has(cr) ? 'recent' : ''].join(' ');
    s += put(cls, X(c), Y(r), h, '', `data-cr="${cr}"`);
  }

  // `under`: the buried units, top first, each peeking out below as a darker rim in its owner's metal.
  function unit(u, under, ghost) {
    const card = cards[u.id], base = card.str === '*' ? null : card.str;
    const delta = base !== null && u.str !== base ? (u.str > base ? ' up' : ' down') : '';
    const peek = under.slice(0, 3).map((b, i) => `<div class="buried" style="transform:translate(${(i + 1) * 8}px,${(i + 1) * 9}px);z-index:${-i - 1}">${kitImg(OWN[b.owner].rim)}</div>`).join('');
    const kws = (card.kw || []).filter(k => BOARD_KW[k]).map(k => `<img src="${kit(BOARD_KW[k])}" alt="" title="${k}" draggable="false">`).join('');
    const rim = ui.enamel ? OWN[u.owner].rim + '_enamel' : OWN[u.owner].rim;
    return `<div class="unit lift ${u.owner}${ghost ? ' ghost' : ''}">${peek}${portrait(u.id, PORTRAIT, card.name)}<img class="rim" src="${kit(rim)}" alt="" draggable="false">` +
      `<div class="ribbon">${kitImg(u.owner === 'A' ? 'ribbon_a' : 'ribbon_b')}<span class="num">${card.name}</span></div>` + (kws ? `<div class="kws">${kws}</div>` : '') +
      `<div class="gem">${kitImg(OWN[u.owner].gem)}<span class="num${delta}">${u.str}</span></div>` +
      (u.timer && !ghost ? `<div class="timer">${kitImg('token')}<span class="num">${u.timer}</span></div>` : '') +
      (under.length && !ghost ? `<div class="under num">+${under.length}</div>` : '') + '</div>';
  }

  el.innerHTML = s;
}
