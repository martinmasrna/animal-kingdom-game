// The Board Toy 3 bot. Position is judged region by region: a region only one side
// stands in is worth more the more of its four tiles that side holds; a region both
// sides stand in is worth nothing to either. A turn is built card by card, each card
// on its best tile by that judgement; the bot tries every affordable set of cards and
// keeps the one whose position is best after the opponent's likely reply (a greedy
// reply from hands sampled out of the cards he has not played). It never reads his
// hand or either deck.

import { CARDS, TILES, GOAL, REGIONS, clone, _play, heldRegions, regionPower, ownTile } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// value of a region by how many of its tiles the only side in it holds (index 0..4)
export const W = { reg: [0, 0.1, 0.5, 1.4, 3.2], maj: 2, margin: 0.15, hp: 0.15, hand: 0.6 };

export function evaluate(s, me) {
  const P = s.p[me], O = s.p[1 - me];
  let v = P.food - O.food;
  for (const rg of REGIONS) {
    const p = regionPower(s, rg), d = p[me] - p[1 - me];
    v += Math.sign(d) * W.maj + W.margin * Math.max(-4, Math.min(4, d));
  }
  for (const u of s.board) if (u) v += (u.side === me ? 1 : -1) * W.hp * Math.min(u.hp, 5);
  v += W.hand * (P.hand.length - O.hand.length);
  return v;
}

function legalMoves(t, me) {
  const P = t.p[me], out = [];
  for (const id of new Set(P.hand)) {
    if (CARDS[id].cost > P.mana) continue;
    for (let i = 0; i < TILES; i++) {
      const u = t.board[i];
      if (CARDS[id].kind === 'Unit' ? u === null && ownTile(me, i) : u && u.side !== me) out.push({ card: id, tile: i });
    }
  }
  return out;
}

// Play one move at a time, always the one that most improves the position; stop when none does.
export function greedyTurn(s) {
  const me = s.turn, moves = [];
  let t = clone(s), cur = evaluate(t, me);
  for (;;) {
    let best = null, bestV = cur;
    for (const m of legalMoves(t, me)) {
      const t2 = clone(t); _play(t2, m.card, m.tile);
      const v = evaluate(t2, me) + W.hand; // judge the board, not the card leaving hand
      if (v > bestV + 1e-9) { bestV = v; best = { m, t2 }; }
    }
    if (!best) return moves;
    moves.push(best.m); t = best.t2; cur = evaluate(t, me);
  }
}

// Every distinct affordable set of cards from hand.
function cardSets(hand, mana) {
  const counts = {};
  for (const id of hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts), out = [];
  (function rec(i, left, cards) {
    if (i === ids.length) { out.push(cards.slice()); return; }
    const c = CARDS[ids[i]];
    for (let k = 0; k <= counts[ids[i]] && k * c.cost <= left; k++) {
      for (let j = 0; j < k; j++) cards.push(ids[i]);
      rec(i + 1, left - k * c.cost, cards);
      cards.length -= k;
    }
  })(0, mana, []);
  return out;
}

// Place a set: strikes first, biggest first, then units, biggest first; each on its best tile.
function placeSet(s, set) {
  const me = s.turn;
  const order = set.slice().sort((a, b) => (CARDS[a].kind === CARDS[b].kind ? CARDS[b].n - CARDS[a].n : CARDS[a].kind === 'Strike' ? -1 : 1));
  let t = clone(s); const moves = [];
  for (const id of order) {
    let best = null, bestV = -Infinity;
    for (let i = 0; i < TILES; i++) {
      const u = t.board[i];
      if (!(CARDS[id].kind === 'Unit' ? u === null && ownTile(me, i) : u && u.side !== me)) continue;
      const t2 = clone(t); _play(t2, id, i);
      const v = evaluate(t2, me);
      if (v > bestV) { bestV = v; best = { m: { card: id, tile: i }, t2 }; }
    }
    if (!best) return null;
    moves.push(best.m); t = best.t2;
  }
  return { t, moves };
}

function lookahead(t, me, hands) {
  const myFood = t.p[me].food + heldRegions(t, me).length;
  if (myFood >= GOAL) return 1000 + myFood;
  let v = 0;
  for (const hand of hands) {
    const r = clone(t), O = r.p[1 - me];
    r.p[me].food = myFood;
    O.maxMana = Math.min(10, O.maxMana + 1); O.mana = O.maxMana;
    O.hand = hand.slice();
    r.turn = 1 - me;
    for (const m of greedyTurn(r)) _play(r, m.card, m.tile);
    O.food += heldRegions(r, 1 - me).length;
    r.turn = me;
    v += O.food >= GOAL ? -1000 : evaluate(r, me);
  }
  return v / hands.length;
}

export function botTurn(s, rng = Math.random, K = 5) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const unseen = O.hand.concat(O.deck); // the pool he might hold: used only as a pool
  const n = Math.min(unseen.length, O.hand.length + (O.deck.length ? 1 : 0));
  const hands = [];
  for (let k = 0; k < K; k++) {
    const pool = unseen.slice();
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = pool[i]; pool[i] = pool[j]; pool[j] = x; }
    hands.push(pool.slice(0, n));
  }
  let best = [], bestV = -Infinity;
  for (const set of cardSets(P.hand, P.mana)) {
    const r = placeSet(s, set);
    if (!r) continue;
    const v = lookahead(r.t, me, hands) - 0.001 * r.moves.length;
    if (v > bestV) { bestV = v; best = r.moves; }
  }
  return best;
}

export function randomTurn(s, rng) {
  const me = s.turn, moves = [];
  let t = clone(s);
  for (let n = 0; n < 20; n++) {
    const opts = legalMoves(t, me);
    if (!opts.length || rng() < 0.15) return moves;
    const m = opts[Math.floor(rng() * opts.length)];
    _play(t, m.card, m.tile); moves.push(m);
  }
  return moves;
}
