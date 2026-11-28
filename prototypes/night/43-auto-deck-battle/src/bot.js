// Bots for Auto deck battle. None reads a hidden thing: while shopping, a bot sees its own shop
// and the opponent's deck as it stood at the start of the round (`shown`), never the opponent's
// shop or what it is buying.

import { CARDS, POOL, GOLD, SHOP, DECK_MAX, ROUNDS, REROLL, REMOVE, clone, step, key, legalActions, battle } from './engine.js';

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

// ------------------------------------------------------------------ trivial bots
export function randomBot(s, rng) { return pickOf(legalActions(s), rng); }
// Greedy (the spec's): buys the most expensive affordable card until it cannot; never rerolls or removes.
export function greedyBot(s) {
  const P = s.p[s.toMove];
  let bi = -1, bc = -1;
  P.shop.forEach((id, i) => { if (id && CARDS[id].cost <= P.gold && CARDS[id].cost > bc && P.deck.length < DECK_MAX) { bc = CARDS[id].cost; bi = i; } });
  return bi >= 0 ? { t: 'buy', i: bi } : { t: 'done' };
}

// ------------------------------------------------------------------ Expert: plans judged by battles
// A plan is a removal (or none) and a set of shop cards to buy. Each plan's deck fights K sampled
// versions of the opponent's next deck (its shown deck plus what a random shop would let it buy,
// bought one of a few plausible ways); a battle is scored by the lives it leaves: a won game +30,
// a lost one -30, otherwise the change in the life difference (in the last round, only who leads).
// Rerolling is judged by dealing S new shops and taking the best plan of each. The same samples
// serve every plan, so plans differ only by what they buy.
export function oppNext(shown, rng) {
  const deck = shown.slice(); let gold = GOLD;
  const shop = Array.from({ length: SHOP }, () => pickOf(POOL, rng));
  const style = rng();
  if (deck.length >= DECK_MAX && rng() < 0.6) { const cheap = deck.slice().sort((a, b) => CARDS[a].cost - CARDS[b].cost)[0]; deck.splice(deck.indexOf(cheap), 1); gold -= REMOVE; }
  const order = style < 0.5 ? shop.slice().sort((a, b) => CARDS[b].cost - CARDS[a].cost) : shop.slice().sort(() => rng() - 0.5);
  for (const id of order) if (CARDS[id].cost <= gold && deck.length < DECK_MAX) { deck.push(id); gold -= CARDS[id].cost; }
  return deck;
}
export function plans(P, gold, shop) {
  const out = [];
  const removes = [null]; if (!P.removed && gold >= REMOVE) for (const c of new Set(P.deck)) removes.push(c);
  const slots = shop.map((id, i) => id ? i : -1).filter(i => i >= 0);
  for (const r of removes) {
    const base = P.deck.slice(); let g = gold;
    if (r) { base.splice(base.indexOf(r), 1); g -= REMOVE; }
    for (let mask = 0; mask < (1 << slots.length); mask++) {
      let cost = 0; const buys = [];
      for (let k = 0; k < slots.length; k++) if (mask & (1 << k)) { cost += CARDS[shop[slots[k]]].cost; buys.push(slots[k]); }
      if (cost > g || base.length + buys.length > DECK_MAX) continue;
      out.push({ remove: r, buys, deck: base.concat(buys.map(i => shop[i])), left: g - cost });
    }
  }
  return out;
}
function makeSamples(s, me, K, rng) {
  const O = s.p[1 - me];
  return Array.from({ length: K }, () => ({ opp: oppNext(O.shown, rng), seed: (rng() * 4294967296) >>> 0 }));
}
function judge(s, me, deck, samples) {
  const M = s.p[me], O = s.p[1 - me], last = s.round >= ROUNDS;
  let tot = 0;
  for (const x of samples) {
    const r = battle(deck, x.opp, makeRng(x.seed), null);
    let my = M.life, his = O.life;
    if (r.winner === 0) his -= r.dmg; else if (r.winner === 1) my -= r.dmg;
    if (my <= 0 || his <= 0) tot += my <= 0 && his <= 0 ? 0 : my <= 0 ? -30 : 30;
    else if (last) tot += my > his ? 30 : my < his ? -30 : 0;
    else tot += (my - his) - (M.life - O.life);
  }
  return tot / samples.length;
}
export function planBot({ K = 60, S = 8, KR = 24 } = {}) {
  return (s, rng) => {
    const me = s.toMove, P = s.p[me];
    const samples = makeSamples(s, me, K, rng);
    let best = null, bv = -Infinity;
    for (const pl of plans(P, P.gold, P.shop)) { const v = judge(s, me, pl.deck, samples) + 0.001 * (pl.deck.length - pl.left); if (v > bv) { bv = v; best = pl; } }
    // rerolling: the best plan of each of S fresh shops, with a gold less
    if (P.gold >= REROLL && S > 0) {
      const few = samples.slice(0, KR), now = plans(P, P.gold, P.shop).reduce((m, pl) => Math.max(m, judge(s, me, pl.deck, few)), -Infinity);
      let rv = 0;
      for (let k = 0; k < S; k++) {
        const shop = Array.from({ length: SHOP }, () => pickOf(POOL, rng));
        rv += plans(P, P.gold - REROLL, shop).reduce((m, pl) => Math.max(m, judge(s, me, pl.deck, few)), -Infinity);
      }
      if (rv / S > now + 0.05) return { t: 'reroll' };
    }
    if (best.remove) return { t: 'remove', card: best.remove };
    if (best.buys.length) return { t: 'buy', i: best.buys[0] };
    return { t: 'done' };
  };
}
export const EXPERT = { K: 60, S: 8, KR: 24 };
export function expertBot(opts = EXPERT) { return planBot(opts); }

export const TRIVIAL = { random: randomBot, greedy: greedyBot };
export function meaning(s, a) { return a.t === 'buy' ? 'b' + s.p[s.toMove].shop[a.i] : key(a); }
