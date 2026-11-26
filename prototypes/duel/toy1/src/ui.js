// Toy 1 as a game screen. Drives the engine through its exported transitions;
// what the player sees comes from engine events, played back one beat at a time.
import { CARDS, DECK, MAX_MANA, REGEN, setVariant, strikeDmg, newMatch, playAction, endTurn, canPlay, deckSummary } from './engine.js';
import { makeRng, botTurn } from './bot.js';

const ME = 0, BOT = 1;
const ui = {
  s: null, view: null, busy: false, over: false, showDecks: false,
  shown: { hp: [0, 0], mana: [0, 0], block: [0, 0] }, hist: [], fresh: new Set(), popGuard: [0, 0], popSword: [0, 0],
  rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0,
};
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
setVariant('SW');
const NAME = { Strike: 'Strike', Guard: 'Guard', Sword: 'Sword', Whetstone: 'Whetstone', Training: 'Training' };
const label = (id) => CARDS[id].kind === 'Strike' || CARDS[id].kind === 'Guard' ? NAME[CARDS[id].kind] + ' ' + CARDS[id].n : NAME[CARDS[id].kind];

const ICON = {
  sword: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z" opacity=".95"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
};
const shieldSVG = '<svg viewBox="0 0 46 54"><path d="M23 2 43 9v15c0 13-9 22-20 28C12 46 3 37 3 24V9Z" fill="#5f7891" stroke="#fff" stroke-width="3"/></svg>';

// ------------------------------------------------------------------ cards
function cardHTML(id, { cls = '', attrs = '', owner = null } = {}) {
  const c = CARDS[id];
  if (c.kind === 'Sword') return `<button class="card k-Heavy ${cls}" ${attrs}>
    <span class="cgem">${c.cost}</span>
    <div class="art"><span class="big">+${c.n}</span>${ICON.sword}</div>
    <div class="nm">Sword</div>
    <div class="tx">Your strikes deal ${c.n} more. Dropped when you're hit.</div>
    <div class="sp"> </div></button>`;
  const strike = c.kind === 'Strike';
  const dmg = strike && owner ? strikeDmg(owner, id) : c.n;
  return `<button class="card k-${strike ? 'Light' : 'Defence'} ${cls}" ${attrs}>
    <span class="cgem">${c.cost}</span>
    <div class="art"><span class="big${dmg > c.n ? ' up' : ''}">${dmg}</span>${strike ? ICON.sword : ICON.shield}</div>
    <div class="nm">${NAME[c.kind]}</div>
    <div class="tx">${strike ? `Deal ${dmg} damage.` : `Absorb ${c.n} damage until your next turn.`}</div>
    <div class="sp"> </div></button>`;
}

// ------------------------------------------------------------------ rendering
function heroHTML(side) {
  const s = ui.view, p = s.p[side], mine = side === ME;
  const hp = ui.shown.hp[side], mana = ui.shown.mana[side], block = ui.shown.block[side];
  const active = !ui.over && s.turn === side;
  const shield = block > 0 ? `<div class="shield${ui.popGuard[side] ? ' pop' : ''}" id="shield${side}">${shieldSVG}<span style="font-size:18px">${block}</span></div>` : '';
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < mana ? ' on' : ''}"></i>`;
  const sword = p.sword ? `<div class="swordb${ui.popSword[side] ? ' pop' : ''}" id="sword${side}">${ICON.sword}<span>+${p.sword}</span></div>` : '';
  return `<div class="left"><div class="guards">${sword}${shield}</div></div>
    <div class="mid"><div class="plate${active ? ' active' : ''}" id="plate${side}">
      <div class="hname">${mine ? 'You' : 'Opponent'}</div>
      <div class="hp${hp <= 8 ? ' low' : ''}">${hp}</div>
    </div></div>
    <div class="right">
      <div class="mana" id="mana${side}">${gems}<span class="manatxt">${mana}<small> energy, +${REGEN} a turn</small></span></div>
      <div class="counts">Deck ${p.deck.length}${mine ? '' : ' · Hand ' + p.hand.length}</div>
    </div>`;
}

function handHTML() {
  const s = ui.view, p = s.p[ME];
  const order = p.hand.map((n, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]];
    const R = { Sword: 0, Strike: 1, Guard: 2 };
    return (R[A.kind] - R[B.kind]) || A.cost - B.cost;
  });
  const myTurn = !ui.busy && !ui.over && s.turn === ME;
  return order.map(i => {
    const id = p.hand[i];
    const ok = myTurn && canPlay(s, id);
    let cls = ok ? 'ok' : (myTurn ? 'no' : '');
    if (ui.fresh.has(i)) cls += ' drawn';
    return cardHTML(id, { cls, owner: p, attrs: `data-play="${id}"${ok ? '' : ' disabled'}` });
  }).join('');
}

function render() {
  document.body.classList.add('playing');
  const s = ui.view;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('hero1').innerHTML = heroHTML(BOT);
  $('hero0').innerHTML = heroHTML(ME);
  $('hand').innerHTML = handHTML();
  const myTurn = !ui.over && s.turn === ME;
  const canAct = myTurn && !ui.busy && s.p[ME].hand.some(id => canPlay(s, id));
  $('turnbox').innerHTML = `<button id="endturn" class="${myTurn && !canAct ? 'done' : ''}"${myTurn && !ui.busy ? '' : ' disabled'}>${myTurn ? 'End turn' : 'His turn'}</button>`;
  $('history').innerHTML = ui.hist.slice(-16).map(h => h.sep
    ? `<div class="hist sep">${h.sep}</div>`
    : `<div class="hist s${h.side}" data-card="${h.card}"><span class="hn">${label(h.card)}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  $('trk1').innerHTML = trackerHTML(BOT);
  $('trk0').innerHTML = trackerHTML(ME);
  $('decks').classList.toggle('show', ui.showDecks);
  if (ui.showDecks) $('decks').innerHTML = `<button class="x" id="closedecks">Close</button><div class="wrap">${deckTable(BOT)}${deckTable(ME)}</div>`;
  ui.fresh.clear(); ui.popGuard = [0, 0]; ui.popSword = [0, 0];
}

// Deck tracker: every card of the list with how many are still to come.
// Yours: still in your deck. His: not yet played (in his hand or his deck).
function trackerHTML(side) {
  const s = ui.view, mine = side === ME, p = s.p[side];
  const rows = deckSummary(s, side).map(r => {
    const c = CARDS[r.id], left = mine ? r.inDeck : r.unseen;
    return `<div class="trow ${c.kind}${left ? '' : ' gone'}"><span class="tg">${c.cost}</span><span class="tn">${label(r.id)}</span><span class="tc">×${left}</span></div>`;
  }).join('');
  const total = mine ? p.deck.length : p.deck.length + p.hand.length;
  return `<h3>${mine ? 'Your deck' : 'His deck'}<small>${total} ${mine ? 'left' : 'unplayed'}</small></h3>${rows}`;
}

function deckTable(side) {
  const s = ui.s, mine = side === ME;
  const rows = deckSummary(s, side).map(r => {
    const c = CARDS[r.id], left = mine ? r.inDeck : r.unseen;
    return `<tr><td>${label(r.id)}</td><td>${c.cost}</td><td>${r.total}</td><td class="${r.played ? '' : 'z'}">${r.played}</td><td class="${left ? '' : 'z'}"><b>${left}</b></td></tr>`;
  }).join('');
  return `<div><h3>${mine ? 'Your deck' : 'His deck'}</h3><p>Both decks are the same list.</p>
    <table><thead><tr><th>Card</th><th>Cost</th><th>In list</th><th>Played</th><th>${mine ? 'In deck' : 'Not seen'}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

// ------------------------------------------------------------------ playback
function centerOf(el) {
  const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 };
}
function floater(side, text, cls, where = 'plate', dy = 0) {
  const el = $(where + side) || $('plate' + side); if (!el) return;
  const c = centerOf(el);
  const f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text;
  f.style.left = c.x + 'px'; f.style.top = (c.y + dy) + 'px';
  $('game').appendChild(f);
  setTimeout(() => f.remove(), 1200);
}
function shake(side) {
  const el = $('plate' + side); if (!el) return;
  el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake');
}
function banner(text) {
  const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show');
}
async function spotlight(card, side) {
  const t = centerOf($('table'));
  $('spot').style.left = t.x + 'px'; $('spot').style.top = t.y + 'px';
  $('spot').innerHTML = cardHTML(card, { cls: `from${side}`, owner: ui.view.p[side] });
  await wait(side === ME ? 380 : 800);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(200);
  $('spot').innerHTML = '';
}

function beats(ev) {
  const out = []; let cur = null;
  for (const e of ev) {
    if (e.t === 'play') { cur = { card: e.card, side: e.side, evs: [e] }; out.push(cur); }
    else { if (!cur) { cur = { evs: [] }; out.push(cur); } cur.evs.push(e); }
  }
  return out;
}

async function playBeats(ev, prev, next) {
  const bs = beats(ev);
  for (let k = 0; k < bs.length; k++) {
    const b = bs[k], last = k === bs.length - 1;
    for (const e of b.evs) if (e.t === 'turn') {
      ui.hist.push({ sep: e.side === ME ? 'Your turn' : 'His turn' });
      banner(e.side === ME ? 'Your turn' : 'His turn');
      await wait(e.side === ME ? 700 : 450);
    }
    if (b.card) await spotlight(b.card, b.side);
    let out = '', cls = '', dmgTo = [0, 0];
    for (const e of b.evs) {
      if (e.t === 'hit') { ui.shown.hp[1 - e.side] -= e.dmg; dmgTo[1 - e.side] += e.dmg; }
      else if (e.t === 'stop') ui.shown.block[e.side] = e.block;
      else if (e.t === 'guard') { ui.shown.block[e.side] = e.block; ui.popGuard[e.side] = 1; }
      else if (e.t === 'expire') ui.shown.block[e.side] = 0;
      else if (e.t === 'sword') ui.popSword[e.side] = 1;
      else if (e.t === 'play' || e.t === 'start') ui.shown.mana[e.side] = e.mana;
    }
    ui.view = last ? next : prev;
    for (const e of b.evs) if (e.t === 'start' && e.drew && e.side === ME) ui.fresh.add(ui.view.p[ME].hand.length - 1);
    render();
    for (const e of b.evs) {
      if (e.t === 'stop') { floater(e.side, 'Absorbed ' + e.n, 'block', 'plate', -24); out = 'absorbed'; cls = 'block'; }
      if (e.t === 'guard') { out = '+' + e.n + ' ⛨'; cls = 'block'; }
      if (e.t === 'sword') { out = '+2'; cls = 'gold'; }
      if (e.t === 'drop') floater(e.side, 'Sword dropped', 'warn', 'plate', 40);
    }
    for (const side of [0, 1]) if (dmgTo[side]) { floater(side, '−' + dmgTo[side], 'dmg'); shake(side); out = (out === 'absorbed' ? 'part, ' : '') + '−' + dmgTo[side]; cls = 'dmg'; }
    if (b.card) {
      ui.hist.push({ side: b.side, card: b.card, out, cls });
      for (const e of b.evs) if (e.t === 'drop') ui.hist.push({ side: e.side, card: 'SW', out: 'dropped', cls: 'warn' });
      render();
    }
    if (b.card) await wait(b.side === ME ? 300 : 550);
  }
}

function syncShown(s) {
  ui.shown.hp = [s.p[0].hp, s.p[1].hp];
  ui.shown.mana = [s.p[0].mana, s.p[1].mana];
  ui.shown.block = [s.p[0].block, s.p[1].block];
}

async function apply(fn) {
  const prev = ui.s, ev = [];
  const next = fn(prev, ev);
  ui.s = next;
  await playBeats(ev, prev, next);
  ui.view = next; syncShown(next);
  if (next.winner !== null) finish();
  render();
}

function finish() {
  ui.over = true;
  const w = ui.s.winner;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="row"><button id="rematch">Play again</button></div>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.showDecks = false;
  syncShown(ui.s);
  $('over').classList.remove('show');
  ui.busy = true; render();
  ui.hist.push({ sep: ui.s.first === ME ? 'Your turn' : 'His turn' });
  banner(ui.s.first === ME ? 'You go first' : 'He goes first');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok);
  else { ui.busy = false; render(); }
}

async function botMove(tok) {
  ui.busy = true; render();
  await wait(400);
  const cards = botTurn(ui.s, ui.rng);
  for (const id of cards) {
    if (tok !== ui.token || ui.over) return;
    await wait(250);
    await apply((s, ev) => playAction(s, id, ev));
  }
  if (tok !== ui.token || ui.over) return;
  await wait(300);
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token) return;
  ui.busy = false; render();
}

async function myPlay(id) {
  if (ui.busy || ui.over || ui.s.turn !== ME || !canPlay(ui.s, id)) return;
  ui.busy = true;
  await apply((s, ev) => playAction(s, id, ev));
  ui.busy = false; render();
}

async function myEndTurn() {
  if (ui.busy || ui.over || ui.s.turn !== ME) return;
  const tok = ui.token;
  ui.busy = true; render();
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

// ------------------------------------------------------------------ input
function peek(e) {
  const h = e.target.closest && e.target.closest('.hist[data-card]');
  const box = $('peek');
  if (!h || !CARDS[h.dataset.card]) { box.innerHTML = ''; return; }
  const g = $('game').getBoundingClientRect(), r = h.getBoundingClientRect();
  box.innerHTML = cardHTML(h.dataset.card);
  box.style.left = (r.right - g.left + 12) + 'px';
  box.style.top = Math.max(8, Math.min(r.top - g.top - 60, g.height - 250)) + 'px';
}
document.addEventListener('mouseover', peek);
document.addEventListener('mouseout', (e) => { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest('.hist')) $('peek').innerHTML = ''; });
document.addEventListener('click', (e) => {
  const t = e.target.closest('button');
  if (!t || t.disabled) return;
  if (t.dataset.play) { myPlay(t.dataset.play); return; }
  switch (t.id) {
    case 'rematch': case 'newmatch': startMatch(); return;
    case 'showdecks': ui.showDecks = !ui.showDecks; render(); return;
    case 'closedecks': ui.showDecks = false; render(); return;
    case 'endturn': myEndTurn(); return;
  }
});
startMatch();
