// Animal Kingdom web client: menu flow (home -> play -> pre-match) and the game screen.
// The server holds the game; this file only renders the seat's view and sends choices back.
import { hasArt, artUrl, stripArt, fitStrips } from './art.js';
import { cardHTML, fitNames, KEYWORDS, hasKeyword } from './card.js';
import { plan } from './timeline.js';
import { renderBoard, BEAT_MS, STAGE, VIEW, setView, crossroadAt, denMouthAt, gemAt, chalk, gemDigits, portrait } from './board.js';
import { collectionScreen as renderCollection, coverOf, deckBody, stripHTML, ICON } from './collection.js';
import { dd, wireDd, onHold, holdEvents } from './menu.js';
import { play as sfx, soundsFor, preload, volume, setVolume } from './sound.js';
import { openFeedback } from './feedback.js';
import { track } from './log.js';
import { loadNews, unread as newsUnread, newsScreen, showSince, hideSince } from './news.js';
import { openPresence, showChallenge, confirmFriend, shareLink, friendRow, friendLabel } from './friends.js';
import { initChat, badge as chatBadge, wireChatButton, ICON_FRIENDS, hasFriends } from './chat.js';
import { bindCoach, isLesson, lessonOf, lessonNow, narrowChoice, narrowPlaces, handLights, holdFood, shownRegion, lessonEnd, drawCoach } from './coach.js';

const app = document.getElementById('app'), pop = document.getElementById('pop'), stackpop = document.getElementById('stackpop');
const COVER = { cats_midrange: 'king_theron', canine_buff_tempo: 'lobo', aggro_hq_rush: 'verminus', colony_food_swarm: 'queen_honoria',
  egg_control: 'eon', food_otk: 'rat_king', ramp: 'borealis', goodstuff: 'gale' };
const RANK = { legendary: 0, rare: 1, common: 2 };
const SKIP = '__skip__';
const artStyle = id => hasArt(id) ? `style="background-image:url(${artUrl(id)})"` : '';
const sv = c => c.str === '*' ? -1 : c.str;
const store = (k, v) => { try { v === undefined ? null : localStorage.setItem(k, v); return localStorage.getItem(k); } catch { return null; } };
const tokenKey = id => 'ak:seat:' + id;
const getToken = id => { try { return sessionStorage.getItem(tokenKey(id)); } catch { return null; } };
const setToken = (id, t) => { try { sessionStorage.setItem(tokenKey(id), t); } catch { /* private mode: the tab just can't reconnect */ } };

let CARDS = {}, MAP, DECKS = [], ME = null;   // ME: your profile {id, name, tag, decks, history}
let V = null, ws = null, wsId = null, screen = null;
const ui = { sel: null, hover: null, peek: false, menu: false, panel: null };

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
function sortIds(ids) {
  return ids.sort((a, b) => RANK[CARDS[a].rarity] - RANK[CARDS[b].rarity] || sv(CARDS[a]) - sv(CARDS[b]) || CARDS[a].name.localeCompare(CARDS[b].name));
}
// A decklist in the game's panels: the collection's strips, each with the copies left.
function rows(list, counts) {
  return `<div class="dbody flat">${sortIds(Object.keys(list)).map(id => stripHTML(id, CARDS, counts ? (counts[id] || 0) : list[id])).join('')}</div>`;
}
const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
function cardPop(el, id, extra, place) {
  const c = CARDS[id], r = el.getBoundingClientRect();
  pop.className = 'pop ' + c.rarity;
  pop.innerHTML = cardHTML(c) + (extra ? `<div class="ev">${extra}</div>` : '');
  pop.style.display = 'flex'; fitNames(pop);
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
function readCard(id, str) {
  const c = CARDS[id]; if (!c) return;
  const kws = Object.keys(KEYWORDS).filter(k => hasKeyword(c, k));
  readOverlay(cardHTML(c, str == null ? {} : { str }) + kws.map(k => `<div class="kw"><b>${k}</b><p>${KEYWORDS[k]}</p></div>`).join(''));
}
function wirePops(root) {
  root.querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card);
    el.onmouseleave = () => pop.style.display = 'none';
    onHold(el, () => cardPop(el, el.dataset.card), () => pop.style.display = 'none');   // touch: shown while held
  });
}
// A deck's cover: the player's chosen one, else the collection's default.
const coverFor = d => d.cover || COVER[d.id] || coverOf(d.list, CARDS);
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
const playable = () => { const mine = myDecks().filter(d => deckSize(d.cards) === 30).map(d => ({ id: 'my:' + d.id, name: d.name, mine: true, cover: d.cover, list: Object.entries(d.cards).flatMap(([id, n]) => Array(n).fill(id)) }));
  return mine.length ? mine : DECKS.filter(d => d.id !== 'goodstuff'); };
const chosenDeck = () => { const all = playable(), id = store('ak:deck'); return all.find(d => d.id === id) || all[0]; };
const deckSpec = d => d.mine ? { name: d.name, list: d.list } : d.id;

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
  CARDS = Object.fromEntries(p.cards.map(c => [c.id, c])); MAP = p.map; DECKS = p.decks; BUILD = p.build;
  // the animals' calls (web/parked_calls/, not served) are parked (Martin, 2026-10-01): only the basic sounds play for now
  await loadProfile();
  // Feedback while the game is in testing: a tab on the screen's edge where the edge is free (home, News, Settings: app.css shows
  // it by screen); Collection and the profile have it beside Back, their side panels holding the edge; the game its own button.
  document.body.insertAdjacentHTML('beforeend', `<button class="ftab" id="ftab">${TOPICON.feedback}<span>Feedback</span></button>`);
  document.getElementById('ftab').onclick = feedback;
  bindCoach({ V: () => V, ui, CARDS: () => CARDS, send: m => send(m), drawGame: () => drawGame(), tapWords, PL: () => PL(), store, startTutorial, firstMatch });
  openPresence({ api, toast, build: checkBuild, key: () => store('ak:key'), deck: () => deckSpec(chosenDeck()),   // friends see you online; challenges arrive
    busy: () => screen === 'game' && V && V.phase === 'playing', accept: m => { setToken(m.id, m.token); location.hash = '#/m/' + m.id; } });
  initChat({ api, toast, inMatch: () => screen === 'game' && !!V && V.phase === 'playing' && !RP.views.length,
    changed: () => { if (screen === 'game' && V) drawGame(); },   // the game's Friends button shows once you have a friend
    challenge: (f, all) => {   // a conversation's Challenge: home's Play with that friend picked
      play.opp = 'friend'; play.friend = f.id; play.friends = all; play.open = null;
      if (location.hash.replace(/^#\/?/, '')) location.hash = '#/'; else homeScreen();
      setTimeout(() => { const go = document.getElementById('go'); if (go && screen === 'home') go.click(); });
    } });
  addEventListener('hashchange', route);
  addEventListener('resize', () => { if (screen === 'game') fitStage(); });
  addEventListener('keydown', e => {   // Escape backs out of whatever is open: the menu, a panel, then the selected card
    if (e.key === 'Escape' && screen === 'home' && play.open) { play.open = null; return route(); }   // Escape closes the open chooser
    if (e.key === 'Escape' && ['ladder', 'news', 'settings'].includes(screen) && !/INPUT|TEXTAREA/.test(e.target.tagName)) {   // a screen with Back: Escape is Back
      const back = document.getElementById('back'); if (back) back.click(); return;
    }
    if (RP.views.length && screen === 'game' && replayKey(e)) return;
    // Space ends your turn, D draws: the same checks as clicking the tablet or the deck (never in a lesson, whose Space is Next)
    if (screen === 'game' && !RP.views.length && !isTutorial() && !/INPUT|TEXTAREA/.test(e.target.tagName) && !e.repeat) {
      if (e.key === ' ' && document.querySelector('#tbtn.can')) { e.preventDefault(); return document.getElementById('tbtn').click(); }
      if ((e.key === 'd' || e.key === 'D') && document.querySelector('#deck.can')) return document.getElementById('deck').click();
    }
    if (e.key !== 'Escape' || screen !== 'game') return;
    const ask = document.getElementById('concov');
    if (ask && ask.classList.contains('on')) return ask.classList.remove('on');
    if (ui.panel) { ui.panel = null; return showPanel(); }
    if (ui.sel) { ui.sel = null; drawGame(); }
  });
  await rejoin();
  route();
}

// Back into the match you're still playing (after a closed tab, a phone that dropped the page, another device): the server
// keeps your seat, so opening the game anywhere takes you to it.
async function rejoin(only) {
  const r = await api('/api/current').catch(() => null), m = r && r.ok ? await r.json() : {};
  if (!m.id || (only && m.id !== only)) return false;
  setToken(m.id, m.token);
  if (!only && !location.hash.startsWith('#/m/' + m.id)) location.hash = '#/m/' + m.id;
  return true;
}

// The home painting at the viewer's time of day (a small easter egg): ?tod=dawn|day|dusk|night overrides it.
const timeOfDay = h => new URLSearchParams(location.search).get('tod') || (h >= 5 && h < 9 ? 'dawn' : h >= 9 && h < 17 ? 'day' : h >= 17 && h < 20 ? 'dusk' : 'night');
function route() {
  track('screen', { route: (location.hash.slice(1) || '/').split('/').slice(0, 2).join('/'), w: innerWidth, h: innerHeight });
  pop.style.display = 'none'; stackpop.style.display = 'none'; hideSince();
  if (!location.hash.startsWith('#/m/')) keepAwake(false);
  const tip = document.getElementById('tip'); if (tip) tip.style.display = 'none';   // the game's hover label lives on body: it must not outlive the screen
  const parts = (location.hash.slice(1) || '/').split('/').filter(Boolean);
  queueMicrotask(drawSearch);   // the search's pill, on a screen without its button
  document.documentElement.dataset.tod = timeOfDay(new Date().getHours());
  const id = parts[1] && parts[1].toUpperCase();
  if (parts[0] !== 'm' || id !== wsId) disconnect();
  if (parts[0] !== 'replay') stopReplay();
  play.open = null;   // a chooser never outlives its screen
  if (parts[0] === 'play') { history.replaceState(null, '', '#/'); return homeScreen(); }   // the old Play screen's address
  if (parts[0] === 'gauntlet') return homeScreen({ gauntlet: true });
  if (parts[0] === 'collection') return collectionScreen(parts[1]);
  showChallenge();   // a challenge waiting while a match was in play shows once you're out of it
  if (parts[0] === 'leaderboard' || parts[0] === 'profile') { history.replaceState(null, '', '#/ladder' + (parts[1] ? '/' + parts[1] : '')); parts[0] = 'ladder'; }   // the old addresses
  if (parts[0] === 'settings') return settingsScreen();
  if (parts[0] === 'news') { screen = 'news'; return newsScreen(app, { api, cards: CARDS, back: () => { location.hash = '#/'; } }); }
  if (parts[0] === 'friend' && id) { homeScreen(); return confirmFriend(id, () => { history.replaceState(null, '', '#/'); route(); }); }
  if (parts[0] === 'ladder') { ladderScreen(); return loadProfile().then(() => { if (location.hash.startsWith('#/ladder')) ladderScreen(); }); }   // a match just played shows
  if (parts[0] === 'replay' && parts[1]) return replayScreen(parts[1]);
  if (parts[0] === 'auth') return finishSignIn(parts[1]);
  if (parts[0] === 'join' && id) return getToken(id) ? (location.hash = '#/m/' + id) : homeScreen({ join: id });
  if (parts[0] === 'm' && id) return matchScreen(id);
  if (parts[0] === 'lab' && parts[1]) return labScreen(parts[1]);
  homeScreen(); if (play.opp === 'ranked') loadProfile().then(() => { if (screen === 'home' && !play.open) homeScreen(); });   // your rating after a ranked game
}

// ------------------------------------------------------------------ home: where a match starts
// There is no separate Play screen (design sandbox play/, 2026-09-30): the usual visit is one click, so home carries the match.
// The key art, the title along its top and, on its ground, one granite piece: your deck | the opponent, Play under them. Each
// side opens its chooser above the piece. Collection and the profile stand beside it for now, until the hub holds more.
// #/gauntlet is the same screen with the developer's gauntlet as the opponent; #/join/<code> the same with a friend's match.
const play = { opp: 'bot', level: 'normal', botDeck: 'random', side: 'mine', code: '', open: null, peek: null };
const LEVELS = [['easy', 'Easy'], ['normal', 'Normal'], ['expert', 'Expert']], SIDES = [['mine', 'You play your deck'], ['theirs', 'The bot plays your deck']];
const label = (opts, v) => (opts.find(o => o[0] === v) || opts[0])[1];
// Home's corner piece (design sandbox screen/nav/, 2026-10-02): you (your name and where you stand, to the profile and its
// leaderboard), Collection by name, and a menu (three bars) listing the rest, the gear kept for Settings in it; seven equal icons were too many. Feedback is a tab on the
// screen's edge while the game is in testing (moves into the gear's list at launch; see boot). Icons painted in the board numbers' chalk.
const TI = n => `<img class="tic" src="/static/kit2/top/${n}.webp" alt="" draggable="false">`;
const TOPICON = { collection: TI('collection'), leaderboard: TI('trophy'), learn: TI('learn'), profile: TI('person'), feedback: TI('feedback'), settings: TI('settings'), news: TI('news'), friends: TI('friends'), menu: TI('menu') };
let newsAsked = false;
const mePiece = () => {   // your rating and place once ranked, your placement games while placing, else the name alone
  const sub = !ME ? '' : ME.rank ? `${ME.rating} · #${ME.rank}` : ME.placing && ME.placing.games ? `Placing ${ME.placing.games} of ${ME.placing.of}` : '';
  return `<a class="backbtn me" href="#/ladder" aria-label="Ladder">${TOPICON.profile}<span><b>${esc(ME ? ME.name : 'Profile')}</b>${sub ? `<small>${sub}</small>` : ''}</span></a>`;
};
function homeScreen(mode = {}) {
  screen = 'home';
  if (!newsAsked) { newsAsked = true; loadNews(api).then(() => { if (screen === 'home') homeScreen(mode); }); }   // the dot and "Since you last played" once it's known
  if (mode.gauntlet) play.opp = 'gauntlet'; else if (play.opp === 'gauntlet' || mode.join) play.opp = mode.join ? 'friend' : 'bot';
  const all = playable(), chosen = chosenDeck(), peek = all.find(d => d.id === play.peek) || chosen;
  if (play.botDeck === 'goodstuff') play.botDeck = 'random';
  const bd = DECKS.find(d => d.id === play.botDeck), redraw = () => homeScreen(mode);
  const botDecks = [['random', 'Random'], ...DECKS.filter(d => d.id !== 'goodstuff').map(d => [d.id, d.name])];   // the seven starters only
  // The level as a three-way picker, like Bot/Friend: three choices are read at a glance, not opened.
  const levels = `<div class="seg">${LEVELS.map(([v, l]) => `<button class="slab${play.level === v ? ' on' : ''}" data-level="${v}">${l}</button>`).join('')}</div>`;
  const fr = play.opp === 'friend' && (play.friends || []).find(f => f.id === play.friend);
  const opp = mode.join ? ['Friend', 'Match ' + mode.join] : play.opp === 'friend' ? ['Friend', fr ? friendLabel(fr, play.friends) : ''] : play.opp === 'gauntlet' ? ['Gauntlet', `${label(LEVELS, play.level)} · ${label(SIDES, play.side)}`]
    : play.opp === 'ranked' ? ['Ranked', `your rating ${(ME && ME.rating) || '1500?'}`]
    : ['Practice', `${label(LEVELS, play.level)} · ${bd ? bd.name : 'Random'}`];
  const go = mode.join ? 'Join match' : play.opp === 'friend' ? (fr ? (fr.online ? `Challenge ${esc(friendLabel(fr, play.friends))}` : 'Send a match link') : 'Create match') : play.opp === 'gauntlet' ? 'Start gauntlet' : 'Play';
  const tile = (d, W, cls = '') => `<div class="dtile${cls}" data-deck="${d.id}" data-strip="${coverFor(d)}" data-ax=".7" style="${stripArt(coverFor(d), W, 56, .7)}"><b>${esc(d.name)}</b></div>`;
  // Your decks beside the list of the one under the pointer (the chosen one to begin with): what is in a deck, while choosing it.
  const deckList = d => deckBody(d.list, CARDS, false, true) + (d.mine ? '<button class="backbtn" id="dedit"><span>Open in collection</span></button>' : '');
  const chooser = play.open === 'decks'
    ? `<div class="chooser decks"><div class="clist">${all.map(d => tile(d, 300, d.id === chosen.id ? ' on' : '')).join('')}</div><div class="dl">${deckList(peek)}</div></div>`
    : play.open === 'opp' ? `<div class="chooser opps">${play.opp === 'gauntlet' ? levels + dd('side', play.side, SIDES)
      : `<div class="seg">${[['bot', 'Practice'], ['ranked', 'Ranked'], ['friend', 'Friend']].map(([v, l]) => `<button class="slab${play.opp === v ? ' on' : ''}" data-opp="${v}">${l}</button>`).join('')}</div>`
        + (play.opp === 'ranked' ? '' : play.opp === 'friend' ? `<div class="flist">${(play.friends || []).map(f => `<button class="slab fr${f.id === play.friend ? ' on' : ''}" data-friend="${f.id}">${friendRow(f, '', play.friends)}</button>`).join('')}</div>
          <button class="slab" id="addfriend">Add a friend</button><div class="frow"><input class="field" id="code" maxlength="6" value="${play.code}" placeholder="Friend's code" autocomplete="off"><button class="slab" id="joinbtn">Join</button></div>`
          : levels + dd('botDeck', play.botDeck, botDecks))}</div>`
    : play.open === 'menu' ? `<div class="chooser gear">${!learned() ? '' : `<button class="slab" id="learn2">${TOPICON.learn}How to play</button>`}<a class="slab" href="#/news">${TOPICON.news}News${newsUnread() ? '<i class="ndot"></i>' : ''}</a><a class="slab" href="#/settings">${TOPICON.settings}Settings</a></div>`
    : play.open === 'learn' ? `<div class="chooser lessons">${LESSON_NAMES.map((n, i) => `<button class="slab" data-lesson="${i + 1}"><b>Lesson ${i + 1}</b>${n}</button>`).join('')}</div>` : '';
  // A new player's piece holds one thing: learn by playing (the tutorial), or say you know how and get the full piece.
  const first = !learned() && !mode.join && !mode.gauntlet;
  app.innerHTML = `<div class="mscr home">${chooser}
    <div class="top"><button class="backbtn ico chatbtn" id="hchat" data-tip="Friends" aria-label="Friends">${TOPICON.friends}${chatBadge()}</button>${mePiece()}<a class="backbtn lab" href="#/collection" aria-label="Collection">${TOPICON.collection}<span>Collection</span></a><button class="backbtn ico${play.open === 'menu' || play.open === 'learn' ? ' open' : ''}" id="gearbtn"${play.open === 'menu' || play.open === 'learn' ? '' : ' data-tip="Menu"'} aria-label="Menu">${TOPICON.menu}${newsUnread() ? '<i class="ndot"></i>' : ''}</button></div>
    ${first ? `<div class="bar first"><button class="play" id="learn">Learn to play</button><button class="slab" id="known">I already know how to play</button></div>` : `<div class="bar"><button class="dtile pick${play.open === 'decks' ? ' open' : ''}" id="deckbtn" data-strip="${coverFor(chosen)}" data-ax=".62" style="${stripArt(coverFor(chosen), 300, 56, .62)}"><b>${esc(chosen.name)}</b><i class="chev"></i></button>
      <button class="slab pick opp${play.open === 'opp' ? ' open' : ''}" id="oppbtn"${mode.join ? ' disabled' : ''}><b>${opp[0]}</b>${opp[1] ? `<span>${esc(opp[1])}</span>` : ''}${mode.join ? '' : '<i class="chev"></i>'}</button>
      <button class="play${search && search.btn === 'go' ? ' searching' : ''}" id="go">${search && search.btn === 'go' ? searchLabel() : go}</button></div>`}</div>`;
  const $ = id => document.getElementById(id), root = app.querySelector('.home');
  fitStrips(root);   // the tiles are as wide as the window allows (upright, one column)
  if (!first && !mode.join && !mode.gauntlet) showSince(api, { onRead: () => { location.hash = '#/news'; } });   // a returning player, once
  wireChatButton($('hchat'));
  $('gearbtn').onclick = () => { play.open = play.open === 'menu' || play.open === 'learn' ? null : 'menu'; play.peek = null; redraw(); };   // the gear opens its list, or closes the lessons it led to
  if (first) {   // Learn to play picks up at lesson 2 once lesson 1 is won
    $('learn').onclick = () => { track('learn_to_play'); startTutorial(store('ak:lesson') === '1' ? 2 : 1); };
    $('known').onclick = () => { track('skip_tutorial'); store('ak:learned', '1'); redraw(); }; return; }
  const toggle = k => { play.open = play.open === k ? null : k; play.peek = null; redraw(); };
  if ($('learn2')) $('learn2').onclick = () => toggle('learn');   // any lesson again, not only from the first
  root.querySelectorAll('[data-lesson]').forEach(el => el.onclick = () => startTutorial(+el.dataset.lesson));
  $('deckbtn').onclick = () => toggle('decks');
  if (!mode.join) $('oppbtn').onclick = () => toggle('opp');
  root.onclick = e => { if (play.open && !e.target.closest('.chooser, .pick, #gearbtn')) { play.open = null; redraw(); } };   // a click elsewhere closes the chooser
  root.querySelectorAll('.chooser [data-deck]').forEach(el => {
    // A click picks the deck and shows its list; the chooser stays open to read it (hover changed the list on the way to it).
    el.onclick = () => { store('ak:deck', el.dataset.deck); play.peek = el.dataset.deck; redraw(); };
  });
  const wireList = () => { const e = $('dedit'); if (e) e.onclick = () => { play.open = null; location.hash = "#/collection/" + play.peek.slice(3); };
    const dl = root.querySelector('.dl'); if (dl) wirePops(dl); };
  if (play.open === 'decks') { play.peek = peek.id; wireList(); }
  if (play.open === 'opp' && play.opp === 'friend' && !play.friends) api('/api/friends').then(r => r.ok && r.json()).then(j => {
    play.friends = j ? j.friends : []; play.code = play.code || ''; play.friendCode = j && j.code; if (screen === 'home') redraw(); });
  root.querySelectorAll('[data-friend]').forEach(el => el.onclick = () => { play.friend = play.friend === el.dataset.friend ? null : el.dataset.friend; redraw(); });
  if ($('addfriend')) $('addfriend').onclick = () => play.friendCode && shareLink(`${location.origin}/#/friend/${play.friendCode}`, 'Be my friend in Animal Kingdom');
  root.querySelectorAll('[data-opp]').forEach(el => el.onclick = () => { play.opp = el.dataset.opp; redraw(); });
  root.querySelectorAll('[data-level]').forEach(el => el.onclick = () => { play.level = el.dataset.level; redraw(); });
  wireDd(root, (k, v) => { play[k] = v; redraw(); });
  const code = $('code');
  if (code) {
    code.oninput = () => play.code = code.value.trim().toUpperCase();
    code.onkeydown = e => { if (e.key === 'Enter') joinCode(); };
    $('joinbtn').onclick = joinCode;
  }
  $('go').onclick = async () => {
    if (mode.join) {
      const r = await api(`/api/match/${mode.join}/join`, { method: 'POST', body: JSON.stringify({ deck: deckSpec(chosen), name: 'Friend' }) });
      if (!r.ok) return toast(r.status === 404 ? `No match ${mode.join}` : await r.text());
      const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id; return;
    }
    if (search) return cancelSearch();
    if (play.opp === 'ranked') return findRanked('go', deckSpec(chosen));
    if (play.opp === 'friend' && fr && fr.online) return startSearch('challenge', 'go', '/api/challenge', { friend: fr.id, deck: deckSpec(chosen) }, friendLabel(fr, play.friends));
    const body = { deck: deckSpec(chosen), name: 'You' };
    if (play.opp === 'bot') {
      const pool = DECKS.filter(d => d.id !== 'goodstuff'), deck = play.botDeck === 'random' ? pool[Math.floor(Math.random() * pool.length)].id : play.botDeck;
      body.bot = { level: play.level, deck };
    }
    if (play.opp === 'gauntlet') body.gauntlet = { level: play.level, reverse: play.side === 'theirs' };
    const r = await api('/api/match', { method: 'POST', body: JSON.stringify(body) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token); play.open = null;
    location.hash = '#/m/' + m.id;
  };
}
// One search at a time: the ranked queue (a person near your rating, else the nearest bot) or a challenge to an online
// friend. Its state lives here, so the button that started it (home's Play, or Play again after a ranked game) shows it
// across redraws; clicking it again cancels it (a cancelled challenge tells the server, so the friend's piece goes). It
// carries on while you look around (collection, profile, leaderboard): there a pill at the bottom keeps its count and cancels
// it on a click, and a match found opens from wherever you are.
let search = null, searchShown = '';   // search: { kind, btn, who, t0, ctl }
const searchLabel = () => { const t = Math.floor((Date.now() - search.t0) / 1000);
  return `<span class="search">${search.kind === 'ranked' ? 'Finding an opponent' : `Waiting for ${esc(search.who)}`} · ${mmss(t)}<small>${tapWords('click to cancel')}</small></span>`; };
function drawSearch() {
  const b = search ? document.getElementById(search.btn) : document.querySelector('.play.searching');
  if (b) { if (search) { b.innerHTML = searchLabel(); b.classList.add('searching'); } else { b.innerHTML = searchShown; b.classList.remove('searching'); } }
  let pill = document.getElementById('qpill');
  if (!search || b || location.hash.startsWith('#/m/')) return pill && pill.remove();
  if (!pill) { pill = document.createElement('button'); pill.id = 'qpill'; pill.className = 'play searching'; pill.onclick = cancelSearch; document.body.append(pill); }
  pill.innerHTML = searchLabel();
}
function cancelSearch() {
  if (!search) return;
  const s = search; search = null; s.ctl.abort();
  if (s.kind === 'challenge') api('/api/challenge', { method: 'DELETE' });
  if (s.kind === 'ranked') api('/api/ranked', { method: 'DELETE' });   // the server doesn't notice the request dropped
  drawSearch();
}
async function startSearch(kind, btn, url, body, who) {
  if (search) return cancelSearch();
  const ctl = new AbortController(), el = document.getElementById(btn);
  searchShown = el ? el.innerHTML : 'Play';
  search = { kind, btn, who, t0: Date.now(), ctl }; drawSearch();
  const iv = setInterval(drawSearch, 1000);
  try {
    const r = await api(url, { method: 'POST', body: JSON.stringify(body), signal: ctl.signal });
    if (!r.ok) throw new Error(r.status === 409 && kind === 'challenge' ? `${who} is busy` : await r.text());
    const m = await r.json(); search = null; setToken(m.id, m.token); play.open = null; sfx('found'); location.hash = '#/m/' + m.id;
  } catch (e) { if (e.name !== 'AbortError' && search && search.ctl === ctl) toast(e.message || 'Could not find a match'); }
  finally { clearInterval(iv); if (search && search.ctl === ctl) search = null; drawSearch(); if (kind === 'challenge') refreshFriends(); }
}
// The friends list again (who is online changes): kept until the fresh one arrives, so the chosen friend stays chosen.
const refreshFriends = () => api('/api/friends').then(r => r.ok && r.json()).then(j => { if (j) { play.friends = j.friends; play.friendCode = j.code; }
  if (screen === 'home' && !search) homeScreen(); }, () => {});
const findRanked = (btn, deck) => startSearch('ranked', btn, '/api/ranked', { deck });

// The leaderboard: everyone on the ladder, people and bots together, best first; your row marked and in view.
// Settings: one column on the ground, like the leaderboard. Sound volume (0 is off) and the sound credits. The game screen
// opens the same controls over the board from its gear (settingsBody is shared).
const CREDITS_URL = '/static/kit2/snd/CREDITS.txt';
function settingsBody() {
  const v = Math.round(volume() * 100);
  return `<div class="srow"><span>Sound</span><input type="range" id="vol" min="0" max="100" step="5" value="${v}" aria-label="Sound volume"><b id="volv">${v ? v + '%' : 'Off'}</b></div>`;
}
function wireSettings(root) {
  const r = root.querySelector('#vol'), out = root.querySelector('#volv');
  r.oninput = () => { setVolume(r.value / 100); out.textContent = +r.value ? r.value + '%' : 'Off'; };
  r.onchange = () => sfx('land');   // a sample at the new volume
}
async function settingsScreen() {
  screen = 'settings';
  app.innerHTML = `<div class="mscr lead sets"><div class="lcol"><div class="hhead"><h2>Settings</h2></div>
    <div class="lbody">${accountBody()}${settingsBody()}<div class="credits"><h3>Sound credits</h3><pre id="credits"></pre></div></div>
    <div class="sfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div></div>`;
  document.getElementById('back').onclick = () => { location.hash = '#/'; };
  wireSettings(app); wireAccount(app, settingsScreen);
  const r = await fetch(CREDITS_URL).catch(() => null), t = r && r.ok ? await r.text() : '';
  const el = document.getElementById('credits'); if (el) el.textContent = t.trim();
}

// A name with its #tag small and dim: the tag only tells two players of one name apart.
// On a person's row (not yours, not a friend's): Add friend, or that you've asked.
const addFriend = x => !x.id || x.friend ? '' : x.asked ? '<small class="asked">Request sent</small>'
  : `<button class="addf" data-addf="${esc(x.id)}" data-tip="Add friend" aria-label="Add friend">${ICON.addfriend}</button>`;
const nameTag = n => { const [a, t] = String(n).split('#'); return esc(a) + (t ? `<i class="tg">#${esc(t)}</i>` : ''); };
// The leaderboard, a tab of the profile: everyone on the ladder, people and bots together, best first; your row marked and
// in view, or, while you're placing, your progress pinned over it.
async function fillLeaderboard() {
  const r = await api('/api/leaderboard'), j = r.ok ? await r.json() : { rows: [] }, pl = j.placing, box = document.getElementById('lboard');
  if (!box) return;
  box.innerHTML = (pl ? `<div class="lr you placing"><span></span><span class="nm">${nameTag(pl.name)}<small>placing, ${pl.games} of ${pl.of}</small></span><b>${pl.rating}</b></div>` : '')
    + j.rows.map((x, i) => `<div class="lr${x.bot ? ' bot' : ''}${x.you ? ' you' : ''}"><span>${i + 1}</span><span class="nm">${nameTag(x.name)}${addFriend(x)}</span><b>${x.rating}</b></div>`).join('');
  box.querySelectorAll('[data-addf]').forEach(b => b.onclick = async () => {
    b.disabled = true;
    const r = await api('/api/friends/request', { method: 'POST', body: JSON.stringify({ to: b.dataset.addf }) });
    if (!r.ok) { b.disabled = false; return toast(await r.text()); }
    const name = b.closest('.nm').firstChild.textContent;
    if ((await r.json()).friends) { b.replaceWith(''); toast(`You and ${name} are friends`, true); }
    else { b.outerHTML = '<small class="asked">Request sent</small>'; toast(`Friend request sent to ${name}`, true); }
  });
  const mine = box.querySelector('.lr.you:not(.placing)'); if (mine) mine.scrollIntoView({ block: 'center' });
}

// The tutorial: a real game with a fixed deal against a gentle opponent, a coach teaching one step at a time (tutorial.js).
// Two lessons: the basics (won by taking the den), then the deeper mechanics (won on food). Learned after the second.
const LESSON_NAMES = ['The basics', 'Special powers'];   // tutorial.py's lessons, in order
const learned = () => !!store('ak:learned') || !!(ME && ME.history && ME.history.length);
async function startTutorial(lesson = 1) {
  const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ tutorial: lesson, name: 'You' }) });
  if (!r.ok) return toast(await r.text());
  const m = await r.json(); setToken(m.id, m.token); play.open = null; location.hash = '#/m/' + m.id;
}
// After the tutorial, straight into a real match: Cats against an Easy bot playing Aggro (the deck chosen for later games too).
async function firstMatch() {
  const cats = playable().find(d => d.name === 'Cats');   // the player's own Cats deck (a copy of the starter), else the starter
  if (cats) store('ak:deck', cats.id);
  const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ deck: cats ? deckSpec(cats) : 'cats_midrange', name: 'You', bot: { level: 'easy', deck: 'aggro_hq_rush' } }) });
  if (!r.ok) return toast(await r.text());
  const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
}
function joinCode() { if (play.code) { play.open = null; location.hash = '#/join/' + play.code; } }

// Feedback from anywhere; on the game screen it carries the match, the turn and the seat's whole view (a bug as it happened).
function feedback() {
  const g = screen === 'game' && V && V.id ? V : null;
  const context = g ? { match: g.id, turn: g.game.round, seat: g.you, opponent: (g.seats[opp()] || {}).bot || 'person',
    replay: RP.views.length ? 'yes' : 'no', ...(isTutorial() ? { lesson: lessonOf(g) } : {}) } : {};
  track('feedback_open', { screen: context.screen });
  openFeedback({ api, toast, context, view: g });
}

// On a touch screen the coach's and the mulligan's "click" is a tap.
const tapWords = t => matchMedia('(hover: none)').matches ? t.replace(/\bClick\b/g, 'Tap').replace(/\bclick\b/g, 'tap') : t;

// ------------------------------------------------------------------ collection (= the deckbuilder): collection.js
// #/collection/<deck id> opens that deck (home's "Open in collection").
function collectionScreen(open) {
  screen = 'collection';
  if (open) history.replaceState(null, '', '#/collection');
  renderCollection(app, { open, cards: CARDS, starters: DECKS.filter(d => d.id !== 'goodstuff'), covers: COVER, getDecks: myDecks, saveDecks, toast, feedback,
    play: d => { store('ak:deck', 'my:' + d.id); location.hash = '#/'; }, back: () => { location.hash = '#/'; } });
}

// ------------------------------------------------------------------ ladder, and your account (in Settings)
// The ladder: the leaderboard and your match history as its two tabs, one column on the ground; your account (name,
// sign-in, the sign-in code) lives in Settings and your friends in the Friends panel (Martin, 2026-10-04).
const PROVIDER = { google: 'Google', discord: 'Discord' };
// Back from Google/Discord: swap the one-time code for this device's own session key.
async function finishSignIn(code) {
  history.replaceState(null, '', '#/settings');
  const r = code && code !== 'failed' ? await api('/api/auth/redeem', { method: 'POST', body: JSON.stringify({ code }) }) : null;
  if (!r || !r.ok) { toast('Sign-in didn\'t go through, try again'); return settingsScreen(); }
  const m = await r.json(); store('ak:key', m.key); ME = m.profile;
  toast(`Signed in as ${ME.name}#${ME.tag}`, true); settingsScreen();
}
// A deck's face: its cover, else (matches from before covers were kept) the starter or your deck of that name.
const deckFace = (cover, name) => cover || COVER[(DECKS.find(d => d.name === name) || {}).id] || (ME.decks.find(d => d.name === name) || {}).cover || '';
// A deck as a board piece: its face in the plain rim (the row's sides already say whose; colour is left to nothing here).
const piece = id => `<span class="pm">${id && hasArt(id) ? `<span class="face" style="${portrait(id, 35)}"></span>` : ''}<img src="/static/kit2/rim_n.webp" alt="" draggable="false"></span>`;
function ladderScreen() {
  screen = 'ladder';
  const when = t => new Date(t * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  // Which deck's matches: a dropdown in the header, as the collection's filters, each deck with its games won–lost.
  const wl = (w, l) => `<i>${w}–${l}</i>`, all = ME.records.reduce((a, r) => [a[0] + r.won, a[1] + r.lost], [0, 0]);
  const filter = dd('deck', ui.histDeck || '', [['', `All decks ${wl(...all)}`], ...ME.records.map(r => [esc(r.deck), `${esc(r.deck)} ${wl(r.won, r.lost)}`])]);
  const shown = ME.history.filter(h => !ui.histDeck || h.my_deck === ui.histDeck);
  const bot = h => h.kind !== 'friend';   // a bot's deck has a name you know; a person's deck name is theirs, so the row names the person
  const result = h => h.won > h.lost ? 'Won' : h.won < h.lost ? 'Lost' : 'Draw';
  const mode = h => ({ ranked: 'Ranked · ', practice: 'Practice · ', friendly: 'Friendly · ' })[h.mode] || '';   // older matches: unknown   // a match is one game (older best-of-3s by their result)
  const hist = shown.map(h => `<div class="hr ${h.won > h.lost ? 'won' : h.won < h.lost ? 'lost' : ''}" data-m="${esc(h.match)}"><b>${result(h)}</b>
    ${piece(deckFace(h.my_cover, h.my_deck))}<span class="dk">${esc(h.my_deck)}</span>${bot(h) ? `${piece(deckFace(h.opp_cover, h.opp_deck))}<span class="dk">${esc(h.opp_deck)}</span>
    <span class="meta">${mode(h)}${esc(h.opp)} · ${when(h.ended)}</span>` : `${piece(h.opp_cover)}<span class="dk">${esc(h.opp)}</span><span class="meta">${mode(h)}${when(h.ended)}</span>`}</div>`).join('');
  // the leaderboard first (Martin, 2026-10-02), the match history its second tab
  const lead = location.hash !== '#/ladder/history';
  app.innerHTML = `<div class="mscr ladder"><div class="hist"><div class="hhead"><div class="ptabs"><a class="ptab${lead ? ' on' : ''}" href="#/ladder">Leaderboard</a><a class="ptab${lead ? '' : ' on'}" href="#/ladder/history">Match history</a></div>${!lead && (hist || ui.histDeck) ? filter : ''}</div>
    <div class="hbody">${lead ? '<div class="lead lb" id="lboard"></div>' : hist ? `<div class="hlist">${hist}</div>` : '<p class="none">No finished matches yet.</p>'}</div>
    <div class="sfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div></div>`;
  document.getElementById('back').onclick = () => { location.hash = '#/'; };
  if (lead) fillLeaderboard();
  wireDd(app, (k, v) => { ui.histDeck = v || null; ladderScreen(); });
  app.querySelectorAll('[data-m]').forEach(el => el.onclick = () => { location.hash = '#/replay/' + el.dataset.m; });
}
// Your account, at the top of Settings: your name#tag (renamed in place), Google/Discord, and while you have neither, the
// sign-in code that brings this profile to another device.
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

// ------------------------------------------------------------------ match connection
function disconnect() { if (ws) { wsId = null; ws.onclose = null; ws.close(); ws = null; } stopPlayback(); V = null; }   // a step still timed would redraw the game over the next screen

async function matchScreen(id) {
  if (!getToken(id) && !(await rejoin(id))) { location.hash = '#/join/' + id; return; }   // a new tab: the server knows your seat
  const token = getToken(id);
  if (wsId === id && ws) return;
  screen = null; V = null; ui.sel = null; ui.peek = false;
  // the screen before stays until the game arrives (a bare "Connecting…" page flashed between them); shown only when slow
  clearTimeout(matchScreen.slow); matchScreen.slow = setTimeout(() => { if (!V && wsId === id) app.innerHTML = `<div class="mscr pre"><p class="wait">Connecting…</p></div>`; }, 600);
  const connect = () => {
    wsId = id;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${id}?token=${encodeURIComponent(token)}`);
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.t === 'build') return checkBuild(m.build);
      if (m.t === 'view') { const prev = V; V = m.view; V.rx = Date.now() / 1000; onView(prev); }
      else if (m.t === 'error' && m.error === 'unknown match or seat') { disconnect(); location.hash = '#/'; toast('That match has ended'); }
      else if (m.t === 'error') toast(m.error);
    };
    ws.onclose = () => { if (wsId === id) setTimeout(() => { if (wsId === id) connect(); }, 1000); };
  };
  connect();
  // back from the background (a phone switched apps, a laptop woke): a socket that died quietly reconnects at once
  matchScreen.wake = () => { if (document.hidden || wsId !== id) return;
    if (!ws || ws.readyState > 1) { if (ws) ws.onclose = null; connect(); } };
}
const send = msg => ws && ws.readyState === 1 && ws.send(JSON.stringify(msg));
const act = action => { ui.sel = null; ui.hover = null; send({ t: 'act', action }); };

// A new view: its events (static/timeline.js) play as steps, each view drawn for its step's length, the new view last.
// Views arriving meanwhile wait their turn: the next playback starts from the last step shown, so nothing is cut short.
const PB = { busy: false, queue: [], t: null };
function onView(prev) {
  if (PB.busy) { PB.queue.push(V); V = PB.shown; return; }   // keep showing the step in play
  const motion = !matchMedia('(prefers-reduced-motion: reduce)').matches;   // reduced motion: the new view at once
  const steps = motion && (screen === 'game' || screen === null) ? plan(prev, V, CARDS) : [{ view: V, step: null }];
  if (steps.length === 1) { ui.step = null; showView(prev); played(); if (RP.playing) replayPlay(true); return; }   // a replay moves on after an update with nothing to animate too
  PB.busy = true;
  const run = (i, before) => {
    const { view, step } = steps[i];
    V = PB.shown = view; ui.step = step; V.rx = Date.now() / 1000;
    showView(before);
    if (!step) return finish(view);
    clearTimeout(PB.t); PB.t = setTimeout(() => run(i + 1, view), step.dur * 1000 / (window.AK_SPEED || 1));   // AK_SPEED: tests only
  };
  const finish = shown => {
    PB.busy = false; ui.step = null; played();
    if (PB.queue.length) { const latest = PB.queue[PB.queue.length - 1]; PB.queue = []; V = latest; return onView(shown); }
    if (RP.playing) replayPlay(true);   // a replay moves on once this one has played out
  };
  run(0, prev);
}
// A strength step's changes as the board flashes them: each unit named, or every copy of a card that grows as one
// (Rattlesnake, Eon) on its owner's side.
function strengthFlash(step) {
  const m = new Map();
  if (!step || step.kind !== 'strength') return m;
  for (const c of step.changes) {
    const dir = c.n > 0 ? 'up' : 'down';
    if (c.iid != null) m.set(c.iid, dir);
    else for (const st of Object.values(V.game.board)) for (const u of st) if (u.id === c.card && u.owner === c.owner) m.set(u.iid, dir);
  }
  return m;
}
// Tell the server the screen has played the events out: a bot opponent waits for it before its next move (server._watched).
function played() {
  if (!wsId || RP.views.length || !V || !V.game) return;
  const ev = V.game.events || [];
  if (ev.length && ev[ev.length - 1].seq !== played.seq) { played.seq = ev[ev.length - 1].seq; send({ t: 'played', seq: played.seq }); }
}
function stopPlayback() { clearTimeout(PB.t); PB.busy = false; PB.queue = []; ui.step = null; }

function showView(prev) {
  // While an animation the player started must play out (the tutorial's fruit on Next), new views wait: a redraw would cut
  // it short. The first held view's predecessor is kept, so what changed meanwhile still animates when they apply.
  const hold = (ui.animUntil || 0) - Date.now();
  if (screen === 'game' && hold > 0) { if (!showView.kept) showView.kept = prev; clearTimeout(showView.t);
    showView.t = setTimeout(() => { const p = showView.kept; showView.kept = null; showView(p); }, hold + 20); return; }
  if (prev && prev.phase === 'lobby' && V.phase === 'playing') sfx('found');   // your friend joined
  if (V.phase === 'lobby') return lobbyScreen();
  if (V.phase === 'prematch') return prematchScreen();
  if (!prev || prev.phase === 'game_over' && V.phase === 'playing') ui.peek = false;
  if (prev && prev.phase === 'playing' && V.phase !== 'playing') showChallenge();
  if (prev && prev.game && V.game && prev.game.history.length > V.game.history.length) ui.sel = null;
  // One-shot animation input: what the board and food were before this view (same game only).
  ui.anim = prev && prev.game && V.game && prev.game.history.length <= V.game.history.length && prev.you === V.you
    ? { board: viewerBoard(prev), food: { A: prev.game.food[prev.you], B: prev.game.food[prev.you === 'A' ? 'B' : 'A'] },
        income: { A: prev.game.income[prev.you], B: prev.game.income[prev.you === 'A' ? 'B' : 'A'] },
        hand: prev.game.hand.map(h => h.iid), oppHand: prev.game.handCount[prev.you === 'A' ? 'B' : 'A'], hist: prev.game.history.length,
        fromStones: !(ui.step && ui.step.kind === 'food' && !ui.step.income),   // only region income flies from the stones
        strength: strengthFlash(ui.step) } : null;
  if (ui.step && ui.step.kind === 'yourturn' && screen === 'game') { turnPlate(); turnCue.until = Date.now() + 900; }
  gameScreen();
}

// Lab: #/lab/<name> renders the frozen view static/lab/<name>.json (no server match; nothing can be played).
// The browser tests start here and feed recorded views through window.__ak.feed.
async function labScreen(name) {
  V = await fetch(`/static/lab/${name}.json`).then(r => r.json());
  screen = null; gameScreen();
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
  if (s.bot) return `Bot (${s.bot[0].toUpperCase() + s.bot.slice(1)})`;
  return p === V.you ? 'You' : esc(s.name || 'Opponent');
}

// Both decklists are open from the start (a rule), so this screen is the two lists, facing, and Ready between them.
function prematchScreen() {
  screen = 'prematch';
  const you = V.you, opp = you === 'A' ? 'B' : 'A', me = V.seats[you];
  const side = (p, cls) => { const counts = V.lists[p], list = Object.entries(counts).flatMap(([id, n]) => Array(n).fill(id));
    return `<div class="piece side ${cls}"><div class="who">${seatLabel(p)}</div>
      <div class="dl">${deckBody(list, CARDS, false, true)}</div></div>`; };
  app.innerHTML = `<div class="mscr pre"><div class="face">${side(you, 'mine')}
      <div class="mid">${me.ready ? '<p class="wait">Waiting for your opponent</p>' : '<button class="play" id="ready">Ready</button>'}</div>
      ${side(opp, 'theirs')}</div><a class="backbtn leave" href="#/"><span>Leave</span></a></div>`;
  const b = document.getElementById('ready'); if (b) b.onclick = () => send({ t: 'ready' });
  wirePops(app);
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
const rel = p => p === V.you ? 'A' : 'B';
const dcr = cr => { if (V.you === 'A') return cr; const [c, r] = cr.split(','); return `${MAP.cols + 1 - Number(c)},${r}`; };

// A lesson (coach.js holds everything the tutorial does on this screen).
const isTutorial = () => isLesson(V);

// What the seat can do right now, in viewer space.
function decision() {
  const G = V.game, d = { mine: V.phase === 'playing' && G.toAct === V.you && !RP.views.length, rings: [], hqRing: false, crChoice: {}, handPick: new Set(), cardOpts: [], otherOpts: [], places: {}, pend: null };
  d.lesson = lessonNow();   // a lesson's step for this moment (coach.js), else null
  if (RP.views.length && V.phase === 'playing' && G.toAct === V.you) d.pend = G.pending;   // a replay shows what you were asked, read-only
  if (!d.mine) return d;
  d.pend = G.pending; d.places = G.legal.place;
  if (d.pend && d.pend.mode === 'choice') {
    for (const o of d.pend.options) {
      if (o.kind === 'cr') d.crChoice[dcr(o.cr || o.v)] = o.v;
      else if (o.kind === 'hand' && d.pend.kind === 'mulligan') d.handPick.add(o.v);   // the mulligan picks in the hand itself
      else if (o.kind === 'hand') d.cardOpts.push({ ...o, str: (G.hand.find(h => h.iid === o.v) || {}).str });   // any other pick from your hand is laid out in the middle: a lit hand reads as "play one" (feedback 2026-10-01)
      else if (o.kind === 'card') d.cardOpts.push(o);
      else d.otherOpts.push(o);
    }
    narrowChoice(d);   // a lesson's target step: only the target it teaches
    d.rings = Object.keys(d.crChoice);
    ui.sel = null;
  } else {
    narrowPlaces(d);   // what a lesson lets be placed
    if (ui.sel && !d.places[ui.sel]) ui.sel = null;
    const ids = Object.keys(d.places);
    if (!ui.sel && ids.length === 1 && d.pend) ui.sel = ids[0];   // a "play this card" prompt: preselect it
    if (ui.sel) for (const t of d.places[ui.sel]) { if (t[0] === 'cr') d.rings.push(dcr(t[1])); else d.hqRing = true; }
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
function gameScreen() {
  if (screen !== 'game') {
    screen = 'game';
    app.innerHTML = `<div class="game kit" id="scr"><div id="world"><img src="/static/kit2/plate_wide.webp" alt="" draggable="false"></div><div id="stage">
      <div class="abs ledge"></div>
      <div id="board"></div>
      <div class="abs menu snd" id="sndbtn"></div><div class="panel setp" id="setp"></div>
      <div class="abs menu hs" id="series" data-tip="History"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 8v4l3 2"/></svg></div>
      <div class="abs opphand" id="opphand"></div>
      <div class="abs menu fb" id="fbbtn" data-tip="Send feedback"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z"/></svg></div>
      <div class="abs menu chatbtn" id="chatbtn" data-tip="Friends">${ICON_FRIENDS}${chatBadge()}</div>
      <div class="abs menu" id="menubtn"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 21V3.5"/><path d="M6 4h12l-3 4.5 3 4.5H6"/></svg></div>
      <div class="abs hand" id="hand"></div>
      <div class="abs deck" id="deck"></div>
      <div class="abs tbtn" id="tbtn"></div>
      <div class="abs waiting" id="waiting"></div>
      <div class="abs prompt" id="choicebar"></div>
      <div class="abs coach" id="coach"></div>
      <div class="abs opts" id="opts"></div>
      <div class="abs reveal" id="reveal"></div>
      <div class="panel mine" id="mine"></div><div class="panel theirs" id="theirs"></div>
      <div class="panel histp" id="histp"><h4>History<span class="removed" id="removed"></span></h4><div class="hist" id="hist"></div></div>
      <div class="abs rbar" id="rbar"></div>
      <div class="abs recent" id="recent"></div>
      <div class="endov" id="endov"></div>
      <div class="endov" id="concov"><div class="endbox ask"><b>Concede this game?</b>
        <div class="btns"><button class="slab" id="keep">Keep playing</button><button class="play danger" id="concede">Concede</button></div></div></div></div></div>`;
    fitStage(false); wireTips(document.getElementById('scr'));
    // The coach points at a card in the hand; hovering that card enlarges it over the coach, so the coach rises above it.
    const hand = document.getElementById('hand'), coach = document.getElementById('coach');
    hand.addEventListener('mouseover', e => { const h = e.target.closest('.hc'); coach.classList.toggle('risen', !!h && !!coach.dataset.iid && (coach.dataset.iid === 'any' || h.dataset.iid === coach.dataset.iid)); });
    hand.addEventListener('mouseleave', () => coach.classList.remove('risen'));
    const $ = id => document.getElementById(id);
    // The flag concedes, after the question in the middle of the board (Keep playing, Escape or a click beside it says no).
    // In a tutorial it leaves for home at once: there is nothing to lose.
    const ask = $('concov');
    $('fbbtn').onclick = e => { e.stopPropagation(); feedback(); };
    wireChatButton($('chatbtn'));
    $('menubtn').onclick = e => { e.stopPropagation(); if (isTutorial()) { location.hash = '#/'; return; } ask.classList.add('on'); };
    ask.onclick = e => { e.stopPropagation(); if (e.target === ask) ask.classList.remove('on'); };
    $('keep').onclick = e => { e.stopPropagation(); ask.classList.remove('on'); };
    $('concede').onclick = e => { e.stopPropagation(); ask.classList.remove('on'); send({ t: 'concede' }); };
    // The series opens the history, the opponent's hand their decklist; hovering your deck shows yours.
    const toggle = k => e => { e.stopPropagation(); ui.panel = ui.panel === k ? null : k; showPanel(); };
    $('series').onclick = toggle('hist'); $('opphand').onclick = toggle('theirs');
    $('deck').onmouseenter = () => { if (matchMedia('(hover: none)').matches) return; ui.panel = 'mine'; showPanel(); };   // touch: held instead (below)
    $('deck').onmouseleave = () => { if (ui.panel === 'mine') { ui.panel = null; showPanel(); } };
    app.querySelectorAll('.panel').forEach(el => el.onclick = e => e.stopPropagation());
    $('scr').addEventListener('click', () => { if (ui.panel) { ui.panel = null; showPanel(); } });
    // touch reads your deck as it reads a card: hold it, or tap it when a tap would draw nothing
    const myList = () => { ui.panel = 'mine'; showPanel(); };
    onHold($('deck'), myList);
    $('deck').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.legal.draw && !d.noDraw) act({ kind: 'draw' }); else if (touch()) myList(); };
    $('tbtn').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.canPass && !d.noPass) { sfx('endturn'); act({ kind: 'pass' }); } };
    $('sndbtn').dataset.tip = 'Settings';
    $('sndbtn').innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>';
    $('sndbtn').onclick = e => { e.stopPropagation(); if (ui.panel !== 'set') { const p = $('setp'); p.innerHTML = `<h4>Settings</h4>${settingsBody()}`; wireSettings(p); }
      ui.panel = ui.panel === 'set' ? null : 'set'; showPanel(); };
    $('setp').onclick = e => e.stopPropagation(); preload();
    wireBoard();
  }
  drawGame();
}

// A match opens on its versus moment (Martin, 2026-10-01, after Hearthstone's "Jaina vs Gul'dan"): over the key art, your
// deck's cover card comes in from the left and the opponent's from the right, "vs" between them; it holds, then lifts off
// the board. Nothing to press; a click skips it. Once per game, never in a lesson or a replay.
function drawIntro() {
  const G = V.game, key = V.id + ':' + V.results.length;
  if (V.phase !== 'playing' || !G || G.history.length || isTutorial() || RP.views.length || !V.id || ui.intro === key) return;
  ui.intro = key;
  const side = p => { const s = V.seats[p] || {}, list = Object.keys(V.lists[p] || {}), mine = p === V.you;
    const own = mine && playable().find(d => d.id === s.deck || d.id === 'my:' + s.deck);
    const cover = own ? coverFor(own) : COVER[s.deck] || coverOf(list, CARDS);
    // One object per player (Martin, 2026-10-02): their cover card, their name in its bar (yours too: a nameplate, not a
    // sentence; the #tag only tells namesakes apart, so it stays on the profile), and in a ranked match their rating as it
    // stands going in, in a gem set into the card's bottom edge. No deck name: a person's deck name is never shown to their opponent.
    const name = s.bot ? seatLabel(p) : esc((s.name || 'Opponent').split('#')[0]), c = CARDS[cover], r = V.ranked && s.rating;
    const gem = r ? `<div class="iring edge ${c.rarity}"><div class="jewel">${gemDigits(parseInt(r, 10))}${r.endsWith('?') ? '<span class="q">?</span>' : ''}</div></div>` : '';
    return `<div class="iside ${p === V.you ? 'A' : 'B'}"><div class="iobj">${cardHTML({ ...c, name }, { cls: 'compact' })}${gem}</div></div>`; };
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
  const key = V.id + ':' + V.results.length + ':' + (V.game && V.game.round);
  if (mine && turnCue.was === false && turnCue.key !== key && !RP.views.length) {
    turnCue.key = key;   // the plate itself is the timeline's step (showView), after everything before it has played
    if (document.hidden) document.title = 'Your turn · Animal Kingdom';
  }
  if (!mine || !document.hidden) document.title = 'Animal Kingdom';
  turnCue.was = mine;
}
addEventListener('visibilitychange', () => { if (!document.hidden) { document.title = 'Animal Kingdom'; if (matchScreen.wake) matchScreen.wake(); } });
// Hearthstone's plate, on granite, with the knock.
function turnPlate() {
  sfx('yourturn');
  const b = document.createElement('div'); b.className = 'yourturn'; b.innerHTML = '<b>Your turn</b>';
  document.getElementById('stage').appendChild(b); setTimeout(() => b.remove(), 1500);
}
// Did your turn's start change something of yours (an Egg hatching), or ask you something? Then it plays after the plate.
const yoursChanged = (a, b, you) => { const mine = g => JSON.stringify(Object.entries(g.board).map(([cr, st]) => [cr, st.filter(u => u.owner === you).map(u => u.iid)]).filter(([, l]) => l.length).sort());
  return mine(a) !== mine(b) || !!(b.pending && b.toAct === you); };

// A phone in a match: a swipe down never reloads the page (pull-to-refresh is off on the game screen, game.css), and the
// screen stays awake while a game is being played, so it can't lock and drop the connection during the opponent's turn.
let wake = null;
function keepAwake(on) {
  if (on && !wake && navigator.wakeLock && !document.hidden) {
    wake = navigator.wakeLock.request('screen').then(l => { l.onrelease = () => { wake = null; }; return l; }).catch(() => { wake = null; });
  } else if (!on && wake) { wake.then(l => l && l.release()).catch(() => {}); wake = null; }
}
addEventListener('visibilitychange', () => { if (!document.hidden && screen === 'game' && V && V.phase === 'playing' && !RP.views.length) keepAwake(true); });   // the lock lapses while hidden

function drawGame() {
  const G = V.game, you = V.you, them = opp(), d = decision(), $ = id => document.getElementById(id);
  const playing = V.phase === 'playing', choosing = !!(d.pend && d.pend.mode === 'choice');
  keepAwake(playing && !RP.views.length);
  lastDecision = d;
  drawIntro();
  $('scr').classList.toggle('rp', !!RP.views.length);   // a replay: upright its controls take the deck's corner
  $('menubtn').style.display = playing && V.id && !RP.views.length ? '' : 'none';
  $('fbbtn').style.display = V.id ? '' : 'none'; $('fbbtn').classList.toggle('alone', $('menubtn').style.display === 'none');   // feedback: any real match or replay, never the lab   // the flag: only a game in play (never the lab or a replay)
  { const n = [$('menubtn'), $('fbbtn')].filter(e => e.style.display !== 'none').length, w = VIEW.port ? 88 : 52;
    $('series').style.right = 16 + w * n + 'px'; $('sndbtn').style.right = 16 + w * (n + 1) + 'px'; $('chatbtn').style.right = 16 + w * (n + 2) + 'px'; }   // Friends, left of sound
  $('chatbtn').style.display = V.id && !isTutorial() && hasFriends() ? '' : 'none';   // a real match or replay, once you have a friend   // sound, left of History   // History, left of feedback and the flag
  $('menubtn').dataset.tip = isTutorial() ? 'Leave tutorial' : 'Concede';
  // the flag concedes a match; a tutorial has nothing to concede, so the same button is a house: back home
  $('menubtn').querySelector('svg').innerHTML = isTutorial() ? '<path d="M3.5 11.5 12 4l8.5 7.5"/><path d="M6 10v10h12V10"/><path d="M10 20v-5h4v5"/>'
    : '<path d="M6 21V3.5"/><path d="M6 4h12l-3 4.5 3 4.5H6"/>';
  if (!playing) $('concov').classList.remove('on');
  drawReplayBar();

  // Top left: the turn (a match is one game while there is one map); it opens the history. The gauntlet counts its games.
  const gameNo = playing ? V.results.length + 1 : V.results.length;
  drawHistory(G); drawLists(G); showPanel();

  // The opponent's card is about to be shown large (below): note when it will have landed, before anything is drawn over it.
  turnCue(playing && G.current === you);   // the card shown, flown down, landed and its dust settled
  // The opponent's hand: one card back each, centred across the board from yours; in a replay their cards, face up (the eye hides them).
  const faces = RP.views.length && RP.eye && G.oppHand;
  const nb = G.handCount[them], step = faces ? Math.min(VIEW.port ? 40 : 72, 504 / Math.max(1, nb - 1)) : VIEW.port ? 36 : 52,   // face up, a gap between cards as in your hand; a full hand (8) stays clear of the replay's controls
    bx0 = (VIEW.port ? 184 : STAGE.w / 2) - ((faces ? 66 : 84) + (nb - 1) * step) / 2;   // upright, left of the buttons
  const A = ui.anim, oppDrew = A ? Math.max(0, nb - A.oppHand) : 0;   // their new cards slide down into their hand
  const slot = i => `${i >= nb - oppDrew ? ' drawn' : ''}" style="left:${bx0 + i * step}px;animation-delay:${(i - (nb - oppDrew)) * 0.12}s`;
  $('opphand').innerHTML = faces
    ? G.oppHand.map((h, i) => `<div class="abs oc ${CARDS[h.id].rarity}${slot(i)}" data-card="${h.id}">${cardHTML(CARDS[h.id], { str: h.str, cls: 'compact' })}</div>`).join('')
    : Array.from({ length: nb }, (_, i) => `<div class="abs back${slot(i)}"></div>`).join('');
  if (faces) { fitNames($('opphand')); $('opphand').querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card, null, 'below'); el.onmouseleave = () => pop.style.display = 'none'; }); }

  // Your hand, centred under the board.
  const n = G.hand.length, cw = 143, gap = n > 1 ? Math.min(14, (PL().handW - n * cw) / (n - 1)) : 0, x0 = PL().handC - (n * cw + (n - 1) * gap) / 2;
  const hand = $('hand');
  let drawnK = 0;
  const lit = handLights(d, G.hand);   // a lesson's hints (coach.js)
  hand.innerHTML = G.hand.map((h, i) => {
    const c = CARDS[h.id], can = d.mine && !d.handPick.size && !choosing && d.places[h.id] && (!lit.one || lit.one.iid === h.iid), pick = d.handPick.has(h.iid);
    const hint = lit.hint(can), shown = lit.shown(h.id);
    const talking = lit.talking || RP.views.length;   // while the coach talks (or in a replay) the cards stay lit, and a ready card still glows
    const cls = [c.rarity, shown ? 'shown' : '', can ? 'can' : '', (can || talking) && h.ready ? 'ready' : '', hint ? 'hint' : '', pick ? 'pick' : '', h.id === ui.sel && h.iid === (lit.one || G.hand.find(x => x.id === ui.sel)).iid ? 'sel' : '', !can && !pick && !talking ? 'dim' : ''].join(' ');   // one copy of the picked card rises
    // a card just drawn slides in from the deck (bottom right), the second a beat after the first
    const drawn = A && !A.hand.includes(h.iid) ? ++drawnK : 0, from = drawn ? `--fx:${PL().deck[0] - (x0 + i * (cw + gap) + cw / 2)}px;animation-delay:${(drawn - 1) * 0.14}s;` : '';
    return `<div class="hc ${cls}${drawn ? ' drawn' : ''}" data-iid="${h.iid}" data-id="${h.id}" style="left:${x0 + i * (cw + gap)}px;z-index:${i + 1};${from}">${cardHTML(c, { str: h.str, cls: 'compact' })}</div>`;
  }).join('');
  fitNames(hand);
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
    if (el.dataset.held) { delete el.dataset.held; return; }   // it was held to read, not tapped
    const iid = Number(el.dataset.iid), id = el.dataset.id;
    if (d.handPick.has(iid)) return act({ kind: 'choice', choice: iid });
    if (!d.mine || !d.places[id] || !el.classList.contains('can')) return;   // a dimmed copy (the tutorial lights one) does nothing
    if (ui.sel !== id) sfx('pick');
    ui.sel = ui.sel === id ? null : id; ui.hover = null; drawGame();
  });

  // The deck is Draw 2; the End turn button is also the turn indicator.
  const canDraw = d.mine && !d.pend && G.legal.draw && !d.noDraw;
  $('deck').className = 'abs deck num' + (canDraw ? ' can' : ''); $('deck').innerHTML = canDraw ? 'Draw 2' : '';
  const tb = $('tbtn');
  // the moves left in the turn, for either player; the next one to be spent pulses while the opponent is thinking
  const pips = playing ? Array.from({ length: G.actionsTotal }, (_, i) => { const used = G.actionsTotal - G.actionsLeft;
    return `<i class="${i < used ? 'used' : i === used ? 'next' : ''}"></i>`; }).join('') : '';
  if (playing && G.current === you) {
    tb.className = 'abs tbtn A num' + (d.mine && !d.pend && G.canPass && !d.noPass ? ' can' : '') + (Date.now() < (turnCue.until || 0) ? ' yours' : ''); tb.innerHTML = `<b>End turn</b><span class="pips">${pips}<span class="clock" id="clock"></span></span>`;
  } else if (playing) { tb.className = 'abs tbtn B num'; tb.innerHTML = `<span class="pips">${pips}<span class="clock" id="clock"></span></span>`; tb.dataset.tip = 'Your opponent\'s turn'; }
  else { tb.className = 'abs tbtn'; tb.innerHTML = ''; }

  // A pending choice: the asking card and its rule; card options float above the hand.
  const bar = $('choicebar'), opts = $('opts'), waiting = $('waiting');
  waiting.textContent = ''; opts.classList.remove('on'); opts.innerHTML = '';
  bar.classList.toggle('mull', !!(d.pend && d.pend.kind === 'mulligan'));   // the mulligan asks in the middle of the empty board, over your hand
  if (d.pend && d.pend.kind === 'mulligan') {
    const k = d.pend.returned;
    // a player's first real match says what the mulligan is for, in plain words (the tutorial skips it); later ones, the short rule
    const first = !store('ak:mullseen');
    const how = tapWords(first ? `This is your starting hand. Don't like a card? Click it to swap it for a new one, up to ${d.pend.cap} times. Then click ${k ? 'Done' : 'Keep hand'}.`
      : 'Click a card to replace it; no copy of a card you replace can come back.');
    bar.innerHTML = `<b>Mulligan · ${k} of ${d.pend.cap} replaced</b>` + (RP.views.length ? '' : `<p>${how}</p><div class="btns"><span class="skip" id="skip">${k ? 'Done' : 'Keep hand'}</span></div>`);
    bar.classList.add('on');
    if ($('skip')) $('skip').onclick = e => { e.stopPropagation(); store('ak:mullseen', '1'); act({ kind: 'choice', choice: SKIP }); };
  } else if (d.pend) {   // a choice only ever reaches the screen after the steps that led to it have played
    const src = d.pend.source && CARDS[d.pend.source];
    // One line at the top centre, where the eyes are: the card that asks and its rule, then Skip when it may be declined;
    // named options as slabs under it.
    const other = d.otherOpts.map((o, i) => `<span class="skip" data-x="${i}">${o.label}</span>`).join('');
    const skip = d.pend.optional && !RP.views.length ? '<span class="skip" id="skip">Skip</span>' : '';
    // offered cards float over the board: a toggle lowers them to read the board, and raises them again (a new choice shows them)
    const pk = JSON.stringify(d.cardOpts.map(o => o.v)); if (ui.optsKey !== pk) { ui.optsKey = pk; ui.optsHidden = false; }
    const peek = d.cardOpts.length ? `<span class="skip" id="optpeek">${ui.optsHidden ? 'Show cards' : 'Hide cards'}</span>` : '';
    // a pick from your hand is headed by what it does; the asking card's rule stays under it
    const ask = { discard: 'Discard a card', shuffle: `Shuffle ${d.pend.left === 1 ? 'a card' : d.pend.left + ' cards'} into your deck` }[d.pend.kind];
    bar.innerHTML = `<div class="line">${ask ? `<b>${ask}</b>${src ? `<p>${src.name}: ${src.text}</p>` : ''}` : src ? `<b>${src.name}</b><p>${src.text}</p>` : '<b>Choose</b>'}${peek}${skip}</div>` + (other && !RP.views.length ? `<div class="btns">${other}</div>` : '');
    bar.classList.add('on');
    if (d.cardOpts.length) {
      opts.innerHTML = d.cardOpts.map((o, i) => { const c = CARDS[o.id]; return `<div class="hc ${c.rarity}" data-o="${i}">${cardHTML(c, o.str == null ? {} : { str: o.str })}</div>`; }).join('');
      opts.classList.add('on'); opts.classList.toggle('hid', !!ui.optsHidden); opts.classList.toggle('many', d.cardOpts.length > 6); fitNames(opts);
      $('optpeek').onclick = e => { e.stopPropagation(); ui.optsHidden = !ui.optsHidden; drawGame(); };
      opts.querySelectorAll('[data-o]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.cardOpts[el.dataset.o].v }); });
    }
    bar.querySelectorAll('[data-x]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.otherOpts[el.dataset.x].v }); });
    const sk = $('skip'); if (sk) sk.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: SKIP }); };
  } else {
    bar.classList.remove('on');
    if (playing && G.decision === 'their_choice') waiting.textContent = 'Opponent is choosing';
    else if (playing && G.decision === 'mulligan' && G.toAct !== you) waiting.textContent = 'Opponent is mulliganing';
  }
  clearTimeout(drawGame.think);
  if (playing && G.toAct === them && V.seats[them].bot && !RP.views.length) {
    const ver = V.version;
    drawGame.think = setTimeout(() => { if (V && V.version === ver && screen === 'game') waiting.textContent = 'Bot is thinking'; }, 2500);
  }
  // The opponent's card, shown large at the centre as it is played, then flown down onto its crossroad (the piece lands as it arrives).
  const st = ui.step;   // what this step shows (static/timeline.js); a view without events just shows what changed
  if (A) A.fx = st ? (st.kind === 'bounce' ? [{ k: 'bounce', card: st.card, owner: rel(st.owner) }] : [])
    : G.history.slice(A.hist).flatMap(m => m.fx).map(f => f.owner ? { ...f, owner: rel(f.owner) } : f);
  if (st && st.kind === 'reveal') {   // the opponent's card, shown large and flown down onto its crossroad; the next step lands it
    const [tx, ty] = crossroadAt(dcr(st.cr)), rv = $('reveal');
    rv.innerHTML = cardHTML(CARDS[st.card]); fitNames(rv); rv.style.setProperty('--tx', `${tx - STAGE.w / 2}px`); rv.style.setProperty("--ty", `${ty - (VIEW.port ? 560 : 300)}px`);
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on'); sfx('reveal');
  }
  drawCoach($('coach'), d.lesson, d.rings);   // a lesson's coach (coach.js); none while steps play
  drawBoard(d);
  if (A && !RP.views.length) soundsFor(document, CARDS);   // one sound per thing that just moved
  drawEnd();
}

// Where the edge pieces stand, on the wide stage or the upright one (game.css .port): the hand's top, centre and width, the
// deck's and End turn's centre tops.
const PL = () => VIEW.port ? { hand: STAGE.h - 210, handC: RP.views.length ? 216 : 300, handW: RP.views.length ? 400 : 568, deck: [655, 1238], end: [655, 1372] }   // upright the deck and End turn end the hand's row
  : { hand: 590, handC: STAGE.w / 2, deck: [1299, 606], end: [1439, 664], handW: 940 };

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
    el.onmouseenter = () => { if (m.kind === 'place') cardPop(el, m.card, moveLine(m), 'below'); else { pop.className = 'pop'; pop.innerHTML = `<div class="ev">${moveLine(m)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex'; const r = el.getBoundingClientRect(); pop.style.left = Math.min(r.left, innerWidth - 200) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; } };
    el.onmouseleave = () => { pop.style.display = 'none'; pop.style.minHeight = ''; };
    if (RP.views.length) el.onclick = e => { e.stopPropagation(); pop.style.display = 'none'; replayPlay(false); replayStep(replayMoveEnd(Number(el.dataset.h))); };
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
  drawRecent(G);
}
function drawLists(G) {
  const sum = o => Object.values(o).reduce((a, b) => a + b, 0), you = V.you, them = opp();
  const mine = document.getElementById('mine'), theirs = document.getElementById('theirs');
  mine.innerHTML = `<h4>Your deck<span class="n">${sum(G.deckLeft)} left</span></h4><div class="rows">${rows(V.lists[you], G.deckLeft)}</div>`;
  theirs.innerHTML = `<h4>Opponent's cards<span class="n">${sum(G.unseen)} left</span></h4><div class="rows">${rows(V.lists[them], G.unseen)}</div>`;
  wirePops(mine); wirePops(theirs);
}

function showPanel() {
  if (isTutorial()) ui.panel = null;   // the tutorial never opens the decklists or the history: nothing it teaches, and they give away its deal
  for (const [k, id] of [['mine', 'mine'], ['theirs', 'theirs'], ['hist', 'histp'], ['set', 'setp']]) document.getElementById(id).classList.toggle('on', ui.panel === k);
  if (ui.panel === 'hist') { const h = document.getElementById('hist'); h.scrollTop = h.scrollHeight; }
}
// The stage keeps its design size (STAGE) and scales to fit the window. The painted ground under it is one painting wider
// and taller than any window (21:9 to 4:3), scaled with the stage, so the window shows more savanna, never bars.
function fitStage(redraw = true) {
  const st = document.getElementById('stage'); if (!st) return;
  // a window taller than wide gets the upright layout (board.js setView); turning the phone redraws the screen
  const port = innerHeight > innerWidth, flip = port !== VIEW.port;
  setView(port); document.getElementById('scr').classList.toggle('port', port);
  const k = Math.min(innerWidth / STAGE.w, innerHeight / STAGE.h), t = `scale(${k}) translate(${-STAGE.w / 2}px, ${-STAGE.h / 2}px)`;
  st.style.transform = t; document.getElementById('world').style.transform = t;
  const plate = document.querySelector('#world img'), src = `/static/kit2/plate_${port ? 'port' : 'wide'}.webp`;   // upright, its own painting
  if (!plate.src.endsWith(src)) plate.src = src;
  // the savanna around the stage, in stage px: the pieces at the screen's edges (hands, corners, deck, End turn) sit at the
  // window's edges, not the stage's, so a window of another shape widens the ground between them, never leaves them floating
  st.style.setProperty('--above', `${Math.max(0, (innerHeight / k - STAGE.h) / 2)}px`);
  st.style.setProperty('--side', `${Math.max(0, (innerWidth / k - STAGE.w) / 2)}px`);
  st.style.setProperty('--k', k);   // the stage's scale: a phone held sideways shows it at half size
  if (flip && redraw && V && V.game) drawGame();
}

function moveLine(m) {
  const who = m.seat === V.you ? 'You' : 'Opponent', name = id => CARDS[id] ? CARDS[id].name : id;
  const fx = m.fx.map(f => {
    if (f.k === 'cover') return `covered ${name(f.card)}`;
    if (f.k === 'remove') return `removed ${name(f.card)}`;
    if (f.k === 'bounce') return `returned ${name(f.card)}`;
    if (f.k === 'draw') return m.kind === 'draw' && f.seat === m.seat ? null : `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'your opponent '}drew ${f.n}`;
    if (f.k === 'food') return `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'your opponent '}${f.n > 0 ? 'gained' : 'paid'} ${Math.abs(f.n)} food`;
    return null;
  }).filter(Boolean);
  const what = m.kind === 'draw' ? `drew ${(m.fx.find(f => f.k === 'draw' && f.seat === m.seat) || { n: 0 }).n}` : m.target[0] === 'hq' ? 'captured the HQ' : '';
  return [`${who} · turn ${m.round}`, what, ...fx].filter(Boolean).join(' · ');
}

function viewerBoard(v) {
  const out = {}, rl = p => p === v.you ? 'A' : 'B';
  for (const [cr, st] of Object.entries(v.game.board)) {
    const c = v.you === 'A' ? cr : `${MAP.cols + 1 - Number(cr.split(',')[0])},${cr.split(',')[1]}`;
    out[c] = st.map(u => ({ ...u, owner: rl(u.owner) }));
  }
  return out;
}
function viewerGame() {
  const G = V.game, you = V.you, them = opp(), board = {};
  for (const [cr, st] of Object.entries(G.board)) board[dcr(cr)] = st.map(u => ({ ...u, owner: rel(u.owner) }));
  return { board, food: { A: G.food[you], B: G.food[them] }, income: { A: G.income[you], B: G.income[them] }, winFood: G.winFood };
}
function viewerMap() {
  if (V.you === 'A') return MAP;
  return { ...MAP, regions: MAP.regions.map(r => ({ ...r, c: [MAP.cols - r.c[0], r.c[1]] })) };
}

let lastDecision = null;
const ANIM_MAX = 3500;   // ms: longer than any board animation a step starts (fruit, pits, gem, landings)
function drawBoard(d) {
  d = d || lastDecision; lastDecision = d;
  let g = viewerGame();
  let preview = null;
  if (ui.sel && ui.hover && d.rings.includes(ui.hover)) {
    const strs = V.game.hand.filter(h => h.id === ui.sel).map(h => h.str);
    preview = { cr: ui.hover, id: ui.sel, str: Math.max(...strs) };
  }
  // A step's animations play once. A redraw while they run (the pointer moving over the board, a card picked) draws the
  // same moment and carries them on from where they are, never restarting them nor cutting them short (Martin, 2026-10-02:
  // the food gem glitched while counting up).
  const now = performance.now();
  if (ui.anim) { ui.animKeep = { A: ui.anim, t0: now }; ui.anim = null; }
  const keep = ui.animKeep && now - ui.animKeep.t0 < ANIM_MAX ? ui.animKeep : null;
  let A = keep ? keep.A : null; const ago = keep ? now - keep.t0 : 0;
  [A, g] = holdFood(d, A, g);   // a lesson may hold the fruit until its Next (coach.js)
  // a den taken: the animal that took it, as it was played (the engine's capture event), standing in the den's mouth
  const cap = V.game.result && V.game.result.reason === 'hq_capture' && (V.game.events || []).filter(e => e.e === 'capture').pop();
  const capture = cap ? { side: rel(cap.den), id: cap.card, owner: rel(cap.player), str: cap.str } : null;
  const region = shownRegion(d);
  const st = ui.step, strike = st && st.by ? { from: dcr(st.by), to: dcr(st.cr) } : null;   // what removed a unit answers in its beat
  const draw = () => renderBoard(document.getElementById('board'), viewerMap(), g, CARDS, { region, rings: d.rings, hqRing: d.hqRing, preview, anim: A, ago, capture, strike,
    beat: endBeat(), current: V.phase === 'playing' ? rel(V.game.current) : null });
  draw();
  if (startBeat(g, A, ago, capture)) draw();
}

// The end's beat (board.js): the game's last move shown rather than told. A den taken falls apart once the animal that took it
// has landed in its mouth; a den that reached the food to win lights up once its gem has counted to the total. It starts once
// per game (beat.key), as the move plays; a game already over when drawn (a reload, a replay's end) shows how it ended at once.
function startBeat(g, A, ago, capture) {
  const res = V.game.result, key = `${V.id}-${V.results.length}`;
  if (!res || (ui.beat && ui.beat.key === key) || !['hq_capture', 'food'].includes(res.reason) || res.winner === null) return false;
  const motion = !matchMedia('(prefers-reduced-motion: reduce)').matches, now = Date.now();
  if (res.reason === 'hq_capture') {
    if (!capture) return false;   // its step hasn't come yet
    ui.beat = { key, kind: 'fall', side: capture.side, t0: A && motion ? now - ago + 400 : now - BEAT_MS - 1 };   // the landing takes .36 s
  } else {
    const side = rel(res.winner);
    if (g.food[side] < V.game.food[res.winner]) return false;   // the winning food hasn't arrived yet
    const gem = document.querySelector(`#board .dcount.${side}.tick`), count = gem ? +gem.dataset.lag + +gem.dataset.dur : 0;
    ui.beat = { key, kind: 'lit', side, t0: A && motion ? now - ago + count + 150 : now - BEAT_MS - 1 };
  }
  if (ui.beat.t0 > now - BEAT_MS) {   // the board shakes as a den is struck (once, not on a redraw)
    if (ui.beat.kind === 'fall') setTimeout(() => document.getElementById('board')?.animate([0, 1, 2, 3, 4, 5, 6].map(i => ({ transform: i === 6 ? 'none'
      : `translate(${Math.sin(i * 2.3) * 16 * (1 - i / 6)}px, ${Math.cos(i * 3.1) * 16 * (1 - i / 6)}px)` })), { duration: 800 }), ui.beat.t0 - now);
  }
  return true;
}
const endBeat = () => { const key = V && `${V.id}-${V.results.length}`;
  return ui.beat && ui.beat.key === key ? { kind: ui.beat.kind, side: ui.beat.side, ago: Date.now() - ui.beat.t0 } : null; };

function wireBoard() {
  const board = document.getElementById('board');
  board.addEventListener('click', e => {
    const den = e.target.closest('[data-den]');   // a den opens that player's list
    if (den) { e.stopPropagation(); ui.panel = ui.panel === den.dataset.den ? null : den.dataset.den; showPanel(); return; }
    const d = lastDecision;
    if (!d || !d.mine) { const g = touch() && e.target.closest('[data-cr]'); if (g) readStack(g.dataset.cr); return; }   // off your turn a tap only reads
    const hq = e.target.closest('[data-hq]');
    if (hq && ui.sel) { const t = d.places[ui.sel].find(t => t[0] === 'hq'); if (t) return act({ kind: 'place', card_id: ui.sel, target: t }); }
    const g = e.target.closest('[data-cr]'); if (!g) return;
    const cr = g.dataset.cr;
    if (cr in d.crChoice) return act({ kind: 'choice', choice: d.crChoice[cr] });
    if (ui.sel && d.rings.includes(cr)) return act({ kind: 'place', card_id: ui.sel, target: ['cr', dcr(cr)] });
    if (touch() && !ui.sel) readStack(cr);
  });
  board.addEventListener('mouseover', e => {
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
  board.addEventListener('contextmenu', e => { if (ui.sel) { e.preventDefault(); ui.sel = null; drawGame(); } });
}

// Hover a piece: the whole stack as cards, the top unit first, then each buried card top to bottom.
// Shown after a short rest on the piece, and never while targets are ringed (it would cover them).
let stackTimer = null, stackCr = null;
function showStack(g, cr) {
  if (touch()) return;   // touch reads a piece by holding or tapping it (readStack)
  if (cr === stackCr) return;
  stackCr = cr; clearTimeout(stackTimer); stackpop.style.display = 'none';
  const st = cr && viewerGame().board[cr];
  if (!st || !st.length || ui.sel || (lastDecision && lastDecision.rings.length)) return;
  stackTimer = setTimeout(() => stackAt(cr), 350);
}
function readStack(cr) {
  const st = V && V.game && viewerGame().board[cr]; if (!st || !st.length) return;
  const card = u => `<div class="sc ${u.owner}">${cardHTML(CARDS[u.id], { str: u.str })}` +
    (u.timer ? `<div class="tm">Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}</div>` : '') + `</div>`;
  const top = st[st.length - 1], buried = st.slice(0, -1).reverse();
  readOverlay(card(top) + (buried.length ? `<div class="under">${buried.map(card).join('')}</div>` : ''));
}
function stackAt(cr) {
  const g = document.querySelector(`#board [data-cr="${cr}"]`), st = V && V.game && viewerGame().board[cr];
  if (!g || !st) return;
  const card = (u, w, top) => { const c = CARDS[u.id];
    return `<div class="sc ${u.owner}">${cardHTML(c, { str: u.str, attrs: `style="--w:${w}px"` })}` +
      (u.timer ? `<div class="tm">Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}</div>` : '') + `</div>`; };
  const top = st[st.length - 1], buried = st.slice(0, -1).reverse();
  stackpop.innerHTML = `<div class="stk">${card(top, 190, true)}</div>` +
    buried.map((u, i) => `<div class="stk">${card(u, 150)}</div>`).join('');
  stackpop.style.display = 'flex'; fitNames(stackpop);
  const r = g.getBoundingClientRect(), w = stackpop.offsetWidth, h = stackpop.offsetHeight;
  stackpop.style.left = (r.right + 8 + w > innerWidth ? r.left - 8 - w : r.right + 8) + 'px';
  stackpop.style.top = Math.max(56, Math.min(r.top - 80, innerHeight - h - 10)) + 'px';
}

function drawEnd() {
  const ov = document.getElementById('endov'), G = V.game;
  if (V.phase === 'playing' || !G.result) { drawEnd.live = V.phase === 'playing'; ov.classList.remove('on');
    if (drawEnd.live && G.decision !== 'playing_out') { drawEnd.key = drawEnd.sounded = null; ui.beat = null; }   // a new game (a rematch reuses the match's id and count): its end is new; not a step of the last move
    return; }
  // The move that ended the game plays out first (the opponent's card shown and landed, a piece in the den, the fruit of the
  // last income or a Roar): the result shows once it has. Only for a game seen ending live, once; with reduced motion at once.
  const key = `${V.id}-${V.results.length}`;
  if (drawEnd.key !== key) {
    const motion = !(typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches);
    drawEnd.until = drawEnd.live && motion && G.result.reason !== 'concede' ? Date.now() + 900 : 0; drawEnd.key = key; drawEnd.live = false; drawEnd.since = Date.now(); }
  // a den taken or a full den: the result waits for its beat (which waits for the move), never longer than 9 s
  if (drawEnd.until && ['hq_capture', 'food'].includes(G.result.reason) && G.result.winner !== null) {
    const b = ui.beat && ui.beat.key === key ? ui.beat : null;
    drawEnd.until = b ? Math.max(drawEnd.until, b.t0 + BEAT_MS) : Math.max(drawEnd.until, Math.min(Date.now() + 200, drawEnd.since + 9000)); }
  const wait = (drawEnd.until || 0) - Date.now();
  if (wait > 0) { ov.classList.remove('on'); clearTimeout(drawEnd.t); drawEnd.t = setTimeout(() => { if (screen === 'game') drawEnd(); }, wait + 20); return; }
  if (ui.peek) { ov.classList.remove('on'); document.getElementById('waiting').innerHTML = `<button class="slab" id="unpeek">Back to results</button>`; document.getElementById('unpeek').onclick = () => { ui.peek = false; drawGame(); }; return; }
  const you = V.you, them = opp(), w = G.result.winner, S = V.score;
  const live = drawEnd.sounded !== key && drawEnd.until && w !== null && !RP.views.length;   // a game seen ending live: its sound and its entrance, once
  if (live) sfx(w === you ? 'victory' : 'defeat');
  drawEnd.sounded = key;
  const res = w === null ? ['D', 'Draw'] : w === you ? ['A', 'Victory'] : ['B', 'Defeat'];
  const how = { hq_capture: w === you ? 'Enemy den captured' : 'Your den was captured', food: `${w === you ? 'You' : 'Your opponent'} reached ${G.winFood} food`, exhaustion: 'Exhaustion · more food wins', passes: 'Both passed · more food wins', max_turns: 'Turn limit · more food wins', concede: w === you ? 'Your opponent conceded' : 'You conceded', timeout: w === you ? 'Your opponent ran out of time three turns in a row' : 'You ran out of time three turns in a row' }[G.result.reason] || G.result.reason;
  const howLine = ['hq_capture', 'food'].includes(G.result.reason) && w !== null ? '' : `<div class="how">${how}.</div>`;   // a den taken, a full den: the board showed it
  const score = `<div class="score"><span class="gem A">${gemDigits(S[you])}</span><span class="gem B">${gemDigits(S[them])}</span></div>`;
  const peek = `<button class="slab" id="peek">See the board</button>`;
  if (RP.views.length) {
    // a replay: the game's result, then the replay again or back to the profile
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div>${howLine}
      <div class="btns"><a class="slab" href="#/ladder/history">Back</a>${peek}<button class="play" id="again">Watch again</button></div></div>`;
    document.getElementById('again').onclick = () => { replayStep(0); replayPlay(true); };
  } else if (V.gauntlet) {
    const g = V.gauntlet, tot = g.record.reduce((a, r) => [a[0] + r.w, a[1] + r.l], [0, 0]);
    const rows = g.record.map(r => `<div>${r.deckName} <b>${r.w}–${r.l}</b></div>`).join('');
    const done = V.phase === 'match_over';
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${done ? 'Gauntlet done' : res[1]}</div>${howLine}
      <div class="how">Game ${g.played} of ${g.total} · overall <b>${tot[0]}–${tot[1]}</b></div><div class="how">${rows}</div>
      ${done ? '' : `<div class="next">Next: ${g.next.yours ? `you play ${g.next.deckName}` : `vs ${g.next.deckName}`} · ${g.next.first === you ? 'you go first' : 'your opponent goes first'}</div>`}
      <div class="btns">${peek}${done ? '<a class="play" href="#/">Menu</a>' : '<button class="play" id="nextg">Next game</button>'}</div></div>`;
    if (!done) document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else if (V.phase === 'game_over') {
    const firstNext = w === null ? G.first : (w === you ? them : you);
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div>${howLine}${score}
      <div class="next">Game ${V.results.length + 1}: ${firstNext === you ? 'you go first' : 'your opponent goes first'}</div>
      <div class="btns">${peek}<button class="play" id="nextg">Next game</button></div></div>`;
    document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else if (isTutorial()) {
    lessonEnd(ov, { res, how, won: w === you });
  } else if (V.ranked) {
    // a ranked game: its result and your rating before and after; Play again looks for the next opponent (no rematch)
    const rt = V.rating, d = rt && rt.delta;
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div>${howLine}
      ${rt ? `<div class="rating"><small>Rating</small><div><b id="rnum">${live ? rt.before : rt.after}</b><span class="rd ${d >= 0 ? 'up' : 'down'}${live ? '' : ' on'}">${d >= 0 ? '+' : '−'}${Math.abs(d)}</span></div></div>` : ''}
      <div class="btns"><a class="slab" href="#/">Menu</a>${peek}<button class="play" id="again">Play again</button></div></div>`;
    document.getElementById('again').onclick = () => findRanked('again', deckSpec(chosenDeck()));
    if (live && rt) countRating(rt);
  } else {
    // one game: its result; a series (best-of-3, back with the maps): the match's result and the score in the gems
    const won = S[you] > S[them], series = V.results.length > 1;
    ov.innerHTML = `<div class="endbox">${series ? `<div class="res ${won ? 'A' : 'B'}">${won ? 'Match won' : 'Match lost'}</div><div class="how">${res[1]} in game ${V.results.length} · ${how}</div>${score}`
      : `<div class="res ${res[0]}">${res[1]}</div>${howLine}`}
      <div class="btns"><a class="slab" href="#/">Menu</a>${peek}<button class="play" id="rematch">Rematch</button></div></div>`;
    document.getElementById('rematch').onclick = () => send({ t: 'rematch' });
  }
  const pk = document.getElementById('peek'); if (pk) pk.onclick = () => { ui.peek = true; drawGame(); };   // a lesson has none
  ov.classList.toggle('won', w === you); ov.classList.toggle('lost', w !== null && w !== you);   // the board behind: lit for a win, dusk for a loss
  ov.classList.toggle('enter', !!live);
  ov.classList.add('on');
}

// A ranked game seen ending live: once the result has landed, the rating counts from before to after, then the change shows.
// The server sends the ratings as shown ("1781", "1500?" while provisional): count on the numbers, land on its text.
function countRating(rt) {
  const t0 = performance.now() + 700, dur = 1100, from = parseInt(rt.before, 10);
  const step = now => { const n = document.getElementById('rnum'); if (!n) return;
    const k = Math.min(1, Math.max(0, (now - t0) / dur)), e = 1 - (1 - k) ** 3;
    n.textContent = k < 1 ? Math.round(from + rt.delta * e) : rt.after;
    if (k < 1) requestAnimationFrame(step); else n.nextElementSibling.classList.add('on'); };
  requestAnimationFrame(step);
}

// ------------------------------------------------------------------ replay
// A finished match played back on the game screen: every view you saw, one per action, stepped or played at the bot's pace.
// Nothing can be done on the board; the controls sit where the menu does, and the arrows and Space drive them too.
const RP = { key: null, views: [], i: 0, playing: false, timer: null, eye: true, shown: [], turns: [] };   // eye: the opponent's hand shown
async function replayScreen(key) {
  if (RP.key === key && RP.views.length) return;
  stopReplay(); screen = null; RP.key = key;
  app.innerHTML = `<div class="mscr pre"><p class="wait">Loading the replay…</p></div>`;
  const back = msg => { RP.key = null; history.replaceState(null, '', '#/ladder/history'); ladderScreen(); toast(msg); };
  let views;
  try { const r = await api('/api/replay/' + encodeURIComponent(key)); if (!r.ok) throw new Error(await r.text()); views = await r.json(); }
  catch (e) { if (RP.key === key) back(e.message || 'The replay didn\'t load, try again'); return; }
  if (RP.key !== key) return;   // left while it loaded
  // A step is a view that brought something: new events (static/timeline.js plays them), a choice put to you, or the game's
  // end. The rest (the opponent's hidden choices, their kept hand) is skipped; the progress bar marks each turn.
  const seq = v => { const ev = v.game.events || []; return ev.length ? ev[ev.length - 1].seq : 0; };
  const yours = v => JSON.stringify(v.game.toAct === v.you && v.game.pending);   // the choice put to you, if any
  const legacy = !views.some(v => (v.game.events || []).length);   // matches from before events (2026-10-01): the old screen comparison
  const look = v => JSON.stringify([v.phase, v.game.board, v.game.hand.map(h => h.id), (v.game.oppHand || []).map(h => h.id), v.game.food,
    v.game.current, v.game.round, yours(v)]);
  RP.shown = views.map((v, i) => i === 0 || i === views.length - 1 || (legacy ? look(v) !== look(views[i - 1])
    : seq(v) !== seq(views[i - 1]) || yours(v) !== yours(views[i - 1]) || v.phase !== views[i - 1].phase));
  RP.turns = views.flatMap((v, i) => i && v.game.round !== views[i - 1].game.round ? [i / (views.length - 1)] : []);
  RP.views = views; RP.eye = true; ui.peek = false; ui.sel = null; ui.panel = null;
  replayStep(0); replayPlay(true);
}
function stopReplay() { clearTimeout(RP.timer); if (RP.views.length) stopPlayback(); Object.assign(RP, { key: null, views: [], i: 0, playing: false, shown: [], turns: [] }); }
function replayStep(i) {
  i = Math.max(0, Math.min(RP.views.length - 1, i));
  const prev = V, step = i === RP.i + 1 || (i > RP.i && RP.shown.slice(RP.i + 1, i).every(s => !s)); RP.i = i; V = RP.views[i]; V.rx = Date.now() / 1000;
  onView(step ? prev : null);   // one step forward plays its animation; any jump lands at once
}
const replayNext = () => { let i = RP.i + 1; while (i < RP.views.length - 1 && !RP.shown[i]) i++; return i; };
const replayPrev = () => { let i = RP.i - 1; while (i > 0 && !RP.shown[i]) i--; return i; };
// The view where move h has fully resolved (its choices included): the last one before the next move.
const replayMoveEnd = h => { let i = RP.views.findIndex(v => v.game.history.length > h + 1); return (i < 0 ? RP.views.length : i) - 1; };
// Playing: the next view after the same beat the bot takes, longer while the opponent's card is shown.
function replayPlay(on) {
  clearTimeout(RP.timer); RP.playing = on && RP.i < RP.views.length - 1;
  if (RP.playing) {
    if (!PB.busy) RP.timer = setTimeout(() => { replayStep(replayNext()); }, RP.i === 0 ? 1200 : 500);   // a beat after the last step
  }
  drawReplayBar();
}
const RICON = { back: '<path d="M15 6l-6 6 6 6"/>', fwd: '<path d="M9 6l6 6-6 6"/>', play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
  pause: '<path d="M8.5 6v12M15.5 6v12"/>', eye: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/><path d="M4 20L20 4"/>' };
const ric = k => `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">${RICON[k]}</svg>`;
// The controls are built once per screen (a drag on the bar must outlive redraws); each view updates them.
function drawReplayBar() {
  const bar = document.getElementById('rbar');
  if (!bar) return;
  if (!RP.views.length) { bar.innerHTML = ''; bar.classList.remove('on'); return; }
  const $ = id => document.getElementById(id), stop = f => e => { e.stopPropagation(); f(e); };
  if (!$('rtrack')) {
    bar.innerHTML = `<button class="slab" id="rback" tabindex="-1" data-tip="Back one move">${ric('back')}</button>
      <button class="slab" id="rplay" tabindex="-1"></button>
      <button class="slab" id="rfwd" tabindex="-1" data-tip="Forward one move">${ric('fwd')}</button>
      <div class="track" id="rtrack"><i></i></div>
      <button class="slab" id="reye" tabindex="-1"></button>
      <a class="slab out" href="#/ladder/history">Leave</a>`;
    $('rback').onclick = stop(() => { replayPlay(false); replayStep(replayPrev()); });
    $('rfwd').onclick = stop(() => { replayPlay(false); replayStep(replayNext()); });
    $('rplay').onclick = stop(() => replayPlay(!RP.playing));
    $('reye').onclick = stop(() => { RP.eye = !RP.eye; drawGame(); });
    // Click or drag along the bar: the game follows the pointer, the turn counter with it.
    const track = $('rtrack'), seek = e => { const r = track.getBoundingClientRect();
      const i = Math.round(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * (RP.views.length - 1)); if (i !== RP.i) replayStep(i); };
    track.onclick = e => e.stopPropagation();
    track.onpointerdown = e => { e.stopPropagation(); track.setPointerCapture(e.pointerId); replayPlay(false); seek(e); track.onpointermove = seek; };
    track.onpointerup = track.onpointercancel = () => { track.onpointermove = null; };
  }
  bar.classList.add('on');
  const n = RP.views.length - 1;
  $('rtrack').innerHTML = RP.turns.map(p => `<b style="left:${p * 100}%"></b>`).join('') + `<i style="width:${n ? RP.i / n * 100 : 100}%"></i>`;
  $('rplay').dataset.tip = RP.playing ? 'Pause' : 'Play'; $('rplay').innerHTML = ric(RP.playing ? 'pause' : 'play');
  $('reye').dataset.tip = `${RP.eye ? 'Hide' : 'Show'} your opponent's hand`; $('reye').innerHTML = ric(RP.eye ? 'eye' : 'eyeoff');
}
// The last few moves beside the turn, newest last (in a replay, where the history is how you find your way).
function drawRecent(G) {
  const el = document.getElementById('recent');
  if (!el) return;
  if (!RP.views.length || !G.history.length) { el.innerHTML = ''; return; }
  const from = Math.max(0, G.history.length - 7);
  el.innerHTML = G.history.slice(from).map((m, k) => { const i = from + k, prev = G.history[i - 1];
    return (k && prev.round !== m.round ? '<span class="tgap"></span>' : '') + histItem(m, i); }).join('');
  wireHist(el, G);
}
function replayKey(e) {
  if (e.key === 'ArrowLeft') { replayPlay(false); replayStep(replayPrev()); }
  else if (e.key === 'ArrowRight') { replayPlay(false); replayStep(replayNext()); }
  else if (e.key === ' ') { e.preventDefault(); replayPlay(!RP.playing); }
  else if (e.key === 'Escape' && !ui.panel) location.hash = '#/ladder/history';
  else return false;
  return true;
}

window.__ak = () => ({ V, ui, d: lastDecision, PB, RP });   // test hook: the headless play-through reads the view (and whether steps are playing, where a replay is)
window.__ak.cards = () => CARDS;   // test hook: the card pool as the client holds it
window.__ak.build = checkBuild;   // test hook: a socket naming another build
window.__ak.feed = v => { const prev = V; V = v; onView(prev); };   // test hook: play a recorded sequence of views through the client
boot();

