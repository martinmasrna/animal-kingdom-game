// Bots for the Vanilla Toy, simplest first. None reads a hidden card: the play-out bot
// reshuffles everything the mover cannot see before each play-out.

import { CARDS, clone, _act, legalActions, endTurn, act } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, rng) => a[Math.floor(rng() * a.length)];
const notSelf = (s) => legalActions(s).filter(a => !(a.target && a.target.side === s.turn));

// Random: each step a uniform choice among every legal action and ending the turn.
export function randomBot(s, rng) {
  const t = clone(s), out = [];
  for (;;) {
    const opts = legalActions(t);
    const k = Math.floor(rng() * (opts.length + 1));
    if (k === opts.length || t.winner !== null) return out;
    _act(t, opts[k]); out.push(opts[k]);
  }
}
// Spend: random actions, never at its own side, and never ends the turn while it can act.
export function spendBot(s, rng) {
  const t = clone(s), out = [];
  for (;;) {
    const opts = notSelf(t);
    if (!opts.length || t.winner !== null) return out;
    const a = pick(opts, rng); _act(t, a); out.push(a);
  }
}
// Face: plays what it can (random order), every spell and every attack at the enemy hero.
export function faceBot(s, rng) {
  const t = clone(s), out = [];
  for (;;) {
    const opts = notSelf(t).filter(a => (a.t === 'play' && (!a.target || a.target.i < 0)) || (a.t === 'attack' && a.to < 0));
    if (!opts.length || t.winner !== null) return out;
    const a = pick(opts, rng); _act(t, a); out.push(a);
  }
}

// A position's worth to `me`: health, the minions on the board, the cards in hand.
export const W = { hp: 0.5, atk: 1, mhp: 1, card: 1.5 };
export function evaluate(s, me) {
  if (s.winner === me) return 1e4;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1e4;
  const P = s.p[me], O = s.p[1 - me];
  let v = W.hp * (Math.max(P.hp, 0) - Math.max(O.hp, 0));
  for (const m of P.board) v += W.atk * m.atk + W.mhp * m.hp;
  for (const m of O.board) v -= W.atk * m.atk + W.mhp * m.hp;
  v += W.card * (P.hand.length - O.hand.length);
  return v;
}
// Greedy: each step the action that most improves that worth; ends the turn when none does.
// A card's own worth in hand is not counted as lost when it is played (it is judged by what it does).
export function greedyBot(s) {
  const me = s.turn, t0 = clone(s), out = [];
  let t = t0;
  const val = (x) => evaluate(x, me) + W.card * (s.p[me].hand.length - x.p[me].hand.length);
  let cur = val(t);
  for (;;) {
    if (t.winner !== null) return out;
    let best = null, bv = cur + 1e-9;
    for (const a of notSelf(t)) { const x = clone(t); _act(x, a); const v = val(x); if (v > bv) { bv = v; best = { a, x }; } }
    if (!best) return out;
    out.push(best.a); t = best.x; cur = bv;
  }
}

function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
const play = (t, acts) => { for (const a of acts) { if (t.winner !== null) break; t = act(t, a); } return t; };
// Play-out: candidate turns are Greedy's own and each first action finished the way Greedy would;
// the best TOPN by Greedy's judgement are each played out R times DEPTH turns ahead with Greedy on
// both sides, after reshuffling the cards the mover cannot see. Keeps the turn that wins most.
export function rolloutBot(TOPN = 6, R = 4, DEPTH = 8) {
  return function (s, rng) {
    const me = s.turn, cands = [];
    const add = (acts) => { const t = play(clone(s), acts); cands.push({ acts, t, v: evaluate(t, me) + W.card * (s.p[me].hand.length - t.p[me].hand.length) }); };
    add(greedyBot(s)); add([]);
    for (const a of notSelf(s)) { const t = act(s, a); add([a, ...greedyBot(t)]); }
    const seen = new Set(), top = [];
    for (const c of cands.sort((a, b) => b.v - a.v)) {
      const key = JSON.stringify([c.t.p.map(p => [p.hp, p.board.map(m => m.card + m.hp + (m.ready ? 'r' : '')).sort()]), c.t.p[me].hand.slice().sort()]);
      if (!seen.has(key)) { seen.add(key); top.push(c); }
      if (top.length >= TOPN) break;
    }
    if (top.length === 1 || top[0].t.winner === me) return top[0].acts;
    let best = top[0], bw = -Infinity;
    for (const c of top) {
      let w = 0;
      for (let r = 0; r < R; r++) {
        let t = clone(c.t); const O = t.p[1 - me];
        const pool = shuffle(O.hand.concat(O.deck), rng); O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
        shuffle(t.p[me].deck, rng);
        if (t.winner === null) t = endTurn(t);
        for (let d = 0; t.winner === null && d < DEPTH; d++) { t = play(t, greedyBot(t)); if (t.winner !== null) break; t = endTurn(t); }
        if (t.winner === me) w += 1; else if (t.winner === 'draw') w += 0.5;
        else if (t.winner === null) { const e = evaluate(t, me); w += e > 0 ? 0.75 : e < 0 ? 0.25 : 0.5; }
      }
      if (w > bw) { bw = w; best = c; }
    }
    return best.acts;
  };
}
