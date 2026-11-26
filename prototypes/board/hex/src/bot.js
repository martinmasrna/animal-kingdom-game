// The Hex bot. Position is judged region by region: a region only one side
// stands in is worth more the more of its four tiles that side holds; a region both
// sides stand in is worth nothing to either. A turn is built card by card, each card
// on its best tile by that judgement; the bot tries every affordable set of cards and
// keeps the one whose position is best after the opponent's likely reply (a greedy
// reply from hands sampled out of the cards he has not played). It never reads his
// hand or either deck.

import { CARDS, TILES, GOAL, REGIONS, clone, _play, heldRegions, regionPower, ownTile, canPlay, endTurn, playAction } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// value of a region by how many of its tiles the only side in it holds (index 0..4)
export const W = { reg: [0, 0.2, 0.9, 3], hp: 0.15, hand: 0.6 };

export function evaluate(s, me) {
  const P = s.p[me], O = s.p[1 - me];
  let v = P.food - O.food;
  for (const rg of REGIONS) {
    const p = regionPower(s, rg);
    if (!p[1 - me]) v += W.reg[p[me]]; else if (!p[me]) v -= W.reg[p[1 - me]];
  }
  for (const u of s.board) if (u) v += (u.side === me ? 1 : -1) * W.hp * Math.min(u.hp, 5);
  v += W.hand * (P.hand.length - O.hand.length);
  return v;
}

function legalMoves(t, me) {
  const P = t.p[me], out = [];
  for (const id of new Set(P.hand)) {
    if (CARDS[id].cost > P.mana) continue;
    for (let i = 0; i < TILES; i++) {
      const u = t.board[i];
      if (CARDS[id].kind === 'Unit' ? ownTile(me, i) && (!u || u.side === me) : u && u.side !== me) out.push({ card: id, tile: i });
    }
  }
  return out;
}

// Play one move at a time, always the one that most improves the position; stop when none does.
export function greedyTurn(s) {
  const me = s.turn, moves = [];
  let t = clone(s), cur = evaluate(t, me);
  for (;;) {
    let best = null, bestV = cur;
    for (const m of legalMoves(t, me)) {
      const t2 = clone(t); _play(t2, m.card, m.tile);
      const v = evaluate(t2, me); // a card played is a card lost: it has to buy more than it costs
      if (v > bestV + 1e-9) { bestV = v; best = { m, t2 }; }
    }
    if (!best) return moves;
    moves.push(best.m); t = best.t2; cur = evaluate(t, me);
  }
}

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

// Place a set: strikes first, biggest first, then units, biggest first; each on its best tile.
function placeSet(s, set) {
  const me = s.turn;
  const order = set.slice().sort((a, b) => (CARDS[a].kind === CARDS[b].kind ? CARDS[b].n - CARDS[a].n : CARDS[a].kind === 'Strike' ? -1 : 1));
  let t = clone(s); const moves = [];
  for (const id of order) {
    let best = null, bestV = -Infinity;
    for (let i = 0; i < TILES; i++) {
      const u = t.board[i];
      if (!(CARDS[id].kind === 'Unit' ? ownTile(me, i) && (!u || u.side === me) : u && u.side !== me)) continue;
      const t2 = clone(t); _play(t2, id, i);
      const v = evaluate(t2, me);
      if (v > bestV) { bestV = v; best = { m: { card: id, tile: i }, t2 }; }
    }
    if (!best) return null;
    moves.push(best.m); t = best.t2;
  }
  return { t, moves };
}

function lookahead(t, me, hands) {
  const myFood = t.p[me].food + heldRegions(t, me).length;
  if (myFood >= GOAL) return 1000 + myFood;
  let v = 0;
  for (const hand of hands) {
    const r = clone(t), O = r.p[1 - me];
    r.p[me].food = myFood;
    O.maxMana = Math.min(10, O.maxMana + 1); O.mana = O.maxMana;
    O.hand = hand.slice();
    r.turn = 1 - me;
    for (const m of greedyTurn(r)) _play(r, m.card, m.tile);
    O.food += heldRegions(r, 1 - me).length;
    r.turn = me;
    v += O.food >= GOAL ? -1000 : evaluate(r, me);
  }
  return v / hands.length;
}

const TOP = 40;
export function botTurn(s, rng = Math.random, K = 5, noise = 0) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const unseen = O.hand.concat(O.deck); // the pool he might hold: used only as a pool
  const n = Math.min(unseen.length, O.hand.length + (O.deck.length ? 1 : 0));
  if (n === unseen.length) K = 1; // he holds every card he has not played: nothing to sample
  const hands = [];
  for (let k = 0; k < K; k++) {
    const pool = unseen.slice();
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = pool[i]; pool[i] = pool[j]; pool[j] = x; }
    hands.push(pool.slice(0, n));
  }
  // judge every set on the spot, then look ahead from the best few
  const cands = [];
  for (const set of cardSets(P.hand, P.mana)) {
    const r = placeSet(s, set);
    if (r) cands.push({ r, v0: evaluate(r.t, me) });
  }
  cands.sort((a, b) => b.v0 - a.v0);
  let best = [], bestV = -Infinity;
  for (const { r } of cands.slice(0, TOP)) {
    const v = lookahead(r.t, me, hands) - 0.001 * r.moves.length + noise * rng();
    if (v > bestV) { bestV = v; best = r.moves; }
  }
  return best;
}

export function randomTurn(s, rng) {
  const me = s.turn, moves = [];
  let t = clone(s);
  for (let n = 0; n < 20; n++) {
    const opts = legalMoves(t, me);
    if (!opts.length || rng() < 0.15) return moves;
    const m = opts[Math.floor(rng() * opts.length)];
    _play(t, m.card, m.tile); moves.push(m);
  }
  return moves;
}

// Expert: candidate turns (Hard's own, and each first play finished the way Hard would), the best
// TOPN by Hard's judgement each played out R times DEPTH turns ahead with Hard on both sides; only
// cards neither player can see are reshuffled for a play-out. Keeps the turn that wins most.
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
const legalAll = (t) => { const out = []; for (const id of new Set(t.p[t.turn].hand)) for (let i = 0; i < TILES; i++) if (canPlay(t, id, i)) out.push({ card: id, tile: i }); return out; };
export function rolloutBot(TOPN, R, DEPTH) {
  return function (s, rng) {
    const me = s.turn, cands = new Map();
    const add = (moves) => {
      const t = clone(s); for (const m of moves) _play(t, m.card, m.tile);
      const key = t.board.map(u => u ? u.side + ':' + u.hp : '-').join(',') + '|' + t.p[me].hand.slice().sort().join(',');
      if (!cands.has(key)) cands.set(key, { moves, t, v: evaluate(t, me) });
    };
    add(greedyTurn(s)); [...cands.values()][0].greedy = true; add([]);
    for (const m of legalAll(s)) { const t = clone(s); _play(t, m.card, m.tile); add([m, ...greedyTurn(t)]); }
    const top = [...cands.values()].sort((a, b) => b.v - a.v).slice(0, TOPN);
    if (top.length === 1) return top[0].moves;
    // Hard's own turn stands unless the play-outs clearly prefer another
    const g = top.find(c => c.greedy) || top[0];
    let best = g, bv = -Infinity, gw = -Infinity;
    for (const c of top) {
      let w = 0;
      for (let r = 0; r < R; r++) {
        let t = clone(c.t); const O = t.p[1 - me];
        const pool = shuffle(O.hand.concat(O.deck), rng); O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
        shuffle(t.p[me].deck, rng);
        t = endTurn(t); let d = 0;
        while (t.winner === null && d < DEPTH) { for (const m of greedyTurn(t)) t = playAction(t, m.card, m.tile); if (t.winner !== null) break; t = endTurn(t); d++; }
        if (t.winner === me) w += 1;
        else if (t.winner === null) { const e = evaluate(t, me) + (t.p[me].food - t.p[1 - me].food); w += e > 0 ? 0.75 : e < 0 ? 0.25 : 0.5; }
        else if (t.winner === 'draw') w += 0.5;
      }
      if (c === g) gw = w;
      if (w > bv) { bv = w; best = c; }
    }
    return bv > gw + 0.2 * R ? best.moves : g.moves;
  };
}

// Centre: Martin's pattern (2026-11-26: "as long as you hold all 4 center tiles, your opponent can
// never get points. So you just save all the removal only for middle 4 tiles, and always put unit
// there after you've cleared it, as strong as you can"). Every triangle on this board holds one of
// the four centre tiles, so holding them all denies every region and pays the two centre triangles.
export const CENTRE = [3, 6, 7, 10];
export function centreBot(s) {
  const me = s.turn, t = clone(s), moves = [];
  const P = t.p[me];
  const play = (card, tile) => { _play(t, card, tile); moves.push({ card, tile }); };
  const units = () => [...new Set(P.hand)].filter(id => CARDS[id].kind === 'Unit' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[b].n - CARDS[a].n);
  for (let guard = 0; guard < 20; guard++) {
    const empty = CENTRE.filter(i => !t.board[i]);
    // an empty centre tile takes the biggest unit I can afford
    if (empty.length && units().length) { play(units()[0], empty[0]); continue; }
    // his centre units, biggest first: the cheapest set of strikes that kills one, if a unit can follow it in
    const foes = CENTRE.filter(i => t.board[i] && t.board[i].side !== me).sort((a, b) => t.board[b].hp - t.board[a].hp);
    const strikes = P.hand.filter(id => CARDS[id].kind === 'Strike');
    const unitCosts = P.hand.filter(id => CARDS[id].kind === 'Unit').map(id => CARDS[id].cost);
    const follow = unitCosts.length ? Math.min(...unitCosts) : 0;
    let did = false;
    for (const i of foes) {
      let best = null;
      for (let mask = 1; mask < (1 << strikes.length); mask++) {
        let cost = 0, dmg = 0; const pick = [];
        for (let k = 0; k < strikes.length; k++) if (mask & (1 << k)) { cost += CARDS[strikes[k]].cost; dmg += CARDS[strikes[k]].n; pick.push(strikes[k]); }
        if (dmg >= t.board[i].hp && cost + follow <= P.mana && (!best || cost < best.cost)) best = { cost, pick };
      }
      if (best) { for (const id of best.pick.sort((x, y) => CARDS[y].n - CARDS[x].n)) if (t.board[i]) play(id, i); did = true; break; }
    }
    if (did) continue;
    // my weakest centre unit, if a bigger one can land on it
    const mine = CENTRE.filter(i => t.board[i] && t.board[i].side === me).sort((a, b) => t.board[a].hp - t.board[b].hp);
    if (mine.length && units().length && CARDS[units()[0]].n > t.board[mine[0]].hp) { play(units()[0], mine[0]); continue; }
    break;
  }
  // the rest of the mana as Hard would spend it, with the strikes kept for the centre
  const kept = P.hand.filter(id => CARDS[id].kind === 'Strike');
  P.hand = P.hand.filter(id => CARDS[id].kind !== 'Strike');
  for (const m of greedyTurn(t)) play(m.card, m.tile);
  P.hand.push(...kept);
  return moves;
}
// Centre+: candidate turns are the centre rule's own and each first play finished by it; each is played
// out R times DEPTH turns ahead with the centre rule on both sides (hidden cards reshuffled); the centre
// rule's turn stands unless the play-outs clearly prefer another.
export function centrePlus(R = 8, DEPTH = 10, TOPN = 6) {
  return function (s, rng) {
    const me = s.turn, cands = [];
    const add = (moves) => { const t = clone(s); for (const m of moves) _play(t, m.card, m.tile); cands.push({ moves, t, v: evaluate(t, me) }); };
    add(centreBot(s)); const base = cands[0];
    for (const m of legalAll(s)) { const t = clone(s); _play(t, m.card, m.tile); add([m, ...centreBot(t)]); }
    const top = [base, ...cands.slice(1).sort((a, b) => b.v - a.v).slice(0, TOPN - 1)];
    let best = base, bw = -Infinity, baseW = 0;
    for (const c of top) {
      let w = 0;
      for (let r = 0; r < R; r++) {
        let t = clone(c.t); const O = t.p[1 - me];
        const pool = shuffle(O.hand.concat(O.deck), rng); O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length); shuffle(t.p[me].deck, rng);
        t = endTurn(t);
        for (let d = 0; t.winner === null && d < DEPTH; d++) { for (const m of centreBot(t)) t = playAction(t, m.card, m.tile); if (t.winner !== null) break; t = endTurn(t); }
        if (t.winner === me) w += 1; else if (t.winner === null) w += (t.p[me].food - t.p[1 - me].food) > 0 ? 0.75 : 0.25;
      }
      if (c === base) baseW = w;
      if (w > bw) { bw = w; best = c; }
    }
    return bw > baseW + 0.2 * R ? best.moves : base.moves;
  };
}
