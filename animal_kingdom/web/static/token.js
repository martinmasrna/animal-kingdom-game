// The hex board's token (Martin's design in the rim tool, design sandbox screen/hex/art/rimtool/rim.src.html, `token`): a
// pointy hexagon of painted wood in the team's colour, a window showing the rim's wood darkened, the animal as a cut-out
// standing in it with its body running behind the drawer at the bottom point, the strength in Martin's own numerals on the
// drawer. The frame, the window's ground and the seam come flattened per team (static/hex/token_{a,b}.webp, exported by the
// design sandbox's screen/kit/hextoken/export.py); this file lays the figure and the number over them.
// Every length is in the token's own space (540 x 624, the rim tool's), written as percentages of the piece's box, so the
// board can draw the token at any size.
import { FIGS } from './hex/figs.js';

export const TW = 540, TH = 624;
const CX = TW / 2, CY = TH / 2, R = TH / 2, T30 = Math.tan(Math.PI / 6);
// the rim tool's geo() at the settled rim of 80, with its drawer even (evenNum) and the window's lower edges meeting the
// drawer in a sharp V (vee)
const RIM = 80, AP = TW / 2 - RIM, WR = AP / Math.cos(Math.PI / 6);
const N = Math.max(40, 2 * (TH - CY - 2 * AP / Math.sqrt(3)) / 1.845);
const NUM_Y = TH - .96 * N, PLATE_Y = NUM_Y - .42 * N, NOTCH_Y = NUM_Y - .885 * N;
const LOW = CY + WR / 2, VDX = (AP * T30 + LOW - NOTCH_Y) / (2 * T30), VY = NOTCH_Y + VDX * T30;
const px = x => `${(x / TW * 100).toFixed(3)}%`, py = y => `${(y / TH * 100).toFixed(3)}%`;
const poly = pts => `polygon(${pts.map(([x, y]) => `${px(x)} ${py(y)}`).join(',')})`;
// the window: the inner hexagon, its bottom cut by the drawer's peak
export const WINDOW = poly([[CX, CY - WR], [CX + AP, CY - WR / 2], [CX + AP, LOW], [CX + VDX, VY], [CX, NOTCH_Y], [CX - VDX, VY], [CX - AP, LOW], [CX - AP, CY - WR / 2]]);
// where the figure may be (drawAnimal over the rim: abovePlate and notBelow): above the drawer and above the window's two
// lower edges carried outward, so a head may rise over the rim at the top and sides, never below
const FAR = 1.5 * TW, RISE = (FAR - AP) * T30;
const FIG_CLIP = poly([[CX - FAR, -TH], [CX + FAR, -TH], [CX + FAR, LOW - RISE], [CX + AP, LOW], [CX + VDX, VY], [CX, NOTCH_Y],
  [CX - VDX, VY], [CX - AP, LOW], [CX - FAR, LOW - RISE]]);
// the number: the SVG's centre on the drawer's centre, drawn 0.6 of the drawer's height tall (its viewBox is 2 x 1.2 digit
// heights, a digit half the drawer) (design sandbox screen/hex/art/numerals/README.md)
const DRAWER_H = TH - NOTCH_Y, NUM_H = .6 * DRAWER_H, NUM_W = NUM_H * 2 / 1.2, NUM_CY = TH - DRAWER_H / 2;
const NUM_BOX = `left:${px(CX - NUM_W / 2)};top:${py(NUM_CY - NUM_H / 2)};width:${px(NUM_W)};height:${py(NUM_H)}`;
// the drawer's height as a share of the piece's width: the cost's hexagon mirrors it at the top point (mana.js)
export const DRAWER_FRAC = DRAWER_H / TW;
const hex = f => `/static/hex/${f}`;

export const hasFigure = id => !!FIGS[id];
// The figure as drawAnimal places it: fit to 92% of the window's width or to its height, its bottom 6% behind the drawer.
export function figure(id) {
  const [fw, fh] = FIGS[id], winH = PLATE_Y - (CY - WR), k = Math.min(.92 * 2 * AP / fw, winH / fh), w = fw * k, h = fh * k;
  return `<div class="tkfig" style="clip-path:${FIG_CLIP}"><img src="${hex(`fig/${id}.webp`)}" alt="" draggable="false" style="left:${px(CX - w / 2)};top:${py(PLATE_Y + .06 * h - h)};width:${px(w)};height:${py(h)}"></div>`;
}
// The strength in Martin's numerals: 0 to 20 drawn as he set them; past 20 (rare) the two digits side by side.
export function numeral(n) {
  n = Math.max(0, Math.round(n));
  const img = (f, st = '') => `<img src="${hex(`num/${f}.svg`)}" alt="${f}" draggable="false"${st ? ` style="${st}"` : ''}>`;
  if (n <= 20) return `<div class="boss num tknum" style="${NUM_BOX}">${img(n)}</div>`;
  const [a, b] = String(n).slice(-2);
  return `<div class="boss num tknum two" style="${NUM_BOX}">${img(a, 'left:-17.5%;scale:.96')}${img(b, 'left:17.5%;scale:.96')}</div>`;
}
export const tokenBase = side => hex(`token_${side === 'A' ? 'a' : 'b'}.webp`);
export const armorShell = side => hex(`armor_${side === 'A' ? 'a' : 'b'}.webp`);
if (typeof Image !== 'undefined') { for (let d = 0; d <= 20; d++) new Image().src = hex(`num/${d}.svg`); for (const s of ['A', 'B']) new Image().src = tokenBase(s); }
