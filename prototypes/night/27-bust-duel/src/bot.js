// Bots for Bust duel. Each returns one action for the player to move. Every pile's contents are
// public; the hidden part is each deck's order, the market deck and future shuffles, which Expert
// redraws before every play-out.

import { CARDS, BUST, BUST_COIN, legalActions, _act, determinize, actionKey, linePower } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, r) => a[Math.floor(r() * a.length)];

export function randomBot(s, r) { return pick(legalActions(s), r); }
export const sensible = legalActions;

// the most expensive affordable market card, or pass
function buyBest(s, value) {
  const P = s.p[s.turn], coin = P.bust ? BUST_COIN : P.pow;
  let best = null, bv = -1;
  s.market.forEach((id, i) => { const v = value(id); if (CARDS[id].cost <= coin && v > bv) { bv = v; best = { t: 'buy', i }; } });
  return best || { t: 'pass' };
}
// Trim the weakest card: Crack, then the lowest power
function trimWorst(s) {
  const P = s.p[s.turn];
  let best = null, bv = Infinity;
  for (const id of new Set(P.disc)) { const c = CARDS[id], v = c.pow - 3 * c.str; if (v < bv) { bv = v; best = id; } }
  return { t: 'trim', card: best };
}
const byCost = (id) => CARDS[id].cost + CARDS[id].pow / 100;

// Greedy: draws while its strain is 1 or less, or while its power is below the opponent's line;
// buys the most expensive affordable card.
export function greedyBot(s) {
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (s.phase === 'buy') return buyBest(s, byCost);
  if (s.phase === 'trim') return trimWorst(s);
  const L = legalActions(s);
  if (L.length === 1) return L[0];
  return (P.strain <= 1 || P.pow < linePower(O)) ? { t: 'draw' } : { t: 'stop' };
}
// Pusher: draws until its strain reaches 3, ignoring the opponent; buys like Greedy.
export function racerBot(s) {
  const P = s.p[s.turn];
  if (s.phase === 'buy') return buyBest(s, byCost);
  if (s.phase === 'trim') return trimWorst(s);
  const L = legalActions(s);
  if (L.length === 1) return L[0];
  return P.strain < 3 ? { t: 'draw' } : { t: 'stop' };
}

// ------------------------------------------------------------------ Expert
// The chance that the next card busts, from what is left in the draw pile (or the discard, which
// is reshuffled into it); exact when the top card was peeked.
export function bustChance(P) {
  if (P.peek !== null && P.deck.length) return P.strain + CARDS[P.deck[0]].str >= BUST ? 1 : 0;
  const pile = P.deck.length ? P.deck : P.disc;
  if (!pile.length) return 1;
  let k = 0; for (const id of pile) if (P.strain + CARDS[id].str >= BUST) k++;
  return k / pile.length;
}
const BUYV = { SU: 8, B6: 6.5, S4: 5, TR: 4.4, SP: 4, S3: 3.5, CA: 3.2, PE: 2 };
function policy(s, r) {
  if (s.phase === 'buy') return r() < 0.85 ? buyBest(s, id => BUYV[id]) : pick(legalActions(s), r);
  if (s.phase === 'trim') return trimWorst(s);
  const L = legalActions(s);
  if (L.length === 1) return L[0];
  const P = s.p[s.turn], O = s.p[1 - s.turn], pb = bustChance(P);
  if (O.bust || O.stop) {
    const op = linePower(O);
    if (P.pow > op) return (P.pow - op >= 5 && P.pow >= 7) || pb > 0.2 ? { t: 'stop' } : { t: 'draw' };
    return pb < 0.65 ? { t: 'draw' } : { t: 'stop' };
  }
  return pb < 0.2 + 0.15 * r() ? { t: 'draw' } : { t: 'stop' };
}

export function ismcts(s, r, { iters = 1500, c = 0.7 } = {}) {
  const me = s.turn, rootActs = sensible(s);
  if (rootActs.length === 1) return rootActs[0];
  const root = { kids: new Map(), n: 0 };
  for (let it = 0; it < iters; it++) {
    const d = determinize(s, me, r), path = [];
    let node = root;
    while (d.winner === null) {
      const acts = sensible(d), player = d.turn, fresh = [];
      let best = null, bv = -Infinity, ba = null;
      for (const a of acts) {
        const k = actionKey(d, a), ch = node.kids.get(k);
        if (!ch) { fresh.push([k, a]); continue; }
        ch.avail++;
        const u = ch.w / ch.n + c * Math.sqrt(Math.log(ch.avail) / ch.n);
        if (u > bv) { bv = u; best = ch; ba = a; }
      }
      if (fresh.length) {
        const [k, a] = pick(fresh, r);
        const ch = { kids: new Map(), n: 0, w: 0, avail: 1, player };
        node.kids.set(k, ch); path.push(ch); _act(d, a);
        break;
      }
      path.push(best); _act(d, ba); node = best;
    }
    while (d.winner === null) _act(d, policy(d, r));
    const v = d.winner === me ? 1 : d.winner === 'draw' ? 0.5 : 0;
    root.n++;
    for (const ch of path) { ch.n++; ch.w += ch.player === me ? v : 1 - v; }
  }
  let best = rootActs[0], bn = -1;
  for (const a of rootActs) { const ch = root.kids.get(actionKey(s, a)); if (ch && ch.n > bn) { bn = ch.n; best = a; } }
  return best;
}
export const expertBot = (o) => (s, r) => ismcts(s, r, o);
