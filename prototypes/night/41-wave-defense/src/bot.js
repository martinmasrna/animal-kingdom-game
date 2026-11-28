// Bots for Wave defense, simplest first. One action at a time through legalActions/act, the same
// API the page uses. None reads the hidden order: the Expert reshuffles the unrevealed threats
// within their tiers, its own deck, and the future reward offers before every play-out.

import { CARDS, THREATS, LANES, WALL, POOL, clone, _act, legalActions } from './engine.js';

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

// ------------------------------------------------------------------ trivial bots
// Random: a uniform choice among every legal action, ending the turn included.
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// Greedy: the most expensive affordable card first; Hit at the threat nearest the Wall; Defenders
// into empty slots, the lane with the most threat attack first; the most expensive reward.
const laneAtk = (s, l) => s.lanes[l].reduce((n, t) => n + t.atk, 0);
export function greedyBot(s) {
  if (s.phase === 'reward') { const o = s.offer.slice().sort((a, b) => CARDS[b].cost - CARDS[a].cost); return { t: 'reward', card: o[0] }; }
  const lanesByAtk = [0, 1, 2].sort((a, b) => laneAtk(s, b) - laneAtk(s, a));
  const cards = [...new Set(s.hand)].filter(id => CARDS[id].cost <= s.mana).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of cards) {
    const c = CARDS[id];
    if (c.kind === 'Defender') { const l = lanesByAtk.find(l => !s.slots[l]); if (l !== undefined) return { t: 'play', card: id, lane: l }; continue; }
    if (c.kind === 'Hit') {
      let best = null; s.lanes.forEach((L, l) => L.forEach(t => { if (!best || t.row < best.t.row) best = { t, l }; }));
      if (best) return { t: 'play', card: id, lane: best.l, uid: best.t.uid };
      continue;
    }
    if (c.kind === 'Bomb' || c.kind === 'Freeze') return { t: 'play', card: id, lane: lanesByAtk[0] };
    return { t: 'play', card: id };
  }
  return { t: 'end' };
}

// ------------------------------------------------------------------ the play-out policy
// Each legal play gets a worth from a few plain rules; the best that pays is played, with noise.
const pressure = (t) => t.atk * (t.row === 1 ? 3 : t.row === 2 ? 2 : t.row === 3 ? 1.2 : 0.8);
function playWorth(s, a) {
  const c = CARDS[a.card];
  if (c.kind === 'Defender') {
    const L = s.lanes[a.lane], d = s.slots[a.lane];
    const p = L.reduce((n, t) => n + pressure(t), 0);
    const val = (x) => x ? (x.hp * 0.6 + x.atk * 1.2 + x.shoot * 2.2) : 0;
    const gain = val(c) - (d ? val(d) + 1.5 : 0);
    if (gain <= 0) return -1;
    return gain * (0.4 + p / 4) + (L.length ? 1 : 0);
  }
  if (c.kind === 'Hit') {
    const t = s.lanes[a.lane].find(x => x.uid === a.uid);
    const kill = t.hp <= c.dmg;
    return (kill ? 4 + t.atk * 2 + (5 - t.row) : Math.min(c.dmg, t.hp) * 0.45 * (t.row <= 2 ? 1.5 : 1)) - (kill ? (c.dmg - t.hp) * 0.25 : 0);
  }
  if (c.kind === 'Bomb') { let v = 0; for (const t of s.lanes[a.lane]) v += t.hp <= c.dmg ? 3 + t.atk * 2 : 1; return v - 2; }
  if (c.kind === 'Freeze') { let v = 0; for (const t of s.lanes[a.lane]) if (t.row <= 2) v += t.atk * (s.slots[a.lane] ? 0.5 : 1.5); return v - 1.5; }
  if (c.kind === 'Wall') { const n = Math.min(c.heal, WALL - s.wall); return s.wall <= 14 ? n * 0.8 : n * 0.3 - 1; }
  if (c.kind === 'Draw') return 3.5;
  return 0;
}
const REWARD_PREF = { Cannon: 6, Twin: 5.5, Hit6: 4.5, Bomb: 4, Heavy: 4.2, Rebuild: 3, Freeze: 2.5 };
export function policyBot(s, rng, noise = 0.15) {
  if (s.phase === 'reward') {
    let best = null, bv = 0.5 + rng() * noise * 4;
    for (const id of s.offer) { const v = REWARD_PREF[id] + (rng() - 0.5) * noise * 8; if (v > bv) { bv = v; best = id; } }
    return { t: 'reward', card: best };
  }
  let best = null, bv = 0;
  for (const a of legalActions(s)) {
    if (a.t !== 'play') continue;
    const v = playWorth(s, a) * (1 + (rng() - 0.5) * noise * 2);
    if (v > bv) { bv = v; best = a; }
  }
  return best || { t: 'end' };
}

// ------------------------------------------------------------------ the Expert
// What the player cannot know is dealt again: unrevealed threats within their tiers, the deck, the
// seeds of later shuffles and offers.
export function determinize(s, rng) {
  const t = clone(s);
  for (let k = 1; k <= 3; k++) {
    const idx = []; t.threatDeck.forEach((c, i) => { if (c.tier === k) idx.push(i); });
    const ids = shuffle(idx.map(i => t.threatDeck[i]), rng);
    idx.forEach((i, j) => { t.threatDeck[i] = ids[j]; });
  }
  shuffle(t.deck, rng);
  t.seedDeck = (rng() * 4294967296) >>> 0; t.seedReward = (rng() * 4294967296) >>> 0;
  return t;
}
const score = (t) => t.result === 'win' ? 1 + 0.5 * t.wall / WALL : 0.02 * Math.min(t.round, 20) / 20;
function playout(t, rng) {
  for (let k = 0; k < 400 && !t.result; k++) _act(t, policyBot(t, rng));
  return score(t);
}
// Successive halving on common resampled worlds; the default (the play-out policy's own move, without
// noise) is never dropped and stands unless the best beats it, world by world, by more than one
// standard error, so a move that changes nothing is never chosen on noise.
function halving(n, budget, run, keep = -1) {
  let alive = [...Array(n).keys()];
  const vals = [...Array(n)].map(() => []);
  const mean = (i) => { let a = 0, c = 0; for (const v of vals[i]) if (v !== undefined) { a += v; c++; } return a / Math.max(1, c); };
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
const sig = (t) => JSON.stringify([t.phase, t.wall, t.mana, t.hand.slice().sort().join(), t.discard.length, t.slots.map(d => d && d.id + d.hp), t.lanes.map(L => L.map(x => x.uid + ':' + x.hp + ':' + x.row)), t.freezeNext]);
export function sameDecision(s, a, b) {
  const x = clone(s), y = clone(s);
  try { _act(x, a); _act(y, b); } catch (e) { return false; }
  return sig(x) === sig(y);
}
export function expertBot({ budget = 2000, topK = 10 } = {}) {
  return function (s, rng) {
    let acts = legalActions(s);
    if (acts.length === 1) return acts[0];
    // one per distinct result, the most plausible plays kept, ending the turn and Greedy's choice always in
    const seen = new Map();
    for (const a of acts) { const t = clone(s); _act(t, a); const k = sig(t); if (!seen.has(k)) seen.set(k, a); }
    acts = [...seen.values()];
    if (s.phase === 'play' && acts.length > topK + 1) {
      const g = greedyBot(s), p0 = policyBot(s, () => 0.5, 0), keep = acts.filter(a => a.t === 'end' || sameDecision(s, a, g) || sameDecision(s, a, p0));
      const rest = acts.filter(a => !keep.includes(a)).map(a => ({ a, v: playWorth(s, a) })).sort((x, y) => y.v - x.v).slice(0, topK).map(x => x.a);
      acts = keep.concat(rest);
    }
    if (acts.length === 1) return acts[0];
    const p = policyBot(s, rng, 0), keep = acts.findIndex(a => sameDecision(s, a, p));
    const seeds = [];
    const seedOf = (k) => { while (seeds.length <= k) seeds.push((rng() * 4294967296) >>> 0); return seeds[k]; };
    const best = halving(acts.length, budget, (i, k) => {
      const r = makeRng(seedOf(k)), t = determinize(s, r);
      _act(t, acts[i]);
      return playout(t, r);
    }, keep);
    return acts[best];
  };
}
