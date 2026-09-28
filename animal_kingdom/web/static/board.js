// Board renderer: the painted kit (static/kit/, from the design sandbox's board/r7) assembled over the plateau.
// Draws in viewer space and stage pixels (the 1672x941 stage in app.css): the viewer is always 'A'
// (blue, den on the left), the opponent 'B' (red, den on the right).
// `g` is a viewer-space game: { board: {cr: [{id, owner, str, timer}]}, food, income, winFood },
// `ui` carries what is interactive: { rings: [cr], hqRing: bool, preview: {cr, id, str} },
// plus `recent`: the crossroads the opponent placed on since your last move.
import { CROP, hasArt, artUrl } from './art.js';

const key = (c, r) => `${c},${r}`;
// Map D's clearings as painted: centre x, y and radius (measured in board/r8/kit/clearings.json).
const CLEAR = {"1,1": [368.7, 182.1, 64.5], "2,1": [601.8, 180.1, 65.0], "3,1": [842.7, 181.2, 67.3], "4,1": [1076.4, 179.2, 70.1], "5,1": [1314.3, 179.9, 68.5], "1,2": [374.1, 368.8, 68.7], "2,2": [603.8, 368.7, 68.5], "3,2": [841.5, 368.4, 67.8], "4,2": [1072.3, 371.5, 67.3], "5,2": [1310.2, 370.7, 69.2], "1,3": [366.8, 555.4, 67.6], "2,3": [604.9, 556.9, 70.0], "3,3": [840.4, 560.6, 71.5], "4,3": [1076.1, 557.8, 70.0], "5,3": [1311.8, 561.4, 69.9]};
// Medallion sprites (board/r10): sprite size, hole centre and radius, outer radius, strength-plate face centre and size (sprite px).
const MEDG = {
  D: {"a": {"W": 375, "hx": 188.5, "hy": 196.5, "hr": 117.5, "R": 185.7, "plate": [67.5, 69.5, 95, 103]}, "b": {"W": 375, "hx": 188.5, "hy": 196.5, "hr": 116.5, "R": 186.3, "plate": [67.0, 71.0, 96, 104]}},
  E: {"a": {"W": 393, "hx": 206.0, "hy": 183.0, "hr": 120.0, "R": 187.0, "plate": [67.5, 69.5, 97, 101]}, "b": {"W": 393, "hx": 206.0, "hy": 184.5, "hr": 120.0, "R": 186.8, "plate": [67.0, 70.5, 96, 101]}},
  F: {"a": {"W": 387, "hx": 203.5, "hy": 179.0, "hr": 115.5, "R": 183.6, "plate": [70.0, 71.5, 96, 99], "outer0": [0, 0]}, "b": {"W": 388, "hx": 203.5, "hy": 179.5, "hr": 115.5, "R": 183.9, "plate": [69.5, 72.0, 97, 98], "outer0": [0, 0]}},
};
const PAW = `<svg viewBox="0 0 40 40"><ellipse cx="20" cy="27" rx="10" ry="8.5"/><ellipse cx="8" cy="15" rx="4" ry="5.2" transform="rotate(-20 8 15)"/><ellipse cx="16" cy="9" rx="4" ry="5.5"/><ellipse cx="25" cy="9" rx="4" ry="5.5"/><ellipse cx="32.5" cy="15" rx="4" ry="5.2" transform="rotate(20 32.5 15)"/></svg>`;
export const kit = n => `/static/kit/${n}.webp`;
export const kitImg = n => `<img src="${kit(n)}" alt="" draggable="false">`;
// Team colours: blue for the viewer, red for the opponent (the genre's own-versus-enemy convention).
const OWN = {
  A: { rim: 'rim_b', enamel: 'rim_b_enamel', gem: 'gem_b', token: 'token_b', ribbon: 'ribbon_b', den: 'den_a' },
  B: { rim: 'rim_a', enamel: 'rim_red_enamel', gem: 'gem_red', token: 'token_red', ribbon: 'ribbon_red', den: 'den_b' },
};
export const teamGem = p => OWN[p].gem;
// Crossroads span the plateau; each den stands off its edge, with its food silo and food plaque below it.
const HQX = { A: 150, B: 1522 }, DEN_Y = 290;
// Design-lab variant (static/lab, #/lab/<name>?v=<id>): '' is the current design.
let VAR = '', THIN = false, PORTRAIT = 136, curCr = null;
const THIN_RIM = { '1a': { A: 'rim_thin_blue', B: 'rim_thin_red' }, '1b': { A: 'rim_thin_iron', B: 'rim_thin_iron' }, '1c': { A: 'rim_thin_blue', B: 'rim_thin_red' } };
// Keywords that change what can be done to a unit already on the board (Flight and Apex Predator only matter while placing).
const BOARD_KW = { Immovable: 'kw_immovable', Stealth: 'kw_stealth', Fragile: 'kw_fragile' };

// A round crop of the card art, `D` stage pixels across; the name stands in for missing art.
export function portrait(id, D, name) {
  if (!hasArt(id)) return `<div class="portrait noart"><span>${name}</span></div>`;
  const [x, y, d] = CROP[id], w = D / d, h = w * 1.5;
  return `<div class="portrait" style="background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${D / 2 - x * w}px ${D / 2 - y * h}px"></div>`;
}

export function renderBoard(el, M, g, cards, ui) {
  VAR = document.documentElement.dataset.v || ''; THIN = ['1a', '1b', '1c'].includes(VAR); PORTRAIT = THIN ? 140 : 136;
  if (VAR[0] === 'f' || VAR[0] === 's') return renderField(el, M, g, cards, ui);
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
    const st = regionState(reg), [c, r] = reg.c, x = (X(c) + X(c + 1)) / 2, y = (Y(r) + Y(r + 1)) / 2;
    if (VAR === '2a' && st) s += put(`token jewel lift${st.full ? '' : ' part'}`, x, y, kitImg(OWN[st.owner].gem) + `<span class="num">+${reg.food}</span>`);
    else if (VAR === '2c' && st && st.full) s += put('flag lift', x, y - 24, kitImg(st.owner === 'A' ? 'flag_blue' : 'flag_red') + `<span class="num">+${reg.food}</span>`);
    else s += put(`token lift${st ? (st.full ? '' : ' part') : ' idle'}`, x, y,
      kitImg(st && VAR !== '2c' ? OWN[st.owner].token : 'token') + `<span class="num">+${reg.food}</span>`);
  }

  // Dens (headquarters), each with its food silo filling toward the win threshold; the paler band is next turn's income.
  for (const p of ['A', 'B']) {
    const x = HQX[p], food = g.food[p], inc = g.income[p], win = g.winFood;
    const f1 = Math.min(1, food / win), f2 = Math.min(1, (food + inc) / win), target = p === 'B' && ui.hqRing;
    s += put(`den lift${target ? ' tgt legal' : ''}`, x, DEN_Y, kitImg(OWN[p].den), '', target ? 'data-hq="1"' : '');
    if (VAR === '2b') {
      // One race gauge per player across the top: food toward the win threshold, next turn's income paler.
      const gx = p === 'A' ? 640 : 1032;
      s += put(`gauge ${p} lift`, gx, 44, `<div class="ch"><div class="inc" style="width:${f2 * 100}%"></div><div class="fill" style="width:${f1 * 100}%"></div></div>` + kitImg('gauge') +
        `<span class="num">${food}<small> / ${win} · +${inc}</small></span>`);
    } else if (VAR === '2c') {
      s += put('plaque food big lift', x, 520, kitImg('plaque') + `<span class="num">${food}<small>+${inc} / turn</small></span>`);
    } else {
      s += put('silo lift', x, 520, `<div class="win"><div class="inc" style="height:${f2 * 100}%"></div><div class="fill" style="height:${f1 * 100}%"></div></div>` + kitImg('silo'));
      s += put('plaque food lift', x, 655, kitImg('plaque') + `<span class="num">${food}<small>+${inc}${VAR === '2a' ? ' / turn' : ''}</small></span>`);
    }
  }

  // Crossroads: the hit area for everything placed on it.
  for (let c = M.cols; c >= 1; c--) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), stack = g.board[cr] || [];
    let h = '';
    if (ui.preview && ui.preview.cr === cr) h = unit({ id: ui.preview.id, owner: 'A', str: ui.preview.str }, stack.slice().reverse(), true);
    else if (stack.length) h = unit(stack[stack.length - 1], stack.slice(0, -1).reverse(), false);
    const cls = ['cr', rings.has(cr) ? 'tgt legal' : '', stack.length ? 'occ' : '', recent.has(cr) ? 'recent' : ''].join(' ');
    s += put(cls, X(c), Y(r), h, `z-index:${M.rows - r + 1}`, `data-cr="${cr}"`);   // upper rows on top, so their names aren't covered
  }

  // `under`: the buried units, top first, each peeking out below as a darker rim in its owner's metal.
  function unit(u, under, ghost) {
    const card = cards[u.id], base = card.str === '*' ? null : card.str;
    const delta = base !== null && u.str !== base ? (u.str > base ? ' up' : ' down') : '';
    const peek = under.slice(0, 3).map((b, i) => `<div class="buried" style="transform:translate(${(i + 1) * 8}px,${(i + 1) * 9}px);z-index:${-i - 1}">${kitImg(THIN ? THIN_RIM[VAR][b.owner] : OWN[b.owner].rim)}</div>`).join('');
    const kws = (card.kw || []).filter(k => BOARD_KW[k]).map(k => `<img src="${kit(BOARD_KW[k])}" alt="" title="${k}" draggable="false">`).join('');
    const rim = THIN ? THIN_RIM[VAR][u.owner] : ui.enamel ? OWN[u.owner].enamel : OWN[u.owner].rim;
    return `<div class="unit lift ${u.owner}${ghost ? ' ghost' : ''}">${peek}${portrait(u.id, PORTRAIT, card.name)}<img class="rim" src="${kit(rim)}" alt="" draggable="false">` +
      (VAR === '1c' ? `<div class="nameplate">${kitImg('nameplate')}<span>${card.name}</span></div>` : `<div class="ribbon">${kitImg(OWN[u.owner].ribbon)}<span class="num">${card.name}</span></div>`) + (kws ? `<div class="kws">${kws}</div>` : '') +
      `<div class="gem">${kitImg(OWN[u.owner].gem)}<span class="num${delta}">${u.str}</span></div>` +
      (u.timer && !ghost ? `<div class="timer">${kitImg('token')}<span class="num">${u.timer}</span></div>` : '') +
      (under.length && !ghost ? `<div class="under num">+${under.length}</div>` : '') + '</div>';
  }

  el.innerHTML = s;
}

// ---------------------------------------------------------------- field mode (lab variants fA/fB/fC)
// A quiet painted field (kit/field_<X>.webp) with engraved sockets, shallow grooves and quiet region numbers;
// each player's food lives in a banner at the screen edge, which is also their headquarters.
function renderField(el, M, g, cards, ui) {
  // Leaving pieces: keep the old DOM of every crossroad whose top changed, to fade it out after the redraw.
  const A = ui.anim, topIid = (b, cr) => ((b[cr] || []).slice(-1)[0] || {}).iid;
  const leaving = A ? [...el.querySelectorAll('.cr')].filter(n => n.querySelector('.unit') && topIid(A.board, n.dataset.cr) !== topIid(g.board, n.dataset.cr) && topIid(A.board, n.dataset.cr) !== undefined)
    .map(n => { const c = n.cloneNode(true); c.classList.add('leaving'); c.removeAttribute('data-cr'); return c; }) : [];
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
  // fX: a quiet field with engraved marks. sX: a painted map (kit/sav_X) that already carries crossroads, paths, dens and markers.
  const MAP_ = VAR[0] === 's';
  const X = MAP_ ? c => 390 + (c - 1) * 232.5 : c => 335 + (c - 1) * 1002 / (M.cols - 1);
  const Y = MAP_ ? r => 185 + (r - 1) * 180 : r => 200 + (r - 1) * 200, EDGE = MAP_ ? { A: 240, B: 1432 } : { A: 222, B: 1450 };
  const conn = { A: connected('A'), B: connected('B') }, rings = new Set(ui.rings || []), recent = new Set(ui.recent || []);
  const put = (cls, x, y, html = '', style = '', attrs = '') => `<div class="sp ${cls}" style="left:${x}px;top:${y}px;${style}" ${attrs}>${html}</div>`;
  const groove = (x1, y1, x2, y2, lit) => { const len = Math.hypot(x2 - x1, y2 - y1), deg = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
    return `<div class="groove${lit ? ' ' + lit : ''}" style="left:${x1}px;top:${y1}px;width:${len}px;transform:rotate(${deg}deg)"></div>`; };
  const litOf = (a, b) => { const o = owner(a); return o && o === owner(b) && conn[o].has(a) && conn[o].has(b) ? o : ''; };

  let s = '';
  for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) {
    if (c < M.cols) s += groove(X(c), Y(r), X(c + 1), Y(r), litOf(key(c, r), key(c + 1, r)));
    if (r < M.rows) s += groove(X(c), Y(r), X(c), Y(r + 1), litOf(key(c, r), key(c, r + 1)));
  }
  for (let r = 1; r <= M.rows; r++) for (const p of ['A', 'B']) {
    const c = p === 'A' ? 1 : M.cols;
    s += groove(EDGE[p], Y(r), X(c), Y(r), owner(key(c, r)) === p ? p : '');
  }
  let fx = '';
  if (!MAP_) for (let r = 1; r <= M.rows; r++) for (let c = 1; c <= M.cols; c++) s += put('eng', X(c), Y(r));
  for (const reg of M.regions) {
    const st = regionState(reg), [c, r] = reg.c;
    // On map D the painted stones sit a little off the grid; their measured centres.
    const at = VAR === 'sD' ? [[492, 725, 960, 1194][c - 1], [268, 458][r - 1]] : [(X(c) + X(c + 1)) / 2, (Y(r) + Y(r + 1)) / 2];
    // A held region recolours its painted stone: a disc the stone's size, blended in "color" mode over the painting.
    const MARK = document.documentElement.dataset.f === 'm';
    if (VAR === 'sD' && st && st.full) s += MARK ? put(`pawmark ${st.owner}`, at[0], at[1], PAW) : put(`stonetint ${st.owner}`, at[0], at[1]);
    s += put(`payout${st && st.full ? ' full ' + st.owner : ''}`, at[0], at[1], `<span class="plus">+</span>${reg.food}`);
  }
  // Side banners: the headquarters. Food toward the win threshold, next turn's income paler above it.
  if (MAP_) for (const p of ['A', 'B']) {
    // The den is painted; its food total is written on the painted slab below it.
    const x = p === 'A' ? 150 : 1522, target = p === 'B' && ui.hqRing;
    s += put(`denhit ${p}${target ? ' tgt legal' : ''}`, x, 355, '', '', target ? 'data-hq="1"' : '');
    if (document.documentElement.dataset.d === '1') s += put('denflag lift', p === 'A' ? 222 : 1450, 238, kitImg(p === 'A' ? 'flag_blue' : 'flag_red'), p === 'B' ? 'transform:translate(-50%,-50%) scaleX(-1)' : '');
    const F = document.documentElement.dataset.f || '';
    if (!F) { s += put(`slab ${p}`, x, 570, `<b class="num">${g.food[p]}</b><span class="num">+${g.income[p]} / turn</span>`); continue; }
    // Food sketches (lab): the painted slab is covered with grass cloned from just below it.
    const sx = p === 'A' ? 12 : 1432;
    if (F !== 'p' && F !== 'o') s += `<div class="grasspatch" style="left:${sx}px;top:486px;background-position:${-sx}px ${-(486 + 96)}px"></div>`;
    const food = g.food[p], inc = g.income[p], win = g.winFood, f1 = Math.min(1, food / win), f2 = Math.min(1, (food + inc) / win);
    const mouth = p === 'A' ? 252 : 1420;
    if (F === 'a') {
      // Ten stones from the grass up to the den mouth, each 10 food; filled from the far end toward the den.
      let st = '';
      for (let i = 0; i < 10; i++) {
        const lo = i / 10, fill = Math.max(0, Math.min(1, (f1 - lo) * 10)), ghost = Math.max(0, Math.min(1, (f2 - lo) * 10)) - fill;
        st += `<i style="top:${(9 - i) * 25}px;--f:${fill};--g:${ghost}"></i>`;
      }
      s += put(`ftrack ${p}`, p === 'A' ? 232 : 1440, 560, st);
      s += put(`carved ${p}`, p === 'A' ? 136 : 1536, 560, `${food}`);
    } else if (F === 'b') {
      s += put(`fgauge ${p}`, p === 'A' ? 110 : 1562, 330, `<div class="inc" style="height:${f2 * 100}%"></div><div class="fill" style="height:${f1 * 100}%"></div>`);
      s += put(`carved ${p}`, p === 'A' ? 136 : 1536, 560, `${food}`);
    } else if (F === 'p') {
      // Painted trough (kit/trough, fruit_ripe, fruit_green): the fruit strips are clipped to the food, inside the hollow.
      s += put(`ptrough ${p}`, x, 560, `<div class="hollow"><div class="inc" style="width:${f2 * 100}%"></div><div class="fill" style="width:${f1 * 100}%"></div></div>` + kitImg('trough'));
      s += put(`carved small ${p}`, x, 612, `${food}<small> / ${win}</small>`);
    } else if (F === 'o') {
      // One fruit is one food: whole fruit heaped three deep, filling column by column toward 100; next turn's income unripe.
      let t = '';
      // Each slot always holds the same kind of fruit (a fixed hash of its index), so the mix doesn't reshuffle as food changes.
      const kind = i => ((i * 2654435761) >>> 0) % 9, jit = (i, k) => (((i * 40503 + k * 9973) >>> 0) % 100) / 100;
      const was = ui.anim ? Math.min(ui.anim.food[p], food) : food, gained = food - was;
      for (let i = 0; i < Math.min(win, food + inc); i++)
        t += `<i class="${i < food ? 'r' : 'g'}${i >= was && i < food ? ' new' : ''}" style="${i >= was && i < food ? `animation-delay:${.55 + (i - was) / Math.max(1, gained) * .5}s;` : ''}left:${Math.floor(i / 3) * 7.4 + jit(i, 1) * 2 - 1}px;top:${(2 - i % 3) * 7 + (Math.floor(i / 3) % 2) * 2 + jit(i, 2) * 2 - 1}px;background-position:${kind(i) * 12.5}% 0;transform:rotate(${jit(i, 3) * 60 - 30}deg)"></i>`;
      const incTag = inc > 0 ? `<b class="incnum num" style="left:${Math.min(Math.floor(Math.min(win, food + inc) / 3) * 7.4 + 14, 236)}px">+${inc}</b>` : '';
      s += put(`otrough ${p}`, p === 'A' ? 160 : 1514, 560, `<div class="hollow">${t}${incTag}</div>` + kitImg('trough'));
      // Fruit flies from each held stone to where the new fruit lands in the trough.
      if (gained > 0) {
        const tx = (p === 'A' ? 160 : 1514) - 145 + 10 + Math.floor(was / 3) * 7.4, ty = 560;
        const srcs = M.regions.filter(reg => { const st = regionState(reg); return st && st.full && st.owner === p; })
          .map(reg => [[492, 725, 960, 1194][reg.c[0] - 1], [268, 458][reg.c[1] - 1]]);
        srcs.forEach(([sx, sy], k) => { for (let j = 0; j < 3; j++)
          fx += `<i class="flyfruit" style="left:${sx}px;top:${sy}px;--dx:${tx - sx}px;--dy:${ty - sy}px;animation-delay:${k * .08 + j * .06}s;background-position:${((k * 3 + j) * 4 % 9) * 12.5}% 0"></i>`; });
      }
      s += put(`carved small ${p}`, p === 'A' ? 160 : 1514, 616, `${food}<small> / ${win}</small>`);
    } else if (F === 't') {
      // A carved trough filled with fruit toward the win at its end; next turn's income as unripe green fruit.
      s += put(`trough ${p}`, x, 560, `<div class="in"><div class="inc" style="width:${f2 * 100}%"></div><div class="fill" style="width:${f1 * 100}%"></div></div><span class="cap"></span>`);
      s += put(`carved small ${p}`, x, 612, `${food}<small> / ${win}</small>`);
    } else if (F === 'r') {
      // A row of ten hollows leading up to the den mouth: ripe fruit = food held (the last one grown to its fraction),
      // green fruit = next turn's income. The den is the finish line.
      let t = '';
      const ripe = food / 10, next = Math.min(10, (food + inc) / 10);
      for (let i = 0; i < 10; i++) {
        const r = Math.max(0, Math.min(1, ripe - i)), u = Math.max(0, Math.min(1, next - i));
        const cls = r >= 1 ? 'ripe' : r > 0 ? 'ripe part' : u > 0 ? 'green' : '';
        const sz = r > 0 && r < 1 ? .45 + .55 * r : u > 0 && u < 1 ? .45 + .55 * u : 1;
        t += `<i class="${cls}" style="top:${(9 - i) * 25}px;--s:${sz}"><b></b></i>`;
      }
      s += put(`fruitrow ${p}`, p === 'A' ? 196 : 1476, 566, t);
      s += put(`carved small vert ${p}`, p === 'A' ? 110 : 1562, 600, `${food}<small>/ ${win}</small>`);
    } else if (F === 'k') {
      // The den's food cache: ten hollows at the den mouth, one portion of food per 10; next turn's income as pale portions.
      let t = '';
      for (let i = 0; i < 10; i++) {
        const on = f1 >= (i + 1) / 10 - 1e-9, soon = !on && f2 >= (i + 1) / 10 - 1e-9;
        t += `<i class="${on ? 'on' : soon ? 'soon' : ''}" style="left:${(i % 5) * 34 + (Math.floor(i / 5) ? 17 : 0)}px;top:${Math.floor(i / 5) * 30}px"><b></b></i>`;
      }
      s += put(`cache ${p}`, p === 'A' ? 150 : 1522, 548, t);
      s += put(`carved small ${p}`, p === 'A' ? 150 : 1522, 630, `${food}<small> / ${win}</small>`);
    } else if (F === 'm') {
      // Tally on the den rock: ten paw prints in the owner's paint, one per 10 food.
      let t = '';
      for (let i = 0; i < 10; i++) { const on = f1 >= (i + 1) / 10 - 1e-9;
        t += `<i class="${on ? 'on' : ''}" style="left:${(i % 5) * 30}px;top:${Math.floor(i / 5) * 34 + (i % 2) * 5}px">${PAW}</i>`; }
      s += put(`tally ${p}`, p === 'A' ? 150 : 1522, 560, t);
      s += put(`carved small ${p}`, p === 'A' ? 150 : 1522, 640, `${food}<small> / ${win}</small>`);
    } else if (F === 'c') {
      const n = Math.round(f1 * 14);
      let pile = '';
      for (let i = 0; i < n; i++) { const row = i < 5 ? 0 : i < 9 ? 1 : i < 12 ? 2 : 3, k = [i, i - 5, i - 9, i - 12][row], w = [5, 4, 3, 2][row];
        pile += `<i class="${['m', 'f', 'm', 'f', 'g'][i % 5]}" style="left:${(k - (w - 1) / 2) * 22}px;bottom:${row * 16}px"></i>`; }
      s += put(`fpile ${p}`, p === 'A' ? 262 : 1410, 408, pile);
      s += put(`carved ${p}`, p === 'A' ? 136 : 1536, 560, `${food}<small> / ${win}</small>`);
    }
  }
  if (!MAP_) for (const p of ['A', 'B']) {
    const food = g.food[p], inc = g.income[p], win = g.winFood, f1 = Math.min(1, food / win), f2 = Math.min(1, (food + inc) / win);
    const target = p === 'B' && ui.hqRing, x = p === 'A' ? 108 : 1564;
    s += put(`hqbar ${p}${target ? ' tgt legal' : ''}`, x, 380,
      `<div class="meter"><div class="inc" style="height:${f2 * 100}%"></div><div class="fill" style="height:${f1 * 100}%"></div><i style="bottom:100%"></i></div>` +
      `<div class="food num">${food}</div><div class="rate num">+${inc}<small> / turn</small></div><div class="goal">${win} to win</div>`, '', target ? 'data-hq="1"' : '');
  }
  for (let c = M.cols; c >= 1; c--) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), stack = g.board[cr] || [];
    let h = '';
    curCr = cr;
    if (ui.preview && ui.preview.cr === cr) h = unit({ id: ui.preview.id, owner: 'A', str: ui.preview.str }, stack.slice().reverse(), true);
    else if (stack.length) h = unit(stack[stack.length - 1], stack.slice(0, -1).reverse(), false);
    const dropped = ui.anim && stack.length && ((ui.anim.board[cr] || []).slice(-1)[0] || {}).iid !== stack[stack.length - 1].iid;
    const SM = document.documentElement.dataset.m === 'S' && VAR === 'sD';
    if (SM && stack.length) { const top = stack[stack.length - 1], [gx, gy, gr] = CLEAR[cr];
      const box = `left:${gx - gr - 30}px;top:${gy - gr - 30}px;width:${2 * gr + 60}px;height:${2 * gr + 60}px;-webkit-mask-position:${-(gx - gr - 30)}px ${-(gy - gr - 30)}px;mask-position:${-(gx - gr - 30)}px ${-(gy - gr - 30)}px`;
      s += `<div class="ringtint band ${top.owner}" style="${box}"></div><div class="ringtint ${top.owner}" style="${box}"></div>`; }
    const cls = ['cr', rings.has(cr) ? 'tgt legal' : '', stack.length ? 'occ' : '', recent.has(cr) ? 'recent' : '', dropped ? 'drop' : ''].join(' ');
    const at = SM ? CLEAR[cr] : [X(c), Y(r)];
    s += put(cls, at[0], at[1], h, `z-index:${M.rows - r + 1}`, `data-cr="${cr}"`);
  }
  function unit(u, under, ghost) {
    const MED = document.documentElement.dataset.m;
    if (MED === 'S' && VAR === 'sD') return stoneUnit(u, under, ghost, curCr);
    if (MED) return medUnit(u, under, ghost, MED);
    const card = cards[u.id], base = card.str === '*' ? null : card.str;
    const delta = base !== null && u.str !== base ? (u.str > base ? ' up' : ' down') : '';
    const peek = under.slice(0, 3).map((b, i) => `<div class="buried" style="transform:translate(${(i + 1) * 8}px,${(i + 1) * 9}px);z-index:${-i - 1}">${kitImg(OWN[b.owner].enamel)}</div>`).join('');
    const kws = (card.kw || []).filter(k => BOARD_KW[k]).map(k => `<img src="${kit(BOARD_KW[k])}" alt="" title="${k}" draggable="false">`).join('');
    return `<div class="unit lift ${u.owner}${ghost ? ' ghost' : ''}">${peek}${portrait(u.id, 136, card.name)}<img class="rim" src="${kit(OWN[u.owner].enamel)}" alt="" draggable="false">` +
      `<div class="ribbon">${kitImg(OWN[u.owner].ribbon)}<span class="num">${card.name}</span></div>` + (kws ? `<div class="kws">${kws}</div>` : '') +
      `<div class="gem">${kitImg(OWN[u.owner].gem)}<span class="num${delta}">${u.str}</span></div>` +
      (u.timer && !ghost ? `<div class="timer">${kitImg('token')}<span class="num">${u.timer}</span></div>` : '') +
      (under.length && !ghost ? `<div class="under">${kitImg(u.owner === 'A' ? 'token_blue' : 'token_red')}<span class="num">${under.length}</span></div>` : '') + '</div>';
  }
  // Medallion in the card's language (lab m=A|B|C, kit/med<X>_*): matte brass ring with a team-enamel band, the card's
  // square strength plate, a parchment name tab, a small brass tab for the buried count. Geometry measured on each sprite.
  // Stone mode: the clearing's own stones carry the team colour (.ringtint); the portrait fills the clearing;
  // strength on a small team-colour plate; no name on the board (hover shows the card).
  function stoneUnit(u, under, ghost, cr) {
    const card = cards[u.id], base = card.str === '*' ? null : card.str, D = cr && CLEAR[cr] ? 2 * CLEAR[cr][2] + 8 : 144;
    const delta = base !== null && u.str !== base ? (u.str > base ? ' up' : ' down') : '';
    const kws = (card.kw || []).filter(k => BOARD_KW[k]).map(k => `<img src="${kit(BOARD_KW[k])}" alt="" title="${k}" draggable="false">`).join('');
    const side = u.owner === 'A' ? 'a' : 'b';
    // Buried units peek out behind the portrait as discs in their owners' colours: how many, and whose.
    const peek = ghost ? '' : under.slice(0, 4).map((b, i) => `<i class="disc ${b.owner}" style="transform:translate(${(i + 1) * 5}px,${(i + 1) * 6}px);z-index:${-i - 1}"></i>`).join('');
    return `<div class="unit stone ${u.owner}${ghost ? ' ghost' : ''}" style="--pp:${D}px">${peek}${portrait(u.id, D, card.name)}` +
      `<div class="splate">${kitImg('plate_' + side)}<span class="${delta.trim()}">${u.str}</span></div>` +
      (kws ? `<div class="kws">${kws}</div>` : '') +
      (u.timer && !ghost ? `<div class="timer">${kitImg('token')}<span class="num">${u.timer}</span></div>` : '') + '</div>';
  }
  function medUnit(u, under, ghost, M) {
    // Team-colour kits (D/E/F): per-side sprites med<X>_{a|b}, tab_, num_, ring_; geometry per side.
    const side = u.owner === 'A' ? 'a' : 'b', G = MEDG[M][side], sc = 172 / (2 * G.R), P = 2 * G.hr * sc + 4, C = 82;
    const place = (g, name) => `<img class="mring" src="${kit(`med${M}_${name}`)}" alt="" draggable="false" style="width:${g.W * sc}px;left:${C - g.hx * sc}px;top:${C - g.hy * sc}px">`;
    const card = cards[u.id], base = card.str === '*' ? null : card.str;
    const delta = base !== null && u.str !== base ? (u.str > base ? ' up' : ' down') : '';
    const peek = under.slice(0, 3).map((b, i) => { const s2 = b.owner === 'A' ? 'a' : 'b';
      return `<div class="buried" style="transform:translate(${(i + 1) * 7}px,${(i + 1) * 8}px);z-index:${-i - 1}">${place(MEDG[M][s2], 'ring_' + s2)}</div>`; }).join('');
    const kws = (card.kw || []).filter(k => BOARD_KW[k]).map(k => `<img src="${kit(BOARD_KW[k])}" alt="" title="${k}" draggable="false">`).join('');
    const [px, py, pw, ph] = [(G.plate[0] - G.hx) * sc + C, (G.plate[1] - G.hy) * sc + C, G.plate[2] * sc, G.plate[3] * sc];
    const R = G.R * sc;
    return `<div class="unit med lift ${u.owner}${ghost ? ' ghost' : ''}" style="--pp:${P}px">${peek}${portrait(u.id, P, card.name)}${place(G, side)}` +
      `<div class="mstr${delta}" style="left:${px - pw / 2}px;top:${py - ph / 2 - 1.3}px;width:${pw}px;height:${ph}px">${u.str}</div>` +   // -1.3: measured optical centre
      `<div class="mname" style="top:${C + R - 24}px">${kitImg(`med${M}_tab_${side}`)}<span>${card.name}</span></div>` +
      (under.length && !ghost ? `<div class="mnum" style="left:${C + R * .72 - 14}px;top:${C + R * .6 - 14}px">${kitImg(`med${M}_num_${side}`)}<span>${under.length}</span></div>` : '') +
      (kws ? `<div class="kws">${kws}</div>` : '') +
      (u.timer && !ghost ? `<div class="timer">${kitImg('token')}<span class="num">${u.timer}</span></div>` : '') + '</div>';
  }
  el.innerHTML = s + fx;
  for (const n of leaving) el.appendChild(n);
  setTimeout(() => { for (const n of leaving) n.remove(); for (const n of el.querySelectorAll('.flyfruit')) n.remove(); }, 1400);
}
