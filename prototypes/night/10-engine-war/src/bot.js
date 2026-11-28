// Bots for the engine war. Each is a step function: given a position, the one action it takes next
// ({ t: 'end' } ends its turn). None reads a hidden card: the Expert deals the unseen cards (the
// opponent's hand and deck, its own deck, the market deck) again before every play-out.

import { CARDS, clone, _act, legalActions, key, determinize } from './engine.js';

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

// Trash a starting Coin from the discard pile, else a starting Shot, else keep everything.
function trashStep(s) {
  const P = s.p[s.turn];
  if (P.discard.includes('COIN')) return { t: 'trash', from: 'discard', card: 'COIN' };
  if (P.discard.includes('SHOT')) return { t: 'trash', from: 'discard', card: 'SHOT' };
  return { t: 'trash', card: null };
}
// the shot at the highest-yield enemy Post it can destroy (a standing Wall Post is the only target)
function bestShot(s) {
  let best = null, bv = -1;
  for (const a of legalActions(s)) if (a.t === 'shoot') { const x = s.p[1 - s.turn].posts[a.i], c = CARDS[x.card], v = c.yld * 10 + c.hp; if (v > bv) { bv = v; best = a; } }
  return best;
}

// Greedy (the spec's rule): buy the dearest affordable row card, again until nothing is affordable;
// then spend damage on the highest-yield Post it can destroy.
export function greedyBot(s) {
  const P = s.p[s.turn];
  if (P.trash > 0) return trashStep(s);
  let bi = -1;
  s.row.forEach((id, i) => { if (id && CARDS[id].cost <= P.coin && (bi < 0 || CARDS[id].cost > CARDS[s.row[bi]].cost)) bi = i; });
  if (bi >= 0) return { t: 'buy', i: bi };
  return bestShot(s) || END;
}

// Racer: never buys Shots and never shoots; buys the best-yield Post it can afford, else Coin 2.
const RACE = { BPOST: 3, POST: 2, SPOST: 1, COIN2: 0.5 };
export function racerBot(s) {
  const P = s.p[s.turn];
  if (P.trash > 0) return trashStep(s);
  let bi = -1;
  s.row.forEach((id, i) => { if (id && RACE[id] && CARDS[id].cost <= P.coin && (bi < 0 || RACE[id] > RACE[s.row[bi]])) bi = i; });
  return bi >= 0 ? { t: 'buy', i: bi } : END;
}

// A position's worth to `me` as a win chance: points, the yield standing on the table (counted for
// a few turns, less when the opponent's deck carries damage), and what each deck buys per card.
function deckStats(p) {
  const all = p.deck.concat(p.hand, p.discard, p.played);
  let coin = 0, dmg = 0;
  for (const id of all) { const c = CARDS[id]; coin += (c.coin || 0) + (c.draw ? 1.5 : 0); dmg += c.dmg || 0; }
  return { coin: coin / Math.max(1, all.length), dmg: dmg / Math.max(1, all.length) };
}
export function evaluate(s, me) {
  const P = s.p[me], O = s.p[1 - me], dp = deckStats(P), dO = deckStats(O);
  const yP = P.posts.reduce((a, x) => a + CARDS[x.card].yld, 0), yO = O.posts.reduce((a, x) => a + CARDS[x.card].yld, 0);
  let v = P.points - O.points + 2.5 * (yP - yO) + 6 * (dp.coin - dO.coin) + 6 * (dp.dmg - dO.dmg);
  return 1 / (1 + Math.exp(-v / 4));
}

function policy(t, rng, eps) { return rng() < eps ? randomBot(t, rng) : greedyBot(t); }
function rollout(t, me, rng, depth, eps, start) {
  for (let steps = 0; t.winner === null && t.turnNo - start < depth && steps < 3000; steps++) _act(t, policy(t, rng, eps));
  if (t.winner === null) return evaluate(t, me);
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}

// Expert: flat Monte Carlo with UCB1 over the distinct actions now (actions that give the same
// position count once). Each play-out deals the unseen cards again, takes the action, and plays on
// with the play-out policy for `depth` turns; an unfinished one is scored by evaluate().
// `playouts` is the budget per action; with `timeMs` it also stops at that time (after at least
// `minPlayouts`), so the page never waits long.
export function mcExpert({ playouts = 3000, depth = 99, eps = 0, C = 0.5, timeMs = 0, minPlayouts = 200 } = {}) {
  return function expert(s, rng) {
    const me = s.turn, opts = [], seen = new Set();
    for (const a of legalActions(s)) {
      const t = clone(s); _act(t, a);
      if (t.winner === me) return a;
      const k = a.t === 'end' ? 'end' : key(t);
      if (!seen.has(k)) { seen.add(k); opts.push({ a, n: 0, w: 0 }); }
    }
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
export const EXPERT = { playouts: 600, depth: 99, eps: 0, C: 0.5 };
