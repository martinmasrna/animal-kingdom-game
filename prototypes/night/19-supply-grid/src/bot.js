// Bots for the supply grid. Each is a step function: given a position, the one action it takes
// next ({ t: 'end' } ends its turn). None reads a hidden card: the Expert deals the unseen cards
// again before every play-out.

import { CARDS, BASE, BASE_POWER, ADJ, N, dist, clone, _act, legalActions, key, determinize, frontier } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const END = { t: 'end' };
export function randomBot(s, rng) { const o = legalActions(s); return o[Math.floor(rng() * o.length)]; }

function coinHelps(P) {
  if (!P.hand.includes('COIN')) return false;
  let now = -1, withCoin = -1;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'Coin') continue; if (c.cost <= P.mana) now = Math.max(now, c.cost); else if (c.cost <= P.mana + 1) withCoin = Math.max(withCoin, c.cost); }
  return withCoin > now;
}
// a strike of mine that destroys the enemy Base
function baseKill(s, me) {
  const eb = BASE[1 - me];
  for (const i of ADJ[eb]) { const x = s.cells[i]; if (x && x.side === me && !x.struck && !x.wall && x.power >= BASE_POWER) return { t: 'strike', from: i, to: eb }; }
  return null;
}
function dearestUnit(P) {
  let best = null;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'Unit' && c.cost <= P.mana && (!best || c.cost > CARDS[best].cost || (c.cost === CARDS[best].cost && !c.wall))) best = id; }
  return best;
}
const towardBase = (me) => (a, b) => dist(a, BASE[1 - me]) - dist(b, BASE[1 - me]) || Math.abs(a % N - 2) - Math.abs(b % N - 2) || a - b;
// enemy pieces gone if the enemy piece on `cell` is destroyed: it and every piece that hangs on it
function removes(s, cell, me) {
  const C = s.cells, side = 1 - me, b = BASE[side], seen = new Uint8Array(N * N), st = [b];
  let reached = 0, all = 0;
  for (const x of C) if (x && x.side === side) all++;
  seen[b] = 1; seen[cell] = 1; reached = 1;
  while (st.length) { const i = st.pop(); for (const j of ADJ[i]) if (!seen[j] && C[j] && C[j].side === side) { seen[j] = 1; reached++; st.push(j); } }
  return all - reached;
}

// Greedy (the spec's rule): strike the enemy Base when that destroys it; play the dearest affordable
// unit on a cell next to an enemy piece it beats (else the cell closest to the enemy Base); Cut the
// enemy piece whose loss takes the most pieces with it; then every strike that destroys an enemy
// piece without losing the striker.
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], C = s.cells;
  const k = baseKill(s, me); if (k) return k;
  if (coinHelps(P)) return { t: 'coin' };
  const u = dearestUnit(P);
  if (u) {
    const fr = frontier(s, me);
    if (fr.length) {
      const c = CARDS[u];
      let best = -1, bp = -1;
      if (!c.wall) for (const cell of fr) for (const j of ADJ[cell]) { const y = C[j]; if (y && y.side !== me && c.power > y.power && y.power > bp) { bp = y.power; best = cell; } }
      if (best < 0) best = fr.sort(towardBase(me))[0];
      return { t: 'place', card: u, cell: best };
    }
  }
  if (P.hand.includes('CUT') && CARDS.CUT.cost <= P.mana) {
    let best = null, bn = 0;
    for (let i = 0; i < N * N; i++) { const y = C[i]; if (y && y.side !== me && !y.base && y.power <= CARDS.CUT.max) { const a = { t: 'cut', to: i }, n = removes(s, i, me) + y.power / 10; if (n > bn) { bn = n; best = a; } } }
    if (best) return best;
  }
  let best = null, bn = 0;
  for (let i = 0; i < N * N; i++) {
    const x = C[i];
    if (!x || x.side !== me || x.struck || x.wall) continue;
    for (const j of ADJ[i]) { const y = C[j]; if (y && y.side !== me && x.power > y.power) { const a = { t: 'strike', from: i, to: j }, n = removes(s, j, me) + y.power / 10; if (n > bn) { bn = n; best = a; } } }
  }
  return best || END;
}

// Racer: grows a chain straight at the enemy Base (dearest unit first) and strikes the Base when it
// can destroy it; no other strike, no Cut.
export function racerBot(s) {
  const me = s.turn, P = s.p[me];
  const k = baseKill(s, me); if (k) return k;
  if (coinHelps(P)) return { t: 'coin' };
  const u = dearestUnit(P);
  if (u) { const fr = frontier(s, me); if (fr.length) return { t: 'place', card: u, cell: fr.sort(towardBase(me))[0] }; }
  return END;
}

// A position's worth to `me` as a win chance: pieces (the count decides round 12), power, and how
// close each side's front is to the other's Base.
export function evaluate(s, me) {
  let v = 0;
  for (let i = 0; i < N * N; i++) { const x = s.cells[i]; if (!x || x.base) continue; const w = 1 + 0.25 * x.power + 0.3 * Math.max(0, 4 - dist(i, BASE[1 - x.side])); v += x.side === me ? w : -w; }
  v += 0.6 * (s.p[me].hand.length - s.p[1 - me].hand.length);
  return 1 / (1 + Math.exp(-v / 3));
}

function policy(t, rng, eps) { return rng() < eps ? randomBot(t, rng) : greedyBot(t); }
function rollout(t, me, rng, depth, eps, start) {
  for (let steps = 0; t.winner === null && t.turnNo - start < depth && steps < 600; steps++) _act(t, policy(t, rng, eps));
  if (t.winner === null) return evaluate(t, me);
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}

// Expert: flat Monte Carlo with UCB1 over the distinct actions now (actions that give the same
// position count once). Each play-out deals the unseen cards again, takes the action, and plays on
// with the play-out policy for `depth` turns; an unfinished one is scored by evaluate().
// `playouts` is the budget per action; with `timeMs` it also stops at that time (after at least
// `minPlayouts`), so the page never waits long.
export function mcExpert({ playouts = 3000, depth = 99, eps = 0, C = 0.5, timeMs = 0, minPlayouts = 200 } = {}) {
  return function expert(s, rng) {
    const me = s.turn, opts = [], seen = new Set();
    for (const a of legalActions(s)) {
      const t = clone(s); _act(t, a);
      if (t.winner === me) return a;
      const k = a.t === 'end' ? 'end' : key(t);
      if (!seen.has(k)) { seen.add(k); opts.push({ a, n: 0, w: 0 }); }
    }
    if (opts.length === 1) return opts[0].a;
    const t0 = timeMs ? Date.now() : 0;
    for (let total = 0; ; total++) {
      if (total >= playouts) break;
      if (timeMs && total >= minPlayouts && (total & 15) === 0 && Date.now() - t0 > timeMs) break;
      let o;
      if (total < opts.length) o = opts[total];
      else { let bu = -1; const lg = Math.log(total); for (const x of opts) { const u = x.w / x.n + C * Math.sqrt(lg / x.n); if (u > bu) { bu = u; o = x; } } }
      const t = determinize(s, me, rng), start = t.turnNo; _act(t, o.a);
      o.w += rollout(t, me, rng, depth, eps, start); o.n++;
    }
    let best = opts[0];
    for (const x of opts) if (x.n > best.n || (x.n === best.n && x.w > best.w)) best = x;
    return best.a;
  };
}
export const EXPERT = { playouts: 500, depth: 99, eps: 0, C: 0.5 };
