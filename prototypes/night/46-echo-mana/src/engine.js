// 46 Echo mana. The vanilla duel (30 health, board 7, opening hands 3 and 4 plus the Coin for
// the second player, draw 1 a turn, fatigue, units attack from the turn after they are played,
// any enemy unit or the enemy hero) with one rule changed: at the start of your turn your mana
// is what the opponent spent on their last turn plus 1, at least 2 and at most 10.
// Pure from the outside: act() clones the state; step() mutates it.

export const HP = 30, MIN_MANA = 2, MAX_MANA = 10, BOARD = 7, TURN_LIMIT = 100;

export const CARDS = {
  ST: { id: 'ST', name: 'Striker', kind: 'Unit', cost: 1, atk: 2, hp: 1 },
  RA: { id: 'RA', name: 'Raider', kind: 'Unit', cost: 2, atk: 3, hp: 2 },
  GU: { id: 'GU', name: 'Guard', kind: 'Unit', cost: 2, atk: 2, hp: 3 },
  LI: { id: 'LI', name: 'Line', kind: 'Unit', cost: 3, atk: 3, hp: 4 },
  HE: { id: 'HE', name: 'Heavy', kind: 'Unit', cost: 4, atk: 4, hp: 5 },
  BI: { id: 'BI', name: 'Big', kind: 'Unit', cost: 5, atk: 5, hp: 5 },
  HU: { id: 'HU', name: 'Huge', kind: 'Unit', cost: 6, atk: 6, hp: 7 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'Spell', cost: 1, dmg: 2 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'Spell', cost: 2, dmg: 3 },
  H6: { id: 'H6', name: 'Hit 6', kind: 'Spell', cost: 4, dmg: 6 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0 },
};
export const DECK = { ST: 3, RA: 3, GU: 3, LI: 3, HE: 3, BI: 3, HU: 3, H2: 3, H3: 3, H6: 3 };
export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// mana: this turn's total; left: what is left of it; spent: paid for cards this turn;
// lastSpent: what this player paid on its previous turn (sets the opponent's next mana).
function newPlayer() { return { hp: HP, mana: 0, left: 0, spent: 0, lastSpent: -1, fatigue: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  p.fatigue++; p.hp -= p.fatigue; emit(s, ev, { t: 'fatigue', side, n: p.fatigue, hp: p.hp });
}
// the mana a player gets from what the other spent (a first turn, with nothing spent before it, gets the floor)
export const echo = (spent) => Math.max(MIN_MANA, Math.min(MAX_MANA, spent + 1));

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toMove: 0, first: 0, winner: null, uid: 1, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.toMove = s.first;
  startTurn(s, null);
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

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side], o = s.p[1 - side];
  s.turnNo++;
  p.mana = p.left = echo(Math.max(0, o.lastSpent));
  p.spent = 0;
  emit(s, ev, { t: 'turn', side, mana: p.mana });
  for (const m of p.board) m.ready = true;
  draw(s, side, ev);
  checkWin(s, ev);
}

// Actions: { t: 'play', card, side, i } (side/i: a spell's target, i = -1 the hero)
//          { t: 'attack', from, to } (to: enemy board index or -1 the hero)
//          { t: 'end' }
export function key(a) {
  if (a.t === 'end') return 'e';
  if (a.t === 'attack') return 'a' + a.from + ':' + a.to;
  return 'p' + a.card + (CARDS[a.card].kind === 'Spell' ? ':' + a.side + ':' + a.i : '');
}
export function isLegal(s, a) {
  if (s.winner !== null || !a) return false;
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (a.t === 'end') return true;
  if (a.t === 'attack') { const m = P.board[a.from]; return !!m && m.ready && (a.to === -1 || (a.to >= 0 && a.to < O.board.length)); }
  if (a.t !== 'play' || !P.hand.includes(a.card)) return false;
  const c = CARDS[a.card];
  if (c.cost > P.left) return false;
  if (c.kind === 'Unit') return P.board.length < BOARD;
  if (c.kind === 'Spell') return (a.side === 0 || a.side === 1) && a.i >= -1 && a.i < s.p[a.side].board.length;
  return true;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.left) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'Coin') out.push({ t: 'play', card: id });
    else for (const side of [0, 1]) for (let i = -1; i < s.p[side].board.length; i++) out.push({ t: 'play', card: id, side, i });
  }
  P.board.forEach((m, from) => { if (m.ready) for (let to = -1; to < O.board.length; to++) out.push({ t: 'attack', from, to }); });
  out.push({ t: 'end' });
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
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'attack') {
    const m = P.board[a.from];
    m.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null, atk: m.atk });
    if (a.to < 0) hit(s, 1 - me, -1, m.atk, ev);
    else { const d = O.board[a.to], da = d.atk; hit(s, 1 - me, a.to, m.atk, ev); hit(s, me, a.from, da, ev); }
    sweep(s, ev); checkWin(s, ev);
    return;
  }
  const c = CARDS[a.card];
  P.left -= c.cost; P.spent += c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
  emit(s, ev, { t: 'play', side: me, card: a.card, a });
  if (c.kind === 'Unit') {
    const m = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
    P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
  } else if (c.kind === 'Coin') { P.left += 1; P.mana += 1; emit(s, ev, { t: 'coin', side: me }); }
  else { hit(s, a.side, a.i, c.dmg, ev); sweep(s, ev); checkWin(s, ev); }
}
function endTurn(s, ev) {
  const P = s.p[s.turn];
  P.lastSpent = P.spent;
  emit(s, ev, { t: 'endturn', side: s.turn, spent: P.spent });
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toMove = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
