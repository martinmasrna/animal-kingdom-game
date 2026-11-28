// Bots for Costed tricks. None reads a hidden card: the Expert deals the opponent's hand from the
// cards it has not seen face-up, leaving out every card its failures to follow suit ruled out,
// and reseeds the shuffle before each search iteration.

import { SUITS, suitOf, rankOf, costOf, deckList, clone, step, key, legalActions, trickWinner } from './engine.js';

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
// how much a card is worth keeping: rank, more for trumps, nothing if it can no longer be paid for
const keep = (s, P, c) => (costOf(c) > P.energy ? 0 : rankOf(c) + (suitOf(c) === s.trump ? 5 : 0));
const lowest = (s, P, cards) => cards.slice().sort((a, b) => keep(s, P, a) - keep(s, P, b) || rankOf(a) - rankOf(b))[0];
// the face-up cards that would take the trick against what was led
function winners(s, P, ups) { return ups.filter(c => trickWinner(s, s.led, { card: c, up: true }, s.leader) === s.toMove); }

export function cands(s) { return legalActions(s); }

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }
// Greedy (the spec's rule): following, it takes a trick worth 2 or more with its cheapest winning
// card it can pay for; leading such a trick, it leads its strongest card it can pay for (a trump
// first). Otherwise it plays face-down its least useful card, or its cheapest legal card when it
// must follow suit.
export function greedyBot(s) {
  const P = s.p[s.toMove], legal = legalActions(s), ups = legal.filter(a => a.up).map(a => a.card), forced = !legal.some(a => !a.up);
  const prize = s.prizes[s.trick];
  const cheapest = (cs) => cs.slice().sort((a, b) => costOf(a) - costOf(b) || rankOf(a) - rankOf(b))[0];
  if (!s.led) {
    if (prize >= 2 && ups.length) { const best = ups.slice().sort((a, b) => (suitOf(b) === s.trump) - (suitOf(a) === s.trump) || rankOf(b) - rankOf(a))[0]; return { t: 'play', card: best, up: true }; }
    return { t: 'play', card: lowest(s, P, P.hand), up: false };
  }
  const win = winners(s, P, ups);
  if (prize >= 2 && win.length) return { t: 'play', card: cheapest(win), up: true };
  if (forced) return { t: 'play', card: cheapest(ups), up: true };
  return { t: 'play', card: lowest(s, P, P.hand), up: false };
}
// High: its highest-ranked card it can pay for, face-up, every time.
export function highBot(s) {
  const P = s.p[s.toMove], ups = legalActions(s).filter(a => a.up).map(a => a.card);
  if (!ups.length) return { t: 'play', card: lowest(s, P, P.hand), up: false };
  return { t: 'play', card: ups.sort((a, b) => rankOf(b) - rankOf(a) || (suitOf(b) === s.trump) - (suitOf(a) === s.trump))[0], up: true };
}

// ------------------------------------------------------------------ Expert: ISMCTS
// Rollout policy: Greedy's rule with taste: leading a big trick it leads a trump it holds only
// when that trump is high, following it takes any trick whose prize is worth the energy, it wins
// a face-down lead with a free card, and it dumps its least useful card face-down. A little noise.
function policy(s, rng) {
  const P = s.p[s.toMove], legal = legalActions(s);
  if (rng() < 0.08) return pickOf(legal, rng);
  const ups = legal.filter(a => a.up).map(a => a.card), forced = !legal.some(a => !a.up), prize = s.prizes[s.trick];
  const cheapest = (cs) => cs.slice().sort((a, b) => costOf(a) - costOf(b) || rankOf(a) - rankOf(b))[0];
  const budget = P.energy / Math.max(1, 8 - s.trick);
  if (!s.led) {
    const strong = ups.filter(c => (suitOf(c) === s.trump && rankOf(c) >= 5) || rankOf(c) === 6);
    if (prize >= 2 && strong.length && rng() < 0.8) return { t: 'play', card: cheapest(strong), up: true };
    const free = ups.filter(c => costOf(c) === 0);
    if (prize === 1 && free.length && rng() < 0.3) return { t: 'play', card: pickOf(free, rng), up: true };
    return { t: 'play', card: lowest(s, P, P.hand), up: false };
  }
  const win = winners(s, P, ups);
  if (win.length) { const c = cheapest(win); if (costOf(c) <= prize * 1.5 * (0.6 + budget / 2) || costOf(c) === 0) return { t: 'play', card: c, up: true }; }
  if (forced) return { t: 'play', card: cheapest(ups), up: true };
  return { t: 'play', card: lowest(s, P, P.hand), up: false };
}
// A position's worth to seat 0 as a win chance: the score difference, and inside a hand the
// prizes still to play for scaled by who has more energy and trumps.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  let v = s.p[0].score - s.p[1].score;
  if (s.trick > 0 && s.trick < 8) {
    const left = s.prizes.slice(s.trick).reduce((a, b) => a + b, 0);
    const pow = (k) => { const p = s.p[k]; return p.energy + p.hand.filter(c => suitOf(c) === s.trump && costOf(c) <= p.energy).length * 2; };
    v += left * 0.5 * Math.tanh((pow(0) - pow(1)) / 6);
  }
  return 1 / (1 + Math.exp(-v / 3.5));
}
function determinize(s, viewer, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - viewer], mine = t.p[viewer];
  const ruled = (c) => O.voids.some(v => suitOf(c) === v.suit && costOf(c) <= v.max);
  const unseen = deckList().filter(c => !O.seen.includes(c));
  const ok = shuffle(unseen.filter(c => !ruled(c)), rng);
  const n = O.hand.length;
  O.hand = ok.slice(0, n);
  O.rest = unseen.filter(c => !O.hand.includes(c));
  return t;
}
// The opponent's face-down card shows nothing.
function obsKey(s, a, viewer) { return !a.up && s.toMove !== viewer ? 'd?' : key(a); }
export const GAME = { cands, key, obsKey, determinize, step, policy, value0, turnNo: (s) => s.hand };

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
export function expertBot(opts = EXPERT) { return (s, rng) => ismcts(s, rng, GAME, opts); }

export const TRIVIAL = { random: randomBot, greedy: greedyBot, high: highBot };
export function meaning(s, a) { return key(a); }
