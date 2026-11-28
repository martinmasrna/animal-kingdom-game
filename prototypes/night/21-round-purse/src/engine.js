// Round purse: best of three rounds of total power, a round ends when both have passed, and one
// mana purse pays for every card of the whole match. Pure from the outside: act() clones the state.

export const PURSE = 18, OPENING = 8, REDRAW = 2, HAND_MAX = 10, ROUNDS = 3, TURN_CAP = 400;
export const CARDS = {
  Grunt: { id: 'Grunt', name: 'Grunt', cost: 0, power: 1 },
  Troop: { id: 'Troop', name: 'Troop', cost: 1, power: 3 },
  Squad: { id: 'Squad', name: 'Squad', cost: 2, power: 5 },
  Heavy: { id: 'Heavy', name: 'Heavy', cost: 3, power: 7 },
  Big: { id: 'Big', name: 'Big', cost: 5, power: 11 },
  Gift: { id: 'Gift', name: 'Gift', cost: 0, power: 0, gift: 4, draw: 2 },
  Cut: { id: 'Cut', name: 'Cut', cost: 2, power: 0, cut: true },
};
export const DECK = { Grunt: 4, Troop: 4, Squad: 3, Heavy: 3, Big: 2, Gift: 2, Cut: 2 };
export const deckList = () => { const a = []; for (const [id, n] of Object.entries(DECK)) for (let i = 0; i < n; i++) a.push(id); return a; };

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleIn(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
export function clone(s) {
  return { ...s, passed: s.passed.slice(), wins: s.wins.slice(), purse: s.purse.slice(), results: s.results.slice(), table: s.table.map(T => T.map(c => ({ ...c }))),
    p: s.p.map(p => ({ deck: p.deck.slice(), hand: p.hand.slice(), discard: p.discard.slice() })) };
}
function emit(ev, e) { if (ev) ev.push(e); }
function draw(s, side, n, ev) { const P = s.p[side]; for (let i = 0; i < n && P.deck.length && P.hand.length < HAND_MAX; i++) { P.hand.push(P.deck.shift()); emit(ev, { t: 'draw', side }); } }
export const total = (s, side) => s.table[side].reduce((a, c) => a + c.power, 0);

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, round: 1, first: 0, turn: 0, toMove: 0, turnNo: 0, winner: null, cap: false, uid: 1,
    passed: [false, false], wins: [0, 0], purse: [PURSE, PURSE], results: [], table: [[], []], p: [{ deck: deckList(), hand: [], discard: [] }, { deck: deckList(), hand: [], discard: [] }] };
  for (const P of s.p) shuffleIn(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  draw(s, 0, OPENING, null); draw(s, 1, OPENING, null);
  s.turn = s.toMove = s.first;
  return s;
}
const starter = (s, round) => round === 2 ? 1 - s.first : s.first;

// Actions: { t: 'play', card } or { t: 'pass' }.
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, out = [{ t: 'pass' }];
  for (const id of new Set(s.p[me].hand)) if (CARDS[id].cost <= s.purse[me]) out.push({ t: 'play', card: id });
  return out;
}
function endRound(s, ev) {
  const a = total(s, 0), b = total(s, 1), w = a === b ? null : a > b ? 0 : 1;
  if (w !== null) s.wins[w]++;
  s.results.push({ w, power: [a, b] });
  emit(ev, { t: 'round', round: s.round, w, power: [a, b], wins: s.wins.slice() });
  for (const side of [0, 1]) for (const c of s.table[side]) s.p[c.owner].discard.push(c.id);
  s.table = [[], []];
  if (s.wins[0] >= 2 || s.wins[1] >= 2 || s.round >= ROUNDS) {
    s.winner = s.wins[0] === s.wins[1] ? 'draw' : s.wins[0] > s.wins[1] ? 0 : 1;
    emit(ev, { t: 'end', winner: s.winner }); return;
  }
  s.round++; s.passed = [false, false];
  draw(s, 0, REDRAW, ev); draw(s, 1, REDRAW, ev);
  s.turn = s.toMove = starter(s, s.round);
  emit(ev, { t: 'start', round: s.round, side: s.turn });
}
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, O = 1 - me, P = s.p[me];
  if (s.passed[me]) throw new Error('already passed');
  if (a.t === 'pass') { s.passed[me] = true; emit(ev, { t: 'pass', side: me }); }
  else if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > s.purse[me]) throw new Error('illegal play');
    s.purse[me] -= c.cost; P.hand.splice(k, 1);
    emit(ev, { t: 'play', side: me, card: a.card });
    if (c.power) { const x = { uid: s.uid++, id: a.card, power: c.power, owner: me }; s.table[me].push(x); emit(ev, { t: 'place', side: me, uid: x.uid }); }
    else if (c.gift) { const x = { uid: s.uid++, id: a.card, power: c.gift, owner: me }; s.table[O].push(x); emit(ev, { t: 'place', side: O, uid: x.uid, gift: true }); draw(s, me, c.draw, ev); }
    else if (c.cut) {
      P.discard.push(a.card);
      const T = s.table[O];
      if (T.length) { let k2 = 0; T.forEach((x, i) => { if (x.power > T[k2].power) k2 = i; }); const x = T.splice(k2, 1)[0]; s.p[x.owner].discard.push(x.id); emit(ev, { t: 'cut', side: O, uid: x.uid, id: x.id }); }
    }
  } else throw new Error('unknown action');
  s.turnNo++;
  if (s.passed[0] && s.passed[1]) { endRound(s, ev); return; }
  if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.cap = true; emit(ev, { t: 'end', winner: 'draw' }); return; }
  if (!s.passed[O]) s.turn = O;
  s.toMove = s.turn;
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
// every card of `side` not in its hand or deck: what the other player has seen
export function seen(s, side) { const out = s.p[side].discard.slice(); for (const T of s.table) for (const c of T) if (c.owner === side) out.push(c.id); return out; }
