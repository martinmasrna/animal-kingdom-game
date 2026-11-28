// Bots for 15 Key pieces. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles everything its side cannot see before each play-out.

import { CARDS, BOARD, KEYS, clone, _act, act, legalActions, actionKey, keysHeld, attackTargets, isPiece } from './engine.js';

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
const val = (u) => CARDS[u.card].kind === 'key' ? 6 + u.hp : u.atk + u.hp;
const isKey = (u) => CARDS[u.card].kind === 'key';

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ shared pieces
function missingKeys(P) { const held = keysHeld(P); return KEYS.filter(k => !held.includes(k)); }
function playMissingKey(s) {
  const P = s.p[s.toAct]; if (P.board.length >= BOARD) return null;
  const miss = missingKeys(P).filter(k => P.hand.includes(k) && CARDS[k].cost <= P.mana).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  return miss.length ? { t: 'play', card: miss[0] } : null;
}
function fetchMissing(s) {
  const P = s.p[s.toAct];
  if (!P.hand.includes('FET') || CARDS.FET.cost > P.mana) return null;
  const k = missingKeys(P).filter(k => !P.hand.includes(k) && P.deck.includes(k))[0];
  return k ? { t: 'play', card: 'FET', key: k } : null;
}
// the cheapest Hit in hand that destroys one of `targets` (the most valuable)
function hitThat(s, targets) {
  const me = s.toAct, P = s.p[me];
  const hits = [...new Set(P.hand)].filter(id => CARDS[id].kind === 'spell' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[a].cost - CARDS[b].cost);
  for (const id of hits) {
    let best = null;
    for (const u of targets) if (u.hp <= CARDS[id].dmg && (!best || val(u) > val(best))) best = u;
    if (best) return { t: 'play', card: id, tgt: { side: 1 - me, uid: best.uid } };
  }
  return null;
}
function attackThatDestroys(s, pred, survive) {
  const me = s.toAct, P = s.p[me], T = attackTargets(s, me).filter(pred);
  for (const u of P.board.filter(v => v.ready && !isKey(v)).sort((a, b) => a.atk - b.atk)) {
    let best = null;
    for (const v of T) if (u.atk >= v.hp && (!survive || v.atk < u.hp) && (!best || val(v) > val(best))) best = v;
    if (best) return { t: 'attack', from: u.uid, to: best.uid };
  }
  return null;
}
function coinFor(s) {
  const P = s.p[s.toAct];
  if (!P.hand.includes('COIN')) return null;
  return P.hand.some(id => CARDS[id].cost === P.mana + 1 && (!isPiece(id) || P.board.length < BOARD) && id !== 'COIN') ? { t: 'play', card: 'COIN' } : null;
}

// ------------------------------------------------------------------ Greedy
// plays a missing Key whenever it can; attacks or Hits an enemy Key it can destroy; otherwise the
// most expensive affordable card (a Fetch for a missing Key, a Hit only where it destroys a unit,
// no second copy of a Key it holds); then trades that destroy a unit and survive.
export function greedyBot(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  const k = playMissingKey(s); if (k) return k;
  const hk = hitThat(s, O.board.filter(isKey)); if (hk) return hk;
  const ak = attackThatDestroys(s, isKey, false); if (ak) return ak;
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].cost <= P.mana && id !== 'COIN').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'unit' && P.board.length < BOARD) return { t: 'play', card: id };
    if (c.kind === 'fetch') { const f = fetchMissing(s); if (f) return f; }
    if (c.kind === 'spell') { const h = hitThat(s, O.board.filter(u => !isKey(u))); if (h && h.card === id) return h; }
  }
  const cn = coinFor(s); if (cn) return cn;
  const tr = attackThatDestroys(s, (u) => !isKey(u), true); if (tr) return tr;
  return { t: 'end' };
}

// ------------------------------------------------------------------ Racer
// plays Keys and Guards first; attacks only to destroy Keys
export function racerBot(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  const k = playMissingKey(s); if (k) return k;
  const f = fetchMissing(s); if (f) return f;
  if (P.board.length < BOARD) for (const id of ['WAL', 'GRD']) if (P.hand.includes(id) && CARDS[id].cost <= P.mana) return { t: 'play', card: id };
  const hk = hitThat(s, O.board.filter(isKey)); if (hk) return hk;
  if (P.board.length < BOARD) { const u = [...new Set(P.hand)].filter(id => CARDS[id].kind === 'unit' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[b].cost - CARDS[a].cost)[0]; if (u) return { t: 'play', card: u }; }
  const cn = coinFor(s); if (cn) return cn;
  // attacks only where the ready units together destroy a Key this turn
  const T = attackTargets(s, me), ready = P.board.filter(v => v.ready && !isKey(v)).sort((a, b) => b.atk - a.atk);
  const tot = ready.reduce((x, u) => x + u.atk, 0);
  const key = T.filter(isKey).sort((a, b) => a.hp - b.hp)[0];
  if (key && tot >= key.hp && ready.length) return { t: 'attack', from: ready[0].uid, to: key.uid };
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1, k = keysHeld(P).length;
    let x = [0, 2, 6, 14][k] + 0.6 * P.hand.length + 0.3 * P.maxMana;
    for (const u of P.board) x += isKey(u) ? 0.4 * u.hp : 0.9 * u.atk + 0.6 * u.hp + (CARDS[u.card].guard ? 1 : 0);
    if (P.deck.length < 4) x -= (4 - P.deck.length) * 2;
    v += sg * x;
  }
  // the side to move with three Keys facing it must break one now
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: every candidate action is followed by a play-out on a world where the
// cards this side cannot see are reshuffled; both sides play Greedy or Racer (drawn per play-out)
// with a denial sense (when the other side holds two or three Keys, every attack and Hit goes at
// the weakest Key it can reach, Guards first) and a little noise, DEPTH turns ahead, then scored.
// Successive halving spends the play-outs on the leaders, every arm seeing the same worlds.
function determinize(s, me, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - me], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
function deny(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  const held = keysHeld(O).length;
  if (held < 2) return null;
  const T = attackTargets(s, me);
  // Hits straight at a Key (they ignore Guard)
  const keys = O.board.filter(isKey).sort((a, b) => a.hp - b.hp);
  const hk = hitThat(s, keys); if (hk) return hk;
  if (held === 3) {
    const hits = P.hand.filter(id => CARDS[id].kind === 'spell' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[b].dmg - CARDS[a].dmg);
    if (hits.length && keys.length) return { t: 'play', card: hits[0], tgt: { side: 1 - me, uid: keys[0].uid } };
  }
  const ready = P.board.filter(v => v.ready && !isKey(v)).sort((a, b) => b.atk - a.atk);
  if (!ready.length) return null;
  const tk = T.filter(isKey).sort((a, b) => a.hp - b.hp)[0];
  if (tk) return { t: 'attack', from: ready[0].uid, to: tk.uid };
  const g = T.filter(u => !isKey(u)).sort((a, b) => a.hp - b.hp)[0];
  if (g && held === 3) return { t: 'attack', from: ready[0].uid, to: g.uid };
  return null;
}
export function candidates(s) {
  const me = s.toAct, seen = new Set(), out = [];
  for (const a of legalActions(s)) {
    if (a.t === 'play' && a.tgt && a.tgt.side === me) continue;
    if (a.t === 'play' && a.card === 'COIN' && !s.p[me].hand.some(id => id !== 'COIN' && CARDS[id].cost === s.p[me].mana + 1)) continue;
    const k = actionKey(a); if (!seen.has(k)) { seen.add(k); out.push(a); }
  }
  return out;
}
function policy(t, rng, eps, style) {
  if (eps > 0 && rng() < eps) return pick(candidates(t), rng);
  const k = playMissingKey(t); if (k) return k;
  return deny(t) || (style[t.toAct] === 'r' ? racerBot(t) : greedyBot(t));
}
function rollout(t, me, rng, eps, depth) {
  const style = [rng() < 0.5 ? 'r' : 'g', rng() < 0.5 ? 'r' : 'g'];
  const stop = t.turnNo + depth; let steps = 0;
  while (t.winner === null && t.turnNo < stop && steps < 600) { _act(t, policy(t, rng, eps, style)); steps++; }
  return winProb(t, me);
}
export const EXPERT = { playouts: 1200, eps: 0.04, depth: 14 };
export function expertBot({ playouts = 1200, eps = 0.04, depth = 14, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s);
    if (arms.length === 1) return arms[0];
    for (const a of arms) { const t = act(s, a); if (t.winner === me) return a; }
    let alive = arms.map(a => ({ a, w: 0, n: 0 }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(3, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, makeRng(seed), eps, depth); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      if (timeMs && Date.now() - t0 > timeMs) break;
      alive = alive.slice(0, Math.ceil(alive.length / 2));
    }
    return alive[0].a;
  };
}
