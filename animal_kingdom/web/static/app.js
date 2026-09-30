// Animal Kingdom web client: menu flow (home -> play -> pre-match) and the game screen.
// The server holds the game; this file only renders the seat's view and sends choices back.
import { hasArt, artUrl, stripArt } from './art.js';
import { cardHTML, fitNames } from './card.js';
import { renderBoard, STAGE, crossroadAt, denMouthAt, chalk, gemDigits, portrait } from './board.js';
import { collectionScreen as renderCollection, coverOf, deckBody, stripHTML } from './collection.js';
import { dd, wireDd } from './menu.js';
import { current as lessonNow, gate, held, lessonOf } from './tutorial.js';

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
function wirePops(root) {
  root.querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card);
    el.onmouseleave = () => pop.style.display = 'none';
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
async function boot() {
  const p = await fetch('/api/pool').then(r => r.json());
  CARDS = Object.fromEntries(p.cards.map(c => [c.id, c])); MAP = p.map; DECKS = p.decks;
  await loadProfile();
  addEventListener('hashchange', route);
  addEventListener('resize', () => { if (screen === 'game') fitStage(); });
  addEventListener('keydown', e => {   // Escape backs out of whatever is open: the menu, a panel, then the selected card
    if (e.key === 'Escape' && screen === 'home' && play.open) { play.open = null; return route(); }   // Escape closes the open chooser
    if (e.key === 'Escape' && screen === 'profile' && !/INPUT/.test(e.target.tagName)) { location.hash = '#/'; return; }
    if (RP.views.length && screen === 'game' && replayKey(e)) return;
    if (e.key !== 'Escape' || screen !== 'game') return;
    const menu = document.getElementById('menudrop');
    if (menu && menu.classList.contains('on')) return menu.classList.remove('on');
    if (ui.panel) { ui.panel = null; return showPanel(); }
    if (ui.sel) { ui.sel = null; drawGame(); }
  });
  route();
}

// The home painting at the viewer's time of day (a small easter egg): ?tod=dawn|day|dusk|night overrides it.
const timeOfDay = h => new URLSearchParams(location.search).get('tod') || (h >= 5 && h < 9 ? 'dawn' : h >= 9 && h < 17 ? 'day' : h >= 17 && h < 20 ? 'dusk' : 'night');
function route() {
  pop.style.display = 'none'; stackpop.style.display = 'none';
  const tip = document.getElementById('tip'); if (tip) tip.style.display = 'none';   // the game's hover label lives on body: it must not outlive the screen
  const parts = (location.hash.slice(1) || '/').split('/').filter(Boolean);
  document.documentElement.dataset.tod = timeOfDay(new Date().getHours());
  const id = parts[1] && parts[1].toUpperCase();
  if (parts[0] !== 'm' || id !== wsId) disconnect();
  if (parts[0] !== 'replay') stopReplay();
  play.open = null;   // a chooser never outlives its screen
  if (parts[0] === 'play') { history.replaceState(null, '', '#/'); return homeScreen(); }   // the old Play screen's address
  if (parts[0] === 'gauntlet') return homeScreen({ gauntlet: true });
  if (parts[0] === 'collection') return collectionScreen(parts[1]);
  if (parts[0] === 'profile') return profileScreen();
  if (parts[0] === 'replay' && parts[1]) return replayScreen(parts[1]);
  if (parts[0] === 'auth') return finishSignIn(parts[1]);
  if (parts[0] === 'join' && id) return getToken(id) ? (location.hash = '#/m/' + id) : homeScreen({ join: id });
  if (parts[0] === 'm' && id) return matchScreen(id);
  if (parts[0] === 'lab' && parts[1]) return labScreen(parts[1]);
  homeScreen();
}

// ------------------------------------------------------------------ home: where a match starts
// There is no separate Play screen (design sandbox play/, 2026-09-30): the usual visit is one click, so home carries the match.
// The key art, the title along its top and, on its ground, one granite piece: your deck | the opponent, Play under them. Each
// side opens its chooser above the piece. Collection and the profile stand beside it for now, until the hub holds more.
// #/gauntlet is the same screen with the developer's gauntlet as the opponent; #/join/<code> the same with a friend's match.
const play = { opp: 'bot', level: 'normal', botDeck: 'random', side: 'mine', code: '', open: null, peek: null };
const LEVELS = [['easy', 'Easy'], ['normal', 'Normal'], ['expert', 'Expert']], SIDES = [['mine', 'You play your deck'], ['theirs', 'The bot plays your deck']];
const label = (opts, v) => (opts.find(o => o[0] === v) || opts[0])[1];
function homeScreen(mode = {}) {
  screen = 'home';
  if (mode.gauntlet) play.opp = 'gauntlet'; else if (play.opp === 'gauntlet' || mode.join) play.opp = mode.join ? 'friend' : 'bot';
  const all = playable(), chosen = chosenDeck(), peek = all.find(d => d.id === play.peek) || chosen;
  const bd = DECKS.find(d => d.id === play.botDeck), redraw = () => homeScreen(mode);
  const botDecks = [['random', 'Random deck'], ...DECKS.map(d => [d.id, d.name + ' deck'])];
  // The level as a three-way picker, like Bot/Friend: three choices are read at a glance, not opened.
  const levels = `<div class="seg">${LEVELS.map(([v, l]) => `<button class="slab${play.level === v ? ' on' : ''}" data-level="${v}">${l}</button>`).join('')}</div>`;
  const opp = mode.join ? ['Friend', 'Match ' + mode.join] : play.opp === 'friend' ? ['Friend', ''] : play.opp === 'gauntlet' ? ['Gauntlet', `${label(LEVELS, play.level)} · ${label(SIDES, play.side)}`]
    : ['Bot', `${label(LEVELS, play.level)} · ${bd ? bd.name + ' deck' : 'Random deck'}`];
  const go = mode.join ? 'Join match' : play.opp === 'friend' ? 'Create match' : play.opp === 'gauntlet' ? 'Start gauntlet' : 'Play';
  const tile = (d, W, cls = '') => `<div class="dtile${cls}" data-deck="${d.id}" style="${stripArt(coverFor(d), W, 56, .7)}"><b>${esc(d.name)}</b></div>`;
  // Your decks beside the list of the one under the pointer (the chosen one to begin with): what is in a deck, while choosing it.
  const deckList = d => deckBody(d.list, CARDS, false, true) + (d.mine ? '<button class="backbtn" id="dedit"><span>Open in collection</span></button>' : '');
  const chooser = play.open === 'decks'
    ? `<div class="chooser decks"><div class="clist">${all.map(d => tile(d, 300, d.id === chosen.id ? ' on' : '')).join('')}</div><div class="dl">${deckList(peek)}</div></div>`
    : play.open === 'opp' ? `<div class="chooser opps">${play.opp === 'gauntlet' ? levels + dd('side', play.side, SIDES)
      : `<div class="seg"><button class="slab${play.opp === 'bot' ? ' on' : ''}" data-opp="bot">Bot</button><button class="slab${play.opp === 'friend' ? ' on' : ''}" data-opp="friend">Friend</button></div>`
        + (play.opp === 'friend' ? `<div class="frow"><input class="field" id="code" maxlength="6" value="${play.code}" placeholder="Friend's code" autocomplete="off"><button class="slab" id="joinbtn">Join</button></div>`
          : levels + dd('botDeck', play.botDeck, botDecks))}</div>` : '';
  // A new player's piece holds one thing: learn by playing (the tutorial), or say you know how and get the full piece.
  const first = !learned() && !mode.join && !mode.gauntlet;
  app.innerHTML = `<div class="mscr home">${play.open === 'decks' ? '' : '<div class="title">Animal Kingdom</div>'}${chooser}
    <div class="flank l"><a class="backbtn" href="#/collection"><span>Collection</span></a>${first ? '' : '<button class="backbtn" id="learn2"><span>How to play</span></button>'}</div>
    ${first ? `<div class="bar first"><button class="play" id="learn">Learn to play</button><button class="slab" id="known">I already know how to play</button></div>` : `<div class="bar"><button class="dtile pick${play.open === 'decks' ? ' open' : ''}" id="deckbtn" style="${stripArt(coverFor(chosen), 300, 56, .62)}"><b>${esc(chosen.name)}</b><i class="chev"></i></button>
      <button class="slab pick opp${play.open === 'opp' ? ' open' : ''}" id="oppbtn"${mode.join ? ' disabled' : ''}><b>${opp[0]}</b>${opp[1] ? `<span>${esc(opp[1])}</span>` : ''}${mode.join ? '' : '<i class="chev"></i>'}</button>
      <button class="play" id="go">${go}</button></div>`}
    <div class="flank r"><a class="backbtn who" href="#/profile"><span><b>${esc(ME.name)}</b><i>#${ME.tag}</i></span></a></div></div>`;
  const $ = id => document.getElementById(id), root = app.querySelector('.home');
  if (first) {   // Learn to play picks up at lesson 2 once lesson 1 is won
    $('learn').onclick = () => startTutorial(store('ak:lesson') === '1' ? 2 : 1);
    $('known').onclick = () => { store('ak:learned', '1'); redraw(); }; return; }
  $('learn2').onclick = () => startTutorial(1);
  const toggle = k => { play.open = play.open === k ? null : k; play.peek = null; redraw(); };
  $('deckbtn').onclick = () => toggle('decks');
  if (!mode.join) $('oppbtn').onclick = () => toggle('opp');
  root.onclick = e => { if (play.open && !e.target.closest('.chooser, .pick')) { play.open = null; redraw(); } };   // a click elsewhere closes the chooser
  root.querySelectorAll('.chooser [data-deck]').forEach(el => {
    // A click picks the deck and shows its list; the chooser stays open to read it (hover changed the list on the way to it).
    el.onclick = () => { store('ak:deck', el.dataset.deck); play.peek = el.dataset.deck; redraw(); };
  });
  const wireList = () => { const e = $('dedit'); if (e) e.onclick = () => { play.open = null; location.hash = "#/collection/" + play.peek.slice(3); };
    const dl = root.querySelector('.dl'); if (dl) wirePops(dl); };
  if (play.open === 'decks') { play.peek = peek.id; wireList(); }
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
    const body = { deck: deckSpec(chosen), name: 'You' };
    if (play.opp === 'bot') {
      const pool = DECKS.filter(d => d.id !== 'goodstuff'), deck = play.botDeck === 'random' ? pool[Math.floor(Math.random() * pool.length)].id : play.botDeck;
      body.bot = { level: play.level, deck };
    }
    if (play.opp === 'gauntlet') body.gauntlet = { level: play.level, reverse: play.side === 'theirs' };
    const r = await api('/api/match', { method: 'POST', body: JSON.stringify(body) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token); play.open = null; location.hash = '#/m/' + m.id;
  };
}
// The tutorial: a real game with a fixed deal against a gentle opponent, a coach teaching one step at a time (tutorial.js).
// Two lessons: the basics (won by taking the den), then the deeper mechanics (won on food). Learned after the second.
const learned = () => !!store('ak:learned') || !!(ME && ME.history && ME.history.length);
async function startTutorial(lesson = 1) {
  const r = await api('/api/match', { method: 'POST', body: JSON.stringify({ tutorial: lesson, name: 'You' }) });
  if (!r.ok) return toast(await r.text());
  const m = await r.json(); setToken(m.id, m.token); play.open = null; location.hash = '#/m/' + m.id;
}
function joinCode() { if (play.code) { play.open = null; location.hash = '#/join/' + play.code; } }

// ------------------------------------------------------------------ collection (= the deckbuilder): collection.js
// #/collection/<deck id> opens that deck (home's "Open in collection").
function collectionScreen(open) {
  screen = 'collection';
  if (open) history.replaceState(null, '', '#/collection');
  renderCollection(app, { open, cards: CARDS, starters: DECKS.filter(d => d.id !== 'goodstuff'), covers: COVER, getDecks: myDecks, saveDecks, toast,
    play: d => { store('ak:deck', 'my:' + d.id); location.hash = '#/'; }, back: () => { location.hash = '#/'; } });
}

// ------------------------------------------------------------------ profile
// Your name#tag, the sign-in code that brings this profile to another device, and your finished matches.
const PROVIDER = { google: 'Google', discord: 'Discord' };
// Back from Google/Discord: swap the one-time code for this device's own session key.
async function finishSignIn(code) {
  history.replaceState(null, '', '#/profile');
  const r = code && code !== 'failed' ? await api('/api/auth/redeem', { method: 'POST', body: JSON.stringify({ code }) }) : null;
  if (!r || !r.ok) { toast('Sign-in didn\'t go through, try again'); return profileScreen(); }
  const m = await r.json(); store('ak:key', m.key); ME = m.profile;
  toast(`Signed in as ${ME.name}#${ME.tag}`, true); profileScreen();
}
// The collection's skeleton: your decks with their records and your matches on the ground, you in the granite column
// (name, account, sign-in code), Back in its foot. A deck filters the matches; a match opens its replay.
// A deck's face: its cover, else (matches from before covers were kept) the starter or your deck of that name.
const deckFace = (cover, name) => cover || COVER[(DECKS.find(d => d.name === name) || {}).id] || (ME.decks.find(d => d.name === name) || {}).cover || '';
// A deck as a board piece: its face in the plain rim (the row's sides already say whose; colour is left to nothing here).
const piece = id => `<span class="pm">${id && hasArt(id) ? `<span class="face" style="${portrait(id, 35)}"></span>` : ''}<img src="/static/kit2/rim_n.webp" alt="" draggable="false"></span>`;
function profileScreen() {
  screen = 'profile';
  const unlinked = ME.providers.filter(p => !ME.logins.some(l => l.provider === p));
  const when = t => new Date(t * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  const recs = ME.records.map(r => { const f = deckFace(r.cover, r.deck);
    return `<div class="dtile rec${ui.histDeck === r.deck ? ' on' : ''}" data-deck="${esc(r.deck)}" style="${f ? stripArt(f, 284, 56, .7) : ''}">
    <b>${esc(r.deck)}</b><span class="wl">${r.won}–${r.lost}</span></div>`; }).join('');
  const shown = ME.history.filter(h => !ui.histDeck || h.my_deck === ui.histDeck);
  const bot = h => h.kind !== 'friend';   // a bot's deck has a name you know; a person's deck name is theirs, so the row names the person
  const result = h => h.won > h.lost ? 'Won' : h.won < h.lost ? 'Lost' : 'Draw';   // a match is one game (older best-of-3s by their result)
  const hist = shown.map(h => `<div class="hr ${h.won > h.lost ? 'won' : h.won < h.lost ? 'lost' : ''}" data-m="${esc(h.match)}"><b>${result(h)}</b>
    ${piece(deckFace(h.my_cover, h.my_deck))}<span class="dk">${esc(h.my_deck)}</span>${bot(h) ? `${piece(deckFace(h.opp_cover, h.opp_deck))}<span class="dk">${esc(h.opp_deck)}</span>
    <span class="meta">${esc(h.opp)} · ${when(h.ended)}</span>` : `${piece(h.opp_cover)}<span class="dk">${esc(h.opp)}</span><span class="meta">${when(h.ended)}</span>`}</div>`).join('');
  const sect = (title, body) => `<div class="sect"><h4>${title}</h4>${body}</div>`;
  const account = ME.logins.length
    ? sect('Account', `${ME.logins.map(l => `<div class="login">${PROVIDER[l.provider]} · ${esc(l.label)}</div>`).join('')}
        <div class="row">${unlinked.map(p => `<button class="slab" data-login="${p}">Also ${PROVIDER[p]}</button>`).join('')}<button class="slab" id="signout">Sign out</button></div>`)
    : ME.providers.length ? sect('Account', `<p>Sign in to keep your decks and matches on every device.</p>
        <div class="row">${ME.providers.map(p => `<button class="slab" data-login="${p}">${PROVIDER[p]}</button>`).join('')}</div>`) : '';
  const code = ME.logins.length ? '' : sect('Sign-in code', `<p>Type it on another device to play there as ${esc(ME.name)}. Anyone with it can too.</p>
      <div class="row"><span class="field keycode" id="key">${ui.showKey ? esc(store('ak:key')) : '••••-••••-••••-••••'}</span><button class="slab" id="showkey">${ui.showKey ? 'Hide' : 'Show'}</button><button class="slab" id="copykey">Copy</button></div>`)
    + sect('Use a different profile', `<div class="row"><input class="field" id="other" placeholder="Sign-in code" autocomplete="off"><button class="slab" id="signin">Sign in</button></div>`);
  app.innerHTML = `<div class="mscr prof"><div class="hist">${hist ? `<div class="recs">${recs}</div><div class="hlist">${hist}</div>` : '<p class="none">No finished matches yet.</p>'}</div>
    <div class="side"><div class="me"><div class="namerow"><input class="field namein" id="pname" maxlength="20" value="${esc(ME.name)}" title="Rename"><span class="tag">#${ME.tag}</span></div>${account}${code}</div>
      <div class="sfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div></div>`;
  document.getElementById('back').onclick = () => { location.hash = '#/'; };
  app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { ui.histDeck = ui.histDeck === el.dataset.deck ? null : el.dataset.deck; profileScreen(); });
  app.querySelectorAll('[data-m]').forEach(el => el.onclick = () => { location.hash = '#/replay/' + el.dataset.m; });
  const nm = document.getElementById('pname');
  nm.onchange = async () => { const r = await api('/api/me', { method: 'PATCH', body: JSON.stringify({ name: nm.value }) });
    if (!r.ok) return toast(await r.text()); ME = await r.json(); profileScreen(); };
  app.querySelectorAll('[data-login]').forEach(el => el.onclick = async () => {
    const r = await api('/api/auth/' + el.dataset.login, { method: 'POST' });
    if (!r.ok) return toast(await r.text());
    location.href = (await r.json()).url;
  });
  const so = document.getElementById('signout');
  if (so) so.onclick = async () => { await api('/api/signout', { method: 'POST' }); localStorage.removeItem('ak:key'); await loadProfile(); location.hash = '#/'; };
  if (ME.logins.length) return;
  document.getElementById('showkey').onclick = () => { ui.showKey = !ui.showKey; profileScreen(); };
  document.getElementById('copykey').onclick = () => navigator.clipboard.writeText(store('ak:key')).then(() => toast('Sign-in code copied', true), () => toast(store('ak:key')));
  const other = document.getElementById('other');
  const signIn = async () => { const r = await api('/api/signin', { method: 'POST', body: JSON.stringify({ code: other.value }) });
    if (!r.ok) return toast('No profile has that sign-in code');
    ME = await r.json(); store('ak:key', other.value.trim().toUpperCase()); ui.showKey = false; toast(`Signed in as ${ME.name}#${ME.tag}`, true); profileScreen(); };
  document.getElementById('signin').onclick = signIn;
  other.onkeydown = e => { if (e.key === 'Enter') signIn(); };
}

// ------------------------------------------------------------------ match connection
function disconnect() { if (ws) { wsId = null; ws.onclose = null; ws.close(); ws = null; } V = null; }

function matchScreen(id) {
  const token = getToken(id);
  if (!token) { location.hash = '#/join/' + id; return; }
  if (wsId === id && ws) return;
  screen = null; V = null; ui.sel = null; ui.peek = false;
  app.innerHTML = `<div class="mscr pre"><p class="wait">Connecting…</p></div>`;
  const connect = () => {
    wsId = id;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${id}?token=${encodeURIComponent(token)}`);
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.t === 'view') { const prev = V; V = m.view; V.rx = Date.now() / 1000; onView(prev); }
      else if (m.t === 'error' && m.error === 'unknown match or seat') { disconnect(); location.hash = '#/'; toast('That match has ended'); }
      else if (m.t === 'error') toast(m.error);
    };
    ws.onclose = () => { if (wsId === id) setTimeout(() => { if (wsId === id) connect(); }, 1000); };
  };
  connect();
}
const send = msg => ws && ws.readyState === 1 && ws.send(JSON.stringify(msg));
const act = action => { ui.sel = null; ui.hover = null; send({ t: 'act', action }); };

function onView(prev) {
  if (V.phase === 'lobby') return lobbyScreen();
  if (V.phase === 'prematch') return prematchScreen();
  if (!prev || prev.phase === 'game_over' && V.phase === 'playing') ui.peek = false;
  if (prev && prev.game && V.game && prev.game.history.length > V.game.history.length) ui.sel = null;
  // One-shot animation input: what the board and food were before this view (same game only).
  ui.anim = prev && prev.game && V.game && prev.game.history.length <= V.game.history.length && prev.you === V.you
    ? { board: viewerBoard(prev), food: { A: prev.game.food[prev.you], B: prev.game.food[prev.you === 'A' ? 'B' : 'A'] },
        income: { A: prev.game.income[prev.you], B: prev.game.income[prev.you === 'A' ? 'B' : 'A'] },
        hand: prev.game.hand.map(h => h.iid), oppHand: prev.game.handCount[prev.you === 'A' ? 'B' : 'A'], hist: prev.game.history.length } : null;
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
      <button class="slab" id="copy">Copy link</button><p>Waiting for your friend to join</p></div>
    <a class="backbtn leave" href="#/"><span>Leave</span></a></div>`;
  document.getElementById('copy').onclick = () => navigator.clipboard.writeText(link).then(() => toast('Link copied', true), () => toast(link));
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
  if (!c || !c.on) { el.innerHTML = ''; return; }
  const spent = c.now + (Date.now() / 1000 - V.rx) - c.since, free = Math.max(0, c.free - spent);
  const bank = Math.max(0, c.bank[c.holder] - Math.max(0, spent - c.free)), left = free + bank;
  el.className = `abs clock ${rel(c.holder)}${left < 10 ? ' low' : ''}`;
  el.innerHTML = `${c.holder === V.you ? 'Your' : "Opponent's"} time <b>${mmss(free > 0 ? free : bank)}</b>${free > 0 ? `<span>+${mmss(bank)}</span>` : ''}`;
}
setInterval(() => { if (screen === 'game') drawClock(); }, 250);

// Viewer space: you are always 'A' on the left; the server's seats are mapped through these.
const opp = () => V.you === 'A' ? 'B' : 'A';
const rel = p => p === V.you ? 'A' : 'B';
const dcr = cr => { if (V.you === 'A') return cr; const [c, r] = cr.split(','); return `${MAP.cols + 1 - Number(c)},${r}`; };

// The tutorial: its opponent is the tutorial's bot. Its lessons seen, per match (a new tutorial starts them over).
const isTutorial = () => !!(V && V.seats && V.seats.B && /^tutorial/.test(V.seats.B.bot || ''));
const tutState = () => { if (!ui.tut || ui.tut.id !== V.id) ui.tut = { id: V.id, seen: new Set(), shown: {} }; return ui.tut; };

// What the seat can do right now, in viewer space.
function decision() {
  const G = V.game, d = { mine: V.phase === 'playing' && G.toAct === V.you && !RP.views.length, rings: [], hqRing: false, crChoice: {}, handPick: new Set(), cardOpts: [], otherOpts: [], places: {}, pend: null };
  if (isTutorial() && V.phase === 'playing') d.lesson = lessonNow(V, ui.sel, CARDS, tutState());   // the tutorial's coach: the lesson for this moment
  if (!d.mine) return d;
  d.pend = G.pending; d.places = G.legal.place;
  if (d.pend && d.pend.mode === 'choice') {
    for (const o of d.pend.options) {
      if (o.kind === 'cr') d.crChoice[dcr(o.cr || o.v)] = o.v;
      else if (o.kind === 'hand') d.handPick.add(o.v);
      else if (o.kind === 'card') d.cardOpts.push(o);
      else d.otherOpts.push(o);
    }
    d.rings = Object.keys(d.crChoice);
    ui.sel = null;
  } else {
    if (d.lesson && d.lesson.only) gate(d, d.lesson.only);   // a forced lesson lets only its step be taken
    if (isTutorial()) {   // teaching cards wait for their step; placing onto your own animal is legal but never taught, so not offered
      d.places = Object.fromEntries(Object.entries(d.places).filter(([id]) => !held(V, d.lesson).includes(id))
        .map(([id, ts]) => [id, ts.filter(t => !(t[0] === 'cr' && (V.game.board[t[1]] || []).slice(-1).some(u => u.owner === V.you)))]).filter(([, ts]) => ts.length));
    }
    if (!ui.sel && d.lesson && d.lesson.only && d.lesson.only.picked && d.places[d.lesson.only.card]) ui.sel = d.lesson.only.card;
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
  let tip = document.getElementById('tip');
  if (!tip) { tip = document.createElement('div'); tip.id = 'tip'; tip.className = 'tip'; document.body.appendChild(tip); }
  root.addEventListener('mouseover', e => { const t = e.target.closest('[data-tip]'); if (!t) { tip.style.display = 'none'; return; }
    tip.textContent = t.dataset.tip; tip.style.display = 'block'; });
  root.addEventListener('mousemove', e => { tip.style.left = (e.clientX + 14) + 'px'; tip.style.top = (e.clientY + 16) + 'px'; });
  root.addEventListener('mouseleave', () => tip.style.display = 'none');
}
function gameScreen() {
  if (screen !== 'game') {
    screen = 'game';
    app.innerHTML = `<div class="game kit" id="scr"><div id="stage">
      <div id="board"></div>
      <div class="abs series" id="series"></div>
      <div class="abs clock" id="clock"></div>
      <div class="abs opphand" id="opphand"></div>
      <div class="abs menu" id="menubtn"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M5 7h14M5 12h14M5 17h14"/></svg>
        <div class="abs menudrop" id="menudrop"><a href="#" id="concede">Concede game</a></div></div>
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
      <div class="endov" id="endov"></div></div></div>`;
    fitStage(); wireTips(document.getElementById('scr'));
    const $ = id => document.getElementById(id);
    $('menubtn').onclick = e => { e.stopPropagation(); $('menudrop').classList.toggle('on'); const c = $('concede'); c.classList.remove('sure'); c.textContent = 'Concede game'; };
    // Conceding asks once, in place: the entry turns into the confirmation; a click elsewhere closes the menu and forgets it.
    $('concede').onclick = e => { e.preventDefault(); e.stopPropagation(); const c = $('concede');
      if (c.classList.contains('sure')) { $('menudrop').classList.remove('on'); send({ t: 'concede' }); }
      else { c.classList.add('sure'); c.textContent = 'Concede this game?'; } };
    // The series opens the history, the opponent's hand their decklist; hovering your deck shows yours.
    const toggle = k => e => { e.stopPropagation(); ui.panel = ui.panel === k ? null : k; showPanel(); };
    $('series').onclick = toggle('hist'); $('opphand').onclick = toggle('theirs');
    $('deck').onmouseenter = () => { ui.panel = 'mine'; showPanel(); };
    $('deck').onmouseleave = () => { if (ui.panel === 'mine') { ui.panel = null; showPanel(); } };
    app.querySelectorAll('.panel').forEach(el => el.onclick = e => e.stopPropagation());
    $('scr').addEventListener('click', () => { $('menudrop').classList.remove('on'); if (ui.panel) { ui.panel = null; showPanel(); } });
    $('deck').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.legal.draw && !d.noDraw) act({ kind: 'draw' }); };
    $('tbtn').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.canPass && !d.noPass) act({ kind: 'pass' }); };
    wireBoard();
  }
  drawGame();
}

function drawGame() {
  const G = V.game, you = V.you, them = opp(), d = decision(), $ = id => document.getElementById(id);
  const playing = V.phase === 'playing', choosing = !!(d.pend && d.pend.mode === 'choice');
  lastDecision = d;
  $('menubtn').style.display = playing && V.id && !RP.views.length ? '' : 'none';   // the menu holds Concede: only a game in play (never the lab or a replay)
  drawReplayBar();

  // Top left: the turn (a match is one game while there is one map); it opens the history. The gauntlet counts its games.
  const gameNo = playing ? V.results.length + 1 : V.results.length;
  $('series').innerHTML = V.gauntlet ? `Game ${gameNo} of ${V.gauntlet.total} · Turn ${G.round}` : `Turn ${G.round}`;
  drawHistory(G); drawLists(G); showPanel();

  // The opponent's hand: one card back each, centred across the board from yours; in a replay their cards, face up (the eye hides them).
  const faces = RP.views.length && RP.eye && G.oppHand;
  const nb = G.handCount[them], step = faces ? Math.min(90, 456 / Math.max(1, nb - 1)) : 52,   // face up, the hand stays clear of the replay's controls
    bx0 = STAGE.w / 2 - (84 + (nb - 1) * step) / 2;
  const A = ui.anim, oppDrew = A ? Math.max(0, nb - A.oppHand) : 0;   // their new cards slide down into their hand
  const slot = i => `${i >= nb - oppDrew ? ' drawn' : ''}" style="left:${bx0 + i * step}px;animation-delay:${(i - (nb - oppDrew)) * 0.12}s`;
  $('opphand').innerHTML = faces
    ? G.oppHand.map((h, i) => `<div class="abs oc ${CARDS[h.id].rarity}${slot(i)}" data-card="${h.id}">${cardHTML(CARDS[h.id], { str: h.str, cls: 'compact' })}</div>`).join('')
    : Array.from({ length: nb }, (_, i) => `<div class="abs back${slot(i)}"></div>`).join('');
  if (faces) { fitNames($('opphand')); $('opphand').querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card, null, 'below'); el.onmouseleave = () => pop.style.display = 'none'; }); }

  // Your hand, centred under the board.
  const n = G.hand.length, cw = 143, gap = n > 1 ? Math.min(14, (940 - n * cw) / (n - 1)) : 0, x0 = STAGE.w / 2 - (n * cw + (n - 1) * gap) / 2;
  const hand = $('hand');
  let drawnK = 0;
  hand.innerHTML = G.hand.map((h, i) => {
    const c = CARDS[h.id], can = d.mine && !d.handPick.size && !choosing && d.places[h.id], pick = d.handPick.has(h.iid);
    const hint = can && d.lesson && d.lesson.only && !ui.sel;   // the card the tutorial asks for
    const talking = d.lesson && d.lesson.next || RP.views.length;   // while the coach talks (or in a replay) the cards stay lit, and a ready card still glows
    const shown = d.lesson && d.lesson.read === h.id;   // the card the coach is explaining, shown large as if hovered
    const cls = [c.rarity, shown ? 'shown' : '', can ? 'can' : '', (can || talking) && h.ready ? 'ready' : '', hint ? 'hint' : '', pick ? 'pick' : '', h.id === ui.sel ? 'sel' : '', !can && !pick && !talking ? 'dim' : ''].join(' ');
    // a card just drawn slides in from the deck (bottom right), the second a beat after the first
    const drawn = A && !A.hand.includes(h.iid) ? ++drawnK : 0, from = drawn ? `--fx:${1299 - (x0 + i * (cw + gap) + cw / 2)}px;animation-delay:${(drawn - 1) * 0.14}s;` : '';
    return `<div class="hc ${cls}${drawn ? ' drawn' : ''}" data-iid="${h.iid}" data-id="${h.id}" style="left:${x0 + i * (cw + gap)}px;z-index:${i + 1};${from}">${cardHTML(c, { str: h.str, cls: 'compact' })}</div>`;
  }).join('');
  fitNames(hand);
  hand.querySelectorAll('.hc').forEach(el => el.onclick = e => {
    e.stopPropagation();
    const iid = Number(el.dataset.iid), id = el.dataset.id;
    if (d.handPick.has(iid)) return act({ kind: 'choice', choice: iid });
    if (!d.mine || !d.places[id]) return;
    ui.sel = ui.sel === id ? null : id; ui.hover = null; drawGame();
  });

  // The deck is Draw 2; the End turn button is also the turn indicator.
  const canDraw = d.mine && !d.pend && G.legal.draw && !d.noDraw;
  $('deck').className = 'abs deck num' + (canDraw ? ' can' : ''); $('deck').innerHTML = canDraw ? 'Draw 2' : '';
  const tb = $('tbtn');
  if (playing && G.current === you) {
    const pips = Array.from({ length: G.actionsTotal }, (_, i) => `<i class="${i < G.actionsTotal - G.actionsLeft ? 'used' : ''}"></i>`).join('');
    tb.className = 'abs tbtn A num' + (d.mine && !d.pend && G.canPass && !d.noPass ? ' can' : ''); tb.innerHTML = `<b>End turn</b><span class="pips">${pips}</span>`;
  } else if (playing) { tb.className = 'abs tbtn B num'; tb.innerHTML = 'Opponent\'s turn'; }
  else { tb.className = 'abs tbtn'; tb.innerHTML = ''; }

  // A pending choice: the asking card and its rule; card options float above the hand.
  const bar = $('choicebar'), opts = $('opts'), waiting = $('waiting');
  waiting.textContent = ''; opts.classList.remove('on'); opts.innerHTML = '';
  if (d.pend && d.pend.kind === 'mulligan') {
    const k = d.pend.returned;
    bar.innerHTML = `<b>Mulligan · ${k} of ${d.pend.cap} replaced</b><p>Click a card to replace it; no copy of a card you replace can come back.</p><div class="btns"><span class="skip" id="skip">${k ? 'Done' : 'Keep hand'}</span></div>`;
    bar.classList.add('on');
    $('skip').onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: SKIP }); };
  } else if (d.pend) {
    const src = d.pend.source && CARDS[d.pend.source];
    const other = d.otherOpts.map((o, i) => `<span class="skip" data-x="${i}">${o.label}</span>`).join('') + (d.pend.optional ? `<span class="skip" id="skip">Skip</span>` : '');
    bar.innerHTML = (src ? `<b>${src.name}</b><p>${src.text}</p>` : '<b>Choose</b>') + (other ? `<div class="btns">${other}</div>` : '');
    bar.classList.add('on');
    if (d.cardOpts.length) {
      opts.innerHTML = d.cardOpts.map((o, i) => { const c = CARDS[o.id]; return `<div class="hc ${c.rarity}" data-o="${i}">${cardHTML(c)}</div>`; }).join('');
      opts.classList.add('on'); fitNames(opts);
      opts.querySelectorAll('[data-o]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.cardOpts[el.dataset.o].v }); });
    }
    bar.querySelectorAll('[data-x]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.otherOpts[el.dataset.x].v }); });
    const sk = $('skip'); if (sk) sk.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: SKIP }); };
  } else {
    bar.classList.remove('on');
    if (playing && G.opponentChoosing) waiting.textContent = G.history.length ? 'Opponent is choosing' : 'Opponent is mulliganing';
  }
  clearTimeout(drawGame.think);
  if (playing && G.toAct === them && V.seats[them].bot && !RP.views.length) {
    const ver = V.version;
    drawGame.think = setTimeout(() => { if (V && V.version === ver && screen === 'game') waiting.textContent = 'Bot is thinking'; }, 2500);
  }
  // The opponent's card, shown large at the centre as it is played, then flown down onto its crossroad (the piece lands as it arrives).
  if (A) A.fx = G.history.slice(A.hist).flatMap(m => m.fx).map(f => f.owner ? { ...f, owner: rel(f.owner) } : f);
  const last = G.history[G.history.length - 1];
  if (A && G.history.length > A.hist && last && last.seat === them && last.kind === 'place') {
    const [tx, ty] = last.target[0] === 'cr' ? crossroadAt(dcr(last.target[1])) : denMouthAt(rel(last.target[1])), rv = $('reveal');
    rv.innerHTML = cardHTML(CARDS[last.card]); fitNames(rv); rv.style.setProperty('--tx', `${tx - STAGE.w / 2}px`); rv.style.setProperty('--ty', `${ty - 300}px`);
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on');
    if (ui.anim) ui.anim.landDelay = 0.95;
    ui.revealEnd = Date.now() + 1050;
  }
  placeCoach($('coach'), d.lesson, d.rings);
  drawBoard(d);
  drawEnd();
}

// The tutorial's coach: a granite piece standing beside what the lesson talks about, its notch pointing at it: above a
// card in the hand, the deck or End turn, beside a crossroad (on the side with more room), a region's stone or a den.
const COACH_W = 300;
function placeCoach(el, L, rings = []) {
  el.className = 'abs coach';
  if (!L) { el.innerHTML = ''; document.getElementById('board').classList.remove('pulse'); return; }
  const a = L.at || {}, card = a.card && document.querySelector(`#hand .hc[data-id="${a.card}"]`);
  let x, y, side;
  const read = a.read && document.querySelector(`#hand .hc[data-id="${a.read}"]`);
  if (read) { const cx = parseFloat(read.style.left) + 71.5;   // beside the large card (2.1x: 300 wide, so 150 + a 24 gap from its middle)
    [x, y, side] = cx - 174 - COACH_W >= 16 ? [cx - 96, 568, 'left'] : [cx + 96, 568, 'right']; }
  else if (card) [x, y, side] = [parseFloat(card.style.left) + 71.5, card.classList.contains('sel') ? 572 : 590, 'above'];   // a picked card stands 18px higher
  else if (a.deck) [x, y, side] = [1299, 606, 'above'];
  else if (a.prompt) [x, y, side] = [151, 604, 'above'];   // the pending choice's piece, bottom left
  else if (a.endturn) [x, y, side] = [1439, 664, 'above'];
  else if (a.cr) { [x, y] = crossroadAt(a.cr); side = x > STAGE.w / 2 ? 'left' : 'right'; }
  else if (a.den) { [x, y] = denMouthAt(a.den); side = a.den === 'B' ? 'left' : 'right'; }
  else if (a.rings && !rings.length) [x, y, side] = [STAGE.w / 2, 590, 'above'];   // no card picked yet: the circles come with one, so point at the hand
  else if (a.rings) {   // beside the group of rings, clear of all of them, with no notch (the rings pulse instead)
    const rs = rings.map(crossroadAt);   // this frame's rings, before the board redraws
    const xs = rs.map(r => r[0]), ys = rs.map(r => r[1]), cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const right = Math.max(...xs) + 78;
    [x, y, side] = right + COACH_W < STAGE.w - 16 ? [right, cy, 'group'] : [Math.min(...xs) - 78 - COACH_W, cy, 'group'];
  }
  else if (a.gem) [x, y, side] = a.gem === 'A' ? [150, 122, 'right'] : [STAGE.w - 150, 122, 'left'];   // a den's food gem, on its crown
  else if (a.hand) [x, y, side] = [STAGE.w / 2, 590, 'above'];
  else if (a.oppcards) [x, y, side] = [STAGE.w / 2 + 170, 72, 'below'];   // beside the opponent's card backs, clear of their revealed card
  else if (a.middle) [x, y, side] = [STAGE.w / 2, 250, 'mid'];
  else if (a.stone) { const [c, r] = a.stone.split(',').map(Number), [x1, y1] = crossroadAt(`${c},${r}`), [x2, y2] = crossroadAt(`${c + 1},${r + 1}`);
    [x, y, side] = [(x1 + x2) / 2 - 20, (y1 + y2) / 2, 'right']; }   // a region's payout stone, in the open ground between crossroads
  else [x, y, side] = [STAGE.w / 2, 590, 'above'];
  const clampX = v => Math.max(16, Math.min(STAGE.w - 16 - COACH_W, v));
  const pos = side === 'above' ? `left:${clampX(x - COACH_W / 2)}px;bottom:${STAGE.h - y + 14}px;--nx:${x - clampX(x - COACH_W / 2)}px`
    : side === 'below' ? `left:${clampX(x - COACH_W / 2)}px;top:${y + 14}px;--nx:${x - clampX(x - COACH_W / 2)}px`
    : side === 'mid' ? `left:${x - COACH_W / 2}px;top:${y}px`
    : side === 'group' ? `left:${x}px;top:${y}px`
    : side === 'right' ? `left:${x + 78}px;top:${y}px` : `left:${x - 78 - COACH_W}px;top:${y}px`;
  // while the opponent's card is shown large in the middle, the coach waits for it to land, then fades in
  const wait = Math.max(0, (ui.revealEnd || 0) - Date.now());
  document.getElementById('board').classList.toggle('pulse', !!a.rings);
  el.className = `abs coach on ${side}${L.next ? ' talk' : ''}${wait ? ' late' : ''}`; el.style.cssText = pos + (wait ? `;animation-delay:${wait}ms` : '');
  el.innerHTML = `<p>${L.text}</p>` + (L.next ? '<button class="slab" id="coachnext">Next</button>' : '');
  // an opening step closes on Next (or Enter/Space), and the next one shows
  if (L.next) el.querySelector('#coachnext').onclick = e => { e.stopPropagation(); tutState().seen.add(L.id); drawGame(); };
}

// The history strip and both decklists, shared by both game screens.
function drawHistory(G) {
  const hist = document.getElementById('hist');
  let hs = '', lastT = null;
  G.history.forEach((m, i) => {
    if (m.round !== lastT) { hs += `<div class="t">Turn ${m.round}</div>`; lastT = m.round; }
    const side = rel(m.seat), t = side === 'A' ? 'a' : 'b';
    // a draw is its count on the team's boss (as a held payout); a placement the unit in small, as on the board
    if (m.kind === 'draw') { const dr = m.fx.find(f => f.k === 'draw' && f.seat === m.seat); hs += `<div class="hi draw ${side}" data-h="${i}">${chalk('+' + (dr ? dr.n : 0))}</div>`; }
    else hs += `<div class="hi unit ${side}" data-h="${i}"><div class="face" style="${portrait(m.card, 32)}"></div><img src="/static/kit2/rim_${t}.webp" alt="" draggable="false"></div>`;
  });
  hist.innerHTML = hs; hist.scrollTop = hist.scrollHeight;
  hist.querySelectorAll('[data-h]').forEach(el => {
    const m = G.history[el.dataset.h];
    el.onmouseenter = () => { if (m.kind === 'place') cardPop(el, m.card, moveLine(m), 'below'); else { pop.className = 'pop'; pop.innerHTML = `<div class="ev">${moveLine(m)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex'; const r = el.getBoundingClientRect(); pop.style.left = Math.min(r.left, innerWidth - 200) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; } };
    el.onmouseleave = () => { pop.style.display = 'none'; pop.style.minHeight = ''; };
  });
  const removed = document.getElementById('removed');
  removed.innerHTML = `Removed <b>${G.removed.length}</b>`;
}
function drawLists(G) {
  const sum = o => Object.values(o).reduce((a, b) => a + b, 0), you = V.you, them = opp();
  const mine = document.getElementById('mine'), theirs = document.getElementById('theirs');
  mine.innerHTML = `<h4>Your deck<span class="n">${sum(G.deckLeft)} left</span></h4><div class="rows">${rows(V.lists[you], G.deckLeft)}</div>`;
  theirs.innerHTML = `<h4>Opponent's cards<span class="n">${sum(G.unseen)} left</span></h4><div class="rows">${rows(V.lists[them], G.unseen)}</div>`;
  wirePops(mine); wirePops(theirs);
}

function showPanel() {
  for (const [k, id] of [['mine', 'mine'], ['theirs', 'theirs'], ['hist', 'histp']]) document.getElementById(id).classList.toggle('on', ui.panel === k);
  if (ui.panel === 'hist') { const h = document.getElementById('hist'); h.scrollTop = h.scrollHeight; }
}
// The stage keeps its design size (STAGE) and scales, letterboxed, to the window.
function fitStage() {
  const st = document.getElementById('stage'); if (!st) return;
  st.style.transform = `scale(${Math.min(innerWidth / STAGE.w, innerHeight / STAGE.h)}) translate(-50%, -50%)`;
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
function drawBoard(d) {
  d = d || lastDecision; lastDecision = d;
  const g = viewerGame();
  let preview = null;
  if (ui.sel && ui.hover && d.rings.includes(ui.hover)) {
    const strs = V.game.hand.filter(h => h.id === ui.sel).map(h => h.str);
    preview = { cr: ui.hover, id: ui.sel, str: Math.max(...strs) };
  }
  const A = ui.anim; ui.anim = null;   // the animations play once, never on hover redraws
  const last = V.game.history[V.game.history.length - 1], won = V.game.result && V.game.result.reason === 'hq_capture' && last && last.target && last.target[0] === 'hq';
  const capture = won ? { side: rel(last.target[1]), id: last.card, owner: rel(last.seat), str: CARDS[last.card].str } : null;
  renderBoard(document.getElementById('board'), viewerMap(), g, CARDS, { rings: d.rings, hqRing: d.hqRing, preview, anim: A, capture, current: V.phase === 'playing' ? rel(V.game.current) : null });
}

function wireBoard() {
  const board = document.getElementById('board');
  board.addEventListener('click', e => {
    const den = e.target.closest('[data-den]');   // a den opens that player's list
    if (den) { e.stopPropagation(); ui.panel = ui.panel === den.dataset.den ? null : den.dataset.den; showPanel(); return; }
    const d = lastDecision; if (!d || !d.mine) return;
    const hq = e.target.closest('[data-hq]');
    if (hq && ui.sel) { const t = d.places[ui.sel].find(t => t[0] === 'hq'); if (t) return act({ kind: 'place', card_id: ui.sel, target: t }); }
    const g = e.target.closest('[data-cr]'); if (!g) return;
    const cr = g.dataset.cr;
    if (cr in d.crChoice) return act({ kind: 'choice', choice: d.crChoice[cr] });
    if (ui.sel && d.rings.includes(cr)) return act({ kind: 'place', card_id: ui.sel, target: ['cr', dcr(cr)] });
  });
  board.addEventListener('mouseover', e => {
    const g = e.target.closest('[data-cr]'), cr = g ? g.dataset.cr : null;
    showStack(g, cr);
    if (cr === ui.hover) return;
    ui.hover = cr;
    if (ui.sel) drawBoard();
  });
  board.addEventListener('mouseleave', () => { showStack(null, null); if (ui.hover) { ui.hover = null; if (ui.sel) drawBoard(); } });
  board.addEventListener('contextmenu', e => { if (ui.sel) { e.preventDefault(); ui.sel = null; drawGame(); } });
}

// Hover a piece: the whole stack as cards, the top unit first, then each buried card top to bottom.
// Shown after a short rest on the piece, and never while targets are ringed (it would cover them).
let stackTimer = null, stackCr = null;
function showStack(g, cr) {
  if (cr === stackCr) return;
  stackCr = cr; clearTimeout(stackTimer); stackpop.style.display = 'none';
  const st = cr && viewerGame().board[cr];
  if (!st || !st.length || ui.sel || (lastDecision && lastDecision.rings.length)) return;
  stackTimer = setTimeout(() => stackAt(cr), 350);
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
  if (V.phase === 'playing' || !G.result) { ov.classList.remove('on'); return; }
  if (ui.peek) { ov.classList.remove('on'); document.getElementById('waiting').innerHTML = `<button class="slab" id="unpeek">Back to results</button>`; document.getElementById('unpeek').onclick = () => { ui.peek = false; drawGame(); }; return; }
  const you = V.you, them = opp(), w = G.result.winner, S = V.score;
  const res = w === null ? ['D', 'Draw'] : w === you ? ['A', 'Victory'] : ['B', 'Defeat'];
  const how = { hq_capture: w === you ? 'Enemy den captured' : 'Your den was captured', food: `${w === you ? 'You' : 'Your opponent'} reached ${G.winFood} food`, exhaustion: 'Exhaustion · more food wins', passes: 'Both passed · more food wins', max_turns: 'Turn limit · more food wins', concede: w === you ? 'Your opponent conceded' : 'You conceded' }[G.result.reason] || G.result.reason;
  const score = `<div class="score"><span class="gem A">${gemDigits(S[you])}</span><span class="gem B">${gemDigits(S[them])}</span></div>`;
  const peek = `<button class="slab" id="peek">See the board</button>`;
  if (RP.views.length) {
    // a replay: the game's result, then the replay again or back to the profile
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div><div class="how">${how} · turn ${G.round}</div>
      <div class="btns"><a class="slab" href="#/profile">Back</a>${peek}<button class="play" id="again">Watch again</button></div></div>`;
    document.getElementById('again').onclick = () => { replayStep(0); replayPlay(true); };
  } else if (V.gauntlet) {
    const g = V.gauntlet, tot = g.record.reduce((a, r) => [a[0] + r.w, a[1] + r.l], [0, 0]);
    const rows = g.record.map(r => `<div>${r.deckName} <b>${r.w}–${r.l}</b></div>`).join('');
    const done = V.phase === 'match_over';
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${done ? 'Gauntlet done' : res[1]}</div><div class="how">${how} · turn ${G.round}</div>
      <div class="how">Game ${g.played} of ${g.total} · overall <b>${tot[0]}–${tot[1]}</b></div><div class="how">${rows}</div>
      ${done ? '' : `<div class="next">Next: ${g.next.yours ? `you play ${g.next.deckName}` : `vs ${g.next.deckName}`} · ${g.next.first === you ? 'you go first' : 'your opponent goes first'}</div>`}
      <div class="btns">${peek}${done ? '<a class="play" href="#/">Menu</a>' : '<button class="play" id="nextg">Next game</button>'}</div></div>`;
    if (!done) document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else if (V.phase === 'game_over') {
    const firstNext = w === null ? G.first : (w === you ? them : you);
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div><div class="how">${how} · turn ${G.round}</div>${score}
      <div class="next">Game ${V.results.length + 1}: ${firstNext === you ? 'you go first' : 'your opponent goes first'}</div>
      <div class="btns">${peek}<button class="play" id="nextg">Next game</button></div></div>`;
    document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else if (isTutorial()) {
    // a lesson's end: lesson 1 leads on to lesson 2, lesson 2 to a real match; a loss offers the same lesson again
    const lesson = lessonOf(V), won = w === you;
    if (won) store(lesson === 1 ? 'ak:lesson' : 'ak:learned', '1');
    const next = !won ? '' : lesson === 1 ? '<div class="next">One more lesson to go.</div>' : '<div class="next">You know the basics. Pick a deck and play a match.</div>';
    const go = !won ? `<a class="slab" href="#/">Menu</a>${peek}<button class="play" id="again">Try again</button>`
      : lesson === 1 ? `${peek}<button class="play" id="nextlesson">Next lesson</button>` : `${peek}<a class="play" href="#/">Play a match</a>`;
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div><div class="how">${how} · turn ${G.round}</div>${next}<div class="btns">${go}</div></div>`;
    if (!won) document.getElementById('again').onclick = () => startTutorial(lesson);
    if (won && lesson === 1) document.getElementById('nextlesson').onclick = () => startTutorial(2);
  } else {
    // one game: its result; a series (best-of-3, back with the maps): the match's result and the score in the gems
    const won = S[you] > S[them], series = V.results.length > 1;
    ov.innerHTML = `<div class="endbox">${series ? `<div class="res ${won ? 'A' : 'B'}">${won ? 'Match won' : 'Match lost'}</div><div class="how">${res[1]} in game ${V.results.length} · ${how}</div>${score}`
      : `<div class="res ${res[0]}">${res[1]}</div><div class="how">${how} · turn ${G.round}</div>`}
      <div class="btns"><a class="slab" href="#/">Menu</a>${peek}<button class="play" id="rematch">Rematch</button></div></div>`;
    document.getElementById('rematch').onclick = () => send({ t: 'rematch' });
  }
  document.getElementById('peek').onclick = () => { ui.peek = true; drawGame(); };
  ov.classList.add('on');
}

// ------------------------------------------------------------------ replay
// A finished match played back on the game screen: every view you saw, one per action, stepped or played at the bot's pace.
// Nothing can be done on the board; the controls sit where the menu does, and the arrows and Space drive them too.
const RP = { key: null, views: [], i: 0, playing: false, timer: null, eye: true };   // eye: the opponent's hand shown
async function replayScreen(key) {
  if (RP.key === key && RP.views.length) return;
  stopReplay(); screen = null; RP.key = key;
  app.innerHTML = `<div class="mscr pre"><p class="wait">Loading the replay…</p></div>`;
  const back = msg => { RP.key = null; history.replaceState(null, '', '#/profile'); profileScreen(); toast(msg); };
  let views;
  try { const r = await api('/api/replay/' + encodeURIComponent(key)); if (!r.ok) throw new Error(await r.text()); views = await r.json(); }
  catch (e) { if (RP.key === key) back(e.message || 'The replay didn\'t load, try again'); return; }
  if (RP.key !== key) return;   // left while it loaded
  RP.views = views; RP.eye = true; ui.peek = false; ui.sel = null; ui.panel = null;
  replayStep(0); replayPlay(true);
}
function stopReplay() { clearTimeout(RP.timer); Object.assign(RP, { key: null, views: [], i: 0, playing: false }); }
function replayStep(i) {
  i = Math.max(0, Math.min(RP.views.length - 1, i));
  const prev = V, step = i === RP.i + 1; RP.i = i; V = RP.views[i]; V.rx = Date.now() / 1000;
  onView(step ? prev : null);   // one step forward plays its animation; any jump lands at once
}
// Playing: the next view after the same beat the bot takes, longer while the opponent's card is shown.
function replayPlay(on) {
  clearTimeout(RP.timer); RP.playing = on && RP.i < RP.views.length - 1;
  if (RP.playing) {
    const G = V.game, last = G.history[G.history.length - 1], shown = last && last.seat !== V.you && last.kind === 'place';
    RP.timer = setTimeout(() => { replayStep(RP.i + 1); replayPlay(true); }, RP.i === 0 ? 1400 : shown ? 2200 : 1100);
  }
  drawReplayBar();
}
const RICON = { back: '<path d="M15 6l-6 6 6 6"/>', fwd: '<path d="M9 6l6 6-6 6"/>', play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
  pause: '<path d="M8.5 6v12M15.5 6v12"/>', eye: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/><path d="M4 20L20 4"/>' };
const ric = k => `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">${RICON[k]}</svg>`;
function drawReplayBar() {
  const bar = document.getElementById('rbar');
  if (!bar) return;
  if (!RP.views.length) { bar.innerHTML = ''; bar.classList.remove('on'); return; }
  const n = RP.views.length - 1, pct = n ? RP.i / n * 100 : 100;
  bar.classList.add('on');
  bar.innerHTML = `<button class="slab" id="rback" tabindex="-1" data-tip="Back one move">${ric('back')}</button>
    <button class="slab" id="rplay" tabindex="-1" data-tip="${RP.playing ? 'Pause' : 'Play'}">${ric(RP.playing ? 'pause' : 'play')}</button>
    <button class="slab" id="rfwd" tabindex="-1" data-tip="Forward one move">${ric('fwd')}</button>
    <div class="track" id="rtrack"><i style="width:${pct}%"></i></div>
    <button class="slab" id="reye" tabindex="-1" data-tip="${RP.eye ? 'Hide' : 'Show'} your opponent's hand">${ric(RP.eye ? 'eye' : 'eyeoff')}</button>
    <a class="slab out" href="#/profile">Leave</a>`;
  const $ = id => document.getElementById(id), stop = f => e => { e.stopPropagation(); f(e); };
  $('rback').onclick = stop(() => { replayPlay(false); replayStep(RP.i - 1); });
  $('rfwd').onclick = stop(() => { replayPlay(false); replayStep(RP.i + 1); });
  $('rplay').onclick = stop(() => replayPlay(!RP.playing));
  $('reye').onclick = stop(() => { RP.eye = !RP.eye; drawGame(); });
  $('rtrack').onclick = stop(e => { const r = e.currentTarget.getBoundingClientRect(); replayPlay(false); replayStep(Math.round((e.clientX - r.left) / r.width * n)); });
}
function replayKey(e) {
  if (e.key === 'ArrowLeft') { replayPlay(false); replayStep(RP.i - 1); }
  else if (e.key === 'ArrowRight') { replayPlay(false); replayStep(RP.i + 1); }
  else if (e.key === ' ') { e.preventDefault(); replayPlay(!RP.playing); }
  else if (e.key === 'Escape' && !ui.panel) location.hash = '#/profile';
  else return false;
  return true;
}

window.__ak = () => ({ V, ui, d: lastDecision });   // test hook: the headless play-through reads the view
window.__ak.cards = () => CARDS;   // test hook: the card pool as the client holds it
window.__ak.feed = v => { const prev = V; V = v; onView(prev); };   // test hook: play a recorded sequence of views through the client
boot();
addEventListener('keydown', e => {   // the tutorial's Next also answers Enter and Space
  const next = screen === 'game' && document.getElementById('coachnext');
  if (next && (e.key === 'Enter' || e.key === ' ') && document.activeElement.tagName !== 'TEXTAREA') { e.preventDefault(); next.click(); }
});
