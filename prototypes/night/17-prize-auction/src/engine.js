// 17 Prize auction: sealed bids from a hand of coin cards for one prize a round. Your deck is your
// money; prizes are better coin or points that clog the deck. Simultaneous: each round both sides
// submit (a discard down to 7 when needed, then a bid) and the round resolves when both bids are in.

export const HAND_MAX = 7, START_HAND = 5, DRAW = 2;
export const CARDS = {
  C1: { id: 'C1', name: 'Coin 1', coin: 1, pts: 0 },
  C2: { id: 'C2', name: 'Coin 2', coin: 2, pts: 0 },
  C3: { id: 'C3', name: 'Coin 3', coin: 3, pts: 0 },
  MES: { id: 'MES', name: 'Messenger', coin: 1, pts: 0, text: 'When drawn, draw 1 more' },
  P2: { id: 'P2', name: 'Point 2', coin: 0, pts: 2 },
  P3: { id: 'P3', name: 'Point 3', coin: 0, pts: 3 },
  P5: { id: 'P5', name: 'Point 5', coin: 0, pts: 5 },
  DEBT: { id: 'DEBT', name: 'Debt', coin: 0, pts: -3, text: 'The lower bidder takes it' },
};
export const START = { C1: 6, C2: 2 };
export const PRIZES = { C3: 4, C2: 3, MES: 2, P2: 3, P3: 2, P5: 1, DEBT: 1 };
const list = (o) => { const out = []; for (const [id, k] of Object.entries(o)) for (let i = 0; i < k; i++) out.push(id); return out; };
export const NPRIZES = list(PRIZES).length;

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { hand: [], deck: list(START), discard: [], won: [] }; }
export function clone(s) {
  return { ...s, prizes: s.prizes.slice(), pot: s.pot.slice(), need: s.need.slice(), bids: s.bids.slice(), last: s.last, p: s.p.map(p => ({ hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), won: p.won.slice() })) };
}
function emit(ev, e) { if (ev) ev.push(e); }
function draw1(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(s, p.discard); p.discard = []; emit(ev, { t: 'shuffle', side }); }
  const c = p.deck.shift(); p.hand.push(c); emit(ev, { t: 'draw', side, card: c });
  if (c === 'MES') draw1(s, side, ev);
}

export function newMatch({ seed } = {}) {
  const s = { seed: (seed >>> 0) || 1, round: 0, phase: 'bid', need: [false, false], bids: [null, null], prizes: list(PRIZES), pot: [], winner: null, capped: false, last: null, p: [newPlayer(), newPlayer()] };
  shuffleInPlace(s, s.prizes);
  for (const p of s.p) shuffleInPlace(s, p.deck);
  for (const side of [0, 1]) for (let i = 0; i < START_HAND; i++) draw1(s, side, null);
  startRound(s, null);
  return s;
}
function startRound(s, ev) {
  s.round++;
  for (const side of [0, 1]) for (let i = 0; i < DRAW; i++) draw1(s, side, ev);
  s.pot.push(s.prizes.shift());
  emit(ev, { t: 'round', round: s.round, pot: s.pot.slice() });
  s.bids = [null, null];
  const over = [0, 1].map(side => s.p[side].hand.length > HAND_MAX);
  if (over[0] || over[1]) { s.phase = 'discard'; s.need = over; } else { s.phase = 'bid'; s.need = [true, true]; }
}
export const coinOf = (cards) => cards.reduce((a, c) => a + CARDS[c].coin, 0);
export const pointsOf = (p) => p.hand.concat(p.deck, p.discard).reduce((a, c) => a + CARDS[c].pts, 0);
export const ownedCoin = (p) => coinOf(p.hand.concat(p.deck, p.discard));
export const nextPrize = (s) => s.prizes[0];

// is `cards` a sub-multiset of `hand`?
export function within(hand, cards) {
  const h = hand.slice();
  for (const c of cards) { const i = h.indexOf(c); if (i < 0) return false; h.splice(i, 1); }
  return true;
}
// Actions: { t: 'discard', cards: [...] } (exactly down to 7) or { t: 'bid', cards: [...] }
export function canSubmit(s, side, a) {
  if (s.winner !== null || !s.need[side]) return false;
  const P = s.p[side];
  if (s.phase === 'discard') return a.t === 'discard' && within(P.hand, a.cards) && P.hand.length - a.cards.length === HAND_MAX;
  return a.t === 'bid' && within(P.hand, a.cards);
}
function removeFrom(arr, cards) { for (const c of cards) arr.splice(arr.indexOf(c), 1); }
function mSubmit(s, side, a, ev) {
  if (!canSubmit(s, side, a)) throw new Error('illegal ' + JSON.stringify(a) + ' for ' + side + ' in ' + s.phase);
  const P = s.p[side];
  if (s.phase === 'discard') {
    removeFrom(P.hand, a.cards); P.discard.push(...a.cards); s.need[side] = false;
    emit(ev, { t: 'discard', side, cards: a.cards.slice() });
    if (!s.need[0] && !s.need[1]) { s.phase = 'bid'; s.need = [true, true]; }
    return;
  }
  s.bids[side] = a.cards.slice(); s.need[side] = false;
  if (s.need[0] || s.need[1]) return;
  resolve(s, ev);
}
function resolve(s, ev) {
  const v = s.bids.map(coinOf), debt = s.pot.includes('DEBT');
  let taker = null, payer = null;
  if (v[0] !== v[1]) {
    const hi = v[0] > v[1] ? 0 : 1;
    if (debt) taker = 1 - hi; else { taker = hi; payer = hi; }
  }
  const pot = s.pot.slice();
  s.last = { bids: [s.bids[0].slice(), s.bids[1].slice()], values: v, pot, taker, payer };
  emit(ev, { t: 'reveal', bids: s.last.bids, values: v, pot, taker });
  if (payer !== null) { const P = s.p[payer]; removeFrom(P.hand, s.bids[payer]); P.discard.push(...s.bids[payer]); }
  if (taker !== null) { const P = s.p[taker]; P.discard.push(...pot); P.won.push(...pot); s.pot = []; }
  s.bids = [null, null];
  if (!s.prizes.length) { s.pot = []; return endGame(s, ev); }
  startRound(s, ev);
}
function endGame(s, ev) {
  const pts = s.p.map(pointsOf);
  if (pts[0] !== pts[1]) s.winner = pts[0] > pts[1] ? 0 : 1;
  else { const c = s.p.map(ownedCoin); s.winner = c[0] === c[1] ? 'draw' : c[0] > c[1] ? 0 : 1; }
  s.phase = 'over'; s.need = [false, false];
  emit(ev, { t: 'end', winner: s.winner, pts });
}
export function submit(s, side, a, ev) { const t = clone(s); mSubmit(t, side, a, ev); return t; }
export function _submit(t, side, a) { mSubmit(t, side, a, null); return t; }
export const actionKey = (a) => a.t + ':' + coinOf(a.cards);
