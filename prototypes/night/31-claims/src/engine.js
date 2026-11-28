// Claims: a unit duel where every card is played face-down as a claimed card from the shared
// list, paying the claimed cost; the opponent may challenge. A caught lie or a failed challenge
// costs 3 life. Pure from the outside: act() clones the state.

export const LIFE = 20, MAX_MANA = 10, BOARD = 5, PENALTY = 3, TURN_CAP = 120;

export const CARDS = {
  Striker: { id: 'Striker', name: 'Striker', kind: 'Unit', cost: 1, atk: 2, hp: 1 },
  Guard: { id: 'Guard', name: 'Guard', kind: 'Unit', cost: 2, atk: 1, hp: 4 },
  Raider: { id: 'Raider', name: 'Raider', kind: 'Unit', cost: 2, atk: 3, hp: 2 },
  Line: { id: 'Line', name: 'Line', kind: 'Unit', cost: 3, atk: 3, hp: 4 },
  Heavy: { id: 'Heavy', name: 'Heavy', kind: 'Unit', cost: 5, atk: 5, hp: 6 },
  Hit3: { id: 'Hit3', name: 'Hit 3', kind: 'Spell', cost: 2, dmg: 3 },
  Blast: { id: 'Blast', name: 'Blast', kind: 'Spell', cost: 4, dmg: 5 },
  Draw2: { id: 'Draw2', name: 'Draw 2', kind: 'Spell', cost: 2, draw: 2 },
};
export const LIST = ['Striker', 'Guard', 'Raider', 'Line', 'Heavy', 'Hit3', 'Blast', 'Draw2'];
export const COPIES = 3;
export const needsTarget = (id) => CARDS[id].dmg > 0;

export function deckList() { const out = []; for (const id of LIST) for (let i = 0; i < COPIES; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { life: LIFE, mana: 0, maxMana: 0, fatigue: 0, coin: false, hand: [], deck: deckList(), board: [], discard: [], revLie: 0, revHonest: 0, faced: 0, challenges: 0 }; }
export function clone(s) {
  return { ...s, pending: s.pending ? { ...s.pending, target: s.pending.target ? { ...s.pending.target } : null } : null,
    p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(ev, e) { if (ev) ev.push(e); }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(ev, { t: 'draw', side }); return; }
  p.fatigue++; p.life -= p.fatigue; emit(ev, { t: 'fatigue', side, n: p.fatigue });
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toMove: 0, first: 0, winner: null, cap: false, pending: null, uid: 1, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].coin = true;
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].life <= 0, b = s.p[1].life <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(ev, { t: 'end', winner: s.winner });
  return true;
}
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++; s.toMove = side;
  emit(ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const m of p.board) m.ready = true;
  draw(s, side, ev);
  checkWin(s, ev);
}

// Actions, by the player to move (s.toMove):
//   { t: 'play', card, name, target }  card: the real card from hand, name: the claimed card,
//                                     target { side, i } for Hit 3 and Blast (i = -1: the player)
//   { t: 'coin' }   { t: 'attack', from, to }  (to = -1: the player)   { t: 'end' }
//   while a claim is pending, by the other player: { t: 'challenge' } or { t: 'pass' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  if (s.pending) return [{ t: 'challenge' }, { t: 'pass' }];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [{ t: 'end' }];
  if (P.coin) out.push({ t: 'coin' });
  for (const card of new Set(P.hand)) for (const name of LIST) {
    const c = CARDS[name];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card, name }); }
    else if (!needsTarget(name)) out.push({ t: 'play', card, name });
    else for (const side of [0, 1]) { out.push({ t: 'play', card, name, target: { side, i: -1 } }); for (let i = 0; i < s.p[side].board.length; i++) out.push({ t: 'play', card, name, target: { side, i } }); }
  }
  P.board.forEach((m, from) => { if (m.ready) { out.push({ t: 'attack', from, to: -1 }); for (let to = 0; to < O.board.length; to++) out.push({ t: 'attack', from, to }); } });
  return out;
}

function hit(s, side, i, n, ev) {
  if (i < 0) { s.p[side].life -= n; emit(ev, { t: 'hit', side, i, n }); return; }
  const m = s.p[side].board[i]; m.hp -= n;
  emit(ev, { t: 'hit', side, i, n, uid: m.uid });
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const P = s.p[side], B = P.board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) {
      const m = B[i];
      if (!m.up) { if (m.real === m.name) P.revHonest++; else P.revLie++; }
      emit(ev, { t: 'die', side, i, uid: m.uid, real: m.real, name: m.name, up: m.up });
      P.discard.push(m.real); B.splice(i, 1);
    }
  }
}
// a claim that stands: the card works as the named card
function resolve(s, pd, up, ev) {
  const P = s.p[pd.side], c = CARDS[pd.name];
  if (c.kind === 'Unit') {
    const m = { uid: s.uid++, name: pd.name, real: pd.card, up, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
    P.board.push(m); emit(ev, { t: 'summon', side: pd.side, uid: m.uid, up });
    return;
  }
  if (c.dmg) { hit(s, pd.target.side, pd.target.i, c.dmg, ev); sweep(s, ev); }
  if (c.draw) for (let k = 0; k < c.draw; k++) draw(s, pd.side, ev);
  if (!up) { if (pd.card === pd.name) P.revHonest++; else P.revLie++; }
  P.discard.push(pd.card);
  emit(ev, { t: 'reveal', side: pd.side, real: pd.card, name: pd.name });
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (s.pending) {
    const pd = s.pending, claimer = s.p[pd.side], ch = 1 - pd.side;
    s.pending = null; s.toMove = s.turn; s.p[ch].faced++;
    if (a.t === 'pass') { emit(ev, { t: 'pass', side: ch }); resolve(s, pd, false, ev); }
    else if (a.t === 'challenge') {
      s.p[ch].challenges++;
      const honest = pd.card === pd.name;
      emit(ev, { t: 'challenge', side: ch, honest, real: pd.card, name: pd.name });
      if (honest) { claimer.revHonest++; s.p[ch].life -= PENALTY; emit(ev, { t: 'penalty', side: ch, n: PENALTY }); if (!checkWin(s, ev)) resolve(s, pd, true, ev); }
      else { claimer.revLie++; claimer.life -= PENALTY; emit(ev, { t: 'penalty', side: pd.side, n: PENALTY }); claimer.discard.push(pd.card); }
    } else throw new Error('a claim is pending');
    checkWin(s, ev);
    return;
  }
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'end') {
    if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.cap = true; emit(ev, { t: 'end', winner: 'draw' }); return; }
    s.turn = 1 - s.turn; startTurn(s, ev); return;
  }
  if (a.t === 'coin') {
    if (!P.coin) throw new Error('no coin');
    P.coin = false; P.mana += 1; emit(ev, { t: 'coin', side: me }); return;
  }
  if (a.t === 'play') {
    const c = CARDS[a.name], k = P.hand.indexOf(a.card);
    if (!c || k < 0 || c.cost > P.mana) throw new Error('illegal play');
    if (c.kind === 'Unit' && P.board.length >= BOARD) throw new Error('board full');
    if (needsTarget(a.name) && (!a.target || a.target.i >= s.p[a.target.side].board.length)) throw new Error('bad target');
    P.mana -= c.cost; P.hand.splice(k, 1);
    s.pending = { side: me, card: a.card, name: a.name, target: needsTarget(a.name) ? { side: a.target.side, i: a.target.i, uid: a.target.i >= 0 ? s.p[a.target.side].board[a.target.i].uid : null } : null };
    s.toMove = 1 - me;
    emit(ev, { t: 'claim', side: me, name: a.name, target: s.pending.target });
    return;
  }
  if (a.t === 'attack') {
    const m = P.board[a.from];
    if (!m || !m.ready || a.to >= O.board.length) throw new Error('illegal attack');
    m.ready = false;
    emit(ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null });
    if (a.to < 0) hit(s, 1 - me, -1, m.atk, ev);
    else { const d = O.board[a.to], da = d.atk; hit(s, 1 - me, a.to, m.atk, ev); hit(s, me, a.from, da, ev); }
    sweep(s, ev); checkWin(s, ev); return;
  }
  throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

// What `viewer` knows of `side`'s cards: every copy not in its discard pile or face-up on its board
// could be in its hand, its deck, under a face-down unit, or the claim on the table.
export function unseenPool(s, side) {
  const P = s.p[side], pool = deckList();
  const drop = (id) => { const k = pool.indexOf(id); if (k >= 0) pool.splice(k, 1); };
  for (const id of P.discard) drop(id);
  for (const m of P.board) if (m.up) drop(m.real);
  return pool;
}
