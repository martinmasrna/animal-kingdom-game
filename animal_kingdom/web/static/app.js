// Animal Kingdom web client: menu flow (home -> play -> pre-match) and the game screen.
// The server holds the game; this file only renders the seat's view and sends choices back.
import { fitStrips } from './art.js';
import { fitNames, readSide } from './card.js';
import { plan, DUR } from './timeline.js';
import { fly, dive, landed as flightLanded, flying, flightEnd, FLIGHT, HIT_DELAY } from './flight.js';
import { carry, carrying, release, drop as carryDrop } from './carry.js';
import { renderBoard, BEAT_MS, STAGE, VIEW, setView, crossroadAt, chalk, portrait, leaderAt, resolvesIn, tokenWidth, RAIL } from './board.js';
import { manaCard, fitPlaques, pipsHTML, costChip, leaderToken, flightGeo, powerCard, powerCostHTML } from './mana.js';
import { playFood } from './foodfx.js';
import { decodeDeck } from './deckcode.js';
import { openPatch, newestPatch } from './patch.js';
import { collectionScreen as renderCollection, coverOf, deckBody, deckIssue, stripsHTML } from './collection.js';
import { onHold, holdEvents } from './menu.js';
import { tokenBase, numeral } from './token.js';
import { play as sfx, soundsFor, preload, volume, setVolume } from './sound.js';
import { openFeedback } from './feedback.js';
import { track } from './log.js';
import { openPresence, showChallenge, confirmFriend, shareLink, friendLabel } from './friends.js';
import { initChat, badge as chatBadge, wireChatButton, ICON_FRIENDS, hasFriends, friendsNow } from './chat.js';

const app = document.getElementById('app'), pop = document.getElementById('pop'), stackpop = document.getElementById('stackpop');
const SKIP = '__skip__';
const store = (k, v) => { try { v === undefined ? null : localStorage.setItem(k, v); return localStorage.getItem(k); } catch { return null; } };
const tokenKey = id => 'ak:seat:' + id;
const getToken = id => { try { return sessionStorage.getItem(tokenKey(id)); } catch { return null; } };
const setToken = (id, t) => { try { sessionStorage.setItem(tokenKey(id), t); } catch { /* private mode: the tab just can't reconnect */ } };

let RULES = null, CARDS = {}, MAP, ME = null, LEADERS = {};   // RULES: the deck rules; LEADERS: card id -> {kind, text}; ME: your profile {id, name, tag, decks}
let V = null, ws = null, wsId = null, screen = null;
const ui = { sel: null, selIid: null, roam: null, hover: null, peek: false, menu: false, panel: null };   // roam: the crossroad (viewer space) of the animal picked to roam

// ------------------------------------------------------------------ shared bits
// The menus' hover labels (menu.css: a tag under the thing) turn to stay in the window: above the thing near the bottom,
// held to its left or right end near a side. The label's width is measured in its own font before it shows.
const tipFont = document.createElement('canvas').getContext('2d');
document.addEventListener('mouseover', e => {
  const t = e.target.closest && e.target.closest('.mscr [data-tip]'); if (!t) return;
  const r = t.getBoundingClientRect(), mid = (r.left + r.right) / 2;
  tipFont.font = "600 14px 'Fira Sans Condensed', sans-serif"; const w = tipFont.measureText(t.dataset.tip).width + 20;
  t.classList.toggle('tip-up', r.bottom + 8 + 32 > innerHeight - 4);
  t.classList.toggle('tip-l', mid - w / 2 < 8); t.classList.toggle('tip-r', mid + w / 2 > innerWidth - 8);
});
function toast(msg, ok) {
  const t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block'; t.classList.toggle('ok', !!ok);
  clearTimeout(toast.h); toast.h = setTimeout(() => t.style.display = 'none', 3500);
}
// A decklist in the game's panels: the collection's strips, each with the copies left.
function rows(list, counts) {
  return stripsHTML(Object.keys(list), CARDS, id => counts ? (counts[id] || 0) : list[id]);   // by cost, each with its cost
}
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
function cardPop(el, id, extra, place) {
  const c = CARDS[id], r = el.getBoundingClientRect();
     // the mana rules' card
  pop.className = 'pop ' + c.rarity + ((' mpop'));
  pop.innerHTML = ((manaCard(c, { cost: c.mana ?? null, w: 200 }))) + (LEADERS[id] ? powerCard(id, LEADERS[id], 170) : '') + (extra ? `<div class="ev">${extra}</div>` : '');
  pop.style.display = 'flex'; fitNames(pop); fitPlaques(pop);
  const h = pop.offsetHeight;
  const w = pop.offsetWidth;
  if (place === 'below') { pop.style.left = Math.min(r.left, innerWidth - w - 10) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; }
  else { pop.style.left = (r.right + 10 + w > innerWidth ? r.left - w - 10 : r.right + 10) + 'px'; pop.style.top = Math.max(8, Math.min(r.top - 40, innerHeight - h - 10)) + 'px'; }
}
// Touch reads a card in the middle of the screen, clear of the finger, until the next tap (feedback 2026-10-01): a hand card
// with each keyword on it explained under it (as the collection's), or a board piece's stack (readStack). `down`: the finger
// A right-click reads a hand card too (a Windows long-press arrives as one).
const touch = () => matchMedia('(hover: none)').matches;
function readOverlay(html) {
  document.querySelectorAll('.readov').forEach(o => o.remove());
  const ov = document.createElement('div'); ov.className = 'readov'; ov.innerHTML = `<div class="rbox">${html}</div>`;
  document.body.appendChild(ov); fitNames(ov);
  let pressed = false;   // only a press that starts on it closes it: the lift of the press that opened it does not
  ov.addEventListener('pointerdown', () => { pressed = true; });
  ov.addEventListener('click', e => { e.stopPropagation(); if (pressed) ov.remove(); });
  ov.addEventListener('contextmenu', e => { e.preventDefault(); ov.remove(); });
}
// A card read large, the one way everywhere (the hand, a board piece): the card, and beside it the cards it makes and its
// keywords explained (under it on a narrow screen). `extra`: what goes under the card itself (a board piece's timer).
function cardRead(id, str, seat = V && V.you, extra = '') {
  const c = CARDS[id]; if (!c) return '';
  const face = (manaCard(c, { ...(str == null ? {} : { str }), cost: c.mana ?? null, owner: seat === V.you ? 'A' : 'B', w: 230 }));   // the mana rules' card, piece, plaque and cost
  const pw = LEADERS[id] ? powerCard(id, LEADERS[id], 170) : '';   // a leader's power beside it, as a card's tokens
  return `<div class="rcard${(c.related || []).length || pw ? ' wide' : ''}">${face}${extra}${pw}${readSide(c, CARDS, (r => manaCard(r, { cost: r.mana ?? null, w: 170 })))}</div>`;
}
function readCard(id, str, seat = V && V.you) {
  const html = cardRead(id, str, seat); if (html) readOverlay(html);
}
function wirePops(root) {
  root.querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card);
    el.onmouseleave = () => pop.style.display = 'none';
    onHold(el, () => cardPop(el, el.dataset.card), () => pop.style.display = 'none');   // touch: shown while held
  });
}
// A deck's cover: its leader (collection.js coverOf).
const coverFor = d => coverOf(d.list, CARDS, d.leader);
// Your profile: the server knows you by the sign-in code this browser keeps (localStorage 'ak:key').
const api = (path, opts = {}) => fetch(path, { ...opts, headers: { 'Content-Type': 'application/json', 'X-AK-Key': store('ak:key') || '', ...(opts.headers || {}) } });
async function loadProfile() {
  if (store('ak:key')) { const r = await api('/api/me'); if (r.ok) return ME = await r.json(); }
  // First visit (or the code no longer exists): a new guest profile, taking along any decks built in this browser before profiles.
  let decks = []; try { decks = JSON.parse(localStorage.getItem('ak:decks') || '[]'); } catch { /* none */ }
  const r = await api('/api/profile', { method: 'POST', body: JSON.stringify({ decks }) });
  if (!r.ok) return ME = { name: 'Player', tag: '', decks: [], history: [], records: [] };
  const m = await r.json(); store('ak:key', m.code); return ME = m.profile;
}
// Player-built decks live in the profile: [{id, name, cards: {cardId: copies}}]. Only complete ones are playable.
const myDecks = () => ME.decks.map(d => ({ ...d, cards: Object.fromEntries(Object.entries(d.cards).filter(([id]) => CARDS[id])) }));
const saveDecks = ds => { ME.decks = ds; api('/api/me/decks', { method: 'PUT', body: JSON.stringify(ds) }).then(r => r.ok || toast('Could not save your decks')); };
const deckSize = cards => Object.values(cards).reduce((a, n) => a + n, 0);
// The decks you can play: your complete decks (a profile starts with the starters as its own); with none, the starters.
// A deck short of its cards is listed too, so it doesn't vanish from home while you build it: shown with its count, opened in
// the collection to finish, never chosen to play (Martin, 2026-10-31: "affordance for decklist with less than 30 cards").
// A deck over the rules (copies or stars, the stars prototype) is treated like an unfinished one: listed, opened in the
// collection to fix, never played. `fix` holds what is over.
const playable = () => { const mine = myDecks().map(d => { const list = Object.entries(d.cards).flatMap(([id, n]) => Array(n).fill(id)).filter(id => CARDS[id]);
    const leader = d.leader && list.includes(d.leader) && LEADERS[d.leader] ? d.leader : null;   // every deck has one (deckIssue)
    const size = RULES ? RULES.deckSize : 30, short = Math.max(0, size - deckSize(d.cards)), fix = short || !RULES ? '' : deckIssue(list, CARDS, RULES, leader, LEADERS);
    return { id: 'my:' + d.id, name: d.name, mine: true, short: short || (fix ? -1 : 0), fix, list, leader }; });
  return mine; };
const chosenDeck = () => { const all = playable().filter(d => !d.short), id = store('ak:deck'); return all.find(d => d.id === id) || all[0]; };
const deckSpec = d => d.mine ? { name: d.name, list: d.list, ...(d.leader ? { leader: d.leader } : {}) } : d.id;

// ------------------------------------------------------------------ routing
// The client's build, from the server that served it. A socket (presence, or a match) names the server's build each time
// it connects, so a tab left open across a deploy learns it runs an old client and reloads: at once, or, while you're
// typing, when you next come back to the tab. A match picks up where it was (the tab keeps its seat).
let BUILD = null;
function checkBuild(b) {
  if (!b || !BUILD || b === BUILD) return;
  const typing = () => document.activeElement && /^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName);
  if (!typing()) return location.reload();
  addEventListener('visibilitychange', () => { if (!document.hidden && !typing()) location.reload(); });
}
async function boot() {
  const p = await fetch('/api/pool').then(r => r.json());
  CARDS = Object.fromEntries(p.cards.map(c => [c.id, c])); MAP = p.map; BUILD = p.build; RULES = p.rules; LEADERS = p.leaders;
  // the animals' calls (web/parked_calls/, not served) are parked (Martin, 2026-10-01): only the basic sounds play for now
  await loadProfile();
  // Feedback while the game is in testing: a tab on the screen's edge where the edge is free (home, News, Settings: app.css shows
  // it by screen); Collection and the profile have it beside Back, their side panels holding the edge; the game its own button.
  document.body.insertAdjacentHTML('beforeend', `<button class="ftab" id="ftab">${TOPICON.feedback}<span>Feedback</span></button>`);
  document.getElementById('ftab').onclick = feedback;
  openPresence({ api, toast, build: checkBuild, key: () => store('ak:key'), deck: () => deckSpec(chosenDeck()),   // friends see you online; challenges arrive
    busy: () => screen === 'game' && V && V.phase === 'playing', accept: m => { setToken(m.id, m.token); location.hash = '#/m/' + m.id; } });
  initChat({ api, toast, inMatch: () => screen === 'game' && !!V && V.phase === 'playing',
    changed: () => { if (screen === 'game' && V) drawGame(); drawPlayFriends(); },   // the game's Friends button shows once you have a friend
    challenge: f => challengeFriend(f) });
  addEventListener('hashchange', route);
  addEventListener('resize', () => { if (screen === 'game') fitStage(); });
  // A phone's keyboard covers the bottom of the page instead of shrinking it, so a field low on a menu screen (a new deck's
  // name, in the collection's bottom sheet) was typed blind. While it is up, the menu screens fit the part still showing
  // (menu.css: html.kb). A pinch zoom shrinks that part too, but changes the scale; a keyboard never does.
  const vv = window.visualViewport;
  if (vv) { const fit = () => { const kb = Math.abs(vv.scale - 1) < .01 && innerHeight - vv.height > 80, s = document.documentElement.style;
    document.documentElement.classList.toggle('kb', kb);
    if (kb) { s.setProperty('--vvt', vv.offsetTop + 'px'); s.setProperty('--vvh', vv.height + 'px'); } };
    vv.addEventListener('resize', fit); vv.addEventListener('scroll', fit); }
  addEventListener('keydown', e => {   // Escape backs out of whatever is open: the menu, a panel, then the selected card
    
    // Space ends your turn: the same check as clicking End turn
    if (screen === 'game' && !/INPUT|TEXTAREA/.test(e.target.tagName) && !e.repeat) {
      if (e.key === ' ' && document.querySelector('#tbtn.can')) { e.preventDefault(); return document.getElementById('tbtn').click(); }
    }
    if (e.key !== 'Escape' || screen !== 'game') return;
    const ask = document.getElementById('concov');
    if (ask && ask.classList.contains('on')) return ask.classList.remove('on');
    if (ui.panel) { ui.panel = null; return showPanel(); }
    if (ui.sel || ui.roam) { ui.sel = null; ui.roam = null; drawGame(); }
  });
  await rejoin();
  route();
  // a new patch opens once, over whatever came up, for a returning player (one with a deck); never over a match in play
  const v = await newestPatch();
  if (v && ME.patchSeen !== v && myDecks().length && !(screen === 'game' && V && V.phase === 'playing')) openPatch({ seen: seePatch });
}

// Back into the match you're still playing (after a closed tab, a phone that dropped the page, another device): the server
// keeps your seat, so opening the game anywhere takes you to it.
async function rejoin(only) {
  const r = await api('/api/current').catch(() => null), m = r && r.ok ? await r.json() : {};
  if (!m.id || (only && m.id !== only)) return false;
  if (!getToken(m.id)) setToken(m.id, m.token);   // a tab that holds a seat keeps it: one profile may hold both seats of a friend match, one window each
  if (!only && !location.hash.startsWith('#/m/' + m.id)) location.hash = '#/m/' + m.id;
  return true;
}

function route() {
  track('screen', { route: (location.hash.slice(1) || '/').split('/').slice(0, 2).join('/'), w: innerWidth, h: innerHeight });
  pop.style.display = 'none'; stackpop.style.display = 'none';
  if (!location.hash.startsWith('#/m/')) keepAwake(false);
  const tip = document.getElementById('tip'); if (tip) tip.style.display = 'none';   // the game's hover label lives on body: it must not outlive the screen
  const parts = (location.hash.slice(1) || '/').split('/').filter(Boolean);
  const id = parts[1] && parts[1].toUpperCase();
  if (parts[0] !== 'm' || id !== wsId) disconnect();
  if (parts[0] === 'play') return manaHome({ play: true });   // Play: a deck and a friend
  if (parts[0] === 'practice') return manaHome({ practice: true });   // Practice: your deck and the bot's
  if (parts[0] === 'collection') return collectionScreen(parts[1]);
  if (parts[0] === 'patch') { history.replaceState(null, '', '#/'); manaHome(); return openPatch({ version: parts[1], seen: seePatch }); }   // a link to the notes: home, the window over it
  showChallenge();   // a challenge waiting while a match was in play shows once you're out of it
  if (parts[0] === 'friend' && id) { manaHome(); return confirmFriend(id, () => { history.replaceState(null, '', '#/'); route(); }); }
  if (parts[0] === 'deck' && parts[1]) return deckLinkScreen(parts.slice(1).join('/'));
  if (parts[0] === 'account') return accountScreen();
  if (parts[0] === 'auth') return finishSignIn(parts[1]);
  if (parts[0] === 'join' && id) return getToken(id) ? (location.hash = '#/m/' + id) : manaHome({ join: id });
  if (parts[0] === 'm' && id) return matchScreen(id);
  manaHome();
}

// ------------------------------------------------------------------ home: where a match starts
const TI = n => `<img class="tic" src="/static/kit2/top/${n}.webp" alt="" draggable="false">`;
const TOPICON = { feedback: TI('feedback'), friends: TI('friends'), person: TI('person') };

function settingsBody() {
  const v = Math.round(volume() * 100);
  return `<div class="srow"><span>Sound</span><input type="range" id="vol" min="0" max="100" step="5" value="${v}" aria-label="Sound volume"><b id="volv">${v ? v + '%' : 'Off'}</b></div>`;
}
function wireSettings(root) {
  const r = root.querySelector('#vol'), out = root.querySelector('#volv');
  r.oninput = () => { setVolume(r.value / 100); out.textContent = +r.value ? r.value + '%' : 'Off'; };
  r.onchange = () => sfx('land');   // a sample at the new volume
}

// Feedback from anywhere; on the game screen it carries the match, the turn and the seat's whole view (a bug as it happened).
function feedback() {
  const g = screen === 'game' && V && V.id ? V : null;
  const context = g ? { match: g.id, turn: g.game.round, seat: g.you, opponent: (g.seats[opp()] || {}).bot || 'person',
 } : {};
  track('feedback_open', { screen: context.screen });
  openFeedback({ api, toast, context, view: g });
}

// ------------------------------------------------------------------ collection (= the deckbuilder): collection.js
// #/collection/<deck id> opens that deck (home's "Open in collection").
function collectionScreen(open) {
  screen = 'collection';
  if (open) history.replaceState(null, '', '#/collection');
  renderCollection(app, { open, rules: RULES, cards: CARDS, leaders: LEADERS, getDecks: myDecks, saveDecks, toast, feedback, share: shareDeck,
    play: d => { store('ak:deck', 'my:' + d.id); location.hash = '#/play'; }, back: () => { location.hash = '#/'; } });
}

// ------------------------------------------------------------------ share links (docs/share-links.md)
// A deck link: #/deck/<the deck code's AK1 part>?n=<name>. It holds the whole list; the server keeps nothing.
const deckLink = (code, name) => `${location.origin}/#/deck/${(code.match(/AK1:([A-Za-z0-9_-]+)/) || [])[1]}?n=${encodeURIComponent(name)}`;
function shareDeck(code, name) { shareLink(deckLink(code, name), `${name}, a deck in Animal Kingdom`); }
// The list, shown to anyone; one tap puts it in your collection (a visitor's guest profile, made at boot, holds it).
function deckLinkScreen(arg) {
  screen = 'decklink';
  const [code, q] = arg.split('?'), name = new URLSearchParams(q || '').get('n');
  const d = decodeDeck(`${name ? '### ' + name + '\n' : ''}AK1:${code}`, CARDS);
  if (!d) { history.replaceState(null, '', '#/'); manaHome(); return toast('That deck link holds no cards'); }
  app.innerHTML = `<div class="mscr ladder"><div class="hist"><div class="hhead"><div class="ptabs"><a class="lback" id="back" href="#/" aria-label="Back"></a><span class="ptab on">${esc(d.name)}</span></div></div>
    <div class="hbody"><div class="dlink">${deckBody(d.list, CARDS)}</div><p><button class="slab" id="dimport">Add to my collection</button> <a class="slab" href="#/">Home</a></p></div></div></div>`;
  document.getElementById('dimport').onclick = () => {
    const mine = myDecks();
    if (mine.length >= RULES.decksMax) return toast(`${RULES.decksMax} decks is the most you can keep: delete one first`);
    const cards = {}; d.list.forEach(id => cards[id] = (cards[id] || 0) + 1);
    const nd = { id: Date.now().toString(36), name: d.name, cards };
    saveDecks([...mine, nd]); toast(`Imported ${d.name}`, true); location.hash = '#/collection/' + nd.id;
  };
}

// ------------------------------------------------------------------ ladder, and your account (in Settings)
// The ladder: the leaderboard and your match history as its two tabs, one column on the ground; your account (name,
// sign-in, the sign-in code) lives in Settings and your friends in the Friends panel (Martin, 2026-10-04).
const PROVIDER = { google: 'Google', discord: 'Discord' };
// ------------------------------------------------------------------ your account
// Your name, signing in with Google or Discord (the server's providers: web/oauth.py) and, before you do, the sign-in code
// that plays as you on another device.
function accountBody() {
  const unlinked = ME.providers.filter(p => !ME.logins.some(l => l.provider === p));
  const sect = (title, body) => `<div class="sect"><h4>${title}</h4>${body}</div>`;
  const account = ME.logins.length
    ? sect('Account', `${ME.logins.map(l => `<div class="login">${PROVIDER[l.provider]} · ${esc(l.label)}</div>`).join('')}
        <div class="row">${unlinked.map(p => `<button class="slab" data-login="${p}">Also ${PROVIDER[p]}</button>`).join('')}<button class="slab" id="signout">Sign out</button></div>`)
    : ME.providers.length ? sect('Account', `<p>Sign in to keep your decks and matches on every device.</p>
        <div class="row">${ME.providers.map(p => `<button class="slab" data-login="${p}">${PROVIDER[p]}</button>`).join('')}</div>`) : '';
  const code = ME.logins.length ? '' : sect('Sign-in code', `<p>Type it on another device to play there as ${esc(ME.name)}. Anyone with it can too.</p>
      <div class="row"><span class="field keycode" id="key">${ui.showKey ? esc(store('ak:key')) : '••••-••••-••••-••••'}</span><button class="slab" id="showkey">${ui.showKey ? 'Hide' : 'Show'}</button><button class="slab" id="copykey">Copy</button></div>`)
    + sect('Use a different profile', `<div class="row"><input class="field" id="other" placeholder="Sign-in code" autocomplete="off"><button class="slab" id="signin">Sign in</button></div>`);
  return sect('Name', `<div class="namerow"><input class="field namein" id="pname" maxlength="20" value="${esc(ME.name)}" title="Rename"><span class="tag">#${ME.tag}</span></div>`) + account + code;
}
function wireAccount(root, redraw) {
  const $r = id => root.querySelector('#' + id);
  const nm = $r('pname');
  nm.onchange = async () => { const r = await api('/api/me', { method: 'PATCH', body: JSON.stringify({ name: nm.value }) });
    if (!r.ok) return toast(await r.text()); ME = await r.json(); redraw(); };
  root.querySelectorAll('[data-login]').forEach(el => el.onclick = async () => {
    const r = await api('/api/auth/' + el.dataset.login, { method: 'POST' });
    if (!r.ok) return toast(await r.text());
    location.href = (await r.json()).url;
  });
  const so = $r('signout');
  if (so) so.onclick = async () => { await api('/api/signout', { method: 'POST' }); localStorage.removeItem('ak:key'); await loadProfile(); location.hash = '#/'; };
  if (ME.logins.length) return;
  $r('showkey').onclick = () => { ui.showKey = !ui.showKey; redraw(); };
  $r('copykey').onclick = () => navigator.clipboard.writeText(store('ak:key')).then(() => toast('Sign-in code copied', true), () => toast(store('ak:key')));
  const other = $r('other');
  const signIn = async () => { const r = await api('/api/signin', { method: 'POST', body: JSON.stringify({ code: other.value }) });
    if (!r.ok) return toast('No profile has that sign-in code');
    ME = await r.json(); store('ak:key', other.value.trim().toUpperCase()); ui.showKey = false; toast(`Signed in as ${ME.name}#${ME.tag}`, true); redraw(); };
  $r('signin').onclick = signIn;
  other.onkeydown = e => { if (e.key === 'Enter') signIn(); };
}
function accountScreen() {
  screen = 'account';
  app.innerHTML = `<div class="mscr lead sets"><div class="lcol"><div class="hhead"><h2>Account</h2></div>
    <div class="lbody">${accountBody()}</div>
    <div class="sfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div></div>`;
  document.getElementById('back').onclick = () => { location.hash = '#/'; };
  wireAccount(app, accountScreen);
}
// Back from Google or Discord: the one-time code swapped for this device's own session key.
async function finishSignIn(code) {
  history.replaceState(null, '', '#/account');
  const r = code && code !== 'failed' ? await api('/api/auth/redeem', { method: 'POST', body: JSON.stringify({ code }) }) : null;
  if (!r || !r.ok) { toast('Sign-in didn\'t go through, try again'); return accountScreen(); }
  const m = await r.json(); store('ak:key', m.key); ME = m.profile;
  toast(`Signed in as ${ME.name}#${ME.tag}`, true); accountScreen();
}

// A deck legal under the deck rules (decks.deck_problems): its size, its copies, only collectible cards, and a leader of
// its own.
function legal(list, leader) {
  const n = {}; for (const id of list) n[id] = (n[id] || 0) + 1;
  return list.length === RULES.deckSize && !!leader && list.includes(leader) && !!LEADERS[leader]
    && Object.entries(n).every(([id, k]) => CARDS[id] && CARDS[id].status === 'collectible' && k <= RULES.copies[CARDS[id].rarity]);
}
// A friend's Challenge (the Friends panel, chat.js): your chosen deck, as Play would play it. An online friend is asked at
// once and the match opens when they accept; an offline one gets a link to a match waiting for them.
async function challengeFriend(f) {
  const d = chosenDeck(), name = f.name.split('#')[0];
  if (!d) return toast('Build a legal deck in the Collection first: 25 cards and a leader');
  if (!f.online) {
    const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ deck: deckSpec(d), name: 'You' }) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token);
    shareLink(`${location.origin}/#/join/${m.id}`, 'A match in Animal Kingdom'); location.hash = '#/m/' + m.id; return;
  }
  toast(`Waiting for ${name} to accept`, true);
  const r = await api('/api/challenge', { method: 'POST', body: JSON.stringify({ friend: f.id, deck: deckSpec(d) }) });
  if (!r.ok) return toast(r.status === 409 ? await r.text() : 'The challenge didn\'t go through');
  const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
}
// Home (a plain prototype, Martin, 2026-11-20): three buttons. Play opens the friend match (#/play: a deck,
// then a match to invite a friend to, or a friend's code); Practice (#/practice) your deck and the simple bot's, both from
// your decks (Martin, 2026-11-21: "select deck for me and my opponent"); Collection is the collection. In Play and
// Practice: your decks that are legal under these rules; a deck of yours that isn't legal is counted under the list.
// the patch notes were opened: seen by this profile, on every device (the server keeps it)
const seePatch = v => { if (ME.patchSeen === v) return; ME.patchSeen = v; api('/api/me/patch', { method: 'POST', body: JSON.stringify({ version: v }) }); };
function manaHome(mode = {}) {
  screen = 'home';
  if (!mode.play && !mode.join && !mode.practice) {
    app.innerHTML = `<div class="mhome"><div class="mtop"><button class="acct pnbtn" id="mpatch">Patch Notes</button><a class="acct" href="#/account" data-tip="Account" aria-label="Account">${TOPICON.person}</a><button class="backbtn ico chatbtn" id="hchat" data-tip="Friends" aria-label="Friends">${TOPICON.friends}${chatBadge()}</button></div><div class="box front">
      <h1>Animal Kingdom<small>A prototype</small></h1>
      <div class="mmenu"><a class="go" id="mplay" href="#/play">Play</a><a class="go sub" id="mprac" href="#/practice">Practice</a><a class="go sub" id="mcoll" href="#/collection">Collection</a></div>
      </div></div>`;
    wireChatButton(document.getElementById('hchat'));
    document.getElementById('mpatch').onclick = () => openPatch({ seen: seePatch });
    return;
  }
  const own = myDecks().map(d => { const list = Object.entries(d.cards).flatMap(([id, n]) => Array(n).fill(id));
    return { id: 'my:' + d.id, name: d.name, mine: true, list, leader: d.leader }; }), mine = own.filter(d => legal(d.list, d.leader)), off = own.length - mine.length;
  const all = [...mine], chosen = all.find(d => d.id === store('ak:deck')) || all[0];   // your legal decks only: the pool's animal decks are no mana decks (2026-11-20)
  const leaderName = d => { const ls = d.leader ? [d.leader] : [...new Set(d.list || [])].filter(id => LEADERS[id]);   // a pool deck: the one card in it that can lead
    return ls.length === 1 && CARDS[ls[0]] ? CARDS[ls[0]].name.split(':')[0] : ''; };
  // a deck: its leader's token beside its name, in the side's colour
  const face = (d, side) => `${d.leader && CARDS[d.leader] ? `<div class="tokpiece" style="--tw:44px">${leaderToken(d.leader, side, CARDS, 44)}</div>` : ''}<span>${esc(d.name)}${leaderName(d) ? `<small>${esc(leaderName(d))}</small>` : ''}</span>`;
  const tile = d => `<button class="dk${chosen && d.id === chosen.id ? ' on' : ''}" data-deck="${d.id}">${face(d, 'A')}</button>`;
  const spec = d => d.mine ? { name: d.name, list: d.list, leader: d.leader } : d.id;
  if (mode.practice) {   // your deck in blue, the bot's in red (the teams' colours); the bot's starts as yours
    const rival = all.find(d => d.id === store('ak:botdeck')) || chosen;
    const otile = d => `<button class="dk opp${rival && d.id === rival.id ? ' on' : ''}" data-opp="${d.id}">${face(d, 'B')}</button>`;
    app.innerHTML = `<div class="mhome"><div class="box">
      <h1>Practice<small>Your deck against the bot's</small></h1>
      <h2>Your deck</h2><div class="decks">${all.map(tile).join('') || '<p>No deck of yours is legal under these rules yet.</p>'}</div>
      ${all.length ? `<h2>The bot's deck</h2><div class="decks">${all.map(otile).join('')}</div>` : ''}
      ${off ? `<p class="foot">${off === 1 ? 'One deck of yours isn\'t' : `${off} decks of yours aren't`} legal in these rules: the collection says why.</p>` : ''}
      <div class="row"><button class="go" id="mgo">Start</button><a class="sec" href="#/">Back</a></div>
      </div></div>`;
    app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { store('ak:deck', el.dataset.deck); manaHome(mode); });
    app.querySelectorAll('[data-opp]').forEach(el => el.onclick = () => { store('ak:botdeck', el.dataset.opp); manaHome(mode); });
    document.getElementById('mgo').onclick = async () => {
      if (!chosen) return toast('Build a legal deck in the Collection first: 25 cards and a leader');
      const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ deck: spec(chosen), bot_deck: spec(rival), name: 'You', bot: true }) });
      if (!r.ok) return toast(await r.text());
      const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
    };
    return;
  }
  app.innerHTML = `<div class="mhome"><div class="box">
    <h1>Play<small>Choose a deck, then invite a friend</small></h1>
    <h2>Your deck</h2><div class="decks">${all.map(tile).join('') || '<p>No deck of yours is legal under these rules yet.</p>'}</div>
    ${off ? `<p class="foot">${off === 1 ? 'One deck of yours isn\'t' : `${off} decks of yours aren't`} legal in these rules: the collection says why.</p>` : ''}
    <div class="row"><button class="go" id="mgo">${mode.join ? `Join match ${esc(mode.join)}` : 'Create match'}</button><a class="sec" href="#/">Back</a></div>
    ${mode.join ? '' : `<div id="mfriends"></div><h2>Join a friend's match</h2><div class="row"><input id="mcode" maxlength="6" placeholder="Code" autocomplete="off"><button class="sec" id="mjoin">Join</button></div>`}
    </div></div>`;
  drawPlayFriends();
  const $ = id => document.getElementById(id);
  app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { store('ak:deck', el.dataset.deck); manaHome(mode); });
  const join = async code => {
    if (!chosen) return toast('Choose a deck first');
    const r = await api(`/api/match/${code}/join`, { method: 'POST', body: JSON.stringify({ deck: spec(chosen), name: 'Friend' }) });
    if (!r.ok) return toast(r.status === 404 ? `No match ${code}` : await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
  $('mgo').onclick = async () => {
    if (mode.join) return join(mode.join);
    if (!chosen) return toast('Choose a deck first');
    const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ deck: spec(chosen), name: 'You' }) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
  const code = $('mcode');
  if (code) { const go = () => { const c = code.value.trim().toUpperCase(); if (c) join(c); };
    code.onkeydown = e => { if (e.key === 'Enter') go(); }; $('mjoin').onclick = go; }
}
// Play's friends (Martin, 2026-11-21: "challenge them directly from play screen"): each online friend a Challenge with
// the deck chosen above, as the Friends panel's; one away shows as away. None: nothing.
function drawPlayFriends() {
  const el = document.getElementById('mfriends'); if (!el) return;
  const all = friendsNow(), on = all.filter(f => f.online), off = all.filter(f => !f.online);
  const html = !all.length ? '' : `<h2>Challenge a friend</h2><div class="mfr">${[...on, ...off].map(f =>
    `<div class="mf${f.online ? ' on' : ''}"><span class="dot${f.online ? ' on' : ''}"></span><b>${esc(friendLabel(f, all))}</b>`
    + (f.online ? `<button class="go sm" data-chal="${f.id}">Challenge</button>` : '<small>Away</small>') + '</div>').join('')}</div>`;
  if (el._html === html) return;
  el.innerHTML = el._html = html;
  el.querySelectorAll('[data-chal]').forEach(b => b.onclick = () => { const f = friendsNow().find(x => x.id === b.dataset.chal); if (f) challengeFriend(f); });
}
function disconnect() {  if (ws) { wsId = null; ws.onclose = null; ws.close(); ws = null; } stopPlayback(); V = null; }   // a step still timed would redraw the game over the next screen

async function matchScreen(id) {
  if (!getToken(id) && !(await rejoin(id))) { location.hash = '#/join/' + id; return; }   // a new tab: the server knows your seat
  const token = getToken(id);
  if (wsId === id && ws) return;
  screen = null; V = null; ui.sel = null; release(); ui.carry = null; ui.back = null; ui.peek = false;
  // the screen before stays until the game arrives (a bare "Connecting…" page flashed between them); shown only when slow
  clearTimeout(matchScreen.slow); matchScreen.slow = setTimeout(() => { if (!V && wsId === id) app.innerHTML = `<div class="mscr pre"><p class="wait">Connecting…</p></div>`; }, 600);
  const connect = () => {
    wsId = id;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${id}?token=${encodeURIComponent(token)}`);
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.t === 'build') return checkBuild(m.build);
      if (m.t === 'view') { const prev = V; V = m.view; V.rx = Date.now() / 1000; clog(`view in: toAct=${V.game && V.game.toAct} pend=${V.game && V.game.pending ? V.game.pending.kind : '-'}${PB.busy ? ' (queued: steps playing)' : ''}`); onView(prev); }
      else if (m.t === 'error' && m.error === 'unknown match or seat') { disconnect(); location.hash = '#/'; toast('That match has ended'); }
      else if (m.t === 'error') { clog('server refused: ' + m.error); toast(m.error); }
    };
    ws.onclose = () => { clog('socket closed, reconnecting'); if (wsId === id) setTimeout(() => { if (wsId === id) connect(); }, 1000); };
  };
  connect();
  // back from the background (a phone switched apps, a laptop woke): a socket that died quietly reconnects at once
  matchScreen.wake = () => { if (document.hidden || wsId !== id) return;
    if (!ws || ws.readyState > 1) { if (ws) ws.onclose = null; connect(); } };
}
const send = msg => {
  clog('send ' + (msg.t === 'act' ? JSON.stringify(msg.action).slice(0, 50) : msg.t) + (ws && ws.readyState === 1 ? '' : ' DROPPED (socket ' + (ws ? ws.readyState : 'none') + ')')); if (!(ws && ws.readyState === 1)) { if (msg.t === 'act') toast('Reconnecting… try again in a moment'); return false; } return ws.send(JSON.stringify(msg)); };   // a dropped move says so (feedback 2026-10-04: clicks that did nothing)
// ?clicklog: a live record of presses, clicks and what the game did with them, in a corner (chasing clicks that do
// nothing, 2026-10-04). Off unless asked for; it costs nothing then.
const CLOG = new URLSearchParams(location.search).has('clicklog');
function clog(line) {
  if (!CLOG) return;
  let box = document.getElementById('clog');
  if (!box) { box = document.createElement('pre'); box.id = 'clog'; box.style.cssText = 'position:fixed;left:6px;bottom:6px;z-index:9999;max-width:520px;max-height:46vh;overflow:hidden;margin:0;padding:6px 8px;background:rgba(0,0,0,.82);color:#9f9;font:11px/1.35 ui-monospace,monospace;pointer-events:none;white-space:pre-wrap'; document.body.append(box); }
  const t = (performance.now() / 1000).toFixed(2);
  box.textContent = (t + ' ' + line + '\n' + box.textContent).split('\n').slice(0, 30).join('\n');
}
if (CLOG) {
  const what = el => { const h = el && el.closest && (el.closest('.hc') || el.closest('[id], [class]')); return !h ? String(el && el.tagName) : (h.dataset.id ? 'card ' + h.dataset.id : h.id ? '#' + h.id : '.' + String(h.className.baseVal ?? h.className).split(' ').slice(0, 2).join('.')); };
  const state = () => { try { const v = V && V.game; return `busy=${PB.busy} step=${ui.step ? ui.step.kind : '-'} toAct=${v ? v.toAct : '-'} you=${V ? V.you : '-'} pend=${v && v.pending ? v.pending.kind : '-'} ws=${ws ? ws.readyState : '-'}`; } catch { return ''; } };
  addEventListener('pointerdown', e => clog(`down ${what(e.target)} | ${state()}`), true);
  addEventListener('click', e => clog(`click ${what(e.target)}${e.isTrusted ? '' : ' (redirected)'}`), true);
}
// The copy of the picked card that plays: the one clicked (copies can differ in strength: a buffed one beside a plain
// one), else the strongest, which is what the engine plays when no copy is named.
const selCopy = () => {
  const hand = V.game.hand || [], same = hand.filter(h => h.id === ui.sel);
  return same.find(h => h.iid === ui.selIid) || same.reduce((a, h) => (!a || h.str > a.str ? h : a), null) || {};
};
const selPlaces = d => d.places[ui.sel] || [];
const placeAction = target => ({ kind: 'place', card_id: ui.sel, target });
const act = action => { if (action.kind === 'place' && ui.carry != null) { release(); ui.carry = null; }   // a held card placed is played, not put back
  ui.sel = null; ui.roam = null; ui.hover = null; send({ t: 'act', action }); };
// The hand's grip (carry.js): with a mouse, a card picked (clicked, or dragged out) leaves the hand and hangs over the pointer
// until it is placed or put back (Martin, 2026-11-13: drag and drop, or click to pick up and click to place, as Hearthstone).
// A card with no painting yet is carried like any other; let go over a crossroad, it lands there without the flight (flight.js turns the painting into the piece).
const canGrip = id => FLIGHT && !touch() && !matchMedia('(prefers-reduced-motion: reduce)').matches;
function grip(el, id, iid) {
  const h = (V.game.hand || []).find(h => h.iid === iid);
  carry(el.querySelector('.mcard'), manaCard(CARDS[id], { str: h ? h.str : undefined, cost: h ? h.cost : null, w: 100 }), flightGeo()); ui.carry = iid;   // its piece on the pointer
}
// A card let go of without being placed goes back to its place in the hand, which opens for it as it comes.
function ungrip() {
  if (ui.carry == null || (ui.sel && ui.selIid === ui.carry)) return;
  const iid = ui.carry; ui.carry = null;
  if (!carrying()) return;
  ui.back = iid; drawGame();
  carryDrop(document.querySelector(`#hand .hc[data-iid="${iid}"] ${('.mcard')}`), () => { if (ui.back === iid) { ui.back = null; if (screen === 'game') drawGame(); } });
}

// A new view: its events (static/timeline.js) play as steps, each view drawn for its step's length, the new view last.
// Views arriving meanwhile wait their turn: the next playback starts from the last step shown, so nothing is cut short.
const PB = { busy: false, queue: [], t: null };
const DUR_REVEAL_HOLD = DUR.reveal * 0.62;   // s: the opponent's card held at the centre before it flies (game.css @keyframes reveal)
// A flown card touches down (flight.js): the board draws the piece landing, with the landing's sound (the step that put it
// there drew the crossroad as it was, so it made none).
const landNow = covered => { if (screen !== 'game') return; drawBoard(); sfx(covered ? 'cover' : 'land', LAND_HIT); };
const LAND_HIT = HIT_DELAY;   // s from the cut to the piece's impact (flight.js: none for Impact, game.css landf for the glow)
// the painted ground
const plateSrc = () => '/static/kit2/plate_hex.webp';
function onView(prev) {
  if (PB.busy) { PB.queue.push(V); V = PB.shown; return; }   // keep showing the step in play
  const motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;   // reduced motion: the new view at once
  const steps = motion && (screen === 'game' || screen === null) ? plan(prev, V, CARDS) : [{ view: V, step: null }];
  if (steps.length === 1) { ui.step = null; showView(prev); played();  return; }   // a replay moves on after an update with nothing to animate too
  PB.busy = true; PB.target = V;   // the view these steps play towards
  const run = (i, before) => {
    const { view, step } = steps[i];
    V = PB.shown = view; ui.step = step; V.rx = Date.now() / 1000;
    showView(before);
    if (!step) return finish(view);
    if (step.kind === 'food' || step.kind === 'raid') foodStep(step);
    const fe = step.kind === 'land' && step.cr ? flightEnd(dcr(step.cr)) : null;   // a landing waits for its card's flight (flight.js)
    clearTimeout(PB.t); PB.t = setTimeout(() => run(i + 1, view), step.dur * 1000 / (window.AK_SPEED || 1) + (fe ? Math.max(0, fe - Date.now()) : 0));   // AK_SPEED: tests only
  };
  const finish = shown => {
    PB.busy = false; ui.step = null; played();
    if (PB.queue.length) { const latest = PB.queue[PB.queue.length - 1]; PB.queue = []; V = latest; return onView(shown); }
       // a replay moves on once this one has played out
  };
  run(0, prev);
}
// A card in your hand that gains strength rises out of the hand, its number changes up there, and it settles back (Martin,
// 2026-10-15, after Hearthstone's hand buffs). The hand redraws on every view, so the motion is timed from when its step began
// (--ago, a negative delay) and carries on across redraws; the old number and the new are both drawn, and CSS swaps them.
const RISE_MS = 1100, rising = new Map();   // iid: { step, t0, was, now }
// Tell the server the screen has played the events out: a bot opponent waits for it before its next move (server._watched).
function played() {
  if (!wsId || 0 || !V || !V.game) return;
  const ev = V.game.events || [];
  if (ev.length && ev[ev.length - 1].seq !== played.seq) { played.seq = ev[ev.length - 1].seq; send({ t: 'played', seq: played.seq }); }
}
function stopPlayback() { clearTimeout(PB.t); PB.busy = false; PB.queue = []; ui.step = null; }
// Your move never waits on an animation (player report 2026-10-04: clicks on cards did nothing while the opponent's moves
// were still playing, the clock running; after the mulligan, the clicks during the 1.5 s 'your turn' step did nothing). A
// press while steps play, when the newest view puts a decision to you, skips to that view, and the click lands on what is
// there now.
let skipped = null;
function skipToYourMove(e) {
  if (!PB.busy || 0 || screen !== 'game') return;
  const latest = PB.queue.length ? PB.queue[PB.queue.length - 1] : PB.target;   // the newest view: queued, else the one playing
  if (!latest || !latest.game || latest.game.toAct !== latest.you) return;
  const shown = PB.shown; clearTimeout(PB.t); PB.busy = false; PB.queue = []; ui.step = null; V = latest; V.rx = Date.now() / 1000;
  showView(shown); played();
  skipped = { x: e.clientX, y: e.clientY, at: Date.now() };
}
addEventListener('pointerdown', skipToYourMove, true);
// The press began on the screen as it was, so the browser has no click to give (its press and release fell on different
// elements): on the release, what now stands under the pointer is clicked, and a late native click is dropped.
let noClickUntil = 0;
addEventListener('pointerup', e => {
  if (!skipped || Date.now() - skipped.at > 1500) { skipped = null; return; }
  skipped = null; noClickUntil = Date.now() + 400;
  const el = document.elementFromPoint(e.clientX, e.clientY); if (el) el.click();
}, true);
addEventListener('click', e => { if (e.isTrusted && Date.now() < noClickUntil) { noClickUntil = 0; e.stopPropagation(); e.preventDefault(); } }, true);

function showView(prev) {
  ui.flyIid = null;   // the card in flight (flight.js) is in the hand again, or gone from it, as this view says
  // While an animation the player started must play out (the tutorial's fruit on Next), new views wait: a redraw would cut
  // it short. The first held view's predecessor is kept, so what changed meanwhile still animates when they apply.
  const hold = (ui.animUntil || 0) - Date.now();
  if (screen === 'game' && hold > 0) { if (!showView.kept) showView.kept = prev; clearTimeout(showView.t);
    showView.t = setTimeout(() => { const p = showView.kept; showView.kept = null; showView(p); }, hold + 20); return; }
  if (prev && prev.phase === 'lobby' && V.phase === 'playing') sfx('found');   // your friend joined
  if (V.phase === 'lobby') return lobbyScreen();
  if (!prev || prev.phase !== 'playing' && V.phase === 'playing') ui.peek = false;
  if (prev && prev.phase === 'playing' && V.phase !== 'playing') showChallenge();
  if (prev && prev.game && V.game && prev.game.history.length > V.game.history.length) ui.sel = null;
  // One-shot animation input: what the board and food were before this view (same game only).
  ui.anim = prev && prev.game && V.game && prev.game.history.length <= V.game.history.length && prev.you === V.you
    ? { board: viewerBoard(prev), food: { A: prev.game.food[prev.you], B: prev.game.food[prev.you === 'A' ? 'B' : 'A'] },
        income: { A: prev.game.income[prev.you], B: prev.game.income[prev.you === 'A' ? 'B' : 'A'] },
        hand: prev.game.hand.map(h => h.iid), oppHand: prev.game.handCount[prev.you === 'A' ? 'B' : 'A'], hist: prev.game.history.length,
        fromStones: !(ui.step && ui.step.kind === 'food' && !ui.step.income),   // only region income flies from the stones
        // a card's food flies from the animals whose doing it is; food eaten (Hungry) flies to the animals that ate it
        flow: ui.step && ui.step.kind === 'food' && !ui.step.income && ui.step.from
          ? { kind: ui.step.kind, side: rel(ui.step.player), at: ui.step.from.map(f => ({ cr: dcr(f.cr), n: f.n })) } : null } : null;
  if (ui.step && ui.step.kind === 'yourturn' && screen === 'game') { turnPlate(); turnCue.until = Date.now() + 900; }
  gameScreen();
}

// Before the match: the key art dimmed, the menus' granite. Waiting for a friend: the code to send, on one piece.
function lobbyScreen() {
  screen = 'lobby';
  const link = `${location.origin}/#/join/${V.id}`;
  app.innerHTML = `<div class="mscr pre"><div class="piece lobbyp"><div class="bigcode">${V.id}</div>
      <button class="slab" id="copy">${matchMedia('(hover: none)').matches ? 'Share link' : 'Copy link'}</button><p>Waiting for your friend to join</p></div>
    <a class="backbtn leave" href="#/"><span>Leave</span></a></div>`;
  document.getElementById('copy').onclick = () => shareLink(link, 'A match in Animal Kingdom');   // a phone's share sheet, straight from the tap
}

function seatLabel(p) {
  const s = V.seats[p];
  if (!s) return '';
  if (s.bot) return esc(s.name || 'Bot');   // its band, as the server named it ("Expert Bot")
  return p === V.you ? 'You' : esc(s.name || 'Opponent');
}

// The turn clock (matches between two people): the free window, then the game bank, of whoever must act.
const mmss = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
function drawClock() {
  const el = document.getElementById('clock'), c = V && V.game && V.game.clock;
  if (!el) return;
  if (!c || !c.on) { el.innerHTML = ''; el.className = 'clock'; return; }   // every view states the clock: {on: false} when there is none
  const spent = c.now + (Date.now() / 1000 - V.rx) - c.since, free = Math.max(0, c.free - spent);
  const bank = Math.max(0, c.bank[c.holder] - Math.max(0, spent - c.free)), left = free + bank;
  el.className = `clock${left < 10 ? ' low' : ''}`;
  el.innerHTML = `<b>${mmss(free > 0 ? free : bank)}</b>`;
  el.dataset.tip = `${c.holder === V.you ? 'Your' : "Your opponent's"} time: ${mmss(free)} for this move, then ${mmss(bank)} in the bank`;
}
setInterval(() => { if (screen === 'game') drawClock(); }, 250);

// Viewer space: you are always 'A' on the left; the server's seats are mapped through these.
const opp = () => V.you === 'A' ? 'B' : 'A';
const rel = p => p === V.you ? 'A' : p === 'wild' ? 'W' : 'B';   // W: a Wild animal, no one's (the Locusts)
const dcr = cr => { if (V.you === 'A') return cr; const [c, r] = cr.split(','); return `${MAP.cols + 1 - Number(c)},${r}`; };

// What the seat can do right now, in viewer space.
function decision() {
  const G = V.game, d = { mine: V.phase === 'playing' && G.toAct === V.you, rings: [], hqRing: false, crChoice: {}, handPick: new Set(), cardOpts: [], otherOpts: [], places: {}, pend: null };
     // a replay shows what you were asked, read-only
  if (!d.mine) return d;
  d.pend = G.pending; d.places = G.legal.place;
  if (d.pend && d.pend.mode === 'choice') {
    for (const o of d.pend.options) {
      if (o.kind === 'cr') d.crChoice[dcr(o.cr || o.v)] = o.v;
      else if (o.kind === 'hq') d.hqRing = true;   // "It roams" may take the enemy den
      else if (o.kind === 'hand' && d.pend.kind === 'mulligan') d.handPick.add(o.v);   // the mulligan picks in the hand itself
      else if (o.kind === 'hand') { const h = G.hand.find(h => h.iid === o.v) || {}; d.cardOpts.push({ ...o, str: h.str, cost: h.cost }); }   // any other pick from your hand is laid out in the middle: a lit hand reads as "play one" (feedback 2026-10-01)
      else if (o.kind === 'card') d.cardOpts.push(o);
      else d.otherOpts.push(o);
    }
    d.rings = Object.keys(d.crChoice);
    ui.sel = null;
  } else {
    if (ui.sel && !d.places[ui.sel]) ui.sel = null;
    const ids = Object.keys(d.places);
    if (!ui.sel && ids.length === 1 && d.pend) ui.sel = ids[0];   // a "play this card" prompt: preselect it
    if (ui.sel) for (const t of selPlaces(d)) { if (t[0] === 'cr') d.rings.push(dcr(t[1])); else d.hqRing = true; }
  }
  return d;
}

// ------------------------------------------------------------------ game screen
// Hover text in the box screen sits on a small dark plaque by the pointer, never in a browser tooltip.
function wireTips(root) {
  if (matchMedia('(hover: none)').matches) return;   // touch: a tap would leave the label standing
  let tip = document.getElementById('tip');
  if (!tip) { tip = document.createElement('div'); tip.id = 'tip'; tip.className = 'tip'; document.body.appendChild(tip); }
  root.addEventListener('mouseover', e => { const t = e.target.closest('[data-tip]'); if (!t) { tip.style.display = 'none'; return; }
    tip.textContent = t.dataset.tip; tip.style.display = 'block'; });
  // beside the pointer on its right, or on its left where the window has no room (the flag, the replay's controls)
  // and under it, or above it at the window's bottom
  root.addEventListener('mousemove', e => { const w = tip.offsetWidth, h = tip.offsetHeight, right = e.clientX + 14 + w <= innerWidth - 8;
    tip.style.left = (right ? e.clientX + 14 : e.clientX - 14 - w) + 'px';
    tip.style.top = (e.clientY + 16 + h <= innerHeight - 8 ? e.clientY + 16 : e.clientY - 10 - h) + 'px'; });
  root.addEventListener('mouseleave', () => tip.style.display = 'none');
}
// A food step's dots (foodfx.js): region income from the held regions' dots, a card's food from its animals, a leader's
// from the leader on the rail; a raid's out of the den it hit.
function foodStep(step) {
  const seat = step.kind === 'raid' ? step.den : step.player, side = rel(seat);
  const before = V.game.food[seat] + (step.kind === 'raid' ? step.n : -step.n);   // this step's view already holds the new count
  const sources = s => {
    if (step.kind === 'food' && step.income) {
      const dots = [...document.querySelectorAll(`#board .rdot.${s}`)], n = step.n;
      return dots.map((el, i) => ({ el, n: Math.floor(n / dots.length) + (i < n % dots.length ? 1 : 0) })).filter(x => x.n);
    }
    const tiles = (step.from || []).map(f => ({ el: document.querySelector(`#board .cr[data-cr="${dcr(f.cr)}"]`), n: f.n })).filter(x => x.el);
    if (tiles.length) return tiles;
    const lead = document.querySelector(`#mrail .ltok[data-lead="${s}"]`);
    return lead ? [{ el: lead, n: step.n }] : [];
  };
  playFood({ ...step, side }, before, sources);
}

function gameScreen() {
  if (screen !== 'game') {
    screen = 'game';
    app.innerHTML = `<div class="game kit${(' hexb')}${(' mana')}" id="scr"><div id="world"><img src="${plateSrc()}" alt="" draggable="false"></div><div id="stage">
      <div class="abs ledge"></div>
      <div id="board"></div>
      <div class="abs menu snd" id="sndbtn"></div><div class="panel setp" id="setp"></div>
      <div class="abs menu hs" id="series" data-tip="History"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 8v4l3 2"/></svg></div>
      <div class="abs menu" id="pilebtn" data-tip="Remove Pile"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3c-4.4 0-7.5 3-7.5 7 0 2.4 1.1 4.2 3 5.2V19h9v-3.8c1.9-1 3-2.8 3-5.2 0-4-3.1-7-7.5-7z"/><circle cx="9" cy="11" r="1.5"/><circle cx="15" cy="11" r="1.5"/><path d="M10.5 19v2M13.5 19v2"/></svg></div><div class="pmodal" id="pilep"></div>
      <div class="abs opphand" id="opphand"></div>
      <div class="abs menu fb" id="fbbtn" data-tip="Send feedback"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z"/></svg></div>
      <div class="abs menu chatbtn" id="chatbtn" data-tip="Friends">${ICON_FRIENDS}${chatBadge()}</div>
      <div class="abs menu" id="menubtn"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 21V3.5"/><path d="M6 4h12l-3 4.5 3 4.5H6"/></svg></div>
      <div class="abs hand" id="hand"></div>
      <div class="abs tbtn" id="tbtn"></div>
      <div class="abs waiting" id="waiting"></div>
      <div class="abs prompt" id="choicebar"></div>
      <div class="abs opts" id="opts"></div>
      <div class="abs reveal" id="reveal"></div>
      <div class="panel mine" id="mine"></div><div class="panel theirs" id="theirs"></div>
      <div class="panel histp" id="histp"><h4>History<span class="removed" id="removed"></span></h4><div class="hist" id="hist"></div></div>
      <div class="abs mrail" id="mrail"></div><div class="abs mlast" id="mlast"></div><div class="abs mhover" id="mhover"></div>
      <div class="endov" id="endov"></div>
      <div class="endov" id="concov"><div class="endbox ask"><b>Concede this game?</b>
        <div class="btns"><button class="slab" id="keep">Keep playing</button><button class="play danger" id="concede">Concede</button></div></div></div></div></div>`;
    fitStage(false); wireTips(document.getElementById('scr'));
    const $ = id => document.getElementById(id);
    // The flag concedes, after the question in the middle of the board (Keep playing, Escape or a click beside it says no).
    // In a tutorial it leaves for home at once: there is nothing to lose.
    const ask = $('concov');
    $('fbbtn').onclick = e => { e.stopPropagation(); feedback(); };
    wireChatButton($('chatbtn'));
    $('menubtn').onclick = e => { e.stopPropagation();  ask.classList.add('on'); };
    ask.onclick = e => { e.stopPropagation(); if (e.target === ask) ask.classList.remove('on'); };
    $('keep').onclick = e => { e.stopPropagation(); ask.classList.remove('on'); };
    $('concede').onclick = e => { e.stopPropagation(); ask.classList.remove('on'); send({ t: 'concede' }); };
    // The series opens the history; the decks (drawRail) open their lists.
    const toggle = k => e => { e.stopPropagation(); ui.panel = ui.panel === k ? null : k; showPanel(); };
    $('series').onclick = toggle('hist'); $('pilebtn').onclick = toggle('pile');
    app.querySelectorAll('.panel').forEach(el => el.onclick = e => e.stopPropagation());
    $('scr').addEventListener('click', () => { if (ui.panel) { ui.panel = null; showPanel(); } });
    $('tbtn').onclick = e => { e.stopPropagation(); if (canEnd(lastDecision)) { sfx('endturn'); act({ kind: 'pass' }); } };
    $('sndbtn').dataset.tip = 'Settings';
    $('sndbtn').innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
    $('sndbtn').onclick = e => { e.stopPropagation(); if (ui.panel !== 'set') { const p = $('setp'); p.innerHTML = `<h4>Settings</h4>${settingsBody()}`; wireSettings(p); }
      ui.panel = ui.panel === 'set' ? null : 'set'; showPanel(); };
    $('setp').onclick = e => e.stopPropagation(); preload();
    wireBoard(); wireRail();
  }
  drawGame();
}

// A match opens on its versus moment (Martin, 2026-10-01, after Hearthstone's "Jaina vs Gul'dan"): over the key art, your
// deck's cover card comes in from the left and the opponent's from the right, "vs" between them; it holds, then lifts off
// the board. Nothing to press; a click skips it. Once per game, never in a lesson or a replay.
function drawIntro() {
  const G = V.game, key = V.id + ':' + V.rematches;
  if (V.phase !== 'playing' || !G || G.history.length || 0 || !V.id || ui.intro === key) return;
  ui.intro = key;
  const side = p => { const s = V.seats[p] || {}, list = Object.keys(V.lists[p] || {}), mine = p === V.you;
    const own = mine && playable().find(d => d.id === s.deck || d.id === 'my:' + s.deck);
    const cover = own ? coverFor(own) : coverOf(list, CARDS);
    // One object per player (Martin, 2026-10-02): their cover card, their name in its bar (yours too: a nameplate, not a
    // sentence; the #tag only tells namesakes apart, so it stays on the profile), and in a ranked match their rating as it
    // stands going in, in a gem set into the card's bottom edge. No deck name: a person's deck name is never shown to their opponent.
    const name = s.bot ? seatLabel(p) : esc((s.name || 'Opponent').split('#')[0]), c = CARDS[cover];
    return `<div class="iside ${p === V.you ? 'A' : 'B'}"><div class="iobj">${manaCard({ ...c, name }, { cost: null, owner: p === V.you ? 'A' : 'B', w: 230 })}</div></div>`; };
  const el = document.createElement('div'); el.className = 'intro'; el.id = 'intro';
  el.innerHTML = `${side(V.you)}<div class="ivs">vs</div>${side(opp())}`;
  document.getElementById('scr').appendChild(el); fitNames(el); sfx('versus', .55);
  const done = () => { el.classList.add('out'); setTimeout(() => el.remove(), 600); };
  // it never takes a click: the first press anywhere sends it off and still reaches what's under it (a mulligan card;
  // Martin, 2026-10-02: the first mulligan clicks were lost to it)
  addEventListener('pointerdown', done, { once: true, capture: true });
  setTimeout(done, matchMedia('(prefers-reduced-motion: reduce)').matches ? 1400 : 2600);
}

// Your turn begins: the tablet lights up once, and a tab in the background says so in its title (a friend's clock is running).
function turnCue(mine) {
  const key = V.id + ':' + V.rematches + ':' + (V.game && V.game.round);
  if (mine && turnCue.was === false && turnCue.key !== key) {
    turnCue.key = key;   // the plate itself is the timeline's step (showView), after everything before it has played
    if (document.hidden) document.title = 'Your turn · Animal Kingdom';
  }
  if (!mine || !document.hidden) document.title = 'Animal Kingdom';
  turnCue.was = mine;
}
addEventListener('visibilitychange', () => { if (!document.hidden) { document.title = 'Animal Kingdom'; if (matchScreen.wake) matchScreen.wake(); } });
// Hearthstone's plate, on granite, with the knock.
function turnPlate(text = 'Your turn', quiet = false) {
  if (!quiet) sfx('yourturn');
  const b = document.createElement('div'); b.className = 'yourturn' + (quiet ? ' skipped' : ''); b.innerHTML = `<b>${text}</b>`;
  document.getElementById('stage').appendChild(b); setTimeout(() => b.remove(), 1500);
}

// A phone in a match: a swipe down never reloads the page (pull-to-refresh is off on the game screen, game.css), and the
// screen stays awake while a game is being played, so it can't lock and drop the connection during the opponent's turn.
let wake = null;
function keepAwake(on) {
  if (on && !wake && navigator.wakeLock && !document.hidden) {
    wake = navigator.wakeLock.request('screen').then(l => { l.onrelease = () => { wake = null; }; return l; }).catch(() => { wake = null; });
  } else if (!on && wake) { wake.then(l => l && l.release()).catch(() => {}); wake = null; }
}
addEventListener('visibilitychange', () => { if (!document.hidden && screen === 'game' && V && V.phase === 'playing') keepAwake(true); });   // the lock lapses while hidden

function drawGame() {
  const G = V.game, you = V.you, them = opp(), d = decision(), $ = id => document.getElementById(id);
  const playing = V.phase === 'playing', choosing = !!(d.pend && d.pend.mode === 'choice');
  keepAwake(playing);
  lastDecision = d;
  const mull = (G.decision === 'mulligan');   // the mana rules' screen (mana.css); its opening hand shown in full
  $('scr').classList.toggle('mana', true);
  drawIntro();
  if ($('scr').classList.contains('rp') !== false) { $('scr').classList.toggle('rp', false); fitStage(false); }   // a replay: upright its controls take a row under the stage
  $('menubtn').style.display = playing && V.id ? '' : 'none';
  $('fbbtn').style.display = V.id ? '' : 'none'; $('fbbtn').classList.toggle('alone', $('menubtn').style.display === 'none');   // feedback: any real match or replay, never the lab   // the flag: only a game in play (never the lab or a replay)
  { const n = [$('menubtn'), $('fbbtn')].filter(e => e.style.display !== 'none').length, w = VIEW.port ? 88 : 52;
    $('series').style.right = 16 + w * n + 'px'; $('pilebtn').style.right = 16 + w * (n + 1) + 'px';
    $('sndbtn').style.right = 16 + w * (n + 2) + 'px'; $('chatbtn').style.right = 16 + w * (n + 3) + 'px'; }   // the Remove Pile left of History; Friends, left of sound
  $('chatbtn').style.display = V.id && hasFriends() ? '' : 'none';   // a real match or replay, once you have a friend   // sound, left of History   // History, left of feedback and the flag
  ['menubtn', 'fbbtn', 'series', 'pilebtn', 'sndbtn', 'chatbtn'].forEach(id => { $(id).style.left = ''; });
  ['menubtn', 'fbbtn', 'series', 'pilebtn', 'sndbtn', 'chatbtn'].filter(id => $(id).style.display !== 'none').forEach((id, i) => { $(id).style.left = 16 + 52 * i + 'px'; });   // the mana screen: a plain row at the top left
  $('menubtn').dataset.tip = ('Concede');
  // the flag concedes a match; a tutorial has nothing to concede, so the same button is a house: back home
  $('menubtn').querySelector('svg').innerHTML = ('<path d="M6 21V3.5"/><path d="M6 4h12l-3 4.5 3 4.5H6"/>');
  if (!playing) $('concov').classList.remove('on');

  // Top left: the turn (a match is one game while there is one map); it opens the history.
  drawHistory(G); drawLists(G); showPanel();

  // The opponent's card is about to be shown large (below): note when it will have landed, before anything is drawn over it.
  turnCue(playing && G.current === you);   // the card shown, flown down, landed and its dust settled
  // The opponent's hand: one small back each, centred across the board from yours.
  const nb = G.handCount[them], step = 50, bx0 = STAGE.w / 2 - (46 + (nb - 1) * step) / 2;
  const A = ui.anim, oppDrew = A ? Math.max(0, nb - A.oppHand) : 0;   // their new cards slide down into their hand
  const slot = i => `${i >= nb - oppDrew ? ' drawn' : ''}" style="left:${bx0 + i * step}px;animation-delay:${(i - (nb - oppDrew)) * 0.12}s`;
  $('opphand').innerHTML = Array.from({ length: nb }, (_, i) => `<div class="abs back${slot(i)}"></div>`).join('');

  // Your hand, centred under the board.
  const held = G.hand.filter(h => h.iid !== ui.flyIid && h.iid !== ui.carry);   // the card in flight or in the grip has left it (flight.js, carry.js)
  // One order for the hand all match (Martin, 2026-11-21): the opening hand sorts from cheapest to dearest once, as dealt;
  // a card the mulligan brings in takes the place of the one it replaced; after that the order holds ("why does it
  // re-shuffle after the mulligan ends?") and a card drawn joins at the right. The cards in flight keep their places.
  {
    const byCost = (x, y) => ((x.cost ?? CARDS[x.id].mana ?? 99) - (y.cost ?? CARDS[y.id].mana ?? 99)) || CARDS[x.id].name.localeCompare(CARDS[y.id].name);
    const ids = G.hand.map(h => h.iid), key = V.id + ':' + V.rematches;
    let order = ui.handOrder && ui.handOrder.key === key ? ui.handOrder.iids : null;
    if (!order) order = [...G.hand].sort(byCost).map(h => h.iid);
    else { const fresh = ids.filter(i => !order.includes(i));
      order = mull ? order.map(i => ids.includes(i) ? i : fresh.shift()).filter(i => i != null).concat(fresh)   // a swap: the new card in the old one's place
        : order.filter(i => ids.includes(i)).concat(fresh); }
    ui.handOrder = { key, iids: order };
    held.sort((x, y) => order.indexOf(x.iid) - order.indexOf(y.iid));
  }
  // the mana screen: a row of pieces under the board (the full cards, large, while the opening hands are chosen)
  const n = held.length, cw = (mull ? 176 : 100), gap = (mull ? 18 : n > 1 ? Math.min(12, (760 - n * cw) / (n - 1)) : 0),
    x0 = ((STAGE.w / 2)) - (n * cw + (n - 1) * gap) / 2;
  const hand = $('hand'); hand.classList.toggle('mull', mull); hand.classList.toggle('free', (!!(d.pend && d.pend.mode !== 'choice' && !mull)));   // a free play: the costs step back
  let drawnK = 0;
  const was = new Map([...hand.querySelectorAll('.hc')].map(el => [el.dataset.iid, el.offsetLeft]));   // where each card stood
  hand.innerHTML = held.map((h, i) => {
    const c = CARDS[h.id], can = d.mine && !d.handPick.size && !choosing && d.places[h.id], pick = d.handPick.has(h.iid);
    // the mana rules light only a card you can play now: on your opponent's turn none is lit (Martin, 2026-11-20); never
    // dimmed while the opening hands are chosen
    const dim = (!mull && !pick && !can);
    const cls = [c.rarity, can ? 'can' : '', pick ? 'pick' : '', h.id === ui.sel && h.iid === selCopy().iid ? 'sel' : '', dim ? 'dim' : ''].join(' ');   // one copy of the picked card rises
    // a card just drawn slides in from the deck (bottom right), the second a beat after the first; a card an effect made or
    // fetched (a Kitten, a Young Stag) came from no deck, so it rises into its place instead (Martin, 2026-10-31: flying in
    // from the deck "just looks weird")
    const drawn = A && !A.hand.includes(h.iid) ? ++drawnK : 0, made = false;
    const from = drawn ? `${made ? '' : `--fx:${deckX() + DECK_W / 2 - (x0 + i * (cw + gap) + cw / 2)}px;`}animation-delay:${(drawn - 1) * 0.14}s;` : '';
    const html = manaCard(c, { str: h.str, cost: h.cost, w: cw, iid: h.iid });
    return `<div class="hc ${cls}${drawn ? (made ? ' made' : ' drawn') : ''}${h.iid === ui.back ? ' away' : ''}" data-iid="${h.iid}" data-id="${h.id}" style="left:${x0 + i * (cw + gap)}px;z-index:${i + 1};${from}">${html}</div>`;
  }).join('');
  fitNames(hand); fitPlaques(hand);
  // a card that left (played, discarded) or came: the others slide to their new places rather than jump
  if (FLIGHT && !matchMedia('(prefers-reduced-motion: reduce)').matches) hand.querySelectorAll('.hc:not(.drawn):not(.made)').forEach(el => {
    const dx = was.get(el.dataset.iid) - el.offsetLeft;
    if (dx) el.animate([{ translate: `${dx}px 0` }, { translate: '0 0' }], { duration: 260 / (window.AK_SPEED || 1), easing: 'cubic-bezier(.3,.7,.4,1)' });
  });
  // touch: press and hold a card to read it (a tap picks it): it opens large in the middle, clear of the finger, and stays
  // after the finger lifts until the next tap (feedback 2026-10-01); the click that ends a hold does nothing
  hand.querySelectorAll('.hc').forEach(el => {
    let t = null;
    const read = () => { const h = (V.game.hand || []).find(h => String(h.iid) === el.dataset.iid); readCard(el.dataset.id, h && h.str); };
    el.onpointerdown = () => delete el.dataset.held;   // each press starts unheld
    holdEvents(el, () => { clearTimeout(t); t = setTimeout(() => { el.dataset.held = '1'; read(); }, 350); }, () => clearTimeout(t), () => clearTimeout(t));
    el.oncontextmenu = e => { e.preventDefault(); if (!document.querySelector('.readov')) read(); };   // right-click, or a long press sent as one
  });
  hand.querySelectorAll('.hc').forEach(el => el.onclick = e => {
    e.stopPropagation();
    if (Date.now() - (ui.dragEnd || 0) < 300) return;   // the click a drag's release makes
    if (el.dataset.held) { delete el.dataset.held; clog('card: ignored (it was held to read)'); return; }   // it was held to read, not tapped
    const iid = Number(el.dataset.iid), id = el.dataset.id;
    if (d.handPick.has(iid)) { clog('card: picked for the choice'); return act({ kind: 'choice', choice: iid }); }
    if (!d.mine || !d.places[id] || !el.classList.contains('can')) { clog(`card: refused (mine=${d.mine} places=${!!d.places[id]} can=${el.classList.contains('can')} pend=${d.pend ? d.pend.kind : '-'} picks=${d.handPick.size})`); return; }   // a dimmed copy (the tutorial lights one) does nothing
    const again = ui.sel === id && selCopy().iid === iid;   // the same copy again drops it; another copy of it picks that one
    if (!again) sfx('pick');
    if (!again && canGrip(id)) { if (ui.carry != null) { release(); ui.carry = null; } grip(el, id, iid); }
    ui.sel = again ? null : id; ui.selIid = again ? null : iid; ui.roam = null; ui.hover = null; drawGame();
  });
  // a press dragged out of the hand picks the card up; its release over a crossroad places it, anywhere else puts it back
  hand.querySelectorAll('.hc.can').forEach(el => el.addEventListener('pointerdown', e => {
    if (e.pointerType !== 'mouse' || e.button !== 0 || !canGrip(el.dataset.id)) return;
    ui.press = { x: e.clientX, y: e.clientY, el, id: el.dataset.id, iid: Number(el.dataset.iid) };
  }));
  ungrip();

  const tb = $('tbtn');
  const pips = '';
  if (playing && G.current === you) {
    tb.className = 'abs tbtn A num' + (canEnd(d) ? ' can' : '') + (Date.now() < (turnCue.until || 0) ? ' yours' : ''); tb.innerHTML = `<b>End turn</b><span class="pips">${pips}<span class="clock" id="clock"></span></span>`; delete tb.dataset.tip;
  } else if (playing) { tb.className = 'abs tbtn B num'; tb.innerHTML = `${(G.decision === 'mulligan' ? '<b>Opening hands</b>' : '<b>Your opponent\'s turn</b>')}<span class="pips">${pips}<span class="clock" id="clock"></span></span>`; tb.dataset.tip = 'Your opponent\'s turn'; }
  else { tb.className = 'abs tbtn'; tb.innerHTML = ''; delete tb.dataset.tip; }

  // A pending choice: the asking card and its rule; card options float above the hand.
  const bar = $('choicebar'), opts = $('opts'), waiting = $('waiting');
  waiting.textContent = ''; opts.classList.remove('on'); opts.innerHTML = '';
  bar.classList.toggle('mull', !!(d.pend && d.pend.kind === 'mulligan'));   // the mulligan asks in the middle of the empty board, over your hand
  if (d.pend && d.pend.kind === 'mulligan') {
    const k = d.pend.returned;
    // a player's first real match says what the mulligan is for, in plain words (the tutorial skips it); later ones, the short rule
    const first = !store('ak:mullseen');
    const how = ('Click a card to swap it for another from your deck. No copy of a card you swap can come back.');
    bar.innerHTML = `<b>Mulligan · ${k} of ${d.pend.cap} replaced</b>` + ((`<p>${how}</p><div class="btns"><span class="skip" id="skip">${k ? 'Done' : 'Keep hand'}</span></div>`));
    bar.classList.add('on');
    if ($('skip')) $('skip').onclick = e => { e.stopPropagation(); store('ak:mullseen', '1'); act({ kind: 'choice', choice: SKIP }); };
  } else if (d.pend) {   // a choice only ever reaches the screen after the steps that led to it have played
    // a choice inside your leader's power names the leader and reads its power, not its card (the leaders prototype)
    const src = d.pend.leader && G.leaders && G.leaders[V.you] ? { name: (CARDS[d.pend.source] || {}).name, text: G.leaders[V.you].text } : d.pend.source && CARDS[d.pend.source];
    // One line at the top centre, where the eyes are: the card that asks and its rule, then Skip when it may be declined;
    // named options as slabs under it.
    const other = d.otherOpts.map((o, i) => `<span class="skip" data-x="${i}">${o.label}</span>`).join('');
    const skip = d.pend.optional ? '<span class="skip" id="skip">Skip</span>' : '';
    // offered cards float over the board: a toggle lowers them to read the board, and raises them again (a new choice shows them)
    const pk = JSON.stringify(d.cardOpts.map(o => o.v)); if (ui.optsKey !== pk) { ui.optsKey = pk; ui.optsHidden = false; }
    const peek = d.cardOpts.length ? `<span class="skip" id="optpeek">${ui.optsHidden ? 'Show cards' : 'Hide cards'}</span>` : '';
    // a pick from your hand is headed by what it does; the asking card's rule stays under it
    bar.innerHTML = `<div class="line">${src ? `<b>${src.name}</b><p>${src.text}</p>` : '<b>Choose</b>'}${peek}${skip}</div>` + (other ? `<div class="btns">${other}</div>` : '');
    bar.classList.add('on');
    if (d.cardOpts.length) {
      opts.innerHTML = d.cardOpts.map((o, i) => { const c = CARDS[o.id]; return `<div class="hc ${c.rarity}" data-o="${i}">${(manaCard(c, { ...(o.str == null ? {} : { str: o.str }), cost: o.cost ?? c.mana ?? null, w: 170 }))}</div>`; }).join('');
      opts.classList.add('on'); opts.classList.toggle('hid', !!ui.optsHidden); opts.classList.toggle('many', d.cardOpts.length > 6); fitNames(opts); fitPlaques(opts);
      $('optpeek').onclick = e => { e.stopPropagation(); ui.optsHidden = !ui.optsHidden; drawGame(); };
      opts.querySelectorAll('[data-o]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.cardOpts[el.dataset.o].v }); });
    }
    bar.querySelectorAll('[data-x]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.otherOpts[el.dataset.x].v }); });
    const sk = $('skip'); if (sk) sk.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: SKIP }); };
  } else if (d.mine && ui.roam === 'den' && G.legal && G.legal.leader) {   // your leader picked on a touch screen: its power and Use
    bar.innerHTML = `<div class="line">${leaderPanel('A')}<span class="skip use" id="actuse">Use</span><span class="skip" id="actno">Cancel</span></div>`;
    bar.classList.add('on');
    $('actuse').onclick = e => { e.stopPropagation(); sfx('pick'); ui.roam = null; act({ kind: 'leader' }); };
    $('actno').onclick = e => { e.stopPropagation(); ui.roam = null; drawGame(); };
  } else {
    bar.classList.remove('on');
    if (playing && G.decision === 'their_choice') waiting.textContent = 'Opponent is choosing';
    else if (playing && G.decision === 'mulligan' && G.toAct !== you) waiting.textContent = 'Opponent is mulliganing';
  }
  clearTimeout(drawGame.think);
  if (playing && G.toAct === them && V.seats[them].bot) {
    const ver = V.version;
    drawGame.think = setTimeout(() => { if (V && V.version === ver && screen === 'game') waiting.textContent = 'Bot is thinking'; }, 2500);
  }
  // The opponent's card, shown large at the centre as it is played, then flown down onto its crossroad (the piece lands as it arrives).
  const st = ui.step;   // what this step shows (static/timeline.js); a view without events just shows what changed
  if (A) A.fx = st ? []
    : G.history.slice(A.hist).flatMap(m => m.fx).map(f => f.owner ? { ...f, owner: rel(f.owner) } : f);
  if (st && st.kind === 'leader') {   // a leader's power used: the leader's card shown large, shrinking into its place by the den
    const [tx, ty] = leaderAt(rel(st.player)), rv = $('reveal');
    rv.innerHTML = ((manaCard({ ...CARDS[st.card], text: ((G.leaders || {})[st.player] || {}).text || CARDS[st.card].text }, { owner: rel(st.player), w: 190, str: null }))) + '<div class="actlbl">Leader</div>'; fitNames(rv); fitPlaques(rv);
    rv.style.setProperty('--tx', `${tx - STAGE.w / 2}px`); rv.style.setProperty("--ty", `${ty - (VIEW.port ? 560 : 300)}px`);
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on'); sfx('reveal');
  }
  if (st && st.kind === 'raidin') {   // the opponent's raiding card, shown large and diving into the den it hits
    const rv = $('reveal'), den = document.querySelector(`#board .mden.${rel(st.den)}`);
    rv.innerHTML = manaCard(CARDS[st.card], { owner: rel(st.player), w: 190, cost: (CARDS[st.card] || {}).mana ?? null }); fitNames(rv); fitPlaques(rv);
    const cy = VIEW.port ? 560 : 300; let tx = 0, ty = 0;
    if (den) { const s = $('scr').getBoundingClientRect(), k = s.width / STAGE.w, r = (den.querySelector('.core') || den).getBoundingClientRect();
      tx = (r.left + r.width / 2 - s.left) / k - STAGE.w / 2; ty = (r.top + r.height / 2 - s.top) / k - cy; }
    rv.style.setProperty('--tx', `${tx}px`); rv.style.setProperty('--ty', `${ty}px`);
    rv.style.setProperty('--hx', `${VIEW.port ? 184 - STAGE.w / 2 : 0}px`); rv.style.setProperty('--hy', `${5 - cy}px`);   // from their hand
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on'); sfx('reveal');
  }
  if (st && st.kind === 'reveal') {   // the opponent's card, shown large and flown down onto its crossroad; the next step lands it
    const [tx, ty] = crossroadAt(dcr(st.cr)), rv = $('reveal');
    rv.innerHTML = (manaCard(CARDS[st.card], { owner: rel(st.player), w: 190, cost: (CARDS[st.card] || {}).mana ?? null })); fitNames(rv); fitPlaques(rv); rv.style.setProperty('--tx', `${tx - STAGE.w / 2}px`); rv.style.setProperty("--ty", `${ty - (VIEW.port ? 560 : 300)}px`);
    rv.style.setProperty('--hx', `${VIEW.port ? 184 - STAGE.w / 2 : 0}px`); rv.style.setProperty('--hy', `${5 - (VIEW.port ? 560 : 300)}px`);   // their hand's centre
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on'); sfx('reveal');
    // after its hold the card flies down and lands as the piece (flight.js); without art it shrinks away as before
    clearTimeout(drawGame.rvfly); drawGame.rvfly = setTimeout(() => { if (ui.step === st && fly(rv.querySelector(('.mcard')), $('board').querySelector(`[data-cr="${dcr(st.cr)}"]`), st.card, dcr(st.cr), viewerGame().board[dcr(st.cr)], landNow, null, null, (flightGeo()))) rv.classList.remove('on'); },
      DUR_REVEAL_HOLD * 1000 / (window.AK_SPEED || 1));
  }
  drawBoard(d);
  if (A) soundsFor(document, CARDS);   // one sound per thing that just moved
  drawRail(G, d); drawLast(G);
  if ((ui.sel || d.rings.length)) { clearTimeout(stackTimer); stackCr = null; manaHover(null); }   // a hovered piece never covers the places a click acts on
  drawEnd();
}

// Where the edge pieces stand, on the wide stage or the upright one (game.css .port): the hand's top, centre and width, the
// deck's and End turn's centre tops.

// The history strip and both decklists, shared by both game screens.
// One move in small: a draw is its count on the team's boss (as a held payout); a placement the unit, as on the board.
function histItem(m, i) {
  const side = rel(m.seat), t = side === 'A' ? 'a' : 'b';
  if (m.kind === 'draw') { const dr = m.fx.find(f => f.k === 'draw' && f.seat === m.seat); return `<div class="hi draw ${side}" data-h="${i}">${chalk('+' + (dr ? dr.n : 0))}</div>`; }
  return `<div class="hi unit ${side}" data-h="${i}"><div class="face" style="${portrait(m.card, 32)}"></div><img src="/static/kit2/rim_${t}.webp" alt="" draggable="false"></div>`;
}
// Hovering a move says what it did; in a replay, clicking it goes to that move.
function wireHist(root, G) {
  root.querySelectorAll('[data-h]').forEach(el => {
    const m = G.history[el.dataset.h];
    el.onmouseenter = () => { if (m.kind === 'place' || m.kind === 'roam' || m.kind === 'act' || m.kind === 'leader') cardPop(el, m.card, moveLine(m), 'below'); else { pop.className = 'pop'; pop.innerHTML = `<div class="ev">${moveLine(m)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex'; const r = el.getBoundingClientRect(); pop.style.left = Math.min(r.left, innerWidth - 200) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; } };
    el.onmouseleave = () => { pop.style.display = 'none'; pop.style.minHeight = ''; };
    
  });
}
function drawHistory(G) {
  const hist = document.getElementById('hist');
  let hs = '', lastT = null;
  G.history.forEach((m, i) => {
    if (m.round !== lastT) { hs += `<div class="t">Turn ${m.round}</div>`; lastT = m.round; }
    hs += histItem(m, i);
  });
  hist.innerHTML = hs; hist.scrollTop = hist.scrollHeight;
  wireHist(hist, G);
  const removed = document.getElementById('removed');
  removed.innerHTML = `Removed <b>${G.removed.length}</b>`;
}
function drawLists(G) {
  const sum = o => Object.values(o).reduce((a, b) => a + b, 0), you = V.you, them = opp();
  const mine = document.getElementById('mine'), theirs = document.getElementById('theirs');
  mine.innerHTML = `<h4>Your deck<span class="n">${sum(G.deckLeft)} left</span></h4><div class="rows">${rows(V.lists[you], G.deckLeft)}</div>`;
  theirs.innerHTML = `<h4>Opponent's cards<span class="n">${sum(G.unseen)} left</span></h4><div class="rows">${rows(V.lists[them], G.unseen)}</div>`;
  wirePops(mine); wirePops(theirs); fitStrips(mine); fitStrips(theirs);
  drawPile(G);
}
// The Remove Pile, from its button beside History: a dialog in full focus (Gwent's graveyard), every removed card in full
// at its strength now (a Python grows there too), yours then your opponent's, the latest first. Escape, ×, or a click beside it closes.
function drawPile(G) {
  const side = (who, label) => {
    const cs = (G.pile || []).filter(c => c.owner === who).reverse();
    return `<div class="t">${label}<span class="n">${cs.length}</span></div>` + (cs.length
      ? `<div class="pgrid">${cs.map(c => `<div class="pc ${CARDS[c.id].rarity}">${manaCard(CARDS[c.id], { str: c.str, cost: CARDS[c.id].mana, w: 150 })}</div>`).join('')}</div>`
      : '<div class="nil">Nothing removed yet</div>');
  };
  const el = document.getElementById('pilep');
  el.innerHTML = `<div class="pbox"><h4>Remove Pile<span class="n">${(G.pile || []).length}</span><span class="x" id="pclose">×</span></h4>`
    + `<div class="pbody">${side(V.you, 'You')}${side(opp(), 'Your opponent')}</div></div>`;
  const close = e => { e.stopPropagation(); ui.panel = null; showPanel(); };
  el.onclick = e => e.target === el ? close(e) : e.stopPropagation();
  document.getElementById('pclose').onclick = close;
}
function showPanel() {
     // the tutorial never opens the decklists or the history: nothing it teaches, and they give away its deal
  for (const [k, id] of [['mine', 'mine'], ['theirs', 'theirs'], ['hist', 'histp'], ['set', 'setp'], ['pile', 'pilep']]) document.getElementById(id).classList.toggle('on', ui.panel === k);
  if (ui.panel === 'hist') { const h = document.getElementById('hist'); h.scrollTop = h.scrollHeight; }
}
// The stage keeps its design size (STAGE) and scales to fit the window. The painted ground under it is one painting wider
// and taller than any window (21:9 to 4:3), scaled with the stage, so the window shows more savanna, never bars.
function fitStage(redraw = true) {
  const st = document.getElementById('stage'); if (!st) return;
  // a window taller than wide gets the upright layout (board.js setView); turning the phone redraws the screen
  const port = innerHeight > innerWidth && false, flip = port !== VIEW.port;   // the mana rules' screen is the desktop one, scaled, on any window
  setView(port); document.getElementById('scr').classList.toggle('port', port);
  // upright, a replay keeps a row under the stage for its controls (game.css .port .rbar): the stage fits the window less it,
  // with 60 stage px of savanna kept above and below (about what a phone shows in play), so the hand, which sits at the edge,
  // stays clear of your den: the board comes out a little smaller
  const rp = port && 0 ? 56 : 0, H = innerHeight - rp;
  const k = Math.min(innerWidth / STAGE.w, H / (STAGE.h + (rp ? 120 : 0))), t = `scale(${k}) translate(${-STAGE.w / 2}px, ${-STAGE.h / 2}px)`;
  st.style.transform = t; document.getElementById('world').style.transform = t;
  st.style.top = document.getElementById('world').style.top = rp ? `calc(50% - ${rp / 2}px)` : '';
  st.style.setProperty('--rp', `${rp / k}px`);
  const plate = document.querySelector('#world img'), src = plateSrc();
  if (!plate.src.endsWith(src)) plate.src = src;
  // the savanna around the stage, in stage px: the pieces at the screen's edges (hands, corners, deck, End turn) sit at the
  // window's edges, not the stage's, so a window of another shape widens the ground between them, never leaves them floating
  st.style.setProperty('--above', `${Math.max(0, (H / k - STAGE.h) / 2)}px`);
  st.style.setProperty('--side', `${Math.max(0, (innerWidth / k - STAGE.w) / 2)}px`);
  st.style.setProperty('--k', k);   // the stage's scale: a phone held sideways shows it at half size
  if (flip && redraw && V && V.game) drawGame();
}

function moveLine(m) {
  const who = m.seat === V.you ? 'You' : 'Opponent', name = id => CARDS[id] ? CARDS[id].name : id;
  const fx = m.fx.map(f => {
    if (f.k === 'cover') return `covered ${name(f.card)}`;
    if (f.k === 'remove') return `removed ${name(f.card)}`;
    if (f.k === 'placed') return `${f.owner === V.you ? 'you' : 'your opponent'} placed ${name(f.card)} on it`;
    if (f.k === 'scare') return `scared off ${name(f.card)}`;
    if (f.k === 'draw') return m.kind === 'draw' && f.seat === m.seat ? null : `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'your opponent '}drew ${f.n}`;
    if (f.k === 'lose') return `${f.seat === V.you ? 'you' : 'your opponent'} lost ${f.n} food`;
    if (f.k === 'food') return `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'your opponent '}${f.n > 0 ? 'gained' : 'paid'} ${Math.abs(f.n)} food`;
    return null;
  }).filter(Boolean);
  const what = m.kind === 'draw' ? `drew ${(m.fx.find(f => f.k === 'draw' && f.seat === m.seat) || { n: 0 }).n}` : m.target[0] === 'hq' ? (('raided the den')) : m.kind === 'roam' ? 'roamed' : m.kind === 'act' ? `used ${CARDS[m.card] ? CARDS[m.card].name : 'its'} ${CARDS[m.card] && /(^|\. )Echo\./.test(CARDS[m.card].text) ? 'Echo' : 'Action'}`
    : m.kind === 'leader' ? `used ${CARDS[m.card] ? CARDS[m.card].name : 'the leader'}'s power` : '';
  return [`${who} · turn ${m.round}`, what, ...fx].filter(Boolean).join(' · ');
}

function viewerBoard(v) {
  const out = {}, rl = p => p === v.you ? 'A' : p === 'wild' ? 'W' : 'B';
  for (const [cr, st] of Object.entries(v.game.board)) {
    const c = v.you === 'A' ? cr : `${MAP.cols + 1 - Number(cr.split(',')[0])},${cr.split(',')[1]}`;
    out[c] = st.map(u => ({ ...u, owner: rl(u.owner) }));
  }
  return out;
}
function viewerGame() {
  const G = V.game, you = V.you, them = opp(), board = {};
  for (const [cr, st] of Object.entries(G.board)) board[dcr(cr)] = st.map(u => ({ ...u, owner: rel(u.owner) }));
  return { board, leaders: G.leaders ? { A: G.leaders[you], B: G.leaders[them] } : {}, food: { A: G.food[you], B: G.food[them] }, income: { A: G.income[you], B: G.income[them] },
    regionFood: G.regionFood && { A: G.regionFood[you], B: G.regionFood[them] }, winFood: G.winFood };
}
function viewerMap() {
  if (V.you === 'A') return MAP;
  const flip = cr => `${MAP.cols + 1 - Number(cr.split(',')[0])},${cr.split(',')[1]}`;
  return { ...MAP, regions: MAP.regions.map(r => ({ ...r, c: [MAP.cols - r.c[0], r.c[1]], ...(r.corners ? { corners: r.corners.map(flip) } : {}) })) };
}

let lastDecision = null;
// Whether the deck (the Draw action) and the End turn button act now: one test lights them and lets their click through.
const canEnd = d => !!(d && d.mine && !d.pend && V.game.canPass && !d.noPass);
const ANIM_MAX = 3500;   // ms: longer than any board animation a step starts (fruit, pits, gem, landings)
function drawBoard(d) {
  d = d || lastDecision; lastDecision = d;
  let g = viewerGame();
  let preview = null;
  if (ui.sel && ui.hover && d.rings.includes(ui.hover)) {
    preview = { cr: ui.hover, id: ui.sel, str: selCopy().str };
  }
  // A step's animations play once. A redraw while they run (the pointer moving over the board, a card picked) draws the
  // same moment and carries them on from where they are, never restarting them nor cutting them short (Martin, 2026-10-02:
  // the food gem glitched while counting up).
  const now = performance.now();
  if (ui.anim) { ui.animKeep = { A: ui.anim, t0: now }; ui.anim = null; }
  const keep = ui.animKeep && now - ui.animKeep.t0 < ANIM_MAX ? ui.animKeep : null;
  let A = keep ? keep.A : null; const ago = keep ? now - keep.t0 : 0;
  const st = ui.step, strike = st && st.by ? { from: dcr(st.by), to: dcr(st.cr) } : null;   // what removed a unit answers in its beat
  const fire = st && st.src ? st.src.map(dcr) : null;   // the animals whose own effect this is: their trigger marks brighten
  const G = V.game, bases = G.bases ? { A: (G.bases[V.you] || []).map(dcr), B: (G.bases[opp()] || []).map(dcr) } : null;   // the mana board's bases
  const draw = () => renderBoard(document.getElementById('board'), viewerMap(), g, CARDS, { bases, rings: d.rings, hqRing: d.hqRing, preview, anim: A, ago, strike, fire, leaders: g.leaders,
    beat: endBeat(), current: V.phase === 'playing' ? rel(V.game.current) : null });
  draw();
  if (startBeat(g, A, ago)) draw();
  const fc = flying(); if (fc && document.querySelector(`#board .cr.flown[data-cr="${fc}"]`)) flightLanded(fc);   // the piece is landing: the card's flight is over
}

// The end's beat (board.js): the game's last move shown rather than told. A den taken falls apart once the animal that took it
// has landed in its mouth; a den that reached the food to win lights up once its gem has counted to the total. It starts once
// per game (beat.key), as the move plays; a game already over when drawn (a reload, a replay's end) shows how it ended at once.
function startBeat(g, A, ago) {
  const res = V.game.result, key = `${V.id}-${V.rematches}`;
  if (!res || (ui.beat && ui.beat.key === key) || res.reason !== 'food' || res.winner === null) return false;
  const motion = !matchMedia('(prefers-reduced-motion: reduce)').matches, now = Date.now();
  const side = rel(res.winner);
  if (g.food[side] < V.game.food[res.winner]) return false;   // the winning food hasn't arrived yet
  const gem = document.querySelector(`#board .dcount.${side}.tick`), count = gem ? +gem.dataset.lag + +gem.dataset.dur : 0;
  ui.beat = { key, kind: 'lit', side, t0: A && motion ? now - ago + count + 150 : now - BEAT_MS - 1 };
  if (ui.beat.t0 > now - BEAT_MS) {   // the board shakes as a den is struck (once, not on a redraw)
    if (ui.beat.kind === 'fall') setTimeout(() => document.getElementById('board')?.animate([0, 1, 2, 3, 4, 5, 6].map(i => ({ transform: i === 6 ? 'none'
      : `translate(${Math.sin(i * 2.3) * 16 * (1 - i / 6)}px, ${Math.cos(i * 3.1) * 16 * (1 - i / 6)}px)` })), { duration: 800 }), ui.beat.t0 - now);
  }
  return true;
}
const endBeat = () => { const key = V && `${V.id}-${V.rematches}`;
  return ui.beat && ui.beat.key === key ? { kind: ui.beat.kind, side: ui.beat.side, ago: Date.now() - ui.beat.t0 } : null; };

const LEADER_MANA = n => ({ power: `Hero power: costs ${n} mana.`, once: `Once per game: costs ${n} mana.`, passive: 'Passive.' });   // the mana rules
function leaderPanel(side) {
  const L = viewerGame().leaders[side]; if (!L) return '';
  const c = CARDS[L.id], who = side === 'A' ? 'Your leader' : "Your opponent's leader", kind = (LEADER_MANA(V.game.abilityCost));
  return `<b>${c ? c.name.split(':')[0] : L.id}</b><p class="lk">${who}. ${kind[L.kind] || ''}</p><p>${L.text}</p>`;
}
// The mana rules' controls around the board (mana.css; Martin, 2026-11-20, the den layout), placed from where the board
// stands (board.js RAIL), so none of them lies on it: each side's leader left of its base row, with its power's price; each
// side's deck right of the board level with its base row, a pile of its face-down cards (their tokens, empty) as thick as
// the cards left in it, with the count, a click showing its list beside it; your mana and End turn (#tbtn, its own element)
// right of your den, their mana right of theirs. Food is in the dens (board.js). Their mana while it isn't their turn is
// their next turn's, unspent.
const LEAD_W = 84, LEAD_H = 97, DECK_W = 84, DECK_H = 97, RAIL_GAP = 24;
const deckX = () => RAIL.right + RAIL_GAP * 2;   // the decks' left edge
function drawRail(G, d) {
  const el = document.getElementById('mrail'); if (!el) return;
  if ((!G)) { el.innerHTML = ''; return; }
  const you = V.you, them = opp(), mana = G.mana || {}, cost = G.abilityCost;
  const lead = side => {
    const p = side === 'A' ? you : them, L = (G.leaders || {})[p], R = RAIL[side];
    const can = side === 'A' && L && L.usable && d && d.mine && !d.pend, dim = L && L.spent;   // the gold ring says when your power can be used
    // a power's cost in the token's drawer, where a card's strength sits (Martin, 2026-11-21); used this turn, the token
    // dims, no label (Martin, 2026-11-21: "remove AI-slop label")
    const isPow = L && L.kind === 'power';
    const tok = L ? `<div class="ltok${isPow ? ' pw' : ''}${can ? ' can' : ''}${dim ? ' dim' : ''}" data-lead="${side}"><div class="unit ${side}" style="--tw:${LEAD_W}px">${leaderToken(L.id, side, CARDS, LEAD_W)}${isPow ? powerCostHTML(L.cost ?? cost) : ''}</div></div>` : '';
    return `<div class="mlead ${side}" style="left:${R.l - RAIL_GAP - LEAD_W}px;top:${R.y - LEAD_H / 2}px">${tok}</div>`;
  };
  // a deck: one token a few cards, so it thins as it is drawn; empty, the bare slot
  const deck = side => {
    const n = (G.deckCount || {})[side === 'A' ? you : them] ?? 0, layers = n ? Math.min(7, Math.ceil(n / 4)) : 0, R = RAIL[side];
    // each card under the top one a step darker, so the pile's edges read (its shadow side)
    const tok = (i, top) => `<div class="unit ${side}" style="--tw:${DECK_W}px;transform:translateY(${-i * 4}px)"><img class="tkbase" src="${tokenBase(side)}" alt="" draggable="false"${top ? '' : ` style="filter:brightness(${(.45 + .35 * i / layers).toFixed(2)}) drop-shadow(0 2px 1px rgba(0,0,0,.55))"`}>${top ? numeral(n) : ''}</div>`;
    const pile = layers ? Array.from({ length: layers }, (_, i) => tok(i, i === layers - 1)).join('') : `<div class="unit ${side} empty" style="--tw:${DECK_W}px"><img class="tkbase" src="${tokenBase(side)}" alt="" draggable="false">${numeral(0)}</div>`;
    return `<div class="mdeck ${side}" data-deck="${side}" style="left:${deckX()}px;top:${R.y - DECK_H / 2}px">${pile}</div>`;
  };
  const m = mana[you] || { left: 0, total: 0 }, t = mana[them] || { left: 0, total: 0 };
  el.innerHTML = lead('B') + lead('A') + deck('B') + deck('A')
    // what is left of the turn's mana as X/N right of the crystals (Martin, 2026-11-21)
    + `<div class="mmana A">${pipsHTML(m.left, m.total)}<b class="mcount">${m.left}/${m.total}</b></div>`
    + `<div class="mmana B">${pipsHTML(t.left, t.total)}<b class="mcount">${t.left}/${t.total}</b></div>`;
  // a deck's list opens beside it, toward the screen's edge
  for (const [side, id] of [['A', 'mine'], ['B', 'theirs']]) { const p = document.getElementById(id);
    p.style.left = `${deckX() + DECK_W + RAIL_GAP}px`; p.style.right = 'auto'; p.style.margin = '0';
    if (side === 'B') { p.style.top = `${RAIL.B.y - DECK_H / 2}px`; p.style.bottom = 'auto'; }
    else { p.style.top = 'auto'; p.style.bottom = `${800 - (RAIL.A.y + DECK_H / 2)}px`; } }
}
// The rail's leaders read on hover (a leader's power) and your leader's power is pressed there; a deck shows its list on a click.
function wireRail() {
  const rail = document.getElementById('mrail'); if (!rail || rail.wired) return; rail.wired = true;
  const hide = () => { pop.style.display = 'none'; pop.style.minHeight = ''; };
  rail.addEventListener('mouseover', e => {
    const lead = e.target.closest('[data-lead]');
    if (lead && !touch()) { pop.className = 'pop' + ((' mpop')); pop.innerHTML = `<div class="ev lead">${leaderPanel(lead.dataset.lead)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex';
      const r = lead.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
      pop.style.left = Math.max(10, r.left - w - 12) + 'px'; pop.style.top = Math.max(8, Math.min(r.top, innerHeight - h - 10)) + 'px'; return; }
    hide();
  });
  rail.addEventListener('mouseout', e => { if (!rail.contains(e.relatedTarget)) hide(); });
  rail.addEventListener('click', e => {
    const lead = e.target.closest('[data-lead]'), d = lastDecision; e.stopPropagation();
    if (lead && lead.dataset.lead === 'A') { const L = viewerGame().leaders.A;
      if (L && L.usable && d && d.mine && !d.pend) { hide(); sfx('pick'); ui.roam = null; ui.sel = null; return act({ kind: 'leader' }); } }
    if (lead && touch()) return readOverlay(leaderPanel(lead.dataset.lead));
    const deck = e.target.closest('[data-deck]'); if (deck) { const k = deck.dataset.deck === 'A' ? 'mine' : 'theirs'; ui.panel = ui.panel === k ? null : k; showPanel(); }
  });
}
// The mana rules' last plays, left of the board: the newest first, each the piece played (or the animal that moved, or the
// leader) with who did what; a turn the server skipped (nothing its player could pay for) as its own line. Hovering a play
// shows its card and what it did.
function drawLast(G) {
  const el = document.getElementById('mlast'); if (!el) return;
  if ((!G)) { el.innerHTML = ''; return; }
  const key = `${V.id}-${V.rematches}`, turnOf = m => (m.round - 1) * 2 + (m.seat === G.first ? 0 : 1);
  const items = G.history.map((m, i) => ({ t: turnOf(m), m, i })).concat((ui.skips || []).filter(k => k.key === key).map(k => ({ t: k.turn, skip: k.seat })));
  items.sort((a, b) => a.t - b.t);
  // the piece in its team's rim says who, the board says what: no words beside it (Martin, 2026-11-20); hover reads the card
  const row = x => x.skip ? '' : `<div class="row" data-h="${x.i}"><div class="mini">${x.m.card ? `<div class="unit ${rel(x.m.seat)}" style="--tw:40px">${leaderToken(x.m.card, rel(x.m.seat), CARDS, 40)}</div>` : ''}</div></div>`;
  const last = items.slice(-6).reverse();
  el.innerHTML = last.map(row).join('');
  el.querySelectorAll('[data-h]').forEach(r => {
    const m = G.history[r.dataset.h];
    r.onmouseenter = () => { if (!m.card || !CARDS[m.card]) return;
      pop.className = 'pop mpop'; pop.innerHTML = manaCard(CARDS[m.card], { owner: rel(m.seat), cost: CARDS[m.card].mana ?? null, w: 180 }) + `<div class="ev">${moveLine(m)}</div>`;
      pop.style.minHeight = '0'; pop.style.display = 'flex'; fitPlaques(pop);
      const b = r.getBoundingClientRect(); pop.style.left = (b.right + 12) + 'px'; pop.style.top = Math.max(8, Math.min(b.top - 120, innerHeight - pop.offsetHeight - 10)) + 'px'; };
    r.onmouseleave = () => { pop.style.display = 'none'; pop.style.minHeight = ''; pop.className = 'pop'; };
  });
}
// Play the picked card from the hand to `target` (['cr', crossroad] or ['hq', den]; `el`, its element on the board): it
// leaves the hand at once, for good, and goes there, flying to a crossroad to turn into the piece (flight.js fly()), or
// diving into the den's ball (dive()); the hand closes up behind it and keeps it out until the server's view says where it
// went (showView), or, a play refused, gives it back.
function play(target, el) {
  const c = selCopy(), start = ui.carry === c.iid ? release() : null; ui.carry = null;
  const from = start ? null : document.querySelector(`#hand .hc[data-iid="${c.iid}"] .mcard`);
  const html = manaCard(CARDS[ui.sel], { str: c.str, cost: c.cost, w: 100 });
  if (target[0] === 'cr') fly(from, el, ui.sel, target[1], viewerGame().board[target[1]], landNow, html, start, flightGeo());
  else dive(from, el.querySelector('.core') || el, html, start);
  act(placeAction(target[0] === 'cr' ? ['cr', dcr(target[1])] : target));
  if (target[0] === 'cr') { clearTimeout(stackTimer); stackCr = target[1]; manaHover(null); }   // the piece landing under the pointer isn't read until the pointer moves on
  ui.flyIid = c.iid; drawGame();
  setTimeout(() => { if (ui.flyIid === c.iid && screen === 'game') { ui.flyIid = null; drawGame(); } }, 5000);   // a refused play: the card is back
}
const denTarget = d => ui.sel && selPlaces(d).find(t => t[0] === 'hq');   // the den the picked card may raid

// The drag (carry.js): a press on a playable card that moves picks it up; its release places it or puts it back.
addEventListener('pointermove', e => {
  const p = ui.press; if (!p || ui.dragging) return;
  if (!(e.buttons & 1)) { ui.press = null; return; }
  if (Math.hypot(e.clientX - p.x, e.clientY - p.y) < 6 || screen !== 'game') return;
  ui.press = null; ui.dragging = true; sfx('pick');
  if (ui.carry != null) { release(); ui.carry = null; }
  if (!(ui.sel === p.id && ui.selIid === p.iid && carrying())) grip(p.el, p.id, p.iid);
  ui.sel = p.id; ui.selIid = p.iid; ui.roam = null; ui.hover = null; drawGame();
});
addEventListener('pointerup', e => {
  ui.press = null;
  if (!ui.dragging) return;
  ui.dragging = false; ui.dragEnd = Date.now();
  const at = document.elementFromPoint(e.clientX, e.clientY), d = lastDecision;
  const g = at && at.closest('#board [data-cr]'), hq = at && at.closest('#board [data-hq]');
  if (g && d && d.mine && d.rings.includes(g.dataset.cr)) return play(['cr', g.dataset.cr], g);
  if (hq && d && d.mine && denTarget(d)) return play(denTarget(d), hq);
  ui.sel = null; drawGame();   // let go anywhere else: back into the hand
});

function wireBoard() {
  const board = document.getElementById('board');
  board.addEventListener('click', e => {
    if (Date.now() - (ui.dragEnd || 0) < 300) return;   // the click a drag's release makes
    const den = e.target.closest('[data-den]');   // a den opens that player's list
    if (den) { e.stopPropagation(); ui.panel = ui.panel === den.dataset.den ? null : den.dataset.den; showPanel(); return; }
    const lead = e.target.closest('[data-lead]');   // the leaders prototype: your leader's power, pressed (a tap reads it first)
    if (lead) { e.stopPropagation(); const L = viewerGame().leaders[lead.dataset.lead], d0 = lastDecision;
      if (lead.dataset.lead === 'A' && L && L.usable && d0 && d0.mine && !d0.pend) {
        if (touch() && ui.roam !== 'den') { ui.roam = 'den'; ui.sel = null; sfx('pick'); return drawGame(); }
        ui.roam = null; sfx('pick'); return act({ kind: 'leader' }); }
      if (touch()) readOverlay(leaderPanel(lead.dataset.lead));
      return; }
    const d = lastDecision;
    if (!d || !d.mine) { const g = touch() && e.target.closest('[data-cr]'); if (g) readStack(g.dataset.cr); return; }   // off your turn a tap only reads
    const hq = e.target.closest('[data-hq]');
    if (hq && d.pend && d.pend.mode === 'choice' && d.hqRing) return act({ kind: 'choice', choice: 'den' });
    if (hq && denTarget(d)) return play(denTarget(d), hq);
    const g = e.target.closest('[data-cr]'); if (!g) return;
    const cr = g.dataset.cr;
    if (cr in d.crChoice) return act({ kind: 'choice', choice: d.crChoice[cr] });
    if (ui.sel && d.rings.includes(cr)) return play(['cr', cr], g);
    if (ui.roam) { ui.roam = null; return drawGame(); }
    if (touch() && !ui.sel) readStack(cr);
  });
  board.addEventListener('mouseover', e => {
    const lead = e.target.closest('[data-lead]');   // a leader reads on hover: its ability as it stands
    if (lead && !touch()) { showStack(null, null); pop.className = 'pop' + ((' mpop')); pop.innerHTML = `<div class="ev lead">${leaderPanel(lead.dataset.lead)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex';
      const r = lead.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight;
      pop.style.left = Math.min(r.right + 10, innerWidth - w - 10) + 'px'; pop.style.top = Math.max(8, Math.min(r.top, innerHeight - h - 10)) + 'px'; return; }
    if (!lead && pop.querySelector('.ev.lead')) { pop.style.display = 'none'; pop.style.minHeight = ''; }
    const g = e.target.closest('[data-cr]'), cr = g ? g.dataset.cr : null;
    showStack(g, cr);
    if (cr === ui.hover) return;
    ui.hover = cr;
    if (ui.sel) drawBoard();
  });
  // touch: holding a piece reads its stack; so does tapping one when the tap would do nothing else
  let holdT = null, held = false;
  holdEvents(board, e => { held = false; clearTimeout(holdT); const g = e.target.closest('[data-cr]'); if (!g) return;
    holdT = setTimeout(() => { held = true; readStack(g.dataset.cr); }, 350); }, () => clearTimeout(holdT), () => clearTimeout(holdT));
  board.addEventListener('click', e => { if (held) { held = false; e.stopImmediatePropagation(); } }, true);   // a hold's lift does nothing else
  board.addEventListener('mouseleave', () => { showStack(null, null); if (ui.hover) { ui.hover = null; if (ui.sel) drawBoard(); } });
  // Right-click: with a card or an animal picked, puts it down; else reads the piece under it large, as in the hand (Martin,
  // 2026-11-16: "right-click card on board to show its detail, like when you right-click card in hand")
  board.addEventListener('contextmenu', e => {
    if (ui.sel || ui.roam) { e.preventDefault(); ui.sel = null; ui.roam = null; return drawGame(); }
    const lead = e.target.closest('[data-lead]');
    if (lead) { e.preventDefault(); return readOverlay(leaderPanel(lead.dataset.lead)); }
    const g = e.target.closest('[data-cr]'), st = g && V && V.game && viewerGame().board[g.dataset.cr];
    if (st && st.length && !document.querySelector('.readov')) { e.preventDefault(); showStack(null, null); readStack(g.dataset.cr); }
  });
}

// Hover a piece: the whole stack as cards, the top unit first, then each buried card top to bottom.
// Shown after a short rest on the piece, and never while targets are ringed (it would cover them).
let stackTimer = null, stackCr = null;
function showStack(g, cr) {
  if (touch()) return;   // touch reads a piece by holding or tapping it (readStack)
  if (cr === stackCr) return;
  stackCr = cr; clearTimeout(stackTimer); stackpop.style.display = 'none'; manaHover(null);
  const st = cr && viewerGame().board[cr];
  if (!st || !st.length || ui.sel || (lastDecision && lastDecision.rings.length)) return;
  stackTimer = (setTimeout(() => manaHover(cr), 120));
}
// The mana rules' board piece hovered: it grows where it stands and its plaque slides out under it (mana.css .mhover); what
// it covers and its timer beside it.
function manaHover(cr) {
  const el = document.getElementById('mhover'); if (!el) return;
  const st = cr && V && V.game && viewerGame().board[cr];
  if (!st || !st.length) { el.classList.remove('on'); el.innerHTML = ''; return; }
  const top = st[st.length - 1], under = st.slice(0, -1).reverse(), [x, y] = crossroadAt(cr), w = Math.round(tokenWidth() * 1.3), ph = w * 624 / 540;
  const side = top.owner === 'W' ? 'W' : top.owner;
  const notes = [top.timer ? resolvesIn(top.timer) : '', under.length ? `Covers ${under.map(u => `${(CARDS[u.id] || {}).name || u.id} (${u.str})`).join(', ')}` : ''].filter(Boolean);
  el.innerHTML = `<div class="abs" style="left:${x - w / 2}px;top:${y - ph / 2}px">${manaCard(CARDS[top.id], { str: top.str, cost: CARDS[top.id].mana ?? null, owner: side, w, iid: top.iid })}`
    + (notes.length ? `<div class="under" style="left:${w + 10}px;top:${ph * .3}px">${notes.map(esc).join('<br>')}</div>` : '') + '</div>';
  el.classList.remove('on'); void el.offsetWidth; el.classList.add('on'); fitPlaques(el);   // measured once shown (hidden, it has no height)
}
// A board piece's stack, as the hover popup (stackAt) and the read (readStack) both show it: each animal's card in its
// owner's form (viewer space: A is you), at its strength now, with its timer under it.
const stackSeat = u => u.owner === 'A' ? V.you : opp();
const timerLine = u => u.timer ? `<div class="tm">${resolvesIn(u.timer)}</div>` : '';
const stackCard = (u, attrs = '') => `<div class="sc ${u.owner}">${manaCard(CARDS[u.id], { str: u.str, cost: CARDS[u.id].mana ?? null, owner: u.owner, w: 170 })}${timerLine(u)}</div>`;
function readStack(cr) {
  const st = V && V.game && viewerGame().board[cr]; if (!st || !st.length) return;
  const top = st[st.length - 1], buried = st.slice(0, -1).reverse();
  readOverlay(cardRead(top.id, top.str, stackSeat(top), timerLine(top)) + (buried.length ? `<div class="under">${buried.map(u => stackCard(u)).join('')}</div>` : ''));
}

function drawEnd() {
  const ov = document.getElementById('endov'), G = V.game;
  if (V.phase === 'playing' || !G.result) { drawEnd.live = V.phase === 'playing'; ov.classList.remove('on');
    if (drawEnd.live && G.decision !== 'playing_out') { drawEnd.key = drawEnd.sounded = null; ui.beat = null; }   // a new game (a rematch reuses the match's id and count): its end is new; not a step of the last move
    return; }
  // The move that ended the game plays out first (the opponent's card shown and landed, a piece in the den, the fruit of the
  // last income or a Roar): the result shows once it has. Only for a game seen ending live, once; with reduced motion at once.
  const key = `${V.id}-${V.rematches}`;
  if (drawEnd.key !== key) {
    const motion = !(typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches);
    drawEnd.until = drawEnd.live && motion && G.result.reason !== 'concede' ? Date.now() + 900 : 0; drawEnd.key = key; drawEnd.live = false; drawEnd.since = Date.now(); }
  // a full den: the result waits for its beat (which waits for the move), never longer than 9 s
  if (drawEnd.until && G.result.reason === 'food' && G.result.winner !== null) {
    const b = ui.beat && ui.beat.key === key ? ui.beat : null;
    drawEnd.until = b ? Math.max(drawEnd.until, b.t0 + BEAT_MS) : Math.max(drawEnd.until, Math.min(Date.now() + 200, drawEnd.since + 9000)); }
  const wait = (drawEnd.until || 0) - Date.now();
  if (wait > 0) { ov.classList.remove('on'); clearTimeout(drawEnd.t); drawEnd.t = setTimeout(() => { if (screen === 'game') drawEnd(); }, wait + 20); return; }
  if (ui.peek) { ov.classList.remove('on'); document.getElementById('waiting').innerHTML = `<button class="slab" id="unpeek">Back to results</button>`; document.getElementById('unpeek').onclick = () => { ui.peek = false; drawGame(); }; return; }
  const you = V.you, them = opp(), w = G.result.winner;
  const live = drawEnd.sounded !== key && drawEnd.until && w !== null;   // a game seen ending live: its sound and its entrance, once
  if (live) sfx(w === you ? 'victory' : 'defeat');
  drawEnd.sounded = key;
  const res = w === null ? ['D', 'Draw'] : w === you ? ['A', 'Victory'] : ['B', 'Defeat'];
  const how = { food: `${w === you ? 'You' : 'Your opponent'} reached ${G.winFood} food`, starved: `${w === you ? 'Your opponent' : 'You'} ran out of food`, max_turns: 'Turn limit · more food wins', concede: w === you ? 'Your opponent conceded' : 'You conceded', timeout: w === you ? 'Your opponent ran out of time three turns in a row' : 'You ran out of time three turns in a row' }[G.result.reason] || G.result.reason;
  // a den taken: the board showed it (Martin, 2026-10-17); a full den says who reached the food, as the lessons' Victory does
  // (phone walkthrough finding 20: a Defeat on food said nothing)
  const howLine = `<div class="how">${how}.</div>`;
  const peek = `<button class="slab" id="peek">See the board</button>`;
  {
    // one game: its result; a series (best-of-3, back with the maps): the match's result and the score in the gems
    // a friend match: a Rematch is an offer the other player accepts or declines (Martin, 2026-11-05, as on chess.com)
    const rm = V.rematch || {}, rmLine = rm.offer === them ? '<div class="how">Your opponent wants a rematch.</div>'
      : rm.offer === you ? '<div class="how">Rematch offered.</div>' : rm.declined === them ? '<div class="how">Your opponent declined the rematch.</div>' : '';
    const rmBtns = rm.offer === them ? '<button class="slab" id="decline">Decline</button><button class="play" id="rematch">Rematch</button>'
      : rm.offer === you || rm.declined ? '' : '<button class="play" id="rematch">Rematch</button>';
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div>${howLine}
      ${rmLine}<div class="btns"><a class="slab" href="#/">Menu</a>${peek}${rmBtns}</div></div>`;
    const rb = document.getElementById('rematch'); if (rb) rb.onclick = () => send({ t: 'rematch' });
    const db = document.getElementById('decline'); if (db) db.onclick = () => send({ t: 'rematch_decline' });
  }
  const pk = document.getElementById('peek'); if (pk) pk.onclick = () => { ui.peek = true; drawGame(); };   // a lesson has none
  ov.classList.toggle('won', w === you); ov.classList.toggle('lost', w !== null && w !== you);   // the board behind: lit for a win, dusk for a loss
  ov.classList.toggle('enter', !!live);
  ov.classList.add('on');
}

window.__ak = () => ({ V, ui, d: lastDecision, PB });   // test hook: the headless play-through reads the view (and whether steps are playing)
window.__ak.cards = () => CARDS;   // test hook: the card pool as the client holds it
window.__ak.build = checkBuild;   // test hook: a socket naming another build
window.__ak.feed = v => { const prev = V; V = v; onView(prev); };   // test hook: play a recorded sequence of views through the client
boot();

