// Card proposal v2 (lab only): the painting is the whole card. Name on a dark fade at the top, rules and tribe on a
// dark fade at the bottom, strength in the board's chalk digits on the painting's shadow, rarity as the card's edge.
import { hasArt, artUrl } from '/static/art.js';

// Every keyword that opens a sentence is bold ("Flight. Battlecry: ..." bolds both).
const KW = /(?<=^|\. )(Battlecry|Deathrattle|Immovable|Flight|Stealth|Apex Predator|Fragile)(:|\.)/g;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');

// The name is centred on the card; a longer name sets smaller in proportion to its length (--n), and one over 18 characters ("Vesper, Champion of the Hive") takes two balanced lines.
export function cardHTML(c, { str = c.str, cls = '' } = {}) {
  const name = c.name;
  const art = hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)})"` : '';
  return `<div class="card3 ${c.rarity} ${cls}"><div class="art"${art}></div>` +
    `<div class="bar${name.length > 18 ? ' two' : ''}" style="--n:${name.length}"><span>${name}</span></div><div class="tab"><div class="face"><span class="n${String(str).length > 1 ? ' two' : ''}">${chalk(str)}</span></div></div>` +
    `<div class="rules">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
