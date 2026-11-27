// Hero HS: Vanilla HS's rules (mana 1 to 10, draw 1 a turn, opening hands 3 and 4 plus the
// Coin, 7 minions a side, attack from the turn after, fatigue) with energy instead of health
// (start 25, lose at 0, win at 50), a 30-card shared pool and three heroes. See RULES.md.
// Pure from the outside: transitions clone the state.

export const START = 25, WIN = 50, MAX_MANA = 10, BOARD = 7, TURN_LIMIT = 100, DECK_SIZE = 20, COPIES = 2;

const M = (id, cost, atk, hp, x = {}) => ({ id, kind: 'Minion', cost, atk, hp, ...x });
const S = (id, cost, x) => ({ id, kind: 'Spell', cost, ...x });
// The pool, in RULES.md's order.
export const POOL = [
  M('m1a', 1, 2, 1), M('m1b', 1, 1, 2), M('m2a', 2, 3, 2), M('m2b', 2, 2, 3), M('m3', 3, 3, 4), M('m4', 4, 4, 5), M('m6', 6, 6, 7), M('m7', 7, 7, 7),
  M('t3', 3, 2, 4, { taunt: 1 }), M('t4', 4, 3, 5, { taunt: 1 }), M('t6', 6, 5, 6, { taunt: 1 }),
  M('r3', 3, 3, 1, { rush: 1 }),
  M('d2a', 2, 1, 1, { bc: { draw: 1 } }), M('d2b', 2, 2, 1, { dies: { draw: 1 } }), M('d5', 5, 4, 4, { bc: { draw: 1 } }),
  M('h1', 1, 1, 1, { bc: { dmg: 1 } }), M('h4', 4, 2, 4, { bc: { dmg: 2 } }),
  M('g3', 3, 3, 3, { bc: { gain: 3 } }), M('e3', 3, 2, 3, { eot: { gain: 1 } }), M('g2', 2, 1, 3, { sot: { atk: 1 } }),
  S('s1', 1, { dmg: 2 }), S('s2', 2, { dmg: 3 }), S('s4', 4, { dmg: 6 }),
  S('a2', 2, { area: 1 }), S('a4', 4, { area: 2 }), S('a7', 7, { area: 4 }),
  S('c3', 3, { draw: 2 }), S('k5', 5, { destroy: 1 }),
  S('b2', 2, { buff: 2 }), S('j3', 3, { gain: 5 }),
];
export const CARDS = { COIN: { id: 'COIN', kind: 'Coin', cost: 0 } };
for (const c of POOL) CARDS[c.id] = c;
// Hero cards; the Mage's becomes HM8 while its owner's deck is empty.
CARDS.HP = M('HP', 3, 3, 3, { bc: { upFire: 1 }, hero: 'P' });
CARDS.HA = M('HA', 6, 6, 6, { sot: { others: 1 }, hero: 'A' });
CARDS.HM = M('HM', 4, 4, 6, { hero: 'M' });
CARDS.HM8 = M('HM8', 8, 8, 8, { bc: { gain: 10 }, hero: 'M' });
// The Fireball ladder: level 0..3 (Baby, Young, Adult, Elder). An upgraded Fireball keeps its cost,
// so a Fireball is a (level, cost) pair: id F<level>_<cost>.
export const FIRE = [{ dmg: 1, cost: 1 }, { dmg: 3, cost: 2 }, { dmg: 6, cost: 4 }, { dmg: 10, cost: 6 }];
export const fireId = (l, c) => `F${l}_${c}`;
for (let l = 0; l < 4; l++) for (const f of FIRE) if (f.cost <= FIRE[l].cost) CARDS[fireId(l, f.cost)] = { id: fireId(l, f.cost), kind: 'Spell', cost: f.cost, dmg: FIRE[l].dmg, fire: l };

export const HEROES = {
  P: { id: 'P', name: 'Pyromancer', card: 'HP', power: 2, passive: 'Your hero power upgrades after every 3 uses.', active: 'Add a Fireball to your hand.' },
  A: { id: 'A', name: 'Angel Warrior', card: 'HA', power: 1, target: true, passive: 'After your minion kills an enemy minion and survives, it gains +1/+1.', active: 'Give a friendly minion +2 attack.' },
  M: { id: 'M', name: 'Mage', card: 'HM', power: 3, passive: 'Fatigue gains you energy instead of losing it.', active: 'Draw a card.' },
};
export const HERO_IDS = ['P', 'A', 'M'];

// Which targets a card needs: 'any' (minion or hero, either side), 'minion' (any minion), or none.
export function targetKind(c) {
  if (c.kind === 'Spell') return c.dmg ? 'any' : (c.destroy || c.buff) ? 'minion' : null;
  if (c.kind === 'Minion' && c.bc && c.bc.dmg) return 'any';
  return null;
}

// Found by bot search (search.mjs), a starting point; see RULES.md.
export let DEFAULT_DECKS = {
  P: ['a7', 'a7', 'd2b', 'h1', 'h1', 'h4', 'k5', 'k5', 'm2a', 'm3', 'm4', 'm4', 'r3', 's1', 's1', 's2', 's2', 's4', 's4', 't4'],
  A: ['a7', 'd2b', 'd2b', 'g2', 'h1', 'h1', 'm2b', 'm3', 'm3', 'm4', 'm4', 'm6', 'm6', 's1', 's2', 's4', 's4', 't3', 't4', 't6'],
  M: ['a7', 'a7', 'd2a', 'd2a', 'd2b', 'g3', 'g3', 'h1', 'h1', 'h4', 'h4', 'k5', 'm1a', 'm1a', 's1', 's2', 's2', 's4', 's4', 't4'],
};
export function setDefaultDecks(d) { DEFAULT_DECKS = d; }
export function deckOK(list) {
  if (list.length !== DECK_SIZE) return false;
  const n = {};
  for (const id of list) { if (!POOL.some(c => c.id === id)) return false; n[id] = (n[id] || 0) + 1; if (n[id] > COPIES) return false; }
  return true;
}

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer(hero, deck) {
  return { hero, energy: START, mana: 0, maxMana: 0, fatigue: 0, hand: [HEROES[hero].card], deck: deck.slice(), board: [], played: [], uses: 0, powered: false };
}
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }
// While the Mage's deck is empty its hero card is the 8/8, in hand and on the board.
function mageCheck(s, side, ev) {
  const p = s.p[side];
  if (p.hero !== 'M' || p.deck.length) return;
  for (let i = 0; i < p.hand.length; i++) if (p.hand[i] === 'HM') { p.hand[i] = 'HM8'; emit(s, ev, { t: 'transform', side, where: 'hand' }); }
  for (const m of p.board) if (m.card === 'HM') { m.card = 'HM8'; m.atk = 8; m.hp = 8; m.max = 8; emit(s, ev, { t: 'transform', side, where: 'board', uid: m.uid }); }
}
function gain(s, side, n, ev) { s.p[side].energy += n; emit(s, ev, { t: 'gain', side, n, energy: s.p[side].energy }); }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { const c = p.deck.shift(); p.hand.push(c); emit(s, ev, { t: 'draw', side }); mageCheck(s, side, ev); return; }
  p.fatigue++;
  if (p.hero === 'M') { gain(s, side, p.fatigue, ev); return; }
  p.energy -= p.fatigue; emit(s, ev, { t: 'fatigue', side, n: p.fatigue, energy: p.energy });
}

// heroes: [hero of side 0, hero of side 1]; decks: the 20 pool cards of each (defaults if left out).
export function newMatch({ seed, first, heroes = ['P', 'A'], decks }) {
  const ds = decks || heroes.map(h => DEFAULT_DECKS[h]);
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, p: [newPlayer(heroes[0], ds[0]), newPlayer(heroes[1], ds[1])] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  mStartTurn(s, null);
  return s;
}

// Energy at 0 or less loses, at 50 or more wins; when both sides qualify, the player whose turn it is wins.
function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const won = [0, 1].map(k => s.p[k].energy >= WIN || s.p[1 - k].energy <= 0);
  if (!won[0] && !won[1]) return false;
  s.winner = won[0] && won[1] ? s.turn : won[0] ? 0 : 1;
  emit(s, ev, { t: 'end', winner: s.winner, how: s.p[s.winner].energy >= WIN ? 'gain' : 'kill' });
  return true;
}

function buff(s, side, m, a, h, ev) { m.atk += a; m.hp += h; m.max += h; emit(s, ev, { t: 'buff', side, uid: m.uid, a, h }); }
function mStartTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  p.powered = false;
  for (const m of p.board) m.ready = true;
  for (const m of p.board.slice()) {
    const sot = CARDS[m.card].sot;
    if (!sot) continue;
    if (sot.atk) buff(s, side, m, sot.atk, 0, ev);
    if (sot.others) for (const o of p.board) if (o !== m) buff(s, side, o, sot.others, sot.others, ev);
  }
  draw(s, side, ev);
  checkWin(s, ev);
}

const hasTaunt = (B) => B.some(m => CARDS[m.card].taunt);
// Actions: { t: 'play', card, target } (target { side, i }: i a board index, -1 for the hero)
//          { t: 'attack', from, to } (own board index; enemy board index or -1 for the hero)
//          { t: 'power', target } (target only for the Angel Warrior: { side: own, i })
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Minion' && P.board.length >= BOARD) continue;
    const tk = targetKind(c);
    if (!tk) { out.push({ t: 'play', card: id }); continue; }
    for (const side of [0, 1]) {
      if (tk === 'any') out.push({ t: 'play', card: id, target: { side, i: -1 } });
      for (let i = 0; i < s.p[side].board.length; i++) out.push({ t: 'play', card: id, target: { side, i } });
    }
  }
  const H = HEROES[P.hero];
  if (!P.powered && H.power <= P.mana) {
    if (H.target) P.board.forEach((m, i) => out.push({ t: 'power', target: { side: me, i } }));
    else out.push({ t: 'power' });
  }
  const taunt = hasTaunt(O.board);
  P.board.forEach((m, from) => {
    if (!m.ready) return;
    if (!taunt) out.push({ t: 'attack', from, to: -1 });
    for (let to = 0; to < O.board.length; to++) if (!taunt || CARDS[O.board[to].card].taunt) out.push({ t: 'attack', from, to });
  });
  return out;
}

function hit(s, side, i, n, ev) {
  if (i < 0) { s.p[side].energy -= n; emit(s, ev, { t: 'hit', side, i, n, energy: s.p[side].energy }); return; }
  const m = s.p[side].board[i]; m.hp -= n;
  emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid });
}
function sweep(s, ev) {
  const dead = [];
  for (const side of [s.turn, 1 - s.turn]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, i, uid: B[i].uid, card: B[i].card }); dead.push([side, B[i]]); B.splice(i, 1); }
  }
  for (const [side, m] of dead) { const d = CARDS[m.card].dies; if (d && d.draw) for (let k = 0; k < d.draw; k++) draw(s, side, ev); }
}
function upgradeFire(p) {
  p.hand = p.hand.map(id => { const c = CARDS[id]; return c.fire !== undefined ? fireId(Math.min(3, c.fire + 1), c.cost) : id; });
}

function mAct(s, a, ev) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    const tk = targetKind(c);
    if (tk) {
      if (!a.target) throw new Error('play needs a target ' + a.card);
      const { side, i } = a.target;
      if (i >= s.p[side].board.length || (i < 0 && tk !== 'any')) throw new Error('bad target');
    }
    if (c.kind === 'Minion' && P.board.length >= BOARD) throw new Error('board full');
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1); P.played.push(a.card);
    emit(s, ev, { t: 'play', side: me, card: a.card, target: a.target, mana: P.mana, tuid: a.target && a.target.i >= 0 ? s.p[a.target.side].board[a.target.i].uid : null });
    if (c.kind === 'Minion') {
      // the when-played effect first (its target index refers to the boards before the summon), then the body
      const m = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: !!c.rush };
      if (c.bc) {
        if (c.bc.dmg) { hit(s, a.target.side, a.target.i, c.bc.dmg, ev); }
        if (c.bc.gain) gain(s, me, c.bc.gain, ev);
        if (c.bc.upFire) { upgradeFire(P); emit(s, ev, { t: 'upfire', side: me }); }
      }
      P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
      if (c.bc && c.bc.draw) for (let k = 0; k < c.bc.draw; k++) draw(s, me, ev);
      sweep(s, ev);
    } else if (c.kind === 'Coin') { P.mana = Math.min(MAX_MANA, P.mana + 1); emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    else if (c.dmg) { hit(s, a.target.side, a.target.i, c.dmg, ev); sweep(s, ev); }
    else if (c.area) { for (let i = 0; i < O.board.length; i++) hit(s, 1 - me, i, c.area, ev); sweep(s, ev); }
    else if (c.destroy) { const m = s.p[a.target.side].board[a.target.i]; m.hp = 0; emit(s, ev, { t: 'destroy', side: a.target.side, uid: m.uid }); sweep(s, ev); }
    else if (c.buff) buff(s, a.target.side, s.p[a.target.side].board[a.target.i], c.buff, c.buff, ev);
    else if (c.gain) gain(s, me, c.gain, ev);
    else if (c.draw) for (let k = 0; k < c.draw; k++) draw(s, me, ev);
  } else if (a.t === 'power') {
    const H = HEROES[P.hero];
    if (P.powered || H.power > P.mana) throw new Error('illegal power');
    P.mana -= H.power; P.powered = true;
    emit(s, ev, { t: 'power', side: me, hero: P.hero, target: a.target, tuid: a.target ? P.board[a.target.i].uid : null });
    if (P.hero === 'P') { const l = Math.min(3, Math.floor(P.uses / 3)); P.hand.push(fireId(l, FIRE[l].cost)); emit(s, ev, { t: 'fire', side: me, level: l }); }
    else if (P.hero === 'A') { const m = P.board[a.target.i]; if (!m || a.target.side !== me) throw new Error('bad power target'); buff(s, me, m, 2, 0, ev); }
    else draw(s, me, ev);
    P.uses++;
  } else {
    const m = P.board[a.from];
    if (!m || !m.ready) throw new Error('illegal attack');
    if (hasTaunt(O.board) && (a.to < 0 || !CARDS[O.board[a.to].card].taunt)) throw new Error('taunt in the way');
    m.ready = false;
    emit(s, ev, { t: 'attack', side: me, from: a.from, to: a.to, uid: m.uid, tuid: a.to >= 0 ? O.board[a.to].uid : null });
    if (a.to < 0) hit(s, 1 - me, -1, m.atk, ev);
    else {
      const d = O.board[a.to], da = d.atk;
      hit(s, 1 - me, a.to, m.atk, ev); hit(s, me, a.from, da, ev);
      // the Angel Warrior's passive, for whichever side's minion survives a fight it won
      if (P.hero === 'A' && m.hp > 0 && d.hp <= 0) buff(s, me, m, 1, 1, ev);
      if (O.hero === 'A' && d.hp > 0 && m.hp <= 0) buff(s, 1 - me, d, 1, 1, ev);
    }
    sweep(s, ev);
  }
  checkWin(s, ev);
}
function mEndTurn(s, ev) {
  if (s.winner !== null) throw new Error('endTurn: match over');
  const P = s.p[s.turn];
  for (const m of P.board) { const e = CARDS[m.card].eot; if (e && e.gain) gain(s, s.turn, e.gain, ev); }
  if (checkWin(s, ev)) return;
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  mStartTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function endTurn(s, ev) { const t = clone(s); mEndTurn(t, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
export function _endTurn(t) { mEndTurn(t, null); return t; }
