// Bots for the Response duel. None reads a hidden card: the Expert reshuffles everything its
// seat cannot see (its own deck order, the opponent's hand and deck, the shuffle seed) before
// each search iteration.

import { CARDS, LIFE, clone, step, key, legalActions, answers } from './engine.js';

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
const isDmg = (id) => CARDS[id].kind === 'Spell' && CARDS[id].dmg > 0;
const ratio = (id) => (CARDS[id].dmg + (CARDS[id].heal || 0) * 0) / CARDS[id].cost;

export function cands(s) { return legalActions(s); }

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }
// Greedy (the spec's rule): the spell with the most damage per mana it can pay for, again and
// again, then Study, spending all its mana; the Coin when it buys a spell. With stored mana it
// answers: Cancel against 5 damage or more, Ward against the rest.
function greedyMain(s) {
  const P = s.p[s.toMove];
  const ok = P.hand.filter(id => CARDS[id].kind === 'Spell' && CARDS[id].cost <= P.mana);
  const dmg = ok.filter(isDmg).sort((a, b) => ratio(b) - ratio(a) || CARDS[b].dmg - CARDS[a].dmg);
  if (dmg.length) return { t: 'cast', card: dmg[0] };
  if (ok.includes('ST')) return { t: 'cast', card: 'ST' };
  if (P.hand.includes('COIN') && P.hand.some(id => CARDS[id].kind === 'Spell' && CARDS[id].cost === P.mana + 1)) return { t: 'cast', card: 'COIN' };
  return { t: 'end' };
}
export function greedyBot(s) {
  if (!s.pending) return greedyMain(s);
  const P = s.p[s.toMove], id = s.pending.card, ok = (r) => P.hand.includes(r) && CARDS[r].cost <= P.stored && answers(r, id);
  if (!isDmg(id)) return { t: 'allow' };
  if (CARDS[id].dmg >= 5 && ok('CA')) return { t: 'respond', card: 'CA' };
  if (ok('WA')) return { t: 'respond', card: 'WA' };
  return { t: 'allow' };
}
// Racer: Greedy's casting, never answers.
export function racerBot(s) { return s.pending ? { t: 'allow' } : greedyMain(s); }

// ------------------------------------------------------------------ Expert: ISMCTS
// Rollout policy: answer big spells (Cancel, else Mirror a Blast, else Ward); on its own turn
// finish the opponent when the damage in hand is enough and nothing is stored against it,
// otherwise sometimes keep mana back for a Response it holds, and cast the best damage.
function policy(s, rng) {
  const me = s.toMove, P = s.p[me], O = s.p[1 - me];
  if (rng() < 0.07) return pickOf(legalActions(s), rng);
  if (s.pending) {
    const id = s.pending.card, ok = (r) => P.hand.includes(r) && CARDS[r].cost <= P.stored && answers(r, id);
    const d = id === 'SG' ? 6 : CARDS[id].dmg;
    if (d >= 5 && ok('CA')) return { t: 'respond', card: 'CA' };
    if (id === 'BL' && ok('MI')) return { t: 'respond', card: 'MI' };
    if (d >= 2 && ok('WA') && (d >= 5 || rng() < 0.6)) return { t: 'respond', card: 'WA' };
    if (d >= 2 && ok('MI') && rng() < 0.5) return { t: 'respond', card: 'MI' };
    return { t: 'allow' };
  }
  const ok = P.hand.filter(id => CARDS[id].kind === 'Spell' && CARDS[id].cost <= P.mana);
  const dmg = ok.filter(isDmg);
  const total = dmg.reduce((n, id) => n + (id === 'SG' ? 0 : CARDS[id].dmg), 0);
  if (dmg.length && O.stored === 0 && total >= O.life) return { t: 'cast', card: dmg.sort((a, b) => CARDS[b].dmg - CARDS[a].dmg)[0] };
  // keep mana for a held Response now and then
  const hold = P.hand.includes('CA') ? 3 : P.hand.includes('MI') ? 2 : P.hand.includes('WA') ? 1 : 0;
  const budget = hold && rng() < 0.45 ? P.mana - hold : P.mana;
  const fit = dmg.filter(id => CARDS[id].cost <= budget).sort((a, b) => CARDS[b].dmg - CARDS[a].dmg + (rng() - 0.5) * 2);
  if (fit.length) return { t: 'cast', card: fit[0] };
  if (ok.includes('ST') && CARDS.ST.cost <= budget && P.hand.length < 7) return { t: 'cast', card: 'ST' };
  if (P.hand.includes('COIN') && P.hand.some(id => CARDS[id].kind === 'Spell' && CARDS[id].cost === P.mana + 1)) return { t: 'cast', card: 'COIN' };
  return { t: 'end' };
}
// A position's worth to seat 0 as a win chance: life, cards in hand, Sieges still to tick,
// stored mana with a Response behind it. Settled: a mover with the damage in hand and mana to
// cast it, against nothing stored, wins.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  const mv = s.toMove;
  if (!s.pending) {
    const P = s.p[mv], O = s.p[1 - mv];
    if (O.stored === 0) {
      let mana = P.mana, d = 0;
      for (const id of P.hand.filter(isDmg).filter(id => id !== 'SG').sort((a, b) => ratio(b) - ratio(a))) if (CARDS[id].cost <= mana) { mana -= CARDS[id].cost; d += CARDS[id].dmg; }
      if (d >= O.life) return mv === 0 ? 0.97 : 0.03;
    }
  }
  const side = (k) => {
    const p = s.p[k], o = s.p[1 - k];
    let v = p.life + 1.2 * p.hand.length + p.sieges.reduce((n, g) => n + g.ticks * g.dmg, 0) * 0.8;
    if (p.stored && p.hand.some(id => CARDS[id].kind === 'Response')) v += 0.5 * Math.min(p.stored, 3);
    return v - 0.15 * Math.max(0, 8 - p.life) * 2;
  };
  return 1 / (1 + Math.exp(-(side(0) - side(1)) / 5));
}
function determinize(s, viewer, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - viewer], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[viewer].deck, rng);
  return t;
}
export const GAME = { cands, key, obsKey: (s, a) => key(a), determinize, step, policy, value0, turnNo: (s) => s.turnNo };

// Single-observer ISMCTS: each iteration deals a world consistent with what the mover has seen,
// walks the shared tree by UCB over the moves legal in that world, expands one, plays out
// `plies` turns with the rollout policy and scores the end by value0.
export function ismcts(s, rng, G, { iters = 1500, c = 0.7, plies = 4, stats = null } = {}) {
  const me = s.toMove, t00 = G.turnNo(s);
  const acts0 = G.cands(s);
  if (acts0.length === 1) return acts0[0];
  const root = { n: 0, kids: new Map() };
  // a win sooner is worth a little more than a win later, a loss later a little more than one now
  const final = (d) => { const k = 0.01 * Math.min(30, G.turnNo(d) - t00); return d.winner === 0 ? 1 - k : d.winner === 1 ? k : 0.5; };
  for (let it = 0; it < iters; it++) {
    const d = G.determinize(s, me, rng);
    let node = root; const path = [];
    while (d.winner === null) {
      const groups = new Map();
      for (const a of G.cands(d)) { const k = G.obsKey(d, a, me); const g = groups.get(k); if (g) g.push(a); else groups.set(k, [a]); }
      const untried = [];
      for (const k of groups.keys()) { const ch = node.kids.get(k); if (ch) ch.avail++; else untried.push(k); }
      let k, fresh = false;
      if (untried.length) { k = untried[Math.floor(rng() * untried.length)]; node.kids.set(k, { n: 0, w: 0, avail: 1, kids: new Map(), mover: d.toMove }); fresh = true; }
      else {
        let best = -Infinity;
        for (const kk of groups.keys()) { const ch = node.kids.get(kk); const u = ch.w / ch.n + c * Math.sqrt(Math.log(ch.avail) / ch.n); if (u > best) { best = u; k = kk; } }
      }
      const g = groups.get(k);
      G.step(d, g.length === 1 ? g[0] : g[Math.floor(rng() * g.length)]);
      node = node.kids.get(k); path.push(node);
      if (fresh) break;
    }
    const t0 = G.turnNo(d);
    let guard = 0;
    while (d.winner === null && G.turnNo(d) - t0 < plies && guard++ < 400) G.step(d, G.policy(d, rng));
    const v0 = d.winner !== null ? final(d) : G.value0(d);
    for (const nd of path) { nd.n++; nd.w += nd.mover === 0 ? v0 : 1 - v0; }
    root.n++;
  }
  if (stats) for (const [k, ch] of root.kids) stats[k] = { n: ch.n, w: +(ch.w / ch.n).toFixed(3) };
  let bestK = null, bn = -1, bw = -1;
  for (const [k, ch] of root.kids) { const w = ch.w / ch.n; if (ch.n > bn || (ch.n === bn && w > bw)) { bn = ch.n; bw = w; bestK = k; } }
  return acts0.find(a => G.obsKey(s, a, me) === bestK) || acts0[0];
}
export const EXPERT = { iters: 1500, c: 0.7, plies: 4 };
export function expertBot(opts = EXPERT) { return (s, rng) => ismcts(s, rng, GAME, opts); }

export const TRIVIAL = { random: randomBot, greedy: greedyBot, racer: racerBot };
export function meaning(s, a) { return key(a); }
