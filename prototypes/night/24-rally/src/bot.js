// Bots for 24 Rally. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles the opponent's hand with his deck, and its own deck,
// before each play-out (played shots and discard piles are public).

import { CARDS, POINTS, GAMES, clone, _act, legalActions, actionKey } from './engine.js';

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
const shots = (s) => legalActions(s).filter(a => a.t === 'shot');

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ Greedy
// serves and returns with the highest-Pace shot it can legally play and afford (the cheaper on a tie)
export function greedyBot(s) {
  const L = shots(s);
  if (!L.length) return { t: 'concede' };
  return L.sort((a, b) => CARDS[b.card].pace - CARDS[a.card].pace || CARDS[a.card].cost - CARDS[b.card].cost || CARDS[b.card].reach - CARDS[a.card].reach)[0];
}
// ------------------------------------------------------------------ Saver
// the other fixed rule: always the cheapest legal shot (the faster on a tie), so stamina never runs dry
export function saverBot(s) {
  const L = shots(s);
  if (!L.length) return { t: 'concede' };
  return L.sort((a, b) => CARDS[a.card].cost - CARDS[b.card].cost || CARDS[b.card].pace - CARDS[a.card].pace)[0];
}

// ------------------------------------------------------------------ Expert
// Determinized play-outs: each candidate shot (or letting the ball go) is followed by a play-out
// in which both sides play Saver's shot (MIX sets the shares of Greedy's, Saver's and any legal
// shot; Saver is the strongest fixed rule here, it beats Greedy 79%), to the end of the current game, on a world where the cards this side cannot see are reshuffled; the
// game's result is turned into a match-win chance from the games score (later games even).
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  t.seed = (rng() * 4294967296) >>> 0;
  return t;
}
// chance to take the match from games (a, b) when every game left is even
const MW = [];
for (let a = GAMES; a >= 0; a--) { MW[a] = []; for (let b = GAMES; b >= 0; b--) MW[a][b] = a >= GAMES ? 1 : b >= GAMES ? 0 : 0.5 * (MW[a + 1] ? MW[a + 1][b] : 1) + 0.5 * MW[a][b + 1]; }
export const matchChance = (s, me) => s.winner === me ? 1 : s.winner !== null ? 0 : MW[s.p[me].games][s.p[1 - me].games];
export function playoutBot(t, rng, mix = [0.4, 0.8]) {
  const r = rng();
  if (r < mix[0]) return greedyBot(t);
  if (r < mix[1]) return saverBot(t);
  const L = shots(t);
  return L.length ? pick(L, rng) : { t: 'concede' };
}
function rollout(t, me, gameNo, rng, mix) {
  let steps = 0;
  while (t.winner === null && t.gameNo === gameNo && steps < 400) { _act(t, playoutBot(t, rng, mix)); steps++; }
  return matchChance(t, me);
}

// every candidate gets the same play-outs (there are at most six); among the candidates within TIE
// of the best, one that wins the point on the spot comes first, then the cheaper shot
export const EXPERT = { playouts: 600, mix: [0, 1], tie: 0.03 };
export function expertBot({ playouts = 300, mix = [0.4, 0.8], tie = 0.03, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = legalActions(s);
    if (arms.length === 1) return arms[0];
    const st = arms.map(a => { const t = clone(s); _act(t, a); return { a, w: 0, n: 0, now: t.winner === me || t.p[me].points > s.p[me].points || t.p[me].games > s.p[me].games }; });
    const t0 = timeMs ? Date.now() : 0;
    for (let i = 0; i < playouts; i++) {
      const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
      for (const x of st) { const t = clone(world); _act(t, x.a); x.w += rollout(t, me, s.gameNo, makeRng(seed), mix); x.n++; }
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    const best = Math.max(...st.map(x => x.w / x.n));
    const near = st.filter(x => x.w / x.n >= best - tie);
    near.sort((x, y) => (y.now - x.now) || (cost(x.a) - cost(y.a)) || (y.w / y.n - x.w / x.n));
    return near[0].a;
  };
}
const cost = (a) => a.t === 'shot' ? CARDS[a.card].cost : 99;
