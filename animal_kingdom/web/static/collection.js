// The collection, which is the deckbuilder (design sandbox builder/notes.md, round B2). The card grid on the left with the
// family, strength, rarity and search filters over it; the decks on the right, the open one unfolded under its tile.
// Click a card to add a copy, right-click it or click its strip to take one out; every change saves.
// app.js hands in what it owns: the cards, the starter decks, the player's decks and how to save them, toast, play, back.
import { fitNames, readSide, markGlyphs, LABEL } from './card.js';
import { CROP, stripArt, fitStrips, lazyArt } from './art.js';
import { encodeDeck, decodeDeck, deckOrder } from './deckcode.js';
import { dd, wireDd, onHold } from './menu.js';
import { track } from './log.js';
import { manaCard, manaPiece, fitPlaques, costChip } from './mana.js';
import { hasFigure } from './token.js';

const RANK = { legendary: 0, rare: 1, common: 2 };
// The deck rules come from the server (/api/pool's rules: decks.py, engine/cards.py and web/profiles.py hold the numbers): the
// deck size, the copies a rarity allows, the stars prototype's budget (a card's level, c.stars, counted per copy), and the
// most decks a profile keeps.
let R = { deckSize: 25, copies: {}, starBudget: 0 };   // until the server's arrive
// The mana ruleset's deck builder (the prototype of 2026-11-20; app.js hands in `mana` and that ruleset's deck rules): every
// card is the mana card (mana.js, the one the match draws), the grid and the deck sort by cost first, a filter by cost
// takes the stars' place, the deck shows how many cards it has at each cost, and the rules are the mana deck rules (no
// star budget; a card with no mana cost is not legal). The default ruleset's screen is unchanged.

const costOf = c => c.mana ?? 99;   // a card with no cost sorts last
const MANA_COSTS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];   // the cost row of the mana collection
// The open deck in the mana rules, two ways (Martin, 2026-11-20: he wanted to try the deck as board tiles, and named the side
// list cleaned up as the other way; neither is settled): `tray`, a band of pieces under the grid (the default), or `list`,
// the side column's strips. ?deckview=list or ?deckview=tray on the address switches, kept in the browser like ?rules.
const DECKVIEW = (() => { const q = typeof location === 'undefined' ? null : new URLSearchParams(location.search).get('deckview');
  try { if (q) localStorage.setItem('ak:deckview', q === 'list' ? 'list' : 'tray'); return localStorage.getItem('ak:deckview') === 'list' ? 'list' : 'tray'; }
  catch { return q === 'list' ? 'list' : 'tray'; } })();
const tray = () => (DECKVIEW === 'tray');
// A card in the grid, a pop or a dialog: the mana card with its cost, or the rectangular card. `w`: the mana card's width.
const face = (c, w, opts = {}) => (manaCard(c, { cost: c.mana ?? null, w }));
const fitAll = el => { fitNames(el); fitPlaques(el); };
const starsOf = list => list.reduce((n, id) => n + (C[id].stars | 0), 0);
// What keeps a deck from play under the rules, in plain words: copies over a card's limit, more cards than a deck holds (a
// deck saved under the old rules, three copies and 30 cards, keeps its list: it shows what is over and is fixed here), too
// many stars. Too few cards is the caller's (the count shows it).
// '' for a playable deck. Home uses it too (app.js), to send such a deck here instead of into a match.
// Every deck has a leader (Martin, 2026-11-16): one of its own legendaries that can lead (`leaders`: the server's map).
export const NO_LEADER = 'Choose a leader', NO_LEADER_CARD = 'Add a legendary that can lead';
export function deckIssue(list, cards = C, rules = R, leader = null, leaders = (X && X.leaders) || {}) {
  const counts = countsOf(list);
  const over = Object.keys(counts).filter(id => cards[id] && counts[id] > rules.copies[cards[id].rarity]);
  const stars = rules.starBudget == null ? 0 : list.reduce((n, id) => n + ((cards[id] || {}).stars | 0), 0) - rules.starBudget;   // the mana rules: no star budget
  if (over.length === 1) { const c = cards[over[0]], k = counts[over[0]] - rules.copies[c.rarity];
    return `${counts[over[0]]} ${c.name}: take out ${k === 1 ? 'one' : k}, ${rules.copies[c.rarity] === 1 ? 'one' : 'two'} at most`; }
  if (over.length) return `${over.length} cards have a copy too many`;
  if (list.length > rules.deckSize) return `${list.length} cards: take ${list.length - rules.deckSize} out, ${rules.deckSize} at most`;
  if (stars > 0) return LABEL.five ? `${stars} over the ${shown5(rules.starBudget, rules.deckSize)}` : `${stars} star${stars > 1 ? 's' : ''} over the ${rules.starBudget}`;
  if (!(leader && list.includes(leader) && leaders[leader])) return list.some(id => leaders[id]) ? NO_LEADER : NO_LEADER_CARD;
  return '';
}
// The other labelling (Martin wants to feel which is easier): every card numbered 1 to 5, its level + 2, and the budget shifted
// to match (the budget + 2 per card). Display only: the rule underneath is the same.
const shown5 = (stars, cards) => stars + 2 * cards;
try { LABEL.five = localStorage.getItem('ak:five') === '1'; } catch { /* no storage */ }
const sv = c => c.str === '*' ? -1 : c.str;
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const svg = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
export const ICON = {
  list: svg('<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>'),
  edit: svg('<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>'),
  search: svg('<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  addfriend: svg('<circle cx="10" cy="8" r="4"/><path d="M3 20c1.2-3.5 3.8-5.5 7-5.5 1.6 0 3 .5 4.2 1.4M18 13v6M15 16h6"/>'),
  image: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>'),
  copy: svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
};

// Copies as dots: filled for the copies in the deck; with `max`, hollow for the ones still allowed.
const pips = (n, max = n) => Array.from({ length: max }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('');

let X, C, cards, st = { open: null, families: new Set(), rar: null, hab: '', str: '', lvl: '', cost: '', q: '', sheet: false }, flash = null, wired = false;
const limit = c => R.copies[c.rarity];   // copies per deck: the rarity's (a card's starter count is the starter's business)
// A deck's cover until its player chooses one: its first legendary with a head crop (the play screen uses the same).
export const coverOf = (list, cards = C) => list.find(id => cards[id].rarity === 'legendary' && CROP[id]) || list.find(id => CROP[id]) || 'lion';
const listOf = cardsObj => Object.entries(cardsObj).flatMap(([id, n]) => Array(n).fill(id));
const countsOf = list => list.reduce((o, id) => (o[id] = (o[id] || 0) + 1, o), {});

// Your decks, saved on your profile (which starts with the starter decks as its own), as {id, name, list, cover}.
function decks() {
  const mine = X.getDecks().map(d => ({ id: d.id, name: d.name, list: listOf(d.cards), cover: d.cover && C[d.cover] ? d.cover : null, leader: d.leader || null }));
  mine.forEach(d => d.cover = d.cover || (d.list.length ? coverOf(d.list) : null));
  return mine;
}
let saved = null;   // each deck's list as last saved: a save logs what changed (log.js)
function save(all) {
  // a leader goes with its card: one taken out of the deck takes the leader with it (the leaders prototype)
  X.saveDecks(all.map(d => ({ id: d.id, name: d.name, cards: countsOf(d.list), cover: d.cover, ...(d.leader && d.list.includes(d.leader) ? { leader: d.leader } : {}) })));
  const now = Object.fromEntries(all.map(d => [d.id, [...d.list]]));
  if (saved) for (const d of all) {
    const was = saved[d.id] || [], rest = [...was], added = [];
    for (const c of d.list) { const i = rest.indexOf(c); if (i >= 0) rest.splice(i, 1); else added.push(c); }
    if (added.length || rest.length || !saved[d.id]) track('deck_change', { deck: d.id, name: d.name, size: d.list.length, added, removed: rest });
  }
  for (const id in saved || {}) if (!now[id]) track('deck_deleted', { deck: id });
  saved = now;
}

// Feedback beside Back (or Done) while the game is in testing: the side panel holds the screen's edge, where home has its tab.
const FB = '<button class="backbtn fbx" data-tip="Feedback" aria-label="Feedback"><img class="tic" src="/static/kit2/top/feedback.webp" alt="" draggable="false"></button>';
export function collectionScreen(app, ctx) {
  X = ctx; C = ctx.cards; if (ctx.rules) R = ctx.rules;
  if (!saved) saved = Object.fromEntries(decks().map(d => [d.id, [...d.list]]));
  cards = Object.values(C).filter(c => c.status === 'collectible');   // the starters' cards and the bench; each ruleset its own collection (the mana prototype holds only the Wisps)
  if (!wired) { wired = true; wireGlobal(); }
  const all = decks();
  // Opens your first deck; with none yet, nothing is open and the grid is for browsing.
  if (ctx.open) st.open = ctx.open;   // arriving from the play screen with a deck to open
  if (st.open !== null && !all.some(d => d.id === st.open)) st.open = null;   // the screen opens on your deck list
  render(app, all);
}

// A deck's strips by rarity, the capped rarities with their counts: the open deck here, the decklist on the play screen.
// Strips are slivers of the cards: strength on a driftwood plaque, the name, copies as dots (legendaries have one).
// One strip: a sliver of the card; the number of copies at its end when there are two or more (the game's decklists: copies
// left), as in Hearthstone. A strip with none left is marked gone.
// `mana`: the mana rules' strip (mstripHTML).
export const stripHTML = (id, cards, have, mana = false) => mana ? mstripHTML(id, cards, have) : `<div class="st ${cards[id].rarity}${have ? '' : ' gone'}${have > (R.copies[cards[id].rarity] ?? 9) || mana && cards[id].mana == null ? ' over' : ''}" data-card="${id}"><div class="art" data-strip="${id}" data-ax=".55" style="${stripArt(id, 166, 30, .55)}"></div>${mana ? `<span class="sc">${cards[id].mana != null ? costChip(cards[id].mana) : ''}</span>` : ''}<span class="s">${String(cards[id].str).split('').map(d => `<img src="/static/kit2/chalk/${d}.webp" alt="${d}">`).join('')}</span><span class="n">${esc(cards[id].name)}</span>${markGlyphs(cards[id], 'lvs')}<span class="x">${have > 1 ? have : ''}</span></div>`;
// The mana rules' strip: the cost in its gold hexagon, the piece's figure where the painting was, the name, the strength
// in the piece's own numerals; two copies are two dots, so a row holds two numbers, not three (Martin, 2026-11-20: "it's
// like holding three different numbers in one row"). No stars.
const numImg = n => /^\d+$/.test(String(n)) && +n <= 20 ? `<img src="/static/hex/num/${n}.svg" alt="${n}" draggable="false">` : esc(n);
const mstripHTML = (id, cards, have) => { const c = cards[id];
  return `<div class="st mst ${c.rarity}${have ? '' : ' gone'}${have > (R.copies[c.rarity] ?? 9) || c.mana == null ? ' over' : ''}" data-card="${id}">`
    + `<span class="sc">${c.mana != null ? costChip(c.mana) : ''}</span>`
    + `<span class="hd">${hasFigure(id) ? `<img src="/static/hex/fig/${id}.webp" alt="" draggable="false">` : ''}</span>`
    + `<span class="n">${esc(c.name)}</span><span class="ms">${numImg(c.str)}</span><span class="x">${have > 1 ? pips(have) : ''}</span></div>`; };
// A deck's strips, one list, in deckOrder (the legendaries first, their gold edge says so, then every other card by strength).
// `have(id)`: the copies a strip shows (a match's decklists: the copies left). `mana`: the mana rules' list, by cost first.
export const stripsHTML = (ids, cards, have, mana = false) => { const by = deckOrder(cards);
  return `<div class="dbody flat">${[...ids].sort(mana ? (a, b) => costOf(cards[a]) - costOf(cards[b]) || by(a, b) : by).map(id => stripHTML(id, cards, have(id), mana)).join('')}</div>`; };
export function deckBody(list, cards, mana = false) {
  const counts = countsOf(list);
  return stripsHTML(Object.keys(counts), cards, id => counts[id], mana);
}
// The mana rules' curve: how many of the deck's cards cost 0 to 10 (a plain count, the lead session's default for the
// prototype, not something Martin asked for).
const curveHTML = list => { const n = {}; for (const id of list) { const k = C[id] && C[id].mana; n[k] = (n[k] || 0) + 1; }
  return `<div class="mcurve">${MANA_COSTS.map(k => `<span class="${n[k] ? '' : 'zero'}">${costChip(k)}<b>${n[k] || 0}</b></span>`).join('')}</div>`; };

// The deck as a tray of pieces (DECKVIEW 'tray'): the leader as one large piece at the left, then a cell for each of the
// deck's cards in two interlocking rows of board tiles, every copy its own piece, filled in cost order and zig-zagging
// between the rows (cell i in row i % 2), so each cost is a run of pieces; a crack the width of .4 of a piece parts one
// cost from the next, and a count under each run says how many it holds. The cells not yet filled are empty outlines
// after the last run, so the tray shows how full the deck is. Every measure is in the piece's width `w`, chosen for the
// window: as wide as fits 25 cells and six cracks across, and no taller than the window can spare.
const SIDE_W = 250, PAD = 24, GAP = 22, PH = 1.15556;   // the controls' width; the tray's edges; between its parts; a piece's height
export function trayGeo(W, H, n = 25, cracks = 6) {
  const most = Math.max(48, Math.min(84, H * .085));
  let w = most;
  for (let k = 0; k < 4; k++) w = Math.min(most, (W - 2 * PAD - 1.75 * w - 2 * GAP - SIDE_W) / ((n - 1) * .53 + 1 + .4 * cracks));
  w = Math.floor(w);
  const h = w * PH, gap = Math.max(2, Math.round(w * .06));
  return { w, h, p: w + gap, dy: .75 * h + gap * .866, crack: Math.round(w * .4), lead: Math.round(1.75 * w) };
}
const HEX_SVG = `<svg viewBox="0 0 100 ${100 * PH}" preserveAspectRatio="none"><polygon vector-effect="non-scaling-stroke" points="50,1 99,${25 * PH} 99,${75 * PH} 50,${100 * PH - 1} 1,${75 * PH} 1,${25 * PH}"/></svg>`;
function trayHTML(d) {
  const leader = d.leader && d.list.includes(d.leader) && (X.leaders || {})[d.leader] ? d.leader : null;
  const by = deckOrder(C), ids = [...d.list].filter(id => C[id]).sort((a, b) => costOf(C[a]) - costOf(C[b]) || by(a, b));
  const n = Math.max(R.deckSize, ids.length), runs = [];
  for (const id of ids) { const k = costOf(C[id]); if (!runs.length || runs.at(-1).k !== k) runs.push({ k, ids: [] }); runs.at(-1).ids.push(id); }
  if (ids.length < n) runs.push({ k: null, ids: Array(n - ids.length).fill(null) });
  const g = trayGeo(innerWidth, innerHeight, n);   // room for every crack, so the pieces keep their size as the deck fills
  let i = 0, x0 = 0, cells = '', counts = '';
  const seen = {}, over = id => (seen[id] = (seen[id] || 0) + 1) > (R.copies[C[id].rarity] ?? 9) || (false);   // a copy past its limit, or a card the rules refuse: marked
  runs.forEach((r, ri) => { if (ri) x0 += g.crack; const first = i;
    for (const id of r.ids) { const at = `left:${(i * g.p / 2 + x0).toFixed(1)}px;top:${(i % 2 * g.dy).toFixed(1)}px;width:${g.w}px;height:${g.h.toFixed(1)}px`;
      cells += id ? `<div class="cell${id === leader ? ' lcopy' : ''}${over(id) ? ' over' : ''}" data-card="${id}" style="${at}">${manaPiece(C[id], { cost: C[id].mana ?? null, w: g.w })}</div>`
        : `<div class="cell empty" style="${at}">${HEX_SVG}</div>`;
      i++; }
    });   // no count under a cost's run: the pieces are there to count (Martin, 2026-11-20)
  const combW = (i - 1) * g.p / 2 + x0 + g.w, combH = g.dy + g.h;
  const lead = leader ? `<div class="tlead" id="dlead" data-card="${leader}" style="width:${g.lead}px">${manaPiece(C[leader], { str: null, w: g.lead })}</div>`
    : `<div class="tlead none" id="dlead" style="width:${g.lead}px;height:${(g.lead * PH).toFixed(1)}px">${HEX_SVG}<span>Choose a leader</span></div>`;
  return `<div class="tleads" style="height:${combH.toFixed(1)}px">${lead}</div><div class="comb" style="width:${combW.toFixed(1)}px;height:${(combH + 26).toFixed(1)}px">${cells}${counts}</div>`;
}

function render(app, all) {
  const keep = [...app.querySelectorAll('.clist, .cgrid')].map(e => e.scrollTop);
  if (st.was !== !!st.open) keep[1] = 0; st.was = !!st.open;   // switching list and deck starts the column at its top
  const open = all.find(d => d.id === st.open), counts = open ? countsOf(open.list) : {};
  const q = st.q.toLowerCase();
  // a search also matches the names of the cards a card makes: "bunny" finds the Rabbit (Martin, 2026-10-31: the token itself is never shown here, it isn't a card for a deck)
  const made = c => (c.related || []).map(id => (C[id] || {}).name || '').join(' ');
  const shown = cards.filter(c => (!st.families.size || c.tags.some(t => st.families.has(t))) && (!st.rar || c.rarity === st.rar) && (!st.hab || c.habitat === st.hab) && (st.str === '' || (st.str === '8+' ? c.str >= 8 : String(c.str) === st.str)) && (true) && ((st.cost === '') || String(c.mana) === st.cost)
    && (!q || (c.name + ' ' + c.text + ' ' + c.tags.join(' ') + ' ' + made(c)).toLowerCase().includes(q)))
    .sort((a, b) => ((costOf(a) - costOf(b))) || sv(a) - sv(b) || RANK[a.rarity] - RANK[b.rarity] || a.name.localeCompare(b.name));

  const grid = !shown.length ? `<div class="none"><p>No cards match</p><button class="quiet" id="clearf">Clear filters</button></div>`
    : '<div class="crow">' + shown.map(c => { const n = counts[c.id] || 0;
      // the mana rules show each card as its piece, with its cost; the full card opens on hover (Martin, 2026-11-20)
      const max = open && n >= limit(c);   // dimmed: every copy is in the deck (the card count and the stars show on their counters)
      return `<div class="tl${max ? ' max' : ''}" data-card="${c.id}">${(manaPiece(c, { cost: c.mana ?? null, w: 150 }))}${n && c.rarity !== 'legendary' ? `<span class="pips${n > limit(c) ? ' over' : ''}">${pips(n, Math.max(n, limit(c)))}</span>` : ''}</div>`; }).join('') + '</div>';

  // the mana rules: a row of costs to pick from, as Hearthstone's collection has, in place of the animal families (Martin, 2026-11-20)
  const tabs = (MANA_COSTS.map(n => `<div class="ctab${st.cost === String(n) ? ' on' : ''}" data-cost="${n}">${costChip(n)}</div>`).join(''));
  const strengths = [...Array(8).keys()].map(String).concat('8+');
  // the levels the collection's cards have, highest first (no level is offered that no card has)
  const levels = [...new Set(cards.map(c => c.stars | 0))].sort((a, b) => b - a);
  const lvlName = v => LABEL.five ? `Number ${v + 2}` : v === 0 ? 'No stars' : v === 1 ? '1 star' : `${v} stars`;   // 0 to 7, then 8 and up together: few animals are 8 or more (Martin, 2026-10-30)
  const head = `<div class="chead"><div class="tabs">${tabs}</div>
    ${dd('str', st.str, [['', 'Any strength'], ...strengths.map(v => [v, 'Strength ' + v])])}
    ${dd('rar', st.rar || '', [['', 'All cards'], ['legendary', 'Legendary']])}
    ${('')}
    ${('')}
    <label class="searchw">${ICON.search}<input class="search field" id="q" placeholder="Search" value="${esc(st.q)}"></label></div>`;

  const body = d => ((curveHTML(d.list))) + deckBody(d.list, C, true);
  const tile = d => d.id === st.open
    ? `<div class="dtile on" data-d="${d.id}"${d.cover ? ` data-strip="${d.cover}" data-ax=".7"` : ''} style="${d.cover ? stripArt(d.cover, 284, 56, .7) : ''}"><b class="nm-edit" title="Rename">${esc(d.name)}</b>
        <div class="tacts"><button class="ic" id="dcover" data-tip="Change cover">${ICON.image}</button><button class="ic" id="dcopy" data-tip="Copy deck code">${ICON.copy}</button><button class="ic txt" id="dshare" data-tip="Copy a link to this deck">Share</button><button class="ic del" id="ddel" data-tip="Delete deck">${ICON.trash}</button></div></div>${leaderRow(d)}${body(d)}`
    // a deck still short of its cards is marked with its count, as on home's chooser (Martin, 2026-10-31)
    // a deck over the rules (copies, stars) says so on its tile: open it to see what (the stars prototype)
    : `<div class="dtile${d.list.length < R.deckSize || deckIssue(d.list, C, R, d.leader) ? ' short' : ''}" data-d="${d.id}"${d.cover ? ` data-strip="${d.cover}" data-ax=".7"` : ''} style="${d.cover ? stripArt(d.cover, 284, 56, .7) : ''}"><b>${esc(d.name)}</b>${d.list.length < R.deckSize ? `<span class="left">${d.list.length}/${R.deckSize}</span>` : (iss => !iss ? '' : `<span class="left">${iss === NO_LEADER || iss === NO_LEADER_CARD ? 'No leader' : /no mana cost/.test(iss) ? 'No cost' : 'Too many'}</span>`)(deckIssue(d.list, C, R, d.leader))}</div>`;
  // Two states, as in Hearthstone: your deck list (New deck is the slot after the last deck, Back in the foot), or one deck
  // being edited (only that deck; Play and Done in the foot).
  // The deck's stars beside its cards, read the same way; over the budget, it turns red and Play says by how much.
  const stars = open ? starsOf(open.list) : 0, over = Math.max(0, stars - R.starBudget), issue = open && open.list.length >= R.deckSize ? deckIssue(open.list, C, R, open.leader) : '';
  // One sunken count holds both (the foot is 300 px): the cards, then the stars; a click on the stars switches the labelling.
  const starCount = !open || true ? '' : `<span class="fc fstars${over ? ' over' : ''}" id="fstars" data-tip="${LABEL.five ? 'Count in stars' : 'Count 1 to 5 instead'}">`
    + (LABEL.five ? `<b>${shown5(stars, open.list.length)}/${shown5(R.starBudget, R.deckSize)}</b><span>Points</span>` : `<b>${stars}/${R.starBudget}</b><span>Stars</span>`) + '</span>';
  const column = open
    ? `<div class="clist editing">${tile(open)}</div>
      <div class="sfoot"><button class="play" id="play"${open.list.length === R.deckSize && !issue ? '' : ' disabled'}>${issue || 'Play this deck'}</button>
        <div class="frow"><div class="fcount${('')}"><span class="fc"><b>${open.list.length}/${R.deckSize}</b><span>Cards</span></span>${starCount}</div>${FB}<button class="backbtn" id="done"><span>Done</span></button></div></div>`
    : `<div class="clist">${all.map(tile).join('')}${all.length < R.decksMax ? `<button class="dnew" id="dnew" data-tip="New deck" aria-label="New deck">${ICON.plus}</button>` : ''}</div>
      <div class="sfoot"><div class="frow"><div class="fcount"><b>${all.length}/${R.decksMax}</b><span>Decks</span></div>${FB}<button class="backbtn" id="back"><span>Back</span></button></div></div>`;

  // The tray (mana rules, a deck open): the deck under the grid, its name, count, Play and Done at its right end; the side
  // column is for choosing a deck only.
  const ctl = open && `<div class="tside"><div class="tname"><b class="nm-edit" title="Rename">${esc(open.name)}</b><span class="tacts"><button class="ic" id="dcopy" data-tip="Copy deck code">${ICON.copy}</button><button class="ic txt" id="dshare" data-tip="Copy a link to this deck">Share</button><button class="ic del" id="ddel" data-tip="Delete deck">${ICON.trash}</button></span></div>
      <button class="play" id="play"${open.list.length === R.deckSize && !issue ? '' : ' disabled'}>${issue || 'Play this deck'}</button>
      <div class="frow"><div class="fcount"><span class="fc"><b>${open.list.length}/${R.deckSize}</b><span>Cards</span></span></div>${FB}<button class="backbtn" id="done"><span>Done</span></button></div></div>`;
  app.innerHTML = open && tray()
    ? `<div class="coll mscr trayed">${head}<div class="cgrid">${grid}</div><div class="mtray">${trayHTML(open)}${ctl}</div><div class="modal" id="cmodal"></div></div>`
    : `<div class="coll mscr">${head}<div class="cgrid">${grid}</div><div class="side${st.sheet ? ' up' : ''}"><button class="grip" id="grip" aria-label="Decks"></button>${column}</div><div class="modal" id="cmodal"></div></div>`;
  lazyArt(app.querySelector('.cgrid'));
  fitStrips(app);   // the deck tiles are as wide as the column (upright, the window)
  app.querySelectorAll('.clist, .cgrid').forEach((e, i) => { if (keep[i] != null) e.scrollTop = keep[i]; });
  fitAll(app);
  wire(app, all, open);
}

const portrait = () => matchMedia('(orientation: portrait)').matches;

// The deck list reorders by dragging a tile (Martin, 2026-10-26): with a mouse, press and move; on a touch screen, hold a
// moment first, so a plain swipe still scrolls the list. The tile lifts and follows the pointer, the others make room as
// it passes their middles, and letting go saves the new order. A drag never opens the deck it moved.
function reorder(app, all, change) {
  const list = app.querySelector('.clist'); if (!list) return;
  let drag = null, held = null, moved = false;
  const tiles = () => [...list.querySelectorAll('.dtile')];
  const start = (t, y) => { drag = { t, y0: y, top0: t.offsetTop }; moved = true; t.classList.add('lift'); list.classList.add('sorting'); };
  const move = y => {
    const { t } = drag; t.style.transform = `translateY(${y - drag.y0 - (t.offsetTop - drag.top0)}px)`;
    const mid = t.getBoundingClientRect().top + t.offsetHeight / 2;
    for (const o of tiles()) { if (o === t) continue; const r = o.getBoundingClientRect();
      if (mid > r.top && mid < r.bottom) { const after = mid > r.top + r.height / 2; o[after ? 'after' : 'before'](t);
        t.style.transform = `translateY(${y - drag.y0 - (t.offsetTop - drag.top0)}px)`; break; } }
    const lr = list.getBoundingClientRect();   // near an edge of a long list, it scrolls under the tile
    if (y < lr.top + 30) list.scrollTop -= 8; else if (y > lr.bottom - 30) list.scrollTop += 8;
  };
  const end = () => { clearTimeout(held); held = null; if (!drag) return;
    const order = tiles().map(e => e.dataset.d); drag.t.classList.remove('lift'); drag.t.style.transform = ''; list.classList.remove('sorting'); drag = null;
    if (order.join() !== all.map(d => d.id).join()) { all.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id)); change(); } };
  for (const t of tiles()) {
    t.addEventListener('mousedown', e => { if (e.button !== 0) return; moved = false; const y0 = e.clientY;
      const mm = ev => { if (!drag && Math.abs(ev.clientY - y0) > 6) start(t, y0); if (drag) { ev.preventDefault(); move(ev.clientY); } };
      const mu = () => { removeEventListener('mousemove', mm); removeEventListener('mouseup', mu); end(); };
      addEventListener('mousemove', mm); addEventListener('mouseup', mu); });
    t.addEventListener('touchstart', e => { moved = false; const y = e.touches[0].clientY; held = setTimeout(() => { held = null; start(t, y); navigator.vibrate?.(10); }, 350); }, { passive: true });
    t.addEventListener('touchmove', e => { if (drag) { e.preventDefault(); move(e.touches[0].clientY); } else { clearTimeout(held); held = null; } }, { passive: false });
    t.addEventListener('touchend', end); t.addEventListener('touchcancel', end);
    t.addEventListener('click', e => { if (moved) { e.stopImmediatePropagation(); e.preventDefault(); moved = false; } }, true);
    t.addEventListener('contextmenu', e => { if (drag || held) e.preventDefault(); });
  }
}

function wire(app, all, open) {
  const $ = id => app.querySelector('#' + id), redo = () => render(app, all), change = () => { save(all); redo(); };
  const pop = document.getElementById('pop'), hidePop = () => { pop.style.display = 'none'; };
  const bk = $('back'); if (bk) bk.onclick = X.back;
  app.querySelectorAll('.fbx').forEach(b => b.onclick = X.feedback);
  wireDd(app, (k, v) => { st[k] = k === 'rar' ? (v || null) : v; redo(); });
  const q = $('q'); q.oninput = () => { st.q = q.value; const at = q.selectionStart; redo(); const n = app.querySelector('#q'); n.focus(); n.setSelectionRange(at, at); };
  app.querySelectorAll('[data-cost]').forEach(e => e.onclick = () => { st.cost = st.cost === e.dataset.cost ? '' : e.dataset.cost; redo(); });   // one cost at a time; again: every cost
  app.querySelectorAll('[data-t]').forEach(e => e.onclick = () => { const f = e.dataset.t; st.families.has(f) ? st.families.delete(f) : st.families.add(f); redo(); });   // toggles; none chosen shows every family
  const cf = $('clearf'); if (cf) cf.onclick = () => { Object.assign(st, { families: new Set(), rar: null, hab: '', str: '', lvl: '', cost: '', q: '' }); redo(); };
  app.querySelectorAll('[data-d]').forEach(e => e.onclick = ev => { if (ev.target.closest('.nm-edit, .tacts, .nm-in')) return; if (!st.open) { st.open = e.dataset.d; st.sheet = false; redo(); } });

  const nm = app.querySelector('.nm-edit');
  if (nm) nm.onclick = () => { const inp = document.createElement('input'); inp.className = 'nm-in'; inp.maxLength = 40; inp.value = open.name; nm.replaceWith(inp); inp.focus(); inp.select();
    let gone = false; const done = keep => { if (gone) return; gone = true; const name = inp.value.trim();
      if (keep && name) open.name = name.slice(0, 40);
      change(); };
    inp.onblur = () => done(true); inp.onkeydown = k => { if (k.key === 'Enter') done(true); if (k.key === 'Escape') { k.stopPropagation(); done(false); } }; };
  const cp = $('dcopy'); if (cp) cp.onclick = () => navigator.clipboard.writeText(encodeDeck(open.name, open.list, C)).then(() => X.toast('Deck code copied', true), () => X.toast('Could not copy'));
  const shr = $('dshare'); if (shr) shr.onclick = () => X.share(encodeDeck(open.name, open.list, C), open.name);
  const cov = $('dcover'); if (cov) cov.onclick = () => pickCover(app, open, id => { open.cover = id; change(); });
  const ld = $('dlead'); if (ld) ld.onclick = () => hidePop() || pickLeader(app, open, id => { setLeader(open, id); change(); });
  const del = $('ddel'); if (del) del.onclick = () => confirmDelete(app, open, () => { all.splice(all.indexOf(open), 1); st.open = null; change(); X.toast(`Deleted ${open.name}`, true); });
  // A new deck starts with its leader, as in Gwent (Martin, 2026-11-17): the leader is chosen first, its card is the deck's
  // first, and the deck opens with its name ready to type. Cancelled, no deck is made.
  const dn = $('dnew'); if (dn) dn.onclick = () => pickLeader(app, null, id => { const d = { id: Date.now().toString(36), name: 'New deck', list: [id], cover: null, leader: id };
    all.push(d); st.open = d.id; st.sheet = false; st.rename = true; change(); });
  const dn2 = $('done'); if (dn2) dn2.onclick = () => { st.open = null; st.sheet = true; redo(); };
  if (!open) reorder(app, all, change);
  // Upright the deck column is a sheet along the bottom: shut, the cards take the screen. Its grip drags it with the finger
  // and lets go to the nearer state (a flick goes its way); a tap on the grip or on the count opens or shuts it.
  const sh = app.querySelector('.side'), g = $('grip');
  if (g) {
  const heights = () => { const was = sh.classList.contains('up'); sh.style.height = '';
    sh.classList.remove('up'); const lo = sh.offsetHeight; sh.classList.add('up'); const hi = sh.offsetHeight;
    sh.classList.toggle('up', was); return [lo, hi]; };
  const settle = (to, [lo, hi] = heights()) => { const from = sh.offsetHeight, h = to ? hi : lo;
    sh.classList.add('up'); sh.style.height = from + 'px'; void sh.offsetHeight;
    const done = () => { st.sheet = to; redo(); };
    if (Math.abs(from - h) < 2) return done();
    sh.style.transition = 'height .22s ease-out'; sh.style.height = h + 'px'; sh.addEventListener('transitionend', done, { once: true }); };
  const sheet = () => settle(!st.sheet);
  let drag = null, tapped = false;
  g.onpointerdown = e => { tapped = false; const hs = heights(), h0 = sh.offsetHeight;
    sh.classList.add('up'); sh.style.transition = 'none'; sh.style.height = h0 + 'px'; fitStrips(app);   // measured now they show
    drag = { hs, h0, y0: e.clientY, y: e.clientY, t: e.timeStamp, v: 0, h: h0 }; g.setPointerCapture(e.pointerId); };
  g.onpointermove = e => { if (!drag) return; const [lo, hi] = drag.hs;
    drag.v = (e.clientY - drag.y) / Math.max(1, e.timeStamp - drag.t); drag.y = e.clientY; drag.t = e.timeStamp;
    drag.h = Math.max(lo, Math.min(hi, drag.h0 - (e.clientY - drag.y0))); sh.style.height = drag.h + 'px'; };
  g.onpointerup = e => { if (!drag) return; const d = drag; drag = null; const [lo, hi] = d.hs;
    if (Math.abs(e.clientY - d.y0) < 8) { tapped = true; return settle(!st.sheet, d.hs); }   // a tap (its click is swallowed below)
    if (e.timeStamp - d.t > 100) d.v = 0;   // held still before letting go: not a flick
    settle(Math.abs(d.v) > .4 ? d.v < 0 : d.h > (lo + hi) / 2, d.hs); };
  g.onpointercancel = () => { if (drag) { const d = drag; drag = null; settle(st.sheet, d.hs); } };
  g.onclick = () => { if (tapped) tapped = false; else sheet(); };
  const fc = app.querySelector('.fcount'); if (fc && portrait()) fc.onclick = sheet;
  }
  if (st.rename) { st.rename = false; const n = app.querySelector('.nm-edit'); if (n) n.click(); }
  const play = $('play'); if (play && !play.disabled) play.onclick = () => X.play(open);
  const fs = $('fstars'); if (fs) fs.onclick = ev => { ev.stopPropagation(); LABEL.five = !LABEL.five; try { localStorage.setItem('ak:five', LABEL.five ? '1' : '0'); } catch { /* no storage */ } st.lvl = ''; redo(); };

  // Click a card to add a copy; a refused add says why. Right-click a card, or click its strip, to take one out.
  app.querySelectorAll('.cgrid [data-card]').forEach(e => {
    e.onclick = () => { const c = C[e.dataset.card];
      if (!open && matchMedia('(hover: none)').matches) { hidePop(); return zoom(app, c); }   // touch, browsing: a tap reads it
      if (!open) return X.toast(`Open a deck ${portrait() ? 'below' : 'on the right'} to build it`);
      const n = open.list.filter(x => x === c.id).length, lv = c.stars | 0, left = R.starBudget == null ? Infinity : R.starBudget - starsOf(open.list);
      const why = open.list.length >= R.deckSize ? 'tot' : n >= limit(c) ? 'pips' : (lv > 0 && lv > left ? 'stars' : null);
      if (why) return refuse(app, e, why, c);
      open.list.push(c.id); hidePop(); flash = c.id; change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); });   // touch: hold to read it large
  });
  app.querySelectorAll('.side [data-card], .mtray .cell[data-card]').forEach(e => { e.onclick = () => {
      if (e.dataset.card === open.leader) return X.toast(`${C[open.leader].name.split(':')[0]} leads this deck: choose another leader to take the card out`);
      open.list.splice(open.list.indexOf(e.dataset.card), 1); hidePop(); change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); }); });
  const fl = flash && [...app.querySelectorAll(`.side .st[data-card="${flash}"], .mtray .cell[data-card="${flash}"]`)].at(-1); flash = null;
  if (fl) { if (fl.closest('.side')) fl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); fl.classList.add('flash'); }
  const tl = app.querySelector('.mtray .tlead'); if (tl && tl.dataset.card) onHold(tl, () => { hidePop(); zoom(app, C[tl.dataset.card]); });

  // Hovering a card or a strip shows the full card, beside it and clear of the deck column. Only the pointer moving opens
  // it: a scroll slides cards under a still pointer, so it closes the card and none opens until the pointer moves again
  // (the browser's own move after a scroll carries no movement).
  const side = app.querySelector('.side')?.getBoundingClientRect().left ?? innerWidth, trayTop = app.querySelector('.mtray')?.getBoundingClientRect().top;
  let on = null;
  const show = e => { on = e; const r = e.getBoundingClientRect(), inSide = !!e.closest('.side');
    const pw = powerOf(C[e.dataset.card]);
    pop.className = 'pop' + (pw ? ' ldr' : '') + ((' mcoll')); pop.innerHTML = face(C[e.dataset.card], 230) + pw; pop.style.display = 'flex'; fitPlaques(pop);
    const w = pop.offsetWidth, h = pop.offsetHeight;
    if (e.closest('.mtray')) {   // a piece in the tray: its card above the tray, centred on it, covering none of the tray
      pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
      pop.style.top = Math.max(8, trayTop - h - 6) + 'px'; return; }
    pop.style.left = (inSide || r.right + 10 + w > side ? r.left - w - 10 : r.right + 10) + 'px';
    pop.style.top = Math.max(8, Math.min(r.top - 40, innerHeight - h - 10)) + 'px'; };
  const root = app.querySelector('.coll');
  root.onmousemove = ev => { if (!ev.movementX && !ev.movementY) return;
    const e = ev.target.closest('[data-card]'); if (e === on) return;
    if (e) show(e); else { on = null; hidePop(); } };
  root.onmouseleave = () => { on = null; hidePop(); };
  root.addEventListener('scroll', () => { if (on) { on = null; hidePop(); } }, { capture: true, passive: true });
}

// A refused add: the card shakes and the limit that stopped it flashes (the deck total, the copy dots or a rarity count).
function refuse(app, el, why, c) {
  const again = (e, cls) => { if (!e) return; e.classList.remove(cls); void e.offsetWidth; e.classList.add(cls); };
  again(el, 'shake');
  if (why === 'tot') { again(app.querySelector('.fcount'), 'shake'); X.toast('The deck is full: take a card out first'); }
  else if (why === 'pips') again(el.querySelector('.pips'), 'flash');
  else if (why === 'cost') X.toast(`${c.name} has no mana cost, so no mana deck can hold it`);
  else if (why === 'stars') { again(app.querySelector('#fstars'), 'shake');
    const left = Math.max(0, R.starBudget - starsOf(st.open ? decks().find(d => d.id === st.open).list : []));
    const n = v => LABEL.five ? `${v}` : `${v} star${v === 1 ? '' : 's'}`;
    X.toast(LABEL.five ? `${c.name} is a ${(c.stars | 0) + 2}, and the deck has room for ${left} more: take a card out first`
      : `${c.name} needs ${n(c.stars | 0)}, and the deck has ${left} left of its ${R.starBudget}: take a starred card out first`); }
}

// Dialogs: Cancel, Escape or a click outside close them.
function dialog(app, html) {
  const m = app.querySelector('#cmodal'); m.innerHTML = html; m.classList.add('on');
  const close = () => { m.classList.remove('on'); removeEventListener('keydown', key, true); };
  const key = e => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  addEventListener('keydown', key, true);
  m.onclick = e => { if (e.target === m) close(); };
  m.querySelector('.cancel').onclick = close;
  return { m, close };
}
// Right-click a card: it opens large in the middle of the screen, read left to right and top to bottom: the card, then
// the cards it makes in the order they come (Hearthstone's related cards), then each keyword on any of them explained
// (as in Hearthstone, Arena and Runeterra). Escape, a click or another right-click closes it.
function zoom(app, c) {
  const m = app.querySelector('#cmodal'); m.classList.add('on', 'zoom');
  const side = readSide(c, C, (r => manaCard(r, { cost: r.mana ?? null, w: 170 })));
  m.innerHTML = `<div class="zbox">${face(c, 300)}${powerOf(c)}${side}</div>`;
  fitAll(m);
  const close = () => { m.classList.remove('on', 'zoom'); m.innerHTML = ''; removeEventListener('keydown', key, true); };
  const key = e => { if (e.key === 'Escape') { e.stopPropagation(); close(); } };
  addEventListener('keydown', key, true);
  m.onclick = close; m.oncontextmenu = e => { e.preventDefault(); close(); };
}

function confirmDelete(app, d, done) {
  const { m, close } = dialog(app, `<div class="dlg"><h3>Delete “${esc(d.name)}”?</h3><p>This can’t be undone. Copy its deck code first if you might want it back.</p>
    <div class="dbtns"><button class="cancel">Cancel</button><button class="danger">Delete deck</button></div></div>`);
  m.querySelector('.cancel').focus();
  m.querySelector('.danger').onclick = () => { close(); done(); };
}
// A deck's leader: a legendary that can lead, which every deck has (Martin, 2026-11-16), chosen when the deck is made
// (2026-11-17). Its card is in the deck while it leads: choosing another leader swaps the cards, and the leader's own strip
// stays put. The row shows the leader with its ability; a click picks another.
const KIND = { power: 'Hero power', once: 'Once per game', passive: 'Always on' };
const leaderIds = () => Object.keys(X.leaders || {}).filter(id => C[id] && C[id].status === 'collectible');   // each ruleset its own leaders
// In the mana rules the plate alone: the card beside it already shows the animal, and the orb is the old painting's.
const powerHTML = (id, D = 150) => { const L = X.leaders[id];
  return `<div class="hpow${(' bare')}">${('')}<div class="plate"><b>${KIND[L.kind]}</b><p>${esc(L.text)}</p></div></div>`; };
// beside a legendary in the collection (in a match the card is just a card)
const powerOf = c => (X.leaders || {})[c.id] && c.status === 'collectible' ? powerHTML(c.id) : '';
function setLeader(d, id) {
  if (d.leader === id) return;
  if (d.leader) { const i = d.list.indexOf(d.leader); if (i >= 0) d.list.splice(i, 1); }
  if (!d.list.includes(id)) d.list.push(id);
  d.leader = id;
}
function leaderRow(d) {
  const id = d.leader && d.list.includes(d.leader) && (X.leaders || {})[d.leader] ? d.leader : null, L = id && X.leaders[id];
  return `<div class="lrow${id ? '' : ' none'}" id="dlead">${id ? ((`<div class="lpc">${manaPiece(C[id], { str: null, w: 50 })}</div>`)) : `<div class="lmed empty"></div>`}`
    + `<div class="ltx">${id ? `<b>${esc(C[id].name.split(':')[0])}</b><span>${KIND[L.kind]}. ${esc(L.text)}</span>` : `<b>No leader</b><span>Choose a leader for this deck</span>`}</div></div>`;
}
// `d`: the deck whose leader changes, or null for a new deck.
function pickLeader(app, d, done) {
  const cur = d && d.leader;
  const { m, close } = dialog(app, `<div class="dlg cov ldr"><h3>Choose a leader</h3><div class="leads">${leaderIds().map(id => `<div class="lv${id === cur ? ' on' : ''}" data-id="${id}"><div class="cv">${face(C[id], 110, { cls: 'compact' })}</div>${powerHTML(id, 96)}</div>`).join('')}</div>
    <div class="dbtns"><button class="cancel">Cancel</button></div></div>`); fitAll(m);
  m.querySelectorAll('.lv').forEach(e => e.onclick = () => { close(); done(e.dataset.id); });
}

function pickCover(app, d, done) {
  const ids = [...new Set(d.list)].filter(id => CROP[id]).sort(deckOrder(C));
  const { m, close } = dialog(app, `<div class="dlg cov"><h3>Choose a cover</h3><div class="covs">${ids.map(id => `<div class="cv${id === d.cover ? ' on' : ''}" data-id="${id}">${face(C[id], 140, { cls: 'compact' })}</div>`).join('')}</div>
    <div class="dbtns"><button class="cancel">Cancel</button></div></div>`); fitAll(m);
  m.querySelectorAll('.cv').forEach(e => e.onclick = () => { close(); done(e.dataset.id); });
}

// Screen-wide keys and paste, live only while the collection is on screen.
function wireGlobal() {
  const here = () => document.querySelector('.coll'), typing = e => /INPUT|SELECT|TEXTAREA/.test(e.target.tagName);
  // the tray's pieces are measured for the window: a new size draws it again
  let rs = null;
  addEventListener('resize', () => { clearTimeout(rs); rs = setTimeout(() => { const h = here(); if (h && h.classList.contains('trayed') && !h.querySelector('.modal.on')) render(h.parentElement, decks()); }, 120); });
  addEventListener('keydown', e => {
    if (!here() || here().querySelector('.modal.on')) return;
    if (e.key === '/' && !typing(e)) { e.preventDefault(); here().querySelector('#q').focus(); }
    else if (e.key === 'Escape' && !typing(e)) { const done = here().querySelector('#done'); done ? done.click() : X.back(); }   // Done while editing, else Back
  });
  // Paste a deck code (or a plain "3x Lion" list) anywhere: it becomes your deck, open.
  addEventListener('paste', e => {
    if (!here() || typing(e)) return;
    const d = decodeDeck(e.clipboardData.getData('text'), C);
    if (!d) return X.toast('That is not a deck code');
    if (decks().length >= R.decksMax) return X.toast(`${R.decksMax} decks is the most you can keep: delete one first`);
    const all = decks(), nd = { id: Date.now().toString(36), name: d.name, list: d.list, cover: coverOf(d.list) };
    const can = [...new Set(d.list)].filter(id => (X.leaders || {})[id]); if (can.length === 1) nd.leader = can[0];   // the one leader it can have
    all.push(nd); st.open = nd.id; save(all);
    render(here().parentElement, all); X.toast(`Imported ${nd.name}`, true);
  });
}
