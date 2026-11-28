// Bots for Blind fronts. None reads a hidden card: the Expert deals the opponent's face-down
// cards from the cards it has not seen, each with the cost its energy drop showed, and reshuffles
// the opponent's hand and both decks and the round seed before each search iteration.

import { CARDS, FRONTS, clone, step, key, frontStrength, legalActions, soloIndex } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pickOf = (a, rng) => a[Math.floor(rng() * a.length)];
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const str = (id) => CARDS[id].str + (id === 'LO' ? 1.5 : 0);
const byOrder = (s) => [0, 1, 2].sort((a, b) => s.values[b] - s.values[a]); // fronts, most valuable first

// Candidate actions: every legal action, except that once the opponent has passed the order of
// the remaining placements does not matter (only canonical orders are tried) and a Feint, which
// then bluffs nobody, goes only where it feeds a Mass.
export function cands(s) {
  const all = legalActions(s);
  if (s.phase !== 'place') return all;
  const P = s.p[s.toMove], O = s.p[1 - s.toMove];
  if (!O.passed) return all;
  return all.filter(a => a.t === 'pass' || (soloIndex(a) >= P.lastSolo && (a.card !== 'FE' || P.placed[a.front].includes('MA'))));
}

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }
function discardLow(s) { const P = s.p[s.toMove]; return { t: 'discard', card: P.hand.slice().sort((a, b) => str(a) - str(b))[0] }; }
// Greedy (the spec's rule): its strongest affordable card to the 3-front, then the 2-front, then
// the 1-front, round and round, passing when it can place nothing; discards its weakest.
export function greedyBot(s) {
  if (s.phase === 'discard') return discardLow(s);
  const P = s.p[s.toMove];
  const ok = P.hand.filter(id => CARDS[id].cost <= P.energy).sort((a, b) => CARDS[b].str - CARDS[a].str || CARDS[a].cost - CARDS[b].cost);
  if (!ok.length) return { t: 'pass' };
  const n = P.placed.reduce((k, f) => k + f.length, 0);
  return { t: 'place', card: ok[0], front: byOrder(s)[n % 3] };
}
// Spread, a fixed split: its three strongest affordable cards, one to each front, most valuable
// front first, then it passes, whatever the opponent does.
export function spreadBot(s) {
  if (s.phase === 'discard') return discardLow(s);
  const P = s.p[s.toMove];
  const n = P.placed.reduce((k, f) => k + f.length, 0);
  const ok = P.hand.filter(id => CARDS[id].cost <= P.energy).sort((a, b) => CARDS[b].str - CARDS[a].str || CARDS[a].cost - CARDS[b].cost);
  if (n >= 3 || !ok.length) return { t: 'pass' };
  return { t: 'place', card: ok[0], front: byOrder(s)[n] };
}

// ------------------------------------------------------------------ Expert: ISMCTS
// What a face-down card of each cost is worth on average, the guess a player makes from the
// energy it saw spent.
const EST = { 0: 0.5, 1: 1.8, 2: 3.8, 3: 5, 4: 7 };
// Rollout policy: discard the weakest; find the most valuable front it is losing (against a guess
// of his cards from their costs, with room for what he may still add) and put the cheapest card
// that takes it there; pass when every front worth fighting is held or nothing helps.
function policy(s, rng) {
  if (s.phase === 'discard') return discardLow(s);
  const me = s.toMove, P = s.p[me], O = s.p[1 - me];
  if (rng() < 0.07) return pickOf(legalActions(s), rng);
  const ok = P.hand.filter(id => CARDS[id].cost <= P.energy);
  if (!ok.length) return { t: 'pass' };
  const slack = O.passed ? 0.5 : 1.5 + Math.min(O.energy, 4) * 0.6;
  let best = null, bk = 0;
  for (let f = 0; f < FRONTS; f++) {
    const mine = frontStrength(P.placed[f]);
    let his = 0; for (const id of O.placed[f]) his += EST[CARDS[id].cost];
    const need = his + slack - mine;
    if (need <= 0) continue;
    // the cheapest card that covers the need, else the strongest affordable one
    const after = (id) => frontStrength(P.placed[f].concat(id)) - mine;
    const cover = ok.filter(id => after(id) >= need).sort((a, b) => CARDS[a].cost - CARDS[b].cost);
    const id = cover.length ? cover[0] : ok.slice().sort((a, b) => after(b) - after(a))[0];
    const gain = s.values[f] * (cover.length ? 1 : 0.35) - CARDS[id].cost * 0.25 + (rng() - 0.5) * 0.8;
    if (gain > bk) { bk = gain; best = { t: 'place', card: id, front: f }; }
  }
  return best || { t: 'pass' };
}
// A position's worth to seat 0: points, plus a little for banked energy and a good hand.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  const side = (k) => { const p = s.p[k]; const h = p.hand.map(str).sort((a, b) => b - a).slice(0, 5).reduce((a, b) => a + b, 0); return p.score + 0.35 * p.energy + 0.08 * h; };
  return 1 / (1 + Math.exp(-(side(0) - side(1)) / 2.2));
}
function determinize(s, viewer, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - viewer];
  const pool = O.hand.concat(O.deck); for (const f of O.placed) pool.push(...f);
  shuffle(pool, rng);
  // his face-down cards: any unseen card of the cost he paid
  O.placed = O.placed.map(f => f.map(id => { const c = CARDS[id].cost, k = pool.findIndex(x => CARDS[x].cost === c); return pool.splice(k, 1)[0]; }));
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[viewer].deck, rng);
  return t;
}
// The opponent's placement shows only its front and its cost.
function obsKey(s, a, viewer) { return a.t === 'place' && s.toMove !== viewer ? 'p$' + CARDS[a.card].cost + a.front : key(a); }
export const GAME = { cands, key, obsKey, determinize, step, policy, value0, turnNo: (s) => s.round };

// Single-observer ISMCTS: each iteration deals a world consistent with what the mover has seen,
// walks the shared tree by UCB over the moves legal in that world, expands one, plays out
// `plies` turns with the rollout policy and scores the end by value0.
export function ismcts(s, rng, G, { iters = 1500, c = 0.7, plies = 4, stats = null } = {}) {
  const me = s.toMove, t00 = G.turnNo(s);
  const acts0 = G.cands(s);
  if (acts0.length === 1) return acts0[0];
  const root = { n: 0, kids: new Map() };
  // a win sooner is worth a little more than a win later, a loss later a little more than one now
  const final = (d) => { const k = 0.01 * Math.min(30, G.turnNo(d) - t00); return d.winner === 0 ? 1 - k : d.winner === 1 ? k : 0.5; };
  for (let it = 0; it < iters; it++) {
    const d = G.determinize(s, me, rng);
    let node = root; const path = [];
    while (d.winner === null) {
      const groups = new Map();
      for (const a of G.cands(d)) { const k = G.obsKey(d, a, me); const g = groups.get(k); if (g) g.push(a); else groups.set(k, [a]); }
      const untried = [];
      for (const k of groups.keys()) { const ch = node.kids.get(k); if (ch) ch.avail++; else untried.push(k); }
      let k, fresh = false;
      if (untried.length) { k = untried[Math.floor(rng() * untried.length)]; node.kids.set(k, { n: 0, w: 0, avail: 1, kids: new Map(), mover: d.toMove }); fresh = true; }
      else {
        let best = -Infinity;
        for (const kk of groups.keys()) { const ch = node.kids.get(kk); const u = ch.w / ch.n + c * Math.sqrt(Math.log(ch.avail) / ch.n); if (u > best) { best = u; k = kk; } }
      }
      const g = groups.get(k);
      G.step(d, g.length === 1 ? g[0] : g[Math.floor(rng() * g.length)]);
      node = node.kids.get(k); path.push(node);
      if (fresh) break;
    }
    const t0 = G.turnNo(d);
    let guard = 0;
    while (d.winner === null && G.turnNo(d) - t0 < plies && guard++ < 400) G.step(d, G.policy(d, rng));
    const v0 = d.winner !== null ? final(d) : G.value0(d);
    for (const nd of path) { nd.n++; nd.w += nd.mover === 0 ? v0 : 1 - v0; }
    root.n++;
  }
  if (stats) for (const [k, ch] of root.kids) stats[k] = { n: ch.n, w: +(ch.w / ch.n).toFixed(3) };
  let bestK = null, bn = -1, bw = -1;
  for (const [k, ch] of root.kids) { const w = ch.w / ch.n; if (ch.n > bn || (ch.n === bn && w > bw)) { bn = ch.n; bw = w; bestK = k; } }
  return acts0.find(a => G.obsKey(s, a, me) === bestK) || acts0[0];
}
export const EXPERT = { iters: 2000, c: 0.7, plies: 1 };
// Once the opponent has passed, the rest of the round is a puzzle for one: every set of
// placements the energy pays for is scored over dealt worlds of his face-down cards (by the same
// end-of-round worth the search uses) and the best set is played, one card at a time.
export function soloPlan(s, rng, samples = 48) {
  const me = s.toMove, P = s.p[me], O = s.p[1 - me];
  const worlds = [];
  for (let k = 0; k < samples; k++) worlds.push(determinize(s, me, rng).p[1 - me].placed.map(frontStrength));
  const hand = P.hand.slice().sort(), n = hand.length;
  const hisHand = 0.08 * O.hand.map(str).sort((a, b) => b - a).slice(0, 5).reduce((a, b) => a + b, 0) + 0.35 * O.energy;
  let best = null, bv = -Infinity;
  const asg = new Array(n).fill(-1);
  const score = () => {
    let e = P.energy; const placed = P.placed.map(f => f.slice()), kept = [];
    for (let i = 0; i < n; i++) { if (asg[i] < 0) kept.push(hand[i]); else { placed[asg[i]].push(hand[i]); e -= CARDS[hand[i]].cost; } }
    const mine = placed.map(frontStrength);
    const keep = 0.08 * kept.map(str).sort((a, b) => b - a).slice(0, 5).reduce((a, b) => a + b, 0) + 0.35 * e;
    let v = 0;
    for (const his of worlds) {
      let a = P.score, b = O.score;
      for (let f = 0; f < FRONTS; f++) { if (mine[f] > his[f]) a += s.values[f]; else if (his[f] > mine[f]) b += s.values[f]; }
      if ((a >= 12 || b >= 12) && a !== b) v += a > b ? 1 : 0;
      else v += 1 / (1 + Math.exp(-((a - b) + keep - hisHand) / 2.2));
    }
    return v / samples;
  };
  const rec = (i, e) => {
    if (i === n) { const v = score(); if (v > bv + 1e-9) { bv = v; best = asg.slice(); } return; }
    const lo = i > 0 && hand[i] === hand[i - 1] ? asg[i - 1] : -1; // identical cards in non-decreasing order
    for (let f = lo; f < FRONTS; f++) {
      if (f >= 0) {
        const c = CARDS[hand[i]].cost;
        if (c > e) continue;
        if (hand[i] === 'FE' && !P.placed[f].includes('MA') && !hand.some((x, j) => x === 'MA' && asg[j] === f)) continue;
        asg[i] = f; rec(i + 1, e - c);
      } else { asg[i] = -1; rec(i + 1, e); }
    }
    asg[i] = -1;
  };
  rec(0, P.energy);
  const first = best && best.findIndex(f => f >= 0);
  return first >= 0 ? { t: 'place', card: hand[first], front: best[first] } : { t: 'pass' };
}
export function expertBot(opts = EXPERT) {
  return (s, rng) => s.phase === 'place' && s.p[1 - s.toMove].passed ? soloPlan(s, rng) : ismcts(s, rng, GAME, opts);
}

export const TRIVIAL = { random: randomBot, greedy: greedyBot, spread: spreadBot };
export function meaning(s, a) { return key(a); }
