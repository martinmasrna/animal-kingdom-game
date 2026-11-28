// Bots for 39 Commander grid. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles everything its side cannot see before each play-out.

import { CARDS, clone, _act, act, legalActions, actionKey, occupancy, cmdOf, pieceById, moveCells, attackTargets, canAct, canMove, hasActed, dist, neighbours } from './engine.js';

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
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ shared pieces of the fixed rules
const cost = (u) => u.card === 'CMD' ? 99 : CARDS[u.card].cost;
// the free cell next to my Commander closest to his
function forwardCell(s, me, occ) {
  const mine = cmdOf(s, me), his = cmdOf(s, 1 - me);
  let best = -1, bd = 99;
  for (const c of neighbours(mine.cell)) if (!occ[c]) { const d = dist(c, his.cell); if (d < bd) { bd = d; best = c; } }
  return best;
}
function cardPlay(s, id, { racer = false } = {}) {
  const me = s.turn, P = s.p[me], c = CARDS[id], occ = occupancy(s);
  const mine = cmdOf(s, me), his = cmdOf(s, 1 - me);
  if (c.kind === 'unit') { const cell = forwardCell(s, me, occ); return cell >= 0 ? { t: 'play', card: id, cell } : null; }
  if (c.kind === 'hit') {
    if (dist(his.cell, mine.cell) <= c.range) return { t: 'play', card: id, tgt: his.uid };
    if (racer) return null;
    let best = null;
    for (const u of s.pieces) if (u.side !== me && u.card !== 'CMD' && dist(u.cell, mine.cell) <= c.range && u.hp <= c.dmg && (!best || cost(u) > cost(best))) best = u;
    return best ? { t: 'play', card: id, tgt: best.uid } : null;
  }
  return null;
}
function bestPlay(s, opts) {
  const me = s.turn, P = s.p[me];
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].kind !== 'coin' && CARDS[id].kind !== 'rally').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) if (CARDS[id].cost <= P.mana) { const a = cardPlay(s, id, opts); if (a) return a; }
  if (P.hand.includes('COIN')) for (const id of ids) if (CARDS[id].cost === P.mana + 1 && cardPlay(s, id, opts)) return { t: 'play', card: 'COIN' };
  return null;
}
// a move that brings the piece closer to his Commander, the closest such cell
function advance(s, u, occ, his) {
  let best = -1, bd = dist(u.cell, his.cell);
  for (const c of moveCells(s, u, occ)) { const d = dist(c, his.cell); if (d < bd) { bd = d; best = c; } }
  return best;
}
// Rally: on a piece that has acted and could now hit his Commander
function rallyPlay(s) {
  const me = s.turn, P = s.p[me];
  if (!P.hand.includes('RAL') || P.mana < CARDS.RAL.cost) return null;
  const his = cmdOf(s, 1 - me), occ = occupancy(s);
  for (const u of s.pieces) if (u.side === me && u.acted && attackTargets(s, u, occ).includes(his.uid)) return { t: 'play', card: 'RAL', tgt: u.uid };
  return null;
}

// ------------------------------------------------------------------ Greedy
// plays the most expensive affordable card that does something (a unit onto the cell nearest his
// Commander, Hit 3 on his Commander when in reach or on a piece it destroys); then each piece
// attacks if it hits his Commander or destroys a piece and survives, otherwise a unit steps toward
// his Commander (its own Commander holds its cell); Rally on a piece that could hit his Commander.
export function greedyBot(s) {
  const me = s.turn;
  const p = bestPlay(s); if (p) return p;
  const occ = occupancy(s), his = cmdOf(s, 1 - me);
  const mine = s.pieces.filter(u => u.side === me && canAct(u));
  for (const u of mine) if (attackTargets(s, u, occ).includes(his.uid)) return { t: 'attack', from: u.uid, to: his.uid };
  for (const u of mine) for (const to of attackTargets(s, u, occ)) {
    const d = pieceById(s, to);
    if (u.atk >= d.hp && (CARDS[u.card].lance || d.atk < u.hp)) return { t: 'attack', from: u.uid, to };
  }
  for (const u of mine) if (u.card !== 'CMD' && canMove(u)) { const c = advance(s, u, occ, his); if (c >= 0) return { t: 'move', from: u.uid, to: c }; }
  const r = rallyPlay(s); if (r) return r;
  return { t: 'end' };
}

// ------------------------------------------------------------------ Racer
// every piece, its Commander too, goes for his Commander: hits it when it can, otherwise steps
// toward it, otherwise hits whatever stands next to it; Hit 3 only at his Commander.
export function racerBot(s) {
  const me = s.turn;
  const p = bestPlay(s, { racer: true }); if (p) return p;
  const occ = occupancy(s), his = cmdOf(s, 1 - me);
  const mine = s.pieces.filter(u => u.side === me && canAct(u));
  for (const u of mine) if (attackTargets(s, u, occ).includes(his.uid)) return { t: 'attack', from: u.uid, to: his.uid };
  for (const u of mine) if (canMove(u)) { const c = advance(s, u, occ, his); if (c >= 0) return { t: 'move', from: u.uid, to: c }; }
  for (const u of mine) { const t = attackTargets(s, u, occ); if (t.length) return { t: 'attack', from: u.uid, to: t[0] }; }
  const r = rallyPlay(s); if (r) return r;
  return { t: 'end' };
}

// ------------------------------------------------------------------ play-out policy
// what Expert's play-outs assume both sides do when PLAYOUT is 'careful': Greedy's plays and
// attacks, but a unit steps forward only onto a cell no enemy piece that could destroy it touches
function threatened(s, side, cell, hp, occ) {
  for (const n of neighbours(cell)) { const d = occ[n]; if (d && d.side !== side && d.atk >= hp) return true; }
  return false;
}
export function carefulBot(s) {
  const me = s.turn;
  const p = bestPlay(s); if (p) return p;
  const occ = occupancy(s), his = cmdOf(s, 1 - me);
  const mine = s.pieces.filter(u => u.side === me && canAct(u));
  for (const u of mine) if (u.card !== 'CMD' && attackTargets(s, u, occ).includes(his.uid)) return { t: 'attack', from: u.uid, to: his.uid };
  for (const u of mine) for (const to of attackTargets(s, u, occ)) {
    const d = pieceById(s, to);
    if (u.atk >= d.hp && (CARDS[u.card].lance || d.atk < u.hp)) return { t: 'attack', from: u.uid, to };
  }
  for (const u of mine) if (u.card !== 'CMD' && canMove(u)) {
    let best = -1, bd = dist(u.cell, his.cell);
    for (const c of moveCells(s, u, occ)) { const d = dist(c, his.cell); if (d < bd && !threatened(s, me, c, u.hp, occ)) { bd = d; best = c; } }
    if (best >= 0) return { t: 'move', from: u.uid, to: best };
  }
  const r = rallyPlay(s); if (r) return r;
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
// a position's worth to `me`: the two Commanders' health (more once low), the units by attack and
// health, how close my units stand to his Commander and his to mine, cards in hand, mana growth
export const W = { cmd: 1.6, low: 1.2, lowAt: 7, atk: 1.0, hp: 0.6, unit: 0.8, near: 0.35, card: 1.2, mana: 0.2 };
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  const cm = [cmdOf(s, 0), cmdOf(s, 1)];
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1, c = cm[side], his = cm[1 - side];
    const h = Math.max(0, c.hp);
    let x = W.cmd * h - W.low * Math.max(0, W.lowAt - h) + W.card * P.hand.filter(id => id !== 'COIN').length + W.mana * P.maxMana;
    for (const u of s.pieces) if (u.side === side && u.card !== 'CMD') {
      x += W.atk * u.atk + W.hp * u.hp + W.unit;
      x += W.near * u.atk * Math.max(0, 4 - dist(u.cell, his.cell)) / 3;
    }
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: each candidate action is followed by Greedy on both sides (a share of
// random moves) up to the same turn for every candidate, on a world where the cards this side
// cannot see are reshuffled, then scored as a win chance; successive halving spends the
// play-outs on the leaders.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
function rollout(t, me, start, depth, rng, eps, pol = greedyBot) {
  let steps = 0;
  while (t.winner === null && t.turnNo - start < depth && steps < 400) {
    const a = eps > 0 && rng() < eps ? randomBot(t, rng) : pol(t);
    _act(t, a); steps++;
  }
  return winProb(t, me);
}
// the actions worth searching: the KEEP best by a one-ply look, plus ending the turn and Greedy's
// own choice; each carries its one-ply worth as a win chance (the tie-breaking prior)
export function candidates(s, keep = 12, withPrior = false) {
  const me = s.toAct;
  const all = legalActions(s);
  const scored = all.map(a => ({ a, v: a.t === 'end' ? evaluate(s, me) : evaluate(act(s, a), me) })).sort((x, y) => y.v - x.v);
  let out = scored;
  if (scored.length > keep) {
    const g = actionKey(greedyBot(s));
    out = scored.slice(0, keep);
    for (const x of scored.slice(keep)) if (x.a.t === 'end' || actionKey(x.a) === g) out.push(x);
  }
  return withPrior ? out.map(x => ({ a: x.a, prior: 1 / (1 + Math.exp(-x.v / 6)) })) : out.map(x => x.a);
}

// BETA: how much the one-ply worth counts beside the play-outs; it decides only near-ties (the
// play-outs often cannot tell taking a free piece now from taking it next turn)
export const EXPERT = { playouts: 400, depth: 6, eps: 0.05, keep: 12, beta: 0.5, policy: 'careful' };
export function expertBot({ playouts = 400, depth = 6, eps = 0.05, keep = 12, beta = 0.5, timeMs = 0, policy = 'greedy' } = {}) {
  const pol = policy === 'careful' ? carefulBot : greedyBot;
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s, keep, true);
    if (arms.length === 1) return arms[0].a;
    for (const { a } of arms) if (a.t !== 'end' && act(s, a).winner === me) return a;
    let alive = arms.map(({ a, prior }) => ({ a, w: 0, n: 0, b: beta * prior }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, s.turnNo, depth, makeRng(seed), eps, pol); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => (y.w / y.n + y.b) - (x.w / x.n + x.b));
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
