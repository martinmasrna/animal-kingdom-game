// The collection, which is the deckbuilder (design sandbox builder/notes.md, round B2). The card grid on the left with the
// family, strength, rarity and search filters over it; the decks on the right, the open one unfolded under its tile.
// Click a card to add a copy, right-click it or click its strip to take one out; every change saves.
// app.js hands in what it owns: the cards, the starter decks, the player's decks and how to save them, toast, play, back.
import { cardHTML, fitNames, KEYWORDS } from './card.js';
import { CROP, artUrl, stripArt, fitStrips, lazyArt } from './art.js';
import { encodeDeck, decodeDeck } from './deckcode.js';
import { dd, wireDd, onHold } from './menu.js';

// Each family's medallion: the card whose animal reads clearest at 40 px (chosen side by side at that size).
const FAMILIES = [['Cat', 'lion'], ['Canine', 'clarion'], ['Rodent', 'chinchilla'], ['Colony', 'worker_bee'], ['Bird', 'andean_condor'],
  ['Snake', 'viper'], ['Bear', 'polar_bear'], ['Megafauna', 'elephant'], ['Lizard', 'chameleon']];
const DECKS_MAX = 20;   // as the server's profiles.DECKS_MAX
const RANK = { legendary: 0, rare: 1, common: 2 }, LIMIT = { legendary: 1, rare: 2, common: 3 }, CAP = { legendary: 4, rare: 8 };
const sv = c => c.str === '*' ? -1 : c.str;
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const svg = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
export const ICON = {
  list: svg('<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>'),
  edit: svg('<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>'),
  search: svg('<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  image: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>'),
  copy: svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
};

// A round head crop of the card art, M px across (CROP: centre x, centre y, diameter as fractions of width, height, width).
const med = (id, M) => { const [cx, cy, D] = CROP[id], w = M / D, h = w * 1.5;
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${M / 2 - cx * w}px ${M / 2 - cy * h}px`; };
// Copies as dots: filled for the copies in the deck; with `max`, hollow for the ones still allowed.
const pips = (n, max = n) => Array.from({ length: max }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('');

let X, C, cards, st = { open: null, families: new Set(), rar: null, str: '', q: '', sheet: false }, flash = null, wired = false;
const limit = c => c.copies || LIMIT[c.rarity];
// A deck's cover until its player chooses one: its first legendary with a head crop (the play screen uses the same).
export const coverOf = (list, cards = C) => list.find(id => cards[id].rarity === 'legendary' && CROP[id]) || list.find(id => CROP[id]) || 'lion';
const listOf = cardsObj => Object.entries(cardsObj).flatMap(([id, n]) => Array(n).fill(id));
const countsOf = list => list.reduce((o, id) => (o[id] = (o[id] || 0) + 1, o), {});

// Your decks, saved on your profile (which starts with the starter decks as its own), as {id, name, list, cover}.
function decks() {
  const mine = X.getDecks().map(d => ({ id: d.id, name: d.name, list: listOf(d.cards), cover: d.cover && C[d.cover] ? d.cover : null }));
  mine.forEach(d => d.cover = d.cover || (d.list.length ? coverOf(d.list) : null));
  return mine;
}
function save(all) {
  X.saveDecks(all.map(d => ({ id: d.id, name: d.name, cards: countsOf(d.list), cover: d.cover })));
}

export function collectionScreen(app, ctx) {
  X = ctx; C = ctx.cards;
  const starterIds = new Set(ctx.starters.map(d => d.id));
  cards = Object.values(C).filter(c => starterIds.has(c.deck) || c.deck === 'bench');   // the bench: cleared cards in no starter
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
export const stripHTML = (id, cards, have) => `<div class="st ${cards[id].rarity}${have ? '' : ' gone'}" data-card="${id}"><div class="art" style="${stripArt(id, 166, 30, .55)}"></div><span class="s">${String(cards[id].str).split('').map(d => `<img src="/static/kit2/chalk/${d}.webp" alt="${d}">`).join('')}</span><span class="n">${esc(cards[id].name)}</span><span class="x">${have > 1 ? have : ''}</span></div>`;
// flat: one list in the same order (rarity, then strength) without the group labels (home's chooser); each strip keeps its rarity edge.
export function deckBody(list, cards, caps = true, flat = false) {
  const counts = countsOf(list), inR = r => list.filter(id => cards[id].rarity === r).length;
  const strip = id => stripHTML(id, cards, counts[id]);
  const rhead = (label, r, cap) => `<h4 class="rh" data-r="${r}"><span>${label}</span>${cap && caps ? `<span>${inR(r)}/${cap}</span>` : ''}</h4>`;
  const byR = r => Object.keys(counts).filter(id => cards[id].rarity === r).sort((a, b) => sv(cards[a]) - sv(cards[b]) || cards[a].name.localeCompare(cards[b].name)).map(strip).join('');
  if (flat) return `<div class="dbody flat">${Object.keys(counts).sort((a, b) => RANK[cards[a].rarity] - RANK[cards[b].rarity] || sv(cards[a]) - sv(cards[b]) || cards[a].name.localeCompare(cards[b].name)).map(strip).join('')}</div>`;
  return `<div class="dbody">${rhead('Legendary', 'legendary', 4)}${byR('legendary')}${rhead('Rare', 'rare', 8)}${byR('rare')}${rhead('Common', 'common')}${byR('common')}</div>`;
}

function render(app, all) {
  const keep = [...app.querySelectorAll('.clist, .cgrid')].map(e => e.scrollTop);
  if (st.was !== !!st.open) keep[1] = 0; st.was = !!st.open;   // switching list and deck starts the column at its top
  const open = all.find(d => d.id === st.open), counts = open ? countsOf(open.list) : {};
  const q = st.q.toLowerCase();
  const shown = cards.filter(c => (!st.families.size || c.tags.some(t => st.families.has(t))) && (!st.rar || c.rarity === st.rar) && (st.str === '' || (st.str === '9+' ? c.str >= 9 : String(c.str) === st.str))
    && (!q || (c.name + ' ' + c.text + ' ' + c.tags.join(' ')).toLowerCase().includes(q)))
    .sort((a, b) => sv(a) - sv(b) || RANK[a.rarity] - RANK[b.rarity] || a.name.localeCompare(b.name));

  const grid = !shown.length ? `<div class="none"><p>No cards match</p><button class="quiet" id="clearf">Clear filters</button></div>`
    : '<div class="crow">' + shown.map(c => { const n = counts[c.id] || 0;
      const max = open && n >= limit(c);   // dimmed: every copy is in the deck (the 30 and the rarity caps show on their counters)
      return `<div class="tl${max ? ' max' : ''}" data-card="${c.id}">${cardHTML(c, { cls: 'compact', lazy: true })}${n && c.rarity !== 'legendary' ? `<span class="pips">${pips(n, limit(c))}</span>` : ''}</div>`; }).join('') + '</div>';

  const tabs = FAMILIES.map(([f, id]) => `<div class="tab${st.families.has(f) ? ' on' : ''}" data-t="${f}" data-tip="${f}"><div class="med" style="${med(id, 36)}"></div></div>`).join('');
  const strengths = [...Array(9).keys()].map(String).concat('9+');   // 0 to 8, then 9 and up together (Hearthstone's 7+)
  const head = `<div class="chead"><div class="tabs">${tabs}</div>
    ${dd('str', st.str, [['', 'Any strength'], ...strengths.map(v => [v, 'Strength ' + v])])}
    ${dd('rar', st.rar || '', [['', 'Any rarity'], ['legendary', 'Legendary'], ['rare', 'Rare'], ['common', 'Common']])}
    <label class="searchw">${ICON.search}<input class="search field" id="q" placeholder="Search" value="${esc(st.q)}"></label></div>`;

  const body = d => deckBody(d.list, C);
  const tile = d => d.id === st.open
    ? `<div class="dtile on" data-d="${d.id}"${d.cover ? ` data-strip="${d.cover}" data-ax=".7"` : ''} style="${d.cover ? stripArt(d.cover, 284, 56, .7) : ''}"><b class="nm-edit" title="Rename">${esc(d.name)}</b>
        <div class="tacts"><button class="ic" id="dcover" data-tip="Change cover">${ICON.image}</button><button class="ic" id="dcopy" data-tip="Copy deck code">${ICON.copy}</button><button class="ic del" id="ddel" data-tip="Delete deck">${ICON.trash}</button></div></div>${body(d)}`
    : `<div class="dtile" data-d="${d.id}"${d.cover ? ` data-strip="${d.cover}" data-ax=".7"` : ''} style="${d.cover ? stripArt(d.cover, 284, 56, .7) : ''}"><b>${esc(d.name)}</b></div>`;
  // Two states, as in Hearthstone: your deck list (New deck is the slot after the last deck, Back in the foot), or one deck
  // being edited (only that deck; Play and Done in the foot).
  const column = open
    ? `<div class="clist editing">${tile(open)}</div>
      <div class="sfoot"><button class="play" id="play"${open.list.length === 30 ? '' : ' disabled'}>Play this deck</button>
        <div class="frow"><div class="fcount"><b>${open.list.length}/30</b><span>Cards</span></div><button class="backbtn" id="done"><span>Done</span></button></div></div>`
    : `<div class="clist">${all.map(tile).join('')}${all.length < DECKS_MAX ? `<button class="dnew" id="dnew" data-tip="New deck" aria-label="New deck">${ICON.plus}</button>` : ''}</div>
      <div class="sfoot"><div class="frow"><div class="fcount"><b>${all.length}/${DECKS_MAX}</b><span>Decks</span></div><button class="backbtn" id="back"><span>Back</span></button></div></div>`;

  app.innerHTML = `<div class="coll mscr">${head}<div class="cgrid">${grid}</div><div class="side${st.sheet ? ' up' : ''}"><button class="grip" id="grip" aria-label="Decks"></button>${column}</div><div class="modal" id="cmodal"></div></div>`;
  lazyArt(app.querySelector('.cgrid'));
  fitStrips(app);   // the deck tiles are as wide as the column (upright, the window)
  app.querySelectorAll('.clist, .cgrid').forEach((e, i) => { if (keep[i] != null) e.scrollTop = keep[i]; });
  fitNames(app);
  wire(app, all, open);
}

const portrait = () => matchMedia('(orientation: portrait)').matches;

function wire(app, all, open) {
  const $ = id => app.querySelector('#' + id), redo = () => render(app, all), change = () => { save(all); redo(); };
  const pop = document.getElementById('pop'), hidePop = () => { pop.style.display = 'none'; };
  const bk = $('back'); if (bk) bk.onclick = X.back;
  wireDd(app, (k, v) => { st[k] = k === 'rar' ? (v || null) : v; redo(); });
  const q = $('q'); q.oninput = () => { st.q = q.value; const at = q.selectionStart; redo(); const n = app.querySelector('#q'); n.focus(); n.setSelectionRange(at, at); };
  app.querySelectorAll('[data-t]').forEach(e => e.onclick = () => { const f = e.dataset.t; st.families.has(f) ? st.families.delete(f) : st.families.add(f); redo(); });   // toggles; none chosen shows every family
  const cf = $('clearf'); if (cf) cf.onclick = () => { Object.assign(st, { families: new Set(), rar: null, str: '', q: '' }); redo(); };
  app.querySelectorAll('[data-d]').forEach(e => e.onclick = ev => { if (ev.target.closest('.nm-edit, .tacts, .nm-in')) return; if (!st.open) { st.open = e.dataset.d; st.sheet = false; redo(); } });

  const nm = app.querySelector('.nm-edit');
  if (nm) nm.onclick = () => { const inp = document.createElement('input'); inp.className = 'nm-in'; inp.maxLength = 40; inp.value = open.name; nm.replaceWith(inp); inp.focus(); inp.select();
    let gone = false; const done = keep => { if (gone) return; gone = true; const name = inp.value.trim();
      if (keep && name) open.name = name.slice(0, 40);
      change(); };
    inp.onblur = () => done(true); inp.onkeydown = k => { if (k.key === 'Enter') done(true); if (k.key === 'Escape') { k.stopPropagation(); done(false); } }; };
  const cp = $('dcopy'); if (cp) cp.onclick = () => navigator.clipboard.writeText(encodeDeck(open.name, open.list, C)).then(() => X.toast('Deck code copied', true), () => X.toast('Could not copy'));
  const cov = $('dcover'); if (cov) cov.onclick = () => pickCover(app, open, id => { open.cover = id; change(); });
  const del = $('ddel'); if (del) del.onclick = () => confirmDelete(app, open, () => { all.splice(all.indexOf(open), 1); st.open = null; change(); X.toast(`Deleted ${open.name}`, true); });
  // A new deck starts empty, open, with its name ready to type.
  const dn = $('dnew'); if (dn) dn.onclick = () => { const d = { id: Date.now().toString(36), name: 'New deck', list: [], cover: null };
    all.push(d); st.open = d.id; st.sheet = false; st.rename = true; change(); };
  const dn2 = $('done'); if (dn2) dn2.onclick = () => { st.open = null; st.sheet = true; redo(); };
  // Upright the deck column is a sheet along the bottom: shut, the cards take the screen. Its grip drags it with the finger
  // and lets go to the nearer state (a flick goes its way); a tap on the grip or on the count opens or shuts it.
  const sh = app.querySelector('.side'), g = $('grip');
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
  if (st.rename) { st.rename = false; const n = app.querySelector('.nm-edit'); if (n) n.click(); }
  const play = $('play'); if (play && !play.disabled) play.onclick = () => X.play(open);

  // Click a card to add a copy; a refused add says why. Right-click a card, or click its strip, to take one out.
  app.querySelectorAll('.cgrid [data-card]').forEach(e => {
    e.onclick = () => { const c = C[e.dataset.card];
      if (!open && matchMedia('(hover: none)').matches) { hidePop(); return zoom(app, c); }   // touch, browsing: a tap reads it
      if (!open) return X.toast(`Open a deck ${portrait() ? 'below' : 'on the right'} to build it`);
      const n = open.list.filter(x => x === c.id).length, inR = open.list.filter(x => C[x].rarity === c.rarity).length;
      const why = open.list.length >= 30 ? 'tot' : n >= limit(c) ? 'pips' : CAP[c.rarity] && inR >= CAP[c.rarity] ? c.rarity : null;
      if (why) return refuse(app, e, why);
      open.list.push(c.id); hidePop(); flash = c.id; change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); });   // touch: hold to read it large
  });
  app.querySelectorAll('.side [data-card]').forEach(e => { e.onclick = () => { open.list.splice(open.list.indexOf(e.dataset.card), 1); hidePop(); change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); hidePop(); zoom(app, C[e.dataset.card]); };
    onHold(e, () => { hidePop(); zoom(app, C[e.dataset.card]); }); });
  const fl = flash && app.querySelector(`.side .st[data-card="${flash}"]`); flash = null;
  if (fl) { fl.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); fl.classList.add('flash'); }

  // Hovering a card or a strip shows the full card, beside it and clear of the deck column.
  const side = app.querySelector('.side').getBoundingClientRect().left;
  app.querySelectorAll('[data-card]').forEach(e => {
    e.onmouseenter = () => { const r = e.getBoundingClientRect(), inSide = !!e.closest('.side');
      pop.className = 'pop'; pop.innerHTML = cardHTML(C[e.dataset.card]); pop.style.display = 'flex';
      const w = pop.offsetWidth, h = pop.offsetHeight;
      pop.style.left = (inSide || r.right + 10 + w > side ? r.left - w - 10 : r.right + 10) + 'px';
      pop.style.top = Math.max(8, Math.min(r.top - 40, innerHeight - h - 10)) + 'px'; };
    e.onmouseleave = hidePop;
  });
}

// A refused add: the card shakes and the limit that stopped it flashes (the deck total, the copy dots or a rarity count).
function refuse(app, el, why) {
  const again = (e, cls) => { if (!e) return; e.classList.remove(cls); void e.offsetWidth; e.classList.add(cls); };
  again(el, 'shake');
  if (why === 'tot') { again(app.querySelector('.fcount'), 'shake'); X.toast('The deck is full: take a card out first'); }
  else if (why === 'pips') again(el.querySelector('.pips'), 'flash');
  else { const rh = app.querySelector(`.rh[data-r="${why}"] span:last-child`); again(rh, 'flash');
    if (!rh || !rh.offsetParent) X.toast(`At most ${CAP[why]} ${why} cards`); }   // the sheet is shut: say it
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
// Right-click a card: it opens large in the middle of the screen, each keyword on it explained beside it (as in
// Hearthstone, Arena and Runeterra). Escape, a click or another right-click closes it.
function zoom(app, c) {
  const kws = Object.keys(KEYWORDS).filter(k => new RegExp(`(^|\\. )${k}[:.]`).test(c.text || ''));
  const m = app.querySelector('#cmodal'); m.classList.add('on', 'zoom');
  m.innerHTML = `<div class="zbox">${cardHTML(c)}${kws.length ? `<div class="kws">${kws.map(k => `<div class="kw"><b>${k}</b><p>${KEYWORDS[k]}</p></div>`).join('')}</div>` : ''}</div>`;
  fitNames(m);
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
function pickCover(app, d, done) {
  const ids = [...new Set(d.list)].filter(id => CROP[id]).sort((a, b) => RANK[C[a].rarity] - RANK[C[b].rarity] || sv(C[a]) - sv(C[b]));
  const { m, close } = dialog(app, `<div class="dlg cov"><h3>Choose a cover</h3><div class="covs">${ids.map(id => `<div class="cv${id === d.cover ? ' on' : ''}" data-id="${id}">${cardHTML(C[id], { cls: 'compact' })}</div>`).join('')}</div>
    <div class="dbtns"><button class="cancel">Cancel</button></div></div>`); fitNames(m);
  m.querySelectorAll('.cv').forEach(e => e.onclick = () => { close(); done(e.dataset.id); });
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
    if (decks().length >= DECKS_MAX) return X.toast(`${DECKS_MAX} decks is the most you can keep: delete one first`);
    const all = decks(), nd = { id: Date.now().toString(36), name: d.name, list: d.list, cover: coverOf(d.list) };
    all.push(nd); st.open = nd.id; save(all);
    render(here().parentElement, all); X.toast(`Imported ${nd.name}`, true);
  });
}
