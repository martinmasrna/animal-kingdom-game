// Card proposal v2 (lab only): the painting is the whole card. Name on a dark fade at the top, rules and tribe on a
// dark fade at the bottom, strength in the board's chalk digits on the painting's shadow, rarity as the card's edge.
import { hasArt, artUrl } from '/static/art.js';

const KW = /^(Battlecry|Deathrattle|Immovable|Flight|Stealth|Apex Predator|Fragile)(:|\.)/;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');

export function cardHTML(c, { str = c.str, cls = '' } = {}) {
  const art = hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)})"` : '';
  return `<div class="card3 ${c.rarity} ${cls}"><div class="art"${art}></div>` +
    `<div class="str">${chalk(str)}</div><div class="nm${c.name.length > 16 ? ' long' : ''}"><span>${c.name}</span></div>` +
    `<div class="rules">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
