// The mana ruleset's card and match screen pieces (the prototype of 2026-11-20; nothing in its look is settled). A card is
// the board piece, the token the board draws (token.js, board.js tokenHTML) complete and unchanged, set in a card shaped
// as the hexagon stretched: its roof parallel to the piece's one frame band outside it, upright sides, a point below. Every
// edge on it is the hexagon's. The piece sits in a collar of one metal, its sides on the frame's inner border; under its
// strength drawer the name plate, then the rules text dark on a light box, then the family in the card's bottom point,
// as strength sits in the piece's. The cost, while in a hand, is the card's own top-left corner: a gold hexagon whose
// upper-left and left edges lie on the card's outline (Martin's pick on 2026-11-20 from the card-layout mockups: "agree").
// The card's box is the piece's (--mw wide, the piece at its top left); the frame reaches past it on every side, so the
// flight and the hand's measures, made for the piece, hold. Every length is in --mw, so it draws at any size.
import { tokenHTML, tokenWidth, squareLook } from './board.js';
import { TW, TH, DRAWER_FRAC } from './token.js';
import { KEYWORDS } from './card.js';
import { FIGS } from './hex/figs.js';
import { NUMS } from './hex/nums.js';

const P = TH / TW;                          // the piece's height, in its widths
const LW = 1.11, LH = LW * P;               // the collar round the piece
const WC = LW / .9;                         // the card's width: the collar plus a band of 5% of the card each side
const BD = (WC - LW) / 2;                   // the frame band
const SL = (LH / 4) / (LW / 2);             // the hexagon's edges' slope
const OFF = BD / Math.cos(Math.PI / 6);     // a roof-parallel line one band out sits this much higher
const X0 = -(WC - 1) / 2, Y0 = -(OFF + (LH - P) / 2); // the card's top-left corner, from the piece's
const YS = (WC / 2) * SL;                   // the card's shoulder below its apex
const PL_T = P - .03 * WC - Y0, PL_H = .085 * WC * 1.75;     // the name plate (from the card's top)
const BX_T = PL_T + PL_H + .02 * WC, BX_H = .32 * WC;        // the text box
const TIP = (WC / 2) * SL;                                   // the bottom point's height
const HC = BX_T + BX_H + .04 * WC + TIP;                     // the card's height
export const CARD_H = HC + Y0;              // the card's box below the piece's top, in its widths
const GEM = .27 * WC;                       // the cost hexagon's width
// The flight's and the grip's measures for this card (flight.js fly, carry.js carry): over its place the card is as wide as
// a board token, its piece's centre above the card's centre by half the card less half the piece.
// The square board's card: over its tile its creature is the standing figure's size, and its picture's centre above the tile's.
export const flightGeo = () => { const w = tokenWidth(); if (squareLook()) return { end: w * RC_END, up: RC_UP, rear: w * RC_END * 1.14, hit: w * RC_END * .96 }; return { end: w, up: (CARD_H - P) / 2, rear: w * 1.14, hit: w * .96 }; };

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const KW = new RegExp(`\\b(${Object.keys(KEYWORDS).join('|')})\\b( \\d+)?[:.]?`, 'g');
const rules = t => esc(t || '').replace(KW, '<b>$&</b>');
const k = n => `calc(var(--mw) * ${n.toFixed(4)})`;
const box = (l, t, w, h) => `left:${k(l)};top:${k(t)};width:${k(w)};height:${k(h)}`;

// The card's chrome, in a box WC x HC (1000 units wide): the outline, the inner border, the collar and the piece's seat.
const U = 1000 / WC, n = v => (v * U).toFixed(1);
const hexPts = (x, y, w, h) => `${x + w / 2},${y} ${x + w},${y + h / 4} ${x + w},${y + 3 * h / 4} ${x + w / 2},${y + h} ${x},${y + 3 * h / 4} ${x},${y + h / 4}`;
// Each card its own gradient ids: an id is the document's, and a url(#id) resolving to a copy inside a hidden element
// paints nothing (the hovered card's frame went missing, Martin, 2026-11-21).
let frames = 0;
const frameSVG = (u = ++frames) => `<svg class="mpl" viewBox="0 0 1000 ${n(HC)}"><defs><linearGradient id="mfr${u}" x1="0" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="#474d56"/><stop offset=".55" stop-color="#363b43"/><stop offset="1" stop-color="#2b2f36"/></linearGradient><linearGradient id="mcl${u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#646c78"/><stop offset="1" stop-color="#2c3037"/></linearGradient></defs>`
  + `<polygon class="mfo" fill="url(#mfr${u})" points="500,0 1000,${n(YS)} 1000,${n(HC - TIP)} 500,${n(HC)} 0,${n(HC - TIP)} 0,${n(YS)}"/>`
  + `<polyline class="mib" points="${n(BD)},${n(OFF + LH / 4)} ${n(BD)},${n(HC - TIP - BD * SL)} 500,${n(HC - OFF)} ${n(WC - BD)},${n(HC - TIP - BD * SL)} ${n(WC - BD)},${n(OFF + LH / 4)}"/>`
  + `<polygon fill="url(#mcl${u})" points="${hexPts(+n(BD), +n(OFF), +n(LW), +n(LH))}"/>`
  + `<polygon fill="#0f1215" points="${hexPts(+n(BD + (LW - 1.05) / 2), +n(-Y0 - .025 * P), +n(1.05), +n(1.05 * P))}"/></svg>`;
// The cost: the card's own top-left corner, its upper-left vertex on the card's shoulder.
const GH = GEM * P;
// The number in Martin's strength numerals (token.js numeral, static/hex/num), inked dark on the gold by an SVG filter: WebKit ignores CSS filters on SVG children.
const COST_SVG = c => { const h = 100 * P * .62, w = h * 2 / 1.2;
  return `<svg viewBox="0 0 100 ${(100 * P).toFixed(2)}"><filter id="mink"><feColorMatrix values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .88 0"/></filter><polygon points="${hexPts(0, 0, 100, 100 * P)}"/><image class="mnum" filter="url(#mink)" href="/static/hex/num/${Math.max(0, Math.min(20, c))}.svg" x="${(50 - w / 2).toFixed(2)}" y="${(50 * P - h / 2).toFixed(2)}" width="${w.toFixed(2)}" height="${h.toFixed(2)}"/></svg>`; };
const COST_AT = box(X0, Y0 + YS - GH / 4, GEM, GH);
// The piece alone (a deck tray, a shown hand) keeps the cost in the piece's own upper-left corner, sharing its two edges.
const PIECE_COST_AT = box(0, .25 * P * (1 - .3), .3, .3 * P);
// A leader's power's cost: in the strength's drawer at the piece's bottom point, its bottom point the piece's and its lower
// edges the piece's, where a card's strength sits (a leader has none to show; Martin, 2026-11-21: "on bottom, where
// strength sits"). As percentages of the piece's box, so it sits on any piece (the rail's token, a card's).
const DW = DRAWER_FRAC / P, DH = DRAWER_FRAC / P;   // the drawer's width (of the piece's width) and height (of its height)
export const powerCostHTML = cost => `<div class="pcost" style="left:${((1 - DW) / 2 * 100).toFixed(3)}%;top:${((1 - DH) * 100).toFixed(3)}%;width:${(DW * 100).toFixed(3)}%;height:${(DH * 100).toFixed(3)}%">${COST_SVG(cost)}</div>`;
// A leader's power read as a card of its own beside the leader's (as a card's tokens are): the leader's figure, what kind
// of ability it is, its text, and a power's cost on top in place of the gem.
export function powerCard(id, L, w = 170) {
  if (squareLook()) return `<div class="pwcard">${rectCard({ id, name: L.kind === 'power' ? 'Hero power' : 'Passive', text: L.text, rarity: 'common' }, { str: null, cost: L.kind === 'power' ? L.cost ?? null : null, w })}</div>`;
  const card = manaCard({ id, name: L.kind === 'power' ? 'Hero power' : 'Passive', text: L.text, rarity: 'common' }, { str: null, w });
  return `<div class="pwcard">${L.kind === 'power' && L.cost != null ? card.replace(/(<div class="mpiece[^>]*>)/, `$1${powerCostHTML(L.cost)}`) : card}</div>`;
}

// One card. `c`: the card (CARDS[id], its text already the ruleset's); `str`: the strength to show; `cost`: its mana cost,
// shown while it is in a hand (null: none, as on the board); `owner`: 'A' yours, 'B' your opponent's (viewer space); `w`:
// the piece's width in stage px (the card reaches a fifth past it); `cls`, `attrs`: extra classes and attributes on the card.
export function manaCard(c, { str = c.str, cost = null, owner = 'A', w = 100, cls = '', attrs = '', iid = null } = {}) {
  if (squareLook()) return rectCard(c, { str, cost, owner, w, cls, attrs });
  const piece = tokenHTML({ id: c.id, owner, str, iid: iid ?? 0 }, { [c.id]: c }, w);
  const tags = (c.tags || []).join(' · ');
  return `<div class="mcard ${owner}${cls ? ' ' + cls : ''}" style="--mw:${w}px" ${attrs}>`
    + `<div class="plaque" style="${box(X0, Y0, WC, HC)}">${frameSVG()}`
    + `<div class="mplate" style="${box(BD, PL_T, LW, PL_H)}"><b class="pname">${esc(c.name)}</b></div>`
    + `<div class="pin" style="${box(BD + .025 * WC, BX_T, WC - 2 * BD - .05 * WC, BX_H)}">${c.text ? `<p>${rules(c.text)}</p>` : ''}</div>`
    + (tags ? `<i class="mfam" style="top:${k(HC - TIP * .62)}">${esc(tags)}</i>` : '') + '</div>'
    + `<div class="mpiece unit ${owner}" style="--tw:${w}px">${piece}</div>`
    + (cost != null ? `<div class="mcost" data-n="${cost}" style="${COST_AT}">${COST_SVG(cost)}</div>` : '') + '</div>';
}

// The piece alone, as a hand shows it under its plaque: the token with its cost hexagon (the collection's deck tray).
// `str: null` draws no strength (a leader, as the rail draws it); `cost: null` no cost mark.
export function manaPiece(c, { str = c.str, cost = null, owner = 'A', w = 60, cls = '', attrs = '' } = {}) {
  if (squareLook()) return rectCard(c, { str, cost, owner, w, cls, attrs });   // the square board's card is all picture at rest: it is its own piece
  return `<div class="mcard mpc ${owner}${cls ? ' ' + cls : ''}" style="--mw:${w}px" ${attrs}><div class="mpiece unit ${owner}" style="--tw:${w}px">${tokenHTML({ id: c.id, owner, str, iid: 0 }, { [c.id]: c }, w)}</div>`
    + (cost != null ? `<div class="mcost" data-n="${cost}" style="${PIECE_COST_AT}">${COST_SVG(cost)}</div>` : '') + '</div>';
}

// A long rule sets smaller until it fits its plaque (as card.js fitNames does for the rectangular card).
export function fitPlaques(root) {
  if (typeof document !== 'undefined' && document.fonts && document.fonts.status !== 'loaded') document.fonts.ready.then(() => fitPlaques(root));   // measured again in the card's own face once it has loaded
  for (const p of root.querySelectorAll('.mcard .pin p, .rc .rtxt p')) {
    p.style.fontSize = '';
    const pin = p.parentElement, cs = getComputedStyle(pin), room = pin.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) - 4;   // the text's own height: a centred box hides overflow above it from scrollHeight
    if (room <= 0 || p.offsetHeight <= room) continue;
    let hi = 1, lo = .55;   // a share of the card's own size (mana.css .pin p), so a card resized after the fit stays fitted
    const base = p.closest('.rc') ? .08 : .096;
    const fits = f => { p.style.fontSize = `calc(var(--mw) * ${(base * f).toFixed(4)})`; return p.offsetHeight <= room; };
    for (let i = 0; i < 7; i++) { const mid = (lo + hi) / 2; if (fits(mid)) lo = mid; else hi = mid; }
    fits(lo);
  }
  for (const b of root.querySelectorAll('.mcard .mplate .pname, .rc .rnm .pname')) {   // a long name narrows to its plate, as a share of the card's size
    b.style.fontSize = '';
    const room = b.parentElement.clientWidth * .94, wd = b.scrollWidth;
    if (room > 0 && wd > room) b.style.fontSize = `calc(var(--mw) * ${((b.closest('.rc') ? .125 : .14) * room / wd).toFixed(4)})`;
  }
}

// The mana as ten small gold hexagons (more while a bonus raises the turn past ten): available filled, spent dimmed, not
// yet reached outlined.
export function pipsHTML(left, total, cap = 10) {
  const n = Math.max(cap, total, left), spent = Math.max(0, total - left), on = Math.max(total, left);   // gained mana (the Mana Blob) can pass the total
  return `<span class="mpips">${Array.from({ length: n }, (_, i) => `<i class="${i < spent ? 'spent' : i < on ? 'on' : 'off'}"></i>`).join('')}</span>`;
}

// A small gold hexagon with a number, for an ability's price beside its button (Roam, Echo, a leader's power).
export const costChip = n => `<span class="mchip" data-n="${n}">${COST_SVG(n)}</span>`;

// The leader on the rail: its token, no strength (it is not on the board), dimmed while its power can't be used.
export function leaderToken(id, owner, cards, w) {
  return tokenHTML({ id, owner, str: null, iid: 0 }, cards, w);
}

// ---------------------------------------------------------------- the square board's card
// The card Martin settled for the square board in its tuning tool (design/screen/square/card/tune, 2026-11-23: "let's go
// with what we have now"; html.sqlook, board.js squareLook): a portrait rectangle 1.38 widths tall in one grey hairline (a
// legendary's near white), all picture at rest, the creature's head free to rise over the top edge, the name bare on its
// foot. Read, a light panel rises inside it with the rules, the name moves to the panel's seam in ink and the creature
// steps back and up (mana.css .rc, --open); a card with no text never opens. The cost is a hexagon on the top-left corner,
// the strength a tile with cut corners on the top-right, both overhanging; both digits Martin's numerals, drawn here as
// strokes so their weight and outline can be set. Every length is a share of the card's width, --mw.
// CARD_LOOK: the tool's dials, under its own keys and units, so the JSON its Copy button gives pastes straight in (the hand
// keys it also gives are the tool's, unused here). Lengths in % of the card's width; digitSize in % of its mark;
// digitWeight in % of the numerals' own stroke; costEdge the digits' dark outline (0: none); borderLight the border's grey
// as lightness; costColor and strColor the two marks. Martin's values of 2026-11-23.
export const CARD_LOOK = {"markOut":5,"markUp":6.5,"markSize":30,"digitSize":109,"digitWeight":130,"costEdge":0,"tileCut":15,"border":2,"borderLight":50,"costColor":"#1f5fae","strColor":"#7a2f24"};
if (globalThis.document) { const L = CARD_LOOK, st = document.documentElement.style, set = (k, v) => st.setProperty('--rc-' + k, v);
  set('mx', L.markOut / 100); set('my', L.markUp / 100); set('ns', L.markSize / 100); set('dg', L.digitSize + '%'); set('cut', L.tileCut + '%');
  set('bd', L.border / 100); set('frame', `hsl(0 0% ${L.borderLight}%)`); set('cost', L.costColor); set('str', L.strColor); }
// Over its tile in flight (flightGeo): the card at the width that makes its creature the standing figure's height (board.js
// STAND), the card's centre this many of its widths below the tile's centre (above, negative) so the creature stands where the figure will.
const RC_END = .62, RC_UP = -.2;
// A number in Martin's numerals as strokes (static/hex/nums.js): the cream stroke over, when costEdge is set, the same
// stroke wider and dark. Past 20 (rare) two of them side by side.
function digits(n) {
  n = Math.max(0, Math.round(n));
  const L = CARD_LOOK, k = L.digitWeight / 100, e = L.costEdge * 200 / (L.markSize * L.digitSize);   // the outline in the drawing's own units
  const g = (ps, c, x, t = '') => `<g class="${c}"${t}>${ps.map(([d, w]) => `<path d="${d}" stroke-width="${(w * k + x).toFixed(4)}"/>`).join('')}</g>`;
  const one = (m, t) => (e ? g(NUMS[m], 'dgo', 2 * e, t) : '') + g(NUMS[m], 'dgi', 0, t);
  const body = n <= 20 ? one(n) : one(Math.floor(n / 10) % 10, ' transform="translate(-.3 0) scale(.8)"') + one(n % 10, ' transform="translate(.3 0) scale(.8)"');
  return `<svg viewBox="-1 -.6 2 1.2" role="img" aria-label="${n}">${body}</svg>`;
}
// One card. The options are manaCard's; `w` is the card's own width. A face-down card (id '__back': a deck) is its frame alone.
function rectCard(c, { str = c.str, cost = null, owner = 'A', w = 100, cls = '', attrs = '' } = {}) {
  const head = k => `<div class="mcard rc ${owner}${k}${cls ? ' ' + cls : ''}" style="--mw:${w}px;--a:${FIGS[c.id] ? (FIGS[c.id][0] / FIGS[c.id][1]).toFixed(4) : 1}" ${attrs}>`;
  if (c.id === '__back') return head(' rback') + '<div class="rface"></div></div>';
  const fig = k => FIGS[c.id] ? `<img class="rfig${k}" src="/static/hex/fig/${c.id}.webp" alt="" draggable="false">` : '';
  return head(`${c.rarity === 'legendary' ? ' legendary' : ''}${c.text ? '' : ' notext'}`)
    + `<div class="rface"><div class="rwin"><i class="rbg"></i>${fig('')}</div>${fig(' out')}`
    + (c.text ? `<div class="rtxt"><p>${rules(c.text)}</p></div>` : '') + `<div class="rnm"><b class="pname">${esc(c.name)}</b></div></div>`
    + (cost != null ? `<div class="mcost" data-n="${cost}"><i></i>${digits(cost)}</div>` : '')
    + (str != null ? `<div class="mstr" data-n="${str}"><i></i>${digits(str)}</div>` : '') + '</div>';
}
