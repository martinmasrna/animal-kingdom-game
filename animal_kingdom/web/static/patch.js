// Patch notes (static/patches/, built by tools/patch/build.py): what changed for a player since the last patch. The rules
// as a list of Martin's words, then the cards: hero powers and changed cards as before -> after pairs, split by what
// changed (effect, mana, strength), then new and removed cards side by side (design sandbox ak-converge/patch-notes).
import { manaCard, powerCostHTML, fitPlaques } from './mana.js';
import { fitNames } from './card.js';
import { FIGS } from './hex/figs.js';

let INDEX = null;   // the patches' versions, newest first
export async function patches() {
  if (!INDEX) INDEX = await fetch('/static/patches/index.json').then(r => r.ok ? r.json() : []).catch(() => []);
  return INDEX;
}
export const newestPatch = async () => (await patches())[0] || null;

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const W = 150;
function card(c) {
  if (c.fig && !FIGS[c.id]) FIGS[c.id] = c.fig;   // a removed card: its figure is kept, its size travels with the patch
  if (!c.power) return manaCard({ ...c, tags: [] }, { cost: c.mana, w: W, str: c.str });
  const h = manaCard({ ...c, tags: [] }, { cost: null, w: W, str: null });   // a hero power: its mana in the drawer, as in the game
  return c.mana != null ? h.replace(/(<div class="mpiece[^>]*>)/, `$1${powerCostHTML(c.mana)}`) : h;
}
const power = L => ({ id: L.id, name: L.kind === 'power' ? 'Hero power' : 'Passive', rarity: 'common', str: null, text: L.text, kw: [], power: true, mana: L.mana });
const pair = p => `<div class="pair">${card(p.was)}<i class="arrow"></i>${card(p.now)}</div>`;
const kind = p => p.was.text !== p.now.text ? 'rework' : p.was.mana !== p.now.mana ? 'mana' : 'str';

export function patchHTML(P) {
  const groups = [['Hero powers', P.powers.map(p => ({ was: power(p.was), now: power(p.now) }))],
    ...[['rework', 'Reworked'], ['mana', 'Mana cost'], ['str', 'Strength']].map(([k, t]) => [t, P.changed.filter(p => kind(p) === k)])];
  const changed = groups.filter(([, ps]) => ps.length).map(([t, ps]) => `<h3>${t}</h3><div class="pairs">${ps.map(pair).join('')}</div>`).join('');
  return `<h1>${esc(P.name)}</h1><div class="date">${esc(P.date)}</div>`
    + (P.rules.length ? `<h2>Rules</h2><ul class="rules">${P.rules.map(r => `<li>${esc(r)}</li>`).join('')}</ul>` : '')
    + (changed ? `<h2>Changed</h2>${changed}` : '')
    + (P.added.length ? `<h2>New</h2><div class="row">${P.added.map(c => `<div>${card(c)}</div>`).join('')}</div>` : '')
    + (P.removed.length ? `<h2>Removed</h2><div class="row">${P.removed.map(c => `<div class="gone">${card(c)}</div>`).join('')}</div>` : '');
}

// The screen: one patch (the newest unless `version` names one), Back to home. Opening the newest marks it seen.
export async function patchScreen(app, { version, back, seen }) {
  const list = await patches(), v = version && list.includes(version) ? version : list[0];
  const P = v && await fetch(`/static/patches/${v}.json`).then(r => r.ok ? r.json() : null).catch(() => null);
  app.innerHTML = `<div class="mscr patch"><div class="pscroll"><div class="pcol">${P ? patchHTML(P) : '<h1>Patch notes</h1>'}</div></div>`
    + `<div class="pfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div>`;
  fitNames(app); fitPlaques(app);
  app.querySelector('#back').onclick = back;
  if (P && v === list[0]) seen(v);
}
