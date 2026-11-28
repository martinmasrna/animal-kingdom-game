// Bots for Lanes and scale. None reads a hidden card: the Expert reshuffles everything its seat
// cannot see (its own deck order, the opponent's hand and deck, the shuffle seed) before each
// search iteration.

import { CARDS, LANES, WIN, dir, clone, step, key, order, legalActions } from './engine.js';

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
const sig = (m) => m ? m.card + m.hp : '-';
const toward = (s, side) => dir(side) * s.scale; // how far the scale leans to `side`
// what my units facing empty slots put on the scale in my next combat
function openAtk(s, side) { const P = s.p[side], O = s.p[1 - side]; let n = 0; for (let l = 0; l < LANES; l++) if (P.slots[l] && !O.slots[l]) n += P.slots[l].atk; return n; }

// Candidate actions: the legal actions in canonical order within the turn, Hit 2 aimed only at
// enemy units, and lanes that look the same (same unit of mine and of his in them) merged.
export function cands(s) {
  if (s.winner !== null) return [];
  const me = s.turn, seen = new Set(), out = [];
  for (const a of legalActions(s)) {
    if (a.t !== 'end' && (order(a) < s.last || (a.card === 'H2' && a.side === me))) continue;
    const k = meaning(s, a);
    if (!seen.has(k)) { seen.add(k); out.push(a); }
  }
  return out;
}

// ------------------------------------------------------------------ trivial bots (one action per call)
export function randomBot(s, rng) {
  const out = [];
  const P = s.p[s.turn];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { for (let l = 0; l < LANES; l++) if (!P.slots[l]) out.push({ t: 'play', card: id, lane: l }); }
    else if (id === 'H2') { for (const side of [0, 1]) for (let l = 0; l < LANES; l++) if (s.p[side].slots[l]) out.push({ t: 'play', card: id, side, lane: l }); }
    else if (id === 'SF') { for (let f = 0; f < LANES; f++) if (P.slots[f]) for (let t = 0; t < LANES; t++) if (!P.slots[t]) out.push({ t: 'play', card: id, from: f, to: t }); }
    else out.push({ t: 'play', card: id });
  }
  out.push({ t: 'end' });
  return pickOf(out, rng);
}
// Greedy (the spec's rule), most expensive card first: a unit goes opposite an enemy unit it
// destroys in this combat, else facing an empty enemy slot, else opposite the enemy unit with the
// most attack; Hit 2 at the enemy unit with the most attack it kills, else the one with the most
// attack; Shift moves a blocked unit to a lane facing an empty slot; Shove always.
function greedyLane(s, id) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me], c = CARDS[id];
  const empty = []; for (let l = 0; l < LANES; l++) if (!P.slots[l]) empty.push(l);
  if (!empty.length) return -1;
  let best = -1, bk = -1;
  for (const l of empty) if (O.slots[l] && c.atk >= O.slots[l].hp && O.slots[l].atk > bk) { bk = O.slots[l].atk; best = l; }
  if (best >= 0) return best;
  const open = empty.filter(l => !O.slots[l]);
  if (open.length) return open[0];
  for (const l of empty) if (O.slots[l].atk > bk) { bk = O.slots[l].atk; best = l; }
  return best;
}
function shiftMove(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const to = [...Array(LANES).keys()].find(l => !P.slots[l] && !O.slots[l]);
  if (to === undefined) return null;
  let from = -1, bk = 0;
  for (let l = 0; l < LANES; l++) if (P.slots[l] && O.slots[l] && P.slots[l].atk > bk) { bk = P.slots[l].atk; from = l; }
  return from >= 0 ? { t: 'play', card: 'SF', from, to } : null;
}
function trivial(s, racer) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].cost <= P.mana && id !== 'COIN').sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'Unit') {
      if (racer) { const l = [...Array(LANES).keys()].find(l => !P.slots[l] && !O.slots[l]); if (l !== undefined) return { t: 'play', card: id, lane: l }; continue; }
      const l = greedyLane(s, id); if (l >= 0) return { t: 'play', card: id, lane: l }; continue;
    }
    if (id === 'H2') {
      if (racer) continue;
      let best = -1, bk = -1;
      for (let l = 0; l < LANES; l++) { const m = O.slots[l]; if (m) { const k = (m.hp <= 2 ? 100 : 0) + m.atk; if (k > bk) { bk = k; best = l; } } }
      if (best >= 0) return { t: 'play', card: id, side: 1 - me, lane: best };
      continue;
    }
    if (id === 'SF') { const m = shiftMove(s); if (m) return m; continue; }
    if (id === 'SV') return { t: 'play', card: id };
  }
  if (P.hand.includes('COIN') && P.hand.some(id => id !== 'COIN' && CARDS[id].cost === P.mana + 1)) return { t: 'play', card: 'COIN' };
  return { t: 'end' };
}
export function greedyBot(s) { return trivial(s, false); }
// Racer: units only into lanes with no enemy unit opposite, Shift out of blocked lanes, Shove; never Hit 2.
export function racerBot(s) { return trivial(s, true); }

// ------------------------------------------------------------------ Expert: ISMCTS
const uv = (m) => m.atk * 1.0 + m.hp * 0.5;
// Rollout policy: finish when the open lanes (and a Shove) reach the end; otherwise block the
// lanes that threaten me when the scale is close, kill what Hit 2 kills, place the most expensive
// unit where it kills or runs free, shift a blocked attacker, Shove. A little noise.
function policy(s, rng) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (rng() < 0.08) return pickOf(cands(s), rng);
  const need = WIN - toward(s, me), mine = openAtk(s, me);
  if (mine >= need) return { t: 'end' };
  if (mine + 1 >= need && P.hand.includes('SV') && P.mana >= 2) return { t: 'play', card: 'SV' };
  const theirs = openAtk(s, 1 - me), danger = WIN + toward(s, me); // what he needs
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].cost <= P.mana && id !== 'COIN');
  ids.sort((a, b) => CARDS[b].cost - CARDS[a].cost + (rng() - 0.5) * 1.5);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'Unit') {
      const empty = []; for (let l = 0; l < LANES; l++) if (!P.slots[l]) empty.push(l);
      if (!empty.length) continue;
      let best = -1, bk = -Infinity;
      for (const l of empty) {
        const d = O.slots[l]; let k;
        if (d) k = (c.atk >= d.hp ? 3 + uv(d) : 0) + (theirs >= danger - 1 ? 2 * d.atk : 0.6 * d.atk);
        else k = 1 + c.atk + (rng() - 0.5);
        if (k > bk) { bk = k; best = l; }
      }
      return { t: 'play', card: id, lane: best };
    }
    if (id === 'H2') {
      let best = -1, bk = 0;
      for (let l = 0; l < LANES; l++) { const m = O.slots[l]; if (m && m.hp <= 2) { const k = uv(m) + (P.slots[l] ? P.slots[l].atk : 0); if (k > bk) { bk = k; best = l; } } }
      if (best >= 0) return { t: 'play', card: id, side: 1 - me, lane: best };
      continue;
    }
    if (id === 'SF') { const m = shiftMove(s); if (m && P.slots[m.from].atk >= 2) return m; continue; }
    if (id === 'SV') return { t: 'play', card: id };
  }
  return { t: 'end' };
}
// A position's worth to seat 0 as a win chance. Settled: a mover whose open lanes (and Shoves it
// can pay for) reach the end wins in its own combat, which nothing can stop.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  const mv = s.toMove, P = s.p[mv];
  const shoves = Math.min(P.hand.filter(x => x === 'SV').length, Math.floor(P.mana / 2));
  if (openAtk(s, mv) + shoves >= WIN - toward(s, mv)) return mv === 0 ? 0.96 : 0.04;
  let b = 0;
  for (const side of [0, 1]) { const sg = side === 0 ? 1 : -1; for (const m of s.p[side].slots) if (m) b += sg * uv(m); }
  const v = 1.0 * s.scale + 0.45 * (openAtk(s, 0) - openAtk(s, 1)) + 0.2 * b + 0.3 * (s.p[0].hand.length - s.p[1].hand.length) + (mv === 0 ? 0.5 : -0.5);
  return 1 / (1 + Math.exp(-v / 2));
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
// what an action means, lanes that look the same counted as one
export function meaning(s, a) {
  if (a.t === 'end') return 'e';
  const me = s.turn, P = s.p[me], O = s.p[1 - me], ls = (l) => sig(P.slots[l]) + '|' + sig(O.slots[l]);
  if (a.card === 'H2') return 'H2' + a.side + ':' + (a.side === me ? sig(P.slots[a.lane]) : ls(a.lane));
  if (a.card === 'SF') return 'SF' + ls(a.from) + '>' + ls(a.to);
  if (CARDS[a.card].kind === 'Unit') return a.card + '@' + ls(a.lane);
  return a.card;
}
