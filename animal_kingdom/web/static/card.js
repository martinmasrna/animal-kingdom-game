// The one card (design sandbox card3/, Martin 2026-10-04): one painted driftwood frame, tinted per rarity (driftwood, steel,
// gold), its name bar holding the name, its banner the strength in chalk digits, its panel the rules and family, the
// painting set into its window. `compact` drops the panel (hand and collection show the painting; the full card shows on hover).
// Size it with the CSS variable --w on .card (everything inside scales with it).
import { hasArt, artUrl, CROP, FULL } from './art.js';

// The full card shows the painting between the name bar and the rules panel: about 61% of its height, so it centres on
// the animal (its FULL height, set per card, else the portrait crop's centre) instead of the painting's top; the compact card centres on
// the same height as far as its painting can move (lift).
const VIS = 0.61;
const focus = id => { const y = FULL[id] ?? (CROP[id] ? CROP[id][1] : 0.35); return Math.max(0, Math.min(1, (y - VIS / 2) / (1 - VIS))) * 100; };
// The compact card shows the painting (20em wide, so 30em tall) from under the band (3.05em) to the bottom (29.34em): it moves up
// to centre on the same height, never further than its top below the band or its bottom at the card's edge.
const lift = id => { const y = FULL[id] ?? (CROP[id] ? CROP[id][1] : 0.35); return Math.max(-3.71, Math.min(0, 13.15 - 30 * y)); };

// Every keyword is bold wherever it stands, with its number and the colon or full stop after it ("Hungry 3." is bold whole,
// and so is Scout in "Roar: Scout a Bird."). The keywords are those KEYWORDS explains, below.
const rules = t => (t || '').replace(KW, '<b>$&</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');

// `str`: the strength to show (hand strength can differ from the printed one); `cls`: extra classes ('compact'); `lazy`: the
// art waits for lazyArt (art.js) to bring it near the screen.
// The name is centred in the bar; a longer name sets smaller in proportion to its length (--n), one over 18 characters may wrap.
export function cardHTML(c, { str = c.str, cls = '', attrs = '', lazy = false } = {}) {
  const base = c.str === '*' ? null : c.str, delta = base !== null && str !== base ? (str > base ? ' up' : ' down') : '';
  const art = !hasArt(c.id) ? '' : lazy ? ` data-art="${artUrl(c.id)}" style="--fy:${focus(c.id).toFixed(0)}%;--oy:${lift(c.id).toFixed(2)}em"`
    : ` style="background-image:url(${artUrl(c.id)});--fy:${focus(c.id).toFixed(0)}%;--oy:${lift(c.id).toFixed(2)}em"`;
  return `<div class="card ${c.rarity} ${cls}" ${attrs}><div class="pic"${art}>${hasArt(c.id) ? '' : `<span>${c.label || c.name}</span>`}</div><div class="cframe"></div>` +
    `<div class="nbar${c.name.length > 18 ? ' two' : ''}" style="--n:${c.name.length}"><span>${c.name}</span></div>` +
    `<div class="stab"><span class="n${String(str).length > 1 ? ' two' : ''}${delta}">${chalk(str)}</span></div>` +
    `<div class="ctext">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}

// Names are set at their largest size and shrink only as much as their bar actually needs (measured, not guessed from length).
export function fitNames(root) {
  for (const s of root.querySelectorAll('.card .nbar:not(.two) span')) {
    s.style.fontSize = '';
    const over = s.scrollWidth / s.clientWidth;
    if (over > 1.001) s.style.fontSize = (parseFloat(getComputedStyle(s).fontSize) / over * .98) + 'px';
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
  'Flight': 'Can be placed on any crossroad, even one not connected to yours. It can\'t take a den that way.',
  'Armor': 'Can\'t be removed, returned to hand or eaten by any ability, not even your own. It can still be covered.',
  'Stealth': 'Enemy abilities can\'t choose it. Effects that hit many animals, or a random one, still do.',
  'Apex Predator': 'Must be placed on top of another animal, yours or an enemy\'s, and eats it. Can\'t be placed on a den.',
  'Spikes': 'The first time an enemy covers it, that enemy is removed.',
  'Poison': 'Whenever an enemy covers it, that enemy is removed at the start of your next turn.',
  'Roam': 'As an action, move it through your animals connected to it, then one crossroad beyond (two with Reach): onto an empty crossroad, onto one of your animals, or onto an enemy it beats. It takes the den only from the den front, connected to your den. Once per turn.',
  'Reach': 'Can be placed up to two crossroads away from one of your connected animals, jumping over what stands between. It can\'t take a den that way.',
  'Hungry': 'At the start of your turn it eats that much of your food. If you can\'t feed it, it loses that much strength for good.',
  'Titan': 'Playing it takes two actions. A free play (an effect like "play another animal") can\'t pay for it.',
  'Flee': 'When an enemy covers it, it runs back to your hand.',
  'Dawn': 'Happens at the start of your turn.',
  'Dusk': 'Happens at the end of your turn.',
  'Scout': 'Look at three different cards of your deck, draw one and shuffle the others back.',
};
const KW = new RegExp(`\\b(${Object.keys(KEYWORDS).join('|')})\\b( \\d+)?[:.]?`, 'g');
