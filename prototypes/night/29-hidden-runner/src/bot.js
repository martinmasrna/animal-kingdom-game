// Bots for Hidden runner, both roles. A Hunter (any of them) reads only public information: the
// pawns, blocks, the announced kinds and `poss`, the nodes the Runner could be on. A Runner never
// reads the Hunter's hand. Expert redraws what its side cannot see before every play-out.

import { N, ADJ, DIST, SPRINT, ECAP, EGAIN, RCARDS, HCARDS, legalActions, _act, clone, determinize, actionKey, bits, reach, roleOf } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, r) => a[Math.floor(r() * a.length)];
const popc = (m) => { let k = 0; while (m) { m &= m - 1; k++; } return k; };
const near = (s, n) => Math.min(DIST[s.pawns[0]][n], DIST[s.pawns[1]][n]);
const nbhd = (n) => { let m = 1 << n; for (const x of ADJ[n]) m |= 1 << x; return m; };

export function randomBot(s, r) { return pick(legalActions(s), r); }
// The choices worth considering: a Search or Block that touches where the Runner could be.
export function sensible(s) {
  const L = legalActions(s);
  if (s.phase !== 'hunt') return L;
  let zone = 0; for (const n of bits(s.poss)) zone |= nbhd(n);
  let zone2 = zone; for (const n of bits(zone)) zone2 |= nbhd(n);
  return L.filter(a => !(a.card === 'SEA' && !(nbhd(a.node) & s.poss)) && !(a.card === 'BLO' && (!(zone2 & (1 << a.node)) || s.pawns.includes(a.node))));
}

// ------------------------------------------------------------------ Greedy (one per role)
// Greedy Runner: its most expensive move card, to the node farthest from the nearest pawn.
function greedyRunner(s) {
  const L = legalActions(s);
  if (s.phase === 'start') { let best = L[0], bd = -1; for (const a of L) { const d = near(s, a.to); if (d > bd) { bd = d; best = a; } } return best; }
  const kinds = [...new Set(L.map(a => a.card))].filter(k => k !== 'HIDE').sort((a, b) => RCARDS[b].cost - RCARDS[a].cost);
  const k = kinds[0] || 'STEP';
  let best = null, bd = -1;
  for (const a of L) if (a.card === k) { const d = near(s, a.to); if (d > bd) { bd = d; best = a; } }
  return best || L[0];
}
// the node whose neighbourhood splits the possible set most evenly
function splitNode(s) {
  const P = s.poss, n0 = popc(P); let best = -1, bv = Infinity;
  for (let n = 0; n < N * N; n++) { const k = popc(P & nbhd(n)); if (!k) continue; const v = Math.abs(2 * k - n0); if (v < bv) { bv = v; best = n; } }
  return best;
}
// Greedy Hunter: Search when 4 nodes or fewer are possible; each pawn one step toward its nearest
// possible node.
function greedyHunter(s) {
  const P = bits(s.poss);
  if (!s.cardUsed && P.length >= 2 && P.length <= 4 && s.H.hand.includes('SEA') && s.H.energy >= HCARDS.SEA.cost) return { t: 'card', card: 'SEA', node: splitNode(s) };
  for (let p = 0; p < 2; p++) {
    if (s.moved[p]) continue;
    const from = s.pawns[p];
    let tgt = P[0], td = Infinity; for (const n of P) if (DIST[from][n] < td) { td = DIST[from][n]; tgt = n; }
    let to = from, bd = DIST[from][tgt];
    for (const x of ADJ[from]) if (DIST[x][tgt] < bd) { bd = DIST[x][tgt]; to = x; }
    return { t: 'move', pawn: p, to };
  }
  return { t: 'done' };
}
export function greedyBot(s) { return roleOf(s, s.turn) === 'R' ? greedyRunner(s) : greedyHunter(s); }

// ------------------------------------------------------------------ Expert
// Play-out policies, both honest. Runner: weighs distance from the pawns, how much the Hunter's
// possible set grows, and the card's cost. Hunter: catches what is certain, Searches a small set,
// otherwise moves the pawns to cover the possible set.
function runnerPolicy(s, r) {
  const L = legalActions(s);
  if (r() < 0.1) return pick(L, r);
  if (s.phase === 'start') return pick(L, r);
  const prev = bits(s.poss), spread = {};
  let best = L[0], bv = -Infinity;
  for (const a of L) {
    if (!(a.card in spread)) { let m = 0; for (const n of prev) for (const x of reach(s, n, a.card)) m |= 1 << x; spread[a.card] = popc(m); }
    const v = 3 * Math.min(3, near(s, a.to)) + 0.6 * spread[a.card] - 0.7 * RCARDS[a.card].cost + r();
    if (v > bv) { bv = v; best = a; }
  }
  return best;
}
function cover(s, pawns) { let c = 0; for (const n of bits(s.poss)) c += Math.min(DIST[pawns[0]][n], DIST[pawns[1]][n]); return c; }
function hunterPolicy(s, r) {
  const P = bits(s.poss), H = s.H;
  if (P.length === 1) {
    const t = P[0];
    for (let p = 0; p < 2; p++) if (!s.moved[p] && ADJ[s.pawns[p]].includes(t)) return { t: 'move', pawn: p, to: t };
    if (!s.cardUsed && H.hand.includes('SPR') && H.energy >= 1) for (let p = 0; p < 2; p++) if (!s.moved[p] && DIST[s.pawns[p]][t] <= SPRINT) return { t: 'card', card: 'SPR', pawn: p, to: t };
  }
  if (!s.cardUsed && P.length >= 2 && P.length <= 6 && H.hand.includes('SEA') && H.energy >= 1) return { t: 'card', card: 'SEA', node: splitNode(s) };
  if (!s.cardUsed && P.length >= 7 && H.hand.includes('FLA') && H.energy >= 3 && r() < 0.5) return { t: 'card', card: 'FLA' };
  for (let p = 0; p < 2; p++) {
    if (s.moved[p]) continue;
    const from = s.pawns[p];
    let to = from, bc = Infinity;
    for (const x of [from, ...ADJ[from]]) { const pw = s.pawns.slice(); pw[p] = x; const c = cover(s, pw) + ((s.poss >> x) & 1 ? -0.5 : 0) + 0.3 * r(); if (c < bc) { bc = c; to = x; } }
    return { t: 'move', pawn: p, to };
  }
  return { t: 'done' };
}
export function policy(s, r) { return roleOf(s, s.turn) === 'R' ? runnerPolicy(s, r) : hunterPolicy(s, r); }

// Determinized flat Monte Carlo with paired samples: each round of the search redraws what the
// mover cannot see once, then plays every action out from that same redraw with the same play-out
// seed, so actions are compared on identical worlds and a small edge (free information) shows.
export function flatMC(s, r, { iters = 3000 } = {}) {
  const me = s.turn, acts = sensible(s);
  if (acts.length === 1) return acts[0];
  // a win now in every redraw of the hidden part (a catch that cannot miss) is taken at once
  for (const a of acts) { let all = true; for (let k = 0; k < 8 && all; k++) if (_act(determinize(s, me, r), a).winner !== me) all = false; if (all) return a; }
  const w = new Array(acts.length).fill(0), rounds = Math.max(8, Math.floor(iters / acts.length));
  // dominance: free information is never worse. Before ending a Hunter round, Search if a Search
  // splits the possible set and the energy it costs would be lost to the cap next round anyway.
  const freeSearch = s.phase === 'hunt' && !s.cardUsed && s.H.hand.includes('SEA') && s.H.energy + EGAIN - HCARDS.SEA.cost >= ECAP && popc(s.poss) >= 2;
  for (let k = 0; k < rounds; k++) {
    const d0 = determinize(s, me, r), seed = (r() * 4294967296) >>> 0;
    for (let i = 0; i < acts.length; i++) {
      const d = clone(d0), rr = makeRng(seed);
      d.seed = seed;
      _act(d, acts[i]);
      while (d.winner === null) _act(d, policy(d, rr));
      if (d.winner === me) w[i]++;
    }
  }
  let best = 0; for (let i = 1; i < acts.length; i++) if (w[i] > w[best]) best = i;
  if (freeSearch && acts[best].t === 'done') { const n = splitNode(s); if (n >= 0 && popc(s.poss & nbhd(n)) < popc(s.poss)) return { t: 'card', card: 'SEA', node: n }; }
  return acts[best];
}
export const expertBot = (o) => (s, r) => flatMC(s, r, o);
export const racerBot = null;
