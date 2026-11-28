// Bots for Junk war, simplest first. One action at a time through legalActions/act, the same API
// the page uses. None reads a hidden card: the Expert deals the opponent's hand and both decks
// again (keeping the Junk everyone saw put on top) and reshuffles the market before every play-out.

import { CARDS, TARGET, clone, _act, legalActions, owned } from './engine.js';

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
const ATTACK = new Set(['Foul', 'Foul2', 'Thief']);

// Playing the hand is not a choice that matters but for two cards: Draw first (more cards in hand),
// then Purge (while the Junk is still in hand), then the rest. Every bot but Random plays this order.
export function playOrder(s) {
  const H = s.p[s.turn].hand;
  return { t: 'play', card: H.includes('Draw') ? 'Draw' : H.includes('Purge') ? 'Purge' : H[0] };
}
// Purge by the fixed rule: Junk first, then Coin.
function purgeRule(s) {
  const H = s.p[s.turn].hand;
  return H.includes('Junk') ? { t: 'purge', card: 'Junk' } : H.includes('Coin') ? { t: 'purge', card: 'Coin' } : { t: 'stop' };
}
// The most expensive affordable row card, optionally skipping attacks.
function buyMost(s, skip) {
  let best = -1;
  s.row.forEach((id, i) => { if (id && CARDS[id].cost <= s.coin && !(skip && skip.has(id)) && (best < 0 || CARDS[id].cost > CARDS[s.row[best]].cost)) best = i; });
  return best >= 0 ? { t: 'buy', i: best } : { t: 'end' };
}

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pick(legalActions(s), rng); }
// Greedy: the most expensive affordable card, again and again; Purge takes Junk first, then Coin.
export function greedyBot(s) { return s.phase === 'play' ? playOrder(s) : s.phase === 'purge' ? purgeRule(s) : buyMost(s); }
// Racer: Greedy that never buys an attack (Foul, Foul 2, Thief).
export function racerBot(s) { return s.phase === 'buy' ? buyMost(s, ATTACK) : greedyBot(s); }

// ------------------------------------------------------------------ the play-out policy
// A buy's worth from a few plain rules that move with the game: coin early, points late, cleaning
// as Junk piles up, attacks while the opponent's deck is still worth spoiling.
function buyWorth(s, id) {
  const P = s.p[s.turn], O = s.p[1 - s.turn], prog = Math.max(P.points, O.points) / TARGET;
  const mine = owned(P), junk = mine.filter(x => x === 'Junk').length, size = mine.length;
  switch (id) {
    case 'Score4': return 8 + 4 * prog;
    case 'Score2': return 4 + 3 * prog;
    case 'Coin3': return 7 - 6.5 * prog;
    case 'Coin2': return 4.2 - 4 * prog;
    case 'Draw': return 3.2 - 2 * prog + junk * 0.1;
    case 'Foul': return (s.junk > 0 ? 3.2 : 1) - 1.5 * prog;
    case 'Foul2': return 3.5 + (s.junk > 0 ? 1.2 : 0) + prog;
    case 'Thief': return 4.5 + 1.5 * prog;
    case 'Clean': return 0.6 + 4 * junk / size;
    case 'Purge': return 0.8 + 6 * junk / size + (prog < 0.3 ? 0.8 : 0);
  }
  return 0;
}
function policyPurge(s) {
  const H = s.p[s.turn].hand;
  if (H.includes('Junk')) return { t: 'purge', card: 'Junk' };
  const P = s.p[s.turn], big = owned(P).filter(x => x === 'Coin2' || x === 'Coin3').length;
  if (big >= 2 && H.includes('Coin')) return { t: 'purge', card: 'Coin' };
  return { t: 'stop' };
}
export function policyBot(s, rng, noise = 0.25) {
  if (s.phase === 'play') return playOrder(s);
  if (s.phase === 'purge') return policyPurge(s);
  let best = null, bv = 1.6;
  s.row.forEach((id, i) => { if (id && CARDS[id].cost <= s.coin) { const v = buyWorth(s, id) * (1 + (rng() - 0.5) * 2 * noise); if (v > bv) { bv = v; best = i; } } });
  return best === null ? { t: 'end' } : { t: 'buy', i: best };
}

// ------------------------------------------------------------------ the Expert
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const pool = shuffle(O.hand.slice(O.knownJunk).concat(O.deck.slice(O.knownTop)), rng);
  // the known Junk kept in place: in hand (counted first) and on top of the deck
  const nh = O.hand.length - O.knownJunk;
  O.hand = Array(O.knownJunk).fill('Junk').concat(pool.slice(0, nh));
  O.deck = Array(O.knownTop).fill('Junk').concat(pool.slice(nh));
  P.deck = P.deck.slice(0, P.knownTop).concat(shuffle(P.deck.slice(P.knownTop), rng));
  shuffle(t.market, rng);
  t.seed = (rng() * 4294967296) >>> 0;
  return t;
}
// Greedy with noise: one buy in EPS is a random affordable card or stopping.
export function noisyGreedy(s, rng, eps = 0.2) {
  if (s.phase === 'buy' && rng() < eps) return pick(legalActions(s), rng);
  return greedyBot(s);
}
function playout(t, me, rng, roll) {
  for (let k = 0; k < 3000 && t.winner === null; k++) _act(t, roll(t, rng));
  if (t.winner === null) return 0.5;
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}
// Successive halving over the candidates on common resampled worlds; the default candidate (Greedy's
// choice) is never dropped, and stands unless the best beats it, paired world by world, by more than
// one standard error.
function halving(n, budget, run, keep = -1) {
  let alive = [...Array(n).keys()];
  const vals = [...Array(n)].map(() => []);
  const mean = (i) => vals[i].reduce((a, b) => a + b, 0) / Math.max(1, vals[i].length);
  const rounds = Math.max(1, Math.ceil(Math.log2(n)));
  let sample = 0;
  for (let r = 0; r < rounds && alive.length > 1; r++) {
    const per = Math.max(2, Math.floor(budget / (rounds * alive.length)));
    for (let k = 0; k < per; k++, sample++) for (const i of alive) vals[i][sample] = run(i, sample);
    alive.sort((a, b) => mean(b) - mean(a));
    const half = alive.slice(0, Math.max(1, Math.ceil(alive.length / 2)));
    if (keep >= 0 && !half.includes(keep)) half.push(keep);
    alive = half;
  }
  alive.sort((a, b) => mean(b) - mean(a));
  const best = alive[0];
  if (keep < 0 || best === keep) return best;
  const d = [];
  for (let k = 0; k < sample; k++) if (vals[best][k] !== undefined && vals[keep][k] !== undefined) d.push(vals[best][k] - vals[keep][k]);
  const m = d.reduce((a, b) => a + b, 0) / d.length, sd = Math.sqrt(d.reduce((a, b) => a + (b - m) * (b - m), 0) / Math.max(1, d.length - 1));
  return m > sd / Math.sqrt(d.length) ? best : keep;
}
const sig = (t) => JSON.stringify([t.phase, t.coin, t.row, t.p.map(p => [p.points, p.hand.slice().sort().join(), p.discard.slice().sort().join(), p.removed.length])]);
export function sameDecision(s, a, b) {
  const x = clone(s), y = clone(s);
  try { _act(x, a); _act(y, b); } catch (e) { return false; }
  return sig(x) === sig(y);
}
// The rest of the turn as whole plans: the Purge targets (none, one, two), the hand played out, then
// any affordable set of up to two row cards or nothing. Each plan is judged by play-outs from the
// opponent's next turn, so the play-out policy never makes this turn's choices; the first action
// of the best plan is played, and the plan is made again at the next step.
function buyPlans(t) {
  const out = [[]], idx = [];
  t.row.forEach((id, i) => { if (id && CARDS[id].cost <= t.coin) idx.push(i); });
  for (let a = 0; a < idx.length; a++) {
    out.push([idx[a]]);
    for (let b = a + 1; b < idx.length; b++) if (CARDS[t.row[idx[a]]].cost + CARDS[t.row[idx[b]]].cost <= t.coin) out.push([idx[a], idx[b]]);
  }
  return out.map(is => is.map(i => ({ t: 'buy', i })).concat([{ t: 'end' }]));
}
function plans(s) {
  const out = [];
  const addBuys = (pre, t) => { if (t.winner !== null) { out.push(pre); return; } for (const b of buyPlans(t)) out.push(pre.concat(b)); };
  if (s.phase === 'buy') { addBuys([], s); return out; }
  // purge phase: every distinct choice of up to purgeLeft cards
  const H = [...new Set(s.p[s.turn].hand)], picks = [[]];
  for (const x of H) { picks.push([x]); if (s.purgeLeft > 1) for (const y of H) if (y >= x && (y !== x || s.p[s.turn].hand.filter(c => c === x).length > 1)) picks.push([x, y]); }
  for (const pk of picks) {
    const pre = pk.map(card => ({ t: 'purge', card }));
    const t = clone(s); for (const a of pre) _act(t, a);
    if (t.phase === 'purge') { pre.push({ t: 'stop' }); _act(t, { t: 'stop' }); }
    // the rest of the hand (a second Purge purges by the play-out rule)
    const play = []; while ((t.phase === 'play' || t.phase === 'purge') && t.winner === null) { const a = t.phase === 'play' ? playOrder(t) : policyPurge(t); play.push(a); _act(t, a); }
    addBuys(pre.concat(play), t);
  }
  return out;
}
function greedyPlan(s) { const t = clone(s), out = []; while (t.winner === null) { const a = greedyBot(t); out.push(a); _act(t, a); if (a.t === 'end') break; } return out; }
const planSig = (s, plan) => { const t = clone(s); for (const a of plan) { if (t.winner !== null) break; if (a.t === 'end') break; _act(t, a); } return sig(t); };
export function expertBot({ budget = 2000 } = {}) {
  return function (s, rng) {
    if (s.phase === 'play') return playOrder(s);
    const me = s.turn, seen = new Map();
    for (const p of plans(s)) { const k = planSig(s, p); if (!seen.has(k)) seen.set(k, p); }
    const ps = [...seen.values()];
    if (ps.length === 1) return ps[0][0];
    const gk = planSig(s, greedyPlan(s)), keep = ps.findIndex(p => planSig(s, p) === gk);
    const seeds = [];
    const seedOf = (k) => { while (seeds.length <= k) seeds.push((rng() * 4294967296) >>> 0); return seeds[k]; };
    const best = halving(ps.length, budget, (i, k) => {
      const r = makeRng(seedOf(k)), t = determinize(s, me, r);
      for (const a of ps[i]) { if (t.winner !== null) break; _act(t, a); }
      return playout(t, me, r, noisyGreedy);
    }, keep);
    return ps[best][0];
  };
}
