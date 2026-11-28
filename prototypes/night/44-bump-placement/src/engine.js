// 44 Bump placement. Five shared action spaces; players alternately place costed cards on them, a
// stronger card bumping a weaker enemy card back to its owner's hand; when both have passed, the
// spaces pay out in order. First to 20 points at the end of a round; after round 12 the higher.
// Pure from the outside: act() clones the state.

export const TARGET = 20, ROUNDS = 12, BASE_MANA = 4, FUND = 3, DRAW = 3, HAND_MAX = 8, OPEN_HAND = 5;

export const CARDS = {
  WOR: { id: 'WOR', name: 'Worker', cost: 0, str: 1 },
  HAN: { id: 'HAN', name: 'Hand', cost: 1, str: 2 },
  FOR: { id: 'FOR', name: 'Foreman', cost: 2, str: 3 },
  BOS: { id: 'BOS', name: 'Boss', cost: 3, str: 4 },
  CHI: { id: 'CHI', name: 'Chief', cost: 5, str: 6 },
  LOC: { id: 'LOC', name: 'Lock', cost: 2, str: 2, lock: true },
  SHO: { id: 'SHO', name: 'Shove', cost: 1, str: 1, shove: 3 },
};
export const DECK = { WOR: 6, HAN: 5, FOR: 4, BOS: 3, CHI: 2, LOC: 2, SHO: 2 };
// the spaces, in the order they pay out at the end of a round
export const SPACES = [
  { id: 'S3', name: 'Score 3', text: '+3 points' },
  { id: 'S1', name: 'Score 1', text: '+1 point, draw 1' },
  { id: 'ST', name: 'Study', text: 'Draw 2' },
  { id: 'FU', name: 'Fund', text: '+3 mana next round' },
  { id: 'SA', name: 'Sabotage', text: 'They discard a random card' },
];

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { points: 0, mana: 0, fund: false, passed: false, hand: [], deck: deckList(), discard: [] }; }
export function clone(s) {
  return { seed: s.seed, round: s.round, turnNo: s.turnNo, first: s.first, starter: s.starter, toAct: s.toAct, phase: s.phase, winner: s.winner, capped: s.capped, byLimit: s.byLimit,
    spaces: s.spaces.map(x => x && { ...x }), p: s.p.map(p => ({ points: p.points, mana: p.mana, fund: p.fund, passed: p.passed, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.round; ev.push(e); } }
function draw(s, side, n, ev) {
  const p = s.p[side];
  for (let i = 0; i < n; i++) {
    if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(s, p.discard); p.discard = []; emit(s, ev, { t: 'reshuffle', side }); }
    p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side });
  }
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, round: 0, turnNo: 0, first: 0, starter: 0, toAct: 0, phase: 'place', winner: null, capped: false, byLimit: false, spaces: [null, null, null, null, null], p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (const side of [0, 1]) draw(s, side, OPEN_HAND, null);
  startRound(s, null);
  return s;
}

// a new round: the starter alternates; both draw 3, mana 4 (+3 after Fund), then anyone over 8
// cards discards down, the starter first
function startRound(s, ev) {
  s.round++;
  s.starter = s.round === 1 ? s.first : 1 - s.starter;
  emit(s, ev, { t: 'round', starter: s.starter });
  for (const side of [0, 1]) {
    const p = s.p[side];
    draw(s, side, DRAW, ev);
    p.mana = BASE_MANA + (p.fund ? FUND : 0); p.fund = false; p.passed = false;
  }
  nextDiscarder(s);
}
function nextDiscarder(s) {
  for (const side of [s.starter, 1 - s.starter]) if (s.p[side].hand.length > HAND_MAX) { s.phase = 'discard'; s.toAct = side; return; }
  s.phase = 'place'; s.toAct = s.starter;
}

// can card id go on space k for player me
export function canPlace(s, me, id, k) {
  const c = CARDS[id], x = s.spaces[k];
  if (c.cost > s.p[me].mana) return false;
  if (!x) return true;
  if (x.side === me) return false;
  return !CARDS[x.card].lock && CARDS[x.card].str < c.str;
}
// the enemy cards a Shove placed on space k may push out: strength 3 or less, not a Lock, another space
export function shoveTargets(s, me, k) {
  const out = [];
  s.spaces.forEach((x, j) => { if (x && j !== k && x.side !== me && !CARDS[x.card].lock && CARDS[x.card].str <= CARDS.SHO.shove) out.push(j); });
  return out;
}

// Actions: { t: 'place', card, space, tgt } (tgt: for Shove, the space whose enemy card it bumps, or -1 when none can be)
//          { t: 'pass' }   { t: 'discard', card } (when over 8 cards at the start of a round)
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toAct, P = s.p[me], out = [];
  if (s.phase === 'discard') { for (const id of new Set(P.hand)) out.push({ t: 'discard', card: id }); return out; }
  for (const id of new Set(P.hand)) for (let k = 0; k < SPACES.length; k++) if (canPlace(s, me, id, k)) {
    if (CARDS[id].shove) { const tg = shoveTargets(s, me, k); if (tg.length) for (const j of tg) out.push({ t: 'place', card: id, space: k, tgt: j }); else out.push({ t: 'place', card: id, space: k, tgt: -1 }); }
    else out.push({ t: 'place', card: id, space: k });
  }
  out.push({ t: 'pass' });
  return out;
}
export const actionKey = (a) => a.t === 'place' ? `p${a.card}@${a.space}${a.tgt !== undefined ? '>' + a.tgt : ''}` : a.t === 'discard' ? 'd' + a.card : 'x';

function bump(s, k, ev) { const x = s.spaces[k]; s.spaces[k] = null; s.p[x.side].hand.push(x.card); emit(s, ev, { t: 'bump', side: x.side, card: x.card, space: k }); }

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me];
  s.turnNo++;
  if (a.t === 'discard') {
    if (s.phase !== 'discard') throw new Error('not discarding');
    const k = P.hand.indexOf(a.card); if (k < 0) throw new Error('no such card');
    P.hand.splice(k, 1); P.discard.push(a.card); emit(s, ev, { t: 'discard', side: me, card: a.card });
    nextDiscarder(s);
    return;
  }
  if (s.phase !== 'place') throw new Error('not placing');
  if (a.t === 'pass') {
    P.passed = true; emit(s, ev, { t: 'pass', side: me });
    if (s.p[1 - me].passed) return endRound(s, ev);
    s.toAct = 1 - me;
    return;
  }
  const c = CARDS[a.card], h = P.hand.indexOf(a.card);
  if (h < 0 || !canPlace(s, me, a.card, a.space)) throw new Error('illegal place');
  if (c.shove) { const tg = shoveTargets(s, me, a.space); if (tg.length ? !tg.includes(a.tgt) : a.tgt !== -1) throw new Error('bad shove target'); }
  P.mana -= c.cost; P.hand.splice(h, 1);
  emit(s, ev, { t: 'place', side: me, card: a.card, space: a.space, mana: P.mana });
  if (s.spaces[a.space]) bump(s, a.space, ev);
  s.spaces[a.space] = { card: a.card, side: me };
  if (c.shove && a.tgt >= 0) bump(s, a.tgt, ev);
  if (!s.p[1 - me].passed) s.toAct = 1 - me;
}

// both have passed: the spaces pay out in order, every placed card goes to its owner's discard,
// then 20 points wins (both: the higher; equal plays on); after round 12 the higher wins, equal draws
function endRound(s, ev) {
  emit(s, ev, { t: 'payout' });
  const sp = s.spaces;
  if (sp[0]) { const p = s.p[sp[0].side]; p.points += 3; emit(s, ev, { t: 'gain', side: sp[0].side, space: 0, n: 3, points: p.points }); }
  if (sp[1]) { const p = s.p[sp[1].side]; p.points += 1; emit(s, ev, { t: 'gain', side: sp[1].side, space: 1, n: 1, points: p.points }); draw(s, sp[1].side, 1, ev); }
  if (sp[2]) { emit(s, ev, { t: 'study', side: sp[2].side, space: 2 }); draw(s, sp[2].side, 2, ev); }
  if (sp[3]) { s.p[sp[3].side].fund = true; emit(s, ev, { t: 'fund', side: sp[3].side, space: 3 }); }
  if (sp[4]) { const o = 1 - sp[4].side, O = s.p[o]; if (O.hand.length) { const k = Math.floor(rand(s) * O.hand.length); const c = O.hand.splice(k, 1)[0]; O.discard.push(c); emit(s, ev, { t: 'sabotage', side: o, card: c, space: 4 }); } }
  for (let k = 0; k < sp.length; k++) if (sp[k]) { s.p[sp[k].side].discard.push(sp[k].card); sp[k] = null; }
  emit(s, ev, { t: 'cleared' });
  const a = s.p[0].points, b = s.p[1].points;
  if (a >= TARGET || b >= TARGET) { if (a !== b) { s.winner = a > b ? 0 : 1; emit(s, ev, { t: 'end', winner: s.winner }); return; } }
  if (s.round >= ROUNDS) { s.byLimit = true; s.winner = a === b ? 'draw' : a > b ? 0 : 1; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startRound(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
