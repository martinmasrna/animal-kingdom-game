// Animal Kingdom web client: menu flow (home -> play -> pre-match) and the game screen.
// The server holds the game; this file only renders the seat's view and sends choices back.
import { hasArt, artUrl } from './art.js';
import { cardHTML } from './card.js';
import { renderBoard, STAGE, crossroadAt } from './board.js';

const app = document.getElementById('app'), pop = document.getElementById('pop'), stackpop = document.getElementById('stackpop');
const COVER = { cats_midrange: 'king_theron', canine_buff_tempo: 'lobo', aggro_hq_rush: 'verminus', colony_food_swarm: 'queen_honoria',
  egg_control: 'eon', food_otk: 'rat_king', ramp: 'borealis' };
const RANK = { legendary: 0, rare: 1, common: 2 };
const COL = { A: 'var(--A)', B: 'var(--B)' };   // history tiles in team colour
const SKIP = '__skip__';
const artStyle = id => hasArt(id) ? `style="background-image:url(${artUrl(id)})"` : '';
const sv = c => c.str === '*' ? -1 : c.str;
const store = (k, v) => { try { v === undefined ? null : localStorage.setItem(k, v); return localStorage.getItem(k); } catch { return null; } };
const tokenKey = id => 'ak:seat:' + id;
const getToken = id => { try { return sessionStorage.getItem(tokenKey(id)); } catch { return null; } };
const setToken = (id, t) => { try { sessionStorage.setItem(tokenKey(id), t); } catch { /* private mode: the tab just can't reconnect */ } };

let CARDS = {}, MAP, DECKS = [];
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
function rows(list, counts) {
  let s = '', g = null;
  sortIds(Object.keys(list)).forEach(id => {
    const c = CARDS[id], k = counts ? (counts[id] || 0) : list[id];
    if (c.rarity !== g) { if (g) s += '<div class="grp"></div>'; g = c.rarity; }
    s += `<div class="dr ${c.rarity}${k ? '' : ' gone'}" data-card="${id}"><div class="ban gradart" ${artStyle(id)}></div><span class="s">${c.str}</span><span class="nm">${c.name}</span><span class="x">${k}</span></div>`;
  });
  return s;
}
function tribes(list) {
  const FAM = ['Cat', 'Canine', 'Rodent', 'Colony', 'Bird', 'Megafauna', 'Snake', 'Bear', 'Egg', 'Lizard'], t = {};
  Object.entries(list).forEach(([id, n]) => CARDS[id].tags.filter(x => FAM.includes(x)).forEach(x => t[x] = (t[x] || 0) + n));
  return Object.entries(t).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([x, k]) => k + ' ' + x).join(' · ');
}
const counted = ids => ids.reduce((o, id) => (o[id] = (o[id] || 0) + 1, o), {});
function cardPop(el, id, extra, place) {
  const c = CARDS[id], r = el.getBoundingClientRect();
  pop.className = 'pop ' + c.rarity;
  pop.innerHTML = cardHTML(c) + (extra ? `<div class="ev">${extra}</div>` : '');
  pop.style.display = 'flex';
  const h = pop.offsetHeight;
  if (place === 'below') { pop.style.left = Math.min(r.left, innerWidth - 200) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; }
  else { pop.style.left = (r.right + 10 + 190 > innerWidth ? r.left - 200 : r.right + 10) + 'px'; pop.style.top = Math.max(8, Math.min(r.top - 40, innerHeight - h - 10)) + 'px'; }
}
function wirePops(root) {
  root.querySelectorAll('[data-card]').forEach(el => {
    el.onmouseenter = () => cardPop(el, el.dataset.card);
    el.onmouseleave = () => pop.style.display = 'none';
  });
}
function miniMap(w, h) {
  const { cols, rows: rs } = MAP, px = 34, py = 16, sx = (w - 2 * px) / (cols - 1), sy = (h - 2 * py) / (rs - 1);
  const P = (c, r) => [px + (c - 1) * sx, py + (r - 1) * sy];
  let s = '';
  for (const reg of MAP.regions) { const [c, r] = reg.c, [x, y] = P(c, r), a = reg.food >= 15 ? 0.28 : 0.12;
    s += `<rect x="${x + 5}" y="${y + 5}" width="${sx - 10}" height="${sy - 10}" rx="3" fill="rgba(207,171,102,${a})"/>`;
    s += `<text x="${x + sx / 2}" y="${y + sy / 2}" text-anchor="middle" dominant-baseline="central" font-family="var(--font-display)" font-weight="600" font-size="12" fill="var(--muted)">+${reg.food}</text>`; }
  for (let c = 1; c <= cols; c++) for (let r = 1; r <= rs; r++) { const [x, y] = P(c, r);
    if (c < cols) { const [x2] = P(c + 1, r); s += `<line x1="${x}" y1="${y}" x2="${x2}" y2="${y}" stroke="var(--line-strong)" stroke-width="1.5"/>`; }
    if (r < rs) { const [, y2] = P(c, r + 1); s += `<line x1="${x}" y1="${y}" x2="${x}" y2="${y2}" stroke="var(--line-strong)" stroke-width="1.5"/>`; } }
  for (let c = 1; c <= cols; c++) for (let r = 1; r <= rs; r++) { const [x, y] = P(c, r); s += `<circle cx="${x}" cy="${y}" r="4" fill="var(--muted)"/>`; }
  s += `<rect x="4" y="${py}" width="12" height="${h - 2 * py}" rx="3" fill="var(--you)" opacity="0.8"/><rect x="${w - 16}" y="${py}" width="12" height="${h - 2 * py}" rx="3" fill="var(--them)" opacity="0.8"/>`;
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" preserveAspectRatio="xMidYMid meet">${s}</svg>`;
}
function deckTile(d, on) {
  const list = counted(d.list), cover = COVER[d.id] || (d.mine && sortIds(Object.keys(list))[0]), cv = cover ? artStyle(cover) : '';
  return `<div class="dk${on ? ' on' : ''}" data-deck="${d.id}"><div class="cv gradart" ${cv}></div><div class="in"><b>${d.name}</b><span>${d.mine ? 'Your deck' : 'Starter deck'} · ${d.list.length} cards</span><span>${tribes(list)}</span></div></div>`;
}
// Player-built decks live in this browser: [{id, name, cards: {cardId: copies}}]. Only complete ones are playable.
const myDecks = () => { try { return JSON.parse(localStorage.getItem('ak:decks') || '[]').map(d => ({ ...d, cards: Object.fromEntries(Object.entries(d.cards).filter(([id]) => CARDS[id])) })); } catch { return []; } };
const saveDecks = ds => { try { localStorage.setItem('ak:decks', JSON.stringify(ds)); } catch { /* private mode */ } };
const deckSize = cards => Object.values(cards).reduce((a, n) => a + n, 0);
const playable = () => DECKS.concat(myDecks().filter(d => deckSize(d.cards) === 30).map(d => ({ id: 'my:' + d.id, name: d.name, mine: true, list: Object.entries(d.cards).flatMap(([id, n]) => Array(n).fill(id)) })));
const chosenDeck = () => { const all = playable(), id = store('ak:deck'); return all.find(d => d.id === id) || all[0]; };
const deckSpec = d => d.mine ? { name: d.name, list: d.list } : d.id;

// ------------------------------------------------------------------ routing
async function boot() {
  const p = await fetch('/api/pool').then(r => r.json());
  CARDS = Object.fromEntries(p.cards.map(c => [c.id, c])); MAP = p.map; DECKS = p.decks;
  addEventListener('hashchange', route);
  addEventListener('resize', () => { if (screen === 'game') fitStage(); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && ui.sel) { ui.sel = null; drawGame(); } });
  route();
}

function route() {
  pop.style.display = 'none'; stackpop.style.display = 'none';
  const parts = (location.hash.slice(1) || '/').split('/').filter(Boolean);
  const id = parts[1] && parts[1].toUpperCase();
  if (parts[0] !== 'm' || id !== wsId) disconnect();
  if (parts[0] === 'play') return playScreen();
  if (parts[0] === 'collection') return collectionScreen();
  if (parts[0] === 'join' && id) return joinScreen(id);
  if (parts[0] === 'm' && id) return matchScreen(id);
  if (parts[0] === 'lab' && parts[1]) return labScreen(parts[1]);
  homeScreen();
}

function homeScreen() {
  screen = 'home';
  app.innerHTML = `<div class="home-bg"></div><div class="center"><div class="title">Animal<br>Kingdom</div>
    <div class="nav"><a class="play" href="#/play">Play</a><a href="#/collection">Collection</a></div></div>`;
}

// ------------------------------------------------------------------ play
const play = { opp: 'bot', level: 'normal', botDeck: 'random', code: '' };
function playScreen() {
  screen = 'play';
  const chosen = chosenDeck(), deck = chosen.id;
  const chip = (k, v, label) => `<span class="chip${play[k] === v ? ' on' : ''}" data-k="${k}" data-v="${v}">${label}</span>`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Menu</a><h1>Play</h1></div>
    <div class="body">
      <div class="opp"><div class="lbl">Opponent</div>
        <div class="opt${play.opp === 'friend' ? ' on' : ''}" data-opp="friend"><b>Friend</b><span>Invite someone with a link or a code</span></div>
        ${play.opp === 'friend' ? `<div class="sub"><div class="lbl">Join with a code</div><div class="row"><input class="codein" id="code" maxlength="6" value="${play.code}" placeholder="CODE"><span class="chip on" id="joinbtn">Join</span></div></div>` : ''}
        <div class="opt${play.opp === 'bot' ? ' on' : ''}" data-opp="bot"><b>Bot</b><span>Play against the computer</span></div>
        <div class="opt${play.opp === 'gauntlet' ? ' on' : ''}" data-opp="gauntlet"><b>Gauntlet</b><span>10 games against each other deck, 5 going first, 5 going second</span></div>
        ${play.opp === 'gauntlet' ? `<div class="sub"><div class="lbl">Level</div><div class="row">${chip('level', 'easy', 'Easy')}${chip('level', 'normal', 'Normal')}${chip('level', 'expert', 'Expert')}</div></div>` : ''}
        ${play.opp === 'bot' ? `<div class="sub"><div class="lbl">Level</div><div class="row">${chip('level', 'easy', 'Easy')}${chip('level', 'normal', 'Normal')}${chip('level', 'expert', 'Expert')}</div>
          <div class="lbl">Their deck</div><div class="row">${chip('botDeck', 'random', 'Random')}${DECKS.map(d => chip('botDeck', d.id, d.name)).join('')}</div></div>` : ''}
      </div>
      <div class="decks"><div class="lbl">Your deck</div><div class="grid">${playable().map(d => deckTile(d, d.id === deck)).join('')}</div></div>
    </div>
    <div class="bar"><span class="fmt">${play.opp === 'gauntlet' ? '60 games · your deck against the other six · both decklists open' : 'Best of 3 · one deck for the whole match · both decklists open'}</span><button class="btn primary" id="go">${play.opp === 'friend' ? 'Create match' : play.opp === 'gauntlet' ? 'Start gauntlet' : 'Start match'}</button></div>`;
  app.querySelectorAll('[data-opp]').forEach(el => el.onclick = () => { play.opp = el.dataset.opp; playScreen(); });
  app.querySelectorAll('.chip[data-k]').forEach(el => el.onclick = () => { play[el.dataset.k] = el.dataset.v; playScreen(); });
  app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { store('ak:deck', el.dataset.deck); playScreen(); });
  const code = document.getElementById('code');
  if (code) {
    code.oninput = () => play.code = code.value.trim().toUpperCase();
    code.onkeydown = e => { if (e.key === 'Enter') joinCode(); };
    document.getElementById('joinbtn').onclick = joinCode;
  }
  document.getElementById('go').onclick = async () => {
    const body = { deck: deckSpec(chosen), name: 'You' };
    if (play.opp === 'bot') {
      const bd = play.botDeck === 'random' ? DECKS[Math.floor(Math.random() * DECKS.length)].id : play.botDeck;
      body.bot = { level: play.level, deck: bd };
    }
    if (play.opp === 'gauntlet') body.gauntlet = { level: play.level };
    const r = await fetch('/api/match', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
}
function joinCode() { if (play.code) location.hash = '#/join/' + play.code; }

function joinScreen(id) {
  screen = 'join';
  if (getToken(id)) { location.hash = '#/m/' + id; return; }
  const chosen = chosenDeck(), deck = chosen.id;
  app.innerHTML = `<div class="top"><a class="back" href="#/play">‹ Play</a><h1>Join match ${id}</h1></div>
    <div class="body"><div class="decks"><div class="lbl">Your deck</div><div class="grid">${playable().map(d => deckTile(d, d.id === deck)).join('')}</div></div></div>
    <div class="bar"><span class="fmt">Best of 3 · one deck for the whole match · both decklists open</span><button class="btn primary" id="go">Join</button></div>`;
  app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { store('ak:deck', el.dataset.deck); joinScreen(id); });
  document.getElementById('go').onclick = async () => {
    const r = await fetch(`/api/match/${id}/join`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ deck: deckSpec(chosen), name: 'Friend' }) });
    if (!r.ok) return toast(r.status === 404 ? `No match ${id}` : await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
}


// ------------------------------------------------------------------ collection (= the deckbuilder)
// One screen, Martin's round B1: filters and art tiles on the left, the deck being edited on the right.
// Click a tile to add a copy, click a deck row to take one out; every change saves.
const LIMIT = { legendary: 1, rare: 2, common: 3 }, CAP = { legendary: 4, rare: 8 };
const FAMS = ['Bear', 'Bird', 'Canine', 'Cat', 'Colony', 'Lizard', 'Megafauna', 'Rodent', 'Snake'];
const coll = { q: '', rar: null, str: null, fam: null, sort: 'str', deck: null };
function collectionScreen() {
  screen = 'collection';
  const pool = Object.values(CARDS).filter(c => DECKS.some(d => d.id === c.deck));
  let decks = myDecks();
  if (coll.deck !== '+' && !decks.some(d => d.id === coll.deck)) coll.deck = decks[0] ? decks[0].id : '+';
  const cur = decks.find(d => d.id === coll.deck);
  const inDeck = r => cur ? Object.entries(cur.cards).filter(([id]) => !r || CARDS[id].rarity === r).reduce((a, [, n]) => a + n, 0) : 0;
  const maxed = c => (cur.cards[c.id] || 0) >= (c.copies || LIMIT[c.rarity]) || (CAP[c.rarity] && inDeck(c.rarity) >= CAP[c.rarity]);
  const canAdd = c => cur && inDeck() < 30 && !maxed(c);
  const q = coll.q.toLowerCase();
  const shown = pool.filter(c => (!coll.rar || c.rarity === coll.rar) && (coll.str === null || c.str === coll.str) && (!coll.fam || c.tags.includes(coll.fam))
    && (!q || (c.name + ' ' + c.text + ' ' + c.tags.join(' ')).toLowerCase().includes(q)))
    .sort(coll.sort === 'str' ? (a, b) => sv(a) - sv(b) || RANK[a.rarity] - RANK[b.rarity] || a.name.localeCompare(b.name)
                              : (a, b) => RANK[a.rarity] - RANK[b.rarity] || sv(a) - sv(b) || a.name.localeCompare(b.name));
  const seg = (k, opts) => '<span class="seg">' + opts.map(([v, l]) => `<span class="${coll[k] === v ? 'on' : ''}" data-k="${k}" data-v="${v}">${l}</span>`).join('') + '</span>';
  const tiles = shown.map(c => { const n = cur ? cur.cards[c.id] || 0 : 0;
    return `<div class="tl ${c.rarity}${cur && maxed(c) ? ' max' : ''}" data-add="${c.id}" data-card="${c.id}"><div class="im gradart" ${artStyle(c.id)}></div><span class="s">${c.str}</span>${n ? `<span class="c">${n}</span>` : ''}<span class="n">${c.name}</span></div>`; }).join('');
  const sec = (r, label) => { const n = inDeck(r), cap = CAP[r];
    const list = cur ? Object.keys(cur.cards).filter(id => CARDS[id].rarity === r) : [];
    return `<h3><span>${label}</span><span class="${cap && n >= cap ? 'full' : ''}">${n}${cap ? ' / ' + cap : ''}</span></h3>` +
      rows(Object.fromEntries(list.map(id => [id, cur.cards[id]]))).replace(/class="dr /g, 'data-rm class="dr '); };
  const panel = cur ? `<div class="dhead"><select id="dsel">${decks.map(d => `<option value="${d.id}"${d.id === cur.id ? ' selected' : ''}>${d.name}</option>`).join('')}<option value="+">+ New deck</option></select>
      <div class="dname"><input id="dname" maxlength="40" value="${cur.name.replace(/"/g, '&quot;')}"><b class="${inDeck() === 30 ? 'ok' : ''}">${inDeck()}<i> / 30</i></b></div></div>
      <div class="dlist">${sec('legendary', 'Legendary')}${sec('rare', 'Rare')}${sec('common', 'Common')}</div>
      <div class="dfoot"><span>${tribes(cur.cards) || 'Click a card to add it'}</span><span class="del" id="ddel">Delete</span></div>`
    : `<div class="dnew"><div class="lbl">New deck</div><span class="chip on" data-new="">Empty deck</span>${DECKS.map(d => `<span class="chip" data-new="${d.id}">Copy ${d.name}</span>`).join('')}${decks.length ? `<span class="back" data-k="deck" data-v="${decks[0].id}">‹ Back to ${decks[0].name}</span>` : ''}</div>`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Menu</a><h1>Collection</h1><span class="r">${pool.length} cards</span></div>
    <div class="filters"><input class="search" id="q" placeholder="Search" value="${coll.q.replace(/"/g, '&quot;')}">${seg('rar', [[null, 'All'], ['legendary', 'Legendary'], ['rare', 'Rare'], ['common', 'Common']])}
      <span class="strs">${[null, 0, 1, 2, 3, 4, 5, 6, 7, 8, 10].map(v => `<span class="${coll.str === v ? 'on' : ''}" data-k="str" data-v="${v}">${v === null ? 'All' : v}</span>`).join('')}</span>
      <select id="fam"><option value="">All families</option>${FAMS.map(f => `<option${coll.fam === f ? ' selected' : ''}>${f}</option>`).join('')}</select>
      <span class="gap"></span><span class="lbl">Sort</span>${seg('sort', [['str', 'Strength'], ['rar', 'Rarity']])}</div>
    <div class="cbody"><div class="tiles">${tiles || '<span class="none">No cards match</span>'}</div><div class="dpanel">${panel}</div></div>`;
  wirePops(app);
  const save = () => { saveDecks(decks); collectionScreen(); };
  app.querySelectorAll('[data-k]').forEach(e => e.onclick = () => { const k = e.dataset.k, v = e.dataset.v; coll[k] = v === 'null' ? null : k === 'str' ? +v : v; collectionScreen(); });
  const qi = document.getElementById('q');
  qi.oninput = () => { coll.q = qi.value; const at = qi.selectionStart; collectionScreen(); const n = document.getElementById('q'); n.focus(); n.setSelectionRange(at, at); };
  document.getElementById('fam').onchange = e => { coll.fam = e.target.value || null; collectionScreen(); };
  app.querySelectorAll('[data-add]').forEach(e => e.onclick = () => { const c = CARDS[e.dataset.add]; if (!cur) return toast('Make a deck first'); if (!canAdd(c)) return;
    cur.cards[c.id] = (cur.cards[c.id] || 0) + 1; pop.style.display = 'none'; save(); });
  app.querySelectorAll('[data-rm]').forEach(e => e.onclick = () => { const id = e.dataset.card; if (--cur.cards[id] <= 0) delete cur.cards[id]; pop.style.display = 'none'; save(); });
  app.querySelectorAll('[data-new]').forEach(e => e.onclick = () => { const src = DECKS.find(d => d.id === e.dataset.new);
    const d = { id: Date.now().toString(36), name: src ? src.name + ' copy' : 'New deck', cards: src ? counted(src.list) : {} };
    decks.push(d); coll.deck = d.id; save(); });
  if (!cur) return;
  document.getElementById('dsel').onchange = e => { coll.deck = e.target.value; collectionScreen(); };
  const nm = document.getElementById('dname'); nm.onchange = () => { cur.name = nm.value.trim() || 'New deck'; save(); };
  document.getElementById('ddel').onclick = () => { decks = decks.filter(d => d.id !== cur.id); coll.deck = null; save(); };
}

// ------------------------------------------------------------------ match connection
function disconnect() { if (live) setLive(false); if (ws) { wsId = null; ws.onclose = null; ws.close(); ws = null; } V = null; }

function matchScreen(id) {
  const token = getToken(id);
  if (!token) { location.hash = '#/join/' + id; return; }
  if (wsId === id && ws) return;
  screen = null; V = null; ui.sel = null; ui.peek = false;
  app.innerHTML = `<div class="lobby"><div class="lbl">Connecting…</div></div>`;
  const connect = () => {
    wsId = id;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${id}?token=${encodeURIComponent(token)}`);
    ws.onmessage = e => {
      const m = JSON.parse(e.data);
      if (m.t === 'view') { const prev = V; V = m.view; onView(prev); }
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

function lobbyScreen() {
  screen = 'lobby';
  const link = `${location.origin}/#/join/${V.id}`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Leave</a><h1>Match</h1><span class="r">Best of 3</span></div>
    <div class="lobby"><div class="lbl">Invite a friend</div><div class="code">${V.id}</div>
      <div class="link">${link}</div><span class="chip on" id="copy">Copy link</span>
      <div class="lbl" style="margin-top:24px">Waiting for them to join</div></div>`;
  document.getElementById('copy').onclick = () => navigator.clipboard.writeText(link).then(() => toast('Link copied', true), () => toast(link));
}

function seatLabel(p) {
  const s = V.seats[p];
  if (!s) return '';
  if (s.bot) return `Bot · ${s.bot[0].toUpperCase() + s.bot.slice(1)}`;
  return p === V.you ? 'You' : 'Opponent';
}

function prematchScreen() {
  screen = 'prematch';
  const you = V.you, opp = you === 'A' ? 'B' : 'A', me = V.seats[you];
  const side = (p, cls) => `<div class="pl ${cls}"><div class="hd"><b>${seatLabel(p)} · ${V.seats[p].deckName}</b><span>${tribes(V.lists[p])}</span></div><div>${rows(V.lists[p])}</div></div>`;
  const mp = (n, sub) => `<div class="mp"><div class="h"><b>Game ${n}</b><span>${MAP.name}${sub}</span></div>${miniMap(360, 86)}</div>`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Leave</a><h1>Match</h1><span class="r">Best of 3</span></div>
    <div class="maps">${mp(1, ` · ${MAP.winFood} food to win`)}${mp(2, '')}${mp(3, ' · only if needed')}</div>
    <div class="lists">${side(you, 'A')}
      <div class="vs"><div class="big">VS</div>${me.ready ? `<div class="t">Waiting for your opponent</div>` : `<button class="btn primary" id="ready">Ready</button>`}</div>
      ${side(opp, 'B')}</div>`;
  const b = document.getElementById('ready'); if (b) b.onclick = () => send({ t: 'ready' });
  wirePops(app);
}

// Viewer space: you are always 'A' on the left; the server's seats are mapped through these.
const opp = () => V.you === 'A' ? 'B' : 'A';
const rel = p => p === V.you ? 'A' : 'B';
const dcr = cr => { if (V.you === 'A') return cr; const [c, r] = cr.split(','); return `${MAP.cols + 1 - Number(c)},${r}`; };

// What the seat can do right now, in viewer space.
function decision() {
  const G = V.game, d = { mine: V.phase === 'playing' && G.toAct === V.you, rings: [], hqRing: false, crChoice: {}, handPick: new Set(), cardOpts: [], otherOpts: [], places: {}, pend: null };
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
      <div class="abs opphand" id="opphand"></div>
      <div class="abs menu" id="menubtn">☰<span class="livedot" id="livedot"></span>
        <div class="abs menudrop" id="menudrop"><a href="#" id="livelink">Live commentary (L)</a><a href="#" id="notelink">Add a note (N)</a><a href="#/">Leave match</a></div></div>
      <div class="abs hand" id="hand"></div>
      <div class="abs deck" id="deck"></div>
      <div class="abs tbtn" id="tbtn"></div>
      <div class="abs waiting" id="waiting"></div>
      <div class="abs prompt" id="choicebar"></div>
      <div class="abs opts" id="opts"></div>
      <div class="abs reveal" id="reveal"></div>
      <div class="panel mine" id="mine"></div><div class="panel theirs" id="theirs"></div>
      <div class="panel histp" id="histp"><h4>History<span class="removed" id="removed"></span></h4><div class="hist" id="hist"></div></div>
      <div class="endov" id="endov"></div></div></div>`;
    fitStage(); wireNotes(); wireTips(document.getElementById('scr'));
    const $ = id => document.getElementById(id);
    $('menubtn').onclick = e => { e.stopPropagation(); $('menudrop').classList.toggle('on'); };
    $('livelink').onclick = e => { e.preventDefault(); e.stopPropagation(); $('menudrop').classList.remove('on'); setLive(!live); };
    $('notelink').onclick = e => { e.preventDefault(); e.stopPropagation(); $('menudrop').classList.remove('on'); openNote(); };
    // The series opens the history, the opponent's hand their decklist; hovering your deck shows yours.
    const toggle = k => e => { e.stopPropagation(); ui.panel = ui.panel === k ? null : k; showPanel(); };
    $('series').onclick = toggle('hist'); $('opphand').onclick = toggle('theirs');
    $('deck').onmouseenter = () => { ui.panel = 'mine'; showPanel(); };
    $('deck').onmouseleave = () => { if (ui.panel === 'mine') { ui.panel = null; showPanel(); } };
    app.querySelectorAll('.panel').forEach(el => el.onclick = e => e.stopPropagation());
    $('scr').addEventListener('click', () => { $('menudrop').classList.remove('on'); if (ui.panel) { ui.panel = null; showPanel(); } });
    $('deck').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.legal.draw) act({ kind: 'draw' }); };
    $('tbtn').onclick = e => { e.stopPropagation(); const d = lastDecision; if (d && d.mine && !d.pend && V.game.canPass) act({ kind: 'pass' }); };
    wireBoard();
  }
  drawGame();
}

function drawGame() {
  const G = V.game, you = V.you, them = opp(), d = decision(), $ = id => document.getElementById(id);
  const playing = V.phase === 'playing', choosing = !!(d.pend && d.pend.mode === 'choice');
  lastDecision = d;

  const gameNo = playing ? V.results.length + 1 : V.results.length;
  const dots = [0, 1, 2].map(i => { const r = V.results[i]; return `<i class="${r ? (r.winner ? rel(r.winner) : '') : i === gameNo - 1 ? 'now' : ''}"></i>`; }).join('');
  $('series').innerHTML = V.gauntlet ? `Game ${gameNo} of ${V.gauntlet.total}` : `Game ${gameNo} of 3 ${dots}`;
  drawHistory(G); drawLists(G); showPanel();

  // The opponent's hand: one card back each, centred across the board from yours.
  const nb = G.handCount[them], step = 52, bx0 = STAGE.w / 2 - (84 + (nb - 1) * step) / 2;
  const A = ui.anim, oppDrew = A ? Math.max(0, nb - A.oppHand) : 0;   // their new cards slide down into their hand
  $('opphand').innerHTML = Array.from({ length: nb }, (_, i) => `<div class="abs back${i >= nb - oppDrew ? ' drawn' : ''}" style="left:${bx0 + i * step}px;animation-delay:${(i - (nb - oppDrew)) * 0.12}s"></div>`).join('');

  // Your hand, centred under the board.
  const n = G.hand.length, cw = 143, gap = n > 1 ? Math.min(14, (940 - n * cw) / (n - 1)) : 0, x0 = STAGE.w / 2 - (n * cw + (n - 1) * gap) / 2;
  const hand = $('hand');
  let drawnK = 0;
  hand.innerHTML = G.hand.map((h, i) => {
    const c = CARDS[h.id], can = d.mine && !d.handPick.size && !choosing && d.places[h.id], pick = d.handPick.has(h.iid);
    const cls = [c.rarity, can ? 'can' : '', pick ? 'pick' : '', h.id === ui.sel ? 'sel' : '', !can && !pick ? 'dim' : ''].join(' ');
    // a card just drawn slides in from the deck (bottom right), the second a beat after the first
    const drawn = A && !A.hand.includes(h.iid) ? ++drawnK : 0, from = drawn ? `--fx:${1299 - (x0 + i * (cw + gap) + cw / 2)}px;animation-delay:${(drawn - 1) * 0.14}s;` : '';
    return `<div class="hc ${cls}${drawn ? ' drawn' : ''}" data-iid="${h.iid}" data-id="${h.id}" style="left:${x0 + i * (cw + gap)}px;z-index:${i + 1};${from}">${cardHTML(c, { str: h.str })}</div>`;
  }).join('');
  hand.querySelectorAll('.hc').forEach(el => el.onclick = e => {
    e.stopPropagation();
    const iid = Number(el.dataset.iid), id = el.dataset.id;
    if (d.handPick.has(iid)) return act({ kind: 'choice', choice: iid });
    if (!d.mine || !d.places[id]) return;
    ui.sel = ui.sel === id ? null : id; ui.hover = null; drawGame();
  });

  // The deck is Draw 2; the End turn button is also the turn indicator.
  const canDraw = d.mine && !d.pend && G.legal.draw;
  $('deck').className = 'abs deck num' + (canDraw ? ' can' : ''); $('deck').innerHTML = canDraw ? 'Draw 2' : '';
  const tb = $('tbtn');
  if (playing && G.current === you) {
    const pips = Array.from({ length: G.actionsTotal }, (_, i) => `<i class="${i < G.actionsTotal - G.actionsLeft ? 'used' : ''}"></i>`).join('');
    tb.className = 'abs tbtn A num' + (d.mine && !d.pend && G.canPass ? ' can' : ''); tb.innerHTML = `<b>End turn</b><span class="pips">${pips}</span>`;
  } else if (playing) { tb.className = 'abs tbtn B num'; tb.innerHTML = 'Their turn'; }
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
      opts.classList.add('on');
      opts.querySelectorAll('[data-o]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.cardOpts[el.dataset.o].v }); });
    }
    bar.querySelectorAll('[data-x]').forEach(el => el.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: d.otherOpts[el.dataset.x].v }); });
    const sk = $('skip'); if (sk) sk.onclick = e => { e.stopPropagation(); act({ kind: 'choice', choice: SKIP }); };
  } else {
    bar.classList.remove('on');
    if (playing && G.opponentChoosing) waiting.textContent = G.history.length ? 'Opponent is choosing' : 'Opponent is mulliganing';
  }
  clearTimeout(drawGame.think);
  if (playing && G.toAct === them && V.seats[them].bot) {
    const ver = V.version;
    drawGame.think = setTimeout(() => { if (V && V.version === ver && screen === 'game') waiting.textContent = 'Bot is thinking'; }, 2500);
  }
  // The opponent's card, shown large at the centre as it is played, then flown down onto its crossroad (the piece lands as it arrives).
  if (A) A.fx = G.history.slice(A.hist).flatMap(m => m.fx).map(f => f.owner ? { ...f, owner: rel(f.owner) } : f);
  const last = G.history[G.history.length - 1];
  if (A && G.history.length > A.hist && last && last.seat === them && last.kind === 'place' && last.target[0] === 'cr') {
    const [tx, ty] = crossroadAt(dcr(last.target[1])), rv = $('reveal');
    rv.innerHTML = cardHTML(CARDS[last.card]); rv.style.setProperty('--tx', `${tx - STAGE.w / 2}px`); rv.style.setProperty('--ty', `${ty - 300}px`);
    rv.classList.remove('on'); void rv.offsetWidth; rv.classList.add('on');
    if (ui.anim) ui.anim.landDelay = 0.95;
  }
  drawBoard(d);
  drawEnd();
}

// The history strip and both decklists, shared by both game screens.
function drawHistory(G) {
  const hist = document.getElementById('hist');
  let hs = '', lastT = null;
  G.history.forEach((m, i) => {
    if (m.round !== lastT) { hs += `<div class="t">T${m.round}</div>`; lastT = m.round; }
    const c = COL[rel(m.seat)];
    if (m.kind === 'draw') { const dr = m.fx.find(f => f.k === 'draw' && f.seat === m.seat); hs += `<div class="hi draw" style="--c:${c}" data-h="${i}">+${dr ? dr.n : 0}</div>`; }
    else { const k = m.fx.filter(f => f.k === 'remove').length;
      hs += `<div class="hi gradart" style="--c:${c};${hasArt(m.card) ? `background-image:url(${artUrl(m.card)})` : ''}" data-h="${i}"><span class="s">${CARDS[m.card].str}</span>${k ? `<span class="k">×${k}</span>` : ''}</div>`; }
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
  theirs.innerHTML = `<h4>Their cards<span class="n">${sum(G.unseen)} left</span></h4><div class="rows">${rows(V.lists[them], G.unseen)}</div>`;
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
  const who = m.seat === V.you ? 'You' : 'They', name = id => CARDS[id] ? CARDS[id].name : id;
  const fx = m.fx.map(f => {
    if (f.k === 'cover') return `covered ${name(f.card)}`;
    if (f.k === 'remove') return `removed ${name(f.card)}`;
    if (f.k === 'bounce') return `returned ${name(f.card)}`;
    if (f.k === 'draw') return m.kind === 'draw' && f.seat === m.seat ? null : `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'they '}drew ${f.n}`;
    if (f.k === 'food') return `${f.seat === m.seat ? '' : f.seat === V.you ? 'you ' : 'they '}${f.n > 0 ? 'gained' : 'paid'} ${Math.abs(f.n)} food`;
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
  renderBoard(document.getElementById('board'), viewerMap(), g, CARDS, { rings: d.rings, hqRing: d.hqRing, preview, anim: A, current: V.phase === 'playing' ? rel(V.game.current) : null });
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
    return `<div class="sc ${u.owner}">${cardHTML(c, { str: top ? u.str : c.str, attrs: `style="--w:${w}px"` })}` +
      (u.timer ? `<div class="tm">Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}</div>` : '') + `</div>`; };
  const top = st[st.length - 1], buried = st.slice(0, -1).reverse();
  stackpop.innerHTML = `<div class="stk">${card(top, 190, true)}</div>` +
    buried.map((u, i) => `<div class="stk">${card(u, 150)}</div>`).join('');
  stackpop.style.display = 'flex';
  const r = g.getBoundingClientRect(), w = stackpop.offsetWidth, h = stackpop.offsetHeight;
  stackpop.style.left = (r.right + 8 + w > innerWidth ? r.left - 8 - w : r.right + 8) + 'px';
  stackpop.style.top = Math.max(56, Math.min(r.top - 80, innerHeight - h - 10)) + 'px';
}

function drawEnd() {
  const ov = document.getElementById('endov'), G = V.game;
  if (V.phase === 'playing' || !G.result) { ov.classList.remove('on'); return; }
  if (ui.peek) { ov.classList.remove('on'); document.getElementById('waiting').innerHTML = `<span class="peek" id="unpeek" style="cursor:pointer;text-decoration:underline">Back to results</span>`; document.getElementById('unpeek').onclick = () => { ui.peek = false; drawGame(); }; return; }
  const you = V.you, them = opp(), w = G.result.winner, S = V.score;
  const res = w === null ? ['D', 'Draw'] : w === you ? ['A', 'Victory'] : ['B', 'Defeat'];
  const how = { hq_capture: w === you ? 'Enemy HQ captured' : 'Your HQ was captured', food: `${w === you ? 'You' : 'They'} reached ${G.winFood} food`, exhaustion: 'Exhaustion · more food wins', max_turns: 'Turn limit · more food wins' }[G.result.reason] || G.result.reason;
  const dots = [0, 1, 2].map(i => { const r = V.results[i]; return `<i class="${r && r.winner ? rel(r.winner) : ''}"></i>`; }).join('');
  const score = `<div class="score"><span class="A">${S[you]}</span><span class="g">${dots}</span><span class="B">${S[them]}</span></div>`;
  const peek = `<span class="peek" id="peek">See the board</span>`;
  if (V.gauntlet) {
    const g = V.gauntlet, tot = g.record.reduce((a, r) => [a[0] + r.w, a[1] + r.l], [0, 0]);
    const rows = g.record.map(r => `<div>${r.deckName} <b>${r.w}–${r.l}</b></div>`).join('');
    const done = V.phase === 'match_over';
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${done ? 'Gauntlet done' : res[1]}</div><div class="how">${how} · turn ${G.round}</div>
      <div class="how">Game ${g.played} of ${g.total} · overall <b>${tot[0]}–${tot[1]}</b></div><div class="how">${rows}</div>
      ${done ? '' : `<div class="next">Next: vs ${g.next.deckName} · ${g.next.first === you ? 'you go first' : 'they go first'}</div>`}
      <div class="btns">${done ? '<a class="btn primary" href="#/">Menu</a>' : '<button class="btn primary" id="nextg">Next game</button>'}</div>${peek}</div>`;
    if (!done) document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else if (V.phase === 'game_over') {
    const firstNext = w === null ? G.first : (w === you ? them : you);
    ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div><div class="how">${how} · turn ${G.round}</div>${score}
      <div class="next">Game ${V.results.length + 1} · ${MAP.name} · ${firstNext === you ? 'you go first' : 'they go first'}</div>
      <div class="btns"><button class="btn primary" id="nextg">Next game</button></div>${peek}</div>`;
    document.getElementById('nextg').onclick = () => send({ t: 'next' });
  } else {
    const won = S[you] > S[them];
    ov.innerHTML = `<div class="endbox"><div class="res ${won ? 'A' : 'B'}">${won ? 'Match won' : 'Match lost'}</div><div class="how">${res[1]} in game ${V.results.length} · ${how}</div>${score}
      <div class="next">${V.seats[you].deckName} vs ${V.seats[them].deckName}</div>
      <div class="btns"><button class="btn primary" id="rematch">Rematch</button><a class="btn" href="#/">Menu</a></div>${peek}</div>`;
    document.getElementById('rematch').onclick = () => send({ t: 'rematch' });
  }
  document.getElementById('peek').onclick = () => { ui.peek = true; drawGame(); };
  ov.classList.add('on');
}

// Playtest notes: N opens a box, Chrome's speech recognition fills it while you talk (or type),
// Enter saves it to the game log at this exact point, Esc discards.
let noteRec = null;
function wireNotes() {
  let box = document.getElementById('notebox');
  if (!box) {
    box = document.createElement('div'); box.id = 'notebox'; box.className = 'notebox';
    box.innerHTML = `<textarea id="notetext" placeholder="Say or type what you're thinking"></textarea>
      <div class="nb"><span class="rec off" id="noterec"></span><span id="notestate">Enter saves · Esc discards</span></div>`;
    document.body.appendChild(box);
  }
  const ta = document.getElementById('notetext');
  ta.onkeydown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); closeNote(true); }
    else if (e.key === 'Escape') { e.preventDefault(); closeNote(false); }
    e.stopPropagation();
  };
}
function openNote() {
  if (live) { toast('Live commentary is already recording'); return; }
  const box = document.getElementById('notebox'), ta = document.getElementById('notetext');
  if (!box || box.classList.contains('on')) return;
  ta.value = ''; box.classList.add('on'); ta.focus();
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const dot = document.getElementById('noterec'), state = document.getElementById('notestate');
  if (!SR) { state.textContent = 'No speech recognition in this browser: type · Enter saves · Esc discards'; return; }
  noteRec = new SR(); noteRec.continuous = true; noteRec.interimResults = true; noteRec.lang = 'en-US';
  let committed = '';
  noteRec.onresult = e => {
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) committed += e.results[i][0].transcript.trim() + ' ';
      else interim += e.results[i][0].transcript;
    }
    ta.value = (committed + interim).trim();
  };
  noteRec.onstart = () => { dot.classList.remove('off'); state.textContent = 'Listening · Enter saves · Esc discards'; };
  noteRec.onend = () => { dot.classList.add('off'); if (box.classList.contains('on')) state.textContent = 'Mic off: edit or type · Enter saves · Esc discards'; };
  noteRec.onerror = e => { state.textContent = `Mic: ${e.error} · type instead · Enter saves`; };
  try { noteRec.start(); } catch { /* already running */ }
}
function closeNote(save) {
  const box = document.getElementById('notebox'), ta = document.getElementById('notetext');
  if (noteRec) { noteRec.onend = null; try { noteRec.stop(); } catch { } noteRec = null; }
  document.getElementById('noterec').classList.add('off');
  if (save && ta.value.trim()) { send({ t: 'note', text: ta.value.trim() }); toast('Note saved', true); }
  box.classList.remove('on');
}
// Live commentary: the mic stays on for the whole game and every finished sentence is sent as a
// note the moment it's recognised, so the server pins it next to the moves being made.
let live = null;
function setLive(on) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (on && !SR) { toast('No speech recognition in this browser'); return; }
  if (live) { live.onend = null; try { live.stop(); } catch { } live = null; }
  if (on) {
    live = new SR(); live.continuous = true; live.interimResults = false; live.lang = 'en-US';
    live.onresult = e => { for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) {
      const text = e.results[i][0].transcript.trim(); if (text) send({ t: 'note', text }); } };
    live.onend = () => { if (live) try { live.start(); } catch { } };   // Chrome stops after a pause; keep going
    live.onerror = e => { if (e.error === 'not-allowed') { toast('Microphone blocked'); setLive(false); } };
    try { live.start(); } catch { }
  }
  const dot = document.getElementById('livedot'); if (dot) dot.style.display = on && live ? 'inline-block' : 'none';
  const link = document.getElementById('livelink'); if (link) link.textContent = live ? 'Stop live commentary (L)' : 'Live commentary (L)';
  if (on && live) toast('Live commentary on', true);
}
addEventListener('keydown', e => {
  if ((e.key === 'l' || e.key === 'L') && screen === 'game' && !e.metaKey && !e.ctrlKey && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault(); setLive(!live);
  }
});
addEventListener('keydown', e => {
  if ((e.key === 'n' || e.key === 'N') && screen === 'game' && !e.metaKey && !e.ctrlKey && document.activeElement.tagName !== 'TEXTAREA') {
    e.preventDefault(); openNote();
  }
});

window.__ak = () => ({ V, ui });   // test hook: the headless play-through reads the view
window.__ak.feed = v => { const prev = V; V = v; onView(prev); };   // test hook: play a recorded sequence of views through the client
boot();
