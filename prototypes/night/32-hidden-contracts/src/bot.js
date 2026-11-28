// Bots for 32 Hidden contracts. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card or contract: Expert reshuffles everything its side cannot see (the
// opponent's hand and deck, the opponent's held, buried and undrawn contracts, both contract decks'
// order) before each play-out.

import { CARDS, CONTRACTS, BOARD, TARGET, clone, _act, act, legalActions, actionKey } from './engine.js';

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

// ------------------------------------------------------------------ Greedy
// plays the most expensive affordable card that does something (a unit while the board has room,
// a Hit only where it destroys, the costliest such target), the Coin when it buys a dearer card;
// then every attack that destroys an enemy unit and survives; never touches its contracts.
function hitTarget(O, dmg) { let best = null; for (const u of O.board) if (u.hp <= dmg && (!best || CARDS[u.card].cost > CARDS[best.card].cost)) best = u; return best; }
function usefulPlay(P, O, id) {
  const c = CARDS[id];
  if (c.kind === 'unit') return P.board.length < BOARD ? { t: 'play', card: id } : null;
  if (c.kind === 'hit') { const u = hitTarget(O, c.dmg); return u ? { t: 'play', card: id, tgt: u.uid } : null; }
  return null;
}
export function bestPlay(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const ids = [...new Set(P.hand)].filter(id => id !== 'COIN').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) if (CARDS[id].cost <= P.mana) { const a = usefulPlay(P, O, id); if (a) return a; }
  if (P.hand.includes('COIN')) for (const id of ids) if (CARDS[id].cost === P.mana + 1 && usefulPlay(P, O, id)) return { t: 'play', card: 'COIN' };
  return null;
}
function safeKill(P, O) {
  let best = null, bv = -1;
  for (const u of P.board) if (u.ready && u.atk > 0) for (const d of O.board) if (u.atk >= d.hp && d.atk < u.hp) {
    const v = CARDS[d.card].cost * 100 - u.atk;
    if (v > bv) { bv = v; best = { t: 'attack', from: u.uid, to: d.uid }; }
  }
  return best;
}
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = bestPlay(s); if (p) return p;
  const k = safeKill(P, O); if (k) return k;
  return { t: 'end' };
}

// ------------------------------------------------------------------ Racer
// builds toward its own contracts and never touches the opponent: plays units cheapest first while
// the board has room (holding back once a held Patience needs the cards), never attacks or Hits.
export function racerBot(s) {
  const me = s.turn, P = s.p[me];
  if (P.contracts.includes('PATIENCE') && P.hand.length <= 6) return { t: 'end' };
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].kind === 'unit' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[a].cost - CARDS[b].cost);
  if (ids.length && P.board.length < BOARD) return { t: 'play', card: ids[0] };
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
// how close a held contract is to scoring, 0..1
function progress(s, side, c) {
  const P = s.p[side], O = s.p[1 - side], n = P.board.length;
  switch (c) {
    case 'CROWD': return Math.min(n, 4) / 4;
    case 'TOWER': return Math.min(1, P.board.reduce((m, u) => Math.max(m, u.hp), 0) / 6);
    case 'CLEAN': return O.board.length === 0 ? 1 : 0.5 / O.board.length;
    case 'MORE': return n > O.board.length ? 1 : n === O.board.length ? 0.4 : 0.1;
    case 'HUNTER': return P.kills >= 2 ? 1 : P.kills === 1 ? 0.4 : 0.15;
    case 'FORCE': return Math.min(1, P.board.reduce((a, u) => a + u.atk, 0) / 10);
    case 'SPREAD': return Math.min(1, new Set(P.board.map(u => CARDS[u.card].cost)).size / 3);
    case 'PATIENCE': return Math.min(1, P.hand.length / 6);
  }
  return 0;
}
// a position's worth to `me`: points (more as the target nears), how close each held contract is,
// units by attack and health, cards in hand
export const W = { pt: 3, near: 0.6, prog: 1.0, atk: 0.5, hp: 0.35, unit: 0.6, card: 0.5 };
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1;
    let x = W.pt * P.points + W.near * Math.max(0, P.points - (TARGET - 5)) * 2 + W.card * P.hand.filter(id => id !== 'COIN').length;
    for (const c of P.contracts) { const q = progress(s, side, c); x += W.prog * CONTRACTS[c].pts * q * q; }
    for (const u of P.board) x += W.atk * u.atk + W.hp * u.hp + W.unit;
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: each candidate action is followed by Greedy on both sides (a share of
// random moves) up to the same turn for every candidate, on a world where everything this side
// cannot see is reshuffled, then scored as a win chance; successive halving spends the play-outs
// on the leaders, and the one-ply worth breaks near-ties.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(P.deck, rng);
  const cpool = shuffle(O.contracts.concat(O.buried, O.cdeck), rng), h = O.contracts.length, b = O.buried.length;
  O.contracts = cpool.slice(0, h); O.buried = cpool.slice(h, h + b); O.cdeck = cpool.slice(h + b);
  shuffle(P.cdeck, rng);
  return t;
}
function rollout(t, me, start, depth, rng, eps) {
  let steps = 0;
  while (t.winner === null && t.turnNo - start < depth && steps < 300) {
    const a = eps > 0 && rng() < eps ? randomBot(t, rng) : greedyBot(t);
    _act(t, a); steps++;
  }
  return winProb(t, me);
}
// the one-ply look sees only what this side may know: the opponent's contracts are left out of it
function quick(s, a, me) { const t = a.t === 'end' ? clone(s) : act(s, a); t.p[1 - me].contracts = []; return evaluate(t, me); }
export function candidates(s, keep = 12, withPrior = false) {
  const me = s.toAct;
  const scored = legalActions(s).map(a => ({ a, v: quick(s, a, me) })).sort((x, y) => y.v - x.v);
  let out = scored;
  if (scored.length > keep) {
    const g = actionKey(greedyBot(s));
    out = scored.slice(0, keep);
    for (const x of scored.slice(keep)) if (x.a.t === 'end' || actionKey(x.a) === g) out.push(x);
  }
  return withPrior ? out.map(x => ({ a: x.a, prior: 1 / (1 + Math.exp(-x.v / 6)) })) : out.map(x => x.a);
}

export const EXPERT = { playouts: 400, depth: 6, eps: 0.05, keep: 12, beta: 0.5 };
export function expertBot({ playouts = 400, depth = 6, eps = 0.05, keep = 12, beta = 0.5, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s, keep, true);
    if (arms.length === 1) return arms[0].a;
    let alive = arms.map(({ a, prior }) => ({ a, w: 0, n: 0, b: beta * prior }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, s.turnNo, depth, makeRng(seed), eps); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => (y.w / y.n + y.b) - (x.w / x.n + x.b));
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
