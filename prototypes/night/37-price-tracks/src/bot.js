// Bots for 37 Price tracks. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert keeps the cards a Spy has shown (and that are still in that
// hand) and reshuffles everything else its side cannot see before each play-out.

import { CARDS, GOODS, PMAX, TARGET, clone, _act, act, legalActions, actionKey, counts } from './engine.js';

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
const can = (P, id) => P.hand.includes(id) && CARDS[id].cost <= P.coin;

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ Greedy
// sells the type with the highest price times count in hand, Boosting it first when it can; with
// coin left, Crashes the dearest good it holds none of, and Spies.
function bestType(s, P) {
  const c = counts(P.hand); let best = null, bv = 0;
  for (const g of GOODS) { const v = s.price[g] * c[g]; if (v > bv || (v === bv && best && c[g] > c[best])) { bv = v; best = c[g] ? g : best; } }
  return best;
}
function sellStep(s) {
  const P = s.p[s.toAct];
  if (P.sold) return null;
  const g = bestType(s, P); if (!g) return null;
  if (can(P, 'BOO') && s.price[g] < PMAX) return { t: 'play', card: 'BOO', good: g };
  return { t: 'sell', good: g, n: counts(P.hand)[g] };
}
export function greedyBot(s) {
  const P = s.p[s.toAct];
  const sl = sellStep(s); if (sl) return sl;
  if (can(P, 'CRA')) { const c = counts(P.hand); const g = GOODS.filter(x => !c[x]).sort((a, b) => s.price[b] - s.price[a])[0]; if (g && s.price[g] > 1) return { t: 'play', card: 'CRA', good: g }; }
  if (can(P, 'SPY')) return { t: 'play', card: 'SPY' };
  return { t: 'end' };
}
// ------------------------------------------------------------------ Racer
// sells every turn like Greedy and never plays Crash
export function racerBot(s) {
  const P = s.p[s.toAct];
  const sl = sellStep(s); if (sl) return sl;
  if (can(P, 'SPY')) return { t: 'play', card: 'SPY' };
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation (for play-outs cut short)
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  const worth = (P) => { const c = counts(P.hand); return P.pts + 0.6 * GOODS.reduce((x, g) => x + c[g] * s.price[g], 0) + 0.8 * P.coin; };
  return worth(s.p[me]) - worth(s.p[1 - me]);
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: every candidate action is followed by a play-out on a world where the
// cards this side cannot see are reshuffled (the opponent's Spied cards stay in his hand); both
// sides play Greedy or Racer (drawn per play-out) with a little noise, to the end of the match;
// successive halving spends the play-outs on the leaders, every arm seeing the same worlds.
function determinize(s, me, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - me];
  const pool = O.hand.concat(O.deck);
  for (const id of O.seen) pool.splice(pool.indexOf(id), 1);
  shuffle(pool, rng);
  const free = O.hand.length - O.seen.length;
  O.hand = O.seen.concat(pool.slice(0, free)); O.deck = pool.slice(free);
  shuffle(t.p[me].deck, rng);
  return t;
}
export function candidates(s) {
  const seen = new Set(), out = [];
  for (const a of legalActions(s)) { const k = actionKey(a); if (!seen.has(k)) { seen.add(k); out.push(a); } }
  return out;
}
function policy(t, rng, eps, style) {
  if (eps > 0 && rng() < eps) return pick(candidates(t), rng);
  return style[t.toAct] === 'r' ? racerBot(t) : greedyBot(t);
}
function rollout(t, me, rng, eps) {
  const style = [rng() < 0.5 ? 'r' : 'g', rng() < 0.5 ? 'r' : 'g'];
  let steps = 0;
  while (t.winner === null && steps < 800) { _act(t, policy(t, rng, eps, style)); steps++; }
  return winProb(t, me);
}
// Whole turns: every sequence of sells and plays this turn (a Spy ends a sequence, since what it
// shows changes what comes after), told apart by the position it leaves; each is scored by
// determinized play-outs from there, the same worlds for every plan.
const posKey = (t) => JSON.stringify([t.toAct, t.winner, t.round, t.price, t.p.map(p => [p.pts, p.coin, p.hand.slice().sort().join(), p.seen.length])]);
function turnPlans(s, cap = 4000) {
  const me = s.toAct, out = new Map();
  let nodes = 0;
  const rec = (t, first) => {
    if (++nodes > cap) return;
    for (const a of candidates(t)) {
      const x = act(t, a), f = first || a;
      if (a.t === 'end' || (a.t === 'play' && a.card === 'SPY') || x.winner !== null || x.toAct !== me) {
        const k = posKey(x) + (a.card === 'SPY' ? 's' : '');
        if (!out.has(k)) out.set(k, { first: f, t: x });
        continue;
      }
      rec(x, f);
    }
  };
  rec(s, null);
  return [...out.values()];
}
export const EXPERT = { playouts: 2000, eps: 0.08 };
export function expertBot({ playouts = 2000, eps = 0.08, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms0 = candidates(s);
    if (arms0.length === 1) return arms0[0];
    const plans = turnPlans(s);
    let alive = plans.map(p => ({ p, w: 0, n: 0 }));
    if (alive.length === 1) return alive[0].p.first;
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(3, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const seed = (rng() * 4294967296) >>> 0, wseed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = determinize(st.p.t, me, makeRng(wseed)); st.w += rollout(t, me, makeRng(seed), eps); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      if (timeMs && Date.now() - t0 > timeMs) break;
      alive = alive.slice(0, Math.ceil(alive.length / 2));
    }
    return alive[0].p.first;
  };
}
