// 15 Key pieces. No life: holding Key A, Key B and Key C at the start of your turn wins; drawing
// from an empty deck loses. Keys are 0-attack pieces the opponent can attack; Guards must be
// attacked first. Mana 1 to 10, draw 1 a turn, the second player gets the Coin.
// Pure from the outside: act() clones; _act() mutates (for play-outs).

export const BOARD = 6, MAX_MANA = 10, TURN_LIMIT = 120;
export const KEYS = ['KA', 'KB', 'KC'];
export const CARDS = {
  KA: { id: 'KA', name: 'Key A', kind: 'key', cost: 2, atk: 0, hp: 3, n: 2 },
  KB: { id: 'KB', name: 'Key B', kind: 'key', cost: 3, atk: 0, hp: 4, n: 2 },
  KC: { id: 'KC', name: 'Key C', kind: 'key', cost: 4, atk: 0, hp: 5, n: 2 },
  FET: { id: 'FET', name: 'Fetch', kind: 'fetch', cost: 2, n: 2 },
  STR: { id: 'STR', name: 'Striker', kind: 'unit', cost: 1, atk: 2, hp: 1, n: 3 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2, n: 3 },
  GRD: { id: 'GRD', name: 'Guard', kind: 'unit', cost: 2, atk: 1, hp: 4, guard: true, n: 3 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 4, n: 3 },
  HEV: { id: 'HEV', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 4, n: 3 },
  WAL: { id: 'WAL', name: 'Wall', kind: 'unit', cost: 4, atk: 2, hp: 7, guard: true, n: 2 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'spell', cost: 2, dmg: 3, n: 3 },
  H5: { id: 'H5', name: 'Hit 5', kind: 'spell', cost: 4, dmg: 5, n: 2 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0, n: 0 },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < c.n; i++) out.push(c.id); return out; }
export const isPiece = (id) => CARDS[id].kind === 'unit' || CARDS[id].kind === 'key';

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(u => ({ ...u })) })) };
}
function emit(s, ev, e) { if (ev) { e.n0 = s.turnNo; ev.push(e); } }
export const keysHeld = (P) => KEYS.filter(k => P.board.some(u => u.card === k));
export const hasGuard = (P) => P.board.some(u => CARDS[u.card].guard);

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, toAct: 0, first: 0, winner: null, capped: false, why: null, p: [newPlayer(), newPlayer()] };
  for (const P of s.p) shuffleInPlace(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) s.p[s.first].hand.push(s.p[s.first].deck.shift());
  for (let i = 0; i < 4; i++) s.p[1 - s.first].hand.push(s.p[1 - s.first].deck.shift());
  s.p[1 - s.first].hand.push('COIN');
  s.toAct = s.first;
  startTurn(s, null);
  return s;
}
function win(s, side, why, ev) { s.winner = side; s.why = why; emit(s, ev, { t: 'end', winner: side, why }); }
function startTurn(s, ev) {
  const me = s.toAct, P = s.p[me];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side: me });
  if (keysHeld(P).length === 3) return win(s, me, 'keys', ev);
  P.maxMana = Math.min(MAX_MANA, P.maxMana + 1); P.mana = P.maxMana;
  for (const u of P.board) u.ready = true;
  if (!P.deck.length) return win(s, 1 - me, 'deck', ev);
  P.hand.push(P.deck.shift()); emit(s, ev, { t: 'draw', side: me });
}

// Actions: { t: 'play', card, tgt?, key? } (tgt { side, uid } for a Hit; key for a Fetch)
//          | { t: 'attack', from: uid, to: uid } | { t: 'end' }
export function attackTargets(s, side) {
  const O = s.p[1 - side];
  return hasGuard(O) ? O.board.filter(u => CARDS[u.card].guard) : O.board;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toAct, P = s.p[me], out = [];
  for (const id of [...new Set(P.hand)]) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (isPiece(id)) { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'spell') { for (const side of [1 - me, me]) for (const u of s.p[side].board) out.push({ t: 'play', card: id, tgt: { side, uid: u.uid } }); }
    else if (c.kind === 'fetch') { for (const k of KEYS) if (P.deck.includes(k)) out.push({ t: 'play', card: id, key: k }); }
    else out.push({ t: 'play', card: id });
  }
  const T = attackTargets(s, me);
  for (const u of P.board) if (u.ready && CARDS[u.card].kind === 'unit') for (const v of T) out.push({ t: 'attack', from: u.uid, to: v.uid });
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'play' ? 'y' + a.card + (a.tgt ? ':' + a.tgt.side + ':' + a.tgt.uid : '') + (a.key ? '>' + a.key : '') : a.t === 'attack' ? 'a' + a.from + '>' + a.to : 'e';

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (isPiece(a.card) && P.board.length >= BOARD) throw new Error('board full');
    P.mana -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, tgt: a.tgt, key: a.key, mana: P.mana });
    if (isPiece(a.card)) {
      const u = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
      P.board.push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid, card: a.card });
    } else if (c.kind === 'spell') {
      const B = s.p[a.tgt.side].board, u = B.find(v => v.uid === a.tgt.uid);
      if (!u) throw new Error('bad target');
      u.hp -= c.dmg; emit(s, ev, { t: 'hit', side: a.tgt.side, uid: u.uid, n: c.dmg, hp: u.hp });
      sweep(s, ev);
    } else if (c.kind === 'fetch') {
      const j = P.deck.indexOf(a.key); if (j < 0 || !KEYS.includes(a.key)) throw new Error('fetch: not in deck');
      P.deck.splice(j, 1); P.hand.push(a.key); emit(s, ev, { t: 'fetch', side: me, key: a.key });
    } else if (c.kind === 'coin') { P.mana = Math.min(MAX_MANA, P.mana + 1); emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
  } else if (a.t === 'attack') {
    const u = P.board.find(v => v.uid === a.from), d = O.board.find(v => v.uid === a.to);
    if (!u || !u.ready || CARDS[u.card].kind !== 'unit') throw new Error('illegal attack');
    if (!d || !attackTargets(s, me).includes(d)) throw new Error('illegal attack target');
    u.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: u.uid, to: d.uid, atk: u.atk });
    d.hp -= u.atk; emit(s, ev, { t: 'hit', side: 1 - me, uid: d.uid, n: u.atk, hp: d.hp });
    if (d.atk > 0) { u.hp -= d.atk; emit(s, ev, { t: 'hit', side: me, uid: u.uid, n: d.atk, hp: u.hp }); }
    sweep(s, ev);
  } else if (a.t === 'end') {
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    s.toAct = 1 - me;
    startTurn(s, ev);
  } else throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
