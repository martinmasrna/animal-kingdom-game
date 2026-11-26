// Hex: a shared hex board of 14 tiles in rows of 2, 3, 4, 3, 2. Hearthstone mana,
// one shared deck list of two kinds of card: Unit (placed on any empty tile, or onto one of
// your own units, which it replaces; its strength is its health) and Strike (deal N damage
// to an enemy unit). A region is any three mutually adjacent tiles; at the end of your turn
// you gain 1 food for each region whose three tiles all hold your units. First to GOAL wins.

export const ROW_LENGTHS = [2, 3, 4, 3, 2];
// each tile's place: row, and x in tile widths from the board's centre line
export const POS = [];
ROW_LENGTHS.forEach((n, r) => { for (let i = 0; i < n; i++) POS.push({ r, x: i - (n - 1) / 2 }); });
export const TILES = POS.length, MAX_MANA = 10, TURN_LIMIT = 80;
const adj = (a, b) => (POS[a].r === POS[b].r && Math.abs(POS[a].x - POS[b].x) === 1) || (Math.abs(POS[a].r - POS[b].r) === 1 && Math.abs(POS[a].x - POS[b].x) === 0.5);
export const REGIONS = [];
for (let a = 0; a < TILES; a++) for (let b = a + 1; b < TILES; b++) for (let c = b + 1; c < TILES; c++)
  if (adj(a, b) && adj(b, c) && adj(a, c)) REGIONS.push([a, b, c]);
// Connection (Martin, 2026-11-26): a unit goes on one of your two base tiles (your nearest row), or
// next to one of your units that links back to a base tile through your own units. Side 0 plays from
// the bottom row, side 1 from the top.
export const BASE = [[TILES - 2, TILES - 1], [0, 1]];
export const NEIGH = Array.from({ length: TILES }, (_, a) => [...Array(TILES).keys()].filter(b => b !== a && adj(a, b)));
export let CONNECT = true;
export function setConnect(v) { CONNECT = v; }
// the tiles holding this side's units that link back to its base through its own units
export function connected(s, side) {
  const seen = new Set(), q = BASE[side].filter(i => s.board[i] && s.board[i].side === side);
  for (const i of q) seen.add(i);
  while (q.length) { const a = q.pop(); for (const b of NEIGH[a]) if (!seen.has(b) && s.board[b] && s.board[b].side === side) { seen.add(b); q.push(b); } }
  return seen;
}
export function ownTile(s, side, tile) {
  if (!CONNECT || BASE[side].includes(tile)) return true;
  const c = connected(s, side);
  return NEIGH[tile].some(j => c.has(j));
}

export let GOAL = 20;
export let DRAW = 2; // cards drawn at the start of each turn
export function setDraw(n) { DRAW = n; }
export function setGoal(g) { GOAL = g; }
export let FULL_HAND = false;
export function setFullHand(v) { FULL_HAND = v; }
export let SECOND_FOOD = 0, SECOND_MANA = 0;
export function setSecond(food, mana) { SECOND_FOOD = food; SECOND_MANA = mana; }
export let SCORE_AT = 'end';
export function setScoreAt(w) { SCORE_AT = w; }
export let SKIP_FIRST_DRAW = true;
export function setSkipFirstDraw(v) { SKIP_FIRST_DRAW = v; }
export let SECOND_HAND = 3;
export function setSecondHand(n) { SECOND_HAND = n; }

export function heldRegions(s, side) {
  const out = [];
  REGIONS.forEach((rg, k) => { if (rg.every(i => s.board[i] && s.board[i].side === side)) out.push(k); });
  return out;
}
export function regionPower(s, rg) { const p = [0, 0]; for (const i of rg) { const u = s.board[i]; if (u) p[u.side]++; } return p; }

export const CARDS = {};
export let DECK = {};
// cfg: { unitHp(cost), strikeDmg(cost), units: {cost: copies}, strikes: {cost: copies} }
export function configure(cfg) {
  for (const k of Object.keys(CARDS)) delete CARDS[k];
  DECK = {};
  for (const [c, k] of Object.entries(cfg.units)) { const id = 'U' + c; CARDS[id] = { id, kind: 'Unit', cost: +c, n: cfg.unitHp(+c) }; DECK[id] = k; }
  for (const [c, k] of Object.entries(cfg.strikes)) { const id = 'S' + c; CARDS[id] = { id, kind: 'Strike', cost: +c, n: cfg.strikeDmg(+c) }; DECK[id] = k; }
}
export const DEFAULT = {
  unitHp: c => c, strikeDmg: c => c,
  units: { 1: 3, 2: 3, 3: 3, 4: 3, 5: 3 },
  strikes: { 1: 3, 2: 3, 3: 2, 4: 2 },
};
configure(DEFAULT);

export function deckList() {
  const out = [];
  for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id);
  return out;
}

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

function newPlayer() { return { food: 0, mana: 0, maxMana: 0, hand: [], deck: deckList(), played: [] }; }
export function clone(s) {
  return {
    ...s,
    board: s.board.map(u => u && { ...u }),
    p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice() })),
  };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function draw(s, side, n) {
  const p = s.p[side]; let d = 0;
  for (let i = 0; i < n && p.deck.length; i++) { p.hand.push(p.deck.shift()); d++; }
  return d;
}
export function unitsOf(s, side) { let n = 0; for (const u of s.board) if (u && u.side === side) n++; return n; }

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, board: Array(TILES).fill(null), p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  if (FULL_HAND) for (const p of [s.first, 1 - s.first]) draw(s, p, s.p[p].deck.length);
  else { draw(s, s.first, 3); draw(s, 1 - s.first, SECOND_HAND); }
  s.p[1 - s.first].food = SECOND_FOOD;
  s.p[1 - s.first].bonusMana = SECOND_MANA;
  s.turn = s.first;
  mStartTurn(s, null);
  return s;
}

function mStartTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  if (SCORE_AT === 'start' && score(s, ev)) return;
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  if (p.bonusMana) { p.mana += p.bonusMana; p.bonusMana = 0; }
  const drew = (SKIP_FIRST_DRAW === 'both' ? s.turnNo <= 2 : s.turnNo === 1 && SKIP_FIRST_DRAW) ? 0 : draw(s, side, DRAW);
  emit(s, ev, { t: 'start', side, mana: p.mana, drew });
}

// A move is { card, tile }: a Unit onto an empty tile, a Strike onto a tile holding an enemy unit.
export function canPlay(s, card, tile) {
  if (s.winner !== null || !CARDS[card]) return false;
  const p = s.p[s.turn], c = CARDS[card];
  if (!p.hand.includes(card) || c.cost > p.mana) return false;
  if (tile === undefined) return c.kind === 'Unit' || s.board.some(u => u && u.side !== s.turn);
  const u = s.board[tile];
  return c.kind === 'Unit' ? (u === null || u.side === s.turn) && ownTile(s, s.turn, tile) : !!u && u.side !== s.turn;
}
export function targets(s, card) {
  const out = [];
  for (let i = 0; i < TILES; i++) if (canPlay(s, card, i)) out.push(i);
  return out;
}

function mPlay(s, card, tile, ev) {
  if (!canPlay(s, card, tile)) throw new Error('play: illegal ' + card + '@' + tile);
  const side = s.turn, p = s.p[side], c = CARDS[card];
  p.mana -= c.cost;
  p.hand.splice(p.hand.indexOf(card), 1);
  p.played.push(card);
  emit(s, ev, { t: 'play', side, card, tile, mana: p.mana });
  if (c.kind === 'Unit') {
    const old = s.board[tile];
    if (old) emit(s, ev, { t: 'replace', side, tile, card: old.card });
    s.board[tile] = { side, card, hp: c.n, max: c.n };
    emit(s, ev, { t: 'place', side, tile });
  } else {
    const u = s.board[tile];
    const dmg = Math.min(u.hp, c.n);
    u.hp -= c.n;
    emit(s, ev, { t: 'hit', side: u.side, tile, dmg: c.n, hp: Math.max(0, u.hp) });
    if (u.hp <= 0) { s.board[tile] = null; emit(s, ev, { t: 'die', side: u.side, tile, card: u.card }); }
  }
}
// Food for the side whose turn it is; true when it wins.
function score(s, ev) {
  const side = s.turn, p = s.p[side], regions = heldRegions(s, side);
  if (!regions.length) return false;
  p.food += regions.length;
  emit(s, ev, { t: 'food', side, n: regions.length, regions, food: p.food });
  if (p.food >= GOAL) { s.winner = side; emit(s, ev, { t: 'end', winner: side }); return true; }
  return false;
}
function mEndTurn(s, ev) {
  if (s.winner !== null) throw new Error('endTurn: match over');
  if (SCORE_AT === 'end' && score(s, ev)) return;
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  mStartTurn(s, ev);
}

export function playAction(s, card, tile, ev) { const t = clone(s); mPlay(t, card, tile, ev); return t; }
export function endTurn(s, ev) { const t = clone(s); mEndTurn(t, ev); return t; }
export function _play(t, card, tile) { mPlay(t, card, tile, null); return t; }

export function deckSummary(s, side) {
  const p = s.p[side], cnt = (a) => a.reduce((m, x) => (m[x] = (m[x] || 0) + 1, m), {});
  const pl = cnt(p.played), d = cnt(p.deck);
  return Object.entries(DECK).map(([id, total]) => ({ id, total, played: pl[id] || 0, inDeck: d[id] || 0, unseen: total - (pl[id] || 0) }));
}
