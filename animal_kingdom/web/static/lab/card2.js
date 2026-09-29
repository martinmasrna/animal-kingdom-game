// Card proposal (lab only): a dark calm body, the art large, strength on the board's boss in chalk digits,
// the rules on a pale flat panel, rarity as the colour of the line around the art.
import { hasArt, artUrl, CROP } from '/static/art.js';

const KW = /^(Battlecry|Deathrattle|Immovable|Flight|Stealth|Apex Predator|Fragile)(:|\.)/;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');
// The window is 0.93 tall per unit wide against the art's 1.5: frame on the portrait crop's centre.
const VIS = 0.62;
const focus = id => { const y = CROP[id] ? CROP[id][1] : 0.35; return Math.max(0, Math.min(1, (y - VIS / 2) / (1 - VIS))) * 100; };

export function cardHTML(c, { str = c.str, cls = '', team = 'a' } = {}) {
  const art = hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)});background-position:50% ${focus(c.id).toFixed(0)}%"` : '';
  return `<div class="card2 ${c.rarity} ${cls}"><div class="art"${art}></div>` +
    `<div class="nm${c.name.length > 16 ? ' long' : ''}"><span>${c.name}</span></div><div class="boss ${team}">${chalk(str)}</div>` +
    `<div class="gem"></div><div class="rules">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
