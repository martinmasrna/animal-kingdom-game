// The Toy 1 bot. A turn is a set of cards; the bot plays investments first, then
// strikes, then guards, so only the set matters. It picks the set whose worst case
// over the opponent's best reply is best, averaged over hands the opponent could
// hold. It never reads his hand or either deck order.
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

// Every distinct affordable set of cards: strike count and sum, guard sum, investments.
export function turnSets(hand, mana, holdsSword = false) {
  const counts = {};
  for (const id of hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts);
  const out = [];
  (function rec(i, left, acc, cards) {
    if (i === ids.length) { out.push({ ...acc, n: cards.length, cost: mana - left, cards: cards.slice() }); return; }
    const c = CARDS[ids[i]];
    let max = counts[ids[i]];
    if (c.kind === 'Sword') max = holdsSword ? 0 : Math.min(max, 1);
    for (let k = 0; k <= max; k++) {
      if (k * c.cost > left) break;
      for (let j = 0; j < k; j++) cards.push(ids[i]);
      const a = { ...acc };
      if (c.kind === 'Strike') { a.sc += k; a.ss += k * c.n; }
      else if (c.kind === 'Guard') a.grd += k * c.n;
      else if (c.kind === 'Whetstone') a.edge += k * c.n;
      else if (c.kind === 'Sword') a.sword += k * c.n;
      else if (c.kind === 'Training') a.train += k * c.n;
      rec(i + 1, left - k * c.cost, a, cards);
      cards.length -= k;
    }
  })(0, mana, { sc: 0, ss: 0, grd: 0, edge: 0, sword: 0, train: 0 }, []);
  return out;
}

export const W = { block: 0.6, hand: 0.4, energy: 0.35, edge: 5, sword: 3, train: 3 };
const ORDER = { Whetstone: 0, Sword: 0, Training: 0, Strike: 1, Guard: 2 };

export function botTurn(s, rng, K = 8, noInvest = false) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  let mine = turnSets(P.hand, P.mana, P.sword > 0);
  if (noInvest) mine = mine.filter(S => !S.edge && !S.sword && !S.train);
  const unseen = [];
  const left = { ...DECK };
  for (const id of O.played) left[id]--;
  for (const [id, k] of Object.entries(left)) for (let i = 0; i < k; i++) unseen.push(id);
  const oppMana = Math.min(MAX_MANA, O.mana + REGEN + O.regenUp);
  const oppHandNext = O.hand.length + (O.deck.length ? 1 : 0);
  const replies = [];
  for (let k = 0; k < K; k++) {
    const pool = unseen.slice();
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = pool[i]; pool[i] = pool[j]; pool[j] = x; }
    replies.push(turnSets(pool.slice(0, Math.min(pool.length, oppHandNext)), oppMana, O.sword > 0));
  }
  let best = null, bestV = -Infinity;
  for (const S of mine) {
    const myEdge = P.edge + S.edge, mySwordNow = P.sword || S.sword;
    const myDmg = S.ss + S.sc * (myEdge + mySwordNow);
    const through = Math.max(0, myDmg - O.block);
    const oppHp = O.hp - through;
    const oppSword = through > 0 ? 0 : O.sword;
    let v;
    if (oppHp <= 0) v = 1000 - S.n * 0.01;
    else {
      v = 0;
      const myBlock = S.grd, myTrain = P.regenUp + S.train;
      const myEnergy = Math.min(MAX_MANA, P.mana - S.cost + REGEN + myTrain);
      for (const T of replies) {
        let worst = Infinity;
        for (const R of T) {
          const hisEdge = O.edge + R.edge, hisSword = oppSword || R.sword;
          const hisDmg = R.ss + R.sc * (hisEdge + hisSword);
          const hit = Math.max(0, hisDmg - myBlock);
          const myHp = P.hp - hit;
          let val;
          if (myHp <= 0) val = -1000;
          else {
            const keepSword = hit > 0 ? 0 : mySwordNow;
            const hisTrain = O.regenUp + R.train;
            val = (myHp - oppHp) - W.block * R.grd
              + W.hand * ((P.hand.length - S.n) - (oppHandNext - R.n))
              + W.energy * (myEnergy - Math.min(MAX_MANA, oppMana - R.cost + REGEN + hisTrain))
              + W.edge * (myEdge - hisEdge) + W.sword * (keepSword - hisSword) + W.train * (myTrain - hisTrain);
          }
          if (val < worst) worst = val;
        }
        v += worst / K;
      }
    }
    if (v > bestV + 1e-9) { bestV = v; best = S; }
  }
  return best.cards.slice().sort((a, b) => ORDER[CARDS[a].kind] - ORDER[CARDS[b].kind] || CARDS[b].n - CARDS[a].n);
}

export function greedyTurn(s) {
  const P = s.p[s.turn];
  let bestSet = null;
  for (const S of turnSets(P.hand, P.mana, P.sword > 0)) if (!bestSet || S.ss > bestSet.ss || (S.ss === bestSet.ss && S.grd > bestSet.grd)) bestSet = S;
  return bestSet.cards.slice().sort((a, b) => ORDER[CARDS[a].kind] - ORDER[CARDS[b].kind]);
}
export function randomTurn(s, rng) {
  const P = s.p[s.turn];
  const sets = turnSets(P.hand, P.mana, P.sword > 0);
  return sets[Math.floor(rng() * sets.length)].cards.slice().sort((a, b) => ORDER[CARDS[a].kind] - ORDER[CARDS[b].kind]);
}
