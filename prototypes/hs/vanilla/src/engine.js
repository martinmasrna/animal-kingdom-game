// Vanilla HS: a card duel with only text-less minions and damage spells, run on the usual
// rules of the genre: 30 health, mana 1 to 10, draw 1 a turn, opening hands 3 and 4 plus the
// Coin for the second player, 7 minions a side, a minion attacks from the turn after it is
// played, attacks hit any enemy minion or the enemy hero, fatigue on an empty deck.
// Pure from the outside: transitions clone the state.

export const HP = 30, MAX_MANA = 10, BOARD = 7, TURN_LIMIT = 100;

// The ten cards Martin reviewed (2026-11-26: "This looks great"), three copies each.
export const CARDS = {
  M1: { id: 'M1', kind: 'Minion', cost: 1, atk: 2, hp: 1 },
  M2a: { id: 'M2a', kind: 'Minion', cost: 2, atk: 3, hp: 2 },
  M2b: { id: 'M2b', kind: 'Minion', cost: 2, atk: 2, hp: 3 },
  M3: { id: 'M3', kind: 'Minion', cost: 3, atk: 3, hp: 4 },
  M4: { id: 'M4', kind: 'Minion', cost: 4, atk: 4, hp: 5 },
  M5: { id: 'M5', kind: 'Minion', cost: 5, atk: 5, hp: 5 },
  M6: { id: 'M6', kind: 'Minion', cost: 6, atk: 6, hp: 7 },
  S1: { id: 'S1', kind: 'Spell', cost: 1, dmg: 2 },
  S2: { id: 'S2', kind: 'Spell', cost: 2, dmg: 3 },
  S4: { id: 'S4', kind: 'Spell', cost: 4, dmg: 6 },
  COIN: { id: 'COIN', kind: 'Coin', cost: 0 },
};
export const DECK = { M1: 3, M2a: 3, M2b: 3, M3: 3, M4: 3, M5: 3, M6: 3, S1: 3, S2: 3, S4: 3 };
export let COIN = true;
export function setCoin(v) { COIN = v; }

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { hp: HP, mana: 0, maxMana: 0, fatigue: 0, hand: [], deck: deckList(), board: [], played: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { const c = p.deck.shift(); p.hand.push(c); emit(s, ev, { t: 'draw', side }); return; }
  p.fatigue++; p.hp -= p.fatigue; emit(s, ev, { t: 'fatigue', side, n: p.fatigue, hp: p.hp });
}

export function newMatch({ seed }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  if (COIN) s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  mStartTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].hp <= 0, b = s.p[1].hp <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}

function mStartTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const m of p.board) m.ready = true;
  draw(s, side, ev);
  checkWin(s, ev);
}

// Actions: { t: 'play', card, target } (target for spells: { side, i } with i a board index or -1 for the hero)
//          { t: 'attack', from, to } (from: own board index; to: enemy board index or -1 for the hero)
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Minion') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'Coin') out.push({ t: 'play', card: id });
    else for (const side of [0, 1]) { const B = s.p[side].board; out.push({ t: 'play', card: id, target: { side, i: -1 } }); for (let i = 0; i < B.length; i++) out.push({ t: 'play', card: id, target: { side, i } }); }
  }
  P.board.forEach((m, from) => { if (m.ready) { out.push({ t: 'attack', from, to: -1 }); for (let to = 0; to < O.board.length; to++) out.push({ t: 'attack', from, to }); } });
  return out;
}

function hit(s, side, i, n, ev) {
  if (i < 0) { s.p[side].hp -= n; emit(s, ev, { t: 'hit', side, i, n, hp: s.p[side].hp }); return; }
  const m = s.p[side].board[i]; m.hp -= n;
  emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid });
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, i, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}

function mAct(s, a, ev) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1); P.played.push(a.card);
    emit(s, ev, { t: 'play', side: me, card: a.card, target: a.target, mana: P.mana });
    if (c.kind === 'Minion') {
      if (P.board.length >= BOARD) throw new Error('board full');
      const m = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
      P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    } else if (c.kind === 'Coin') { P.mana = Math.min(MAX_MANA, P.mana + 1); emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    else {
      const { side, i } = a.target;
      if (i >= s.p[side].board.length) throw new Error('bad target');
      hit(s, side, i, c.dmg, ev); sweep(s, ev);
    }
  } else {
    const m = P.board[a.from];
    if (!m || !m.ready) throw new Error('illegal attack');
    m.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null });
    if (a.to < 0) hit(s, 1 - me, -1, m.atk, ev);
    else { const d = O.board[a.to]; const da = d.atk; hit(s, 1 - me, a.to, m.atk, ev); hit(s, me, a.from, da, ev); }
    sweep(s, ev);
  }
  checkWin(s, ev);
}
function mEndTurn(s, ev) {
  if (s.winner !== null) throw new Error('endTurn: match over');
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  mStartTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function endTurn(s, ev) { const t = clone(s); mEndTurn(t, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
