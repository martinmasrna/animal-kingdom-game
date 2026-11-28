// Curling line: stones on a one-dimensional sheet of 12 cells push the first stone in their path;
// closest to the Mark (cell 9) scores curling-style. Throws are cards bought with energy.
// Pure from the outside: act() clones the state.

export const CELLS = 12, MARK = 9, HOUSE = 3, ENDS = 6, THROWS = 8, HAND = 5, ENERGY = 5, LAG = 4;
export const CARDS = {
  Guard: { id: 'Guard', name: 'Guard', cost: 0, d: 5 },
  Short: { id: 'Short', name: 'Short', cost: 0, d: 7 },
  Draw8: { id: 'Draw8', name: 'Draw 8', cost: 1, d: 8 },
  Draw9: { id: 'Draw9', name: 'Draw 9', cost: 2, d: 9 },
  Draw10: { id: 'Draw10', name: 'Draw 10', cost: 1, d: 10 },
  Hit: { id: 'Hit', name: 'Hit', cost: 1, d: 12 },
  Any: { id: 'Any', name: 'Any', cost: 3, d: null },
};
export const DECK = { Guard: 2, Short: 2, Draw8: 2, Draw9: 2, Draw10: 2, Hit: 2, Any: 2 };
export const deckList = () => { const a = []; for (const [id, n] of Object.entries(DECK)) for (let i = 0; i < n; i++) a.push(id); return a; };
export const inHouse = (c) => Math.abs(c - MARK) <= HOUSE;

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleIn(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
export function clone(s) { return { ...s, stones: s.stones.map(x => ({ ...x })), score: s.score.slice(), energy: s.energy.slice(), p: s.p.map(p => ({ deck: p.deck.slice(), hand: p.hand.slice(), discard: p.discard.slice() })) }; }
function emit(ev, e) { if (ev) ev.push(e); }

// A throw to d: the lowest stone on cells 1..d stops it on the cell before and is pushed on by what
// is left of the throw; a pushed stone that meets another stops before it and passes the rest on.
// Returns the moves for the page: [{ uid, from, to }] with to 0 or 13 meaning out.
export function slide(stones, owner, d, uid) {
  const moves = [];
  const at = (c) => stones.find(x => x.cell === c);
  const firstIn = (lo, hi) => { let best = null; for (const x of stones) if (x.cell >= lo && x.cell <= hi && (!best || x.cell < best.cell)) best = x; return best; };
  const push = (st, k) => {
    const from = st.cell, target = from + k, q = firstIn(from + 1, target);
    if (q) { st.cell = q.cell - 1; moves.push({ uid: st.uid, from, to: st.cell }); push(q, target - q.cell + 1); }
    else if (target > CELLS) { moves.push({ uid: st.uid, from, to: CELLS + 1 }); stones.splice(stones.indexOf(st), 1); }
    else { st.cell = target; moves.push({ uid: st.uid, from, to: target }); }
  };
  const p = firstIn(1, d);
  if (!p) { stones.push({ uid, owner, cell: d }); moves.push({ uid, from: 0, to: d, thrown: true }); return moves; }
  const stop = p.cell - 1;
  if (stop >= 1) { stones.push({ uid, owner, cell: stop }); moves.push({ uid, from: 0, to: stop, thrown: true }); }
  else moves.push({ uid, from: 0, to: 0, thrown: true, out: true });
  push(p, d - p.cell + 1);
  return moves;
}
// The end's score if it stopped now: [side, points] or null for a blank end.
export function endScore(stones) {
  const best = [99, 99];
  for (const x of stones) if (inHouse(x.cell)) best[x.owner] = Math.min(best[x.owner], Math.abs(x.cell - MARK));
  if (best[0] === 99 && best[1] === 99) return null;
  if (best[0] === best[1]) return null;
  const w = best[0] < best[1] ? 0 : 1;
  const n = stones.filter(x => x.owner === w && inHouse(x.cell) && Math.abs(x.cell - MARK) < best[1 - w]).length;
  return [w, n];
}

function startEnd(s, ev) {
  s.stones = []; s.throwNo = 0; s.energy = [ENERGY, ENERGY];
  for (const P of s.p) {
    P.discard.push(...P.hand); P.hand = [];
    for (let i = 0; i < HAND; i++) { if (!P.deck.length) { P.deck = shuffleIn(s, P.discard); P.discard = []; } if (P.deck.length) P.hand.push(P.deck.shift()); }
  }
  s.toMove = 1 - s.hammer;
  emit(ev, { t: 'endStart', end: s.end, hammer: s.hammer });
}
export function newMatch({ seed, hammer }) {
  const s = { seed: (seed >>> 0) || 1, end: 1, throwNo: 0, hammer: 0, firstHammer: 0, toMove: 0, stones: [], score: [0, 0], energy: [ENERGY, ENERGY], winner: null, cap: false, uid: 1, lastEnd: null,
    p: [{ deck: deckList(), hand: [], discard: [] }, { deck: deckList(), hand: [], discard: [] }] };
  for (const P of s.p) shuffleIn(s, P.deck);
  s.hammer = rand(s) < 0.5 ? 0 : 1;
  if (hammer === 0 || hammer === 1) s.hammer = hammer;
  s.firstHammer = s.first = s.hammer; // the first-player check reads the hammer in end 1
  startEnd(s, null);
  return s;
}

// Actions: { t: 'throw', card, d } with card null for the free Lag (d 4); Any takes any d from 4 to 12.
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toMove, out = [{ t: 'throw', card: null, d: LAG }];
  for (const id of new Set(s.p[me].hand)) {
    const c = CARDS[id];
    if (c.cost > s.energy[me]) continue;
    if (c.d) out.push({ t: 'throw', card: id, d: c.d });
    else for (let d = LAG; d <= CELLS; d++) out.push({ t: 'throw', card: id, d });
  }
  return out;
}
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (a.t !== 'throw') throw new Error('unknown action');
  const me = s.toMove, P = s.p[me];
  if (a.card) {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > s.energy[me] || (c.d ? a.d !== c.d : !(a.d >= LAG && a.d <= CELLS))) throw new Error('illegal throw');
    s.energy[me] -= c.cost; P.hand.splice(k, 1); P.discard.push(a.card);
  } else if (a.d !== LAG) throw new Error('Lag is d 4');
  const moves = slide(s.stones, me, a.d, s.uid++);
  emit(ev, { t: 'throw', side: me, card: a.card, d: a.d, moves });
  s.throwNo++;
  if (s.throwNo < THROWS) { s.toMove = s.throwNo % 2 === 0 ? 1 - s.hammer : s.hammer; return; }
  // the end is scored
  const sc = endScore(s.stones);
  s.lastEnd = sc;
  if (sc) { s.score[sc[0]] += sc[1]; s.hammer = 1 - sc[0]; }
  emit(ev, { t: 'score', end: s.end, result: sc, score: s.score.slice() });
  const done = s.end >= ENDS && s.score[0] !== s.score[1];
  if (done || s.end >= ENDS + 1) {
    s.winner = s.score[0] === s.score[1] ? 'draw' : s.score[0] > s.score[1] ? 0 : 1;
    emit(ev, { t: 'end', winner: s.winner }); return;
  }
  s.end++;
  startEnd(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
