// Breaking sites. Three shared sites lie face-up, each with a threshold and two prizes. Both
// players put units (power, mana cost) onto their side of any site; the moment the total power on
// a site, both sides together, reaches its threshold, it breaks: more power takes the Winner
// points, the other side the Runner-up points if it has a unit there (a tie gives both the
// Runner-up points); its units are discarded and the next site replaces it. First to 15 wins.
// Pure from the outside: act() clones the state; _act() mutates (for the bots' play-outs).

export const TARGET = 15, MAX_MANA = 10, PER_SITE = 4, SLOTS = 3, TURN_LIMIT = 100;

export const CARDS = {
  PAWN: { id: 'PAWN', name: 'Pawn', kind: 'Unit', cost: 1, power: 1 },
  SQUAD: { id: 'SQUAD', name: 'Squad', kind: 'Unit', cost: 2, power: 3 },
  FORCE: { id: 'FORCE', name: 'Force', kind: 'Unit', cost: 3, power: 4 },
  HEAVY: { id: 'HEAVY', name: 'Heavy', kind: 'Unit', cost: 4, power: 6 },
  BIG: { id: 'BIG', name: 'Big', kind: 'Unit', cost: 5, power: 7 },
  MOVE: { id: 'MOVE', name: 'Move', kind: 'Move', cost: 1 },
  STRIKE: { id: 'STRIKE', name: 'Strike', kind: 'Strike', cost: 2, max: 3 },
  BOOST: { id: 'BOOST', name: 'Boost', kind: 'Boost', cost: 2, plus: 3 },
  DRAW2: { id: 'DRAW2', name: 'Draw 2', kind: 'Draw', cost: 2, n: 2 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0 },
};
export const DECK = { PAWN: 5, SQUAD: 5, FORCE: 3, HEAVY: 3, BIG: 3, MOVE: 3, STRIKE: 3, BOOST: 3, DRAW2: 2 };
export const SITES = [[8, 3, 1], [9, 3, 1], [10, 4, 1], [10, 4, 2], [11, 4, 2], [12, 5, 2], [12, 5, 2], [13, 5, 3], [14, 6, 3], [15, 6, 3]].map(([thr, win, run]) => ({ thr, win, run }));

const list = (o) => { const out = []; for (const [id, k] of Object.entries(o)) for (let i = 0; i < k; i++) out.push(id); return out; };
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { points: 0, mana: 0, maxMana: 0, fatigue: 0, hand: [], deck: list(DECK), gone: 0 }; }
export function clone(s) {
  return { ...s, sdeck: s.sdeck.slice(), sites: s.sites.map(x => x && { ...x, u: [x.u[0].map(m => ({ ...m })), x.u[1].map(m => ({ ...m }))] }), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  s.p[1 - side].points += 1; emit(s, ev, { t: 'fatigue', side, to: 1 - side });
}
const newSite = (s) => s.sdeck.length ? { ...s.sdeck.shift(), uid: UID++, u: [[], []] } : null;

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, capped: false, sdeck: SITES.map(x => ({ ...x })), sites: [], p: [newPlayer(), newPlayer()] };
  shuffleInPlace(s, s.sdeck);
  for (const p of s.p) shuffleInPlace(s, p.deck);
  for (let i = 0; i < SLOTS; i++) s.sites.push(newSite(s));
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

export const power = (site, side) => site.u[side].reduce((a, m) => a + m.power, 0);
export const total = (site) => power(site, 0) + power(site, 1);

function checkEnd(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].points >= TARGET, b = s.p[1].points >= TARGET;
  if (a || b) {
    s.winner = a && b ? (s.p[0].points === s.p[1].points ? 'draw' : s.p[0].points > s.p[1].points ? 0 : 1) : a ? 0 : 1;
    emit(s, ev, { t: 'end', winner: s.winner }); return true;
  }
  if (!s.sdeck.length && s.sites.every(x => !x)) {
    const x = s.p[0].points, y = s.p[1].points;
    s.winner = x === y ? 'draw' : x > y ? 0 : 1; emit(s, ev, { t: 'end', winner: s.winner, by: 'sites' }); return true;
  }
  return false;
}
// Every site whose total power has reached its threshold breaks, the mover's best first.
function breaks(s, ev) {
  for (;;) {
    if (s.winner !== null) return;
    let k = -1, best = -Infinity;
    s.sites.forEach((x, i) => { if (x && total(x) >= x.thr) { const g = gains(x); const v = g[s.turn] - g[1 - s.turn]; if (v > best) { best = v; k = i; } } });
    if (k < 0) return;
    const x = s.sites[k], g = gains(x);
    s.p[0].points += g[0]; s.p[1].points += g[1];
    s.p[0].gone += x.u[0].length; s.p[1].gone += x.u[1].length;
    emit(s, ev, { t: 'break', slot: k, uid: x.uid, gains: g, pw: [power(x, 0), power(x, 1)], points: [s.p[0].points, s.p[1].points] });
    s.sites[k] = newSite(s);
    if (s.sites[k]) emit(s, ev, { t: 'site', slot: k, uid: s.sites[k].uid });
    checkEnd(s, ev);
  }
}
// the points each side takes if this site breaks now
export function gains(x) {
  const a = power(x, 0), b = power(x, 1), g = [0, 0];
  if (a === b) { if (x.u[0].length) g[0] = x.run; if (x.u[1].length) g[1] = x.run; }
  else { const w = a > b ? 0 : 1; g[w] = x.win; if (x.u[1 - w].length) g[1 - w] = x.run; }
  return g;
}

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  draw(s, side, ev);
  checkEnd(s, ev);
}

// Actions: { t: 'unit', card, slot }  { t: 'move', from: [slot, i], slot }  { t: 'strike', slot, i }
//          { t: 'boost', slot, i }  { t: 'draw' }  { t: 'coin' }  { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], out = [], S = s.sites;
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') S.forEach((x, k) => { if (x && x.u[me].length < PER_SITE) out.push({ t: 'unit', card: id, slot: k }); });
    else if (c.kind === 'Coin') out.push({ t: 'coin' });
    else if (c.kind === 'Draw') out.push({ t: 'draw' });
    else if (c.kind === 'Strike') S.forEach((x, k) => { if (x) x.u[1 - me].forEach((m, i) => { if (m.power <= c.max) out.push({ t: 'strike', slot: k, i }); }); });
    else if (c.kind === 'Boost') S.forEach((x, k) => { if (x) x.u[me].forEach((m, i) => out.push({ t: 'boost', slot: k, i })); });
    else if (c.kind === 'Move') S.forEach((x, k) => { if (x) x.u[me].forEach((m, i) => S.forEach((y, j) => { if (y && j !== k && y.u[me].length < PER_SITE) out.push({ t: 'move', from: [k, i], slot: j }); })); });
  }
  out.push({ t: 'end' });
  return out;
}

function endTurn(s, ev) {
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  startTurn(s, ev);
}
function pay(P, id) {
  const c = CARDS[id];
  if (!P.hand.includes(id) || c.cost > P.mana) throw new Error('cannot pay ' + id);
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(id), 1);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], S = s.sites;
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'coin') { pay(P, 'COIN'); P.mana += 1; emit(s, ev, { t: 'coin', side: me }); return; }
  if (a.t === 'draw') { pay(P, 'DRAW2'); emit(s, ev, { t: 'play', side: me, card: 'DRAW2' }); for (let k = 0; k < CARDS.DRAW2.n; k++) draw(s, me, ev); checkEnd(s, ev); return; }
  if (a.t === 'unit') {
    const x = S[a.slot], c = CARDS[a.card];
    if (!x || c.kind !== 'Unit' || x.u[me].length >= PER_SITE) throw new Error('illegal unit');
    pay(P, a.card);
    const m = { uid: UID++, card: a.card, power: c.power };
    x.u[me].push(m);
    emit(s, ev, { t: 'play', side: me, card: a.card, slot: a.slot, uid: m.uid });
  } else if (a.t === 'strike') {
    const x = S[a.slot], m = x && x.u[1 - me][a.i];
    if (!m || m.power > CARDS.STRIKE.max) throw new Error('illegal strike');
    pay(P, 'STRIKE');
    x.u[1 - me].splice(a.i, 1); s.p[1 - me].gone++;
    emit(s, ev, { t: 'play', side: me, card: 'STRIKE', slot: a.slot, tuid: m.uid });
  } else if (a.t === 'boost') {
    const x = S[a.slot], m = x && x.u[me][a.i];
    if (!m) throw new Error('illegal boost');
    pay(P, 'BOOST');
    m.power += CARDS.BOOST.plus;
    emit(s, ev, { t: 'play', side: me, card: 'BOOST', slot: a.slot, tuid: m.uid });
  } else if (a.t === 'move') {
    const x = S[a.from[0]], y = S[a.slot], m = x && x.u[me][a.from[1]];
    if (!m || !y || a.from[0] === a.slot || y.u[me].length >= PER_SITE) throw new Error('illegal move');
    pay(P, 'MOVE');
    x.u[me].splice(a.from[1], 1); y.u[me].push(m);
    emit(s, ev, { t: 'play', side: me, card: 'MOVE', slot: a.slot, from: a.from[0], tuid: m.uid });
  } else throw new Error('unknown action ' + a.t);
  breaks(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

export function key(s) {
  return JSON.stringify([s.turn, s.winner, s.p.map(p => [p.points, p.mana]), s.sites.map(x => x ? [x.thr, x.win, x.run, x.u[0].map(m => m.power).sort(), x.u[1].map(m => m.power).sort()] : 0), s.p[s.turn].hand.slice().sort()]);
}
// What the mover cannot see dealt again: the opponent's hand and deck together (the Coin is public),
// the mover's deck, and the order of the site deck.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const coins = O.hand.filter(c => c === 'COIN'), hidden = O.hand.filter(c => c !== 'COIN');
  const pool = shuffle(hidden.concat(O.deck), rng);
  O.hand = pool.slice(0, hidden.length).concat(coins); O.deck = pool.slice(hidden.length);
  shuffle(P.deck, rng); shuffle(t.sdeck, rng);
  return t;
}
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
