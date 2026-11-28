// Bots for Showdown. None reads a hidden card: the Expert deals the opponent's hand, deck and
// line afresh for every play-out, keeping the line consistent with the mana it was shown to cost.

import { CARDS, MANA, BET, clone, step, key, legalActions, lines, lineCost, linePower } from './engine.js';

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

// a line's power as its owner can judge it before seeing the other line (a Mirror counted as 5)
export const MIRROR_GUESS = 5;
export function estPower(line) {
  let t = 0;
  for (const id of line) t += id === 'SO' ? (line.length === 1 ? 4 : 0) : id === 'MR' ? MIRROR_GUESS : CARDS[id].power;
  return t;
}
// the most powerful line a hand can buy (the cheaper one on a tie)
export function bestLine(hand) {
  let best = [], bv = -1, bc = 99;
  for (const l of lines(hand)) { const v = estPower(l), c = lineCost(l); if (v > bv || (v === bv && c < bc)) { bv = v; bc = c; best = l; } }
  return best;
}

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }
// Greedy (the spec's): buys the most powerful line it can afford; bets or raises with power 9 or
// more, otherwise checks and always calls.
export function greedyBot(s) {
  if (s.phase === 'buy') return { t: 'buy', line: bestLine(s.p[s.toMove].hand) };
  const P = s.p[s.toMove], f = s.p[1 - s.toMove].contrib - P.contrib, strong = estPower(P.line) >= 9;
  if (f === 0) return strong && P.chips >= BET ? { t: 'bet' } : { t: 'check' };
  if (strong && !P.raised && P.chips >= f + BET) return { t: 'raise' };
  return { t: 'call' };
}
// Caller: buys like Greedy, never bets, always calls.
export function callerBot(s) {
  if (s.phase === 'buy') return { t: 'buy', line: bestLine(s.p[s.toMove].hand) };
  const f = s.p[1 - s.toMove].contrib - s.p[s.toMove].contrib;
  return f === 0 ? { t: 'check' } : { t: 'call' };
}

// ------------------------------------------------------------------ Expert: determinized play-outs
// How the Expert expects anyone to buy: mostly the strongest lines (weights by estimated power),
// sometimes anything (a bluff, a cheap line to keep cards).
function modelLine(hand, rng, cands = lines(hand)) {
  if (!cands.length) return null;
  if (rng() < 0.15) return pickOf(cands, rng);
  let tot = 0; const w = cands.map(l => { const x = Math.exp(estPower(l) / 1.5); tot += x; return x; });
  let r = rng() * tot;
  for (let i = 0; i < cands.length; i++) { r -= w[i]; if (r <= 0) return cands[i]; }
  return cands[cands.length - 1];
}
// How the Expert expects anyone to bet: by the margin of its own line over what the other's
// spend usually buys, with some noise.
function policy(s, rng) {
  if (s.phase === 'buy') return { t: 'buy', line: modelLine(s.p[s.toMove].hand, rng) };
  const acts = legalActions(s);
  if (rng() < 0.08) return pickOf(acts, rng);
  const me = s.toMove, P = s.p[me], O = s.p[1 - me], f = O.contrib - P.contrib;
  const margin = estPower(P.line) - (1.5 + 2 * O.spent);
  const has = (t) => acts.some(a => a.t === t);
  if (margin >= 3) return { t: has('raise') ? 'raise' : has('bet') ? 'bet' : f ? 'call' : 'check' };
  if (f === 0) return { t: 'check' };
  if (margin >= -1) return { t: 'call' };
  return { t: rng() < 0.6 ? 'fold' : 'call' };
}
// a world consistent with what `me` has seen: the opponent's unseen cards dealt again into hand,
// line (same size, and the same cost once the spends are shown) and deck
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], M = t.p[me];
  shuffle(M.deck, rng);
  const seenDisc = O.discard.slice(); for (const id of O.unseen) seenDisc.splice(seenDisc.indexOf(id), 1);
  const pool = [...O.deck, ...O.hand, ...(O.line || []), ...O.unseen];
  const H = O.hand.length, L = O.line ? O.line.length : 0, costKnown = t.phase === 'bet' && O.line;
  let hand = null, line = null;
  for (let tries = 0; tries < 40 && hand === null; tries++) {
    shuffle(pool, rng);
    const pre = pool.slice(0, H + L);
    if (!O.line) { hand = pre; line = null; break; }
    const ok = lines(pre).filter(l => l.length === L && (!costKnown || lineCost(l) === O.spent));
    if (!ok.length) continue;
    line = modelLine(pre, rng, ok); hand = pre.slice(); for (const id of line) hand.splice(hand.indexOf(id), 1);
  }
  if (hand === null) {
    // no dealt hand could have bought that line: draw the line straight from the unseen cards
    const ok = lines(pool).filter(l => l.length === L && (!costKnown || lineCost(l) === O.spent));
    line = ok.length ? modelLine(pool, rng, ok) : pool.slice(0, L);
    const rest = pool.slice(); for (const id of line) rest.splice(rest.indexOf(id), 1);
    shuffle(rest, rng); hand = rest.slice(0, H);
  }
  const used = hand.concat(line || []), rest = pool.slice(); for (const id of used) rest.splice(rest.indexOf(id), 1);
  shuffle(rest, rng);
  O.hand = hand; O.line = line; O.unseen = rest.slice(0, O.unseen.length); O.deck = rest.slice(O.unseen.length); O.discard = seenDisc.concat(O.unseen);
  return t;
}
// the end of the play-out: the round in progress and the next one, or the end of the game
function playout(t, rng, rounds) {
  const stop = t.round + rounds;
  let guard = 0;
  while (t.winner === null && t.round < stop && guard++ < 400) step(t, policy(t, rng));
  return t;
}
function scoreFor(t, me, base) {
  if (t.winner !== null) return t.winner === me ? 40 : t.winner === 'draw' ? 0 : -40;
  return (t.p[me].chips - t.p[1 - me].chips) - base;
}
export function rolloutBot({ R = 200, rounds = 2 } = {}) {
  return (s, rng) => {
    const me = s.toMove, acts = legalActions(s);
    if (acts.length === 1) return acts[0];
    const base = s.p[me].chips - s.p[1 - me].chips;
    const seeds = Array.from({ length: R }, () => (rng() * 4294967296) >>> 0);
    let best = acts[0], bv = -Infinity;
    for (const a of acts) {
      let tot = 0;
      for (let r = 0; r < R; r++) {
        const wr = makeRng(seeds[r]);
        const t = determinize(s, me, wr);
        t.seed = (wr() * 4294967296) >>> 0;
        step(t, a);
        tot += scoreFor(playout(t, wr, rounds), me, base);
      }
      if (tot > bv + 1e-9) { bv = tot; best = a; }
    }
    return best;
  };
}
export const EXPERT = { R: 200, rounds: 2 };
export function expertBot(opts = EXPERT) { return rolloutBot(opts); }

export const TRIVIAL = { random: randomBot, greedy: greedyBot, caller: callerBot };
export function meaning(s, a) { return key(a); }
