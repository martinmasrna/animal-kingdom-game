// 14 Response duel. No board: spells hit the opponent, and mana left at the end of your turn is
// stored through the opponent's next turn, where it pays for one Response to each Spell they
// cast. Pure from the outside: act() clones the state.

export const LIFE = 20, MAX_MANA = 10, HAND_MAX = 10, TURN_LIMIT = 120;

export const CARDS = {
  BO: { id: 'BO', name: 'Bolt', kind: 'Spell', cost: 1, dmg: 2, text: '2 damage to the opponent.', copies: 5 },
  BL: { id: 'BL', name: 'Blast', kind: 'Spell', cost: 3, dmg: 5, text: '5 damage to the opponent.', copies: 3 },
  BA: { id: 'BA', name: 'Barrage', kind: 'Spell', cost: 5, dmg: 8, text: '8 damage to the opponent.', copies: 2 },
  DR: { id: 'DR', name: 'Drain', kind: 'Spell', cost: 2, dmg: 2, heal: 2, text: '2 damage to the opponent; you gain 2 life.', copies: 3 },
  ST: { id: 'ST', name: 'Study', kind: 'Spell', cost: 2, dmg: 0, text: 'Draw 2 cards.', copies: 3 },
  SG: { id: 'SG', name: 'Siege', kind: 'Spell', cost: 4, dmg: 6, text: 'At the start of each of your next 3 turns, 2 damage to the opponent.', copies: 2 },
  CA: { id: 'CA', name: 'Cancel', kind: 'Response', cost: 3, text: 'Cancel the spell.', copies: 4 },
  WA: { id: 'WA', name: 'Ward', kind: 'Response', cost: 1, text: 'The spell deals 3 less damage (a Siege 1 less each time).', copies: 5 },
  MI: { id: 'MI', name: 'Mirror', kind: 'Response', cost: 2, text: 'The spell’s damage hits its caster instead (5 or less; not Siege).', copies: 3 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0, text: 'Gain 1 mana this turn.' },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < (c.copies || 0); i++) out.push(c.id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { life: LIFE, mana: 0, maxMana: 0, stored: 0, fatigue: 0, hand: [], deck: deckList(), discard: [], sieges: [] }; }
export function clone(s) {
  return { ...s, pending: s.pending && { ...s.pending }, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), sieges: p.sieges.map(g => ({ ...g })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].life <= 0, b = s.p[1].life <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}
function hurt(s, side, n, ev, why) { if (n <= 0) return; s.p[side].life -= n; emit(s, ev, { t: 'dmg', side, n, life: s.p[side].life, why }); }
function heal(s, side, n, ev) { const p = s.p[side], h = Math.min(n, LIFE - p.life); if (h > 0) { p.life += h; emit(s, ev, { t: 'heal', side, n: h, life: p.life }); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { p.fatigue++; emit(s, ev, { t: 'fatigue', side, n: p.fatigue }); hurt(s, side, p.fatigue, ev, 'fatigue'); return; }
  const c = p.deck.shift();
  if (p.hand.length >= HAND_MAX) { p.discard.push(c); emit(s, ev, { t: 'burnt', side, card: c }); return; }
  p.hand.push(c); emit(s, ev, { t: 'draw', side });
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toMove: 0, first: 0, winner: null, pending: null, p: [newPlayer(), newPlayer()] };
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
  for (const g of p.sieges) { hurt(s, 1 - side, g.dmg, ev, 'siege'); g.ticks--; }
  p.sieges = p.sieges.filter(g => g.ticks > 0);
  if (checkWin(s, ev)) return;
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana; p.stored = 0;
  draw(s, side, ev);
  checkWin(s, ev);
}

// which Responses can answer which Spell
export function answers(resp, spell) {
  if (resp === 'CA' || resp === 'WA') return true;
  if (resp === 'MI') return CARDS[spell].dmg > 0 && CARDS[spell].dmg <= 5 && spell !== 'SG';
  return false;
}
// Actions: { t: 'cast', card } · { t: 'end' } in your turn;
//          { t: 'respond', card } · { t: 'allow' } when a Spell of the opponent waits for you.
export function key(a) { return a.t === 'cast' ? 'c' + a.card : a.t === 'respond' ? 'r' + a.card : a.t === 'end' ? 'e' : 'a'; }
export function isLegal(s, a) {
  if (s.winner !== null) return false;
  const P = s.p[s.toMove];
  if (s.pending) {
    if (a.t === 'allow') return true;
    return a.t === 'respond' && CARDS[a.card] && CARDS[a.card].kind === 'Response' && P.hand.includes(a.card) && CARDS[a.card].cost <= P.stored && answers(a.card, s.pending.card);
  }
  if (a.t === 'end') return true;
  return a.t === 'cast' && P.hand.includes(a.card) && CARDS[a.card].kind !== 'Response' && CARDS[a.card].cost <= P.mana;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.toMove], out = [];
  if (s.pending) {
    for (const id of new Set(P.hand)) if (isLegal(s, { t: 'respond', card: id })) out.push({ t: 'respond', card: id });
    out.push({ t: 'allow' });
    return out;
  }
  for (const id of new Set(P.hand)) if (isLegal(s, { t: 'cast', card: id })) out.push({ t: 'cast', card: id });
  out.push({ t: 'end' });
  return out;
}
// the opponent gets a say whenever it has stored mana and cards in hand
const canAnswer = (O) => O.stored >= 1 && O.hand.length > 0;

function resolve(s, resp, ev) {
  const me = s.turn, P = s.p[me], id = s.pending.card, c = CARDS[id];
  s.pending = null; s.toMove = me;
  if (resp === 'CA') { emit(s, ev, { t: 'cancelled', side: me, card: id }); P.discard.push(id); return; }
  const less = resp === 'WA' ? 3 : 0, target = resp === 'MI' ? me : 1 - me;
  if (id === 'ST') { draw(s, me, ev); draw(s, me, ev); }
  else if (id === 'SG') { P.sieges.push({ ticks: 3, dmg: resp === 'WA' ? 1 : 2 }); emit(s, ev, { t: 'siege', side: me, dmg: resp === 'WA' ? 1 : 2 }); }
  else { hurt(s, target, Math.max(0, c.dmg - less), ev, id); if (c.heal) heal(s, me, c.heal, ev); }
  P.discard.push(id);
  checkWin(s, ev);
}
function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.toMove, P = s.p[me];
  if (s.pending) {
    if (a.t === 'respond') {
      P.stored -= CARDS[a.card].cost; P.hand.splice(P.hand.indexOf(a.card), 1); P.discard.push(a.card);
      emit(s, ev, { t: 'respond', side: me, card: a.card, to: s.pending.card });
      resolve(s, a.card, ev);
    } else { emit(s, ev, { t: 'allow', side: me }); resolve(s, null, ev); }
    return;
  }
  if (a.t === 'end') { endTurn(s, ev); return; }
  const c = CARDS[a.card];
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
  emit(s, ev, { t: 'cast', side: me, card: a.card });
  if (c.kind === 'Coin') { P.mana = Math.min(MAX_MANA, P.mana + 1); return; }
  s.pending = { card: a.card };
  if (canAnswer(s.p[1 - me])) s.toMove = 1 - me; else resolve(s, null, ev);
}
function endTurn(s, ev) {
  const P = s.p[s.turn];
  P.stored = P.mana; P.mana = 0;
  emit(s, ev, { t: 'endturn', side: s.turn, stored: P.stored });
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toMove = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
