// Bots for Momentum rope. Each returns one action for the player to move. None reads a hidden
// card: Expert redraws everything its player cannot see before every play-out.

import { CARDS, END, VMAX, fwd, legalActions, _act, clone, determinize, actionKey } from './engine.js';

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

// The turn's worth to the mover: (marker after the end-of-turn move + 2 x velocity), both forward.
function turnWorth(s, me) {
  const f = fwd(me);
  if (s.winner !== null) return s.winner === me ? 1000 : -1000;
  let d = s.vel;
  if ((d < 0 && s.p[0].anchor) || (d > 0 && s.p[1].anchor)) d = 0;
  const pos = Math.max(-END, Math.min(END, s.pos + d));
  if (f * pos >= END) return 1000;
  if (f * pos <= -END) return -1000;
  return f * pos + 2 * f * s.vel;
}
// apply a card without drawing (Draw 2's cards are unknown when planning)
function plan(t, id) {
  if (id === 'DR2') { const P = t.p[t.turn]; P.mana -= CARDS.DR2.cost; P.hand.splice(P.hand.indexOf('DR2'), 1); return t; }
  return _act(t, { t: 'play', card: id });
}
// Greedy: the sequence of plays this turn with the best turnWorth, spending the most mana among ties;
// returns its first action.
export function greedyBot(s) {
  const me = s.turn, memo = new Map();
  function best(t, depth) {
    const P = t.p[me];
    const key = P.mana + '|' + P.hand.slice().sort().join('') + '|' + t.pos + '|' + t.vel + '|' + (t.p[0].anchor ? 1 : 0) + (t.p[1].anchor ? 1 : 0) + '|' + t.winner;
    if (memo.has(key)) return memo.get(key);
    let res = { v: turnWorth(t, me), spent: 0, first: null };
    if (t.winner === null && depth < 7) for (const id of new Set(P.hand)) {
      if (CARDS[id].cost > P.mana) continue;
      const x = plan(clone(t), id), r = best(x, depth + 1), spent = r.spent + CARDS[id].cost;
      if (r.v > res.v + 1e-9 || (Math.abs(r.v - res.v) < 1e-9 && spent > res.spent)) res = { v: r.v, spent, first: id };
    }
    memo.set(key, res);
    return res;
  }
  const r = best(s, 0);
  return r.first ? { t: 'play', card: r.first } : { t: 'end' };
}
// Racer: only Shove, Jolt, Heave, Big Heave and Surge: velocity first, Surge while velocity is
// forward, then the shoves.
export function racerBot(s) {
  const me = s.turn, P = s.p[me], f = fwd(me), has = (id) => P.hand.includes(id) && CARDS[id].cost <= P.mana;
  for (const id of ['BIG', 'HEA']) if (has(id) && f * s.vel < VMAX) return { t: 'play', card: id };
  if (has('SUR') && f * s.vel > 0) return { t: 'play', card: 'SUR' };
  for (const id of ['JOL', 'SHO']) if (has(id)) return { t: 'play', card: id };
  if (P.hand.includes('COIN') && ['BIG', 'HEA', 'JOL', 'SUR'].some(id => P.hand.includes(id) && CARDS[id].cost === P.mana + 1)) return { t: 'play', card: 'COIN' };
  return { t: 'end' };
}

// ------------------------------------------------------------------ Expert
// Play-out policy: the single card that most improves turnWorth (Draw 2 while mana is spare), else
// end the turn; one action in seven random.
function policy(s, r) {
  if (r() < 0.15) return pick(legalActions(s), r);
  const me = s.turn, P = s.p[me];
  let best = null, bv = turnWorth(s, me) + 1e-9;
  for (const id of new Set(P.hand)) {
    if (CARDS[id].cost > P.mana || id === 'DR2' || id === 'COIN') continue;
    const v = turnWorth(_act(clone(s), { t: 'play', card: id }), me);
    if (v > bv) { bv = v; best = id; }
  }
  if (best) return { t: 'play', card: best };
  if (P.hand.includes('DR2') && P.mana >= 2) return { t: 'play', card: 'DR2' };
  return { t: 'end' };
}

export function ismcts(s, r, { iters = 1500, c = 0.7 } = {}) {
  const me = s.turn, rootActs = sensible(s);
  if (rootActs.length === 1) return rootActs[0];
  for (const a of rootActs) { const t = _act(determinize(s, me, r), a); if (t.winner === me) return a; }
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
