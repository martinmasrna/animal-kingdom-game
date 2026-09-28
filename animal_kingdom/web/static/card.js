// The one card: a painted brass frame per rarity (kit/frame_<rarity>.webp, from the design sandbox's board/r9)
// with the art behind its window and name, strength, rules text and tribe set into its blank areas.
// Size it with the CSS variable --w on .card (everything inside scales with it).
import { hasArt, artUrl } from './art.js';

const KW = /^(Battlecry|Deathrattle|Immovable|Flight|Stealth|Apex Predator|Fragile)(:|\.)/;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');

// `str`: the strength to show (hand and board strength can differ from the printed one); `cls`: extra classes.
export function cardHTML(c, { str = c.str, cls = '', attrs = '' } = {}) {
  const base = c.str === '*' ? null : c.str, delta = base !== null && str !== base ? (str > base ? ' up' : ' down') : '';
  return `<div class="card ${c.rarity} ${cls}" ${attrs}>` +
    `<div class="win"${hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)})"` : ''}>${hasArt(c.id) ? '' : `<span>${c.name}</span>`}</div>` +
    `<img class="frame" src="/static/kit/frame_${c.rarity}.webp" alt="" draggable="false">` +
    `<div class="cname">${c.name}</div><div class="cstr${delta}">${str}</div>` +
    `<div class="ctext">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
