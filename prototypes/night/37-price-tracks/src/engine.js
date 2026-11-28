// 37 Price tracks. Goods cards in your deck sell at three shared prices; a sale scores the price
// times the cards sold and then drops that price by as many; every price rises by 1 after each
// round. Boost and Crash push prices, Spy shows the opponent's hand. When a player reaches 40 the
// match ends at the end of that round (both have had the same number of turns) and the higher
// score wins; otherwise after 14 rounds. (The spec ended it at once on 40; moved to the round's end,
// the one rule change the night run allows: see report.json.)
// Pure from the outside: act() clones; _act() mutates (for play-outs).

export const TARGET = 40, ROUNDS = 14, HAND = 5, HAND_MAX = 8, COIN_GAIN = 2, COIN_CAP = 6, PMIN = 1, PMAX = 9, PSTART = 4;
export const GOODS = ['X', 'Y', 'Z'];
export const CARDS = {
  X: { id: 'X', name: 'Good X', kind: 'good', n: 5 },
  Y: { id: 'Y', name: 'Good Y', kind: 'good', n: 5 },
  Z: { id: 'Z', name: 'Good Z', kind: 'good', n: 5 },
  BOO: { id: 'BOO', name: 'Boost', kind: 'boost', cost: 1, n: 2 },
  CRA: { id: 'CRA', name: 'Crash', kind: 'crash', cost: 2, n: 2 },
  SPY: { id: 'SPY', name: 'Spy', kind: 'spy', cost: 1, n: 1 },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < c.n; i++) out.push(c.id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// seen: the cards in this player's hand the opponent knows of (from a Spy), kept up to date as
// they leave the hand; it is public information for the honest bots.
function newPlayer() { return { pts: 0, coin: 0, hand: [], deck: deckList(), disc: [], seen: [], sold: false }; }
export function clone(s) {
  return { ...s, price: { ...s.price }, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), disc: p.disc.slice(), seen: p.seen.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.n0 = s.turnNo; ev.push(e); } }
function drawOne(s, side, ev) {
  const P = s.p[side];
  if (!P.deck.length) {
    if (!P.disc.length) return false;
    P.deck = shuffleInPlace(s, P.disc); P.disc = [];
    emit(s, ev, { t: 'reshuffle', side });
  }
  P.hand.push(P.deck.shift()); emit(s, ev, { t: 'draw', side });
  return true;
}
const leaveHand = (P, id) => { P.hand.splice(P.hand.indexOf(id), 1); const k = P.seen.indexOf(id); if (k >= 0) P.seen.splice(k, 1); };

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, round: 1, toAct: 0, first: 0, winner: null, capped: false, why: null, reached: false, price: { X: PSTART, Y: PSTART, Z: PSTART }, p: [newPlayer(), newPlayer()] };
  for (const P of s.p) shuffleInPlace(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (const side of [0, 1]) for (let i = 0; i < HAND; i++) drawOne(s, side, null);
  s.toAct = s.first;
  startTurn(s, null);
  return s;
}
function startTurn(s, ev) {
  const P = s.p[s.toAct];
  s.turnNo++; P.sold = false;
  emit(s, ev, { t: 'turn', side: s.toAct, round: s.round });
  P.coin = Math.min(COIN_CAP, P.coin + COIN_GAIN);
  while (P.hand.length < HAND && drawOne(s, s.toAct, ev));
}
export const counts = (hand) => { const c = { X: 0, Y: 0, Z: 0 }; for (const id of hand) if (c[id] !== undefined) c[id]++; return c; };

// Actions: { t: 'sell', good, n } once a turn | { t: 'play', card, good? } (good for Boost, Crash)
//          | { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.toAct], out = [];
  if (!P.sold) { const c = counts(P.hand); for (const g of GOODS) for (let n = 1; n <= c[g]; n++) out.push({ t: 'sell', good: g, n }); }
  for (const id of [...new Set(P.hand)]) {
    const c = CARDS[id];
    if (c.kind === 'good' || c.cost > P.coin) continue;
    if (c.kind === 'spy') out.push({ t: 'play', card: id });
    else for (const g of GOODS) out.push({ t: 'play', card: id, good: g });
  }
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'sell' ? 's' + a.good + a.n : a.t === 'play' ? 'y' + a.card + (a.good || '') : 'e';

function finishByScore(s, ev, why) {
  const [a, b] = [s.p[0].pts, s.p[1].pts];
  s.winner = a === b ? 'draw' : a > b ? 0 : 1; s.why = why;
  emit(s, ev, { t: 'end', winner: s.winner, why });
}
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me];
  if (a.t === 'sell') {
    if (P.sold) throw new Error('already sold this turn');
    const c = counts(P.hand);
    if (!GOODS.includes(a.good) || !(a.n >= 1 && a.n <= c[a.good])) throw new Error('illegal sell');
    for (let i = 0; i < a.n; i++) { leaveHand(P, a.good); P.disc.push(a.good); }
    const gain = s.price[a.good] * a.n, from = s.price[a.good];
    P.pts += gain; P.sold = true;
    s.price[a.good] = Math.max(PMIN, s.price[a.good] - a.n);
    emit(s, ev, { t: 'sell', side: me, good: a.good, n: a.n, gain, pts: P.pts, from, to: s.price[a.good] });
    if (P.pts >= TARGET && !s.reached) { s.reached = true; emit(s, ev, { t: 'reached', side: me }); }
  } else if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.kind === 'good' || c.cost > P.coin) throw new Error('illegal play ' + a.card);
    if (c.kind !== 'spy' && !GOODS.includes(a.good)) throw new Error('play: no good');
    P.coin -= c.cost; leaveHand(P, a.card); P.disc.push(a.card);
    emit(s, ev, { t: 'play', side: me, card: a.card, good: a.good, coin: P.coin });
    if (c.kind === 'boost') { const from = s.price[a.good]; s.price[a.good] = Math.min(PMAX, from + 2); emit(s, ev, { t: 'price', good: a.good, from, to: s.price[a.good] }); }
    else if (c.kind === 'crash') { const from = s.price[a.good]; s.price[a.good] = Math.max(PMIN, from - 3); emit(s, ev, { t: 'price', good: a.good, from, to: s.price[a.good] }); }
    else if (c.kind === 'spy') { const O = s.p[1 - me]; O.seen = O.hand.slice(); emit(s, ev, { t: 'spy', side: me, hand: O.hand.slice() }); }
  } else if (a.t === 'end') {
    // hand max 8 (never binds: the hand only refills up to 5)
    while (P.hand.length > HAND_MAX) { const id = P.hand[P.hand.length - 1]; leaveHand(P, id); P.disc.push(id); }
    if (me !== s.first) {
      // the round ends: every price rises by 1
      for (const g of GOODS) s.price[g] = Math.min(PMAX, s.price[g] + 1);
      emit(s, ev, { t: 'round', round: s.round, price: { ...s.price } });
      if (s.reached) return finishByScore(s, ev, 'target');
      if (s.round >= ROUNDS) return finishByScore(s, ev, 'rounds');
      s.round++;
    }
    s.toAct = 1 - me;
    startTurn(s, ev);
  } else throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
