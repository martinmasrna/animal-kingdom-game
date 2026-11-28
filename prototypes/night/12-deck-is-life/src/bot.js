// Bots for Deck is life. None reads a hidden card: the Expert reshuffles everything its seat
// cannot see (its own deck order, the opponent's hand and deck, the shuffle seed) before each
// search iteration.

import { CARDS, BOARD, clone, step, isLegal, key } from './engine.js';

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

// ------------------------------------------------------------------ shared helpers
const VAL = { ST: 1.5, RA: 3, GU: 2.5, LI: 4, HE: 5, BI: 6, H2: 2, B3: 4.5, D2: 2, RC: 3, COIN: 0 };
const unitVal = (m) => m.atk * 1.1 + m.hp * 0.7;
export function bestRecover(P) { return P.discard.slice().sort((a, b) => VAL[b] - VAL[a]).slice(0, 3); }
const sig = (u) => u.card + u.hp + (u.ready ? 'r' : '');

// Candidate actions: every legal kind of action, with Recover's choice fixed to the three best
// cards, Hit 2 aimed only at enemy units, identical units merged.
export function cands(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (id === 'H2') { const seen = new Set(); O.board.forEach((m, i) => { if (!seen.has(sig(m))) { seen.add(sig(m)); out.push({ t: 'play', card: id, side: 1 - me, i }); } }); }
    else if (id === 'RC') { if (P.discard.length) out.push({ t: 'play', card: id, pick: bestRecover(P) }); }
    else out.push({ t: 'play', card: id });
  }
  const seenA = new Set();
  P.board.forEach((m, from) => {
    if (!m.ready || seenA.has(sig(m))) return; seenA.add(sig(m));
    out.push({ t: 'attack', from, to: -1 });
    const seenT = new Set();
    O.board.forEach((d, to) => { if (!seenT.has(sig(d))) { seenT.add(sig(d)); out.push({ t: 'attack', from, to }); } });
  });
  out.push({ t: 'end' });
  return out;
}

// ------------------------------------------------------------------ trivial bots (one action per call)
// Random: a uniform choice among the kinds of action, ending the turn included.
export function randomBot(s, rng) {
  const P = s.p[s.turn], opts = [];
  for (const a of cands(s)) {
    if (a.card === 'RC') opts.push({ t: 'play', card: 'RC', pick: shuffle(P.discard.slice(), rng).slice(0, 3) });
    else if (a.card === 'H2') { for (const side of [0, 1]) s.p[side].board.forEach((_, i) => opts.push({ t: 'play', card: 'H2', side, i })); }
    else opts.push(a);
  }
  const seen = new Set();
  return pickOf(opts.filter(a => { const k = key(a); if (seen.has(k)) return false; seen.add(k); return true; }), rng);
}
// Greedy (the spec's rule): the most expensive affordable card first (Draw 2 only while its deck
// holds 3 or more, Recover whenever it has a discard, Hit 2 at the enemy unit with the most attack
// it kills, else the one with the most attack); then each ready unit attacks an enemy unit it
// destroys and survives (the one with the most attack), otherwise the enemy player.
function greedyPlay(s, racer) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const ok = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit' && P.board.length >= BOARD) continue;
    if (id === 'D2' && P.deck.length < 3) continue;
    if (id === 'RC' && !P.discard.length) continue;
    if (id === 'H2' && (racer || !O.board.length)) continue;
    if (id === 'COIN') continue;
    ok.push(id);
  }
  if (!ok.length) {
    // the Coin only when it buys a card
    if (P.hand.includes('COIN') && P.hand.some(id => id !== 'COIN' && CARDS[id].cost === P.mana + 1 && (CARDS[id].kind !== 'Unit' || P.board.length < BOARD))) return { t: 'play', card: 'COIN' };
    return null;
  }
  ok.sort((a, b) => CARDS[b].cost - CARDS[a].cost || (CARDS[a].kind === 'Unit' ? -1 : 1));
  const id = ok[0];
  if (id === 'H2') {
    let best = -1, bk = -1;
    O.board.forEach((m, i) => { const k = (m.hp <= 2 ? 100 : 0) + m.atk; if (k > bk) { bk = k; best = i; } });
    return { t: 'play', card: id, side: 1 - me, i: best };
  }
  if (id === 'RC') return { t: 'play', card: id, pick: bestRecover(P) };
  return { t: 'play', card: id };
}
function greedyAttack(s, racer) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const from = P.board.findIndex(m => m.ready);
  if (from < 0) return null;
  const m = P.board[from];
  if (!racer) {
    let to = -1, bk = -1;
    O.board.forEach((d, i) => { if (m.atk >= d.hp && d.atk < m.hp && d.atk > bk) { bk = d.atk; to = i; } });
    if (to >= 0) return { t: 'attack', from, to };
  }
  return { t: 'attack', from, to: -1 };
}
export function greedyBot(s) { return greedyPlay(s, false) || greedyAttack(s, false) || { t: 'end' }; }
// Racer: Greedy's plays without Hit 2, every attack at the enemy player.
export function racerBot(s) { return greedyPlay(s, true) || greedyAttack(s, true) || { t: 'end' }; }

// ------------------------------------------------------------------ Expert: ISMCTS
// Rollout policy: lethal when it is there; trades that kill and survive (or kill something worth
// more); the most expensive card; otherwise face. A little noise keeps the play-outs varied.
function policy(s, rng) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (rng() < 0.08) return pickOf(cands(s), rng);
  // lethal: ready attack plus affordable burn reach the whole deck
  let face = 0; for (const m of P.board) if (m.ready) face += m.atk;
  const burns = P.hand.filter(x => x === 'B3').length;
  const nb = Math.min(burns, Math.floor(P.mana / 3));
  if (face + 3 * nb >= O.deck.length) {
    if (nb && P.hand.includes('B3') && P.mana >= 3) return { t: 'play', card: 'B3' };
    const from = P.board.findIndex(m => m.ready);
    if (from >= 0) return { t: 'attack', from, to: -1 };
  }
  // plays
  const ok = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana || id === 'COIN') continue;
    if (c.kind === 'Unit' && P.board.length >= BOARD) continue;
    if (id === 'D2' && P.deck.length < 8) continue;
    if (id === 'RC' && P.discard.length < 2) continue;
    if (id === 'H2' && !O.board.some(m => m.hp <= 2)) continue;
    ok.push(id);
  }
  if (ok.length) {
    ok.sort((a, b) => CARDS[b].cost - CARDS[a].cost + (rng() - 0.5) * 1.2);
    const id = ok[0];
    if (id === 'H2') { let best = -1, bk = -1; O.board.forEach((m, i) => { if (m.hp <= 2 && unitVal(m) > bk) { bk = unitVal(m); best = i; } }); return { t: 'play', card: id, side: 1 - me, i: best }; }
    if (id === 'RC') return { t: 'play', card: id, pick: bestRecover(P) };
    return { t: 'play', card: id };
  }
  // attacks
  const from = P.board.findIndex(m => m.ready);
  if (from >= 0) {
    const m = P.board[from];
    let to = -1, bk = 0;
    O.board.forEach((d, i) => {
      if (m.atk < d.hp) return;
      const gain = d.atk >= m.hp ? unitVal(d) - unitVal(m) : unitVal(d) + 1;
      if (gain > bk) { bk = gain; to = i; }
    });
    return { t: 'attack', from, to };
  }
  return { t: 'end' };
}
// A position's worth to seat 0, as a win chance: cards left to draw (life), board, hand.
// Nothing blocks in this game, so two cases are settled already: the side that draws next with
// an empty deck is lost, and a mover whose ready attack and affordable Burns cover the other
// deck has won. Otherwise a deck counts for more the lower it gets.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  const mv = s.toMove, P = s.p[mv], O = s.p[1 - mv];
  const win = (side) => side === 0 ? 0.97 : 0.03;
  if (!O.deck.length) return win(mv);
  let reach = 0; for (const m of P.board) if (m.ready) reach += m.atk;
  reach += 3 * Math.min(P.hand.filter(x => x === 'B3').length, Math.floor(P.mana / 3));
  if (reach >= O.deck.length) return win(mv);
  const life = (d) => d - 0.6 * Math.max(0, 10 - d);
  const side = (k) => { const p = s.p[k]; let b = 0; for (const m of p.board) b += unitVal(m); return life(p.deck.length) + 0.75 * b + 0.8 * p.hand.length; };
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
// what an action means, independent of which of two identical units does it
export function meaning(s, a) {
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (a.t === 'attack') return 'a' + sig(P.board[a.from]) + '>' + (a.to < 0 ? 'face' : sig(O.board[a.to]));
  if (a.card === 'H2') return 'H2>' + a.side + sig(s.p[a.side].board[a.i]);
  if (a.card === 'RC') return 'RC';
  return a.t === 'end' ? 'end' : 'p' + a.card;
}
