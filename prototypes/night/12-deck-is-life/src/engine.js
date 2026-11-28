// 12 Deck is life. No life total: damage banishes cards off the top of your deck, drawing
// extra costs life, Recover shuffles cards from your discard back in, and a player who must
// draw from an empty deck loses at once. Pure from the outside: act() clones the state.

export const MAX_MANA = 10, BOARD = 6, TURN_LIMIT = 120;

export const CARDS = {
  ST: { id: 'ST', name: 'Striker', kind: 'Unit', cost: 1, atk: 2, hp: 1 },
  RA: { id: 'RA', name: 'Raider', kind: 'Unit', cost: 2, atk: 3, hp: 2 },
  GU: { id: 'GU', name: 'Guard', kind: 'Unit', cost: 2, atk: 1, hp: 4 },
  LI: { id: 'LI', name: 'Line', kind: 'Unit', cost: 3, atk: 3, hp: 4 },
  HE: { id: 'HE', name: 'Heavy', kind: 'Unit', cost: 4, atk: 4, hp: 5 },
  BI: { id: 'BI', name: 'Big', kind: 'Unit', cost: 5, atk: 5, hp: 6 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'Spell', cost: 1, text: '2 damage to a unit.' },
  B3: { id: 'B3', name: 'Burn 3', kind: 'Spell', cost: 3, text: '3 damage to the opponent.' },
  D2: { id: 'D2', name: 'Draw 2', kind: 'Spell', cost: 1, text: 'Draw 2 cards.' },
  RC: { id: 'RC', name: 'Recover', kind: 'Spell', cost: 2, text: 'Shuffle up to 3 discarded cards into your deck.' },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0, text: 'Gain 1 mana this turn.' },
};
export const DECK = { ST: 3, RA: 3, GU: 3, LI: 3, HE: 3, BI: 3, H2: 3, B3: 3, D2: 3, RC: 3 };
export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList(), board: [], discard: [], banished: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), banished: p.banished.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function lose(s, side, ev) { if (s.winner === null) { s.winner = 1 - side; emit(s, ev, { t: 'end', winner: s.winner }); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { emit(s, ev, { t: 'empty', side }); lose(s, side, ev); return; }
  p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side });
}
// damage to a player: that many cards off the top of their deck, face-up, out of the game
function burn(s, side, n, ev) {
  const p = s.p[side], gone = p.deck.splice(0, n);
  p.banished.push(...gone);
  emit(s, ev, { t: 'banish', side, n: gone.length, cards: gone });
}

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

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const m of p.board) m.ready = true;
  draw(s, side, ev);
}

// Actions:
//   { t: 'play', card }                         a unit, Burn 3, Draw 2, the Coin
//   { t: 'play', card: 'H2', side, i }          Hit 2 at unit i of `side`
//   { t: 'play', card: 'RC', pick: [ids] }      Recover these cards (0 to 3) from the discard
//   { t: 'attack', from, to }                   own ready unit `from` at enemy unit `to`, or the player (-1)
//   { t: 'end' }
export function key(a) {
  if (a.t === 'end') return 'e';
  if (a.t === 'attack') return 'a' + a.from + ':' + a.to;
  if (a.card === 'H2') return 'pH2:' + a.side + ':' + a.i;
  if (a.card === 'RC') return 'pRC:' + a.pick.slice().sort().join(',');
  return 'p' + a.card;
}
function subMultiset(pick, pool) { const left = pool.slice(); for (const c of pick) { const k = left.indexOf(c); if (k < 0) return false; left.splice(k, 1); } return true; }
export function isLegal(s, a) {
  if (s.winner !== null) return false;
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (a.t === 'end') return true;
  if (a.t === 'attack') { const m = P.board[a.from]; return !!m && m.ready && (a.to === -1 || (a.to >= 0 && a.to < O.board.length)); }
  if (a.t !== 'play' || !P.hand.includes(a.card)) return false;
  const c = CARDS[a.card];
  if (c.cost > P.mana) return false;
  if (c.kind === 'Unit') return P.board.length < BOARD;
  if (a.card === 'H2') return (a.side === 0 || a.side === 1) && a.i >= 0 && a.i < s.p[a.side].board.length;
  if (a.card === 'RC') return Array.isArray(a.pick) && a.pick.length <= 3 && subMultiset(a.pick, P.discard);
  return true;
}
// Every legal action, Recover once per distinct choice of min(3, discard) cards.
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn], O = s.p[1 - s.turn], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (id === 'H2') { for (const side of [0, 1]) s.p[side].board.forEach((_, i) => out.push({ t: 'play', card: id, side, i })); }
    else if (id === 'RC') { for (const pick of picks(P.discard, Math.min(3, P.discard.length))) out.push({ t: 'play', card: id, pick }); }
    else out.push({ t: 'play', card: id });
  }
  P.board.forEach((m, from) => { if (m.ready) { out.push({ t: 'attack', from, to: -1 }); for (let to = 0; to < O.board.length; to++) out.push({ t: 'attack', from, to }); } });
  out.push({ t: 'end' });
  return out;
}
function picks(pool, n) {
  const ids = [...new Set(pool)].sort(), cnt = ids.map(id => pool.filter(x => x === id).length), out = [];
  const rec = (k, left, cur) => {
    if (left === 0) { out.push(cur.slice()); return; }
    if (k >= ids.length) return;
    for (let take = Math.min(cnt[k], left); take >= 0; take--) { for (let j = 0; j < take; j++) cur.push(ids[k]); rec(k + 1, left - take, cur); cur.length -= take; }
  };
  rec(0, n, []);
  return out;
}

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const P = s.p[side], B = P.board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, i, uid: B[i].uid, card: B[i].card }); P.discard.push(B[i].card); B.splice(i, 1); }
  }
}
function hitUnit(s, side, i, n, ev) { const m = s.p[side].board[i]; m.hp -= n; emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid }); }

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'attack') {
    const m = P.board[a.from];
    m.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null, atk: m.atk });
    if (a.to < 0) burn(s, 1 - me, m.atk, ev);
    else { const d = O.board[a.to], da = d.atk; hitUnit(s, 1 - me, a.to, m.atk, ev); hitUnit(s, me, a.from, da, ev); sweep(s, ev); }
    return;
  }
  const c = CARDS[a.card];
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
  emit(s, ev, { t: 'play', side: me, card: a.card, a });
  if (c.kind === 'Unit') {
    const m = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
    P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    return;
  }
  if (c.kind === 'Coin') { P.mana = Math.min(MAX_MANA, P.mana + 1); return; }
  if (a.card === 'H2') { hitUnit(s, a.side, a.i, 2, ev); sweep(s, ev); }
  else if (a.card === 'B3') burn(s, 1 - me, 3, ev);
  else if (a.card === 'D2') { draw(s, me, ev); if (s.winner === null) draw(s, me, ev); }
  else if (a.card === 'RC') {
    for (const id of a.pick) P.discard.splice(P.discard.indexOf(id), 1);
    P.deck.push(...a.pick); shuffleInPlace(s, P.deck);
    emit(s, ev, { t: 'recover', side: me, cards: a.pick.slice() });
  }
  P.discard.push(a.card);
}
function endTurn(s, ev) {
  emit(s, ev, { t: 'endturn', side: s.turn });
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toMove = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
