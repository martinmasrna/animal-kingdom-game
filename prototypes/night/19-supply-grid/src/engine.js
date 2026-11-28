// Supply grid. A 5x5 grid; each player's Base sits on its own edge. You place units only next to
// a piece that is connected to your Base through your own pieces; a piece that loses that
// connection is removed at once. Pieces strike orthogonal neighbours: the lower power is destroyed,
// equal powers destroy both. Destroy the enemy Base, or have more pieces after round 12.
// Pure from the outside: act() clones the state; _act() mutates (for the bots' play-outs).

export const N = 5, MAX_MANA = 8, ROUNDS = 12, BASE_POWER = 3;
export const BASE = [2, 22]; // A: row 1 column 3; B: row 5 column 3

export const CARDS = {
  POST: { id: 'POST', name: 'Post', kind: 'Unit', cost: 1, power: 1 },
  LINE: { id: 'LINE', name: 'Line', kind: 'Unit', cost: 2, power: 2 },
  SQUAD: { id: 'SQUAD', name: 'Squad', kind: 'Unit', cost: 3, power: 3 },
  HEAVY: { id: 'HEAVY', name: 'Heavy', kind: 'Unit', cost: 4, power: 4 },
  BIG: { id: 'BIG', name: 'Big', kind: 'Unit', cost: 6, power: 6 },
  WALL: { id: 'WALL', name: 'Wall', kind: 'Unit', cost: 2, power: 3, wall: true },
  CUT: { id: 'CUT', name: 'Cut', kind: 'Spell', cost: 2, max: 2 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0 },
};
export const DECK = { POST: 5, LINE: 5, SQUAD: 4, HEAVY: 3, BIG: 2, WALL: 3, CUT: 2 };

export const ADJ = [];
for (let i = 0; i < N * N; i++) {
  const r = Math.floor(i / N), c = i % N, a = [];
  if (r > 0) a.push(i - N); if (r < N - 1) a.push(i + N); if (c > 0) a.push(i - 1); if (c < N - 1) a.push(i + 1);
  ADJ.push(a);
}
export const dist = (i, j) => Math.abs(Math.floor(i / N) - Math.floor(j / N)) + Math.abs(i % N - j % N);

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList() }; }
export function clone(s) {
  return { ...s, cells: s.cells.map(x => x && { ...x }), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); }
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, capped: false, cells: Array(N * N).fill(null), p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (const side of [0, 1]) s.cells[BASE[side]] = { uid: UID++, side, card: 'BASE', power: BASE_POWER, base: true, struck: false };
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const x of s.cells) if (x && x.side === side) x.struck = false;
  draw(s, side, ev);
}

// Every piece of `side` connected to its Base through its own pieces.
export function supplied(s, side) {
  const out = new Set(), b = BASE[side], C = s.cells;
  if (!C[b] || C[b].side !== side || !C[b].base) return out;
  const st = [b]; out.add(b);
  while (st.length) { const i = st.pop(); for (const j of ADJ[i]) if (!out.has(j) && C[j] && C[j].side === side) { out.add(j); st.push(j); } }
  return out;
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const ok = supplied(s, side);
    for (let i = 0; i < N * N; i++) { const x = s.cells[i]; if (x && x.side === side && !ok.has(i)) { emit(s, ev, { t: 'cutoff', side, cell: i, uid: x.uid, card: x.card }); s.cells[i] = null; } }
  }
  const a = !(s.cells[BASE[0]] && s.cells[BASE[0]].base), b = !(s.cells[BASE[1]] && s.cells[BASE[1]].base);
  if (a || b) { s.winner = a && b ? 'draw' : a ? 1 : 0; emit(s, ev, { t: 'end', winner: s.winner }); }
}
export function count(s, side) { let n = 0; for (const x of s.cells) if (x && x.side === side) n++; return n; }
// Cells where `side` may place a unit: empty and next to one of its (always supplied) pieces.
export function frontier(s, side) {
  const out = [];
  for (let i = 0; i < N * N; i++) { if (s.cells[i]) continue; for (const j of ADJ[i]) { const x = s.cells[j]; if (x && x.side === side) { out.push(i); break; } } }
  return out;
}

// Actions: { t: 'place', card, cell }  { t: 'strike', from, to }  { t: 'cut', to }  { t: 'coin' }  { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], out = [], C = s.cells;
  let fr = null;
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Coin') out.push({ t: 'coin' });
    else if (c.kind === 'Unit') { fr = fr || frontier(s, me); for (const cell of fr) out.push({ t: 'place', card: id, cell }); }
    else for (let i = 0; i < N * N; i++) { const x = C[i]; if (x && x.side !== me && !x.base && x.power <= c.max) out.push({ t: 'cut', to: i }); }
  }
  for (let i = 0; i < N * N; i++) {
    const x = C[i];
    if (!x || x.side !== me || x.struck || x.wall) continue;
    for (const j of ADJ[i]) if (C[j] && C[j].side !== me) out.push({ t: 'strike', from: i, to: j });
  }
  out.push({ t: 'end' });
  return out;
}

function endTurn(s, ev) {
  if (s.turnNo >= 2 * ROUNDS) {
    const a = count(s, 0), b = count(s, 1);
    s.winner = a === b ? 'draw' : a > b ? 0 : 1;
    emit(s, ev, { t: 'end', winner: s.winner, by: 'count', counts: [a, b] });
    return;
  }
  s.turn = 1 - s.turn;
  startTurn(s, ev);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], C = s.cells;
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'coin') {
    if (!P.hand.includes('COIN')) throw new Error('no coin');
    P.hand.splice(P.hand.indexOf('COIN'), 1); P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); return;
  }
  if (a.t === 'place') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.kind !== 'Unit' || c.cost > P.mana) throw new Error('illegal place ' + a.card);
    if (C[a.cell] || !ADJ[a.cell].some(j => C[j] && C[j].side === me)) throw new Error('illegal cell ' + a.cell);
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
    const x = { uid: UID++, side: me, card: a.card, power: c.power, wall: !!c.wall, struck: false };
    C[a.cell] = x;
    emit(s, ev, { t: 'place', side: me, card: a.card, cell: a.cell, uid: x.uid, mana: P.mana });
    return;
  }
  if (a.t === 'cut') {
    const c = CARDS.CUT, x = C[a.to];
    if (!P.hand.includes('CUT') || c.cost > P.mana || !x || x.side === me || x.base || x.power > c.max) throw new Error('illegal cut');
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf('CUT'), 1);
    emit(s, ev, { t: 'cut', side: me, to: a.to, uid: x.uid, card: x.card, mana: P.mana });
    C[a.to] = null; emit(s, ev, { t: 'die', side: x.side, cell: a.to, uid: x.uid, card: x.card });
    sweep(s, ev); return;
  }
  if (a.t === 'strike') {
    const x = C[a.from], y = C[a.to];
    if (!x || x.side !== me || x.struck || x.wall || !y || y.side === me || !ADJ[a.from].includes(a.to)) throw new Error('illegal strike');
    x.struck = true;
    emit(s, ev, { t: 'strike', side: me, from: a.from, to: a.to, uid: x.uid, tuid: y.uid, p1: x.power, p2: y.power });
    if (x.power <= y.power) { C[a.from] = null; emit(s, ev, { t: 'die', side: x.side, cell: a.from, uid: x.uid, card: x.card }); }
    if (y.power <= x.power) { C[a.to] = null; emit(s, ev, { t: 'die', side: y.side, cell: a.to, uid: y.uid, card: y.card }); }
    sweep(s, ev); return;
  }
  throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

export function key(s) {
  return JSON.stringify([s.turn, s.winner, s.cells.map(x => x ? x.side + x.card + (x.struck ? '*' : '') : '.').join(','), s.p.map(p => p.mana), s.p[s.turn].hand.slice().sort()]);
}
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const coins = O.hand.filter(c => c === 'COIN'), hidden = O.hand.filter(c => c !== 'COIN');
  const pool = shuffle(hidden.concat(O.deck), rng);
  O.hand = pool.slice(0, hidden.length).concat(coins); O.deck = pool.slice(hidden.length);
  shuffle(P.deck, rng);
  return t;
}
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
