// The collection, which is the deckbuilder. Every card is the card the match draws (mana.js), the grid and the deck sort
// by cost, with a row of costs and the strength, rarity and search filters over the grid. Click a card to add a copy,
// right-click it or click its strip to take one out; every change saves.
// app.js hands in what it owns: the cards, the player's decks and how to save them, toast, play, back.
import { fitNames, readSide } from './card.js';
import { CROP, stripArt, fitStrips, lazyArt } from './art.js';
import { encodeDeck, decodeDeck, deckOrder } from './deckcode.js';
import { onHold } from './menu.js';
import { track } from './log.js';
import { manaCard, manaPiece, fitPlaques, costChip, powerCard } from './mana.js';
import { hasFigure } from './token.js';
import { squareLook } from './board.js';

const RANK = { legendary: 0, common: 1 };
// The deck rules come from the server (/api/pool's rules: decks.py, engine/cards.py and web/profiles.py hold the numbers): the
// deck size, the copies a rarity allows, and the most decks a profile keeps.
let R = { deckSize: 25, copies: {} };   // until the server's arrive

const costOf = c => c.mana ?? 99;   // a card with no cost sorts last
// The cost row of the collection and the curve's bars: 1 to 6 and 7+ (Martin, 2026-11-21), the last taking every dearer card.
const MANA_COSTS = [1, 2, 3, 4, 5, 6, 7], TOP = 7;
const costKey = k => Math.min(Math.max(k, 1), TOP);
const plus = k => k === TOP ? '<sup>+</sup>' : '';
// A card in the grid, a pop or a dialog: the card with its cost. `w`: its width.
const face = (c, w, opts = {}) => (manaCard(c, { cost: c.mana ?? null, w }));
const fitAll = el => { fitNames(el); fitPlaques(el); };
// What keeps a deck from play under the rules, in plain words: copies over a card's limit, more cards than a deck holds (a
// deck saved under other rules keeps its list: it shows what is over and is fixed here). Too few cards is the caller's (the
// count shows it).
// '' for a playable deck. Home uses it too (app.js), to send such a deck here instead of into a match.
// Every deck has a leader (Martin, 2026-11-16): one of its own legendaries that can lead (`leaders`: the server's map).
export const NO_LEADER = 'Choose a leader', NO_LEADER_CARD = 'Add a legendary that can lead';
export function deckIssue(list, cards = C, rules = R, leader = null, leaders = (X && X.leaders) || {}) {
  const counts = countsOf(list);
  const over = Object.keys(counts).filter(id => cards[id] && counts[id] > rules.copies[cards[id].rarity]);
  if (over.length === 1) { const c = cards[over[0]], k = counts[over[0]] - rules.copies[c.rarity];
    return `${counts[over[0]]} ${c.name}: take out ${k === 1 ? 'one' : k}, ${rules.copies[c.rarity] === 1 ? 'one' : 'two'} at most`; }
  if (over.length) return `${over.length} cards have a copy too many`;
  if (list.length > rules.deckSize) return `${list.length} cards: take ${list.length - rules.deckSize} out, ${rules.deckSize} at most`;
  if (!(leader && list.includes(leader) && leaders[leader])) return list.some(id => leaders[id]) ? NO_LEADER : NO_LEADER_CARD;
  return '';
}
const sv = c => c.str === '*' ? -1 : c.str;
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const svg = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
export const ICON = {
  list: svg('<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>'),
  edit: svg('<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>'),
  search: svg('<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  addfriend: svg('<circle cx="10" cy="8" r="4"/><path d="M3 20c1.2-3.5 3.8-5.5 7-5.5 1.6 0 3 .5 4.2 1.4M18 13v6M15 16h6"/>'),
  copy: svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
};

// Copies as dots: filled for the copies in the deck; with `max`, hollow for the ones still allowed.
const pips = (n, max = n) => Array.from({ length: max }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('');

let X, C, cards, st = { open: null, rar: null, cost: '', q: '', sheet: false }, flash = null, wired = false;
const limit = c => R.copies[c.rarity];   // copies per deck: the rarity's (a card's starter count is the starter's business)
// A deck's cover is its leader (Martin, 2026-11-21: "it will automatically just be your Hero"); a deck without one shows
// its first legendary, else its first card (the play screen uses the same).
export const coverOf = (list, cards = C, leader = null) => (leader && cards[leader] ? leader : null)
  || list.find(id => cards[id] && cards[id].rarity === 'legendary') || list.find(id => cards[id]) || null;
// The cover on a deck's tile: its painting where it has one, else its figure at the tile's right end.
const coverAttrs = id => !id ? '' : CROP[id] ? ` data-strip="${id}" data-ax=".7" style="${stripArt(id, 284, 56, .7)}"`
  : hasFigure(id) ? ` style="background-image:url(/static/hex/fig/${id}.webp);background-repeat:no-repeat;background-size:auto 150%;background-position:right 10px top 30%"` : '';
const listOf = cardsObj => Object.entries(cardsObj).flatMap(([id, n]) => Array(n).fill(id));
const countsOf = list => list.reduce((o, id) => (o[id] = (o[id] || 0) + 1, o), {});

// Your decks, saved on your profile (which starts with the starter decks as its own), as {id, name, list, leader}.
const decks = () => X.getDecks().map(d => ({ id: d.id, name: d.name, list: listOf(d.cards), leader: d.leader || null }));
let saved = null;   // each deck's list as last saved: a save logs what changed (log.js)
function save(all) {
  // a leader goes with its card: one taken out of the deck takes the leader with it (the leaders prototype)
  X.saveDecks(all.map(d => ({ id: d.id, name: d.name, cards: countsOf(d.list), ...(d.leader && d.list.includes(d.leader) ? { leader: d.leader } : {}) })));
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
// The mana rules' strip: the cost in its gold hexagon, the piece's figure where the painting was, the name, and on the
// right a legendary's gem or the copies as dots; no strength (Martin, 2026-11-21: "keep only the little dots"), no stars.
export const stripHTML = (id, cards, have) => { const c = cards[id];
  return `<div class="st mst ${c.rarity}${have ? '' : ' gone'}${have > (R.copies[c.rarity] ?? 9) || c.mana == null ? ' over' : ''}" data-card="${id}">`
    + `<span class="sc">${c.mana != null ? costChip(c.mana) : ''}</span>`
    + `<span class="hd">${hasFigure(id) ? `<img src="/static/hex/fig/${id}.webp" alt="" draggable="false">` : ''}</span>`
    + `<span class="n">${esc(c.name)}</span><span class="x">${c.rarity === 'legendary' ? '<img class="lgem" src="/static/hex/gem.webp" alt="" draggable="false">' : have > 1 ? pips(have) : ''}</span></div>`; };
// A deck's strips, one list, in deckOrder (the legendaries first, their gold edge says so, then every other card by strength).
// `have(id)`: the copies a strip shows (a match's decklists: the copies left). `mana`: the mana rules' list, by cost first.
export const stripsHTML = (ids, cards, have) => { const by = deckOrder(cards);
  return `<div class="dbody flat">${[...ids].sort((a, b) => costOf(cards[a]) - costOf(cards[b]) || by(a, b)).map(id => stripHTML(id, cards, have(id))).join('')}</div>`; };
export function deckBody(list, cards) {
  const counts = countsOf(list);
  return stripsHTML(Object.keys(counts), cards, id => counts[id]);
}
// The deck's mana curve, as Hearthstone draws it (Martin, 2026-11-21, its "Cards/Mana Cost" chart): a gold bar per cost
// in a dark slot, 1 to 6 and 7+, its height the cost's share of the tallest, the count above it, the cost below.
const curveHTML = list => { const n = MANA_COSTS.map(() => 0);
  for (const id of list) { const k = C[id] && C[id].mana; if (k != null) n[costKey(k) - 1]++; }
  const top = Math.max(1, ...n);
  return `<div class="mcurve">${MANA_COSTS.map((k, i) => `<div class="cb${n[i] ? '' : ' zero'}"><div class="slot"><b>${n[i]}</b><i style="height:${(n[i] / top * 100).toFixed(1)}%"></i></div>`
    + `<span class="ck">${costChip(k)}${plus(k)}</span></div>`).join('')}</div>`; };

function render(app, all) {
  const keep = [...app.querySelectorAll('.clist, .cgrid')].map(e => e.scrollTop);
  if (st.was !== !!st.open) keep[1] = 0; st.was = !!st.open;   // switching list and deck starts the column at its top
  const open = all.find(d => d.id === st.open), counts = open ? countsOf(open.list) : {};
  const q = st.q.toLowerCase();
  // a search also matches the names of the cards a card makes: "bunny" finds the Rabbit (Martin, 2026-10-31: the token itself is never shown here, it isn't a card for a deck)
  const made = c => (c.related || []).map(id => (C[id] || {}).name || '').join(' ');
  const shown = cards.filter(c => (!st.rar || c.rarity === st.rar) && ((st.cost === '') || (c.mana != null && String(costKey(c.mana)) === st.cost))
    && (!q || (c.name + ' ' + c.text + ' ' + made(c)).toLowerCase().includes(q)))
    .sort((a, b) => ((costOf(a) - costOf(b))) || sv(a) - sv(b) || RANK[a.rarity] - RANK[b.rarity] || a.name.localeCompare(b.name));

  const grid = !shown.length ? `<div class="none"><p>No cards match</p><button class="quiet" id="clearf">Clear filters</button></div>`
    : '<div class="crow">' + shown.map(c => { const n = counts[c.id] || 0;
      // the mana rules show each card as its piece, with its cost; the full card opens on hover (Martin, 2026-11-20)
      const max = open && n >= limit(c);   // dimmed: every copy is in the deck (the card count and the stars show on their counters)
      return `<div class="tl${max ? ' max' : ''}" data-card="${c.id}">${(manaPiece(c, { cost: c.mana ?? null, w: 150 }))}${n && c.rarity !== 'legendary' ? `<span class="pips${n > limit(c) ? ' over' : ''}">${pips(n, Math.max(n, limit(c)))}</span>` : ''}</div>`; }).join('') + '</div>';

  // a row of costs to pick from, as Hearthstone's collection has (Martin, 2026-11-20)
  const tabs = (MANA_COSTS.map(n => `<div class="ctab${st.cost === String(n) ? ' on' : ''}" data-cost="${n}">${costChip(n)}${plus(n)}</div>`).join(''));
  // Heroes only: the legendaries, the cards that lead (Martin, 2026-11-21, in place of the strength and rarity menus)
  const head = `<div class="chead"><div class="tabs">${tabs}</div>
    <button class="slab chk${st.rar ? ' on' : ''}" id="fheroes" aria-pressed="${!!st.rar}"><i></i>Heroes only</button>
    <label class="searchw">${ICON.search}<input class="search field" id="q" placeholder="Search" value="${esc(st.q)}"></label></div>`;

  const body = d => ((curveHTML(d.list))) + deckBody(d.list, C);
  const tile = d => d.id === st.open
    ? `<div class="dtile on" data-d="${d.id}"${coverAttrs(coverOf(d.list, C, d.leader))}><b class="nm-edit" title="Rename">${esc(d.name)}</b>
        <div class="tacts"><button class="ic" id="dcopy" data-tip="Copy deck code">${ICON.copy}</button><button class="ic txt" id="dshare" data-tip="Copy a link to this deck">Share</button><button class="ic del" id="ddel" data-tip="Delete deck">${ICON.trash}</button></div></div>${leaderRow(d)}${body(d)}`
    // a deck still short of its cards is marked with its count, as on home's chooser (Martin, 2026-10-31)
    // a deck over the rules (copies, stars) says so on its tile: open it to see what (the stars prototype)
    : `<div class="dtile${d.list.length < R.deckSize || deckIssue(d.list, C, R, d.leader) ? ' short' : ''}" data-d="${d.id}"${coverAttrs(coverOf(d.list, C, d.leader))}><b>${esc(d.name)}</b>${d.list.length < R.deckSize ? `<span class="left">${d.list.length}/${R.deckSize}</span>` : (iss => !iss ? '' : `<span class="left">${iss === NO_LEADER || iss === NO_LEADER_CARD ? 'No leader' : /no mana cost/.test(iss) ? 'No cost' : 'Too many'}</span>`)(deckIssue(d.list, C, R, d.leader))}</div>`;
  // Two states, as in Hearthstone: your deck list (New deck is the slot after the last deck, Back in the foot), or one deck
  // being edited (only that deck; Play and Done in the foot).
  const issue = open && open.list.length >= R.deckSize ? deckIssue(open.list, C, R, open.leader) : '';
  const column = open
    ? `<div class="clist editing">${tile(open)}</div>
      <div class="sfoot"><button class="play" id="play"${open.list.length === R.deckSize && !issue ? '' : ' disabled'}>${issue || 'Play this deck'}</button>
        <div class="frow"><div class="fcount${('')}"><span class="fc"><b>${open.list.length}/${R.deckSize}</b><span>Cards</span></span></div>${FB}<button class="backbtn" id="done"><span>Done</span></button></div></div>`
    : `<div class="clist">${all.map(tile).join('')}${all.length < R.decksMax ? `<button class="dnew" id="dnew" data-tip="New deck" aria-label="New deck">${ICON.plus}</button>` : ''}</div>
      <div class="sfoot"><div class="frow"><div class="fcount"><b>${all.length}/${R.decksMax}</b><span>Decks</span></div>${FB}<button class="backbtn" id="back"><span>Back</span></button></div></div>`;

  app.innerHTML = `<div class="coll mscr">${head}<div class="cgrid">${grid}</div><div class="side${st.sheet ? ' up' : ''}"><button class="grip" id="grip" aria-label="Decks"></button>${column}</div><div class="modal" id="cmodal"></div></div>`;
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
  $('fheroes').onclick = () => { st.rar = st.rar ? null : 'legendary'; redo(); };
  const q = $('q'); q.oninput = () => { st.q = q.value; const at = q.selectionStart; redo(); const n = app.querySelector('#q'); n.focus(); n.setSelectionRange(at, at); };
  app.querySelectorAll('[data-cost]').forEach(e => e.onclick = () => { st.cost = st.cost === e.dataset.cost ? '' : e.dataset.cost; redo(); });   // one cost at a time; again: every cost
  const cf = $('clearf'); if (cf) cf.onclick = () => { Object.assign(st, { rar: null, str: '', cost: '', q: '' }); redo(); };
  app.querySelectorAll('[data-d]').forEach(e => e.onclick = ev => { if (ev.target.closest('.nm-edit, .tacts, .nm-in')) return; if (!st.open) { st.open = e.dataset.d; st.sheet = false; redo(); } });

  const nm = app.querySelector('.nm-edit');
  if (nm) nm.onclick = () => { const inp = document.createElement('input'); inp.className = 'nm-in'; inp.maxLength = 40; inp.value = open.name; nm.replaceWith(inp); inp.focus(); inp.select();
    let gone = false; const done = keep => { if (gone) return; gone = true; const name = inp.value.trim();
      if (keep && name) open.name = name.slice(0, 40);
      change(); };
    inp.onblur = () => done(true); inp.onkeydown = k => { if (k.key === 'Enter') done(true); if (k.key === 'Escape') { k.stopPropagation(); done(false); } }; };
  const cp = $('dcopy'); if (cp) cp.onclick = () => navigator.clipboard.writeText(encodeDeck(open.name, open.list, C)).then(() => X.toast('Deck code copied', true), () => X.toast('Could not copy'));
  const shr = $('dshare'); if (shr) shr.onclick = () => X.share(encodeDeck(open.name, open.list, C), open.name);
  const ld = $('dlead'); if (ld) ld.onclick = () => hidePop() || pickLeader(app, open, id => { setLeader(open, id); change(); });
  const del = $('ddel'); if (del) del.onclick = () => confirmDelete(app, open, () => { all.splice(all.indexOf(open), 1); st.open = null; change(); X.toast(`Deleted ${open.name}`, true); });
  // A new deck starts with its leader, as in Gwent (Martin, 2026-11-17): the leader is chosen first, its card is the deck's
  // first, and the deck opens with its name ready to type. Cancelled, no deck is made.
  const dn = $('dnew'); if (dn) dn.onclick = () => pickLeader(app, null, id => { const d = { id: Date.now().toString(36), name: 'New deck', list: [id], leader: id };
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

  // Click a card to add a copy; a refused add says why. Right-click a card, or click its strip, to take one out.
  app.querySelectorAll('.cgrid [data-card]').forEach(e => {
    e.onclick = () => { const c = C[e.dataset.card];
      if (!open && matchMedia('(hover: none)').matches) { hidePop(); return zoom(app, c); }   // touch, browsing: a tap reads it
      if (!open) return X.toast(`Open a deck ${portrait() ? 'below' : 'on the right'} to build it`);
      const n = open.list.filter(x => x === c.id).length;
      const why = open.list.length >= R.deckSize ? 'tot' : n >= limit(c) ? 'pips' : null;
      if (why) return refuse(app, e, why, c);
      open.list.push(c.id); hidePop(); flash = c.id; change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); });   // touch: hold to read it large
  });
  app.querySelectorAll('.side [data-card]').forEach(e => { e.onclick = () => {
      if (e.dataset.card === open.leader) return X.toast(`${C[open.leader].name.split(':')[0]} leads this deck: choose another leader to take the card out`);
      open.list.splice(open.list.indexOf(e.dataset.card), 1); hidePop(); change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); }); });
  const fl = flash && [...app.querySelectorAll(`.side .st[data-card="${flash}"]`)].at(-1); flash = null;
  if (fl) { fl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); fl.classList.add('flash'); }

  // Hovering a card or a strip shows the full card, beside it and clear of the deck column. Only the pointer moving opens
  // it: a scroll slides cards under a still pointer, so it closes the card and none opens until the pointer moves again
  // (the browser's own move after a scroll carries no movement).
  const side = app.querySelector('.side')?.getBoundingClientRect().left ?? innerWidth;
  let on = null;
  const show = e => { on = e; const r = e.getBoundingClientRect(), inSide = !!e.closest('.side');
    const pw = powerOf(C[e.dataset.card]);
    pop.className = 'pop' + (pw ? ' ldr' : '') + ((' mcoll')); pop.innerHTML = face(C[e.dataset.card], 230) + pw; pop.style.display = 'flex'; fitPlaques(pop);
    const w = pop.offsetWidth, h = pop.offsetHeight;
    // a strip of the deck: the card left of the whole deck column, clear of every strip's cost (Martin, 2026-11-21)
    pop.style.left = (inSide ? e.closest('.side').getBoundingClientRect().left - w - 14 : r.right + 10 + w > side ? r.left - w - 10 : r.right + 10) + 'px';
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
// a leader's abilities as one line: "Passive. ... Hero power: ..."
const abilities = L => [L.passive && `Passive. ${L.passive}`, L.power && `Hero power: ${L.power}`].filter(Boolean).join(' ');
const leaderIds = () => Object.keys(X.leaders || {}).filter(id => C[id] && C[id].status === 'collectible');   // each ruleset its own leaders
// In the mana rules the plate alone: the card beside it already shows the animal, and the orb is the old painting's.
const powerHTML = (id, D = 150) => { const L = X.leaders[id];
  return `<div class="hpow${(' bare')}">${('')}<div class="plate">${L.passive ? `<b>Passive</b><p>${esc(L.passive)}</p>` : ''}${L.power ? `<b>Hero power</b><p>${esc(L.power)}</p>` : ''}</div></div>`; };
// beside a legendary in the collection (in a match the card is just a card)
// a leader's power as a card beside the leader's, as a card's tokens are (Martin, 2026-11-21)
const powerOf = (c, w = 170) => (X.leaders || {})[c.id] && c.status === 'collectible' ? powerCard(c.id, X.leaders[c.id], w) : '';
function setLeader(d, id) {
  if (d.leader === id) return;
  if (d.leader) { const i = d.list.indexOf(d.leader); if (i >= 0) d.list.splice(i, 1); }
  if (!d.list.includes(id)) d.list.push(id);
  d.leader = id;
}
function leaderRow(d) {
  const id = d.leader && d.list.includes(d.leader) && (X.leaders || {})[d.leader] ? d.leader : null, L = id && X.leaders[id];
  return `<div class="lrow${id ? '' : ' none'}" id="dlead">${id ? (squareLook() ? `<div class="lpc lfig"><img src="/static/hex/fig/${id}.webp" alt="" draggable="false"></div>` : `<div class="lpc">${manaPiece(C[id], { str: null, w: 50 })}</div>`) : `<div class="lmed empty"></div>`}`
    + `<div class="ltx">${id ? `<b>${esc(C[id].name.split(':')[0])}</b><span>${esc(abilities(L))}</span>` : `<b>No leader</b><span>Choose a leader for this deck</span>`}</div></div>`;
}
// `d`: the deck whose leader changes, or null for a new deck.
function pickLeader(app, d, done) {
  const cur = d && d.leader;
  const { m, close } = dialog(app, `<div class="dlg cov ldr"><h3>Choose a leader</h3><div class="leads">${leaderIds().map(id => `<div class="lv${id === cur ? ' on' : ''}" data-id="${id}"><div class="cv">${face(C[id], 110, { cls: 'compact' })}</div>${powerHTML(id, 96)}</div>`).join('')}</div>
    <div class="dbtns"><button class="cancel">Cancel</button></div></div>`); fitAll(m);
  m.querySelectorAll('.lv').forEach(e => e.onclick = () => { close(); done(e.dataset.id); });
}

// Screen-wide keys and paste, live only while the collection is on screen.
function wireGlobal() {
  const here = () => document.querySelector('.coll'), typing = e => /INPUT|SELECT|TEXTAREA/.test(e.target.tagName);
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
    const all = decks(), nd = { id: Date.now().toString(36), name: d.name, list: d.list };
    const can = [...new Set(d.list)].filter(id => (X.leaders || {})[id]); if (can.length === 1) nd.leader = can[0];   // the one leader it can have
    all.push(nd); st.open = nd.id; save(all);
    render(here().parentElement, all); X.toast(`Imported ${nd.name}`, true);
  });
}
