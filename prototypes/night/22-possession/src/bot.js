// Bots for Possession. Each takes (position, its side, rng) and returns the option it chooses. None
// reads the opponent's choice or hand: the Expert deals the opponent's hand again for every sample.

import { OPTS, ATT, DEF, TABLE, ZONES, options, role, inRange, clone, _play, determinize, PLAYS } from './engine.js';

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
export function randomBot(s, side, rng) { const o = options(s, side); return o[Math.floor(rng() * o.length)]; }

// Greedy (the spec's rule): Shoot whenever in range, otherwise the dearest affordable option of its
// side; ties go cards first in a fixed order.
const GREEDY_ATT = ['LONG', 'PASS', 'DRIBBLE', 'WALK'], GREEDY_DEF = ['PRESS', 'TACKLE', 'INTERCEPT', 'BLOCK', 'STAND'];
export function greedyBot(s, side) {
  const o = options(s, side);
  if (o.includes('SHOOT')) return 'SHOOT';
  for (const id of role(s, side) === 'att' ? GREEDY_ATT : GREEDY_DEF) if (o.includes(id)) return id;
  return o[0];
}
// Racer: attacks as hard as it can (Shoot in range, else the longest gain) and never spends on defence.
export function racerBot(s, side) {
  const o = options(s, side);
  if (role(s, side) === 'def') return 'STAND';
  for (const id of ['SHOOT', 'LONG', 'PASS', 'DRIBBLE', 'WALK']) if (o.includes(id)) return id;
  return o[0];
}

// The play-out policy. 'uniform': both sides choose uniformly among their options. 'mix': a rough
// sensible player: in range the attacker shoots half the time and the defender blocks half the
// time; otherwise cards are twice as likely as basics.
function pickMix(t, side, rng) {
  const o = options(t, side), r = role(t, side), att = t.poss;
  if (r === 'att' && o.includes('SHOOT')) return rng() < 0.5 ? 'SHOOT' : pickW(o.filter(x => x !== 'SHOOT'), rng);
  if (r === 'def' && inRange(t, att) && o.includes('BLOCK')) return rng() < 0.5 ? 'BLOCK' : pickW(o.filter(x => x !== 'BLOCK'), rng);
  return pickW(o, rng);
}
function pickW(o, rng) {
  let z = 0; for (const x of o) z += OPTS[x].basic ? 1 : 2;
  let r = rng() * z; for (const x of o) { r -= OPTS[x].basic ? 1 : 2; if (r <= 0) return x; } return o[o.length - 1];
}
function rollout(t, me, rng, pol) {
  while (t.winner === null) {
    if (pol === 'mix') _play(t, [pickMix(t, 0, rng), pickMix(t, 1, rng)]);
    else { const a = options(t, 0), b = options(t, 1); _play(t, [a[Math.floor(rng() * a.length)], b[Math.floor(rng() * b.length)]]); }
  }
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}

// Expert: the spec's matrix-game player. It samples `dets` deals of the opponent's hidden hand; for
// each deal it estimates every pair (my option, his option) by `reps` play-outs of the rest of the
// match; then it solves the resulting game of incomplete information (my one mixed strategy against
// a mixed strategy of his for each deal) by regret matching, and samples its option from the
// average strategy. It never sees his choice.
const PURIFY = 0.1;
// My options that no other option of mine beats outright: one that does at least as well against
// every option he may have, for no more stamina, makes it pointless.
function outcomeFor(s, me, mine, his) {
  const att = s.poss === me, a = att ? mine : his, d = att ? his : mine, r = TABLE[a][d];
  const room = s.poss === 0 ? ZONES - 1 - s.ball : s.ball;
  const v = r === 'G' ? 100 : r === 'T' ? -100 : Math.min(r, room);
  return att ? v : -v;
}
function undominated(s, me, mine, his) {
  return mine.filter(i => !mine.some(k => {
    if (k === i || OPTS[k].cost > OPTS[i].cost) return false;
    let strict = OPTS[k].cost < OPTS[i].cost;
    for (const j of his) { const a = outcomeFor(s, me, k, j), b = outcomeFor(s, me, i, j); if (a < b) return false; if (a > b) strict = true; }
    return strict;
  }));
}
export function matrixExpert({ dets = 8, reps = 12, iters = 1000, pol = 'uniform', vsUniform = false, read = true, K = 1, margin = 0.01 } = {}) {
  return function expert(s, me, rng) {
    const deals = [];
    for (let d = 0; d < dets; d++) { const base = determinize(s, me, rng); deals.push({ base, his: options(base, 1 - me) }); }
    const mine = undominated(s, me, options(s, me), [...new Set(deals.flatMap(d => d.his))]);
    if (mine.length === 1) return mine[0];
    const D = [];
    for (const { base, his } of deals) {
      // the same `reps` futures for every pair (common random numbers), so the pairs differ
      // only by what the choices themselves change
      const seeds = Array.from({ length: reps }, () => (rng() * 4294967296) >>> 0);
      const M = mine.map(a => his.map(b => {
        let w = 0;
        for (let r = 0; r < reps; r++) {
          const rr = makeRng(seeds[r]), t = clone(base); shuffle(t.p[0].deck, rr); shuffle(t.p[1].deck, rr); t.seed = seeds[r]; // his hand stays this deal's
          _play(t, me === 0 ? [a, b] : [b, a]); w += rollout(t, me, rr, pol);
        }
        return w / reps;
      }));
      D.push({ his, M });
    }
    if (vsUniform) { // diagnostic only: best reply to an opponent who picks uniformly
      let bi = 0, bv = -1;
      for (let i = 0; i < mine.length; i++) { let v = 0; for (const d of D) v += d.M[i].reduce((a, b) => a + b, 0) / d.his.length; if (v > bv) { bv = v; bi = i; } }
      return mine[bi];
    }
    // regret matching: x over my options; y[d] over his options in deal d
    const n = mine.length, R = new Float64Array(n), X = new Float64Array(n);
    for (const d of D) { d.R = new Float64Array(d.his.length); d.Y = new Float64Array(d.his.length); }
    const strat = (Rg) => { let z = 0; for (const r of Rg) z += Math.max(0, r); return Array.from(Rg, r => z > 0 ? Math.max(0, r) / z : 1 / Rg.length); };
    for (let it = 0; it < iters; it++) {
      const x = strat(R), ys = D.map(d => strat(d.R));
      const u = new Float64Array(n);
      D.forEach((d, k) => { for (let i = 0; i < n; i++) for (let j = 0; j < d.his.length; j++) u[i] += d.M[i][j] * ys[k][j] / D.length; });
      let ux = 0; for (let i = 0; i < n; i++) ux += x[i] * u[i];
      for (let i = 0; i < n; i++) { R[i] += u[i] - ux; X[i] += x[i]; }
      D.forEach((d, k) => {
        const m = d.his.length, v = new Float64Array(m);
        for (let j = 0; j < m; j++) for (let i = 0; i < n; i++) v[j] += x[i] * (1 - d.M[i][j]);
        let vy = 0; for (let j = 0; j < m; j++) vy += ys[k][j] * v[j];
        for (let j = 0; j < m; j++) { d.R[j] += v[j] - vy; d.Y[j] += ys[k][j]; }
      });
    }
    // drop the options the average strategy plays rarely (left over from early iterations)
    let z = 0; for (const v of X) z += v;
    for (let i = 0; i < n; i++) if (X[i] < PURIFY * z) X[i] = 0;
    z = 0; for (const v of X) z += v;
    if (read) {
      // Reading: what he chose before in this situation (his role, ball in range or not), from
      // the revealed plays only, pulls the forecast of his choice away from the equilibrium.
      // Play the best reply to that forecast when it clearly beats the equilibrium mix.
      const opp = 1 - me, oppAtt = s.poss === opp, ctx = inRange(s, s.poss), cnt = {};
      for (const h of s.hist) if ((h.att === opp) === oppAtt && h.r === ctx) { const c = oppAtt ? h.a : h.d; cnt[c] = (cnt[c] || 0) + 1; }
      const ev = new Float64Array(n);
      for (const d of D) {
        const m = d.his.length; let zy = 0; for (const v of d.Y) zy += v;
        let zc = 0; for (const id of d.his) zc += cnt[id] || 0;
        const q = d.his.map((id, j) => ((cnt[id] || 0) + K * d.Y[j] / zy) / (zc + K));
        for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) ev[i] += d.M[i][j] * q[j] / D.length;
      }
      let evEq = 0, bi = 0; for (let i = 0; i < n; i++) { evEq += ev[i] * X[i] / z; if (ev[i] > ev[bi]) bi = i; }
      if (ev[bi] > evEq + margin) return mine[bi];
    }
    let r = rng() * z;
    for (let i = 0; i < n; i++) { r -= X[i]; if (r <= 0) return mine[i]; }
    return mine[n - 1];
  };
}
export const EXPERT = { dets: 8, reps: 12, iters: 1000, read: true, K: 1, margin: 0.01 };
export const mcExpert = matrixExpert;
