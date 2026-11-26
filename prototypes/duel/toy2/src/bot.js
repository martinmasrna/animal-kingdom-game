// The Toy 2 bot. For each thing it could do now (pass or play a card) it samples
// hands the opponent could hold, plays the rest of the round out with a one-step
// greedy policy for both sides, and keeps the option with the best average result.
// It never reads his hand or either deck order.
import { CARDS, DECK, clone, _act, legalActions } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle(rng, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

export const W = { hand: 0.4, energy: 0.3, sword: 3, aggression: 0.2 };
export function evaluate(s, side) {
  if (s.winner !== null) return s.winner === 'draw' ? 0 : s.winner === side ? 1000 : -1000;
  const P = s.p[side], O = s.p[1 - side];
  return (P.hp - O.hp) + W.aggression * (P.maxHp - O.hp) + W.hand * (Math.min(P.hand.length, 6) - Math.min(O.hand.length, 6)) + W.energy * (P.mana - O.mana) + W.sword * (P.sword - O.sword);
}

// A world consistent with what `side` can see: his hand and both deck orders drawn at random.
function sampleWorld(s, side, rng) {
  const w = clone(s);
  const me = w.p[side], op = w.p[1 - side];
  const left = { ...DECK };
  for (const id of op.played.concat(op.line)) left[id]--;
  const pool = [];
  for (const [id, k] of Object.entries(left)) for (let i = 0; i < k; i++) pool.push(id);
  shuffle(rng, pool);
  op.hand = pool.slice(0, op.hand.length);
  op.deck = pool.slice(op.hand.length);
  me.deck = shuffle(rng, me.deck.slice());
  w.seed = Math.floor(rng() * 4294967296) | 0;
  return w;
}

// Finish the round as if both players passed from here.
function settle(t) { const r = t.round; while (t.winner === null && t.round === r) _act(t, null); return t; }

// Rollout policy: the option that looks best if both pass right after it.
function greedyStep(t) {
  const side = t.toAct;
  let best = null, bv = -Infinity;
  for (const a of legalActions(t)) {
    const v = evaluate(settle(_act(clone(t), a)), side);
    if (v > bv) { bv = v; best = a; }
  }
  return best;
}
function rollout(t, side) {
  const r = t.round;
  while (t.winner === null && t.round === r) _act(t, greedyStep(t));
  return evaluate(t, side);
}

export function botAct(s, rng, K = 12) {
  const side = s.toAct;
  const opts = legalActions(s);
  if (opts.length === 1) return null;
  const worlds = Array.from({ length: K }, () => sampleWorld(s, side, rng));
  let best = null, bv = -Infinity;
  for (const a of opts) {
    let v = 0;
    for (const w of worlds) v += rollout(_act(clone(w), a), side) / K;
    if (v > bv + 1e-9) { bv = v; best = a; }
  }
  return best;
}

// Baselines for measuring the bot.
export function greedyAct(s) { return greedyStep(clone(s)); }
export function randomAct(s, rng) { const o = legalActions(s); return rng() < 0.3 ? null : o[Math.floor(rng() * o.length)]; }
