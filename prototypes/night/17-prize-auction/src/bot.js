// Bots for 17 Prize auction. Each is a function (state, side, rng) -> the action that side submits
// now (a discard when its hand is over 7, else a bid). Bots are asked before either bid is in, so
// none sees the other's bid; Expert also reshuffles every card it cannot see.

import { CARDS, HAND_MAX, NPRIZES, clone, _submit, coinOf, pointsOf } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// the bid of value v (or the least above it) that pays with the most, smallest cards
export function bidFor(hand, v) {
  const n = { C1: 0, MES: 0, C2: 0, C3: 0 };
  for (const c of hand) if (c in n) n[c]++;
  const ones = n.C1 + n.MES, total = ones + 2 * n.C2 + 3 * n.C3;
  if (v <= 0) return [];
  if (v >= total) return hand.filter(c => CARDS[c].coin > 0);
  for (let target = v; target <= total; target++) {
    let best = null;
    for (let a3 = 0; a3 <= n.C3; a3++) for (let a2 = 0; a2 <= n.C2; a2++) {
      const r = target - 3 * a3 - 2 * a2;
      if (r < 0 || r > ones) continue;
      const k = a3 + a2 + r;
      if (!best || k > best.k) best = { a3, a2, r, k };
    }
    if (best) {
      const out = [];
      for (let i = 0; i < best.a3; i++) out.push('C3');
      for (let i = 0; i < best.a2; i++) out.push('C2');
      const c1 = Math.min(best.r, n.C1);
      for (let i = 0; i < c1; i++) out.push('C1');
      for (let i = 0; i < best.r - c1; i++) out.push('MES');
      return out;
    }
  }
  return hand.filter(c => CARDS[c].coin > 0);
}
const DISCARD_ORDER = { DEBT: 0, P2: 0, P3: 0, P5: 0, C1: 1, MES: 2, C2: 3, C3: 4 };
// down to 7: points and Debt first, then the smallest coin
export function discardFor(hand) {
  const k = hand.length - HAND_MAX;
  return hand.slice().sort((a, b) => DISCARD_ORDER[a] - DISCARD_ORDER[b]).slice(0, k);
}
const handCoin = (s, side) => coinOf(s.p[side].hand);
function potInfo(s) {
  let pts = 0, coin = 0, debt = false;
  for (const c of s.pot) { if (c === 'DEBT') debt = true; pts += Math.max(0, CARDS[c].pts); if (CARDS[c].pts <= 0 && c !== 'DEBT') coin += CARDS[c].coin + (c === 'MES' ? 1 : 0); }
  return { pts, coin, debt, net: pts + (debt ? -3 : 0) };
}

// ------------------------------------------------------------------ Random
export function randomBot(s, side, rng) {
  const hand = s.p[side].hand;
  if (s.phase === 'discard') return { t: 'discard', cards: shuffle(hand.slice(), rng).slice(0, hand.length - HAND_MAX) };
  return { t: 'bid', cards: hand.filter(() => rng() < 0.5) };
}
// ------------------------------------------------------------------ Greedy
// all its coin on point prizes, half (rounded down) on coin prizes, nothing on Debt
export function greedyBot(s, side) {
  const hand = s.p[side].hand;
  if (s.phase === 'discard') return { t: 'discard', cards: discardFor(hand) };
  const { pts, debt } = potInfo(s), sum = handCoin(s, side);
  if (debt) return { t: 'bid', cards: [] };
  return { t: 'bid', cards: bidFor(hand, pts > 0 ? sum : Math.floor(sum / 2)) };
}
// ------------------------------------------------------------------ Racer
// points only: all its coin on point prizes, nothing on anything else
export function racerBot(s, side) {
  const hand = s.p[side].hand;
  if (s.phase === 'discard') return { t: 'discard', cards: discardFor(hand) };
  const { pts, debt } = potInfo(s);
  return { t: 'bid', cards: pts > 0 && !debt ? bidFor(hand, handCoin(s, side)) : [] };
}

// ------------------------------------------------------------------ Expert
// The play-out policy: values the pot (points, coin worth more early), bids that value times a
// random appetite; with Debt in the pot, all or nothing depending on the pot's sign.
function policyBid(s, side, rng, appetite) {
  const hand = s.p[side].hand, sum = handCoin(s, side);
  const { pts, coin, debt, net } = potInfo(s);
  const left = s.prizes.length / NPRIZES;
  const val = (debt ? net : pts) + coin * (0.3 + 1.1 * left);
  if (debt) return bidFor(hand, val + coin * 0.5 > 0 ? 0 : sum);
  return bidFor(hand, Math.min(sum, Math.round(val * appetite * (0.6 + 0.8 * rng()))));
}
function runOut(t, rng, app) {
  while (t.winner === null) {
    if (t.phase === 'discard') { const side = t.need[0] ? 0 : 1; _submit(t, side, { t: 'discard', cards: discardFor(t.p[side].hand) }); continue; }
    const b0 = policyBid(t, 0, rng, app[0]), b1 = policyBid(t, 1, rng, app[1]);
    _submit(t, 0, { t: 'bid', cards: b0 }); _submit(t, 1, { t: 'bid', cards: b1 });
  }
}
// what the opponent could bid at most: its hand size in its best cards from what it may hold
function maxPossible(s, o) {
  const P = s.p[o], pool = P.hand.concat(P.deck).map(c => CARDS[c].coin).sort((a, b) => b - a);
  return pool.slice(0, P.hand.length).reduce((a, b) => a + b, 0);
}
function determinize(s, me, rng) {
  const t = clone(s), o = 1 - me, O = t.p[o];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  if (t.prizes.length > 1) { const rest = shuffle(t.prizes.slice(1), rng); t.prizes = [t.prizes[0]].concat(rest); }
  return t;
}
// zero-sum matrix game by fictitious play: the row player's mixed strategy
export function solve(A, iters = 600) {
  const R = A.length, C = A[0].length, rc = new Float64Array(R), cc = new Float64Array(C), rs = new Float64Array(R), cs = new Float64Array(C);
  let r = 0, c = 0;
  for (let it = 0; it < iters; it++) {
    rc[r]++; cc[c]++;
    for (let j = 0; j < C; j++) cs[j] += A[r][j];
    for (let i = 0; i < R; i++) rs[i] += A[i][c];
    r = 0; for (let i = 1; i < R; i++) if (rs[i] > rs[r]) r = i;
    c = 0; for (let j = 1; j < C; j++) if (cs[j] < cs[c]) c = j;
  }
  return Array.from(rc, x => x / iters);
}
// a finished play-out's worth: mostly who won, partly by how much (a smoother signal)
function score(t, me) {
  const w = t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
  const m = pointsOf(t.p[me]) - pointsOf(t.p[1 - me]);
  return 0.6 * w + 0.4 / (1 + Math.exp(-m / 4));
}
export function expertBot({ worlds = 6, timeMs = 0 } = {}) {
  return function (s, me, rng) {
    const hand = s.p[me].hand;
    if (s.phase === 'discard') return { t: 'discard', cards: discardFor(hand) };
    const o = 1 - me, oMax = maxPossible(s, o), mySum = handCoin(s, me);
    const myVals = []; for (let v = 0; v <= Math.min(mySum, oMax + 1); v++) myVals.push(v);
    // distinct bids only (some values pay the same cards)
    const myBids = [], seenV = new Set();
    for (const v of myVals) { const b = bidFor(hand, v), k = coinOf(b); if (!seenV.has(k)) { seenV.add(k); myBids.push(b); } }
    if (myBids.length === 1) return { t: 'bid', cards: myBids[0] };
    const oVals = []; for (let v = 0; v <= Math.min(oMax, mySum + 1); v++) oVals.push(v);
    const A = myBids.map(() => new Float64Array(oVals.length)), N = myBids.map(() => new Float64Array(oVals.length));
    const t0 = timeMs ? Date.now() : 0;
    for (let w = 0; w < worlds; w++) {
      const world = determinize(s, me, rng), oHand = world.p[o].hand, seed = (rng() * 4294967296) >>> 0;
      const app = [0.7 + 0.8 * rng(), 0.7 + 0.8 * rng()];
      for (let j = 0; j < oVals.length; j++) {
        const ob = bidFor(oHand, oVals[j]);
        for (let i = 0; i < myBids.length; i++) {
          const t = clone(world);
          _submit(t, me, { t: 'bid', cards: myBids[i] }); _submit(t, o, { t: 'bid', cards: ob });
          if (t.winner === null) runOut(t, makeRng(seed + j), app);
          A[i][j] += score(t, me); N[i][j]++;
        }
      }
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    const M = A.map((row, i) => Array.from(row, (x, j) => x / N[i][j]));
    const mix = solve(M);
    // play the equilibrium mix, ignoring slivers
    let tot = 0; const p = mix.map(x => (x >= 0.05 ? x : 0)); for (const x of p) tot += x;
    let r = rng() * tot, k = 0;
    for (; k < p.length - 1; k++) { r -= p[k]; if (r <= 0) break; }
    // with Debt in the pot every bid comes back, so a side that bids at all should bid the most
    // it needs (weakly dominant): it wants to be the higher bidder
    if (s.pot.includes('DEBT') && coinOf(myBids[k]) > 0) k = myBids.length - 1;
    return { t: 'bid', cards: myBids[k] };
  };
}
// the settings the sim and the set positions use
export const EXPERT = { worlds: 12 };
