// 05 Front and back rows. Melee units stand in the front row, Ranged units in the back row.
// Attacks must target the enemy front row; only when it is empty can they reach the back row or
// the player. A Melee attacker and its target trade damage; a Ranged attacker takes nothing back.
// Pure from the outside: act() and endTurn() clone the state.

export const LIFE = 20, MAX_MANA = 10, ROW = 3, TURN_CAP = 120;

export const CARDS = {
  STR: { id: 'STR', name: 'Striker', kind: 'unit', ranged: false, cost: 1, atk: 2, hp: 1 },
  WAL: { id: 'WAL', name: 'Wall', kind: 'unit', ranged: false, cost: 2, atk: 1, hp: 5 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', ranged: false, cost: 2, atk: 3, hp: 2 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', ranged: false, cost: 3, atk: 3, hp: 4 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'unit', ranged: false, cost: 5, atk: 5, hp: 6 },
  SHO: { id: 'SHO', name: 'Shooter', kind: 'unit', ranged: true, cost: 2, atk: 1, hp: 2 },
  GUN: { id: 'GUN', name: 'Gunner', kind: 'unit', ranged: true, cost: 3, atk: 2, hp: 2 },
  CAN: { id: 'CAN', name: 'Cannon', kind: 'unit', ranged: true, cost: 5, atk: 4, hp: 3 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'hit', cost: 1, dmg: 2 },
  H4: { id: 'H4', name: 'Hit 4', kind: 'hit', cost: 3, dmg: 4 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0 },
};
export const DECK = { STR: 3, WAL: 3, RAI: 3, LIN: 3, HEA: 3, SHO: 3, GUN: 3, CAN: 3, H2: 3, H4: 3 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { life: LIFE, mana: 0, maxMana: 0, fatigue: 0, hand: [], deck: deckList(), front: [], back: [] }; }
const cu = (u) => ({ uid: u.uid, card: u.card, atk: u.atk, hp: u.hp, max: u.max, ready: u.ready, ranged: u.ranged });
export function clone(s) {
  return { seed: s.seed, turnNo: s.turnNo, turn: s.turn, toAct: s.toAct, first: s.first, winner: s.winner, capped: s.capped, uid: s.uid,
    p: s.p.map(p => ({ life: p.life, mana: p.mana, maxMana: p.maxMana, fatigue: p.fatigue, hand: p.hand.slice(), deck: p.deck.slice(), front: p.front.map(cu), back: p.back.map(cu) })) };
}
function emit(s, ev, e) { if (ev) { e.turnNo = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  p.fatigue++; p.life -= p.fatigue; emit(s, ev, { t: 'fatigue', side, n: p.fatigue, life: p.life });
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toAct: 0, first: 0, winner: null, capped: false, uid: 1, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.toAct = s.first;
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
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const u of p.front) u.ready = true;
  for (const u of p.back) u.ready = true;
  draw(s, side, ev);
  checkWin(s, ev);
}

// where a unit stands: { row, i } in its owner's rows
export function find(P, uid) {
  let i = P.front.findIndex(u => u.uid === uid); if (i >= 0) return { row: 'front', i, u: P.front[i] };
  i = P.back.findIndex(u => u.uid === uid); if (i >= 0) return { row: 'back', i, u: P.back[i] };
  return null;
}
// what an attack may hit: the enemy front row; when it is empty, the back row and the player (0)
export function attackTargets(O) { return O.front.length ? O.front.map(u => u.uid) : O.back.map(u => u.uid).concat([0]); }
export const canPlace = (P, id) => (CARDS[id].ranged ? P.back : P.front).length < ROW;

// Actions: { t: 'play', card, tgt } (tgt: an enemy unit's uid, for Hit cards)
//          { t: 'attack', from, to } (from: own unit uid; to: enemy unit uid, or 0 for the player)
//          { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  const seen = new Set();
  for (const id of P.hand) {
    if (seen.has(id)) continue; seen.add(id);
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'unit') { if (canPlace(P, id)) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'coin') out.push({ t: 'play', card: id });
    else for (const u of O.front.concat(O.back)) out.push({ t: 'play', card: id, tgt: u.uid });
  }
  const tg = attackTargets(O);
  for (const u of P.front.concat(P.back)) if (u.ready) for (const to of tg) out.push({ t: 'attack', from: u.uid, to });
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'play' ? 'p' + a.card + (a.tgt ? ':' + a.tgt : '') : a.t === 'attack' ? 'a' + a.from + '>' + a.to : 'e';

function sweep(s, ev) {
  for (const side of [0, 1]) for (const row of ['front', 'back']) {
    const R = s.p[side][row];
    for (let i = R.length - 1; i >= 0; i--) if (R[i].hp <= 0) { emit(s, ev, { t: 'die', side, uid: R[i].uid, card: R[i].card }); R.splice(i, 1); }
  }
}
function hit(s, side, u, n, ev) { u.hp -= n; emit(s, ev, { t: 'hit', side, uid: u.uid, n, hp: u.hp }); }

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (a.t === 'end') return mEndTurn(s, ev);
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (c.kind === 'unit' && !canPlace(P, a.card)) throw new Error('row full');
    let tu = null;
    if (c.kind === 'hit') { const f = find(O, a.tgt); if (!f) throw new Error('bad target'); tu = f.u; }
    P.mana -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, tgt: a.tgt, mana: P.mana });
    if (c.kind === 'unit') {
      const u = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false, ranged: c.ranged };
      (c.ranged ? P.back : P.front).push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid, row: c.ranged ? 'back' : 'front' });
    } else if (c.kind === 'coin') { P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    else { hit(s, 1 - me, tu, c.dmg, ev); sweep(s, ev); }
  } else if (a.t === 'attack') {
    const f = find(P, a.from);
    if (!f || !f.u.ready) throw new Error('illegal attack');
    const tg = attackTargets(O);
    if (!tg.includes(a.to)) throw new Error('bad attack target');
    const u = f.u; u.ready = false;
    emit(s, ev, { t: 'attack', side: me, uid: u.uid, to: a.to });
    if (a.to === 0) { O.life -= u.atk; emit(s, ev, { t: 'face', side: 1 - me, n: u.atk, life: O.life }); }
    else {
      const d = find(O, a.to).u, back = d.atk;
      hit(s, 1 - me, d, u.atk, ev);
      if (!u.ranged && back > 0) hit(s, me, u, back, ev);
      sweep(s, ev);
    }
  } else throw new Error('unknown action');
  checkWin(s, ev);
}
function mEndTurn(s, ev) {
  emit(s, ev, { t: 'endturn', side: s.turn });
  if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toAct = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
