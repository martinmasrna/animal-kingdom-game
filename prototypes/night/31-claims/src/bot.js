// Bots for Claims, simplest first. Every bot picks one action at a time through legalActions/act,
// the same API the page uses. None reads a hidden card: the Expert reasons only from what the
// table shows (discard piles, face-up units, hand sizes, the claims already revealed) and
// resamples everything else before each play-out.

import { CARDS, LIST, COPIES, BOARD, PENALTY, needsTarget, clone, _act, legalActions, unseenPool } from './engine.js';

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

// ------------------------------------------------------------------ public reasoning about claims
// The lie rate a viewer reads off `side`'s revealed claims, pulled toward a prior of 1 in 4.
export const lieRate = (P) => (P.revLie + 1) / (P.revLie + P.revHonest + 4);
// How likely the pending claim of `name` by `side` is honest, from public information only:
// the chance its hand held a copy (counting the unseen copies), against how often it lies.
export function pHonest(s, side, name) {
  const P = s.p[side], pool = unseenPool(s, side), lam = lieRate(P);
  let u = pool.filter(x => x === name).length;
  if (u === 0) return 0;
  const down = P.board.filter(m => !m.up);
  u = Math.max(0, u - (1 - lam) * down.filter(m => m.name === name).length);
  const N = pool.length - down.length, h = P.hand.length + 1; // the hand before this card left it
  let none = 1;
  for (let i = 0; i < h; i++) none *= Math.max(0, N - u - i) / Math.max(1, N - i);
  const has = 1 - none;
  if (has <= 0) return 0;
  return (1 - lam) * has / ((1 - lam) * has + lam);
}
const allSeen = (s, side, name) => !unseenPool(s, side).includes(name);

// ------------------------------------------------------------------ worth of a position
const lifeWorth = (h) => 0.6 * h - 0.6 * Math.max(0, 10 - h);
const unitWorth = (m) => 1.4 * m.atk + m.hp;
export function evaluate(s, me) {
  if (s.winner === me) return 1e4;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1e4;
  const P = s.p[me], O = s.p[1 - me];
  let v = lifeWorth(Math.max(P.life, 0)) - lifeWorth(Math.max(O.life, 0));
  for (const m of P.board) v += unitWorth(m);
  for (const m of O.board) v -= unitWorth(m);
  v += 1.6 * (P.hand.length - O.hand.length) + 0.3 * (P.maxMana - O.maxMana);
  return v;
}
const winProb = (s, me) => s.winner !== null ? (s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : 0) : 1 / (1 + Math.exp(-evaluate(s, me) / 9));

// ------------------------------------------------------------------ simple rules shared by the bots
// Burn and ready attackers that reach the enemy player this turn, if they add up to lethal.
function lethalLine(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  let dmg = 0;
  const acts = [];
  P.board.forEach((m, i) => { if (m.ready) { dmg += m.atk; acts.push({ t: 'attack', from: i, to: -1 }); } });
  const burns = P.hand.filter(id => CARDS[id].dmg).sort((a, b) => CARDS[b].dmg / CARDS[b].cost - CARDS[a].dmg / CARDS[a].cost);
  let mana = P.mana + (P.coin ? 1 : 0);
  const spells = [];
  for (const id of burns) { if (dmg >= O.life) break; if (CARDS[id].cost <= mana) { mana -= CARDS[id].cost; dmg += CARDS[id].dmg; spells.push(id); } }
  if (dmg < O.life) return null;
  const spent = spells.reduce((a, id) => a + CARDS[id].cost, 0);
  const out = [];
  if (spent > P.mana) out.push({ t: 'coin' });
  for (const id of spells) out.push({ t: 'play', card: id, name: id, target: { side: 1 - me, i: -1 } });
  return out.concat(acts);
}
// The best enemy unit a burn of `dmg` kills (most worth), or -1.
function bestKill(O, dmg) { let best = -1, bv = -1; O.board.forEach((m, i) => { if (m.hp <= dmg && unitWorth(m) > bv) { bv = unitWorth(m); best = i; } }); return best; }
// One attacker's best target by a fixed rule: a kill it survives, else a trade up, else the player.
function attackTarget(P, O, i) {
  const m = P.board[i];
  let best = -1, bv = 0;
  O.board.forEach((d, j) => {
    const kills = d.hp <= m.atk, dies = m.hp <= d.atk;
    let v = -Infinity;
    if (kills && !dies) v = 10 + unitWorth(d);
    else if (kills && dies && unitWorth(d) >= unitWorth(m)) v = unitWorth(d) - unitWorth(m) + 1;
    if (v > bv) { bv = v; best = j; }
  });
  return best;
}

// ------------------------------------------------------------------ trivial bots
// Random: random claims (half of them honest), random targets, challenges a third of the time.
export function randomBot(s, rng) {
  if (s.pending) return rng() < 1 / 3 ? { t: 'challenge' } : { t: 'pass' };
  const me = s.turn, P = s.p[me], O = s.p[1 - me], opts = [{ t: 'end' }];
  if (P.coin) opts.push({ t: 'coin' });
  const ready = P.board.map((m, i) => m.ready ? i : -1).filter(i => i >= 0);
  if (ready.length) { const from = pick(ready, rng), to = Math.floor(rng() * (O.board.length + 1)) - 1; opts.push({ t: 'attack', from, to }); }
  if (P.hand.length) {
    const card = pick(P.hand, rng);
    const names = LIST.filter(n => CARDS[n].cost <= P.mana && (CARDS[n].kind !== 'Unit' || P.board.length < BOARD));
    if (names.length) {
      const name = rng() < 0.5 && names.includes(card) ? card : pick(names, rng);
      let target;
      if (needsTarget(name)) { const side = rng() < 0.5 ? 0 : 1; target = { side, i: Math.floor(rng() * (s.p[side].board.length + 1)) - 1 }; }
      opts.push({ t: 'play', card, name, target });
    }
  }
  return pick(opts, rng);
}

// Greedy: honest only; the most expensive affordable card first (burn at the best kill, else the
// player), then each attack by the fixed rule; challenges only when every copy is in sight.
export function greedyBot(s) {
  if (s.pending) return allSeen(s, s.pending.side, s.pending.name) ? { t: 'challenge' } : { t: 'pass' };
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const kill = lethalLine(s);
  if (kill && kill.length) return kill[0];
  const playable = (mana) => P.hand.filter(id => CARDS[id].cost <= mana && (CARDS[id].kind !== 'Unit' || P.board.length < BOARD));
  let cards = playable(P.mana);
  if (P.coin) { const more = playable(P.mana + 1); if (more.some(id => CARDS[id].cost === P.mana + 1)) return { t: 'coin' }; }
  if (cards.length) {
    const id = cards.sort((a, b) => CARDS[b].cost - CARDS[a].cost)[0];
    let target;
    if (needsTarget(id)) { const k = bestKill(O, CARDS[id].dmg); target = { side: 1 - me, i: k }; }
    return { t: 'play', card: id, name: id, target };
  }
  for (let i = 0; i < P.board.length; i++) if (P.board[i].ready) return { t: 'attack', from: i, to: attackTarget(P, O, i) };
  return { t: 'end' };
}

// Racer: honest, the most expensive card first, every spell and every attack at the enemy player.
export function racerBot(s) {
  if (s.pending) return allSeen(s, s.pending.side, s.pending.name) ? { t: 'challenge' } : { t: 'pass' };
  const me = s.turn, P = s.p[me];
  const cards = P.hand.filter(id => CARDS[id].cost <= P.mana && (CARDS[id].kind !== 'Unit' || P.board.length < BOARD));
  if (P.coin && P.hand.some(id => CARDS[id].cost === P.mana + 1)) return { t: 'coin' };
  if (cards.length) { const id = cards.sort((a, b) => CARDS[b].cost - CARDS[a].cost)[0]; return { t: 'play', card: id, name: id, target: needsTarget(id) ? { side: 1 - me, i: -1 } : undefined }; }
  for (let i = 0; i < P.board.length; i++) if (P.board[i].ready) return { t: 'attack', from: i, to: -1 };
  return { t: 'end' };
}

// ------------------------------------------------------------------ the play-out policy
// Fast, honest, in place: claims stand unchallenged inside a play-out.
function playHonest(t, id, target) { _act(t, { t: 'play', card: id, name: id, target }); if (t.pending) _act(t, { t: 'pass' }); }
function policyTurn(t, rng) {
  const me = t.turn, P = t.p[me], O = t.p[1 - me];
  if (t.pending) _act(t, { t: 'pass' });
  const kill = lethalLine(t);
  if (kill) { for (const a of kill) { if (t.winner !== null) return; if (a.t === 'play') playHonest(t, a.card, a.target); else _act(t, a); } return; }
  for (let guard = 0; guard < 12 && t.winner === null; guard++) {
    if (P.coin && P.hand.some(id => CARDS[id].cost === P.mana + 1 && CARDS[id].kind === 'Unit') && P.board.length < BOARD) _act(t, { t: 'coin' });
    const opts = [];
    for (const id of new Set(P.hand)) {
      const c = CARDS[id];
      if (c.cost > P.mana) continue;
      if (c.kind === 'Unit') { if (P.board.length < BOARD) opts.push({ id, v: c.cost + 0.5 }); }
      else if (c.dmg) { const k = bestKill(O, c.dmg); if (k >= 0 && unitWorth(O.board[k]) >= 2 * c.cost) opts.push({ id, v: c.cost, target: { side: 1 - me, i: k } }); }
      else if (P.hand.length <= 3) opts.push({ id, v: 0.5 });
    }
    if (!opts.length) break;
    const o = rng() < 0.15 ? pick(opts, rng) : opts.sort((a, b) => b.v - a.v)[0];
    playHonest(t, o.id, o.target);
  }
  if (t.winner !== null) return;
  const order = P.board.map((m, i) => i).filter(i => P.board[i].ready).sort((a, b) => P.board[b].atk - P.board[a].atk).map(i => P.board[i].uid);
  for (const uid of order) {
    if (t.winner !== null) return;
    const i = P.board.findIndex(m => m.uid === uid);
    if (i < 0 || !P.board[i].ready) continue;
    _act(t, { t: 'attack', from: i, to: attackTarget(P, O, i) });
  }
}

// ------------------------------------------------------------------ resampling what `me` cannot see
// The opponent's hand, deck and face-down units are dealt again from the copies `me` has not seen
// (a face-down unit is what it claims as often as that player tells the truth); my own deck is reshuffled.
export function determinize(s, me, rng) {
  const t = clone(s), o = 1 - me, O = t.p[o];
  const pool = shuffle(unseenPool(t, o), rng);
  const pd = t.pending && t.pending.side === o ? t.pending : null;
  const take = (want) => { const k = want ? pool.indexOf(want) : -1; if (k >= 0) return pool.splice(k, 1)[0]; return pool.pop(); };
  const lam = lieRate(O);
  for (const m of O.board) if (!m.up) m.real = take(rng() < 1 - lam ? m.name : null);
  if (pd) pd.card = take(null);
  const nh = O.hand.length;
  O.hand = pool.splice(0, nh); O.deck = pool;
  shuffle(t.p[me].deck, rng);
  return t;
}

// ------------------------------------------------------------------ the Expert
// How the Expert expects an opponent to answer its claim: from the opponent's side of the table,
// challenge when the claim looks unlikely, always when the claim would kill, never on 3 life or less.
function challengeChance(s, name, target) {
  const claimer = s.turn, ch = 1 - claimer, C = s.p[ch];
  const p = pHonest(s, claimer, name);
  if (p <= 0) return 1;
  const c = CARDS[name];
  if (c.dmg && target && target.side === ch && target.i < 0 && c.dmg >= C.life) return 1;
  if (C.life <= PENALTY) return 0;
  const q = p < 0.25 ? 1 : p > 0.45 ? 0 : (0.45 - p) / 0.2;
  // scaled by how often this opponent has actually challenged, against a baseline of one claim in four
  return Math.min(1, q * (C.challenges + 1) / (0.25 * C.faced + 1));
}
// After the root action, the rest of this turn and DEPTH more turns by the policy, then the position's worth.
function playout(t, me, rng, depth) {
  if (t.pending) {
    // my claim: the opponent answers by the model; its claim cannot be pending here
    const pd = t.pending;
    const q = challengeChance(t, pd.name, pd.target);
    _act(t, { t: rng() < q ? 'challenge' : 'pass' });
  }
  if (t.winner === null && t.turn === me) { policyTurn(t, rng); if (t.winner === null) _act(t, { t: 'end' }); }
  for (let d = 0; d < depth && t.winner === null; d++) { policyTurn(t, rng); if (t.winner === null) _act(t, { t: 'end' }); }
  return winProb(t, me);
}
const sig = (t) => JSON.stringify([t.pending && [t.pending.card, t.pending.name, t.pending.target && t.pending.target.side, t.pending.target && t.pending.target.i],
  t.p.map(p => [p.life, p.mana, p.coin, p.hand.slice().sort().join(), p.board.map(m => m.name + m.real + m.hp + m.atk + (m.ready ? 'r' : '')).join()])]);
// The root's candidate actions: every distinct honest play, each claim of a card not in hand paid
// with the cheapest card in hand, every attack, the Coin, ending the turn; one per distinct result.
function candidates(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [{ t: 'end' }];
  if (P.coin) out.push({ t: 'coin' });
  const spare = P.hand.slice().sort((a, b) => CARDS[a].cost - CARDS[b].cost)[0];
  const targets = [{ side: 1 - me, i: -1 }].concat(O.board.map((m, i) => ({ side: 1 - me, i })));
  for (const name of LIST) {
    const c = CARDS[name];
    if (c.cost > P.mana || (c.kind === 'Unit' && P.board.length >= BOARD)) continue;
    const card = P.hand.includes(name) ? name : spare;
    if (!card) continue;
    if (needsTarget(name)) for (const target of targets) out.push({ t: 'play', card, name, target });
    else out.push({ t: 'play', card, name });
  }
  P.board.forEach((m, from) => { if (m.ready) { out.push({ t: 'attack', from, to: -1 }); O.board.forEach((_, to) => out.push({ t: 'attack', from, to })); } });
  const seen = new Set(), uniq = [];
  for (const a of out) { const t = clone(s); _act(t, a); const k = sig(t); if (!seen.has(k)) { seen.add(k); uniq.push({ a, t }); } }
  return uniq;
}
// One-step worth of a candidate, as if a claim stood: to keep only the most plausible for play-outs.
function quick(c, me) { const t = clone(c.t); if (t.pending) _act(t, { t: 'pass' }); return evaluate(t, me); }

// Successive halving over the candidates with common resamples: each round every survivor gets the
// same resampled worlds, the worse half is dropped.
function halving(n, budget, run) {
  let alive = [...Array(n).keys()];
  const sum = new Float64Array(n), cnt = new Uint32Array(n);
  const rounds = Math.max(1, Math.ceil(Math.log2(n)));
  let sample = 0;
  for (let r = 0; r < rounds && alive.length > 1; r++) {
    const per = Math.max(2, Math.floor(budget / (rounds * alive.length)));
    for (let k = 0; k < per; k++, sample++) for (const i of alive) { sum[i] += run(i, sample); cnt[i]++; }
    alive.sort((a, b) => sum[b] / cnt[b] - sum[a] / cnt[a]);
    alive = alive.slice(0, Math.max(1, Math.ceil(alive.length / 2)));
  }
  return { best: alive[0], mean: (i) => sum[i] / Math.max(1, cnt[i]) };
}

export function expertBot({ budget = 3000, depth = 10, topK = 10 } = {}) {
  return function (s, rng) {
    const me = s.toMove;
    if (s.winner !== null) return null;
    const seeds = []; const seedOf = (k) => { while (seeds.length <= k) seeds.push((rng() * 4294967296) >>> 0); return seeds[k]; };
    if (s.pending) {
      // my answer to the opponent's claim: both branches over the same resampled worlds,
      // the claim honest as often as the table suggests
      const pd = s.pending, p = pHonest(s, pd.side, pd.name);
      if (p <= 0) return { t: 'challenge' };
      const pool = unseenPool(s, pd.side).filter(x => x !== pd.name);
      const run = (i, k) => {
        const r = makeRng(seedOf(k)), t = determinize(s, me, r);
        const honest = r() < p || !pool.length;
        t.pending.card = honest ? pd.name : pick(pool, r);
        _act(t, i === 0 ? { t: 'pass' } : { t: 'challenge' });
        return playout(t, me, r, depth);
      };
      const res = halving(2, budget, run);
      return res.best === 0 ? { t: 'pass' } : { t: 'challenge' };
    }
    const kill = lethalLine(s);
    if (kill && kill.length) return kill[0];
    let cands = candidates(s);
    if (cands.length === 1) return cands[0].a;
    const g = greedyBot(s);
    cands.forEach(c => { c.q = quick(c, me); });
    const keep = cands.filter(c => c.a.t === 'end').concat(cands.filter(c => c.a.t !== 'end').sort((a, b) => b.q - a.q).slice(0, topK));
    const gs = (() => { const t = clone(s); _act(t, g); return sig(t); })();
    if (!keep.some(c => sig(c.t) === gs)) { const c = cands.find(c => sig(c.t) === gs); if (c) keep.push(c); }
    cands = keep;
    const run = (i, k) => {
      const r = makeRng(seedOf(k));
      const t = determinize(s, me, r);
      _act(t, cands[i].a);
      return playout(t, me, r, depth);
    };
    const res = halving(cands.length, budget, run);
    return cands[res.best].a;
  };
}

// The state each action leads to, as the deciding player sees it: two actions are the same
// decision when they lead to the same table.
export function sameDecision(s, a, b) {
  const x = clone(s), y = clone(s);
  try { _act(x, a); _act(y, b); } catch (e) { return false; }
  return sig(x) === sig(y);
}
