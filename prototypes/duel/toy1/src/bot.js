// The Toy 1 bot. A turn is just a set of cards (order never matters: strikes
// hit his block first, guards only add to your own), so the bot picks the set
// whose worst case over the opponent's best reply is best, averaged over hands
// the opponent could hold. It never reads his hand or either deck order.
import { CARDS, DECK, MAX_MANA, REGEN } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Every distinct affordable set of cards from a hand: { str, grd, n, cards }.
export function turnSets(hand, mana) {
  const counts = {};
  for (const id of hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts);
  const out = [];
  const total = mana;
  (function rec(i, mana, str, grd, cards) {
    const spent = total - mana;
    if (i === ids.length) { out.push({ str, grd, n: cards.length, cost: spent, cards: cards.slice() }); return; }
    const c = CARDS[ids[i]];
    for (let k = 0; k <= counts[ids[i]]; k++) {
      if (k * c.cost > mana) break;
      for (let j = 0; j < k; j++) cards.push(ids[i]);
      rec(i + 1, mana - k * c.cost, str + (c.kind === 'Strike' ? k * c.n : 0), grd + (c.kind === 'Guard' ? k * c.n : 0), cards);
      cards.length -= k;
    }
  })(0, mana, 0, 0, []);
  return out;
}

const W = { block: 0.6, hand: 0.4, energy: 0.35 };

// Choose the bot's whole turn. Returns the list of cards to play (maybe empty).
export function botTurn(s, rng, K = 8) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const mine = turnSets(P.hand, P.mana);
  const unseen = [];
  const left = { ...DECK };
  for (const id of O.played) left[id]--;
  for (const [id, k] of Object.entries(left)) for (let i = 0; i < k; i++) unseen.push(id);
  const oppMana = Math.min(MAX_MANA, O.mana + REGEN);
  const replies = [];
  for (let k = 0; k < K; k++) {
    const pool = unseen.slice();
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = pool[i]; pool[i] = pool[j]; pool[j] = x; }
    replies.push(turnSets(pool.slice(0, Math.min(pool.length, O.hand.length + (O.deck.length ? 1 : 0))), oppMana));
  }
  const oppHandNext = O.hand.length + (O.deck.length ? 1 : 0);
  let best = null, bestV = -Infinity;
  for (const S of mine) {
    const oppHp = O.hp - Math.max(0, S.str - O.block);
    let v;
    if (oppHp <= 0) v = 1000 - S.n * 0.01;
    else {
      v = 0;
      const myBlock = S.grd;
      for (const T of replies) {
        let worst = Infinity;
        for (const R of T) {
          const myHp = P.hp - Math.max(0, R.str - myBlock);
          const val = myHp <= 0 ? -1000
            : (myHp - oppHp) - W.block * R.grd + W.hand * ((P.hand.length - S.n) - (oppHandNext - R.n))
              + W.energy * (Math.min(MAX_MANA, P.mana - S.cost + REGEN) - Math.min(MAX_MANA, oppMana - R.cost + REGEN));
          if (val < worst) worst = val;
        }
        v += worst / K;
      }
    }
    if (v > bestV + 1e-9) { bestV = v; best = S; }
  }
  // strikes biggest first, then guards: the order changes nothing but reads well
  return best.cards.slice().sort((a, b) => (CARDS[a].kind === CARDS[b].kind ? CARDS[b].n - CARDS[a].n : CARDS[a].kind === 'Strike' ? -1 : 1));
}

// Baselines for measuring the bot.
export function greedyTurn(s) {
  const P = s.p[s.turn];
  let bestSet = null;
  for (const S of turnSets(P.hand, P.mana)) if (!bestSet || S.str > bestSet.str || (S.str === bestSet.str && S.grd > bestSet.grd)) bestSet = S;
  return bestSet.cards;
}
export function randomTurn(s, rng) {
  const P = s.p[s.turn];
  const sets = turnSets(P.hand, P.mana);
  return sets[Math.floor(rng() * sets.length)].cards;
}
