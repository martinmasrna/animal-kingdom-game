// Toy 6 bots. A round is a small simultaneous game (up to 5 actions each), so a bot
// fills the table of every pair of actions with the value of where that pair leads,
// and plays the mixed strategy that table calls for. Depth is how many rounds ahead
// the table looks. Everything is visible except the choice itself, so no sampling.
import { R, legal, resolve } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const W = { st: 0.4 };
export function evaluate(s, side) {
  if (s.winner !== null) return s.winner === 'draw' ? 0 : s.winner === side ? 1000 : -1000;
  const v = (s.hp[side] - s.hp[1 - side]) + W.st * (s.st[side] - s.st[1 - side]);
  // with a time limit, a health lead is worth more the closer the end is
  return R.timeDecides ? v * (1 + 2 * Math.min(1, (s.round - 1) / R.roundLimit)) : v;
}

// Zero-sum matrix game by regret matching: returns the row mix, the column mix and the value.
export function solve(A, R_, C, iters = 300) {
  const rr = new Float64Array(R_), cr = new Float64Array(C), rs = new Float64Array(R_), cs = new Float64Array(C);
  const x = new Float64Array(R_), y = new Float64Array(C);
  const mix = (reg, out) => { let s = 0; for (let i = 0; i < reg.length; i++) s += reg[i] > 0 ? reg[i] : 0; for (let i = 0; i < reg.length; i++) out[i] = s > 0 ? (reg[i] > 0 ? reg[i] / s : 0) : 1 / reg.length; };
  for (let it = 0; it < iters; it++) {
    mix(rr, x); mix(cr, y);
    let v = 0;
    const ur = new Float64Array(R_), uc = new Float64Array(C);
    for (let r = 0; r < R_; r++) for (let c = 0; c < C; c++) { const a = A[r * C + c]; ur[r] += a * y[c]; uc[c] -= a * x[r]; }
    for (let r = 0; r < R_; r++) v += x[r] * ur[r];
    for (let r = 0; r < R_; r++) { rr[r] = Math.max(0, rr[r] + ur[r] - v); rs[r] += x[r]; }
    for (let c = 0; c < C; c++) { cr[c] = Math.max(0, cr[c] + uc[c] + v); cs[c] += y[c]; }
  }
  let ts = 0, tc = 0; for (const a of rs) ts += a; for (const a of cs) tc += a;
  const X = Array.from(rs, a => a / ts), Y = Array.from(cs, a => a / tc);
  let val = 0; for (let r = 0; r < R_; r++) for (let c = 0; c < C; c++) val += X[r] * Y[c] * A[r * C + c];
  return { x: X, y: Y, v: val };
}

function table(s, side, depth) {
  const mine = legal(s, side), his = legal(s, 1 - side);
  const A = new Float64Array(mine.length * his.length);
  for (let r = 0; r < mine.length; r++) for (let c = 0; c < his.length; c++) {
    const acts = side === 0 ? [mine[r], his[c]] : [his[c], mine[r]];
    A[r * his.length + c] = value(resolve(s, acts), side, depth - 1);
  }
  return { mine, his, A };
}
export function value(s, side, depth) {
  if (s.winner !== null || depth === 0) return evaluate(s, side);
  const { mine, his, A } = table(s, side, depth);
  return solve(A, mine.length, his.length, 120).v;
}
function sample(rng, xs, ps) { let r = rng(); for (let i = 0; i < xs.length; i++) { r -= ps[i]; if (r <= 0) return xs[i]; } return xs[xs.length - 1]; }

export const randomBot = (s, side, rng) => { const l = legal(s, side); return l[Math.floor(rng() * l.length)]; };
// Weak: the best action against an opponent who picks at random, one round ahead.
export const weakBot = (s, side, rng) => {
  const { mine, his, A } = table(s, side, 1);
  let best = [], bv = -Infinity;
  mine.forEach((m, r) => { let v = 0; for (let c = 0; c < his.length; c++) v += A[r * his.length + c] / his.length; if (v > bv + 1e-9) { bv = v; best = [m]; } else if (Math.abs(v - bv) <= 1e-9) best.push(m); });
  return best[Math.floor(rng() * best.length)];
};
// Normal and expert: the equilibrium mix, looking `depth` rounds ahead.
export const mixBot = (depth) => (s, side, rng) => {
  const { mine, his, A } = table(s, side, depth);
  const { x } = solve(A, mine.length, his.length, 400);
  return sample(rng, mine, x);
};
