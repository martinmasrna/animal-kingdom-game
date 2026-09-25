// Board renderer (from the design mockups' table.js, horizontal and flat only).
// Draws in viewer space: the viewer is always 'A' (orange, HQ on the left), the opponent 'B'.
// `g` is a viewer-space game: { board: {cr: [{id, owner, str, timer}]}, food, income, winFood },
// `ui` carries what is interactive: { rings: [cr], hqRing: bool, preview: {cr, id, str} }.
const COL = { A: 'var(--you)', B: 'var(--them)' }, DEEP = { A: 'var(--you-deep)', B: 'var(--them-deep)' };
const RGB = { A: 'var(--you-rgb)', B: 'var(--them-rgb)' };
const key = (c, r) => `${c},${r}`;

export function renderBoard(el, M, g, cards, ui, o) {
  const top = cr => (g.board[cr] || []).slice(-1)[0], owner = cr => (top(cr) || {}).owner;
  const nb = cr => { const [c, r] = cr.split(',').map(Number), out = []; if (c > 1) out.push(key(c - 1, r)); if (c < M.cols) out.push(key(c + 1, r)); if (r > 1) out.push(key(c, r - 1)); if (r < M.rows) out.push(key(c, r + 1)); return out; };
  function connected(p) {
    const f = p === 'A' ? 1 : M.cols, seen = new Set(), q = [];
    for (let r = 1; r <= M.rows; r++) if (owner(key(f, r)) === p) { seen.add(key(f, r)); q.push(key(f, r)); }
    while (q.length) for (const n of nb(q.shift())) if (!seen.has(n) && owner(n) === p) { seen.add(n); q.push(n); }
    return seen;
  }
  function regionState(reg) {
    const [c, r] = reg.c, cs = [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)];
    for (const p of ['A', 'B']) { const n = cs.filter(x => owner(x) === p).length; if (n === 4) return { owner: p, full: true }; if (n === 3 && cs.every(x => owner(x) === p || !top(x))) return { owner: p, full: false }; }
    return null;
  }

  const R = o.tokenR || 30, Wf = o.wide || 460, pad = 70, hqT = 64, hqL = Wf - 2 * pad + 64, gap = o.gap || 56, step = o.step || 150;
  const Hf = 2 * (hqT + gap) + step * (M.cols - 1), cstep = (Wf - 2 * pad) / (M.rows - 1), cx = Wf / 2;
  const flat = (c, r) => [pad + (r - 1) * cstep, Hf - hqT - gap - (c - 1) * step];
  const proj = ([x, y]) => [Hf - y, x, 1];   // a quarter turn: your HQ on the left
  const P = (c, r) => proj(flat(c, r)), pos = cr => { const [c, r] = cr.split(',').map(Number); return P(c, r); };
  const poly = pts => pts.map(p => proj(p)).map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const conn = { A: connected('A'), B: connected('B') };
  const hqRect = { A: [cx - hqL / 2, Hf - hqT, hqL, hqT], B: [cx - hqL / 2, 0, hqL, hqT] };
  const rings = new Set(ui.rings || []);

  let s = '';
  // Regions.
  const ins = R + 12, lab = 20;
  for (const reg of M.regions) {
    const [c, r] = reg.c, a = flat(c, r), b = flat(c + 1, r + 1);
    const x0 = Math.min(a[0], b[0]) + ins, x1 = Math.max(a[0], b[0]) - ins, y0 = Math.min(a[1], b[1]) + ins + lab, y1 = Math.max(a[1], b[1]) - ins;
    const q = poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), st = regionState(reg);
    if (st && st.full) s += `<polygon points="${q}" fill="rgba(${RGB[st.owner]},0.14)"/>`;
    else if (st) s += `<polygon points="${q}" fill="none" stroke="rgba(${RGB[st.owner]},0.5)" stroke-width="1.5" stroke-dasharray="4 5" stroke-linejoin="round"/>`;
    else s += `<polygon points="${q}" fill="rgba(255,255,255,0.025)"/>`;
    const [mx, my] = proj([(x0 + x1) / 2, (y0 + y1) / 2]);
    s += `<text x="${mx}" y="${my}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="600" font-size="24" fill="${st && st.full ? COL[st.owner] : 'var(--faint)'}">+${reg.food}</text>`;
  }

  // Paths.
  const done = new Set();
  for (let c = 1; c <= M.cols; c++) for (let r = 1; r <= M.rows; r++) for (const n of nb(key(c, r))) {
    const a = key(c, r), id = [a, n].sort().join('|'); if (done.has(id)) continue; done.add(id);
    const [x1, y1] = pos(a), [x2, y2] = pos(n), oa = owner(a), lit = oa && oa === owner(n) && conn[oa].has(a) && conn[oa].has(n);
    s += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${lit ? COL[oa] : 'var(--line)'}" stroke-width="${lit ? 3.5 : 2}" opacity="${lit ? 0.8 : 1}" stroke-linecap="round"/>`;
  }
  for (const p of ['A', 'B']) {
    const fr = p === 'A' ? 1 : M.cols, [hx, hy, hw, hh] = hqRect[p], hcx = hx + hw / 2, edgeY = p === 'A' ? hy : hy + hh;
    for (let r = 1; r <= M.rows; r++) {
      const fp = flat(fr, r), lit = owner(key(fr, r)) === p, mid = (edgeY + fp[1]) / 2;
      const [ax, ay] = proj([hcx + (fp[0] - hcx) * 0.35, edgeY]), [c1x, c1y] = proj([hcx + (fp[0] - hcx) * 0.35, mid]), [c2x, c2y] = proj([fp[0], mid]), [bx, by] = proj(fp);
      s += `<path d="M${ax},${ay} C${c1x},${c1y} ${c2x},${c2y} ${bx},${by}" fill="none" stroke="${lit ? COL[p] : 'var(--line)'}" stroke-width="${lit ? 3.5 : 2}" opacity="${lit ? 0.8 : 1}"/>`;
    }
  }

  // HQs: each is also its owner's food silo, filling toward the win threshold; the lighter band is next turn's income.
  for (const p of ['A', 'B']) {
    const [hx, hy, hw, hh] = hqRect[p], q = poly([[hx, hy], [hx + hw, hy], [hx + hw, hy + hh], [hx, hy + hh]]);
    const target = p === 'B' && ui.hqRing;
    s += `<g ${target ? 'data-hq="1" class="tgt"' : ''}>`;
    if (target) s += `<polygon points="${poly([[hx - 9, hy - 9], [hx + hw + 9, hy - 9], [hx + hw + 9, hy + hh + 9], [hx - 9, hy + hh + 9]])}" fill="none" stroke="var(--text)" stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round"/>`;
    s += `<polygon points="${q}" fill="${DEEP[p]}" stroke="${COL[p]}" stroke-width="2.5" stroke-linejoin="round"/>`;
    const food = g.food[p], inc = g.income[p], f1 = Math.min(1, food / g.winFood), f2 = Math.min(1, (food + inc) / g.winFood), i = 3;
    const band = (a, b, op) => b > a ? `<polygon points="${poly([[hx + hw - hw * b + i, hy + i], [hx + hw - hw * a - i, hy + i], [hx + hw - hw * a - i, hy + hh - i], [hx + hw - hw * b + i, hy + hh - i]])}" fill="${COL[p]}" opacity="${op}" stroke="${COL[p]}" stroke-opacity="${op}" stroke-width="4" stroke-linejoin="round"/>` : '';
    s += band(f1, f2, 0.3) + band(0, f1, 0.85);
    const [tx, ty] = proj([hx + 30, hy + hh / 2]), [ix, iy] = proj([hx + 56, hy + hh / 2]), [mx, my] = proj([hx + hw * 0.6, hy + hh / 2]);
    s += `<text x="${tx}" y="${ty}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="700" font-size="34" fill="${COL[p]}">${food}</text>`;
    s += `<text x="${ix}" y="${iy}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="600" font-size="17" fill="${COL[p]}" opacity="0.85">+${inc}</text>`;
    s += `<text x="${mx}" y="${my}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="700" font-size="15" letter-spacing="0.14em" fill="var(--token-text)" opacity="0.55" transform="rotate(-90 ${mx} ${my})">${p === 'A' ? 'YOUR HQ' : 'ENEMY HQ'}</text>`;
    s += '</g>';
  }

  // Legal targets: a ring around the crossroad.
  for (const cr of rings) {
    const [x, y] = pos(cr);
    s += `<circle cx="${x}" cy="${y}" r="${R + 9}" fill="none" stroke="var(--text)" stroke-width="2" stroke-dasharray="5 4" opacity="0.9"/>`;
  }

  // Pieces, and a hit area on every crossroad.
  for (let c = M.cols; c >= 1; c--) for (let r = 1; r <= M.rows; r++) {
    const cr = key(c, r), [x, y] = pos(cr), stack = g.board[cr] || [], tgt = rings.has(cr);
    s += `<g data-cr="${cr}" class="${tgt ? 'tgt' : ''}${stack.length ? ' occ' : ''}">`;
    s += `<circle cx="${x}" cy="${y}" r="${R + 10}" fill="transparent"/>`;
    if (ui.preview && ui.preview.cr === cr) s += piece(x, y, { id: ui.preview.id, owner: 'A', str: ui.preview.str }, stack.length, true);
    else if (!stack.length) s += `<circle cx="${x}" cy="${y}" r="5" fill="var(--line-strong)"/>`;
    else s += piece(x, y, stack[stack.length - 1], stack.length - 1, false);
    s += '</g>';
  }

  function piece(x, y, u, buried, ghost) {
    const card = cards[u.id], p = u.owner, r = R;
    let q = `<g opacity="${ghost ? 0.6 : 1}">`;
    const body = (by, f, st, w, extra) => `<circle cx="${x}" cy="${by}" r="${r}" fill="${f}" stroke="${st}" stroke-width="${w}" ${extra}/>`;
    for (let i = Math.min(buried, 2); i >= 1; i--) q += body(y + i * 5, 'var(--surface-2)', 'var(--line-strong)', 1.5, '');
    q += body(y, DEEP[p], COL[p], 2.5, ghost ? 'stroke-dasharray="4 3"' : '');
    q += `<text x="${x}" y="${y + 1}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="700" font-size="${r * 1.15}" fill="${COL[p]}">${u.str}</text>`;
    q += `<text x="${x}" y="${y + r + 16 + Math.min(buried, 2) * 5}" text-anchor="middle" font-family="var(--font-text)" font-weight="500" font-size="11" letter-spacing="0.06em" fill="var(--muted)" stroke="var(--bg)" stroke-width="4" paint-order="stroke">${card.name.toUpperCase()}</text>`;
    if (u.timer && !ghost) q += `<circle cx="${x + r * 0.78}" cy="${y - r * 0.78}" r="16" fill="${COL[p]}" stroke="var(--bg)" stroke-width="3"/><text x="${x + r * 0.78}" y="${y - r * 0.78 + 1}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="700" font-size="22" fill="var(--token-text)">${u.timer}</text>`;
    if (buried && !ghost) q += `<text x="${x + r + 4}" y="${y + r - 2}" font-family="var(--font-display)" font-weight="600" font-size="14" fill="var(--muted)" stroke="var(--bg)" stroke-width="4" paint-order="stroke">+${buried}</text>`;
    return q + '</g>';
  }

  const m = 26, b = [[-m, -m], [Wf + m, -m], [Wf + m, Hf + m], [-m, Hf + m]].map(proj);
  const x0 = Math.min(...b.map(p => p[0])), x1 = Math.max(...b.map(p => p[0])), y0 = Math.min(...b.map(p => p[1])), y1 = Math.max(...b.map(p => p[1]));
  el.innerHTML = `<svg viewBox="${x0} ${y0} ${x1 - x0} ${y1 - y0}" width="${o.fitW}" height="${o.fitH}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible">${s}</svg>`;
}
