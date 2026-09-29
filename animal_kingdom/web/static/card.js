// The one card (design sandbox card2/, Martin 2026-09-29): the painting fills the card inside a rarity edge (graphite,
// silver, gold); a painted driftwood bar holds the name, a painted banner the strength in chalk digits, a driftwood panel
// the rules and family. `compact` drops the panel (hand and collection show the painting; the full card shows on hover).
// Size it with the CSS variable --w on .card (everything inside scales with it).
import { hasArt, artUrl, CROP } from './art.js';

// The full card shows the painting between the name bar and the rules panel: about 61% of its height, so it centres on
// the animal (the portrait crop's centre height) instead of the painting's top; the compact card shows ~88% from the top.
const VIS = 0.61;
const focus = id => { const y = CROP[id] ? CROP[id][1] : 0.35; return Math.max(0, Math.min(1, (y - VIS / 2) / (1 - VIS))) * 100; };

// Every keyword that opens a sentence is bold ("Flight. Roar: ..." bolds both).
const KW = /(?<=^|\. )(Roar|Immovable|Flight|Stealth|Apex Predator)(:|\.)/g;
const rules = t => (t || '').replace(KW, '<b>$1$2</b>');
const chalk = n => String(n).split('').map(d => d === '*' ? '<b>*</b>' : `<img src="/static/kit2/chalk/${d}.webp" alt="${d}" draggable="false">`).join('');

// `str`: the strength to show (hand strength can differ from the printed one); `cls`: extra classes ('compact').
// The name is centred in the bar; a longer name sets smaller in proportion to its length (--n), one over 18 characters may wrap.
export function cardHTML(c, { str = c.str, cls = '', attrs = '' } = {}) {
  const base = c.str === '*' ? null : c.str, delta = base !== null && str !== base ? (str > base ? ' up' : ' down') : '';
  const art = hasArt(c.id) ? ` style="background-image:url(${artUrl(c.id)});--fy:${focus(c.id).toFixed(0)}%"` : '';
  return `<div class="card ${c.rarity} ${cls}" ${attrs}><div class="pic"${art}>${hasArt(c.id) ? '' : `<span>${c.name}</span>`}</div>` +
    `<div class="nbar${c.name.length > 18 ? ' two' : ''}" style="--n:${c.name.length}"><span>${c.name}</span></div>` +
    `<div class="stab"><span class="n${String(str).length > 1 ? ' two' : ''}${delta}">${chalk(str)}</span></div>` +
    `<div class="ctext">${c.text ? `<p>${rules(c.text)}</p>` : ''}<i>${c.tags.join(' · ')}</i></div></div>`;
}
