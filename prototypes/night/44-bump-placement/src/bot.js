// Bots for 44 Bump placement. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles the opponent's hand with his deck, and its own deck,
// before each play-out (discard piles are public).

import { CARDS, SPACES, TARGET, clone, _act, act, legalActions, actionKey, canPlace, shoveTargets } from './engine.js';

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
const PRIORITY = [0, 2, 1, 3, 4]; // Score 3, Study, Score 1, Fund, Sabotage

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// the weakest card goes first when discarding down
function discardWeakest(s) {
  const P = s.p[s.toAct];
  let w = P.hand[0];
  for (const id of P.hand) if (CARDS[id].str < CARDS[w].str || (CARDS[id].str === CARDS[w].str && CARDS[id].cost < CARDS[w].cost)) w = id;
  return { t: 'discard', card: w };
}
// Shove's push: the strongest enemy card it can reach, the better space first
function shoveTgt(s, me, k) {
  const tg = shoveTargets(s, me, k);
  if (!tg.length) return -1;
  return tg.sort((a, b) => CARDS[s.spaces[b].card].str - CARDS[s.spaces[a].card].str || PRIORITY.indexOf(a) - PRIORITY.indexOf(b))[0];
}
const placeAct = (s, me, id, k) => CARDS[id].shove ? { t: 'place', card: id, space: k, tgt: shoveTgt(s, me, k) } : { t: 'place', card: id, space: k };

// ------------------------------------------------------------------ Greedy
// its strongest affordable card on the best space it can take (Score 3, Study, Score 1, Fund,
// Sabotage); passes when it can place nothing
export function greedyBot(s) {
  if (s.phase === 'discard') return discardWeakest(s);
  const me = s.toAct, P = s.p[me];
  const ids = [...new Set(P.hand)].sort((a, b) => CARDS[b].str - CARDS[a].str || CARDS[a].cost - CARDS[b].cost);
  for (const k of PRIORITY) for (const id of ids) if (canPlace(s, me, id, k)) return placeAct(s, me, id, k);
  return { t: 'pass' };
}

// ------------------------------------------------------------------ Racer
// points only: takes Score 3, else Score 1, with its cheapest card that can; ignores every other space
export function racerBot(s) {
  if (s.phase === 'discard') return discardWeakest(s);
  const me = s.toAct, P = s.p[me];
  const ids = [...new Set(P.hand)].sort((a, b) => CARDS[a].cost - CARDS[b].cost || CARDS[b].str - CARDS[a].str);
  for (const k of [0, 1]) for (const id of ids) if (canPlace(s, me, id, k)) return placeAct(s, me, id, k);
  return { t: 'pass' };
}

// ------------------------------------------------------------------ evaluation
// a position's worth to `me`: points (more as 20 nears), cards in hand, Fund for next round, and
// what each space it holds will pay, discounted while the opponent can still place
export const W = { pt: 1, near: 0.15, card: 0.55, fund: 1.0, hold: 0.8 };
const PAY = [3, 1 + 0.55, 1.1, 1.0, 0.5];
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1;
    let x = W.pt * P.points + W.near * Math.max(0, P.points - (TARGET - 8)) + W.card * P.hand.length + (P.fund ? W.fund : 0);
    s.spaces.forEach((sp, k) => { if (sp && sp.side === side) x += PAY[k] * (s.p[1 - side].passed ? 1 : W.hold); });
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 3));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: each candidate action is followed by Greedy on both sides (a share of
// random moves) to the start of round +DEPTH for every candidate alike, on a world where the cards
// this side cannot see are reshuffled, then scored as a win chance; successive halving spends the
// play-outs on the leaders, and the one-ply worth breaks near-ties.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  t.seed = (rng() * 4294967296) >>> 0; // the Sabotage draws and reshuffles to come
  return t;
}
function rollout(t, me, start, depth, rng, eps) {
  let steps = 0;
  while (t.winner === null && t.round - start < depth && steps < 400) {
    const a = eps > 0 && rng() < eps ? randomBot(t, rng) : greedyBot(t);
    _act(t, a); steps++;
  }
  return winProb(t, me);
}
export function candidates(s, keep = 12, withPrior = false) {
  const me = s.toAct;
  const seen = new Set(), all = [];
  for (const a of legalActions(s)) { const k = actionKey(a); if (!seen.has(k)) { seen.add(k); all.push(a); } }
  const scored = all.map(a => ({ a, v: evaluate(act(s, a), me) })).sort((x, y) => y.v - x.v);
  let out = scored;
  if (scored.length > keep) {
    const g = actionKey(greedyBot(s));
    out = scored.slice(0, keep);
    for (const x of scored.slice(keep)) if (x.a.t === 'pass' || actionKey(x.a) === g) out.push(x);
  }
  return withPrior ? out.map(x => ({ a: x.a, prior: 1 / (1 + Math.exp(-x.v / 3)) })) : out.map(x => x.a);
}

export const EXPERT = { playouts: 400, depth: 2, eps: 0.05, keep: 12, beta: 0.5 };
export function expertBot({ playouts = 400, depth = 2, eps = 0.05, keep = 12, beta = 0.5, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s, keep, true);
    if (arms.length === 1) return arms[0].a;
    let alive = arms.map(({ a, prior }) => ({ a, w: 0, n: 0, b: beta * prior }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, s.round, depth, makeRng(seed), eps); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => (y.w / y.n + y.b) - (x.w / x.n + x.b));
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
