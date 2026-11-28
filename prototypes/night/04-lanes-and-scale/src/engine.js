// 04 Lanes and scale. Four lanes, one slot per side in each. At the end of your turn each of your
// units, lane 1 to 4, hits the enemy unit opposite it or, facing an empty slot, tips a shared
// scale by its attack; five toward you wins at once. Pure from the outside: act() clones.

export const MAX_MANA = 10, LANES = 4, WIN = 5, TURN_LIMIT = 120;

export const CARDS = {
  WA: { id: 'WA', name: 'Wall', kind: 'Unit', cost: 1, atk: 0, hp: 4 },
  ST: { id: 'ST', name: 'Striker', kind: 'Unit', cost: 1, atk: 1, hp: 2 },
  RA: { id: 'RA', name: 'Raider', kind: 'Unit', cost: 2, atk: 2, hp: 2 },
  LA: { id: 'LA', name: 'Lancer', kind: 'Unit', cost: 3, atk: 3, hp: 2 },
  LI: { id: 'LI', name: 'Line', kind: 'Unit', cost: 3, atk: 2, hp: 4 },
  HE: { id: 'HE', name: 'Heavy', kind: 'Unit', cost: 4, atk: 3, hp: 5 },
  BI: { id: 'BI', name: 'Big', kind: 'Unit', cost: 5, atk: 4, hp: 6 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'Spell', cost: 1, text: '2 damage to a unit.' },
  SF: { id: 'SF', name: 'Shift', kind: 'Spell', cost: 1, text: 'Move one of your units to an empty slot on your side.' },
  SV: { id: 'SV', name: 'Shove', kind: 'Spell', cost: 2, text: 'Move the scale 1 toward you.' },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0, text: 'Gain 1 mana this turn.' },
};
export const DECK = { WA: 3, ST: 3, RA: 3, LA: 3, LI: 3, HE: 3, BI: 3, H2: 3, SF: 3, SV: 3 };
export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export const dir = (side) => side === 0 ? 1 : -1; // seat 0 wins at +5, seat 1 at -5

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList(), slots: [null, null, null, null], used: 0 }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), slots: p.slots.map(m => m && { ...m }) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function tip(s, side, n, ev, why) {
  if (s.winner !== null || !n) return;
  s.scale += dir(side) * n;
  emit(s, ev, { t: 'scale', side, n, scale: s.scale, why });
  if (s.scale >= WIN) { s.winner = 0; emit(s, ev, { t: 'end', winner: 0 }); }
  else if (s.scale <= -WIN) { s.winner = 1; emit(s, ev, { t: 'end', winner: 1 }); }
}
function draw(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { emit(s, ev, { t: 'empty', side }); tip(s, 1 - side, 1, ev, 'empty'); return; }
  p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side });
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toMove: 0, first: 0, winner: null, uid: 1, scale: 0, p: [newPlayer(), newPlayer()] };
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
  s.last = -1; // the last play's place in a canonical order, for bots that skip reorderings
  draw(s, side, ev);
}

// A canonical order of plays within a turn: nothing but legality depends on the order of plays
// (combat comes at the end), and every end-of-turn board is reachable in this order.
const RANK = { COIN: 0, SV: 1, H2: 2, SF: 3, WA: 4, ST: 5, RA: 6, LA: 7, LI: 8, HE: 9, BI: 10 };
export function order(a) { return RANK[a.card] * 100 + (a.lane ?? a.to ?? 0) * 10 + (a.side ?? a.from ?? 0); }

// Actions:
//   { t: 'play', card, lane }              a unit into an empty slot of yours
//   { t: 'play', card: 'H2', side, lane }  Hit 2 at the unit in that slot
//   { t: 'play', card: 'SF', from, to }    Shift your unit from lane `from` to empty lane `to`
//   { t: 'play', card: 'SV' } / { t: 'play', card: 'COIN' }
//   { t: 'end' }                           your combat, then the opponent's turn
export function key(a) {
  if (a.t === 'end') return 'e';
  if (a.card === 'H2') return 'pH2:' + a.side + ':' + a.lane;
  if (a.card === 'SF') return 'pSF:' + a.from + '>' + a.to;
  if (CARDS[a.card].kind === 'Unit') return 'p' + a.card + ':' + a.lane;
  return 'p' + a.card;
}
const lane = (x) => Number.isInteger(x) && x >= 0 && x < LANES;
export function isLegal(s, a) {
  if (s.winner !== null) return false;
  const P = s.p[s.turn];
  if (a.t === 'end') return true;
  if (a.t !== 'play' || !P.hand.includes(a.card)) return false;
  const c = CARDS[a.card];
  if (c.cost > P.mana) return false;
  if (c.kind === 'Unit') return lane(a.lane) && !P.slots[a.lane];
  if (a.card === 'H2') return (a.side === 0 || a.side === 1) && lane(a.lane) && !!s.p[a.side].slots[a.lane];
  if (a.card === 'SF') return lane(a.from) && lane(a.to) && !!P.slots[a.from] && !P.slots[a.to];
  return true;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { for (let l = 0; l < LANES; l++) if (!P.slots[l]) out.push({ t: 'play', card: id, lane: l }); }
    else if (id === 'H2') { for (const side of [0, 1]) for (let l = 0; l < LANES; l++) if (s.p[side].slots[l]) out.push({ t: 'play', card: id, side, lane: l }); }
    else if (id === 'SF') { for (let f = 0; f < LANES; f++) if (P.slots[f]) for (let t = 0; t < LANES; t++) if (!P.slots[t]) out.push({ t: 'play', card: id, from: f, to: t }); }
    else out.push({ t: 'play', card: id });
  }
  out.push({ t: 'end' });
  return out;
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.turn, P = s.p[me];
  if (a.t === 'end') { combat(s, ev); if (s.winner === null) endTurn(s, ev); return; }
  const c = CARDS[a.card];
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1); P.used++;
  s.last = order(a);
  emit(s, ev, { t: 'play', side: me, card: a.card, a });
  if (c.kind === 'Unit') {
    const m = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp };
    P.slots[a.lane] = m; emit(s, ev, { t: 'summon', side: me, lane: a.lane, uid: m.uid });
  } else if (c.kind === 'Coin') P.mana = Math.min(MAX_MANA, P.mana + 1);
  else if (a.card === 'H2') {
    const m = s.p[a.side].slots[a.lane]; m.hp -= 2;
    emit(s, ev, { t: 'hit', side: a.side, lane: a.lane, uid: m.uid, n: 2, hp: m.hp });
    if (m.hp <= 0) { s.p[a.side].slots[a.lane] = null; emit(s, ev, { t: 'die', side: a.side, lane: a.lane, uid: m.uid }); }
  } else if (a.card === 'SF') { P.slots[a.to] = P.slots[a.from]; P.slots[a.from] = null; emit(s, ev, { t: 'shift', side: me, from: a.from, to: a.to, uid: P.slots[a.to].uid }); }
  else if (a.card === 'SV') tip(s, me, 1, ev, 'shove');
}
// the active player's units strike, lane 1 to lane 4
function combat(s, ev) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  for (let l = 0; l < LANES && s.winner === null; l++) {
    const m = P.slots[l];
    if (!m) continue;
    const d = O.slots[l];
    if (d) {
      emit(s, ev, { t: 'strike', side: me, lane: l, uid: m.uid, tuid: d.uid, n: m.atk });
      if (!m.atk) continue;
      d.hp -= m.atk;
      emit(s, ev, { t: 'hit', side: 1 - me, lane: l, uid: d.uid, n: m.atk, hp: d.hp });
      if (d.hp <= 0) { O.slots[l] = null; emit(s, ev, { t: 'die', side: 1 - me, lane: l, uid: d.uid }); }
    } else {
      emit(s, ev, { t: 'strike', side: me, lane: l, uid: m.uid, tuid: null, n: m.atk });
      tip(s, me, m.atk, ev, 'lane');
    }
  }
}
function endTurn(s, ev) {
  emit(s, ev, { t: 'endturn', side: s.turn });
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toMove = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
