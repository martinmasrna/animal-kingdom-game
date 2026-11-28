// Score-or-fight duel. Units with attack and health and a mana cost; a unit cannot act the turn
// it is played. Each turn a ready unit either attacks an enemy unit (both deal their attack to each
// other) or scores its current health. There is no hero. First to 40 wins.
// Pure from the outside: act() clones the state; _act() mutates (for the bots' play-outs).

export const TARGET = 40, MAX_MANA = 10, BOARD = 6, TURN_LIMIT = 80;

export const CARDS = {
  STR: { id: 'STR', name: 'Striker', kind: 'Unit', cost: 1, atk: 2, hp: 1 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'Unit', cost: 2, atk: 3, hp: 2 },
  GRD: { id: 'GRD', name: 'Guard', kind: 'Unit', cost: 2, atk: 2, hp: 3 },
  LIN: { id: 'LIN', name: 'Line', kind: 'Unit', cost: 3, atk: 3, hp: 4 },
  HVY: { id: 'HVY', name: 'Heavy', kind: 'Unit', cost: 4, atk: 4, hp: 5 },
  BIG: { id: 'BIG', name: 'Big', kind: 'Unit', cost: 5, atk: 5, hp: 5 },
  HUG: { id: 'HUG', name: 'Huge', kind: 'Unit', cost: 6, atk: 6, hp: 7 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'Spell', cost: 1, dmg: 2 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'Spell', cost: 2, dmg: 3 },
  H6: { id: 'H6', name: 'Hit 6', kind: 'Spell', cost: 4, dmg: 6 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0 },
};
export const DECK = { STR: 3, RAI: 3, GRD: 3, LIN: 3, HVY: 3, BIG: 3, HUG: 3, H2: 3, H3: 3, H6: 3 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { score: 0, mana: 0, maxMana: 0, fatigue: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
function gain(s, side, n, ev, why) {
  s.p[side].score += n; emit(s, ev, { t: 'gain', side, n, why, score: s.p[side].score });
}
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { const c = p.deck.shift(); p.hand.push(c); emit(s, ev, { t: 'draw', side }); return; }
  p.fatigue++; emit(s, ev, { t: 'fatigue', side, n: 2 * p.fatigue });
  gain(s, 1 - side, 2 * p.fatigue, ev, 'fatigue');
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, capped: false, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].score >= TARGET, b = s.p[1].score >= TARGET;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 0 : 1;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const m of p.board) m.ready = true;
  draw(s, side, ev);
  checkWin(s, ev);
}

// Actions: { t: 'play', card, to } (to: enemy board index, spells only)
//          { t: 'attack', from, to }   { t: 'score', from }   { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'Coin') out.push({ t: 'play', card: id });
    else for (let i = 0; i < O.board.length; i++) out.push({ t: 'play', card: id, to: i });
  }
  P.board.forEach((m, from) => {
    if (!m.ready) return;
    out.push({ t: 'score', from });
    for (let to = 0; to < O.board.length; to++) out.push({ t: 'attack', from, to });
  });
  out.push({ t: 'end' });
  return out;
}

function hit(s, side, i, n, ev) {
  const m = s.p[side].board[i]; m.hp -= n;
  emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid });
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, i, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}

function endTurn(s, ev) {
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  startTurn(s, ev);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (c.kind === 'Unit' && P.board.length >= BOARD) throw new Error('board full');
    if (c.kind === 'Spell' && !(a.to >= 0 && a.to < O.board.length)) throw new Error('bad target');
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, to: a.to, tuid: c.kind === 'Spell' ? O.board[a.to].uid : null, mana: P.mana });
    if (c.kind === 'Unit') {
      const m = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
      P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    } else if (c.kind === 'Coin') { P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    else { hit(s, 1 - me, a.to, c.dmg, ev); sweep(s, ev); }
  } else if (a.t === 'attack') {
    const m = P.board[a.from], d = O.board[a.to];
    if (!m || !m.ready || !d) throw new Error('illegal attack');
    m.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: d.uid });
    const da = d.atk; hit(s, 1 - me, a.to, m.atk, ev); hit(s, me, a.from, da, ev);
    sweep(s, ev);
  } else if (a.t === 'score') {
    const m = P.board[a.from];
    if (!m || !m.ready) throw new Error('illegal score');
    m.ready = false;
    emit(s, ev, { t: 'score', side: me, from: a.from, uid: m.uid, n: m.hp });
    gain(s, me, m.hp, ev, 'score');
  } else throw new Error('unknown action ' + a.t);
  checkWin(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

// What a player can see of a position, as one string: both boards, scores and mana, own hand.
export function key(s) {
  const P = s.p[s.turn];
  return JSON.stringify([s.turn, s.winner, s.p.map(p => [p.score, p.mana, p.board.map(m => m.card + ':' + m.hp + (m.ready ? 'r' : '')).sort()]), P.hand.slice().sort()]);
}
// The same position with everything the mover cannot see dealt again: the opponent's hand and
// deck reshuffled together (the Coin stays where it is, it is public), the mover's deck reshuffled.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const coins = O.hand.filter(c => c === 'COIN'), hidden = O.hand.filter(c => c !== 'COIN');
  const pool = shuffle(hidden.concat(O.deck), rng);
  O.hand = pool.slice(0, hidden.length).concat(coins); O.deck = pool.slice(hidden.length);
  shuffle(P.deck, rng);
  return t;
}
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
