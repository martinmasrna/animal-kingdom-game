// 07 Blind fronts. Each round both gain energy and draw; three fronts are worth 1, 2 and 3 in a
// shown random order; players alternately commit one card face-down to a front, paying its cost,
// or pass for the round; then everything is revealed and the higher strength at each front takes
// its value. Energy banks between rounds. Pure from the outside: act() clones the state.

export const INCOME = 4, CAP = 10, HAND_MAX = 8, DRAW = 2, TARGET = 12, ROUNDS = 12, FRONTS = 3;

export const CARDS = {
  FE: { id: 'FE', name: 'Feint', cost: 0, str: 0, copies: 3 },
  SC: { id: 'SC', name: 'Scout', cost: 0, str: 1, copies: 3 },
  TR: { id: 'TR', name: 'Troop', cost: 1, str: 2, copies: 4 },
  SQ: { id: 'SQ', name: 'Squad', cost: 2, str: 4, copies: 4 },
  EL: { id: 'EL', name: 'Elite', cost: 3, str: 5, copies: 3 },
  HE: { id: 'HE', name: 'Heavy', cost: 4, str: 7, copies: 2 },
  LO: { id: 'LO', name: 'Lone', cost: 2, str: 3, copies: 3, text: '+3 if it is your only card at its front.' },
  MA: { id: 'MA', name: 'Mass', cost: 1, str: 1, copies: 3, text: '+1 for each other card of yours at its front.' },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < c.copies; i++) out.push(c.id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { energy: 4, score: 0, hand: [], deck: deckList(), discard: [], placed: [[], [], []], passed: false }; }
export function clone(s) {
  return { ...s, values: s.values.slice(), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), placed: p.placed.map(f => f.slice()) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function draw(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(s, p.discard); p.discard = []; emit(s, ev, { t: 'reshuffle', side }); }
  p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side });
}

// strength of every card a side placed at a front, after card texts
export function frontStrength(cards) {
  let n = 0;
  for (const id of cards) {
    const c = CARDS[id];
    n += c.str;
    if (id === 'LO' && cards.length === 1) n += 3;
    if (id === 'MA') n += cards.length - 1;
  }
  return n;
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, first: 0, lead: 0, toMove: 0, phase: 'place', values: [1, 2, 3], winner: null, steps: 0, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (const p of s.p) for (let i = 0; i < 5; i++) p.hand.push(p.deck.shift());
  startRound(s, null);
  return s;
}
function startRound(s, ev) {
  s.round++;
  s.lead = s.round % 2 === 1 ? s.first : 1 - s.first;
  for (const side of [0, 1]) {
    const p = s.p[side];
    p.energy = Math.min(CAP, p.energy + INCOME);
    p.passed = false; p.placed = [[], [], []]; p.lastSolo = -1;
    for (let i = 0; i < DRAW; i++) draw(s, side, ev);
  }
  s.values = shuffleInPlace(s, [1, 2, 3]);
  emit(s, ev, { t: 'round', round: s.round, lead: s.lead, values: s.values.slice() });
  s.phase = 'discard';
  nextDiscard(s);
}
// the round's first player discards down to the hand limit first, then the other
function nextDiscard(s) {
  for (const side of [s.lead, 1 - s.lead]) if (s.p[side].hand.length > HAND_MAX) { s.toMove = side; return; }
  s.phase = 'place'; s.toMove = s.lead;
}

const ORDER = Object.keys(CARDS);
export const soloIndex = (a) => a.front * 10 + ORDER.indexOf(a.card);

// Actions: { t: 'discard', card } · { t: 'place', card, front } · { t: 'pass' }
export function key(a) { return a.t === 'pass' ? 'x' : a.t === 'discard' ? 'd' + a.card : 'p' + a.card + a.front; }
export function isLegal(s, a) {
  if (s.winner !== null) return false;
  const P = s.p[s.toMove];
  if (s.phase === 'discard') return a.t === 'discard' && P.hand.includes(a.card);
  if (a.t === 'pass') return true;
  return a.t === 'place' && P.hand.includes(a.card) && CARDS[a.card].cost <= P.energy && Number.isInteger(a.front) && a.front >= 0 && a.front < FRONTS;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.toMove], out = [];
  if (s.phase === 'discard') { for (const id of new Set(P.hand)) out.push({ t: 'discard', card: id }); return out; }
  for (const id of new Set(P.hand)) if (CARDS[id].cost <= P.energy) for (let f = 0; f < FRONTS; f++) out.push({ t: 'place', card: id, front: f });
  out.push({ t: 'pass' });
  return out;
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.toMove, P = s.p[me];
  s.steps++;
  if (a.t === 'discard') {
    P.hand.splice(P.hand.indexOf(a.card), 1); P.discard.push(a.card);
    emit(s, ev, { t: 'discard', side: me, card: a.card });
    nextDiscard(s); return;
  }
  if (a.t === 'pass') { P.passed = true; emit(s, ev, { t: 'pass', side: me }); }
  else {
    P.hand.splice(P.hand.indexOf(a.card), 1); P.energy -= CARDS[a.card].cost; P.placed[a.front].push(a.card);
    if (s.p[1 - me].passed) P.lastSolo = soloIndex(a); // placements made alone, for bots that skip reorderings
    emit(s, ev, { t: 'place', side: me, front: a.front, cost: CARDS[a.card].cost, card: a.card });
  }
  const O = s.p[1 - me];
  if (P.passed && O.passed) { reveal(s, ev); return; }
  s.toMove = O.passed ? me : 1 - me;
}
function reveal(s, ev) {
  const res = [];
  for (let f = 0; f < FRONTS; f++) {
    const a = frontStrength(s.p[0].placed[f]), b = frontStrength(s.p[1].placed[f]);
    const w = a > b ? 0 : b > a ? 1 : null;
    if (w !== null) s.p[w].score += s.values[f];
    res.push({ front: f, str: [a, b], winner: w, value: s.values[f], cards: [s.p[0].placed[f].slice(), s.p[1].placed[f].slice()] });
  }
  emit(s, ev, { t: 'reveal', res, score: [s.p[0].score, s.p[1].score] });
  for (const p of s.p) { for (const f of p.placed) p.discard.push(...f); p.placed = [[], [], []]; }
  const [a, b] = [s.p[0].score, s.p[1].score];
  if ((a >= TARGET || b >= TARGET) && a !== b) s.winner = a > b ? 0 : 1;
  else if (s.round >= ROUNDS) { s.winner = a > b ? 0 : b > a ? 1 : 'draw'; s.limit = true; }
  if (s.winner !== null) { s.phase = 'over'; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startRound(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
