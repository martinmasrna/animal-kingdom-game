// 02 Attack and block: a life duel where the defender chooses the blocks, attackers stay
// exhausted through the opponent's turn and damage on surviving units heals at end of turn.
// One API for the page, the bots and the sim: legalActions(s) for the player to act (s.toAct),
// act(s, a, ev) returns the next state (the input is never changed).

export const LIFE = 20, MAX_MANA = 10, BOARD = 6, TURN_LIMIT = 120;

export const CARDS = {
  STR: { id: 'STR', name: 'Striker', kind: 'unit', cost: 1, atk: 2, hp: 1 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2 },
  WAL: { id: 'WAL', name: 'Wall', kind: 'unit', cost: 2, atk: 0, hp: 5 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 3 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 4 },
  BIG: { id: 'BIG', name: 'Big', kind: 'unit', cost: 5, atk: 5, hp: 5 },
  HUG: { id: 'HUG', name: 'Huge', kind: 'unit', cost: 6, atk: 6, hp: 6 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'hit', cost: 1, dmg: 2 },
  H4: { id: 'H4', name: 'Hit 4', kind: 'hit', cost: 3, dmg: 4 },
  D2: { id: 'D2', name: 'Draw 2', kind: 'draw', cost: 2, n: 2 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0 },
};
export const DECK = { STR: 3, RAI: 3, WAL: 3, LIN: 3, HEA: 3, BIG: 3, HUG: 3, H2: 3, H4: 3, D2: 3 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { life: LIFE, mana: 0, maxMana: 0, fatigue: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, attackers: s.attackers.slice(), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(u => ({ ...u })) })) };
}
function emit(s, ev, e) { if (ev) { e.turnNo = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  p.fatigue++; p.life -= p.fatigue; emit(s, ev, { t: 'fatigue', side, n: p.fatigue });
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, uid: 1, turnNo: 0, turn: 0, toAct: 0, phase: 'main', attacked: false, attackers: [], first: 0, winner: null, capped: false, p: [newPlayer(), newPlayer()] };
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
  const a = s.p[0].life <= 0, b = s.p[1].life <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++; s.phase = 'main'; s.toAct = side; s.attacked = false; s.attackers = [];
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const u of p.board) { u.ex = false; u.fresh = false; }
  draw(s, side, ev);
  checkWin(s, ev);
}

export const unitAt = (P, uid) => P.board.find(u => u.uid === uid);
export const canAttackWith = (u) => !u.ex && !u.fresh;
export const canBlockWith = (u) => !u.ex;
export const left = (u) => u.hp - u.dmg; // health left this turn

function subsets(arr) { const out = []; for (let m = 1; m < (1 << arr.length); m++) { const x = []; for (let k = 0; k < arr.length; k++) if (m & (1 << k)) x.push(arr[k]); out.push(x); } return out; }
// every assignment of at most one blocker to each attacker (each blocker blocks at most one)
export function blockAssignments(blockers, attackers) {
  const out = [];
  const rec = (i, used, pairs) => {
    if (i === blockers.length) { out.push(pairs.slice()); return; }
    rec(i + 1, used, pairs);
    for (const a of attackers) if (!used.has(a)) { used.add(a); pairs.push([blockers[i], a]); rec(i + 1, used, pairs); pairs.pop(); used.delete(a); }
  };
  rec(0, new Set(), []);
  return out;
}

// Actions: { t: 'play', card, tgt } (tgt: an enemy unit's uid, for Hit cards)
//          { t: 'attack', units: [uid...] }   once a turn, from the main phase
//          { t: 'block', pairs: [[blockerUid, attackerUid]...] }   the defender, right after an attack
//          { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  if (s.phase === 'block') {
    const bl = P.board.filter(canBlockWith).map(u => u.uid);
    return blockAssignments(bl, s.attackers).map(pairs => ({ t: 'block', pairs }));
  }
  const out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'hit') { for (const u of O.board) out.push({ t: 'play', card: id, tgt: u.uid }); }
    else out.push({ t: 'play', card: id });
  }
  if (!s.attacked) { const el = P.board.filter(canAttackWith).map(u => u.uid); for (const x of subsets(el)) out.push({ t: 'attack', units: x }); }
  out.push({ t: 'end' });
  return out;
}

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].dmg >= B[i].hp) { emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}
function hurt(s, side, u, n, ev) { if (n <= 0) return; u.dmg += n; emit(s, ev, { t: 'hit', side, uid: u.uid, n }); }

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    if (s.phase !== 'main') throw new Error('not now');
    const c = CARDS[a.card];
    if (!c || !P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (c.kind === 'unit' && P.board.length >= BOARD) throw new Error('board full');
    let tgt = null;
    if (c.kind === 'hit') { tgt = unitAt(O, a.tgt); if (!tgt) throw new Error('bad target'); }
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, tgt: a.tgt });
    if (c.kind === 'unit') { const u = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, dmg: 0, fresh: true, ex: false }; P.board.push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid }); }
    else if (c.kind === 'hit') { hurt(s, 1 - me, tgt, c.dmg, ev); sweep(s, ev); }
    else if (c.kind === 'draw') { for (let i = 0; i < c.n; i++) draw(s, me, ev); }
    else P.mana += 1;
  } else if (a.t === 'attack') {
    if (s.phase !== 'main' || s.attacked) throw new Error('no attack now');
    const units = a.units || [];
    if (!units.length || new Set(units).size !== units.length) throw new Error('bad attack');
    for (const id of units) { const u = unitAt(P, id); if (!u || !canAttackWith(u)) throw new Error('cannot attack with ' + id); }
    s.attacked = true; s.attackers = units.slice();
    for (const id of units) unitAt(P, id).ex = true;
    emit(s, ev, { t: 'attack', side: me, units: units.slice() });
    s.phase = 'block'; s.toAct = 1 - me;
  } else if (a.t === 'block') {
    if (s.phase !== 'block') throw new Error('no block now');
    const att = s.turn, A = s.p[att], D = P; // the defender is acting
    const pairs = a.pairs || [], usedB = new Set(), usedA = new Set();
    for (const [b, x] of pairs) {
      const bu = unitAt(D, b);
      if (!bu || !canBlockWith(bu) || usedB.has(b) || usedA.has(x) || !s.attackers.includes(x)) throw new Error('bad block');
      usedB.add(b); usedA.add(x);
    }
    emit(s, ev, { t: 'block', side: me, pairs: pairs.map(p => p.slice()) });
    const blockedBy = new Map(pairs.map(([b, x]) => [x, b]));
    let face = 0;
    for (const x of s.attackers) {
      const au = unitAt(A, x); if (!au) continue;
      const b = blockedBy.get(x);
      if (b === undefined) { face += au.atk; emit(s, ev, { t: 'face', side: att, uid: x, n: au.atk }); continue; }
      const bu = unitAt(D, b);
      const da = au.atk, db = bu.atk;
      hurt(s, me, bu, da, ev); hurt(s, att, au, db, ev);
    }
    if (face) { D.life -= face; emit(s, ev, { t: 'life', side: me, n: face, life: D.life }); }
    sweep(s, ev);
    s.phase = 'main'; s.toAct = att; s.attackers = [];
  } else if (a.t === 'end') {
    if (s.phase !== 'main') throw new Error('cannot end now');
    for (const side of [0, 1]) for (const u of s.p[side].board) u.dmg = 0;
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    s.turn = 1 - s.turn;
    startTurn(s, ev);
    return;
  } else throw new Error('unknown action');
  checkWin(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
export const actionKey = (a) => a.t === 'play' ? 'p' + a.card + (a.tgt !== undefined ? '@' + a.tgt : '') : a.t === 'attack' ? 'a' + a.units.slice().sort((x, y) => x - y).join(',') : a.t === 'block' ? 'b' + a.pairs.map(p => p.join('>')).sort().join(',') : 'e';
