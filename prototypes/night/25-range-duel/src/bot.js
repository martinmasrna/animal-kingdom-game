// Bots for 25 Range duel. Each is a function (state, side, rng) -> the move that side submits this
// turn. Bots are asked before either move is in, so none sees the other's choice; Expert also
// reshuffles every card it cannot see.

import { CARDS, SPACES, clone, _submit, legalActions, dist } from './engine.js';

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
const STEP_IN = { t: 'move', card: 'STEP', dir: 1 }, STEP_OUT = { t: 'move', card: 'STEP', dir: -1 }, REST = { t: 'move', card: 'REST' };

// the distance after a card's own movement, if the other fighter stands still
function distAfter(s, side, id) {
  const c = CARDS[id], d = dist(s), me = s.p[side].pos, o = s.p[1 - side].pos;
  if (!c.mv) return d;
  if (c.mv > 0) return Math.max(1, d - c.mv);
  const away = Math.sign(me - o), np = Math.max(1, Math.min(SPACES, me + away * -c.mv));
  return Math.abs(np - o);
}
export const hitsStill = (s, side, id) => { const c = CARDS[id]; if (!c.dmg) return false; const d = distAfter(s, side, id); return d >= c.rng[0] && d <= c.rng[1]; };

// ------------------------------------------------------------------ Random
export function randomBot(s, side, rng) { const L = legalActions(s, side); return L[Math.floor(rng() * L.length)]; }
// ------------------------------------------------------------------ Greedy
// the highest-damage move that hits if the opponent stays where it is (the faster on a tie);
// Step toward when none does
export function greedyBot(s, side) {
  let best = null;
  for (const a of legalActions(s, side)) {
    const c = CARDS[a.card];
    if (c.basic || !hitsStill(s, side, a.card)) continue;
    if (!best || c.dmg > CARDS[best.card].dmg || (c.dmg === CARDS[best.card].dmg && c.speed < CARDS[best.card].speed)) best = a;
  }
  return best || STEP_IN;
}

// ------------------------------------------------------------------ Expert
// Each turn is a matrix game: my moves against every move the opponent could make. Each cell is
// estimated by play-outs on worlds where the cards this side cannot see are reshuffled (and the
// opponent is dealt the card of the column). Expert plays the equilibrium mix of that matrix, and
// once it has watched the opponent at this distance, the best answer to what the opponent does there.
// play-out policy: mostly the best hit at the current distance, otherwise close in or rest, with noise
function policy(s, side, rng) {
  const P = s.p[side], d = dist(s);
  if (rng() < 0.25) {
    const k = Math.floor(rng() * (P.hand.length + 3));
    if (k < P.hand.length && CARDS[P.hand[k]].cost <= P.energy) return { t: 'move', card: P.hand[k] };
    return k % 3 === 0 ? STEP_IN : k % 3 === 1 ? STEP_OUT : REST;
  }
  if (rng() < 0.85) {
    let best = null;
    for (const id of P.hand) {
      const c = CARDS[id];
      if (c.cost > P.energy || !c.dmg || !hitsStill(s, side, id)) continue;
      if (!best || c.dmg > CARDS[best].dmg || (c.dmg === CARDS[best].dmg && c.speed < CARDS[best].speed) || rng() < 0.2) best = id;
    }
    if (best) return { t: 'move', card: best };
  }
  if (P.energy <= 1 && rng() < 0.5) return REST;
  return d > 1 ? STEP_IN : (rng() < 0.5 ? STEP_OUT : REST);
}
function runOut(t, rng) {
  while (t.winner === null) { const a0 = policy(t, 0, rng), a1 = policy(t, 1, rng); _submit(t, 0, a0); _submit(t, 1, a1); }
}
function score(t, me) {
  const w = t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
  const m = t.p[me].life - t.p[1 - me].life;
  return 0.7 * w + 0.3 / (1 + Math.exp(-m / 3));
}
// a world where the cards this side cannot see are reshuffled; `need` is dealt into the opponent's hand
function determinize(s, me, rng, need) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  if (need) { const k = pool.indexOf(need); if (k >= O.hand.length) { const x = pool[0]; pool[0] = pool[k]; pool[k] = x; } }
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
export const moveKey = (a) => a.card + (a.dir ? (a.dir > 0 ? '+' : '-') : '');
// zero-sum matrix game by fictitious play: both sides' mixed strategies
export function solve(A, iters = 800) {
  const R = A.length, C = A[0].length, rc = new Float64Array(R), cc = new Float64Array(C), rs = new Float64Array(R), cs = new Float64Array(C);
  let r = 0, c = 0;
  for (let it = 0; it < iters; it++) {
    rc[r]++; cc[c]++;
    for (let j = 0; j < C; j++) cs[j] += A[r][j];
    for (let i = 0; i < R; i++) rs[i] += A[i][c];
    r = 0; for (let i = 1; i < R; i++) if (rs[i] > rs[r]) r = i;
    c = 0; for (let j = 1; j < C; j++) if (cs[j] < cs[c]) c = j;
  }
  return { row: Array.from(rc, x => x / iters), col: Array.from(cc, x => x / iters) };
}
// a card that does nothing this turn whatever the opponent does: it does not move, and either it
// cannot reach any distance the opponent can step to, or it is a Guard and nothing of his can reach
function pointless(s, me, id) {
  const c = CARDS[id];
  if (c.mv) return false;
  const d = dist(s), reach = new Set();
  for (const k of [-2, -1, 0, 1]) reach.add(Math.max(1, Math.min(SPACES - 1, d + k)));
  if (c.dmg) return ![...reach].some(x => x >= c.rng[0] && x <= c.rng[1]);
  if (c.guard) {
    const O = s.p[1 - me];
    for (const oid of new Set(O.hand.concat(O.deck))) { const oc = CARDS[oid]; if (oc.dmg && oc.cost <= O.energy && hitsStill(s, 1 - me, oid)) return false; }
    return true;
  }
  return false;
}
export function expertBot({ samples = 16, model = true, timeMs = 0 } = {}) {
  const memory = [{ prevD: null, obs: [] }, { prevD: null, obs: [] }];
  return function (s, me, rng) {
    const o = 1 - me, mem = memory[me];
    // what the opponent did last turn, at the distance it was then
    if (s.turn <= 1) { mem.prevD = null; mem.obs = []; }
    if (mem.prevD !== null && s.last && s.last.moves[o]) mem.obs.push({ d: mem.prevD, k: moveKey(s.last.moves[o]) });
    mem.prevD = dist(s);
    const mine = legalActions(s, me).filter(a => CARDS[a.card].basic || !pointless(s, me, a.card));
    const O = s.p[o], cols = [STEP_IN, STEP_OUT, REST];
    for (const id of new Set(O.hand.concat(O.deck))) if (CARDS[id].cost <= O.energy) cols.push({ t: 'move', card: id });
    const A = mine.map(() => new Float64Array(cols.length));
    let n = 0;
    const t0 = timeMs ? Date.now() : 0;
    for (; n < samples; n++) {
      for (let j = 0; j < cols.length; j++) {
        const need = CARDS[cols[j].card].basic ? null : cols[j].card;
        const world = determinize(s, me, rng, need), seed = (rng() * 4294967296) >>> 0;
        for (let i = 0; i < mine.length; i++) {
          const t = clone(world);
          _submit(t, me, mine[i]); _submit(t, o, cols[j]);
          if (t.winner === null) runOut(t, makeRng(seed));
          A[i][j] += score(t, me);
        }
      }
      if (timeMs && Date.now() - t0 > timeMs) { n++; break; }
    }
    const M = A.map(row => Array.from(row, x => x / n));
    const { row, col } = solve(M);
    // the opponent, as watched at this distance: the best answer to it
    const seen = mem.obs.filter(x => x.d === dist(s));
    if (model && seen.length >= 2) {
      const P = cols.map((c, j) => (seen.filter(x => x.k === moveKey(c)).length + 2 * col[j]) / (seen.length + 2));
      let bi = 0, bv = -Infinity;
      for (let i = 0; i < mine.length; i++) { let v = 0; for (let j = 0; j < cols.length; j++) v += P[j] * M[i][j]; if (v > bv) { bv = v; bi = i; } }
      return mine[bi];
    }
    let tot = 0; const p = row.map(x => (x >= 0.05 ? x : 0)); for (const x of p) tot += x;
    let r = rng() * tot, k = 0;
    for (; k < p.length - 1; k++) { r -= p[k]; if (r <= 0) break; }
    return mine[k];
  };
}
export const EXPERT = { samples: 16 };
