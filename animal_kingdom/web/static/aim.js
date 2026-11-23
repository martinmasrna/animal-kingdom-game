// The target arrow (Martin, 2026-11-23, after Hearthstone's; design/screen/square/arrow, the "blocks" form): who acts on
// whom. A curve lifted as a thrown thing is, from the source to the tip, of separate blocks that grow toward a triangular
// head, dark outline, drop shadow, in the acting team's colour (blue yours, red theirs). One SVG layer on the stage, over
// the board and its pieces, under the panels (mana.css .aim). Points are stage px; app.js says where the pieces stand.
import { STAGE, tokenWidth } from './board.js';

const COL = { A: '#4f9be8', B: '#e2473a' }, DARK = '#14100c';
const N = 60;   // points along the curve

// the curve from a to b, bowed as a thrown thing flies: its middle pushed off the line by `bow` of its length (at least
// `min` px, so the next tile's arrow still arcs), on the line's upper side (a straight up or down one bows to its right):
// N + 1 points, each with the distance run to it
function curve(a, b, bow, min) {
  const dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || 1;
  let nx = dy / d, ny = -dx / d; if (ny > 0 || (Math.abs(ny) < .2 && nx < 0)) { nx = -nx; ny = -ny; }
  const h = Math.max(bow * d, min), m = [(a[0] + b[0]) / 2 + nx * h, (a[1] + b[1]) / 2 + ny * h], pts = []; let run = 0;
  for (let i = 0; i <= N; i++) { const t = i / N, u = 1 - t, p = [u * u * a[0] + 2 * u * t * m[0] + t * t * b[0], u * u * a[1] + 2 * u * t * m[1] + t * t * b[1]];
    if (i) run += Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]); pts.push([p[0], p[1], run]); }
  return pts;
}
// the point at distance l along the curve, with the direction it runs there
function at(pts, l) {
  l = Math.max(0, Math.min(l, pts[N][2])); let i = 1; while (i < N && pts[i][2] < l) i++;
  const p = pts[i - 1], q = pts[i], k = (l - p[2]) / (q[2] - p[2] || 1), dx = q[0] - p[0], dy = q[1] - p[1], n = Math.hypot(dx, dy) || 1;
  return { x: p[0] + dx * k, y: p[1] + dy * k, tx: dx / n, ty: dy / n };
}
const off = (p, along, side) => `${(p.x + p.tx * along - p.ty * side).toFixed(1)},${(p.y + p.ty * along + p.tx * side).toFixed(1)}`;

// The arrow's shapes from a to b, `s` its scale (1 on the wide stage's tiles); '' when the two are too close for one.
// `grow`: ms since it appeared, while its blocks still come out of the source one after another (mana.css .aim .g).
export function arrowShapes(a, b, s = 1, grow = null) {
  const pts = curve(a, b, .34, 42 * s), L = pts[N][2];
  // a short arrow (the next tile: every target there is today) is drawn smaller, so it still has blocks before its head
  const k = s * Math.max(.85, Math.min(1, L / (200 * s))), hl = 38 * k, hw = 28 * k;
  if (L < hl + 30 * k) return '';
  const start = 10 * k, end = L - hl, n = Math.max(2, Math.round((end - start) / (34 * k))), step = (end - start) / n;
  const delay = i => grow == null ? '' : ` class="g" style="animation-delay:${Math.round(i * 22 - grow)}ms"`;
  let body = '';
  for (let i = 0; i < n; i++) {
    const p = at(pts, start + i * step + step * .08), q = at(pts, start + i * step + step * .78);
    const w = (7 + 11 * (i / n)) * k, w2 = (7 + 11 * ((i + .7) / n)) * k;
    body += `<polygon${delay(i)} points="${off(p, 0, w)} ${off(q, 0, w2)} ${off(q, 0, -w2)} ${off(p, 0, -w)}"/>`;
  }
  const h = at(pts, L - hl);
  body += `<polygon${delay(n)} points="${off(h, 0, hw)} ${off(h, hl, 0)} ${off(h, 0, -hw)} ${off(h, hl * .22, 0)}"/>`;
  return body;
}

// The layer: drawn into the stage once, sized to it (the upright stage is another size).
function layer() {
  let el = document.getElementById('aim');
  if (!el) { const st = document.getElementById('stage'); if (!st) return null;
    el = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); el.id = 'aim'; el.setAttribute('class', 'aim');
    const pl = document.getElementById('mplane'); st.insertBefore(el, pl ? pl.nextSibling : null); }
  el.setAttribute('viewBox', `0 0 ${STAGE.w} ${STAGE.h}`); el.setAttribute('width', STAGE.w); el.setAttribute('height', STAGE.h);
  return el;
}

// Draw the arrow from `from` to `to` (stage px) in `side`'s colour; `grow`: ms since it first showed, null once grown (or
// with reduced motion). null `to` clears it. Whether an arrow is drawn (none between two points too close).
export function drawAim(from, to, side, grow = null) {
  const el = layer(); if (!el) return false;
  el.classList.remove('out'); clearTimeout(drawAim.t);
  if (!from || !to) { el.innerHTML = ''; return false; }
  const body = arrowShapes(from, to, tokenWidth() / 144, grow);
  el.innerHTML = body ? `<g fill="${COL[side] || COL.A}" stroke="${DARK}" stroke-width="${(3 * tokenWidth() / 144).toFixed(2)}" stroke-linejoin="round">${body}</g>` : '';
  el.dataset.side = side; el.dataset.from = from.map(Math.round).join(','); el.dataset.to = to.map(Math.round).join(',');
  return !!body;
}

// Take it away: at once, or fading (`fade`, the opponent's arrow as its effect shows).
export function clearAim(fade = false) {
  const el = document.getElementById('aim'); if (!el || !el.innerHTML) return;
  delete el.dataset.from; delete el.dataset.to;
  if (!fade) { el.innerHTML = ''; return; }
  el.classList.add('out'); clearTimeout(drawAim.t); drawAim.t = setTimeout(() => { el.innerHTML = ''; el.classList.remove('out'); }, 180);
}
export const aimShown = () => { const el = document.getElementById('aim'); return !!(el && el.innerHTML && !el.classList.contains('out')); };
