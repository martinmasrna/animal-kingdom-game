// Toy 1: the smallest duel. Two identical characters, 30 health, Hearthstone mana,
// one shared deck list of two kinds of card: Strike (deal N) and Guard (absorb N
// until your next turn). Pure from the outside: transitions clone the state.

export const HP = 30, MAX_MANA = 10, TURN_LIMIT = 80;
// Energy: both start full at 10; unspent energy is kept; each turn you regain REGEN, never above 10.
export let REGEN = 4;
export function setRegen(r) { REGEN = r; }

// A Strike deals what it costs; a Guard absorbs twice what it costs (Martin, 2026-11-26).
export const CARDS = {};
for (let c = 1; c <= 6; c++) CARDS['S' + c] = { id: 'S' + c, kind: 'Strike', cost: c, n: c };
for (let c = 1; c <= 4; c++) CARDS['G' + c] = { id: 'G' + c, kind: 'Guard', cost: c, n: 2 * c };
export const DECK = { S1: 3, S2: 3, S3: 3, S4: 3, S5: 3, S6: 3, G1: 3, G2: 3, G3: 3, G4: 3 };

export function deckList() {
  const out = [];
  for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id);
  return out;
}

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

function newPlayer() { return { hp: HP, maxHp: HP, mana: MAX_MANA, turns: 0, block: 0, hand: [], deck: deckList(), played: [] }; }
function clonePlayer(p) { return { ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice() }; }
export function clone(s) { return { ...s, p: [clonePlayer(s.p[0]), clonePlayer(s.p[1])] }; }

function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function draw(s, side, n) {
  const p = s.p[side]; let d = 0;
  for (let i = 0; i < n && p.deck.length; i++) { p.hand.push(p.deck.shift()); d++; }
  return d;
}

export function newMatch({ seed }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  draw(s, s.first, 3); draw(s, 1 - s.first, 4);
  s.turn = s.first;
  mStartTurn(s, null);
  return s;
}

function mStartTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  if (p.block) emit(s, ev, { t: 'expire', side, n: p.block });
  p.block = 0;
  const before = p.mana;
  if (p.turns > 0) p.mana = Math.min(MAX_MANA, p.mana + REGEN);
  p.turns++;
  const drew = draw(s, side, 1);
  emit(s, ev, { t: 'start', side, mana: p.mana, gain: p.mana - before, drew });
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].hp <= 0, b = s.p[1].hp <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}

export function canPlay(s, id) {
  if (s.winner !== null || !CARDS[id]) return false;
  const p = s.p[s.turn];
  return p.hand.includes(id) && CARDS[id].cost <= p.mana;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  return [...new Set(s.p[s.turn].hand)].filter(id => canPlay(s, id));
}

function mPlay(s, id, ev) {
  if (!canPlay(s, id)) throw new Error('play: illegal ' + id);
  const side = s.turn, p = s.p[side], o = s.p[1 - side], c = CARDS[id];
  p.mana -= c.cost;
  p.hand.splice(p.hand.indexOf(id), 1);
  p.played.push(id);
  emit(s, ev, { t: 'play', side, card: id, mana: p.mana });
  if (c.kind === 'Strike') {
    const absorbed = Math.min(o.block, c.n);
    o.block -= absorbed;
    if (absorbed) emit(s, ev, { t: 'stop', side: 1 - side, n: absorbed, block: o.block });
    const dmg = c.n - absorbed;
    if (dmg) { o.hp -= dmg; emit(s, ev, { t: 'hit', side, dmg }); }
    checkWin(s, ev);
  } else {
    p.block += c.n;
    emit(s, ev, { t: 'guard', side, n: c.n, block: p.block });
  }
}
function mEndTurn(s, ev) {
  if (s.winner !== null) throw new Error('endTurn: match over');
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  mStartTurn(s, ev);
}

export function playAction(s, id, ev) { const t = clone(s); mPlay(t, id, ev); return t; }
export function endTurn(s, ev) { const t = clone(s); mEndTurn(t, ev); return t; }
export function _play(t, id) { mPlay(t, id, null); return t; }
export function _endTurn(t) { mEndTurn(t, null); return t; }

// Per card of the list: copies, played, and (for the viewer's own side) in hand / in deck.
export function deckSummary(s, side) {
  const p = s.p[side], cnt = (a) => a.reduce((m, x) => (m[x] = (m[x] || 0) + 1, m), {});
  const pl = cnt(p.played), h = cnt(p.hand), d = cnt(p.deck);
  return Object.entries(DECK).map(([id, total]) => ({ id, total, played: pl[id] || 0, inHand: h[id] || 0, inDeck: d[id] || 0, unseen: total - (pl[id] || 0) }));
}
