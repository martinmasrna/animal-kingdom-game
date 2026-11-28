// Bots for Round purse, simplest first. One action at a time through legalActions/act, the same API
// the page uses. None reads a hidden card: the Expert deals the opponent's hand again from the cards
// it has not shown, and reshuffles both decks, before every play-out.

import { CARDS, deckList, clone, _act, legalActions, total, seen } from './engine.js';

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

export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// What a card adds to my side against the other's this round: its power; Cut, the power it removes; Gift, minus 4.
function swing(s, id) {
  const c = CARDS[id], O = s.table[1 - s.turn];
  if (c.cut) return O.length ? Math.max(...O.map(x => x.power)) : 0;
  if (c.gift) return -c.gift;
  return c.power;
}
function strongest(s) {
  let best = null, bv = 0;
  for (const a of legalActions(s)) if (a.t === 'play') { const v = swing(s, a.card); if (v > bv || (v === bv && best && CARDS[a.card].cost < CARDS[best.card].cost)) { bv = v; best = a; } }
  return best;
}
// Greedy: while behind or level, its strongest affordable card; passes when ahead, so it never
// passes while behind, in the deciding round or any other, unless nothing it can play helps.
export function greedyBot(s) {
  const me = s.turn, a = total(s, me), b = total(s, 1 - me);
  if (a > b) return { t: 'pass' };
  return strongest(s) || { t: 'pass' };
}
// Spend: its strongest affordable card every turn, never passing while one helps.
export function spendBot(s) { return strongest(s) || { t: 'pass' }; }
// Greedy with noise.
export function noisyGreedy(s, rng, eps = 0.2) { return rng() < eps ? pick(legalActions(s), rng) : greedyBot(s); }

// The play-out policy, a purse-minded Greedy: ahead, pass; behind or level, the cheapest card that
// gets ahead; when no single card does, keep fighting only a round that decides the match or one
// still open, and otherwise give it up (dumping a Gift into it first).
const decidingRound = (s) => s.round === 3 || s.wins[1 - s.turn] === 1;
export function thriftyBot(s) {
  const me = s.turn, a = total(s, me), b = total(s, 1 - me), L = legalActions(s).filter(x => x.t === 'play');
  if (a > b) return { t: 'pass' };
  let best = null;
  for (const x of L) { const v = swing(s, x.card); if (a + v > b && (!best || CARDS[x.card].cost < CARDS[best.card].cost || (CARDS[x.card].cost === CARDS[best.card].cost && v < swing(s, best.card)))) best = x; }
  if (best) return best;
  const gift = L.find(x => CARDS[x.card].gift);
  if (decidingRound(s) || (!s.passed[1 - me] && b - a <= 6)) return strongest(s) || gift || { t: 'pass' };
  return gift || { t: 'pass' };
}
export function noisyThrifty(s, rng, eps = 0.2) { return rng() < eps ? pick(legalActions(s), rng) : thriftyBot(s); }

// ------------------------------------------------------------------ the Expert
export function determinize(s, me, rng) {
  const t = clone(s), o = 1 - me, O = t.p[o];
  const pool = deckList();
  for (const id of seen(t, o)) { const k = pool.indexOf(id); if (k >= 0) pool.splice(k, 1); }
  shuffle(pool, rng);
  const h = O.hand.length;
  O.hand = pool.slice(0, h); O.deck = pool.slice(h);
  shuffle(t.p[me].deck, rng);
  t.seed = (rng() * 4294967296) >>> 0;
  return t;
}
function playout(t, me, rng, roll) {
  for (let k = 0; k < 500 && t.winner === null; k++) _act(t, roll(t, rng));
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : t.winner === null ? 0.5 : 0;
}
// Successive halving on common resampled worlds; the default (the play-out policy's move) is never dropped and
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
const key = (a) => a.t === 'pass' ? 'pass' : a.card;
export function sameDecision(s, a, b) { return key(a) === key(b); }
export function expertBot({ budget = 3000, rollout = 'thrifty' } = {}) {
  const roll = rollout === 'random' ? (t, r) => pick(legalActions(t), r) : rollout === 'greedy' ? noisyGreedy : noisyThrifty;
  return function (s, rng) {
    const me = s.turn, acts = legalActions(s).sort((x, y) => (x.t === 'pass' ? -1 : CARDS[x.card].cost) - (y.t === 'pass' ? -1 : CARDS[y.card].cost));
    if (acts.length === 1) return acts[0];
    const g = rollout === 'thrifty' ? thriftyBot(s) : greedyBot(s), keep = acts.findIndex(a => sameDecision(s, a, g));
    const seeds = [];
    const seedOf = (k) => { while (seeds.length <= k) seeds.push((rng() * 4294967296) >>> 0); return seeds[k]; };
    const best = halving(acts.length, budget, (i, k) => {
      const r = makeRng(seedOf(k)), t = determinize(s, me, r);
      _act(t, acts[i]);
      return playout(t, me, r, roll);
    }, keep);
    return acts[best];
  };
}
