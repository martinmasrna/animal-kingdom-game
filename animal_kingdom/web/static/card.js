

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
// `draw`: how a related card is drawn (the mana rules draw their own card, mana.js).
export function readSide(c, cards, draw) {
  const rel = (c.related || []).map(id => cards[id]).filter(Boolean);
  const kws = Object.keys(KEYWORDS).filter(k => [c, ...rel].some(x => hasKeyword(x, k)));
  if (!rel.length && !kws.length) return '';
  const cls = !rel.length ? '' : rel.length === 1 ? ' few' : ' row';
  return `<div class="zside${cls}">` +
    (rel.length ? `<div class="rel${rel.length > 4 ? ' many' : ''}">${rel.map(draw).join(c.evolves ? '<i class="arr"></i>' : '')}</div>` : '') +
    (kws.length ? `<div class="kws">${kws.map(k => `<div class="kw"><b>${k}</b><p>${KEYWORDS[k]}</p></div>`).join('')}</div>` : '') + '</div>';
}

// Each keyword in one line, for players learning the rules: a card read large lists its own.
export const hasKeyword = (c, k) => new RegExp(`(^|\\. |: )${k}[:. ]`).test(c.text || '');
export const KEYWORDS = {
  'Roar': 'Happens when you place this animal.',
  'Flight': 'Can be placed on any tile, even one not connected to yours.',
  'Armor': 'Can\'t be removed, returned to hand or eaten by any ability, not even your own. It can still be covered.',
  'Stealth': 'Enemy abilities can\'t choose it. Effects that hit many animals, or a random one, still do.',
  'Spikes': 'The first time an enemy covers it, that enemy is removed.',
  'Poison': 'Whenever an enemy covers it, that enemy is removed at the start of your next turn.',
  'Hungry': 'Must be placed on top of an enemy it beats. When that enemy is removed, gain 1 food.',
  'Scout': 'Look at 3 cards from your deck. Draw one. The rest stay where they were.',
};
