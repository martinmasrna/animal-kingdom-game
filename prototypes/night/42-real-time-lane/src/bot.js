// Bots for 42 Real-time lane. Each is a function (state, side, rng) -> one action for that side
// this tick. Bots decide every second tick (once a second); the page asks the same. None reads a
// hidden card: Expert rebuilds the opponent's queue from the plays it has seen.

import { CARDS, DECK, HAND, LEN, SPAWN, DIR, BLAST_R, clone, _step, hand, wallSpots } from './engine.js';

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
const WAIT = { t: 'wait' };
export const DECIDE_EVERY = 2;

const enemies = (s, side) => s.units.filter(u => u.side !== side);
// the Blast spot that hits the most enemy units (ties: the most health hit)
export function densest(s, side) {
  const E = enemies(s, side); let best = null;
  for (const c of E) {
    let n = 0, h = 0; for (const e of E) if (Math.abs(e.x - c.x) <= BLAST_R) { n++; h += Math.min(8, e.hp); }
    if (!best || n > best.n || (n === best.n && h > best.h)) best = { x: c.x, n, h };
  }
  return best;
}
const clampHalf = (side, x) => side === 0 ? Math.min(6, Math.max(SPAWN[0], x)) : Math.max(6, Math.min(SPAWN[1], x));
const snap = (x) => Math.round(x * 2) / 2;
// a Wall just in front of the biggest enemy unit, inside the own half
function wallSpot(s, side) {
  const E = enemies(s, side).filter(u => !u.wall); if (!E.length) return null;
  const big = E.reduce((a, b) => (b.hp > a.hp ? b : a));
  return clampHalf(side, snap(big.x - DIR[side] * 0.5));
}

// ------------------------------------------------------------------ Random
export function randomBot(s, side, rng) {
  const opts = [WAIT];
  for (const id of hand(s, side)) {
    const c = CARDS[id]; if (s.mana[side] < c.cost) continue;
    if (c.kind === 'unit') opts.push({ t: 'play', card: id });
    else if (c.kind === 'wall') { const sp = wallSpots(side); opts.push({ t: 'play', card: id, x: sp[Math.floor(rng() * sp.length)] }); }
    else opts.push({ t: 'play', card: id, x: snap(0.5 + rng() * 11) });
  }
  return opts[Math.floor(rng() * opts.length)];
}
// ------------------------------------------------------------------ Greedy
// the most expensive affordable card the moment it can; Blast at the densest enemy group, Wall
// just in front of the biggest enemy unit (neither when there is no enemy unit)
function playOf(s, side, id) {
  const c = CARDS[id];
  if (c.kind === 'unit') return { t: 'play', card: id };
  if (c.kind === 'blast') { const d = densest(s, side); return d ? { t: 'play', card: id, x: d.x } : null; }
  const x = wallSpot(s, side); return x === null ? null : { t: 'play', card: id, x };
}
export function greedyBot(s, side) {
  const ids = hand(s, side).filter(id => CARDS[id].cost <= s.mana[side]).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) { const a = playOf(s, side, id); if (a) return a; }
  return WAIT;
}
// ------------------------------------------------------------------ Racer
export function racerBot(s, side) {
  const ids = hand(s, side).filter(id => CARDS[id].kind === 'unit' && CARDS[id].cost <= s.mana[side]).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  return ids.length ? { t: 'play', card: ids[0] } : WAIT;
}

// ------------------------------------------------------------------ evaluation
// base health, then the units: what is left of each one's price, and how far it has come
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 1.2 * (s.base[me] - s.base[1 - me]) + 0.35 * (s.mana[me] - s.mana[1 - me]);
  for (const u of s.units) {
    const c = CARDS[u.card], price = c.cost / (c.n || 1);
    const prog = u.side === 0 ? u.x / LEN : (LEN - u.x) / LEN;
    const w = price * (0.4 + 0.6 * u.hp / u.max) + (u.wall ? 0 : u.atk * prog * 1.2);
    v += u.side === me ? w : -w;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// rebuilds the opponent's queue: the cards it has played sit at the back in the order last played,
// the others in front in an unknown order
function determinize(s, me, rng) {
  const t = clone(s), o = 1 - me, seen = s.seen[o], known = [];
  for (let i = seen.length - 1; i >= 0 && known.length < DECK.length; i--) if (!known.includes(seen[i])) known.push(seen[i]);
  known.reverse();
  t.queue[o] = shuffle(DECK.filter(id => !known.includes(id)), rng).concat(known);
  return t;
}
// the play-out policy: a player who waits for a random amount of mana, then plays a sensible card
function policy(s, side, rng, th) {
  const m = s.mana[side];
  const E = enemies(s, side), mine = s.units.filter(u => u.side === side && !u.wall);
  // a threat close to the base with nothing in front of it: answer now
  const d = DIR[side], threat = E.some(e => !e.wall && (side === 0 ? e.x : LEN - e.x) < 5) && !mine.some(u => (side === 0 ? u.x : LEN - u.x) < 6);
  if (m < th && !threat) return WAIT;
  const opts = [];
  for (const id of hand(s, side)) {
    const c = CARDS[id]; if (c.cost > m) continue;
    if (c.kind === 'unit') opts.push({ t: 'play', card: id });
    else if (c.kind === 'blast') { const b = densest(s, side); if (b && (b.n >= 2 || b.h >= 6)) opts.push({ t: 'play', card: id, x: b.x }); }
    else { const x = wallSpot(s, side); if (x !== null && E.some(e => !e.wall && (side === 0 ? e.x : LEN - e.x) < 7)) opts.push({ t: 'play', card: id, x }); }
  }
  if (!opts.length) return WAIT;
  void d;
  return opts[Math.floor(rng() * opts.length)];
}
function rollout(t, me, first, horizon, rng) {
  const th = [3 + Math.floor(rng() * 6), 3 + Math.floor(rng() * 6)];
  const end = t.tick + horizon;
  let acts = first;
  while (t.winner === null && t.tick < end) {
    if (!acts) {
      if (t.tick % DECIDE_EVERY === 0) acts = [policy(t, 0, rng, th[0]), policy(t, 1, rng, th[1])];
      else acts = [WAIT, WAIT];
    }
    _step(t, acts); acts = null;
  }
  return winProb(t, me);
}
export function candidates(s, me) {
  const out = [WAIT], seen = new Set(['w']);
  const add = (a) => { const k = a.card + '@' + a.x; if (!seen.has(k)) { seen.add(k); out.push(a); } };
  const E = enemies(s, me);
  for (const id of hand(s, me)) {
    const c = CARDS[id]; if (c.cost > s.mana[me]) continue;
    if (c.kind === 'unit') add({ t: 'play', card: id });
    else if (c.kind === 'blast') {
      const d = densest(s, me); if (d) add({ t: 'play', card: id, x: d.x });
      for (const e of E) if (!e.wall) add({ t: 'play', card: id, x: snap(e.x) });
    } else {
      const x = wallSpot(s, me); if (x !== null) add({ t: 'play', card: id, x });
      add({ t: 'play', card: id, x: me === 0 ? 3 : LEN - 3 }); add({ t: 'play', card: id, x: me === 0 ? 6 : LEN - 6 });
    }
  }
  return out.slice(0, 14);
}
// the settings the sim and the set positions use (the page gives Expert more play-outs and a clock)
export const EXPERT = { playouts: 160, horizon: 40 };
export function expertBot({ playouts = 160, horizon = 40, timeMs = 0 } = {}) {
  return function (s, me, rng) {
    const arms = candidates(s, me);
    if (arms.length === 1) return arms[0];
    const stats = arms.map(a => ({ a, w: 0, n: 0 }));
    let alive = stats.slice();
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        const prng = makeRng(seed), th = 3 + Math.floor(prng() * 6), oppFirst = policy(world, 1 - me, prng, th);
        for (const st of alive) {
          const t = clone(world), first = me === 0 ? [st.a, oppFirst] : [oppFirst, st.a];
          st.w += rollout(t, me, first, horizon, makeRng(seed ^ 0x5bd1e995)); st.n++;
        }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
