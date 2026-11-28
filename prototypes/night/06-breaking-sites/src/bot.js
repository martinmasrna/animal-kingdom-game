// Bots for breaking sites. Each is a step function: given a position, the one action it takes next
// ({ t: 'end' } ends its turn). None reads a hidden card: the Expert deals the unseen cards (the
// opponent's hand and deck, its own deck, the site deck) again before every play-out.

import { CARDS, PER_SITE, TARGET, clone, _act, legalActions, key, determinize, power, total, gains } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const END = { t: 'end' };
export function randomBot(s, rng) { const o = legalActions(s); return o[Math.floor(rng() * o.length)]; }

function coinHelps(P) {
  if (!P.hand.includes('COIN')) return false;
  let now = -1, withCoin = -1;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'Coin') continue; if (c.cost <= P.mana) now = Math.max(now, c.cost); else if (c.cost <= P.mana + 1) withCoin = Math.max(withCoin, c.cost); }
  return withCoin > now;
}
// how good adding `pw` power of mine to a site is, by Greedy's rule: a break it wins is best (more
// points first), a break it loses is never taken, otherwise the bigger lead the better
function siteValue(x, me, pw) {
  const mine = power(x, me) + pw, his = power(x, 1 - me);
  if (total(x) + pw >= x.thr) return mine > his ? 1000 + x.win : -Infinity;
  return mine - his + x.win / 100;
}
const dearest = (P, kind) => { let best = null; for (const id of P.hand) { const c = CARDS[id]; if (c.kind === kind && c.cost <= P.mana && (!best || c.cost > CARDS[best].cost)) best = id; } return best; };

// Greedy (the spec's rule): play the dearest affordable unit at the site where it creates or widens
// its lead most, never breaking a site it would lose; Strike the biggest enemy unit it can destroy;
// then Boost the same way a unit is placed, and Draw 2. It never plays Move.
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], S = s.sites;
  if (coinHelps(P)) return { t: 'coin' };
  const u = dearest(P, 'Unit');
  if (u) {
    let best = -1, bv = -Infinity;
    S.forEach((x, k) => { if (x && x.u[me].length < PER_SITE) { const v = siteValue(x, me, CARDS[u].power); if (v > bv) { bv = v; best = k; } } });
    if (best >= 0) return { t: 'unit', card: u, slot: best };
  }
  if (P.hand.includes('STRIKE') && CARDS.STRIKE.cost <= P.mana) {
    let best = null, bp = -1;
    S.forEach((x, k) => { if (x) x.u[1 - me].forEach((m, i) => { if (m.power <= CARDS.STRIKE.max && m.power > bp) { bp = m.power; best = { t: 'strike', slot: k, i }; } }); });
    if (best) return best;
  }
  if (P.hand.includes('BOOST') && CARDS.BOOST.cost <= P.mana) {
    let best = null, bv = -Infinity;
    S.forEach((x, k) => { if (x && x.u[me].length) { const v = siteValue(x, me, CARDS.BOOST.plus); if (v > bv) { bv = v; best = { t: 'boost', slot: k, i: 0 }; } } });
    if (best && bv > -Infinity) return best;
  }
  if (P.hand.includes('DRAW2') && CARDS.DRAW2.cost <= P.mana) return { t: 'draw' };
  return END;
}

// Racer: plays its dearest units at the open site with the highest Winner points, ignoring the
// opponent's power there.
export function racerBot(s) {
  const me = s.turn, P = s.p[me], S = s.sites;
  if (coinHelps(P)) return { t: 'coin' };
  const u = dearest(P, 'Unit');
  if (u) {
    let best = -1;
    S.forEach((x, k) => { if (x && x.u[me].length < PER_SITE && (best < 0 || x.win > S[best].win)) best = k; });
    if (best >= 0) return { t: 'unit', card: u, slot: best };
  }
  return END;
}

// A position's worth to `me` as a win chance: points, and the share of each open site's prize
// its current power would take, plus cards in hand.
export function evaluate(s, me) {
  let v = s.p[me].points - s.p[1 - me].points;
  for (const x of s.sites) if (x) { const a = power(x, me), b = power(x, 1 - me); if (a + b) v += (x.win + x.run) * (a - b) / (a + b) * 0.5; }
  v += 0.7 * (s.p[me].hand.length - s.p[1 - me].hand.length);
  return 1 / (1 + Math.exp(-v / 3));
}

function policy(t, rng, eps) { return rng() < eps ? randomBot(t, rng) : greedyBot(t); }
function rollout(t, me, rng, depth, eps, start) {
  for (let steps = 0; t.winner === null && t.turnNo - start < depth && steps < 2000; steps++) _act(t, policy(t, rng, eps));
  if (t.winner === null) return evaluate(t, me);
  // a win sooner and a loss later are worth a little more, so a lost position is still played on
  const late = Math.min(1, (t.turnNo - start) / 40);
  return t.winner === me ? 0.9 + 0.1 * (1 - late) : t.winner === 'draw' ? 0.5 : 0.1 * late;
}

// Expert: flat Monte Carlo with UCB1 over the distinct actions now (actions that give the same
// position count once). Each play-out deals the unseen cards again, takes the action, and plays on
// with the play-out policy for `depth` turns; an unfinished one is scored by evaluate().
// `playouts` is the budget per action; with `timeMs` it also stops at that time (after at least
// `minPlayouts`), so the page never waits long.
export function mcExpert({ playouts = 3000, depth = 99, eps = 0, C = 0.5, timeMs = 0, minPlayouts = 200 } = {}) {
  return function expert(s, rng) {
    const me = s.turn, opts = [], seen = new Set(), lost = [];
    for (const a of legalActions(s)) {
      const t = clone(s); _act(t, a);
      if (t.winner === me) return a;
      if (t.winner !== null && t.winner !== 'draw') { lost.push(a); continue; } // never hands him the game while anything else is possible
      const k = a.t === 'end' ? 'end' : key(t);
      if (!seen.has(k)) { seen.add(k); opts.push({ a, n: 0, w: 0 }); }
    }
    if (!opts.length) return lost[0];
    if (opts.length === 1) return opts[0].a;
    const t0 = timeMs ? Date.now() : 0;
    for (let total = 0; ; total++) {
      if (total >= playouts) break;
      if (timeMs && total >= minPlayouts && (total & 15) === 0 && Date.now() - t0 > timeMs) break;
      let o;
      if (total < opts.length) o = opts[total];
      else { let bu = -1; const lg = Math.log(total); for (const x of opts) { const u = x.w / x.n + C * Math.sqrt(lg / x.n); if (u > bu) { bu = u; o = x; } } }
      const t = determinize(s, me, rng), start = t.turnNo; _act(t, o.a);
      o.w += rollout(t, me, rng, depth, eps, start); o.n++;
    }
    let best = opts[0];
    for (const x of opts) if (x.n > best.n || (x.n === best.n && x.w > best.w)) best = x;
    return best.a;
  };
}
export const EXPERT = { playouts: 1000, depth: 99, eps: 0, C: 0.5 };
