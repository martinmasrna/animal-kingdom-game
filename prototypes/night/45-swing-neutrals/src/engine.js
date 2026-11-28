// 45 Swing neutrals. No units of your own: three shared Neutrals on loyalty tracks from -3 to +3
// (positive leans to seat 0, negative to seat 1). Influence cards pull them; at the start of your
// turn every Neutral still leaning your way deals its attack to the opponent. Life 15.
// (The spec had the hit at the end of your own turn; moved to the start of your next turn, the one
// rule change the night run allows: see report.json.)
// Pure from the outside: act() clones; _act() mutates (for play-outs).

export const LIFE = 15, MAX_MANA = 8, TURN_LIMIT = 120, SHIELD = 4;
export const NEUTRALS = [2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 5, 5];
export const CARDS = {
  S1: { id: 'S1', name: 'Sway 1', kind: 'sway', cost: 1, pull: 1, n: 5 },
  S2: { id: 'S2', name: 'Sway 2', kind: 'sway', cost: 2, pull: 2, n: 4 },
  S3: { id: 'S3', name: 'Sway 3', kind: 'sway', cost: 4, pull: 3, n: 3 },
  SPR: { id: 'SPR', name: 'Spread', kind: 'spread', cost: 3, n: 3 },
  EXI: { id: 'EXI', name: 'Exile', kind: 'exile', cost: 3, n: 3 },
  SHD: { id: 'SHD', name: 'Shield', kind: 'shield', cost: 2, n: 3 },
  RAL: { id: 'RAL', name: 'Rally', kind: 'rally', cost: 2, n: 2 },
  DR2: { id: 'DR2', name: 'Draw 2', kind: 'draw', cost: 2, n: 3 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0, n: 0 },
};
export function deckList() { const out = []; for (const c of Object.values(CARDS)) for (let i = 0; i < c.n; i++) out.push(c.id); return out; }
export const dir = (side) => side === 0 ? 1 : -1;
// how far a Neutral leans toward `side` (-3..3)
export const toward = (n, side) => n.loy * dir(side);

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { life: LIFE, mana: 0, maxMana: 0, fatigue: 0, shield: 0, hand: [], deck: deckList() }; }
export function clone(s) {
  return { ...s, ndeck: s.ndeck.slice(), slots: s.slots.map(n => ({ ...n })), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.n0 = s.turnNo; ev.push(e); } }
function drawOne(s, side, ev) {
  const P = s.p[side];
  if (P.deck.length) { P.hand.push(P.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  P.fatigue++; damage(s, side, P.fatigue, ev, 'fatigue');
}
function damage(s, side, n, ev, src, slot) {
  const P = s.p[side], blocked = Math.min(P.shield, n);
  P.shield -= blocked; P.life -= n - blocked;
  emit(s, ev, { t: 'damage', side, n: n - blocked, blocked, src, slot, life: P.life });
}
const newNeutral = (atk) => ({ uid: UID++, atk, loy: 0 });

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, toAct: 0, first: 0, winner: null, capped: false, ndeck: NEUTRALS.slice(), slots: [], p: [newPlayer(), newPlayer()] };
  shuffleInPlace(s, s.ndeck);
  for (let i = 0; i < 3; i++) s.slots.push(newNeutral(s.ndeck.shift()));
  for (const P of s.p) shuffleInPlace(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) drawOne(s, s.first, null);
  for (let i = 0; i < 4; i++) drawOne(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
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
  const me = s.toAct, P = s.p[me];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side: me });
  for (let j = 0; j < 3; j++) if (toward(s.slots[j], me) >= 1) damage(s, 1 - me, s.slots[j].atk, ev, 'neutral', j);
  if (checkWin(s, ev)) return;
  P.maxMana = Math.min(MAX_MANA, P.maxMana + 1); P.mana = P.maxMana;
  drawOne(s, s.toAct, ev);
  checkWin(s, ev);
}

// Actions: { t: 'play', card, slot? } (slot 0..2 for Sway, Exile, Rally) | { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toAct, P = s.p[me], out = [];
  for (const id of [...new Set(P.hand)]) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'sway') for (let k = 0; k < 3; k++) out.push({ t: 'play', card: id, slot: k });
    else if (c.kind === 'exile') { if (s.ndeck.length) for (let k = 0; k < 3; k++) out.push({ t: 'play', card: id, slot: k }); }
    else if (c.kind === 'rally') { for (let k = 0; k < 3; k++) if (toward(s.slots[k], me) >= 1) out.push({ t: 'play', card: id, slot: k }); }
    else out.push({ t: 'play', card: id });
  }
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'play' ? 'y' + a.card + (a.slot !== undefined ? ':' + a.slot : '') : 'e';
const clamp = (x) => Math.max(-3, Math.min(3, x));

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me];
  if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (c.kind === 'exile' && !s.ndeck.length) throw new Error('exile: neutral deck empty');
    if (c.kind === 'rally' && !(toward(s.slots[a.slot], me) >= 1)) throw new Error('rally: not loyal');
    if ((c.kind === 'sway' || c.kind === 'exile' || c.kind === 'rally') && !(a.slot >= 0 && a.slot < 3)) throw new Error('bad slot');
    P.mana -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, slot: a.slot, mana: P.mana });
    if (c.kind === 'sway') { const n = s.slots[a.slot], from = n.loy; n.loy = clamp(n.loy + c.pull * dir(me)); emit(s, ev, { t: 'loy', slot: a.slot, from, to: n.loy }); }
    else if (c.kind === 'spread') for (let j = 0; j < 3; j++) { const n = s.slots[j], from = n.loy; n.loy = clamp(n.loy + dir(me)); emit(s, ev, { t: 'loy', slot: j, from, to: n.loy }); }
    else if (c.kind === 'exile') { const old = s.slots[a.slot]; s.slots[a.slot] = newNeutral(s.ndeck.shift()); emit(s, ev, { t: 'exile', slot: a.slot, old: old.atk, atk: s.slots[a.slot].atk, uid: s.slots[a.slot].uid }); }
    else if (c.kind === 'shield') { P.shield += SHIELD; emit(s, ev, { t: 'shield', side: me, shield: P.shield }); }
    else if (c.kind === 'rally') damage(s, 1 - me, s.slots[a.slot].atk, ev, 'rally', a.slot);
    else if (c.kind === 'draw') { drawOne(s, me, ev); drawOne(s, me, ev); }
    else if (c.kind === 'coin') { P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    checkWin(s, ev);
  } else if (a.t === 'end') {
    P.mana = 0;
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    s.toAct = 1 - me;
    startTurn(s, ev);
  } else throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
