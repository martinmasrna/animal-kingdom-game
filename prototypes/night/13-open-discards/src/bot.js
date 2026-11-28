// Bots for Open discards. None reads a hidden card: the Expert reshuffles everything its seat
// cannot see (its own deck order, the opponent's hand and deck) before each search iteration.
// Discard piles are face-up, so every bot sees both.

import { CARDS, BOARD, TAX, clone, step, key, legalActions } from './engine.js';

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
const sig = (u) => u.card + u.hp + (u.ready ? 'r' : '');
const unitVal = (m) => m.atk * 1.5 + m.hp;

// every card the mover could play now, from hand and (once a turn) from the opponent's discard
function sources(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) out.push({ id, disc: false, price: CARDS[id].cost });
  if (!P.took) for (const id of new Set(O.discard)) out.push({ id, disc: true, price: CARDS[id].cost + TAX });
  return out.filter(x => x.price <= P.mana && (CARDS[x.id].kind !== 'Unit' || P.board.length < BOARD));
}

// Candidate actions for the search: spells only at enemy units and the enemy hero, identical
// units merged, the Coin only when it lets a card be played that could not be otherwise.
export function cands(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  const coinHelps = () => P.hand.some(x => CARDS[x].cost === P.mana + 1) || (!P.took && O.discard.some(x => CARDS[x].cost + TAX === P.mana + 1));
  for (const { id, disc } of sources(s)) {
    const c = CARDS[id];
    if (c.kind === 'Unit') out.push({ t: 'play', card: id, disc });
    else if (c.kind === 'Coin') { if (coinHelps()) out.push({ t: 'play', card: id, disc }); }
    else {
      out.push({ t: 'play', card: id, disc, side: 1 - me, i: -1 });
      const seen = new Set(); O.board.forEach((m, i) => { if (!seen.has(sig(m))) { seen.add(sig(m)); out.push({ t: 'play', card: id, disc, side: 1 - me, i }); } });
    }
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
// Random: a uniform choice among every legal action, ending the turn included.
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }

// Lethal: ready attacks plus the burn this turn's mana (and the Coin) buys, from hand and at most
// one from his discard, reach his health. Nothing can block, so this is exact. Returns the next
// action of such a turn, or null.
export function lethalStep(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  let face = 0, from = -1;
  P.board.forEach((m, i) => { if (m.ready) { face += m.atk; if (from < 0) from = i; } });
  if (face >= O.hp) return { t: 'attack', from, to: -1 };
  const spells = P.hand.filter(id => CARDS[id].kind === 'Spell').map(id => ({ id, disc: false, price: CARDS[id].cost }));
  if (!P.took) for (const id of new Set(O.discard)) if (CARDS[id].kind === 'Spell') spells.push({ id, disc: true, price: CARDS[id].cost + TAX });
  const coin = P.hand.includes('COIN') ? 1 : 0;
  let best = null;
  for (let mask = 1; mask < (1 << spells.length); mask++) {
    let cost = 0, dmg = 0, discs = 0, first = null;
    for (let k = 0; k < spells.length; k++) if (mask & (1 << k)) { const x = spells[k]; cost += x.price; dmg += CARDS[x.id].dmg; if (x.disc) discs++; first = first || x; }
    if (discs > 1 || cost > P.mana + coin || face + dmg < O.hp) continue;
    if (!best || cost < best.cost) best = { cost, first, coin: cost > P.mana };
  }
  if (!best) return null;
  if (best.coin) return { t: 'play', card: 'COIN', disc: false };
  return { t: 'play', card: best.first.id, disc: best.first.disc, side: 1 - me, i: -1 };
}

// Greedy (the template's, choosing among hand cards and the opponent's discard alike): lethal
// when it is there; otherwise the single action that most improves a fixed worth (health, worth
// more below 12; units on the board; cards in hand), and the turn ends when none does.
export const W = { hp: 0.5, low: 0.5, lowAt: 12, atk: 1.5, mhp: 1, card: 2 };
const hpWorth = (h) => W.hp * h - W.low * Math.max(0, W.lowAt - h);
export function evaluate(s, me) {
  if (s.winner === me) return 1e4;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1e4;
  const P = s.p[me], O = s.p[1 - me];
  let v = hpWorth(Math.max(P.hp, 0)) - hpWorth(Math.max(O.hp, 0));
  for (const m of P.board) v += W.atk * m.atk + W.mhp * m.hp;
  for (const m of O.board) v -= W.atk * m.atk + W.mhp * m.hp;
  v += W.card * (P.hand.length - O.hand.length);
  return v;
}
const notSelf = (s) => legalActions(s).filter(a => !(a.t === 'play' && a.side === s.turn) && a.t !== 'end');
export function greedyBot(s) {
  const k = lethalStep(s);
  if (k) return k;
  const me = s.turn;
  let best = { t: 'end' }, bv = evaluate(s, me) + 1e-9;
  for (const a of notSelf(s)) { const x = step(clone(s), a); const v = evaluate(x, me); if (v > bv) { bv = v; best = a; } }
  return best;
}
// Racer: plays the most expensive card it can (hand or his discard), every spell and every
// attack at the enemy hero.
export function racerBot(s) {
  const k = lethalStep(s);
  if (k) return k;
  const me = s.turn, P = s.p[me];
  const ok = sources(s).filter(x => x.id !== 'COIN').sort((a, b) => b.price - a.price || (a.disc ? 1 : -1));
  if (ok.length) { const x = ok[0]; return CARDS[x.id].kind === 'Spell' ? { t: 'play', card: x.id, disc: x.disc, side: 1 - me, i: -1 } : { t: 'play', card: x.id, disc: x.disc }; }
  if (P.hand.includes('COIN') && P.hand.some(x => CARDS[x].cost === P.mana + 1)) return { t: 'play', card: 'COIN', disc: false };
  const from = P.board.findIndex(m => m.ready);
  return from >= 0 ? { t: 'attack', from, to: -1 } : { t: 'end' };
}

// ------------------------------------------------------------------ Expert: ISMCTS
// Rollout policy: lethal when it is there; a spell that kills the most valuable enemy unit it
// can; the most expensive unit, from hand or his discard (with noise); trades that kill and
// survive or kill something worth more; otherwise face.
function policy(s, rng) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const k = lethalStep(s);
  if (k) return k;
  if (rng() < 0.08) return pickOf(cands(s), rng);
  const units = [];
  for (const x of sources(s)) {
    const c = CARDS[x.id];
    if (x.id === 'COIN') continue;
    if (c.kind === 'Spell') {
      let bi = -1, bv = 2.5;
      O.board.forEach((m, i) => { if (m.hp <= c.dmg && unitVal(m) - x.price > bv) { bv = unitVal(m) - x.price; bi = i; } });
      if (bi >= 0) return { t: 'play', card: x.id, disc: x.disc, side: 1 - me, i: bi };
      continue;
    }
    units.push(x);
  }
  if (units.length) { units.sort((a, b) => CARDS[b.id].cost - CARDS[a.id].cost + (a.disc ? 0.6 : 0) - (b.disc ? 0.6 : 0) + (rng() - 0.5) * 1.5); return { t: 'play', card: units[0].id, disc: units[0].disc }; }
  if (P.hand.includes('COIN') && P.hand.some(x => x !== 'COIN' && CARDS[x].kind === 'Unit' && CARDS[x].cost === P.mana + 1) && P.board.length < BOARD) return { t: 'play', card: 'COIN', disc: false };
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
// A position's worth to seat 0, as a win chance: health (worth more when low), board, hand.
export function value0(s) {
  if (s.winner !== null) return s.winner === 0 ? 1 : s.winner === 1 ? 0 : 0.5;
  const side = (k) => { const p = s.p[k]; let b = 0; for (const m of p.board) b += unitVal(m); return hpWorth(Math.max(0, p.hp)) + b + 2 * p.hand.length; };
  return 1 / (1 + Math.exp(-(side(0) - side(1)) / 10));
}
function determinize(s, viewer, rng) {
  const t = clone(s);
  const O = t.p[1 - viewer], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[viewer].deck, rng);
  return t;
}
export const GAME = { cands, obsKey: (s, a) => key(a), determinize, step, policy, value0, turnNo: (s) => s.turnNo };

// Single-observer ISMCTS: each iteration deals a world consistent with what the mover has seen,
// walks the shared tree by UCB over the moves legal in that world, expands one, plays out
// `plies` turns with the rollout policy and scores the end by value0.
export function ismcts(s, rng, G, { iters = 1500, c = 0.7, plies = 4, stats = null } = {}) {
  const me = s.toMove, t00 = G.turnNo(s);
  const acts0 = G.cands(s);
  if (acts0.length === 1) return acts0[0];
  const root = { n: 0, kids: new Map() };
  const final = (d) => { const k = 0.01 * Math.min(30, G.turnNo(d) - t00); return d.winner === 0 ? 1 - k : d.winner === 1 ? k : 0.5; };
  for (let it = 0; it < iters; it++) {
    const d = G.determinize(s, me, rng);
    let node = root; const path = [];
    while (d.winner === null) {
      const groups = new Map();
      for (const a of G.cands(d)) { const k = G.obsKey(d, a, me); if (!groups.has(k)) groups.set(k, a); }
      const untried = [];
      for (const k of groups.keys()) { const ch = node.kids.get(k); if (ch) ch.avail++; else untried.push(k); }
      let k, fresh = false;
      if (untried.length) { k = untried[Math.floor(rng() * untried.length)]; node.kids.set(k, { n: 0, w: 0, avail: 1, kids: new Map(), mover: d.toMove }); fresh = true; }
      else {
        let best = -Infinity;
        for (const kk of groups.keys()) { const ch = node.kids.get(kk); const u = ch.w / ch.n + c * Math.sqrt(Math.log(ch.avail) / ch.n); if (u > best) { best = u; k = kk; } }
      }
      G.step(d, groups.get(k));
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
// ------------------------------------------------------------------ Expert: turn search
// The whole turn is planned at its start. A beam search over this turn's actions (states merged
// when equal, ranked by Greedy's worth) collects the distinct ways to end the turn; the best
// `top` of them by that worth, plus Greedy's own turn, are each played on in `R` worlds dealt
// from what the mover cannot see (the same R worlds for each), played on by Greedy on both sides
// for `depth` turns (40: to the end of the game), the end scored as a win (1), a loss (0) or, if
// the game is still going, Greedy's worth squashed into a win chance. The plan with the best mean
// is played out action by action, and replanned if the position is not the one it expected.
const skey = (s) => s.p.map(p => [p.hp, p.mana, p.took ? 1 : 0, p.hand.slice().sort().join(''), p.discard.slice().sort().join(''), p.board.map(sig).sort().join(',')].join('|')).join('/') + s.turn;
function turnEnds(s, beam) {
  const me = s.turn, ends = new Map();
  let front = [{ s, acts: [] }];
  const seen = new Set([skey(s)]);
  for (let d = 0; d < 20 && front.length; d++) {
    const next = [];
    for (const f of front) {
      const k = skey(f.s);
      if (!ends.has(k)) ends.set(k, { ...f, v: evaluate(f.s, me) });
      if (f.s.winner !== null) continue;
      for (const a of cands(f.s)) {
        if (a.t === 'end') continue;
        const x = step(clone(f.s), a), kx = skey(x);
        if (seen.has(kx)) continue; seen.add(kx);
        next.push({ s: x, acts: [...f.acts, a], v: evaluate(x, me) });
      }
    }
    next.sort((a, b) => b.v - a.v);
    front = next.slice(0, beam);
  }
  return [...ends.values()];
}
function greedyTurn(s) { let guard = 0; while (s.winner === null && guard++ < 60) { const a = greedyBot(s); step(s, a); if (a.t === 'end') break; } return s; }
export function turnSearch(s, rng, { beam = 24, top = 10, R = 24, depth = 2, score = 'eval', cheat = false, margin = 0 } = {}) {
  const me = s.turn;
  const ends = turnEnds(s, beam).sort((a, b) => b.v - a.v);
  const win = ends.find(e => e.s.winner === me);
  if (win) return win.acts;
  // Greedy's own turn is always a candidate
  const g = { s: clone(s), acts: [] };
  for (let guard = 0; guard < 60; guard++) { const a = greedyBot(g.s); if (a.t === 'end' || g.s.winner !== null) break; g.acts.push(a); step(g.s, a); }
  const cand = ends.slice(0, top);
  if (!cand.some(c => skey(c.s) === skey(g.s))) cand.push({ ...g, v: evaluate(g.s, me) });
  if (cand.length === 1) return cand[0].acts;
  // the same R worlds for every candidate, so the comparison is not muddied by the deal
  const seeds = Array.from({ length: R }, () => (rng() * 4294967296) >>> 0);
  let best = null, bv = -Infinity;
  for (const c of cand) {
    let tot = 0;
    for (let r = 0; r < R; r++) {
      let t = cheat ? clone(c.s) : determinize(c.s, me, makeRng(seeds[r]));
      if (t.winner === null) step(t, { t: 'end' });
      for (let d = 1; d < depth && t.winner === null; d++) greedyTurn(t);
      tot += score === 'win' ? (t.winner === me ? 1 : t.winner === null ? 1 / (1 + Math.exp(-evaluate(t, me) / 6)) : t.winner === 'draw' ? 0.5 : 0) : Math.max(-60, Math.min(60, evaluate(t, me)));
    }
    c.mean = tot / R;
    if (c.mean > bv) { bv = c.mean; best = c; }
  }
  // Greedy's own turn stands unless another beats it by `margin`: a plan that only looks
  // better by the luck of the play-outs is not worth leaving the plain play for
  const gc = cand.find(c => skey(c.s) === skey(g.s));
  return gc && best.mean < gc.mean + margin ? gc.acts : best.acts;
}
export const EXPERT = { kind: 'turn', beam: 48, top: 14, R: 128, depth: 40, score: 'win', margin: 0.03 };
// Expert: lethal when it is there (exact here, nothing blocks), otherwise the search. Kind
// 'turn' is the turn search above; kind 'ismcts' the action-by-action tree search (kept for
// comparison; leaf 'eval' scores a play-out's end by Greedy's worth instead of value0).
const evalLeaf = (s) => s.winner !== null ? value0(s) : 1 / (1 + Math.exp(-evaluate(s, 0) / 6));
export function expertBot(opts = EXPERT) {
  if (opts.kind === 'ismcts') {
    const G = { ...GAME, ...(opts.leaf === 'eval' ? { value0: evalLeaf } : {}) };
    return (s, rng) => lethalStep(s) || ismcts(s, rng, G, opts);
  }
  let plan = null;
  return (s, rng) => {
    const k = lethalStep(s);
    if (k) return k;
    const sk = skey(s);
    if (plan && plan.key === sk && plan.acts.length) { const a = plan.acts.shift(); plan.key = skey(step(clone(s), a)); return a; }
    const acts = turnSearch(s, rng, opts);
    if (!acts.length) { plan = null; return { t: 'end' }; }
    const a = acts.shift();
    plan = { acts, key: skey(step(clone(s), a)) };
    return a;
  };
}

export const TRIVIAL = { random: randomBot, greedy: greedyBot, racer: racerBot };
// what an action means, independent of which of two identical units does it
export function meaning(s, a) {
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (a.t === 'attack') return 'a' + sig(P.board[a.from]) + '>' + (a.to < 0 ? 'face' : sig(O.board[a.to]));
  if (a.t === 'end') return 'end';
  const src = a.disc ? 'D' : '';
  if (CARDS[a.card].kind === 'Spell') return 'p' + src + a.card + '>' + a.side + (a.i < 0 ? 'face' : sig(s.p[a.side].board[a.i]));
  return 'p' + src + a.card;
}
