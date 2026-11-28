// Bots for 45 Swing neutrals. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles the hands, the decks and the Neutral deck before
// each play-out.

import { CARDS, clone, _act, act, legalActions, actionKey, toward } from './engine.js';

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
const can = (P, id) => P.hand.includes(id) && CARDS[id].cost <= P.mana;

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ Greedy
// spends its mana pulling the highest-attack Neutral onto its side (the smallest Sway that gets it
// there, else the biggest it has), then the next highest; with no Sway that helps, Spread when two
// Neutrals gain from it, Rally, Draw 2, Shield, Exile on their best Neutral.
function swayPlay(s, rng) {
  const me = s.toAct, P = s.p[me];
  const order = [0, 1, 2].sort((a, b) => s.slots[b].atk - s.slots[a].atk || a - b);
  const sways = ['S1', 'S2', 'S3'].filter(id => can(P, id));
  if (!sways.length) return null;
  for (const k of order) {
    const need = 1 - toward(s.slots[k], me);
    if (need <= 0) continue;
    const enough = sways.filter(id => CARDS[id].pull >= need);
    return { t: 'play', card: enough.length ? enough[0] : sways[sways.length - 1], slot: k };
  }
  return null;
}
export function greedyBot(s) {
  const me = s.toAct, P = s.p[me];
  const sw = swayPlay(s); if (sw) return sw;
  if (can(P, 'SPR') && s.slots.filter(n => toward(n, me) < 3).length >= 2) return { t: 'play', card: 'SPR' };
  if (can(P, 'RAL')) { const k = [0, 1, 2].filter(j => toward(s.slots[j], me) >= 1).sort((a, b) => s.slots[b].atk - s.slots[a].atk)[0]; if (k !== undefined) return { t: 'play', card: 'RAL', slot: k }; }
  if (can(P, 'DR2')) return { t: 'play', card: 'DR2' };
  if (can(P, 'SHD')) return { t: 'play', card: 'SHD' };
  if (can(P, 'EXI') && s.ndeck.length) { const k = [0, 1, 2].filter(j => toward(s.slots[j], me) <= -1).sort((a, b) => s.slots[b].atk - s.slots[a].atk)[0]; if (k !== undefined) return { t: 'play', card: 'EXI', slot: k }; }
  if (P.hand.includes('COIN') && P.hand.some(id => id !== 'COIN' && CARDS[id].cost === P.mana + 1)) return { t: 'play', card: 'COIN' };
  return { t: 'end' };
}
// ------------------------------------------------------------------ Racer
// Greedy without Exile or Shield: every card pulls or hits
export function racerBot(s) {
  const me = s.toAct, P = s.p[me];
  const sw = swayPlay(s); if (sw) return sw;
  if (can(P, 'SPR') && s.slots.filter(n => toward(n, me) < 3).length >= 2) return { t: 'play', card: 'SPR' };
  if (can(P, 'RAL')) { const k = [0, 1, 2].filter(j => toward(s.slots[j], me) >= 1).sort((a, b) => s.slots[b].atk - s.slots[a].atk)[0]; if (k !== undefined) return { t: 'play', card: 'RAL', slot: k }; }
  if (can(P, 'DR2')) return { t: 'play', card: 'DR2' };
  if (P.hand.includes('COIN') && P.hand.some(id => id !== 'COIN' && CARDS[id].cost === P.mana + 1)) return { t: 'play', card: 'COIN' };
  return { t: 'end' };
}

// ------------------------------------------------------------------ evaluation
// life, and what the Neutrals lean toward (a Neutral leaning far is hard to pull back)
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  const P = s.p[me], O = s.p[1 - me];
  let v = 1.0 * (P.life + P.shield * 0.7) - 1.0 * (O.life + O.shield * 0.7) + 0.5 * (P.hand.length - O.hand.length);
  for (const n of s.slots) { const t = toward(n, me); v += n.atk * (t >= 1 ? 0.5 + 0.25 * t : t <= -1 ? -0.5 + 0.25 * t : 0); }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 5));

// ------------------------------------------------------------------ Expert
// Determinized play-outs: every candidate action is followed by a play-out on a world where the
// cards this side cannot see (the other hand, both decks, the Neutral deck) are reshuffled; both
// sides play Greedy or Racer (drawn per play-out) with Rally-lethal sense and a little noise, to the end;
// successive halving spends the play-outs on the leaders, every arm seeing the same worlds.
function determinize(s, me, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - me], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng); shuffle(t.ndeck, rng);
  return t;
}
// lethal sense: a Rally that finishes him now
function lethalSense(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  if (!can(P, 'RAL')) return null;
  for (let k = 0; k < 3; k++) if (toward(s.slots[k], me) >= 1 && s.slots[k].atk >= O.life + O.shield) return { t: 'play', card: 'RAL', slot: k };
  return null;
}
export function candidates(s) {
  const me = s.toAct, seen = new Set(), out = [];
  for (const a of legalActions(s)) {
    if (a.t === 'play' && a.card === 'COIN' && !s.p[me].hand.some(id => id !== 'COIN' && CARDS[id].cost === s.p[me].mana + 1)) continue;
    const k = actionKey(a); if (!seen.has(k)) { seen.add(k); out.push(a); }
  }
  return out;
}
function policy(t, rng, eps, style) {
  if (eps > 0 && rng() < eps) return pick(candidates(t), rng);
  return lethalSense(t) || (style[t.toAct] === 'r' ? racerBot(t) : greedyBot(t));
}
function rollout(t, me, rng, eps) {
  const style = [rng() < 0.5 ? 'r' : 'g', rng() < 0.5 ? 'r' : 'g'];
  let steps = 0;
  while (t.winner === null && steps < 1500) { _act(t, policy(t, rng, eps, style)); steps++; }
  return winProb(t, me);
}
// Whole turns: every sequence of plays this turn (Draw 2 ends a sequence, since what it draws is
// unknown), told apart by the position it leaves; each is scored by play-outs from there.
const posKey = (t) => JSON.stringify([t.toAct, t.winner, t.slots.map(n => n.uid + ':' + n.loy), t.p.map(p => [p.life, p.shield, p.mana, p.hand.slice().sort().join()]), t.ndeck.length]);
function turnPlans(s, cap = 3000) {
  const me = s.toAct, out = new Map();
  let nodes = 0;
  const rec = (t, first) => {
    if (++nodes > cap) return;
    for (const a of candidates(t)) {
      const x = act(t, a), f = first || a;
      if (a.t === 'end' || a.card === 'DR2' || x.winner !== null || x.toAct !== me) {
        const k = posKey(x) + (a.card === 'DR2' ? 'd' : '');
        if (!out.has(k)) out.set(k, { first: f, t: x, done: a.t === 'end' || x.winner !== null || x.toAct !== me });
        continue;
      }
      rec(x, f);
    }
  };
  rec(s, null);
  return [...out.values()];
}
export const EXPERT = { playouts: 2000, eps: 0.05 };
export function expertBot({ playouts = 2000, eps = 0.05, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms0 = candidates(s);
    if (arms0.length === 1) return arms0[0];
    for (const a of arms0) { const t = act(s, a); if (t.winner === me) return a; }
    const plans = turnPlans(s);
    let alive = plans.map(p => ({ p, w: 0, n: 0 }));
    if (alive.length === 1) return alive[0].p.first;
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(3, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const seed = (rng() * 4294967296) >>> 0, wseed = (rng() * 4294967296) >>> 0;
        for (const st of alive) {
          // the plan's position, with what this side cannot see reshuffled (the same world for every plan)
          const t = determinize(st.p.t, me, makeRng(wseed));
          st.w += rollout(t, me, makeRng(seed), eps); st.n++;
        }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      if (timeMs && Date.now() - t0 > timeMs) break;
      alive = alive.slice(0, Math.ceil(alive.length / 2));
    }
    return alive[0].p.first;
  };
}
