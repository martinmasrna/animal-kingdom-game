// Duel: Grid. The bot. It sees only public information: it builds a public view first and works from that alone.
import { CARDS, DECKS, SHAPES, NEIGHBOURS, MANA_CAP, BASICS, CARD_ORDER, colOf, rowOf, popcount, isAttack,
  choiceCost, posAtSpeed, resolveRound, shuffle, actionSets, allLegalChoices } from './engine.js';

export const BOT_PARAMS = { samples: 8, botCap: 44, oppCap: 30, iterations: 400, minProb: 0.02, eps: 0.15 };

// What a hero at `side` may know. The opponent's hand and both deck orders are gone.
export function publicView(state, side) {
  const me = state.p[side], op = state.p[1 - side];
  return {
    round: state.round, side,
    me: { hero: me.hero, hp: me.hp, maxHp: me.maxHp, regen: me.regen, mana: me.mana, sharpen: me.sharpen, pos: me.pos, fatigue: me.fatigue,
      hand: me.hand.slice(), deckCards: me.deck.slice().sort(), discard: me.discard.slice(), known: me.known.slice() },
    op: { hero: op.hero, hp: op.hp, maxHp: op.maxHp, regen: op.regen, mana: op.mana, sharpen: op.sharpen, pos: op.pos, fatigue: op.fatigue,
      handCount: op.hand.length, deckCount: op.deck.length, discard: op.discard.slice(), known: op.known.slice() },
  };
}

// The cards of a hero's list not yet seen (not played for good, not known to be in hand).
export function unseenCards(hero, discard, known) {
  const left = { ...DECKS[hero] };
  for (const c of discard) left[c]--;
  for (const c of known) left[c]--;
  const out = [];
  for (const c of CARD_ORDER) for (let i = 0; i < (left[c] || 0); i++) out.push(c);
  return out;
}

// One full state consistent with the view: the opponent's unknown hand and both decks drawn at random.
function sampleState(view, rng) {
  const unseen = shuffle(unseenCards(view.op.hero, view.op.discard, view.op.known), rng);
  const unknownHand = view.op.handCount - view.op.known.length;
  const opHand = view.op.known.concat(unseen.slice(0, unknownHand));
  const opDeck = unseen.slice(unknownHand);
  const me = { hero: view.me.hero, hp: view.me.hp, maxHp: view.me.maxHp, regen: view.me.regen, mana: view.me.mana, deck: shuffle(view.me.deckCards.slice(), rng),
    hand: view.me.hand.slice(), discard: view.me.discard.slice(), known: view.me.known.slice(), sharpen: view.me.sharpen, pos: view.me.pos, fatigue: view.me.fatigue };
  const op = { hero: view.op.hero, hp: view.op.hp, maxHp: view.op.maxHp, regen: view.op.regen, mana: view.op.mana, deck: opDeck,
    hand: opHand, discard: view.op.discard.slice(), known: view.op.known.slice(), sharpen: view.op.sharpen, pos: view.op.pos, fatigue: view.op.fatigue };
  const p = view.side === 0 ? [me, op] : [op, me];
  return { round: view.round, over: false, winner: null, p };
}

// ---------- evaluation ----------
const OFFENCE = [1, 0.55, 0];      // being able to use melee next round, by column
const EXPOSURE = [1, 0.6, 0.15];   // how much of the enemy's damage can reach you, by column
export const EVAL = { hpScale: 14, mana: 0.35, hand: 1, sharpen: 2.2, offence: 1.2, trailOffence: 0.25, exposure: 0.9, room: 0.15, fatigue: 1 };
const HAND_VALUE = Array.from({ length: 31 }, (_, n) => 3.2 * (1 - Math.pow(0.72, n)));
export function evaluate(s, side) {
  if (s.over) {
    if (s.winner === 'draw') return 0;
    return s.winner === side ? 1000 + s.p[side].hp : -1000 - s.p[1 - side].hp;
  }
  const a = s.p[side], b = s.p[1 - side];
  const W = EVAL;
  const diff = a.hp - b.hp;
  // health first; with hpScale set, a curve that makes the trailing hero take risks and the leader avoid them
  let v = W.hpScale ? W.hpScale * Math.tanh(diff / W.hpScale) : diff;
  // mana that would overflow the cap at the next regain is worth nothing; extra cards in a big hand are worth less
  v += W.mana * (Math.min(a.mana, MANA_CAP - a.regen) - Math.min(b.mana, MANA_CAP - b.regen));
  v += W.hand * (HAND_VALUE[Math.min(a.hand.length, 30)] - HAND_VALUE[Math.min(b.hand.length, 30)]);
  v += W.sharpen * (a.sharpen - b.sharpen);
  // position: reach for the next round's melee, weighted up for whoever is behind on health
  const offA = W.offence + W.trailOffence * Math.max(0, -diff), offB = W.offence + W.trailOffence * Math.max(0, diff);
  v += offA * OFFENCE[colOf(a.pos)] - offB * OFFENCE[colOf(b.pos)];
  v -= W.exposure * (EXPOSURE[colOf(a.pos)] - EXPOSURE[colOf(b.pos)]);
  v += W.room * (NEIGHBOURS[a.pos].length - NEIGHBOURS[b.pos].length);
  // fatigue: the damage an empty deck will deal at the start of the next round
  v += W.fatigue * ((b.deck.length ? 0 : b.fatigue + 1) - (a.deck.length ? 0 : a.fatigue + 1));
  return v;
}

// ---------- candidate choices ----------
// Attacks in a canonical order: guards Parry, Block, Brace; attacks weakest first (so a guard eats the smaller hit).
const GUARD_RANK = { Parry: 0, Block: 1, Brace: 2 };
export function canonicalOrder(actions) {
  return actions.slice().sort((x, y) => {
    const cx = CARDS[x.card], cy = CARDS[y.card];
    if (cx.kind === 'defence' && cy.kind === 'defence') return GUARD_RANK[x.card] - GUARD_RANK[y.card];
    if (isAttack(x.card) && isAttack(y.card)) return cx.dmg * (cx.hits || 1) - cy.dmg * (cy.hits || 1);
    return 0;
  });
}

// Target options for one attack: shapes that can hit a tile the enemy may stand on, deduplicated and undominated.
function targetOptions(card, speed, enemyPos) {
  if (speed === 'fast') {
    const m = SHAPES[card].find((x) => (x >> enemyPos) & 1);
    return m === undefined ? [] : [m];
  }
  let E = 1 << enemyPos;
  for (const n of NEIGHBOURS[enemyPos]) E |= 1 << n;
  const byCover = new Map();
  for (const m of SHAPES[card]) { const c = m & E; if (c && !byCover.has(c)) byCover.set(c, m); }
  const covers = [...byCover.keys()];
  const out = [];
  for (const c of covers) if (!covers.some((o) => o !== c && (o & c) === c)) out.push(byCover.get(c));
  return out;
}

function quickScore(q, enemy, choice) {
  let v = 0;
  let E = 1 << enemy.pos; for (const n of NEIGHBOURS[enemy.pos]) E |= 1 << n;
  const nE = popcount(E);
  for (const a of choice.actions) {
    const C = CARDS[a.card];
    v -= 0.35 * C.cost + (C.basic ? 0 : 0.9);
    if (isAttack(a.card)) {
      const per = C.dmg + q.sharpen;
      const cover = C.speed === 'fast' ? 1 : popcount(a.tiles & E) / nE;
      let d = per * cover * (C.hits === 2 && C.speed !== 'fast' ? 1 : 1);
      if (C.kind === 'light') d *= 0.85;
      if (C.speed === 'slow') d *= 0.75;
      v += d;
    } else if (C.kind === 'defence') v += a.card === 'Parry' ? 2.6 : a.card === 'Brace' ? 2.2 : 1.3;
    else if (a.card === 'Meditate') v += 0.35 * Math.min(3, MANA_CAP - q.mana);
    else if (a.card === 'Bandage') v += 0.9 * Math.min(5, q.maxHp - q.hp);
    else if (a.card === 'Sharpen') v += 3.2;
    else if (a.card === 'Study') v += 2.2;
  }
  const dest = choice.step == null ? q.pos : choice.step;
  v += 1.2 * OFFENCE[colOf(dest)] - 0.9 * EXPOSURE[colOf(dest)];
  return v;
}

// Candidate choices for `side` in a full state, pruned of waste, capped with diversity across steps.
export function candidates(s, side, cap) {
  const q = s.p[side], enemy = s.p[1 - side];
  const steps = [null, ...NEIGHBOURS[q.pos]];
  const all = [];
  for (const set of actionSets(q)) {
    // waste: healing at full health, studying an empty deck, meditating into a full pool, two copies of one guard
    if (set.includes('Bandage') && q.hp >= q.maxHp) continue;
    if (set.includes('Study') && q.deck.length === 0) continue;
    if (set.includes('Meditate')) {
      const paid = q.mana - choiceCost(q.hero, set.map((card) => ({ card })));
      if (Math.min(MANA_CAP, paid + 3 + q.regen) <= Math.min(MANA_CAP, paid + q.regen)) continue;
    }
    if (set.length === 2 && CARDS[set[0]].kind === 'defence' && CARDS[set[1]].kind === 'defence' && (set[0] === 'Brace' || set[1] === 'Brace')) continue;
    for (const step of steps) {
      let combos = [[]], ok = true;
      for (const card of set) {
        const C = CARDS[card];
        if (!isAttack(card)) { combos = combos.map((c) => [...c, { card, tiles: 0 }]); continue; }
        if (C.melee && colOf(posAtSpeed(q.pos, step, C.speed)) !== 0) { ok = false; break; }
        const opts = targetOptions(card, C.speed, enemy.pos);
        if (!opts.length) { ok = false; break; }
        const next = [];
        for (const c of combos) for (const m of opts) next.push([...c, { card, tiles: m }]);
        combos = next;
      }
      if (!ok) continue;
      const seen = new Set();
      for (const actions of combos) {
        const ca = canonicalOrder(actions);
        const key = ca.map((a) => a.card + a.tiles).sort().join('|');
        if (seen.has(key)) continue;
        seen.add(key);
        all.push({ choice: { actions: ca, step }, setKey: set.join('+'), step, score: 0 });
      }
    }
  }
  for (const c of all) c.score = quickScore(q, enemy, c.choice);
  // keep the best per step destination, at most 3 targetings of one action set per step, always the empty set
  const groups = new Map();
  for (const c of all) { const k = String(c.step); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(c); }
  const per = Math.max(3, Math.ceil(cap / groups.size));
  const out = [];
  for (const g of groups.values()) {
    g.sort((x, y) => y.score - x.score);
    const perSet = new Map();
    let taken = 0;
    for (const c of g) {
      if (c.setKey === '') { out.push(c.choice); continue; }
      const n = perSet.get(c.setKey) || 0;
      if (n >= 3 || taken >= per) continue;
      perSet.set(c.setKey, n + 1); taken++;
      out.push(c.choice);
    }
  }
  return out;
}

// ---------- solving the simultaneous round ----------
function rmStrategy(R, out) {
  let sum = 0;
  for (let i = 0; i < R.length; i++) sum += R[i] > 0 ? R[i] : 0;
  if (sum <= 0) { const u = 1 / R.length; for (let i = 0; i < R.length; i++) out[i] = u; }
  else for (let i = 0; i < R.length; i++) out[i] = R[i] > 0 ? R[i] / sum : 0;
  return out;
}

// Bayesian zero-sum game: the bot has one strategy; each sampled opponent hand plays its own. Regret matching+.
// eps: weight of the uniform opponent in the bot's own payoff, so among equally safe options it prefers the one that
// gains most against a player who errs (Jab into a guard that might not come).
export function solve(mats, nB, iterations, eps = 0) {
  const S = mats.length;
  const rowMean = new Float64Array(nB);
  for (const m of mats) for (let i = 0; i < nB; i++) { let a = 0; for (let j = 0; j < m.nO; j++) a += m.A[i * m.nO + j]; rowMean[i] += a / m.nO / S; }
  const Rb = new Float64Array(nB), x = new Float64Array(nB), avg = new Float64Array(nB), u = new Float64Array(nB);
  const Ro = mats.map((m) => new Float64Array(m.nO)), y = mats.map((m) => new Float64Array(m.nO));
  for (let t = 1; t <= iterations; t++) {
    rmStrategy(Rb, x);
    for (let s = 0; s < S; s++) rmStrategy(Ro[s], y[s]);
    u.fill(0);
    for (let s = 0; s < S; s++) {
      const A = mats[s].A, nO = mats[s].nO, ys = y[s];
      for (let i = 0; i < nB; i++) { let acc = 0; const row = i * nO; for (let j = 0; j < nO; j++) acc += A[row + j] * ys[j]; u[i] += acc / S; }
    }
    if (eps) for (let i = 0; i < nB; i++) u[i] = (1 - eps) * u[i] + eps * rowMean[i];
    let ub = 0; for (let i = 0; i < nB; i++) ub += x[i] * u[i];
    for (let i = 0; i < nB; i++) { Rb[i] = Math.max(0, Rb[i] + u[i] - ub); avg[i] += t * x[i]; }
    for (let s = 0; s < S; s++) {
      const A = mats[s].A, nO = mats[s].nO, R = Ro[s], ys = y[s];
      const v = new Float64Array(nO);
      for (let i = 0; i < nB; i++) { const xi = x[i]; if (!xi) continue; const row = i * nO; for (let j = 0; j < nO; j++) v[j] -= xi * A[row + j]; }
      let vb = 0; for (let j = 0; j < nO; j++) vb += ys[j] * v[j];
      for (let j = 0; j < nO; j++) R[j] = Math.max(0, R[j] + v[j] - vb);
    }
  }
  let sum = 0; for (let i = 0; i < nB; i++) sum += avg[i];
  for (let i = 0; i < nB; i++) avg[i] /= sum;
  return avg;
}

// The bot's choice for `side`. It reads only publicView(state, side). rng: () => [0, 1).
export function botChoose(state, side, rng, params) {
  const P = { ...BOT_PARAMS, ...(params || {}) };
  const view = publicView(state, side);
  const samples = [];
  for (let i = 0; i < P.samples; i++) samples.push(sampleState(view, rng));
  const mine = candidates(samples[0], side, P.botCap);   // the bot's own options do not depend on the sample
  const mats = samples.map((s) => {
    const theirs = candidates(s, 1 - side, P.oppCap);
    const A = new Float64Array(mine.length * theirs.length);
    for (let i = 0; i < mine.length; i++) for (let j = 0; j < theirs.length; j++) {
      const ch = side === 0 ? [mine[i], theirs[j]] : [theirs[j], mine[i]];
      A[i * theirs.length + j] = evaluate(resolveRound(s, ch, { log: false }).state, side);
    }
    return { A, nO: theirs.length };
  });
  const strat = solve(mats, mine.length, P.iterations, P.eps);
  let total = 0;
  for (let i = 0; i < strat.length; i++) { if (strat[i] < P.minProb) strat[i] = 0; total += strat[i]; }
  let r = rng() * total, pick = 0;
  for (let i = 0; i < strat.length; i++) { r -= strat[i]; if (r <= 0 && strat[i] > 0) { pick = i; break; } pick = strat[i] > 0 ? i : pick; }
  return { choice: mine[pick], strategy: strat, options: mine };
}

// ---------- reference opponents for the self-test ----------
export function randomChoose(state, side, rng) {
  const all = allLegalChoices(state, side);
  return all[(rng() * all.length) | 0];
}

// Stays in (or walks to) the front column and plays the highest-damage affordable attacks at the enemy's tile.
export function greedyChoose(state, side) {
  const q = state.p[side], enemy = state.p[1 - side];
  const step = colOf(q.pos) === 0 ? null : q.pos - 3;
  let best = { actions: [], step }, bestDmg = 0;
  for (const set of actionSets(q)) {
    let dmg = 0; const actions = []; let ok = set.length > 0;
    for (const card of set) {
      const C = CARDS[card];
      if (!isAttack(card)) { ok = false; break; }
      if (C.melee && colOf(posAtSpeed(q.pos, step, C.speed)) !== 0) { ok = false; break; }
      const m = SHAPES[card].find((x) => (x >> enemy.pos) & 1);
      if (m === undefined) { ok = false; break; }
      actions.push({ card, tiles: m });
      dmg += C.dmg;
    }
    if (ok && dmg > bestDmg) { bestDmg = dmg; best = { actions: canonicalOrder(actions), step }; }
  }
  return best;
}
