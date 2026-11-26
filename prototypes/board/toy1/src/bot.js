// The Board Toy 1 bot. A turn is a set of cards from hand plus a target for each
// Strike; tiles carry no geometry, so a unit goes on any empty tile and enemy
// units with the same health are the same target. The bot tries every affordable
// set and every distinct way to aim its strikes, and keeps the plan whose position
// scores best after the opponent's reply. It never reads his hand or either deck.

import { CARDS, TILES, GOAL, clone, _play } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const W = { unit: 2.2, hp: 0.2, hpCap: 4, hand: 0.6 };

// Every distinct affordable set of cards from hand.
function cardSets(hand, mana) {
  const counts = {};
  for (const id of hand) counts[id] = (counts[id] || 0) + 1;
  const ids = Object.keys(counts), out = [];
  (function rec(i, left, cards) {
    if (i === ids.length) { out.push(cards.slice()); return; }
    const c = CARDS[ids[i]];
    for (let k = 0; k <= counts[ids[i]] && k * c.cost <= left; k++) {
      for (let j = 0; j < k; j++) cards.push(ids[i]);
      rec(i + 1, left - k * c.cost, cards);
      cards.length -= k;
    }
  })(0, mana, []);
  return out;
}

// All plans for one card set: strikes first (biggest first), each aimed at a distinct
// kind of enemy unit (by health), then units onto empty tiles while any are free.
function plansFor(s, set, cb) {
  const me = s.turn;
  const strikes = set.filter(id => CARDS[id].kind === 'Strike').sort((a, b) => CARDS[b].n - CARDS[a].n);
  const units = set.filter(id => CARDS[id].kind === 'Unit').sort((a, b) => CARDS[b].n - CARDS[a].n);
  (function aim(t, k, moves) {
    if (k === strikes.length) {
      const moves2 = moves.slice();
      let placed = 0;
      for (const id of units) {
        const tile = t.board.indexOf(null);
        if (tile < 0) break;
        _play(t, id, tile); moves2.push({ card: id, tile }); placed++;
      }
      if (placed < units.length) return; // a set whose units don't fit is the same as a smaller set
      cb(t, moves2);
      return;
    }
    const seen = new Set();
    let any = false;
    for (let i = 0; i < TILES; i++) {
      const u = t.board[i];
      if (!u || u.side === me) continue;
      const key = u.hp;
      if (seen.has(key)) continue;
      seen.add(key); any = true;
      const t2 = clone(t);
      _play(t2, strikes[k], i);
      aim(t2, k + 1, moves.concat({ card: strikes[k], tile: i }));
    }
    if (!any) return; // no target left: the strike stays in hand (a smaller set covers it)
  })(clone(s), 0, []);
}

// After my plan I score my units; then the opponent replies (a greedy reply from a hand
// sampled out of the cards he has not played) and scores his. Averaged over K sampled hands.
function lookahead(t, me, hands) {
  const P = t.p[me];
  const myFood = P.food + countUnits(t, me);
  if (myFood >= GOAL) return 1000 + myFood;
  let v = 0;
  for (const hand of hands) {
    const r = clone(t), O = r.p[1 - me];
    r.p[me].food = myFood;
    O.maxMana = Math.min(10, O.maxMana + 1); O.mana = O.maxMana;
    O.hand = hand.slice();
    r.turn = 1 - me;
    for (const m of greedyTurn(r)) _play(r, m.card, m.tile);
    O.food += countUnits(r, 1 - me);
    r.turn = me;
    v += O.food >= GOAL ? -1000 : evaluate(r, me);
  }
  return v / hands.length;
}
function countUnits(s, side) { let n = 0; for (const u of s.board) if (u && u.side === side) n++; return n; }
// Position value for `me` at the start of my next turn.
export function evaluate(s, me) {
  const P = s.p[me], O = s.p[1 - me];
  let v = P.food - O.food;
  for (const u of s.board) if (u) v += (u.side === me ? 1 : -1) * (W.unit + W.hp * Math.min(u.hp, W.hpCap));
  v += W.hand * (P.hand.length - O.hand.length);
  return v;
}

export function botTurn(s, rng = Math.random, K = 6) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const unseen = O.hand.concat(O.deck); // what he might hold: never looked at as hand or order, only as the pool
  const n = Math.min(unseen.length, O.hand.length + (O.deck.length ? 1 : 0));
  const hands = [];
  for (let k = 0; k < K; k++) {
    const pool = unseen.slice();
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = pool[i]; pool[i] = pool[j]; pool[j] = x; }
    hands.push(pool.slice(0, n));
  }
  let best = [], bestV = -Infinity;
  for (const set of cardSets(P.hand, P.mana)) {
    plansFor(s, set, (t, moves) => {
      const v = lookahead(t, me, hands) - 0.001 * moves.length;
      if (v > bestV) { bestV = v; best = moves; }
    });
  }
  return best;
}

// Baselines for the self-test.
export function greedyTurn(s) {
  const me = s.turn, moves = [];
  let t = clone(s);
  for (;;) {
    const P = t.p[me];
    const hand = [...new Set(P.hand)].filter(id => CARDS[id].cost <= P.mana);
    // kill the biggest unit a strike can kill, else play the biggest unit
    let pick = null;
    for (const id of hand.filter(id => CARDS[id].kind === 'Strike').sort((a, b) => CARDS[a].cost - CARDS[b].cost)) {
      let bt = -1, bh = -1;
      t.board.forEach((u, i) => { if (u && u.side !== me && u.hp <= CARDS[id].n && u.hp > bh) { bh = u.hp; bt = i; } });
      if (bt >= 0) { pick = { card: id, tile: bt }; break; }
    }
    if (!pick) {
      const tile = t.board.indexOf(null);
      const u = hand.filter(id => CARDS[id].kind === 'Unit').sort((a, b) => CARDS[b].cost - CARDS[a].cost)[0];
      if (u && tile >= 0) pick = { card: u, tile };
    }
    if (!pick) return moves;
    _play(t, pick.card, pick.tile); moves.push(pick);
  }
}
export function randomTurn(s, rng) {
  const me = s.turn, moves = [];
  let t = clone(s);
  for (let n = 0; n < 20; n++) {
    const opts = [];
    for (const id of new Set(t.p[me].hand)) {
      if (CARDS[id].cost > t.p[me].mana) continue;
      for (let i = 0; i < TILES; i++) {
        const u = t.board[i];
        if (CARDS[id].kind === 'Unit' ? u === null : u && u.side !== me) opts.push({ card: id, tile: i });
      }
    }
    if (!opts.length || rng() < 0.15) return moves;
    const m = opts[Math.floor(rng() * opts.length)];
    _play(t, m.card, m.tile); moves.push(m);
  }
  return moves;
}
