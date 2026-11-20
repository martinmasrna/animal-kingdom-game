// The mana ruleset's card and match screen pieces (the prototype of 2026-11-20; nothing in its look is settled). A card is
// two parts: the board piece on top, the token the board draws (token.js, board.js tokenHTML) complete and unchanged, and
// a plain text plaque hanging under it (name, rules text, family), the piece's lower point sitting in a notch in the
// plaque. While the card is in a hand, its cost is a small gold hexagon inside the piece's upper-left corner: a scaled
// copy of the piece sharing that corner, so its upper-left and left edges lie on the piece's own rim (prototype, not
// settled). Every length is in the card's width, --mw (the piece's width), so it draws at any size.
import { tokenHTML, tokenWidth } from './board.js';
import { TW, TH } from './token.js';
import { KEYWORDS } from './card.js';

const P = TH / TW;                 // the piece's height, in its widths
export const PLAQUE = 1.2;         // the plaque's height below its top corners, in card widths
const TOP = .75 * P;               // the plaque's top corners: level with the piece's lower side corners
export const CARD_H = TOP + PLAQUE;   // the whole card's height, in its widths
const NOTCH = .25 * P;             // the notch's depth (the piece's lower point) and the plaque's own lower point
const COST = .3;                   // the cost mark's size, in pieces
// The flight's and the grip's measures for this card (flight.js fly, carry.js carry): over its place the card is as wide as
// a board token, its piece's centre above the card's centre by half the card less half the piece.
export const flightGeo = () => { const w = tokenWidth(); return { end: w, up: (CARD_H - P) / 2, rear: w * 1.14, hit: w * .96 }; };

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const KW = new RegExp(`\\b(${Object.keys(KEYWORDS).join('|')})\\b( \\d+)?[:.]?`, 'g');
const rules = t => esc(t || '').replace(KW, '<b>$&</b>');

// The plaque's outline as an SVG polygon in a W x L box (1000 units wide): the notch on top, the point below.
const L = 1000 * PLAQUE, D = 1000 * NOTCH;
const PLAQUE_SVG = `<svg class="mpl" viewBox="0 0 1000 ${L}" preserveAspectRatio="none"><polygon vector-effect="non-scaling-stroke" points="0,0 500,${D} 1000,0 1000,${L - D} 500,${L} 0,${L - D}"/></svg>`;
// The cost mark: a pointy hexagon, its box placed so its upper-left corner is the piece's (0, P/4).
const hexPts = (w, h) => `${w / 2},0 ${w},${h / 4} ${w},${3 * h / 4} ${w / 2},${h} 0,${3 * h / 4} 0,${h / 4}`;
const COST_SVG = n => `<svg viewBox="0 0 100 ${100 * P}"><polygon points="${hexPts(100, 100 * P)}"/><text x="50" y="${50 * P}" text-anchor="middle" dominant-baseline="central">${n}</text></svg>`;
const COST_AT = `left:0;top:calc(var(--mw) * ${(.25 * P * (1 - COST)).toFixed(4)});width:calc(var(--mw) * ${COST});height:calc(var(--mw) * ${(COST * P).toFixed(4)})`;

// One card. `c`: the card (CARDS[id], its text already the ruleset's); `str`: the strength to show; `cost`: its mana cost,
// shown while it is in a hand (null: none, as on the board); `owner`: 'A' yours, 'B' your opponent's (viewer space); `w`:
// the card's width in stage px; `cls`, `attrs`: extra classes and attributes on the card.
export function manaCard(c, { str = c.str, cost = null, owner = 'A', w = 100, cls = '', attrs = '', iid = null } = {}) {
  const piece = tokenHTML({ id: c.id, owner, str, iid: iid ?? 0 }, { [c.id]: c }, w);
  const tags = (c.tags || []).join(' · ');
  return `<div class="mcard ${owner}${cls ? ' ' + cls : ''}" style="--mw:${w}px" ${attrs}>`
    + `<div class="plaque">${PLAQUE_SVG}<div class="pin"><b class="pname">${esc(c.name)}</b>${c.text ? `<p>${rules(c.text)}</p>` : ''}${tags ? `<i>${esc(tags)}</i>` : ''}</div></div>`
    + `<div class="mpiece unit ${owner}" style="--tw:${w}px">${piece}</div>`
    + (cost != null ? `<div class="mcost" style="${COST_AT}">${COST_SVG(cost)}</div>` : '') + '</div>';
}

// A long rule sets smaller until it fits its plaque (as card.js fitNames does for the rectangular card).
export function fitPlaques(root) {
  for (const p of root.querySelectorAll('.mcard .pin p')) {
    p.style.fontSize = '';
    const pin = p.parentElement, room = pin.clientHeight;
    if (room <= 0 || pin.scrollHeight <= room + .5) continue;
    let hi = parseFloat(getComputedStyle(p).fontSize), lo = hi * .55;
    const fits = px => { p.style.fontSize = px + 'px'; return pin.scrollHeight <= room + .5; };
    for (let i = 0; i < 7; i++) { const mid = (lo + hi) / 2; if (fits(mid)) lo = mid; else hi = mid; }
    p.style.fontSize = lo + 'px';
  }
}

// The mana as six small gold hexagons (more while a bonus raises the turn past six): available filled, spent dimmed, not
// yet reached outlined.
export function pipsHTML(left, total, cap = 6) {
  const n = Math.max(cap, total), spent = total - left;
  return `<span class="mpips">${Array.from({ length: n }, (_, i) => `<i class="${i < spent ? 'spent' : i < total ? 'on' : 'off'}"></i>`).join('')}</span>`;
}

// A small gold hexagon with a number, for an ability's price beside its button (Roam, Echo, a leader's power).
export const costChip = n => `<span class="mchip">${COST_SVG(n)}</span>`;

// The leader on the rail: its token, no strength (it is not on the board), dimmed while its power can't be used.
export function leaderToken(id, owner, cards, w) {
  return tokenHTML({ id, owner, str: null, iid: 0 }, cards, w);
}
