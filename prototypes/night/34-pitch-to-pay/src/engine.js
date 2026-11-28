// 34 Pitch to pay. No mana: a card is paid for by pitching other cards from hand for their
// pitch value; pitched cards go under the deck in the order pitched, unspent mana is lost at the
// end of the turn, and the hand refills to five. A unit board in the usual attack style.
// Pure from the outside: act() clones; _act() mutates (for play-outs).

export const LIFE = 30, BOARD = 6, HAND = 5, BLEED_FROM = 15, TURN_LIMIT = 120;

export const CARDS = {
  PIP: { id: 'PIP', name: 'Pip', kind: 'unit', cost: 1, atk: 1, hp: 1, pitch: 3, n: 6 },
  STR: { id: 'STR', name: 'Striker', kind: 'unit', cost: 1, atk: 2, hp: 1, pitch: 1, n: 3 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2, pitch: 1, n: 3 },
  GRD: { id: 'GRD', name: 'Guard', kind: 'unit', cost: 2, atk: 1, hp: 4, pitch: 2, n: 3 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 4, pitch: 2, n: 3 },
  HEV: { id: 'HEV', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 5, pitch: 2, n: 3 },
  BIG: { id: 'BIG', name: 'Big', kind: 'unit', cost: 6, atk: 6, hp: 7, pitch: 1, n: 3 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'spell', cost: 2, dmg: 3, pitch: 2, n: 3 },
  H5: { id: 'H5', name: 'Hit 5', kind: 'spell', cost: 4, dmg: 5, pitch: 1, n: 3 },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < c.n; i++) out.push(c.id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
// known: how many cards at the bottom of the deck are public (pitched there, not yet redrawn)
function newPlayer() { return { life: LIFE, hand: [], deck: deckList(), disc: [], board: [], pool: 0, turns: 0, known: 0 }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), disc: p.disc.slice(), board: p.board.map(u => ({ ...u })) })) };
}
function emit(s, ev, e) { if (ev) { e.n0 = s.turnNo; ev.push(e); } }

function drawOne(s, side, ev) {
  const P = s.p[side];
  if (!P.deck.length) {
    if (!P.disc.length) return false;
    P.deck = shuffleInPlace(s, P.disc); P.disc = []; P.known = 0;
    emit(s, ev, { t: 'reshuffle', side });
  }
  P.hand.push(P.deck.shift());
  if (P.deck.length < P.known) P.known = P.deck.length;
  emit(s, ev, { t: 'draw', side });
  return true;
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, toAct: 0, first: 0, winner: null, capped: false, p: [newPlayer(), newPlayer()] };
  for (const P of s.p) shuffleInPlace(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 4; i++) drawOne(s, s.first, null);
  for (let i = 0; i < 5; i++) drawOne(s, 1 - s.first, null);
  s.toAct = s.first;
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
  const P = s.p[s.toAct];
  s.turnNo++; P.turns++; P.pool = 0;
  emit(s, ev, { t: 'turn', side: s.toAct });
  for (const u of P.board) u.ready = true;
  if (P.turns >= BLEED_FROM) { const n = P.turns - BLEED_FROM + 1; P.life -= n; emit(s, ev, { t: 'bleed', side: s.toAct, n, life: P.life }); }
  checkWin(s, ev);
}

const uniq = (a) => [...new Set(a)];
// Actions: { t: 'pitch', card } | { t: 'play', card, tgt? } (tgt { side, i }, i -1 the player)
//          | { t: 'attack', from, to } (to -1 the enemy player) | { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toAct, P = s.p[me], O = s.p[1 - me], out = [];
  const ids = uniq(P.hand);
  for (const id of ids) out.push({ t: 'pitch', card: id });
  for (const id of ids) {
    const c = CARDS[id];
    if (c.cost > P.pool) continue;
    if (c.kind === 'unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else for (const side of [1 - me, me]) { out.push({ t: 'play', card: id, tgt: { side, i: -1 } }); s.p[side].board.forEach((_, i) => out.push({ t: 'play', card: id, tgt: { side, i } })); }
  }
  P.board.forEach((u, from) => { if (u.ready) { out.push({ t: 'attack', from, to: -1 }); O.board.forEach((_, to) => out.push({ t: 'attack', from, to })); } });
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'pitch' ? 'p' + a.card : a.t === 'play' ? 'y' + a.card + (a.tgt ? ':' + a.tgt.side + ':' + a.tgt.i : '') : a.t === 'attack' ? 'a' + a.from + '>' + a.to : 'e';

function hit(s, side, i, n, ev) {
  if (i < 0) { s.p[side].life -= n; emit(s, ev, { t: 'hit', side, i, n, life: s.p[side].life }); return; }
  const u = s.p[side].board[i]; u.hp -= n;
  emit(s, ev, { t: 'hit', side, i, n, hp: u.hp, uid: u.uid });
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const P = s.p[side], B = P.board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, i, uid: B[i].uid, card: B[i].card }); P.disc.push(B[i].card); B.splice(i, 1); }
  }
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'pitch') {
    const k = P.hand.indexOf(a.card);
    if (k < 0) throw new Error('pitch: not in hand ' + a.card);
    P.hand.splice(k, 1); P.pool += CARDS[a.card].pitch; P.deck.push(a.card); P.known++;
    emit(s, ev, { t: 'pitch', side: me, card: a.card, pool: P.pool });
  } else if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.pool) throw new Error('illegal play ' + a.card);
    P.pool -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, tgt: a.tgt, pool: P.pool });
    if (c.kind === 'unit') {
      if (P.board.length >= BOARD) throw new Error('board full');
      const u = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
      P.board.push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid });
    } else {
      const { side, i } = a.tgt;
      if (i >= s.p[side].board.length) throw new Error('bad target');
      hit(s, side, i, c.dmg, ev); P.disc.push(a.card); sweep(s, ev);
    }
  } else if (a.t === 'attack') {
    const u = P.board[a.from];
    if (!u || !u.ready) throw new Error('illegal attack');
    u.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: u.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null, atk: u.atk });
    if (a.to < 0) hit(s, 1 - me, -1, u.atk, ev);
    else { const d = O.board[a.to]; if (!d) throw new Error('bad attack target'); const da = d.atk; hit(s, 1 - me, a.to, u.atk, ev); hit(s, me, a.from, da, ev); }
    sweep(s, ev);
  } else if (a.t === 'end') {
    P.pool = 0;
    while (P.hand.length < HAND && drawOne(s, me, ev));
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    s.toAct = 1 - me;
    startTurn(s, ev);
    return;
  } else throw new Error('unknown action ' + a.t);
  checkWin(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
