// Bots for 18 Edge flip grid. Each is a function (state, rng) -> one action for s.turn. None reads
// a hidden card: Expert reshuffles the opponent's hand and deck and its own deck before each play-out.

import { CARDS, CELLS, NB, ROTS, clone, _act, act, legalActions, flipsAt, edgesOf, count } from './engine.js';

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
const END = { t: 'end' };
const placements = (s) => legalActions(s).filter(a => a.t === 'place');

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { const L = legalActions(s); return L[Math.floor(rng() * L.length)]; }
// ------------------------------------------------------------------ Greedy
// the Coin at once; then each placement the one that takes the most cells now (flips + its own),
// the most expensive card among ties, until nothing can be placed
export function greedyBot(s) {
  const P = s.p[s.turn];
  if (P.hand.includes('COIN')) return { t: 'coin' };
  let best = null, bv = -1;
  for (const a of placements(s)) {
    const v = flipsAt(s, s.turn, a.card, a.rot, a.cell).length + 1;
    if (v > bv || (v === bv && CARDS[a.card].cost > CARDS[best.card].cost)) { bv = v; best = a; }
  }
  return best || END;
}
// ------------------------------------------------------------------ Filler
// its cheapest card in a cell with no enemy neighbour (any cell when there is none), until nothing fits
export function fillerBot(s) {
  const me = s.turn, P = s.p[me];
  const ids = [...new Set(P.hand)].filter(id => id !== 'COIN' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[a].cost - CARDS[b].cost);
  if (!ids.length) return END;
  const empty = []; for (let c = 0; c < CELLS; c++) if (!s.grid[c]) empty.push(c);
  if (!empty.length) return END;
  const calm = empty.filter(c => !NB[c].some(([nc]) => s.grid[nc] && s.grid[nc].owner !== me));
  return { t: 'place', card: ids[0], cell: (calm.length ? calm : empty)[0], rot: 0 };
}

// ------------------------------------------------------------------ Expert
// a placement's worth at a glance: cells taken now, less what its weak edges leave open
export function glance(s, a) {
  const me = s.turn, e = edgesOf(a.card, a.rot);
  let v = 1 + flipsAt(s, me, a.card, a.rot, a.cell).length;
  for (const [nc, mi] of NB[a.cell]) if (!s.grid[nc]) v -= (5 - e[mi]) * 0.08;
  return v - CARDS[a.card].cost * 0.04;
}
// play-out policy: the best of a few sampled placements, now and then the turn ended early
function policy(s, rng) {
  const P = s.p[s.turn];
  if (P.hand.includes('COIN') && rng() < 0.7) return { t: 'coin' };
  const ids = [...new Set(P.hand)].filter(id => id !== 'COIN' && CARDS[id].cost <= P.mana);
  if (!ids.length) return END;
  const empty = []; for (let c = 0; c < CELLS; c++) if (!s.grid[c]) empty.push(c);
  let best = null, bv = -Infinity;
  for (let k = 0; k < 16; k++) {
    const id = ids[Math.floor(rng() * ids.length)], rots = ROTS[id];
    const a = { t: 'place', card: id, cell: empty[Math.floor(rng() * empty.length)], rot: rots[Math.floor(rng() * rots.length)] };
    const v = glance(s, a) + rng() * 0.3;
    if (v > bv) { bv = v; best = a; }
  }
  if (bv < 1 && rng() < 0.25) return END;
  return best;
}
function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.filter(x => x !== 'COIN').concat(O.deck), rng), coin = O.hand.includes('COIN');
  const hn = O.hand.length - (coin ? 1 : 0);
  O.hand = pool.slice(0, hn); if (coin) O.hand.push('COIN'); O.deck = pool.slice(hn);
  shuffle(t.p[me].deck, rng);
  return t;
}
function rollout(t, me, rng) {
  let steps = 0;
  while (t.winner === null && steps < 300) { _act(t, policy(t, rng)); steps++; }
  if (t.winner === null) return 0.5;
  const w = t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0, m = count(t, me) - count(t, 1 - me);
  return 0.75 * w + 0.25 / (1 + Math.exp(-m / 2));
}
export function candidates(s, keep = 12) {
  const L = legalActions(s), out = [], pl = [];
  for (const a of L) if (a.t === 'place') pl.push({ a, v: glance(s, a) }); else out.push(a);
  pl.sort((x, y) => y.v - x.v);
  // the best few of every card, then the best overall
  const per = new Map();
  for (const x of pl) { const n = per.get(x.a.card) || 0; if (n < 2) { per.set(x.a.card, n + 1); out.push(x.a); } }
  for (const x of pl) { if (out.length >= keep + 2) break; if (!out.includes(x.a)) out.push(x.a); }
  return out;
}
export function expertBot({ playouts = 300, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.turn;
    const arms = candidates(s);
    if (arms.length === 1) return arms[0];
    for (const a of arms) { const t = act(s, a); if (t.winner === me) return a; }
    let alive = arms.map(a => ({ a, w: 0, n: 0 }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, makeRng(seed)); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
export const EXPERT = { playouts: 300 };
