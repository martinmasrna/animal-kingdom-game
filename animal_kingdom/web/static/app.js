// Animal Kingdom web client: menu flow (home -> play -> pre-match) and the game screen.
// The server holds the game; this file only renders the seat's view and sends choices back.
import { renderBoard } from './board.js';

const app = document.getElementById('app'), pop = document.getElementById('pop'), stackpop = document.getElementById('stackpop');
const ART = { lion: '/static/art/lion.jpg', king_theron: '/static/art/king_theron.jpg' };
const COVER = { cats_midrange: 'king_theron' };
const RANK = { legendary: 0, rare: 1, common: 2 };
const COL = { A: 'var(--you)', B: 'var(--them)' };
const SKIP = '__skip__';
const artStyle = id => ART[id] ? `style="background-image:url(${ART[id]})"` : '';
const sv = c => c.str === '*' ? -1 : c.str;
const store = (k, v) => { try { v === undefined ? null : localStorage.setItem(k, v); return localStorage.getItem(k); } catch { return null; } };
const tokenKey = id => 'ak:seat:' + id;
const getToken = id => { try { return sessionStorage.getItem(tokenKey(id)); } catch { return null; } };
const setToken = (id, t) => { try { sessionStorage.setItem(tokenKey(id), t); } catch { /* private mode: the tab just can't reconnect */ } };

let CARDS = {}, MAP, DECKS = [];
let V = null, ws = null, wsId = null, screen = null;
const ui = { sel: null, hover: null, peek: false, menu: false };

// ------------------------------------------------------------------ shared bits
function toast(msg) {
  const t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block';
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
  pop.innerHTML = `<div class="art gradart" ${artStyle(id)}></div><div class="s">${c.str}</div><div class="nm">${c.name}</div><div class="tx">${c.text || ''}</div><div class="tg">${c.tags.join(' · ')}</div>` + (extra ? `<div class="ev">${extra}</div>` : '');
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
  const list = counted(d.list), cv = COVER[d.id] ? `style="background-image:url(${ART[COVER[d.id]]})"` : '';
  return `<div class="dk${on ? ' on' : ''}" data-deck="${d.id}"><div class="cv gradart" ${cv}></div><div class="in"><b>${d.name}</b><span>Starter deck · ${d.list.length} cards</span><span>${tribes(list)}</span></div></div>`;
}

// ------------------------------------------------------------------ routing
async function boot() {
  const p = await fetch('/api/pool').then(r => r.json());
  CARDS = Object.fromEntries(p.cards.map(c => [c.id, c])); MAP = p.map; DECKS = p.decks;
  addEventListener('hashchange', route);
  addEventListener('resize', () => { if (screen === 'game') drawGame(); });
  addEventListener('keydown', e => { if (e.key === 'Escape' && ui.sel) { ui.sel = null; drawGame(); } });
  route();
}

function route() {
  pop.style.display = 'none'; stackpop.style.display = 'none';
  const parts = (location.hash.slice(1) || '/').split('/').filter(Boolean);
  const id = parts[1] && parts[1].toUpperCase();
  if (parts[0] !== 'm' || id !== wsId) disconnect();
  if (parts[0] === 'play') return playScreen();
  if (parts[0] === 'join' && id) return joinScreen(id);
  if (parts[0] === 'm' && id) return matchScreen(id);
  homeScreen();
}

function homeScreen() {
  screen = 'home';
  app.innerHTML = `<div class="home-bg"></div><div class="center"><div class="title">Animal<br>Kingdom</div>
    <div class="nav"><a class="play" href="#/play">Play</a></div></div>`;
}

// ------------------------------------------------------------------ play
const play = { opp: 'bot', level: 'normal', botDeck: 'random', code: '' };
function playScreen() {
  screen = 'play';
  const deck = store('ak:deck') || 'cats_midrange';
  const chip = (k, v, label) => `<span class="chip${play[k] === v ? ' on' : ''}" data-k="${k}" data-v="${v}">${label}</span>`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Menu</a><h1>Play</h1></div>
    <div class="body">
      <div class="opp"><div class="lbl">Opponent</div>
        <div class="opt${play.opp === 'friend' ? ' on' : ''}" data-opp="friend"><b>Friend</b><span>Invite someone with a link or a code</span></div>
        ${play.opp === 'friend' ? `<div class="sub"><div class="lbl">Join with a code</div><div class="row"><input class="codein" id="code" maxlength="6" value="${play.code}" placeholder="CODE"><span class="chip on" id="joinbtn">Join</span></div></div>` : ''}
        <div class="opt${play.opp === 'bot' ? ' on' : ''}" data-opp="bot"><b>Bot</b><span>Play against the computer</span></div>
        ${play.opp === 'bot' ? `<div class="sub"><div class="lbl">Level</div><div class="row">${chip('level', 'easy', 'Easy')}${chip('level', 'normal', 'Normal')}${chip('level', 'expert', 'Expert')}</div>
          <div class="lbl">Their deck</div><div class="row">${chip('botDeck', 'random', 'Random')}${DECKS.map(d => chip('botDeck', d.id, d.name)).join('')}</div></div>` : ''}
      </div>
      <div class="decks"><div class="lbl">Your deck</div><div class="grid">${DECKS.map(d => deckTile(d, d.id === deck)).join('')}</div></div>
    </div>
    <div class="bar"><span class="fmt">Best of 3 · one deck for the whole match · both decklists open</span><button class="btn primary" id="go">${play.opp === 'bot' ? 'Start match' : 'Create match'}</button></div>`;
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
    const body = { deck, name: 'You' };
    if (play.opp === 'bot') {
      const bd = play.botDeck === 'random' ? DECKS[Math.floor(Math.random() * DECKS.length)].id : play.botDeck;
      body.bot = { level: play.level, deck: bd };
    }
    const r = await fetch('/api/match', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
}
function joinCode() { if (play.code) location.hash = '#/join/' + play.code; }

function joinScreen(id) {
  screen = 'join';
  if (getToken(id)) { location.hash = '#/m/' + id; return; }
  const deck = store('ak:deck') || 'cats_midrange';
  app.innerHTML = `<div class="top"><a class="back" href="#/play">‹ Play</a><h1>Join match ${id}</h1></div>
    <div class="body"><div class="decks"><div class="lbl">Your deck</div><div class="grid">${DECKS.map(d => deckTile(d, d.id === deck)).join('')}</div></div></div>
    <div class="bar"><span class="fmt">Best of 3 · one deck for the whole match · both decklists open</span><button class="btn primary" id="go">Join</button></div>`;
  app.querySelectorAll('[data-deck]').forEach(el => el.onclick = () => { store('ak:deck', el.dataset.deck); joinScreen(id); });
  document.getElementById('go').onclick = async () => {
    const r = await fetch(`/api/match/${id}/join`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ deck, name: 'Friend' }) });
    if (!r.ok) return toast(r.status === 404 ? `No match ${id}` : await r.text());
    const m = await r.json(); setToken(m.id, m.token); location.hash = '#/m/' + m.id;
  };
}

// ------------------------------------------------------------------ match connection
function disconnect() { if (ws) { wsId = null; ws.onclose = null; ws.close(); ws = null; } V = null; }
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
  gameScreen();
}

function lobbyScreen() {
  screen = 'lobby';
  const link = `${location.origin}/#/join/${V.id}`;
  app.innerHTML = `<div class="top"><a class="back" href="#/">‹ Leave</a><h1>Match</h1><span class="r">Best of 3</span></div>
    <div class="lobby"><div class="lbl">Invite a friend</div><div class="code">${V.id}</div>
      <div class="link">${link}</div><span class="chip on" id="copy">Copy link</span>
      <div class="lbl" style="margin-top:24px">Waiting for them to join</div></div>`;
  document.getElementById('copy').onclick = () => navigator.clipboard.writeText(link).then(() => toast('Link copied'), () => toast(link));
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

// ------------------------------------------------------------------ game screen
function gameScreen() {
  if (screen !== 'game') {
    screen = 'game';
    app.innerHTML = `<div class="screen" id="scr">
      <div class="topbar"><div id="series"></div><div class="hist" id="hist"></div><div class="removed" id="removed"></div>
        <div class="menu" id="menubtn">☰<div class="menudrop" id="menudrop"><a href="#/">Leave match</a></div></div></div>
      <div id="stage"><div id="board"></div></div>
      <div class="col lc"><div class="ph" id="pa"></div><div class="dl A" id="mine"></div></div>
      <div class="col rc"><div class="ph" id="pb"></div><div class="dl B" id="theirs"></div></div>
      <div class="hand" id="hand"></div>
      <div class="deck" id="deck"></div>
      <div class="prompt" id="choicebar"></div>
      <div class="waiting" id="waiting"></div>
      <div class="endov" id="endov"></div></div>`;
    const menubtn = document.getElementById('menubtn');
    menubtn.onclick = e => { e.stopPropagation(); document.getElementById('menudrop').classList.toggle('on'); };
    const scr = document.getElementById('scr');
    scr.addEventListener('click', () => document.getElementById('menudrop').classList.remove('on'));
    scr.addEventListener('scroll', () => { scr.scrollTop = 0; scr.scrollLeft = 0; });   // hover lifts must never scroll the screen
    wireBoard();
  }
  drawGame();
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

function drawGame() {
  if (!V || !V.game) return;
  const G = V.game, you = V.you, them = opp(), d = decision();
  const scr = document.getElementById('scr');
  scr.classList.toggle('choosing', !!(d.pend && d.pend.mode === 'choice'));

  // Series + history + removed.
  const gameNo = V.phase === 'playing' ? V.results.length + 1 : V.results.length;
  const dots = [0, 1, 2].map(i => { const r = V.results[i]; return `<i class="${r ? (r.winner ? rel(r.winner) : '') : i === gameNo - 1 ? 'now' : ''}"></i>`; }).join('');
  document.getElementById('series').innerHTML = `<div class="series"><b>Game ${gameNo} of 3</b><span class="games">${dots}</span><span>${MAP.name}</span></div>`;
  const hist = document.getElementById('hist');
  let hs = '', lastT = null;
  G.history.forEach((m, i) => {
    if (m.round !== lastT) { hs += `<div class="t">T${m.round}</div>`; lastT = m.round; }
    const c = COL[rel(m.seat)];
    if (m.kind === 'draw') { const dr = m.fx.find(f => f.k === 'draw' && f.seat === m.seat); hs += `<div class="hi draw" style="--c:${c}" data-h="${i}">+${dr ? dr.n : 0}</div>`; }
    else { const k = m.fx.filter(f => f.k === 'remove').length;
      hs += `<div class="hi gradart" style="--c:${c};${ART[m.card] ? `background-image:url(${ART[m.card]})` : ''}" data-h="${i}"><span class="s">${CARDS[m.card].str}</span>${k ? `<span class="k">×${k}</span>` : ''}</div>`; }
  });
  hist.innerHTML = hs; hist.scrollLeft = hist.scrollWidth;
  hist.querySelectorAll('[data-h]').forEach(el => {
    const m = G.history[el.dataset.h];
    el.onmouseenter = () => { if (m.kind === 'place') cardPop(el, m.card, moveLine(m), 'below'); else { pop.className = 'pop'; pop.innerHTML = `<div class="ev">${moveLine(m)}</div>`; pop.style.minHeight = '0'; pop.style.display = 'flex'; const r = el.getBoundingClientRect(); pop.style.left = Math.min(r.left, innerWidth - 200) + 'px'; pop.style.top = (r.bottom + 8) + 'px'; } };
    el.onmouseleave = () => { pop.style.display = 'none'; pop.style.minHeight = ''; };
  });
  const removed = document.getElementById('removed');
  removed.innerHTML = `Removed <b>${G.removed.length}</b>`;

  // Player headers.
  const header = p => {
    const r = rel(p), turn = G.current === p && V.phase === 'playing';
    const pips = turn ? `<span class="pips">${Array.from({ length: G.actionsTotal }, (_, i) => `<span class="${i < G.actionsTotal - G.actionsLeft ? 'on' : ''}"></span>`).join('')}</span>` : '';
    const label = turn ? `<span class="tt ${r}">${p === you ? 'Your turn' : 'Their turn'} ${pips}</span>` : `<span class="who">${seatLabel(p)} · ${V.seats[p].deckName}</span>`;
    return `<div class="l1">${label}</div>`;
  };
  document.getElementById('pa').innerHTML = header(you);
  document.getElementById('pb').innerHTML = header(them);
  const sum = o => Object.values(o).reduce((a, b) => a + b, 0);
  const mine = document.getElementById('mine'), theirs = document.getElementById('theirs');
  mine.innerHTML = `<h4>Your deck<span class="n">${sum(G.deckLeft)} left</span></h4>${rows(V.lists[you], G.deckLeft)}`;
  theirs.innerHTML = `<h4>Their cards<span class="backs" title="Cards in their hand">${'<span></span>'.repeat(G.handCount[them])}</span><span class="n">${sum(G.unseen)} left</span></h4>${rows(V.lists[them], G.unseen)}`;
  wirePops(mine); wirePops(theirs);

  // Hand.
  const hand = document.getElementById('hand');
  hand.innerHTML = G.hand.map(h => {
    const c = CARDS[h.id], can = d.mine && !d.handPick.size && d.places[h.id], pick = d.handPick.has(h.iid);
    const base = sv(c), cls = [c.rarity, can ? 'can' : '', pick ? 'pick can' : '', h.id === ui.sel ? 'sel' : '', d.mine && !can && !pick ? 'dim' : ''].join(' ');
    const delta = base >= 0 && h.str !== base ? (h.str > base ? ' up' : ' down') : '';
    return `<div class="hc ${cls}" data-iid="${h.iid}" data-id="${h.id}"><div class="art gradart" ${artStyle(h.id)}></div><div class="s${delta}">${h.str}</div><div class="nm">${c.name}</div><div class="tx">${c.text}</div></div>`;
  }).join('');
  hand.querySelectorAll('.hc').forEach(el => el.onclick = e => {
    e.stopPropagation();
    const iid = Number(el.dataset.iid), id = el.dataset.id;
    if (d.handPick.has(iid)) return act({ kind: 'choice', choice: iid });
    if (!d.mine || !d.places[id]) return;
    ui.sel = ui.sel === id ? null : id; ui.hover = null; drawGame();
  });

  // Deck pile.
  const canDraw = d.mine && !d.pend && G.legal.draw;
  const deck = document.getElementById('deck');
  deck.innerHTML = `<div class="pilebtn ${canDraw ? 'can' : d.mine ? 'off' : ''}" id="drawbtn"><b>Draw 2</b><span>${G.deckCount[you]} in deck</span><span>hand ${G.hand.length} / ${G.handLimit}</span></div>`;
  document.getElementById('drawbtn').onclick = () => { if (canDraw) act({ kind: 'draw' }); };

  // Prompt for a pending choice: the card that asks and its rule, nothing more.
  const bar = document.getElementById('choicebar'), waiting = document.getElementById('waiting');
  waiting.textContent = '';
  if (d.pend) {
    const src = d.pend.source && CARDS[d.pend.source];
    const head = src ? `<div class="th gradart" ${artStyle(src.id)}><span>${src.str}</span></div><div><b>${src.name}</b><div class="q">${src.text}</div></div>` : `<div><b>Choose</b></div>`;
    const opts = d.cardOpts.length || d.otherOpts.length ? `<div class="opts">${d.cardOpts.map((o, i) => { const c = CARDS[o.id]; return `<div class="oc" data-o="${i}"><div class="art gradart" ${artStyle(o.id)}></div><div class="s">${c.str}</div><div class="nm">${c.name}</div><div class="tx">${c.text}</div></div>`; }).join('')}${d.otherOpts.map((o, i) => `<span class="skip" data-x="${i}">${o.label}</span>`).join('')}</div>` : '';
    bar.innerHTML = head + opts + (d.pend.optional ? `<span class="skip" id="skip">Skip</span>` : '');
    bar.classList.add('on');
    bar.querySelectorAll('[data-o]').forEach(el => el.onclick = () => act({ kind: 'choice', choice: d.cardOpts[el.dataset.o].v }));
    bar.querySelectorAll('[data-x]').forEach(el => el.onclick = () => act({ kind: 'choice', choice: d.otherOpts[el.dataset.x].v }));
    const sk = document.getElementById('skip'); if (sk) sk.onclick = () => act({ kind: 'choice', choice: SKIP });
  } else {
    bar.classList.remove('on');
    if (V.phase === 'playing' && G.opponentChoosing) waiting.textContent = 'Opponent is choosing';
  }
  // A bot can think for several seconds (Expert, under load): say so rather than look frozen.
  clearTimeout(drawGame.think);
  if (V.phase === 'playing' && G.toAct === them && V.seats[them].bot) {
    const ver = V.version;
    drawGame.think = setTimeout(() => { if (V && V.version === ver && screen === 'game') waiting.textContent = 'Bot is thinking'; }, 2500);
  }

  drawBoard(d);
  drawEnd();
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
  const stage = document.getElementById('stage'), g = viewerGame();
  let preview = null;
  if (ui.sel && ui.hover && d.rings.includes(ui.hover)) {
    const strs = V.game.hand.filter(h => h.id === ui.sel).map(h => h.str);
    preview = { cr: ui.hover, id: ui.sel, str: Math.max(...strs) };
  }
  const H = V.game.history, recent = [];
  for (let i = H.length - 1; i >= 0 && H[i].seat !== V.you; i--) if (H[i].target && H[i].target[0] === 'cr') recent.push(dcr(H[i].target[1]));
  renderBoard(document.getElementById('board'), viewerMap(), g, CARDS, { rings: d.rings, hqRing: d.hqRing, preview, recent }, { fitW: stage.clientWidth, fitH: stage.clientHeight });
}

function wireBoard() {
  const board = document.getElementById('board');
  board.addEventListener('click', e => {
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
    return `<div class="sc ${c.rarity}" style="--w:${w}px;--c:${COL[u.owner]}"><div class="own"></div><div class="art gradart" ${artStyle(u.id)}></div><div class="s">${top ? u.str : c.str}</div><div class="nm">${c.name}</div><div class="tx">${c.text || ''}</div>` +
      (u.timer ? `<div class="tm">Resolves in ${u.timer} turn${u.timer > 1 ? 's' : ''}</div>` : '') + `<div class="tg">${c.tags.join(' · ')}</div></div>`; };
  const top = st[st.length - 1], buried = st.slice(0, -1).reverse();
  stackpop.innerHTML = `<div class="stk"><div class="cap">On top</div>${card(top, 190, true)}</div>` +
    buried.map((u, i) => `<div class="stk"><div class="cap">${i === 0 ? 'Under it' : ''}</div>${card(u, 150)}</div>`).join('');
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
  if (V.phase === 'game_over') {
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

window.__ak = () => ({ V, ui });   // test hook: the headless play-through reads the view
boot();
