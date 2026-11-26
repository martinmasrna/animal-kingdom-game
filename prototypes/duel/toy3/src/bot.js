// The Toy 3 bot. A round is a simultaneous blind choice, so the bot treats it as a
// small game: its options against the options of hands the opponent could hold,
// scored one round ahead, solved by regret matching (the opponent gets his own best
// mix per sampled hand). It plays a random draw from the resulting mix, so it can't
// be read by always doing the same thing. It never reads his hand or deck orders.
import { CARDS, DECK, clone, _commit } from './engine.js';

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

export const W = { hand: 0.4, energy: 0.3, sword: 3 };
export function evaluate(s, side) {
  if (s.winner !== null) return s.winner === 'draw' ? 0 : s.winner === side ? 1000 : -1000;
  const P = s.p[side], O = s.p[1 - side];
  return (P.hp - O.hp) + W.hand * (Math.min(P.hand.length, 6) - Math.min(O.hand.length, 6)) + W.energy * (P.mana - O.mana) + W.sword * (P.sword - O.sword);
}

// Every distinct affordable set of cards from a player's hand.
export function sets(s, side) {
  const p = s.p[side];
  const counts = {};
  for (const id of p.hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts);
  const out = [];
  (function rec(i, left, cards, swords) {
    if (i === ids.length) { out.push(cards.slice()); return; }
    const c = CARDS[ids[i]];
    let max = counts[ids[i]];
    if (c.kind === 'Sword') max = p.sword ? 0 : Math.min(max, 1);
    for (let k = 0; k <= max; k++) {
      if (k * c.cost > left) break;
      for (let j = 0; j < k; j++) cards.push(ids[i]);
      rec(i + 1, left - k * c.cost, cards);
      cards.length -= k;
    }
  })(0, p.mana, []);
  return out;
}

function sampleWorld(s, side, rng) {
  const w = clone(s);
  const me = w.p[side], op = w.p[1 - side];
  const left = { ...DECK };
  for (const id of op.played) left[id]--;
  const pool = [];
  for (const [id, k] of Object.entries(left)) for (let i = 0; i < k; i++) pool.push(id);
  shuffle(rng, pool);
  op.hand = pool.slice(0, op.hand.length);
  op.deck = pool.slice(op.hand.length);
  me.deck = shuffle(rng, me.deck.slice());
  w.seed = Math.floor(rng() * 4294967296) | 0;
  return w;
}

function matrix(w, side, rows, cols) {
  const A = new Float64Array(rows.length * cols.length), ch = [null, null];
  for (let r = 0; r < rows.length; r++) for (let c = 0; c < cols.length; c++) {
    ch[side] = rows[r]; ch[1 - side] = cols[c];
    A[r * cols.length + c] = evaluate(_commit(clone(w), ch), side);
  }
  return A;
}

function rm(reg, out) {
  let sum = 0;
  for (let i = 0; i < reg.length; i++) sum += reg[i] > 0 ? reg[i] : 0;
  if (sum <= 0) { out.fill(1 / reg.length); return out; }
  for (let i = 0; i < reg.length; i++) out[i] = reg[i] > 0 ? reg[i] / sum : 0;
  return out;
}
// Rows: the bot. Columns: the opponent, with his own mix per sampled hand.
function solve(mats, R, Cs, iters) {
  const K = mats.length;
  const rReg = new Float64Array(R), rSum = new Float64Array(R), x = new Float64Array(R), u = new Float64Array(R);
  const cReg = Cs.map(C => new Float64Array(C)), ys = Cs.map(C => new Float64Array(C)), v = Cs.map(C => new Float64Array(C));
  for (let it = 1; it <= iters; it++) {
    rm(rReg, x);
    for (let k = 0; k < K; k++) rm(cReg[k], ys[k]);
    u.fill(0);
    for (let k = 0; k < K; k++) {
      const A = mats[k], C = Cs[k], y = ys[k], vk = v[k];
      vk.fill(0);
      for (let r = 0; r < R; r++) {
        let acc = 0; const base = r * C, xr = x[r];
        for (let c = 0; c < C; c++) { const a = A[base + c]; acc += a * y[c]; vk[c] -= xr * a; }
        u[r] += acc / K;
      }
      let ev = 0; for (let c = 0; c < C; c++) ev += y[c] * vk[c];
      for (let c = 0; c < C; c++) { const n = cReg[k][c] + vk[c] - ev; cReg[k][c] = n > 0 ? n : 0; }
    }
    let ev = 0; for (let r = 0; r < R; r++) ev += x[r] * u[r];
    for (let r = 0; r < R; r++) { const n = rReg[r] + u[r] - ev; rReg[r] = n > 0 ? n : 0; rSum[r] += it * x[r]; }
  }
  let tot = 0; for (let r = 0; r < R; r++) tot += rSum[r];
  return Array.from(rSum, a => a / tot);
}

// Keep the `keep` options that score best on average against the other side's options.
function prune(w, side, rows, cols, keep) {
  if (rows.length <= keep && cols.length <= keep) return [rows, cols];
  const A = matrix(w, side, rows, cols), R = rows.length, C = cols.length;
  const rs = rows.map((_, r) => { let m = Infinity, sum = 0; for (let c = 0; c < C; c++) { const a = A[r * C + c]; sum += a; m = Math.min(m, a); } return sum / C + 0.5 * Math.max(m, -500); });
  const cs = cols.map((_, c) => { let m = -Infinity, sum = 0; for (let r = 0; r < R; r++) { const a = A[r * C + c]; sum += a; m = Math.max(m, a); } return -(sum / R) - 0.5 * Math.min(m, 500); });
  const top = (arr, sc) => arr.map((_, i) => i).sort((a, b) => sc[b] - sc[a]).slice(0, keep).map(i => arr[i]);
  const empty = (a) => a.some(x => !x.length) ? a : a.concat([[]]);
  return [rows.length > keep ? empty(top(rows, rs)) : rows, cols.length > keep ? empty(top(cols, cs)) : cols];
}

export function botChoose(s, side, rng, { K = 6, keep = 24, iters = 300 } = {}) {
  const worlds = Array.from({ length: K }, () => sampleWorld(s, side, rng));
  let rows = sets(s, side);
  const colsK = worlds.map(w => sets(w, 1 - side));
  // prune my options once (against the first sampled hand), his per sampled hand
  [rows] = prune(worlds[0], side, rows, colsK[0], keep);
  const cols = worlds.map((w, k) => prune(w, side, rows, colsK[k], keep)[1]);
  const mats = worlds.map((w, k) => matrix(w, side, rows, cols[k]));
  let x = solve(mats, rows.length, cols.map(c => c.length), iters);
  x = x.map(p => (p < 0.03 ? 0 : p));
  const tot = x.reduce((a, b) => a + b, 0) || 1;
  let r = rng() * tot;
  for (let i = 0; i < x.length; i++) { r -= x[i]; if (r <= 0 && x[i] > 0) return rows[i]; }
  return rows[x.indexOf(Math.max(...x))];
}

// Baselines for measuring the bot.
export function greedyChoose(s, side) {
  // biggest total strike damage it can afford, then guards with what is left
  let best = [], bs = -1;
  for (const set of sets(s, side)) {
    const dmg = set.reduce((a, id) => a + (CARDS[id].kind === 'Strike' ? CARDS[id].n : 0), 0);
    const g = set.reduce((a, id) => a + (CARDS[id].kind === 'Guard' ? CARDS[id].n : 0), 0);
    if (dmg * 100 + g > bs) { bs = dmg * 100 + g; best = set; }
  }
  return best;
}
export function randomChoose(s, side, rng) { const o = sets(s, side); return o[Math.floor(rng() * o.length)]; }
