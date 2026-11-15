// The one card (design sandbox card3/, Martin 2026-10-04): one painted driftwood frame, tinted per rarity (driftwood, steel,
// gold), its name bar holding the name, its banner the strength in chalk digits, its panel the rules and family, the
// painting set into its window. `compact` drops the panel (hand and collection show the painting; the full card shows on hover).
// Size it with the CSS variable --w on .card (everything inside scales with it).
import { hasArt, artUrl, CROP, FULL } from './art.js';

// The full card shows the painting between the name bar and the rules panel: about 61% of its height, so it centres on
// the animal (its FULL height, set per card, else the portrait crop's centre) instead of the painting's top; the compact card centres on
// the same height as far as its painting can move (lift).
// FACE (the stars prototype, Martin 2026-11-15: "we can try D"): 'open' is Gwent's way, the painting filling the card in
// the hand and the collection with only the strength banner hanging from its top-left corner and the level rising on a
// smaller banner from its bottom-right, no name; read in full, the painting runs from the card's top edge down to a plank
// with the name, the rules panel under it (tools/stars/bake_card_face.py cut the pieces from the frame painting).
// 'band' is the card as it was: the name bar across the top.
export const FACE = 'open';
const VIS = FACE === 'open' ? 0.596 : 0.61;   // open: 17.89em of the painting's 30em show above the plank
const focus = id => { const y = FULL[id] ?? (CROP[id] ? CROP[id][1] : 0.35); return Math.max(0, Math.min(1, (y - VIS / 2) / (1 - VIS))) * 100; };
// The compact card shows the painting (20em wide, so 30em tall) from under the band (3.05em) to the bottom (29.34em): it moves up
// to centre on the same height, never further than its top below the band or its bottom at the card's edge.
// The open compact card shows the whole painting but its bottom 0.66em, so it barely moves.
const lift = id => { const y = FULL[id] ?? (CROP[id] ? CROP[id][1] : 0.35);
  return FACE === 'open' ? Math.max(-0.66, Math.min(0, 14.67 - 30 * y)) : Math.max(-3.71, Math.min(0, 13.15 - 30 * y)); };

// Every keyword is bold wherever it stands, with its number and the colon or full stop after it ("Hungry 3." is bold whole,
// and so is Scout in "Roar: Scout a Bird."). The keywords are those KEYWORDS explains, below.
const rules = t => (t || '').replace(KW, '<b>$&</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');

// The stars prototype (branch `stars`, 2026-11-14, not settled): a card's level (c.stars, from the server: 0 ordinary,
// 1 strong, 2 legendary, 3 monster) is marked on the card, level 0 not at all, so a player counts only the exceptions.
// MARK is the one switch: the symbol ('gem': the level's number inside one plump star, as a cost sits in a mana gem;
// 'count': one star with the level's number before it from 2 up; 'star': a star per level; 'claw': scratches as a tally) and the place ('tr': the name
// bar's right end; 'tl': the bar's left end, the strength banner moved to the top right; 'br': a piece of the card's wood at
// the painting's bottom right). LABEL.five is the collection's other labelling: every card numbered 1 to 5 (its level + 2).
export const MARK = { symbol: 'gem', place: 'tr' };
export const LABEL = { five: false };
const STAR = (() => { const p = []; for (let i = 0; i < 10; i++) { const a = Math.PI * (i / 5 - .5), r = i % 2 ? 4.9 : 11;
  p.push(`${(12 + r * Math.cos(a)).toFixed(2)},${(12.9 + r * Math.sin(a)).toFixed(2)}`); } return p.join(' '); })();
const FAT = (() => { const p = []; for (let i = 0; i < 10; i++) { const a = Math.PI * (i / 5 - .5), r = i % 2 ? 7.4 : 11.6;
  p.push(`${(12 + r * Math.cos(a)).toFixed(2)},${(12.6 + r * Math.sin(a)).toFixed(2)}`); } return p.join(' '); })();
const CW = n => 15 + 6.5 * (n - 1);   // a tally of n scratches, in the glyph's 24-high units
const GLYPH = {
  gem: n => `<svg class="gem" viewBox="0 0 24 24"><polygon points="${FAT}" class="sol" stroke-width="2.2" stroke-linejoin="round"/>`
    + `<text x="12" y="13.6" text-anchor="middle" dominant-baseline="central">${n}</text></svg>`,
  count: n => (n > 1 ? `<i class="num">${n}</i>` : '') + GLYPH.star(1),
  star: n => `<svg class="g" viewBox="0 0 24 24"><polygon points="${STAR}" fill="#fff" stroke="#fff" stroke-width="1.2" stroke-linejoin="round"/></svg>`.repeat(n),
  // claw marks: n scratches drawn as one tally, each a tapered stroke from top right to bottom left
  claw: n => `<svg class="g claw" viewBox="0 0 ${CW(n)} 24" style="aspect-ratio:${CW(n)}/24">${Array.from({ length: n }, (_, i) => { const x = 1.5 + 6.5 * i;
      return `<path fill="#fff" d="M${x + 9} 1C${x + 7.5} 8 ${x + 4.5} 15 ${x + .5} 23C${x + 7.5} 16 ${x + 11} 9 ${x + 12.5} 2Z"/>`; }).join('')}</svg>`,
};
// The open face's level: a star inked on the level's banner, its number left bare wood (a mask, the same for every card of
// a level, so repeated ids agree).
const tagHTML = lv => `<span class="ltag"><svg viewBox="0 0 24 24"><defs><mask id="akl${lv}"><rect width="24" height="24" fill="#fff"/>`
  + `<text x="12" y="13.7" text-anchor="middle" dominant-baseline="central" fill="#000">${lv}</text></mask></defs>`
  + `<polygon points="${FAT}" mask="url(#akl${lv})" stroke-width="2.2" stroke-linejoin="round"/></svg></span>`;
// The mark's html and how many glyph widths it takes ('' and 0 for a card with none).
function mark(c) {
  const lv = c.stars | 0;
  if (LABEL.five) return [`<span class="lvl five">${chalk(lv + 2)}</span>`, 1];
  if (!lv) return ['', 0];
  const w = MARK.symbol === 'gem' ? 1.45 : MARK.symbol === 'count' ? (lv > 1 ? 1.45 : 1) : MARK.symbol === 'claw' && lv > 0 ? CW(lv) / 24 : Math.abs(lv);
  return [`<span class="lvl">${GLYPH[MARK.symbol](lv)}</span>`, w];
}

// The mark alone, for a deck's strips (collection.js): the same glyphs in a span of class `cls`; '' for a card with none.
export function markGlyphs(c, cls) {
  const lv = c.stars | 0;
  if (LABEL.five) return `<span class="${cls} five">${lv + 2}</span>`;
  return lv ? `<span class="${cls}">${GLYPH[MARK.symbol](lv)}</span>` : '';
}

// `str`: the strength to show (hand strength can differ from the printed one); `cls`: extra classes ('compact'); `lazy`: the
// art waits for lazyArt (art.js) to bring it near the screen.
// The name is centred in the bar; a longer name sets smaller in proportion to its length (--n), one over 18 characters may wrap.
export function cardHTML(c, { str = c.str, cls = '', attrs = '', lazy = false } = {}) {
  const base = c.str === '*' ? null : c.str, delta = base !== null && str !== base ? (str > base ? ' up' : ' down') : '';
  const art = !hasArt(c.id) ? '' : lazy ? ` data-art="${artUrl(c.id)}" style="--fy:${focus(c.id).toFixed(0)}%;--oy:${lift(c.id).toFixed(2)}em"`
    : ` style="background-image:url(${artUrl(c.id)});--fy:${focus(c.id).toFixed(0)}%;--oy:${lift(c.id).toFixed(2)}em"`;
  const open = FACE === 'open', [lvl, lw] = open ? [(c.stars | 0) > 0 ? tagHTML(c.stars | 0) : '', 0] : mark(c);
  return `<div class="card ${c.rarity} ${open ? 'fo' : `mk-${MARK.place}${lvl ? ' lv' : ''}`} ${cls}" ${attrs}><div class="pic"${art}>${hasArt(c.id) ? '' : `<span>${c.label || c.name}</span>`}</div><div class="cframe"></div>` +
    `<div class="nbar${c.name.length > 18 ? ' two' : ''}" style="--n:${c.name.length}${lvl ? `;--lw:${lw}` : ''}"><span>${c.name}</span></div>` +
    `<div class="stab"><span class="n${String(str).length > 1 ? ' two' : ''}${delta}">${chalk(str)}</span></div>` +
    `<div class="ctext">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div>${lvl}</div>`;
}

// Names are set at their largest size and shrink only as much as their bar actually needs (measured, not guessed from length).
// The effect text does the same in its panel: a long effect sets smaller, never past the family line under it (length is
// no constraint on a card, Martin 2026-10-30; the panel fits the text, not the other way round).
export function fitNames(root) {
  for (const s of root.querySelectorAll('.card .nbar:not(.two) span')) {
    s.style.fontSize = '';
    const over = s.scrollWidth / s.clientWidth;
    if (over > 1.001) s.style.fontSize = (parseFloat(getComputedStyle(s).fontSize) / over * .98) + 'px';
  }
  for (const p of root.querySelectorAll('.card:not(.compact) .ctext p')) {
    p.style.fontSize = '';
    const box = p.parentElement, cs = getComputedStyle(box);
    const room = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    if (room <= 0 || p.offsetHeight <= room + 0.5) continue;
    // the largest size that fits, by halving the range: rewrapping isn't linear, so no formula lands on it
    const fits = px => { p.style.fontSize = px + 'px'; return p.offsetHeight <= room + 0.5; };
    let hi = parseFloat(getComputedStyle(p).fontSize), lo = hi / 2;
    for (let i = 0; i < 7; i++) { const mid = (lo + hi) / 2; if (fits(mid)) lo = mid; else hi = mid; }
    p.style.fontSize = lo + 'px';
  }
}

// A card read large: the cards it makes (its related cards, in the order they come; arrows when they are what it becomes)
// and each keyword on any of them explained, as one block (.zside) the collection's zoom and the game's card view lay out
// right of the card. One related card takes the keywords beside it ('few'); two or more, under them, as wide as their row.
export function readSide(c, cards) {
  const rel = (c.related || []).map(id => cards[id]).filter(Boolean);
  const kws = Object.keys(KEYWORDS).filter(k => [c, ...rel].some(x => hasKeyword(x, k)))
    .concat(Object.keys(TERMS).filter(t => [c, ...rel].some(x => new RegExp(`\\b${t.toLowerCase()}\\b`).test(x.text || ''))));
  if (!rel.length && !kws.length) return '';
  const cls = !rel.length ? '' : rel.length === 1 ? ' few' : ' row';
  return `<div class="zside${cls}">` +
    (rel.length ? `<div class="rel${rel.length > 4 ? ' many' : ''}">${rel.map(r => cardHTML(r)).join(c.evolves ? '<i class="arr"></i>' : '')}</div>` : '') +
    (kws.length ? `<div class="kws">${kws.map(k => `<div class="kw"><b>${k}</b><p>${KEYWORDS[k] || TERMS[k]}</p></div>`).join('')}</div>` : '') + '</div>';
}

// Each keyword in one line, for players learning the rules: the collection's zoom lists them, the board's badges show them on hover.
// Scout is a card-text term ("Roar: Scout a Bird."), explained the same way (hasKeyword finds it).
// Rules words a card uses mid-sentence ("Dusk: if this is grazing, draw a card."), explained beside its keywords (rulings.md).
export const TERMS = { 'Grazing': 'An animal grazes while it\'s the top animal on a corner of a region you control.' };
export const hasKeyword = (c, k) => new RegExp(`(^|\\. |: )${k}[:. ]`).test(c.text || '');
export const KEYWORDS = {
  'Roar': 'Happens when you place this animal.',
  'Action': 'Costs one of your two actions. Each animal can do it once a turn.',   // the actions prototype
  'Flight': 'Can be placed on any crossroad, even one not connected to yours. It can\'t take a den that way.',
  'Armor': 'Can\'t be removed, returned to hand or eaten by any ability, not even your own. It can still be covered.',
  'Stealth': 'Enemy abilities can\'t choose it. Effects that hit many animals, or a random one, still do.',
  'Apex Predator': 'Must be placed on top of another animal, yours or an enemy\'s, and eats it. Can\'t be placed on a den.',
  'Spikes': 'The first time an enemy covers it, that enemy is removed.',
  'Poison': 'Whenever an enemy covers it, that enemy is removed at the start of your next turn.',
  'Roam': 'As an action, move it through your animals connected to it, then one crossroad beyond (two with Reach): onto an empty crossroad, onto one of your animals, or onto an enemy it beats. It takes the den only from the den front, connected to your den. Once per turn.',
  'Reach': 'Can be placed up to two crossroads away from one of your connected animals, jumping over what stands between. It can\'t take a den that way.',
  'Hungry': 'At the start of your turn it eats up to that much of your food, and loses 1 strength for good for each food it was short.',
  'Titan': 'Playing it takes two actions. A free play (an effect like "play another animal") can\'t pay for it.',
  'Flee': 'When an enemy covers it, it runs back to your hand.',
  'Wild': 'Belongs to no one: it connects no one and holds no region, and any animal can cover it. Every turn is its turn.',
  'Dawn': 'Happens at the start of your turn.',
  'Dusk': 'Happens at the end of your turn.',
  'Fall': 'Happens when it is removed from the board.',
  'Scout': 'Look at three different cards of your deck, draw one and shuffle the others back.',
};
const KW = new RegExp(`\\b(${Object.keys(KEYWORDS).join('|')})\\b( \\d+)?[:.]?`, 'g');
