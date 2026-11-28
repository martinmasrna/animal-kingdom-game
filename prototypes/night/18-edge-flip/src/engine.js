// 18 Edge flip grid: a 4x4 grid; cards carry four edge numbers and cost mana by their strength. A
// placed card takes every orthogonally adjacent enemy card whose touching edge is strictly lower.
// Most cells when the grid is full (or both pass in a row) wins.

export const N = 4, CELLS = N * N, MAX_MANA = 6, TURN_LIMIT = 60;
// edges clockwise from the top: [top, right, bottom, left]
export const CARDS = {
  POI: { id: 'POI', name: 'Point', cost: 1, e: [3, 1, 1, 1] },
  PAI: { id: 'PAI', name: 'Pair', cost: 1, e: [2, 2, 1, 1] },
  EVE: { id: 'EVE', name: 'Even', cost: 2, e: [2, 2, 2, 2] },
  SPE: { id: 'SPE', name: 'Spear', cost: 2, e: [4, 1, 2, 1] },
  HOO: { id: 'HOO', name: 'Hook', cost: 3, e: [4, 3, 1, 1] },
  BLO: { id: 'BLO', name: 'Block', cost: 3, e: [3, 3, 3, 2] },
  LAN: { id: 'LAN', name: 'Lance', cost: 4, e: [5, 2, 3, 2] },
  CRO: { id: 'CRO', name: 'Crown', cost: 5, e: [4, 4, 4, 4] },
  COIN: { id: 'COIN', name: 'Coin', cost: 0, coin: true },
};
export const DECK = { POI: 3, PAI: 3, EVE: 3, SPE: 3, HOO: 2, BLO: 2, LAN: 2, CRO: 2 };
export const deckList = () => { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; };
export const edgesOf = (id, rot) => { const e = CARDS[id].e, out = [0, 0, 0, 0]; for (let i = 0; i < 4; i++) out[(i + rot) % 4] = e[i]; return out; };
// the distinct rotations of a card (Even and Crown have one)
export const ROTS = {};
for (const id of Object.keys(CARDS)) { if (CARDS[id].coin) continue; const seen = new Set(); ROTS[id] = []; for (let r = 0; r < 4; r++) { const k = edgesOf(id, r).join(); if (!seen.has(k)) { seen.add(k); ROTS[id].push(r); } } }
// neighbours of each cell: [cell, my edge index, their edge index]
export const NB = [];
for (let c = 0; c < CELLS; c++) {
  const x = c % N, y = Math.floor(c / N), out = [];
  if (y > 0) out.push([c - N, 0, 2]);
  if (x < N - 1) out.push([c + 1, 1, 3]);
  if (y < N - 1) out.push([c + N, 2, 0]);
  if (x > 0) out.push([c - 1, 3, 1]);
  NB.push(out);
}

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList() }; }
export function clone(s) {
  return { ...s, grid: s.grid.map(g => g && { ...g }), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice() })) };
}
function emit(ev, e) { if (ev) ev.push(e); }
function draw(s, side) { const p = s.p[side]; if (p.deck.length) p.hand.push(p.deck.shift()); }

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, placed: false, passes: 0, winner: null, capped: false, grid: Array(CELLS).fill(null), p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 4; i++) draw(s, s.first);
  for (let i = 0; i < 5; i++) draw(s, 1 - s.first);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  startTurn(s, null);
  return s;
}
function startTurn(s, ev) {
  const P = s.p[s.turn];
  s.turnNo++; s.placed = false;
  P.maxMana = Math.min(MAX_MANA, P.maxMana + 1); P.mana = P.maxMana;
  draw(s, s.turn);
  emit(ev, { t: 'turn', side: s.turn });
}
export const count = (s, side) => s.grid.reduce((a, g) => a + (g && g.owner === side ? 1 : 0), 0);
export const full = (s) => s.grid.every(Boolean);
// the enemy cards a card would take from a cell
export function flipsAt(s, side, id, rot, cell) {
  const e = edgesOf(id, rot), out = [];
  for (const [nc, mi, ti] of NB[cell]) { const g = s.grid[nc]; if (g && g.owner !== side && e[mi] > g.e[ti]) out.push(nc); }
  return out;
}

// Actions: { t: 'place', card, cell, rot } | { t: 'coin' } | { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn], out = [];
  if (P.hand.includes('COIN')) out.push({ t: 'coin' });
  for (const id of new Set(P.hand)) {
    if (id === 'COIN' || CARDS[id].cost > P.mana) continue;
    for (let c = 0; c < CELLS; c++) if (!s.grid[c]) for (const rot of ROTS[id]) out.push({ t: 'place', card: id, cell: c, rot });
  }
  out.push({ t: 'end' });
  return out;
}
function endGame(s, ev) {
  const a = count(s, 0), b = count(s, 1);
  s.winner = a === b ? 'draw' : a > b ? 0 : 1;
  emit(ev, { t: 'end', winner: s.winner, cells: [a, b] });
}
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me];
  if (a.t === 'coin') {
    const i = P.hand.indexOf('COIN'); if (i < 0) throw new Error('no coin');
    P.hand.splice(i, 1); P.mana += 1; emit(ev, { t: 'coin', side: me }); return;
  }
  if (a.t === 'place') {
    const c = CARDS[a.card];
    if (!c || c.coin || !P.hand.includes(a.card) || c.cost > P.mana || s.grid[a.cell] !== null || !ROTS[a.card].includes(a.rot)) throw new Error('illegal ' + JSON.stringify(a));
    const fl = flipsAt(s, me, a.card, a.rot, a.cell);
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
    s.grid[a.cell] = { card: a.card, rot: a.rot, e: edgesOf(a.card, a.rot), owner: me };
    emit(ev, { t: 'place', side: me, card: a.card, cell: a.cell, rot: a.rot });
    for (const nc of fl) { s.grid[nc].owner = me; emit(ev, { t: 'flip', side: me, cell: nc }); }
    s.placed = true;
    if (full(s)) endGame(s, ev);
    return;
  }
  if (a.t === 'end') {
    s.passes = s.placed ? 0 : s.passes + 1;
    emit(ev, { t: 'endturn', side: me, pass: !s.placed });
    if (s.passes >= 2) { endGame(s, ev); return; }
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(ev, { t: 'end', winner: 'draw' }); return; }
    s.turn = 1 - s.turn;
    startTurn(s, ev);
    return;
  }
  throw new Error('unknown action');
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
export const actionKey = (a) => a.t === 'place' ? `${a.card}@${a.cell}r${a.rot}` : a.t;
