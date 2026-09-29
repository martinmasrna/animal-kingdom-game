// The one card: a painted brass frame per rarity (kit/frame_<rarity>.webp, from the design sandbox's board/r9)
// with the art behind its window and name, strength, rules text and tribe set into its blank areas.
// Size it with the CSS variable --w on .card (everything inside scales with it).
import { hasArt, artUrl, CROP } from './art.js';

// The window shows 73% of a 2:3 painting's height (its box is 1.09 tall per unit wide, the art 1.5), so
// centring it cuts the heads off. Frame on the head instead: the portrait crop's centre height, clamped.
const VIS = 0.728;
const focus = id => { const y = CROP[id] ? CROP[id][1] : 0.35; return Math.max(0, Math.min(1, (y - VIS / 2) / (1 - VIS))) * 100; };

// Every keyword that opens a sentence is bold ("Flight. Battlecry: ..." bolds both).
const KW = /(?<=^|\. )(Battlecry|Deathrattle|Immovable|Flight|Stealth|Apex Predator|Fragile)(:|\.)/g;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');

// `str`: the strength to show (hand and board strength can differ from the printed one); `cls`: extra classes.
export function cardHTML(c, { str = c.str, cls = '', attrs = '' } = {}) {
  const base = c.str === '*' ? null : c.str, delta = base !== null && str !== base ? (str > base ? ' up' : ' down') : '';
  return `<div class="card ${c.rarity} ${cls}" ${attrs}>` +
    `<div class="win"${hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)});background-position:50% ${focus(c.id).toFixed(0)}%"` : ''}>${hasArt(c.id) ? '' : `<span>${c.name}</span>`}</div>` +
    `<img class="frame" src="/static/kit/frame_${c.rarity}.webp" alt="" draggable="false">` +
    `<div class="cname">${c.name}</div><div class="cstr${delta}">${str}</div>` +
    `<div class="ctext">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
