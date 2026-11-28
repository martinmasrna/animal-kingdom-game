// Bots for 05 Front and back rows. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles everything its side cannot see before each play-out.

import { CARDS, clone, _act, act, legalActions, attackTargets, canPlace, find, actionKey } from './engine.js';

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
const units = (P) => P.front.concat(P.back);

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ Greedy
// plays the most expensive affordable card that does something (a unit with room in its row, a
// Hit only where it destroys, the costliest such target), the Coin when it buys a dearer card;
// then attacks: a kill the attacker survives first, then the player when the front is open,
// then the weakest front unit; ends the turn when nothing is left.
function hitTarget(O, dmg, frontOnly) {
  let best = null;
  for (const u of frontOnly ? O.front : units(O)) if (u.hp <= dmg && (!best || CARDS[u.card].cost > CARDS[best.card].cost || (CARDS[u.card].cost === CARDS[best.card].cost && u.atk > best.atk))) best = u;
  return best;
}
function usefulPlay(P, O, id, frontOnly) {
  const c = CARDS[id];
  if (c.kind === 'unit') return canPlace(P, id) ? { t: 'play', card: id } : null;
  if (c.kind === 'hit') { const u = hitTarget(O, c.dmg, frontOnly); return u ? { t: 'play', card: id, tgt: u.uid } : null; }
  return null;
}
export function bestPlay(s, frontOnly = false) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const ids = [...new Set(P.hand)].filter(id => id !== 'COIN').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) if (CARDS[id].cost <= P.mana) { const a = usefulPlay(P, O, id, frontOnly); if (a) return a; }
  if (P.hand.includes('COIN')) for (const id of ids) if (CARDS[id].cost === P.mana + 1 && usefulPlay(P, O, id, frontOnly)) return { t: 'play', card: 'COIN' };
  return null;
}
const survives = (u, d) => u.ranged || d.atk < u.hp;
const value = (u) => CARDS[u.card].cost * 10 + u.atk;
function safeKill(P, O) {
  let best = null, bv = -1;
  const tg = attackTargets(O).filter(x => x !== 0).map(uid => find(O, uid).u);
  for (const u of units(P)) if (u.ready) for (const d of tg) if (u.atk >= d.hp && survives(u, d)) {
    const v = value(d) * 100 - u.atk;
    if (v > bv) { bv = v; best = { t: 'attack', from: u.uid, to: d.uid }; }
  }
  return best;
}
function strongestReady(P) {
  let best = null;
  for (const u of units(P)) if (u.ready && (!best || (u.ranged && !best.ranged) || (u.ranged === best.ranged && u.atk > best.atk))) best = u;
  return best;
}
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = bestPlay(s); if (p) return p;
  const k = safeKill(P, O); if (k) return k;
  const a = strongestReady(P);
  if (a && a.atk > 0) {
    if (!O.front.length) return { t: 'attack', from: a.uid, to: 0 };
    let w = O.front[0]; for (const d of O.front) if (d.hp < w.hp) w = d;
    return { t: 'attack', from: a.uid, to: w.uid };
  }
  return { t: 'end' };
}

// ------------------------------------------------------------------ Racer
// plays like Greedy (its Hits only on front units); every unit hits the player whenever the front
// is open, otherwise the front unit it can destroy (Ranged first), otherwise the weakest front unit.
export function racerBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = bestPlay(s, true); if (p) return p;
  const ready = units(P).filter(u => u.ready && u.atk > 0).sort((a, b) => (b.ranged - a.ranged) || (b.atk - a.atk));
  if (!ready.length) return { t: 'end' };
  if (!O.front.length) return { t: 'attack', from: ready[0].uid, to: 0 };
  for (const u of ready) { const d = O.front.filter(d => d.hp <= u.atk).sort((a, b) => b.hp - a.hp)[0]; if (d) return { t: 'attack', from: u.uid, to: d.uid }; }
  let w = O.front[0]; for (const d of O.front) if (d.hp < w.hp) w = d;
  return { t: 'attack', from: ready[0].uid, to: w.uid };
}

// ------------------------------------------------------------------ play-out policy
// what Expert's play-outs assume both sides do: Greedy's plays, then only attacks that pay
// (a kill it survives, the player when the front is open, free Ranged damage, a trade at least
// even), and nothing else.
export function playoutBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = bestPlay(s); if (p) return p;
  const k = safeKill(P, O); if (k) return k;
  const ready = units(P).filter(u => u.ready && u.atk > 0);
  if (!ready.length) return { t: 'end' };
  if (!O.front.length) return { t: 'attack', from: ready[0].uid, to: 0 };
  let w = O.front[0]; for (const d of O.front) if (d.hp < w.hp) w = d;
  const r = ready.find(u => u.ranged); if (r) return { t: 'attack', from: r.uid, to: w.uid };
  for (const u of ready) for (const d of O.front) if (u.atk >= d.hp && value(d) >= value(u)) return { t: 'attack', from: u.uid, to: d.uid };
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
// a position's worth to `me`: life (more once low), units by attack and health (Ranged a little
// more: they hit without being hit), cards in hand, mana growth
export const W = { life: 0.6, low: 0.5, lowAt: 8, atk: 1.0, hp: 0.6, unit: 0.8, ranged: 0.4, card: 1.4, mana: 0.2, open: 0.25 };
const lifeWorth = (l) => W.life * l - W.low * Math.max(0, W.lowAt - l);
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1;
    let x = lifeWorth(Math.max(0, P.life)) + W.card * P.hand.filter(id => id !== 'COIN').length + 0.4 * (P.hand.includes('COIN') ? 1 : 0) + W.mana * P.maxMana;
    for (const u of P.front) x += W.atk * u.atk + W.hp * u.hp + W.unit;
    for (const u of P.back) x += (W.atk + W.ranged) * u.atk + W.hp * u.hp + W.unit;
    // an empty front row leaves the back row and life open to the other side's attackers
    if (!P.front.length) { const O = s.p[1 - side]; let a = 0; for (const u of units(O)) a += u.atk; x -= W.open * a; }
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: each candidate action is followed by Greedy on both sides (5% random
// moves) for DEPTH turns, on a world where the cards this side cannot see are reshuffled, then the
// position is scored as a win chance; successive halving spends the play-outs on the leaders.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
// every arm's play-out stops at the same turn, counted from the decision's own turn
function rollout(t, me, start, depth, rng, eps) {
  let steps = 0;
  while (t.winner === null && t.turnNo - start < depth && steps < 300) {
    const a = eps > 0 && rng() < eps ? randomBot(t, rng) : playoutBot(t);
    _act(t, a); steps++;
  }
  return winProb(t, me);
}
// symmetric actions collapse: same card on the same kind of target
function symKey(s, a) {
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  const d = (side, uid) => { const f = find(side, uid); return f ? f.u.card + f.u.hp : 'x'; };
  if (a.t === 'attack') return 'a' + d(P, a.from) + '>' + (a.to === 0 ? 'face' : d(O, a.to));
  if (a.t === 'play') return 'p' + a.card + (a.tgt ? '>' + d(O, a.tgt) : '');
  return 'e';
}
export function candidates(s, keep = 12) {
  const me = s.toAct, seen = new Set(), all = [];
  for (const a of legalActions(s)) { const k = symKey(s, a); if (!seen.has(k)) { seen.add(k); all.push(a); } }
  const scored = all.map(a => ({ a, v: a.t === 'end' ? evaluate(s, me) : evaluate(act(s, a), me) })).sort((x, y) => y.v - x.v);
  if (scored.length <= keep) return scored.map(x => x.a);
  const g = actionKey(greedyBot(s)), out = scored.slice(0, keep).map(x => x.a);
  for (const x of scored.slice(keep)) if (x.a.t === 'end' || actionKey(x.a) === g) out.push(x.a);
  return out;
}

// the settings the sim and the set positions use; the page gives Expert a clock as well
export const EXPERT = { playouts: 400, depth: 6, eps: 0.05, keep: 12 };
export function expertBot({ playouts = 400, depth = 6, eps = 0.05, keep = 12, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s, keep);
    if (arms.length === 1) return arms[0];
    for (const a of arms) if (a.t !== 'end' && act(s, a).winner === me) return a;
    let alive = arms.map(a => ({ a, w: 0, n: 0 }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(2, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) { const t = clone(world); _act(t, st.a); st.w += rollout(t, me, s.turnNo, depth, makeRng(seed), eps); st.n++; }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      alive = alive.slice(0, Math.ceil(alive.length / 2));
      if (timeMs && Date.now() - t0 > timeMs) break;
    }
    return alive[0].a;
  };
}
