// Bots for 02 Attack and block. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles everything its side cannot see before each play-out.

import { CARDS, BOARD, clone, _act, act, legalActions, canAttackWith, canBlockWith, left, blockAssignments, unitAt } from './engine.js';

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
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// ------------------------------------------------------------------ Random
// uniform over the legal actions; a block is a random assignment drawn directly
export function randomBot(s, rng) {
  if (s.phase === 'block') {
    const P = s.p[s.toAct], free = s.attackers.slice(), pairs = [];
    for (const u of P.board) if (canBlockWith(u) && free.length && rng() < 0.5) { const k = Math.floor(rng() * free.length); pairs.push([u.uid, free[k]]); free.splice(k, 1); }
    return { t: 'block', pairs };
  }
  return pick(legalActions(s), rng);
}

// ------------------------------------------------------------------ Greedy
// plays the most expensive card that does something (a Hit only where it destroys, the most
// costly unit it can), attacks with every unit no enemy blocker could destroy and survive,
// all-in when the attack adds up to his life; blocks each attacker with its smallest unit that
// destroys it and survives, the rest unblocked unless that is lethal.
const size = (u) => u.atk + u.hp;
function hitTarget(O, dmg) {
  let best = null;
  for (const u of O.board) if (left(u) <= dmg && (!best || CARDS[u.card].cost > CARDS[best.card].cost)) best = u;
  return best;
}
function usefulPlay(s, id, P, O) {
  const c = CARDS[id];
  if (c.kind === 'unit') return P.board.length < BOARD ? { t: 'play', card: id } : null;
  if (c.kind === 'hit') { const u = hitTarget(O, c.dmg); return u ? { t: 'play', card: id, tgt: u.uid } : null; }
  if (c.kind === 'draw') return { t: 'play', card: id };
  return null;
}
export function bestPlay(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  const ids = [...new Set(P.hand)].filter(id => id !== 'COIN').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) if (CARDS[id].cost <= P.mana) { const a = usefulPlay(s, id, P, O); if (a) return a; }
  if (P.hand.includes('COIN')) for (const id of ids) if (CARDS[id].cost === P.mana + 1 && usefulPlay(s, id, P, O)) return { t: 'play', card: 'COIN' };
  return null;
}
function lethalAttack(s) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  const el = P.board.filter(u => canAttackWith(u) && u.atk > 0);
  const tot = el.reduce((a, u) => a + u.atk, 0);
  return el.length && tot >= O.life ? { t: 'attack', units: el.map(u => u.uid) } : null;
}
export function safeAttackers(s) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  const blockers = O.board.filter(canBlockWith);
  return P.board.filter(u => canAttackWith(u) && u.atk > 0 && !blockers.some(b => b.atk >= left(u) && left(b) > u.atk));
}
export function greedyBlock(s) {
  const D = s.p[s.toAct], A = s.p[s.turn];
  const att = s.attackers.map(x => unitAt(A, x)).filter(Boolean).sort((a, b) => b.atk - a.atk);
  const free = D.board.filter(canBlockWith).sort((a, b) => size(a) - size(b));
  const pairs = [], done = new Set();
  for (const x of att) {
    const b = free.find(b => b.atk >= left(x) && left(b) > x.atk);
    if (b) { pairs.push([b.uid, x.uid]); done.add(x.uid); free.splice(free.indexOf(b), 1); }
  }
  let face = att.filter(x => !done.has(x.uid)).reduce((a, x) => a + x.atk, 0);
  for (const x of att) {
    if (face < D.life || !free.length) break;
    if (done.has(x.uid)) continue;
    const b = free.shift(); pairs.push([b.uid, x.uid]); done.add(x.uid); face -= x.atk;
  }
  return { t: 'block', pairs };
}
export function greedyBot(s) {
  if (s.phase === 'block') return greedyBlock(s);
  if (!s.attacked) { const l = lethalAttack(s); if (l) return l; }
  const p = bestPlay(s); if (p) return p;
  if (!s.attacked) { const safe = safeAttackers(s); if (safe.length) return { t: 'attack', units: safe.map(u => u.uid) }; }
  return { t: 'end' };
}

// ------------------------------------------------------------------ Racer
// plays like Greedy, attacks with everything every turn, blocks only to stop lethal
export function racerBlock(s) {
  const D = s.p[s.toAct], A = s.p[s.turn];
  const att = s.attackers.map(x => unitAt(A, x)).filter(Boolean).sort((a, b) => b.atk - a.atk);
  const free = D.board.filter(canBlockWith).sort((a, b) => size(a) - size(b));
  let face = att.reduce((a, x) => a + x.atk, 0); const pairs = [];
  for (const x of att) { if (face < D.life || !free.length) break; const b = free.shift(); pairs.push([b.uid, x.uid]); face -= x.atk; }
  return { t: 'block', pairs };
}
export function racerBot(s) {
  if (s.phase === 'block') return racerBlock(s);
  const p = bestPlay(s); if (p) return p;
  if (!s.attacked) { const el = s.p[s.toAct].board.filter(u => canAttackWith(u) && u.atk > 0); if (el.length) return { t: 'attack', units: el.map(u => u.uid) }; }
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
export const W = { life: 0.7, low: 0.6, lowAt: 8, atk: 1.0, hp: 0.7, unit: 1.0, card: 1.3, ex: 0.3 };
const lifeWorth = (l) => W.life * l - W.low * Math.max(0, W.lowAt - l);
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1;
    let x = lifeWorth(Math.max(0, P.life)) + W.card * P.hand.length + 0.15 * P.maxMana;
    for (const u of P.board) x += W.atk * u.atk + W.hp * left(u) + W.unit - (u.ex ? W.ex : 0);
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 5));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: every candidate action is followed by a Greedy-vs-Greedy play-out on a
// world where the cards this side cannot see are reshuffled, to the end of the game or DEPTH
// turns and then scored; successive halving spends the play-outs on the candidates that lead.
function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
function rollout(t, me, depth, rng, eps) {
  const start = t.turnNo;
  let steps = 0;
  while (t.winner === null && t.turnNo - start < depth && steps < 400) {
    const a = eps > 0 && rng() < eps ? randomBot(t, rng) : greedyBot(t);
    _act(t, a); steps++;
  }
  return winProb(t, me);
}
// a one-ply look: the action, the opponent's Greedy block when it is an attack, the worth after
function quick(s, a, me) {
  let t = act(s, a);
  if (t.phase === 'block' && t.winner === null) t = act(t, greedyBlock(t));
  return evaluate(t, me);
}
export function candidates(s, keepAttacks = 8, keepBlocks = 10) {
  const me = s.toAct, all = legalActions(s);
  if (s.phase === 'block') {
    let opts = all;
    if (opts.length > keepBlocks) {
      const g = greedyBlock(s), r = racerBlock(s);
      const scored = opts.map(a => ({ a, v: quick(s, a, me) })).sort((x, y) => y.v - x.v).slice(0, keepBlocks).map(x => x.a);
      opts = scored.concat([g, r, { t: 'block', pairs: [] }]);
    }
    return dedupe(opts);
  }
  const plays = all.filter(a => a.t !== 'attack');
  let atks = all.filter(a => a.t === 'attack' && a.units.every(id => unitAt(s.p[me], id).atk > 0));
  if (atks.length > keepAttacks) atks = atks.map(a => ({ a, v: quick(s, a, me) })).sort((x, y) => y.v - x.v).slice(0, keepAttacks).map(x => x.a);
  return dedupe(plays.concat(atks));
}
const key = (a) => JSON.stringify(a.t === 'block' ? { t: 'b', p: a.pairs.map(p => p.join('>')).sort() } : a.t === 'attack' ? { t: 'a', u: a.units.slice().sort() } : a);
function dedupe(list) { const seen = new Set(), out = []; for (const a of list) { const k = key(a); if (!seen.has(k)) { seen.add(k); out.push(a); } } return out; }

// the settings the sim and the set positions use (the page gives Expert more play-outs and a clock)
export const EXPERT = { playouts: 1000, depth: 99, eps: 0.05 };
export function expertBot({ playouts = 600, depth = 99, eps = 0.05, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    let arms = candidates(s);
    if (arms.length === 1) return arms[0];
    for (const a of arms) { const t = act(s, a); if (t.winner === me) return a; }
    const stats = arms.map(a => ({ a, w: 0, n: 0 }));
    let alive = stats.slice();
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) {
          const t = clone(world); _act(t, st.a);
          st.w += rollout(t, me, depth, makeRng(seed), eps); st.n++;
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
