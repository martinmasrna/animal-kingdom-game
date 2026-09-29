// The collection, which is the deckbuilder (design sandbox builder/notes.md, round B2). The card grid on the left with the
// family, strength, rarity and search filters over it; the decks on the right, the open one unfolded under its tile.
// Click a card to add a copy, right-click it or click its strip to take one out; every change saves.
// app.js hands in what it owns: the cards, the starter decks, the player's decks and how to save them, toast, play, back.
import { cardHTML } from './card.js';
import { CROP, artUrl } from './art.js';
import { encodeDeck, decodeDeck } from './deckcode.js';

const FAMILIES = [['Cat', 'lion'], ['Canine', 'gray_wolf'], ['Rodent', 'squirrel'], ['Colony', 'queen_bee'], ['Bird', 'eagle'],
  ['Snake', 'viper'], ['Bear', 'grizzly_bear'], ['Megafauna', 'elephant'], ['Lizard', 'chameleon']];
const RANK = { legendary: 0, rare: 1, common: 2 }, LIMIT = { legendary: 1, rare: 2, common: 3 }, CAP = { legendary: 4, rare: 8 };
const sv = c => c.str === '*' ? -1 : c.str;
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const svg = d => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICON = {
  back: svg('<path d="M15 5l-7 7 7 7"/>'),
  image: svg('<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 17l-5-5-9 8"/>'),
  copy: svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
  trash: svg('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
};

// A round head crop of the card art, M px across (CROP: centre x, centre y, diameter as fractions of width, height, width).
const med = (id, M) => { const [cx, cy, D] = CROP[id], w = M / D, h = w * 1.5;
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${M / 2 - cx * w}px ${M / 2 - cy * h}px`; };
// Copies as dots: filled for the copies in the deck; with `max`, hollow for the ones still allowed.
const pips = (n, max = n) => Array.from({ length: max }, (_, i) => `<i class="${i < n ? 'on' : ''}"></i>`).join('');

let X, C, cards, st = { open: null, family: null, rar: null, str: '', q: '' }, flash = null, wired = false;
const limit = c => c.copies || LIMIT[c.rarity];
const coverOf = list => list.find(id => C[id].rarity === 'legendary' && CROP[id]) || list.find(id => CROP[id]) || 'lion';
const listOf = cardsObj => Object.entries(cardsObj).flatMap(([id, n]) => Array(n).fill(id));
const countsOf = list => list.reduce((o, id) => (o[id] = (o[id] || 0) + 1, o), {});
const familyCount = list => { const t = {}; list.forEach(id => C[id].tags.forEach(x => { if (FAMILIES.some(f => f[0] === x)) t[x] = (t[x] || 0) + 1; }));
  return Object.entries(t).sort((a, b) => b[1] - a[1]); };

// Your decks (saved on your profile) then the starters, all as {id, name, list, cover, own}.
function decks() {
  const mine = X.getDecks().map(d => ({ id: d.id, name: d.name, list: listOf(d.cards), cover: d.cover && C[d.cover] ? d.cover : null, own: true }));
  mine.forEach(d => d.cover = d.cover || coverOf(d.list.length ? d.list : ['lion']));
  return [...mine, ...X.starters.map(d => ({ id: d.id, name: d.name, list: d.list, cover: X.covers[d.id] || coverOf(d.list), own: false }))];
}
function save(all) {
  X.saveDecks(all.filter(d => d.own).map(d => ({ id: d.id, name: d.name, cards: countsOf(d.list), cover: d.cover })));
}
// Editing a starter makes your copy of it first; the starter never changes.
function editable(all) {
  const d = all.find(x => x.id === st.open); if (!d || d.own) return d;
  const copy = { id: Date.now().toString(36), name: (d.name + ' copy').slice(0, 40), list: [...d.list], cover: d.cover, own: true };
  all.splice(all.filter(x => x.own).length, 0, copy); st.open = copy.id; X.toast(`Editing your copy: ${copy.name}`, true); return copy;
}

export function collectionScreen(app, ctx) {
  X = ctx; C = ctx.cards;
  const starterIds = new Set(ctx.starters.map(d => d.id));
  cards = Object.values(C).filter(c => starterIds.has(c.deck));
  if (!wired) { wired = true; wireGlobal(); }
  const all = decks();
  // First visit: your first deck, or else the first starter (adding to it starts your copy).
  if (st.open === null || !all.some(d => d.id === st.open)) st.open = (all.find(d => d.own) || all[0] || {}).id || null;
  render(app, all);
}

function render(app, all) {
  const keep = [...app.querySelectorAll('.clist, .cgrid')].map(e => e.scrollTop);
  const open = all.find(d => d.id === st.open), counts = open ? countsOf(open.list) : {};
  const inR = r => open ? open.list.filter(id => C[id].rarity === r).length : 0;
  const q = st.q.toLowerCase();
  const shown = cards.filter(c => (!st.family || c.tags.includes(st.family)) && (!st.rar || c.rarity === st.rar) && (st.str === '' || String(c.str) === st.str)
    && (!q || (c.name + ' ' + c.text + ' ' + c.tags.join(' ')).toLowerCase().includes(q)))
    .sort((a, b) => sv(a) - sv(b) || RANK[a.rarity] - RANK[b.rarity] || a.name.localeCompare(b.name));

  const grid = !shown.length ? `<div class="none"><p>No cards match</p><button class="quiet" id="clearf">Clear filters</button></div>`
    : '<div class="crow">' + shown.map(c => { const n = counts[c.id] || 0;
      const max = open && (n >= limit(c) || (!n && CAP[c.rarity] && inR(c.rarity) >= CAP[c.rarity]));   // dimmed: no further copy can go in
      return `<div class="tl${max ? ' max' : ''}" data-card="${c.id}">${cardHTML(c, { cls: 'compact' })}${n && c.rarity !== 'legendary' ? `<span class="pips">${pips(n, limit(c))}</span>` : ''}</div>`; }).join('') + '</div>';

  const tabs = `<div class="tab${st.family ? '' : ' on'}" data-t="" data-tip="All families"><div class="med mosaic">${['lion', 'gray_wolf', 'eagle', 'elephant'].map(id => `<i style="${med(id, 18)}"></i>`).join('')}</div></div>`
    + FAMILIES.map(([f, id]) => `<div class="tab${st.family === f ? ' on' : ''}" data-t="${f}" data-tip="${f}"><div class="med" style="${med(id, 36)}"></div></div>`).join('');
  const strengths = [...new Set(cards.map(c => String(c.str)))].sort((a, b) => (a === '*' ? -1 : +a) - (b === '*' ? -1 : +b));
  const head = `<div class="chead"><div class="tabs">${tabs}</div>
    <select class="sel" id="strsel"><option value="">Any strength</option>${strengths.map(v => `<option value="${v}"${st.str === v ? ' selected' : ''}>${v === '*' ? 'Variable' : 'Strength ' + v}</option>`).join('')}</select>
    <select class="sel" id="rarsel">${[['', 'Any rarity'], ['legendary', 'Legendary'], ['rare', 'Rare'], ['common', 'Common']].map(([v, l]) => `<option value="${v}"${(st.rar || '') === v ? ' selected' : ''}>${l}</option>`).join('')}</select>
    <input class="search" id="q" placeholder="Search" value="${esc(st.q)}"></div>`;

  const strip = id => `<div class="st" data-card="${id}"><div class="art" style="background-image:url(${artUrl(id)})"></div><span class="s">${C[id].str}</span><span class="n">${esc(C[id].name)}</span><span class="x">${C[id].rarity === 'legendary' ? '' : pips(counts[id])}</span></div>`;
  const byR = r => Object.keys(counts).filter(id => C[id].rarity === r).sort((a, b) => sv(C[a]) - sv(C[b]) || C[a].name.localeCompare(C[b].name)).map(strip).join('');
  const rhead = (label, r, cap) => `<h4 class="rh" data-r="${r}"><span>${label}</span><span class="${cap && inR(r) >= cap ? 'full' : ''}">${inR(r)}${cap ? ' / ' + cap : ''}</span></h4>`;
  const body = d => { const fams = familyCount(d.list);
    return `<div class="dbody">${fams.length > 1 ? `<div class="fams">${fams.map(([f, n]) => `<div data-tip="${f}"><div class="med" style="${med(FAMILIES.find(x => x[0] === f)[1], 26)}"></div>${n}</div>`).join('')}</div>` : ''}
      ${rhead('Legendary', 'legendary', 4)}${byR('legendary')}${rhead('Rare', 'rare', 8)}${byR('rare')}${rhead('Common', 'common')}${byR('common')}
      ${d.list.length === 30 ? '<div class="play" id="play">Play this deck</div>' : `<div class="play off">${d.list.length} / 30 cards</div>`}</div>`; };
  const tile = d => d.id === st.open
    ? `<div class="dtile on" data-d="${d.id}" style="background-image:url(${artUrl(d.cover)})"><b${d.own ? ' class="nm-edit" title="Rename"' : ''}>${esc(d.name)}</b>
        <div class="tacts">${d.own ? `<button class="ic" id="dcover" data-tip="Change cover">${ICON.image}</button>` : ''}<button class="ic" id="dcopy" data-tip="Copy deck code">${ICON.copy}</button>${d.own ? `<button class="ic del" id="ddel" data-tip="Delete deck">${ICON.trash}</button>` : ''}</div></div>${body(d)}`
    : `<div class="dtile" data-d="${d.id}" style="background-image:url(${artUrl(d.cover)})"><b>${esc(d.name)}</b><span>${familyCount(d.list).slice(0, 2).map(([f, n]) => n + ' ' + f).join(' · ')}</span></div>`;
  const mine = all.filter(d => d.own), starters = all.filter(d => !d.own);

  app.innerHTML = `<div class="coll">${head}<div class="cgrid">${grid}</div>
    <div class="side"><div class="clist">${mine.map(tile).join('')}${mine.length ? '<div class="dsep"></div>' : ''}${starters.map(tile).join('')}</div>
      <div class="sfoot"><button class="backbtn" id="back">${ICON.back}<span>Back</span></button></div></div><div class="modal" id="cmodal"></div></div>`;
  app.querySelectorAll('.clist, .cgrid').forEach((e, i) => { if (keep[i] != null) e.scrollTop = keep[i]; });
  wire(app, all, open);
}

function wire(app, all, open) {
  const $ = id => app.querySelector('#' + id), redo = () => render(app, all), change = () => { save(all); redo(); };
  const pop = document.getElementById('pop'), hidePop = () => { pop.style.display = 'none'; };
  $('back').onclick = X.back;
  $('strsel').onchange = e => { st.str = e.target.value; redo(); };
  $('rarsel').onchange = e => { st.rar = e.target.value || null; redo(); };
  const q = $('q'); q.oninput = () => { st.q = q.value; const at = q.selectionStart; redo(); const n = app.querySelector('#q'); n.focus(); n.setSelectionRange(at, at); };
  app.querySelectorAll('[data-t]').forEach(e => e.onclick = () => { const f = e.dataset.t || null; st.family = st.family === f ? null : f; redo(); });   // the selected family again clears it
  const cf = $('clearf'); if (cf) cf.onclick = () => { Object.assign(st, { family: null, rar: null, str: '', q: '' }); redo(); };
  app.querySelectorAll('[data-d]').forEach(e => e.onclick = ev => { if (ev.target.closest('.nm-edit, .tacts, .nm-in')) return; st.open = st.open === e.dataset.d ? null : e.dataset.d; redo(); });

  const nm = app.querySelector('.nm-edit');
  if (nm) nm.onclick = () => { const inp = document.createElement('input'); inp.className = 'nm-in'; inp.maxLength = 40; inp.value = open.name; nm.replaceWith(inp); inp.focus(); inp.select();
    let gone = false; const done = keep => { if (gone) return; gone = true; if (keep) open.name = inp.value.trim() || open.name; change(); };
    inp.onblur = () => done(true); inp.onkeydown = k => { if (k.key === 'Enter') done(true); if (k.key === 'Escape') { k.stopPropagation(); done(false); } }; };
  const cp = $('dcopy'); if (cp) cp.onclick = () => navigator.clipboard.writeText(encodeDeck(open.name, open.list, C)).then(() => X.toast('Deck code copied', true), () => X.toast('Could not copy'));
  const cov = $('dcover'); if (cov) cov.onclick = () => pickCover(app, open, change);
  const del = $('ddel'); if (del) del.onclick = () => confirmDelete(app, open, () => { all.splice(all.indexOf(open), 1); st.open = null; change(); X.toast(`Deleted ${open.name}`, true); });
  const play = $('play'); if (play) play.onclick = () => X.play(open);

  // Click a card to add a copy; a refused add says why. Right-click a card, or click its strip, to take one out.
  app.querySelectorAll('.cgrid [data-card]').forEach(e => {
    e.onclick = () => { const c = C[e.dataset.card];
      if (!open) return X.toast('Open a deck to add cards');
      const n = open.list.filter(x => x === c.id).length, inR = open.list.filter(x => C[x].rarity === c.rarity).length;
      const why = open.list.length >= 30 ? 'tot' : n >= limit(c) ? 'pips' : CAP[c.rarity] && inR >= CAP[c.rarity] ? c.rarity : null;
      if (why) return refuse(app, e, why);
      editable(all).list.push(c.id); hidePop(); flash = c.id; change(); };
    e.oncontextmenu = ev => { ev.preventDefault(); if (!open || !open.list.includes(e.dataset.card)) return;
      const d = editable(all); d.list.splice(d.list.indexOf(e.dataset.card), 1); hidePop(); change(); };
  });
  app.querySelectorAll('.side [data-card]').forEach(e => e.onclick = () => { const d = editable(all); d.list.splice(d.list.indexOf(e.dataset.card), 1); hidePop(); change(); });
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
  if (why === 'tot') { again(app.querySelector('.play'), 'shake'); if (!app.querySelector('.play.off')) X.toast('The deck is full: take a card out first'); }
  else again(why === 'pips' ? el.querySelector('.pips') : app.querySelector(`.rh[data-r="${why}"] span:last-child`), 'flash');
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
function confirmDelete(app, d, done) {
  const { m, close } = dialog(app, `<div class="dlg"><h3>Delete “${esc(d.name)}”?</h3><p>This can’t be undone. Copy its deck code first if you might want it back.</p>
    <div class="dbtns"><button class="cancel">Cancel</button><button class="danger">Delete deck</button></div></div>`);
  m.querySelector('.cancel').focus();
  m.querySelector('.danger').onclick = () => { close(); done(); };
}
function pickCover(app, d, done) {
  const ids = [...new Set(d.list)].filter(id => CROP[id]).sort((a, b) => RANK[C[a].rarity] - RANK[C[b].rarity] || sv(C[a]) - sv(C[b]));
  const { m, close } = dialog(app, `<div class="dlg cov"><h3>Choose a cover</h3><div class="covs">${ids.map(id => `<div class="cv${id === d.cover ? ' on' : ''}" data-id="${id}">${cardHTML(C[id], { cls: 'compact' })}</div>`).join('')}</div>
    <div class="dbtns"><button class="cancel">Cancel</button></div></div>`);
  m.querySelectorAll('.cv').forEach(e => e.onclick = () => { d.cover = e.dataset.id; close(); done(); });
}

// Screen-wide keys and paste, live only while the collection is on screen.
function wireGlobal() {
  const here = () => document.querySelector('.coll'), typing = e => /INPUT|SELECT|TEXTAREA/.test(e.target.tagName);
  addEventListener('keydown', e => {
    if (!here() || here().querySelector('.modal.on')) return;
    if (e.key === '/' && !typing(e)) { e.preventDefault(); here().querySelector('#q').focus(); }
    else if (e.key === 'Escape' && !typing(e)) X.back();
  });
  // Paste a deck code (or a plain "3x Lion" list) anywhere: it becomes your deck, open.
  addEventListener('paste', e => {
    if (!here() || typing(e)) return;
    const d = decodeDeck(e.clipboardData.getData('text'), C);
    if (!d) return X.toast('That is not a deck code');
    const all = decks(), nd = { id: Date.now().toString(36), name: d.name, list: d.list, cover: coverOf(d.list), own: true };
    all.splice(all.filter(x => x.own).length, 0, nd); st.open = nd.id; save(all);
    render(here().parentElement, all); X.toast(`Imported ${nd.name}`, true);
  });
}
