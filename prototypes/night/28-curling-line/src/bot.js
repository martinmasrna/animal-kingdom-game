// Bots for Curling line, simplest first. One throw at a time through legalActions/act, the same API
// the page uses. None reads a hidden card: the Expert deals the opponent's hand again from the cards
// not in its discard pile, and reshuffles both decks, before every play-out.

import { CARDS, clone, _act, legalActions, slide, endScore } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, rng) => a[Math.floor(rng() * a.length)];
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const cost = (a) => a.card ? CARDS[a.card].cost : 0;

export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// Greedy: the throw that leaves the best score if the end stopped now, cheapest among ties.
export function nowValue(s, a) {
  const me = s.toMove, st = s.stones.map(x => ({ ...x }));
  slide(st, me, a.d, -1);
  const sc = endScore(st);
  return sc ? (sc[0] === me ? sc[1] : -sc[1]) : 0;
}
export function greedyBot(s) {
  // each target cell once, reached by the cheapest throw that reaches it
  const byD = new Map();
  for (const a of legalActions(s)) { const o = byD.get(a.d); if (!o || cost(a) < cost(o)) byD.set(a.d, a); }
  let best = null, bv = -Infinity, bc = Infinity;
  for (const a of byD.values()) { const v = nowValue(s, a), c = cost(a); if (v > bv || (v === bv && c < bc)) { bv = v; bc = c; best = a; } }
  return best;
}
// Greedy with noise, for play-outs: one throw in EPS is random.
export function noisyGreedy(s, rng, eps = 0.25) { return rng() < eps ? pick(legalActions(s), rng) : greedyBot(s); }

// ------------------------------------------------------------------ the Expert
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng), h = O.hand.length;
  O.hand = pool.slice(0, h); O.deck = pool.slice(h);
  shuffle(t.p[me].deck, rng);
  t.seed = (rng() * 4294967296) >>> 0;
  return t;
}
function playout(t, me, rng) {
  while (t.winner === null) _act(t, noisyGreedy(t, rng));
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}
// Successive halving on common resampled worlds; the default (Greedy's throw) is never dropped and
// stands unless the best beats it, world by world, by more than one standard error.
function halving(n, budget, run, keep) {
  let alive = [...Array(n).keys()];
  const vals = [...Array(n)].map(() => []);
  const mean = (i) => { let a = 0, c = 0; for (const v of vals[i]) if (v !== undefined) { a += v; c++; } return a / Math.max(1, c); };
  const rounds = Math.max(1, Math.ceil(Math.log2(n)));
  let sample = 0;
  for (let r = 0; r < rounds && alive.length > 1; r++) {
    const per = Math.max(2, Math.floor(budget / (rounds * alive.length)));
    for (let k = 0; k < per; k++, sample++) for (const i of alive) vals[i][sample] = run(i, sample);
    alive.sort((a, b) => mean(b) - mean(a));
    const half = alive.slice(0, Math.max(1, Math.ceil(alive.length / 2)));
    if (keep >= 0 && !half.includes(keep)) half.push(keep);
    alive = half;
  }
  alive.sort((a, b) => mean(b) - mean(a));
  const best = alive[0];
  if (keep < 0 || best === keep) return best;
  const d = [];
  for (let k = 0; k < sample; k++) if (vals[best][k] !== undefined && vals[keep][k] !== undefined) d.push(vals[best][k] - vals[keep][k]);
  const m = d.reduce((a, b) => a + b, 0) / d.length, sd = Math.sqrt(d.reduce((a, b) => a + (b - m) * (b - m), 0) / Math.max(1, d.length - 1));
  return m > sd / Math.sqrt(d.length) ? best : keep;
}
const sig = (t) => JSON.stringify([t.end, t.score, t.hammer, t.winner, t.stones.map(x => x.owner + ':' + x.cell).sort(), t.energy, t.p.map(p => p.hand.slice().sort().join())]);
export function sameDecision(s, a, b) { const x = clone(s), y = clone(s); _act(x, a); _act(y, b); return sig(x) === sig(y); }
export function expertBot({ budget = 3000 } = {}) {
  return function (s, rng) {
    const me = s.toMove, seen = new Map();
    // equivalent throws collapse onto the cheapest
    for (const a of legalActions(s).sort((x, y) => cost(x) - cost(y))) { const t = clone(s); _act(t, a); const k = sig(t); if (!seen.has(k)) seen.set(k, a); }
    const acts = [...seen.values()];
    if (acts.length === 1) return acts[0];
    const g = greedyBot(s), keep = acts.findIndex(a => sameDecision(s, a, g));
    const seeds = [];
    const seedOf = (k) => { while (seeds.length <= k) seeds.push((rng() * 4294967296) >>> 0); return seeds[k]; };
    const best = halving(acts.length, budget, (i, k) => {
      const r = makeRng(seedOf(k)), t = determinize(s, me, r);
      _act(t, acts[i]);
      return playout(t, me, r);
    }, keep);
    return acts[best];
  };
}
