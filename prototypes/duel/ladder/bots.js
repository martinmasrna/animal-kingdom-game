// Generic bots for any game with this shape:
//   init(rng) -> state, toMove(s) -> 0|1, moves(s) -> [m], play(s, m) -> new state,
//   winner(s) -> null | 0 | 1 | 'draw', evaluate(s, side) -> number (side's view).
// The same four bots play every candidate game, so only the game changes.

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffled(rng, a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

const WIN = 1e6;
function terminalValue(g, s, side, depthLeft) {
  const w = g.winner(s);
  if (w === null) return null;
  if (w === 'draw') return 0;
  return (w === side ? WIN : -WIN) + (w === side ? depthLeft : -depthLeft); // prefer quick wins, slow losses
}

export function randomBot(g, s, rng) { const m = g.moves(s); return m[Math.floor(rng() * m.length)]; }

// Weak: one move ahead, by the evaluation.
export function greedyBot(g, s, rng) {
  const side = g.toMove(s);
  let best = null, bv = -Infinity;
  for (const m of shuffled(rng, g.moves(s))) {
    const t = g.play(s, m);
    const tv = terminalValue(g, t, side, 0);
    const v = tv !== null ? tv : g.evaluate(t, side);
    if (v > bv) { bv = v; best = m; }
  }
  return best;
}

// Minimax with alpha-beta to a fixed number of plies, by the evaluation at the leaves.
function search(g, s, side, depth, alpha, beta, deadline) {
  const tv = terminalValue(g, s, side, depth);
  if (tv !== null) return tv;
  if (depth === 0) return g.evaluate(s, side);
  if (deadline && Date.now() > deadline) throw TIMEOUT;
  const mine = g.toMove(s) === side;
  const ms = g.moves(s);
  if (mine) {
    let v = -Infinity;
    for (const m of ms) { v = Math.max(v, search(g, g.play(s, m), side, depth - 1, alpha, beta, deadline)); alpha = Math.max(alpha, v); if (alpha >= beta) break; }
    return v;
  }
  let v = Infinity;
  for (const m of ms) { v = Math.min(v, search(g, g.play(s, m), side, depth - 1, alpha, beta, deadline)); beta = Math.min(beta, v); if (alpha >= beta) break; }
  return v;
}
const TIMEOUT = new Error('timeout');

function rootSearch(g, s, rng, depth, deadline, order) {
  const side = g.toMove(s);
  const ms = order || shuffled(rng, g.moves(s));
  let best = ms[0], bv = -Infinity;
  const vals = [];
  for (const m of ms) {
    const v = search(g, g.play(s, m), side, depth - 1, bv === -Infinity ? -Infinity : bv - 1e-9, Infinity, deadline);
    vals.push([m, v]);
    if (v > bv) { bv = v; best = m; }
  }
  return { best, bv, vals };
}

export function depthBot(depth) {
  return (g, s, rng) => rootSearch(g, s, rng, depth, 0).best;
}

// Expert: iterative deepening until the time budget runs out (or maxDepth).
export function timedBot(ms, maxDepth = 40) {
  return (g, s, rng) => {
    const deadline = Date.now() + ms;
    let best = randomBot(g, s, rng), order = shuffled(rng, g.moves(s));
    for (let d = 1; d <= maxDepth; d++) {
      try {
        const r = rootSearch(g, s, rng, d, deadline, order);
        best = r.best;
        // search the best moves first next time; keep random order among equals
        order = r.vals.sort((a, b) => b[1] - a[1]).map(x => x[0]);
        if (Math.abs(r.bv) >= WIN - 1000) break;
      } catch (e) { if (e !== TIMEOUT) throw e; break; }
    }
    return best;
  };
}

// Hidden information: perfect-information search on K sampled worlds that match what the
// bot can see (g.sample), averaged per move. It never looks at the real hidden cards.
function pimcValues(g, s, rng, K, depth, deadline) {
  const side = g.toMove(s);
  const ms = shuffled(rng, g.moves(s));
  const worlds = Array.from({ length: K }, () => g.sample(s, side, rng));
  const vals = ms.map(m => {
    let v = 0;
    for (const w of worlds) v += search(g, g.play(w, m), side, depth - 1, -Infinity, Infinity, deadline) / K;
    return [m, v];
  });
  return vals;
}
export function pimcBot(K, depth) {
  return (g, s, rng) => { const v = pimcValues(g, s, rng, K, depth, 0); return v.reduce((a, b) => (b[1] > a[1] ? b : a))[0]; };
}
export function pimcTimed(ms, K, maxDepth = 30) {
  return (g, s, rng) => {
    const deadline = Date.now() + ms;
    let best = randomBot(g, s, rng);
    for (let d = 1; d <= maxDepth; d++) {
      try { const v = pimcValues(g, s, rng, K, d, deadline); best = v.reduce((a, b) => (b[1] > a[1] ? b : a))[0]; }
      catch (e) { if (e !== TIMEOUT) throw e; break; }
    }
    return best;
  };
}
