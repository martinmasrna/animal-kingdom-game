// Bots for Siege clock. None reads a hidden card: the Expert deals the cards its seat cannot see
// (the opponent's hand and deck, its own deck order) afresh for every play-out.

import { CARDS, FIELD, WALL, GATE, clone, step, key, legalActions, aimable, canBlock, field, wall } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pickOf = (a, rng) => a[Math.floor(rng() * a.length)];
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const gateDmg = (m) => m.card === 'RM' ? 2 * m.atk : m.atk;

// ------------------------------------------------------------------ trivial bots (one action per call)
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }

// the most expensive affordable card that does something, with its target by a fixed rule
function ruleCard(s, { volley = true } = {}) {
  const me = s.toMove, P = s.p[me], att = me === s.att;
  const room = P.units.length < (att ? FIELD : WALL);
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].cost <= P.mana).sort((a, b) => CARDS[b].cost - CARDS[a].cost || (CARDS[a].kind === 'Unit' ? -1 : 1));
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'Unit') { if (room) return { t: 'play', card: id }; continue; }
    if (id === 'AD' || id === 'DD') { if (P.deck.length) return { t: 'play', card: id }; continue; }
    if (id === 'RP') { if (s.gate < GATE) return { t: 'play', card: id }; continue; }
    if (id === 'OI') { if (field(s).length) return { t: 'play', card: id }; continue; }
    if (id === 'VO') {
      if (!volley || !wall(s).length) continue;
      // the Wall unit it kills with the most attack, else the one with the least health
      let bi = -1, bk = -Infinity;
      wall(s).forEach((m, i) => { const k = (m.hp <= 2 ? 100 + m.atk : -m.hp); if (k > bk) { bk = k; bi = i; } });
      return { t: 'play', card: id, i: bi };
    }
    if (id === 'RU') {
      let bi = -1, bk = -1;
      P.units.forEach((m, i) => { if (m.fresh && !m.ready && gateDmg(m) > bk) { bk = gateDmg(m); bi = i; } });
      if (bi >= 0) return { t: 'play', card: id, i: bi };
      continue;
    }
    if (id === 'SN') { const i = aimRule(s, 2); if (i >= 0) return { t: 'play', card: id, i }; continue; }
  }
  return null;
}
// a Field target for n damage: the unit it kills that hits the Gate hardest, else the hardest hitter
function aimRule(s, n) {
  let bi = -1, bk = -Infinity;
  field(s).forEach((m, i) => { if (!aimable(s, i)) return; const k = (m.hp <= n ? 100 : 0) + gateDmg(m); if (k > bk) { bk = k; bi = i; } });
  return bi;
}
// blocks by the fixed rule: each attacker (hardest Gate hit first) blocked by the weakest Wall
// unit that destroys it and survives; Wall units left over block the hardest hitters left
export function blockPlan(s) {
  const F = field(s), Wl = wall(s), plan = new Array(Wl.length).fill(-1), used = new Set();
  const atks = F.map((m, i) => i).filter(i => F[i].sent && F[i].card !== 'CL').sort((a, b) => gateDmg(F[b]) - gateDmg(F[a]));
  const taken = new Set();
  for (const ai of atks) {
    let bw = -1;
    Wl.forEach((w, wi) => { if (!used.has(wi) && canBlock(s, w) && w.atk >= F[ai].hp && F[ai].atk < w.hp && (bw < 0 || w.hp + w.atk < Wl[bw].hp + Wl[bw].atk)) bw = wi; });
    if (bw >= 0) { plan[bw] = ai; used.add(bw); taken.add(ai); }
  }
  const left = atks.filter(ai => !taken.has(ai));
  Wl.map((w, wi) => wi).filter(wi => !used.has(wi) && canBlock(s, Wl[wi])).sort((a, b) => Wl[b].hp - Wl[a].hp).forEach(wi => { const ai = left.shift(); if (ai != null) plan[wi] = ai; });
  return plan;
}
function ruleBlock(s) {
  const a = blockPlan(s)[s.bi];
  const m = a >= 0 ? field(s)[a] : null;
  return { t: 'block', a: m && m.blockedBy == null ? a : -1 };
}
function ruleShoot(s) { return { t: 'shoot', i: aimRule(s, 1) }; }
// Greedy (the spec's): plays the most expensive affordable cards; the Attacker then sends every
// ready unit; the Defender blocks and shoots by the fixed rules above.
export function greedyBot(s) {
  if (s.phase === 'block') return ruleBlock(s);
  if (s.phase === 'shoot') return ruleShoot(s);
  const c = ruleCard(s);
  if (c) return c;
  if (s.phase === 'att') { const i = s.p[s.att].units.findIndex(m => m.ready && !m.sent); if (i >= 0) return { t: 'send', i }; }
  return { t: 'end' };
}
// Racer (Attacker only): as Greedy, but never spends on the Wall (no Volley); sends everything.
export function racerBot(s) {
  if (s.toMove !== s.att) return greedyBot(s);
  const c = ruleCard(s, { volley: false });
  if (c) return c;
  const i = s.p[s.att].units.findIndex(m => m.ready && !m.sent);
  return i >= 0 ? { t: 'send', i } : { t: 'end' };
}

// ------------------------------------------------------------------ Expert: rollouts
// Each legal action is tried in R worlds dealt from what the mover cannot see (the same R worlds
// for every action), and each world is played to the end of the game by Greedy on both sides.
// The action with the best mean wins (a win is 1; a small share of the margin breaks ties
// between lost or won causes). Since the game lasts at most ten rounds, every play-out ends.
function determinize(s, viewer, rng) {
  const t = clone(s);
  const O = t.p[1 - viewer], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[viewer].deck, rng);
  t.seed = (rng() * 4294967296) >>> 0;
  return t;
}
function playout(t, policy) { let guard = 0; while (t.winner === null && guard++ < 2000) step(t, policy(t)); return t; }
function scoreFor(t, me) {
  const won = t.winner === me ? 1 : 0;
  const margin = me === t.att ? (GATE - t.gate) / GATE : t.gate / GATE;
  return won + 0.05 * margin;
}
// distinct actions: blocks of equal attackers, shots at equal units and sends of equal units merged
const usig = (m) => m.card + m.hp + (m.ready ? 'r' : '') + (m.sent ? 's' : '') + (m.blockedBy != null ? 'b' : '');
export function cands(s) {
  const seen = new Set(), out = [];
  for (const a of legalActions(s)) {
    let k = key(a);
    if (a.t === 'send') k = 's' + usig(s.p[s.att].units[a.i]);
    if (a.t === 'block' && a.a >= 0) k = 'b' + usig(field(s)[a.a]);
    if (a.t === 'shoot' || (a.t === 'play' && a.card === 'SN')) k = a.t + (a.card || '') + usig(field(s)[a.i]);
    if (a.t === 'play' && a.card === 'VO') k = 'pVO' + usig(wall(s)[a.i]);
    if (a.t === 'play' && a.card === 'RU') k = 'pRU' + usig(s.p[s.att].units[a.i]);
    if (!seen.has(k)) { seen.add(k); out.push(a); }
  }
  return out;
}
export function rolloutBot({ R = 64 } = {}) {
  return (s, rng) => {
    const me = s.toMove, acts = cands(s);
    if (acts.length === 1) return acts[0];
    const seeds = Array.from({ length: R }, () => (rng() * 4294967296) >>> 0);
    let best = acts[0], bv = -Infinity;
    for (const a of acts) {
      let tot = 0;
      for (let r = 0; r < R; r++) {
        const t = determinize(s, me, makeRng(seeds[r]));
        step(t, a);
        tot += scoreFor(playout(t, greedyBot), me);
      }
      if (tot > bv + 1e-9) { bv = tot; best = a; }
    }
    return best;
  };
}
export const EXPERT = { R: 64 };
export function expertBot(opts = EXPERT) { return rolloutBot(opts); }

export const TRIVIAL = { random: randomBot, greedy: greedyBot, racer: racerBot };
export function meaning(s, a) {
  if (a.t === 'send') return 's' + usig(s.p[s.att].units[a.i]);
  if (a.t === 'block') return a.a < 0 ? 'b-' : 'b' + usig(field(s)[a.a]);
  if (a.t === 'shoot') return 'x' + usig(field(s)[a.i]);
  if (a.t === 'play' && a.i != null) return 'p' + a.card + usig((a.card === 'VO' ? wall(s) : field(s))[a.i] || { card: '?' });
  return key(a);
}
