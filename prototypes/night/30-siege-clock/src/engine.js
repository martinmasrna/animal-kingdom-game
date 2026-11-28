// 30 Siege clock. Two roles with their own decks: the Attacker must bring the Gate from 20 to 0
// within ten rounds; the Defender holds. Each round the Attacker plays cards and sends units at
// the Gate, the Defender blocks with Wall units (they never tire), then the Defender plays
// cards and its Shooters fire. Pure from the outside: act() clones the state; step() mutates it.

export const GATE = 20, ROUNDS = 10, FIELD = 5, WALL = 4, HAND0 = 4, MAX_MANA = 10;
// The one rule changed from the spec (it had Wall units block every round): a Wall unit that
// blocks is tired and cannot block in the next round. TIRE = false plays the spec's rule.
export let TIRE = true;
export function setTire(v) { TIRE = v; }

export const CARDS = {
  // Attacker
  GR: { id: 'GR', name: 'Grunt', side: 'A', kind: 'Unit', cost: 1, atk: 2, hp: 2 },
  CL: { id: 'CL', name: 'Climber', side: 'A', kind: 'Unit', cost: 2, atk: 2, hp: 1, text: 'Cannot be blocked.' },
  RM: { id: 'RM', name: 'Ram', side: 'A', kind: 'Unit', cost: 3, atk: 3, hp: 3, text: 'Double damage to the Gate.' },
  BR: { id: 'BR', name: 'Brute', side: 'A', kind: 'Unit', cost: 4, atk: 4, hp: 6 },
  SH: { id: 'SH', name: 'Shield', side: 'A', kind: 'Unit', cost: 3, atk: 1, hp: 6, text: 'Shooters and Snipes must target it.' },
  VO: { id: 'VO', name: 'Volley', side: 'A', kind: 'Spell', cost: 2, text: '2 damage to a Wall unit.' },
  RU: { id: 'RU', name: 'Rush', side: 'A', kind: 'Spell', cost: 1, text: 'A unit played this turn may attack.' },
  AD: { id: 'AD', name: 'Draw 2', side: 'A', kind: 'Spell', cost: 2, text: 'Draw 2 cards.' },
  // Defender
  GU: { id: 'GU', name: 'Guard', side: 'D', kind: 'Unit', cost: 1, atk: 1, hp: 3 },
  SO: { id: 'SO', name: 'Shooter', side: 'D', kind: 'Unit', cost: 2, atk: 1, hp: 2, text: 'Shoots 1 at the end of your turn.' },
  PI: { id: 'PI', name: 'Pike', side: 'D', kind: 'Unit', cost: 3, atk: 3, hp: 4 },
  HV: { id: 'HV', name: 'Heavy', side: 'D', kind: 'Unit', cost: 4, atk: 3, hp: 7 },
  RP: { id: 'RP', name: 'Repair', side: 'D', kind: 'Spell', cost: 2, text: 'Gate +3 (max 20).' },
  OI: { id: 'OI', name: 'Oil', side: 'D', kind: 'Spell', cost: 4, text: '2 damage to every Field unit.' },
  SN: { id: 'SN', name: 'Snipe', side: 'D', kind: 'Spell', cost: 1, text: '2 damage to a Field unit.' },
  DD: { id: 'DD', name: 'Draw 2', side: 'D', kind: 'Spell', cost: 2, text: 'Draw 2 cards.' },
};
export const DECKS = {
  A: { GR: 4, CL: 3, RM: 3, BR: 3, SH: 2, VO: 3, RU: 3, AD: 3 },
  D: { GU: 4, SO: 4, PI: 3, HV: 2, RP: 3, OI: 3, SN: 3, DD: 2 },
};
function deckList(role) { const out = []; for (const [id, k] of Object.entries(DECKS[role])) for (let i = 0; i < k; i++) out.push(id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// s.att / s.def: the seats of the two roles. s.phase: 'att' (Attacker plays and sends units),
// 'block' (the Defender assigns its Wall units one by one, s.bi the next), 'def' (Defender plays),
// 'shoot' (the Defender aims its Shooters one by one, s.si the next).
function newPlayer(role) { return { role, mana: 0, hand: [], deck: deckList(role), units: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), units: p.units.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function draw(s, side, ev) { const p = s.p[side]; if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); } }

// attacker: the seat that attacks (0 or 1); first is the same thing, kept for the harness
export function newMatch({ seed, attacker }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, turnNo: 0, gate: GATE, winner: null, uid: 1, phase: 'att', bi: 0, si: 0, p: null, att: 0, def: 1 };
  s.att = attacker === 0 || attacker === 1 ? attacker : (rand(s) < 0.5 ? 0 : 1);
  s.def = 1 - s.att; s.first = s.att;
  s.p = [null, null]; s.p[s.att] = newPlayer('A'); s.p[s.def] = newPlayer('D');
  for (const p of s.p) shuffleInPlace(s, p.deck);
  for (const p of s.p) for (let i = 0; i < HAND0; i++) p.hand.push(p.deck.shift());
  startAttacker(s, null);
  return s;
}
export const field = (s) => s.p[s.att].units, wall = (s) => s.p[s.def].units;
function startAttacker(s, ev) {
  s.round++; s.turnNo++;
  const P = s.p[s.att];
  s.phase = 'att'; s.turn = s.toMove = s.att;
  P.mana = Math.min(MAX_MANA, s.round);
  for (const m of P.units) { m.ready = true; m.fresh = false; m.sent = false; }
  emit(s, ev, { t: 'turn', side: s.att, round: s.round });
  draw(s, s.att, ev);
}
function startDefender(s, ev) {
  s.turnNo++;
  const P = s.p[s.def];
  s.phase = 'def'; s.turn = s.toMove = s.def;
  P.mana = Math.min(MAX_MANA, s.round);
  emit(s, ev, { t: 'turn', side: s.def, round: s.round });
  draw(s, s.def, ev);
}
// Shield: while one stands, Shooters and Snipes may target only Shields
const shieldUp = (s) => field(s).some(m => m.card === 'SH');
export const aimable = (s, i) => !shieldUp(s) || field(s)[i].card === 'SH';
const sentList = (s) => field(s).map((m, i) => i).filter(i => field(s)[i].sent);
// a Wall unit may block unless it blocked last round
export const canBlock = (s, w) => !(TIRE && w.tired === s.round - 1);
const blockable = (s) => field(s).map((m, i) => i).filter(i => field(s)[i].sent && field(s)[i].card !== 'CL' && field(s)[i].blockedBy == null);

// Actions:
//   phase att:   { t: 'play', card, i } (i: Volley's Wall target, Rush's Field unit)  { t: 'send', i }  { t: 'end' }
//   phase block: { t: 'block', a } (the next Wall unit blocks sent unit a, or -1: no block)
//   phase def:   { t: 'play', card, i } (i: Snipe's Field target)  { t: 'end' }
//   phase shoot: { t: 'shoot', i } (the next Shooter hits Field unit i)
export function key(a) {
  if (a.t === 'end') return 'e';
  if (a.t === 'send') return 's' + a.i;
  if (a.t === 'block') return 'b' + a.a;
  if (a.t === 'shoot') return 'x' + a.i;
  return 'p' + a.card + (a.i != null ? ':' + a.i : '');
}
function needsTarget(id) { return id === 'VO' || id === 'RU' || id === 'SN'; }
export function isLegal(s, a) {
  if (s.winner !== null || !a) return false;
  const me = s.toMove, P = s.p[me];
  if (s.phase === 'block') {
    if (a.t !== 'block') return false;
    if (a.a === -1) return true;
    const m = field(s)[a.a];
    return !!m && m.sent && m.card !== 'CL' && m.blockedBy == null;
  }
  if (s.phase === 'shoot') return a.t === 'shoot' && a.i >= 0 && a.i < field(s).length && aimable(s, a.i);
  if (a.t === 'end') return true;
  if (a.t === 'send') { const m = s.phase === 'att' && P.units[a.i]; return !!m && m.ready && !m.sent; }
  if (a.t !== 'play' || !P.hand.includes(a.card)) return false;
  const c = CARDS[a.card];
  if (c.cost > P.mana) return false;
  if (c.kind === 'Unit') return P.units.length < (P.role === 'A' ? FIELD : WALL) && a.i == null;
  if (a.card === 'VO') return a.i >= 0 && a.i < wall(s).length;
  if (a.card === 'RU') { const m = P.units[a.i]; return !!m && m.fresh && !m.ready; }
  if (a.card === 'SN') return a.i >= 0 && a.i < field(s).length && aimable(s, a.i);
  return a.i == null;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.toMove, P = s.p[me], out = [];
  if (s.phase === 'block') { out.push({ t: 'block', a: -1 }); for (const i of blockable(s)) out.push({ t: 'block', a: i }); return out; }
  if (s.phase === 'shoot') { field(s).forEach((_, i) => { if (aimable(s, i)) out.push({ t: 'shoot', i }); }); return out; }
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.units.length < (P.role === 'A' ? FIELD : WALL)) out.push({ t: 'play', card: id }); }
    else if (id === 'VO') wall(s).forEach((_, i) => out.push({ t: 'play', card: id, i }));
    else if (id === 'RU') P.units.forEach((m, i) => { if (m.fresh && !m.ready) out.push({ t: 'play', card: id, i }); });
    else if (id === 'SN') field(s).forEach((_, i) => { if (aimable(s, i)) out.push({ t: 'play', card: id, i }); });
    else out.push({ t: 'play', card: id });
  }
  if (s.phase === 'att') P.units.forEach((m, i) => { if (m.ready && !m.sent) out.push({ t: 'send', i }); });
  out.push({ t: 'end' });
  return out;
}

function hurt(s, side, i, n, ev) { const m = s.p[side].units[i]; m.hp -= n; emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid }); }
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const U = s.p[side].units;
    for (let i = U.length - 1; i >= 0; i--) if (U[i].hp <= 0) {
      emit(s, ev, { t: 'die', side, i, uid: U[i].uid, card: U[i].card });
      // a Wall unit that dies frees the attacker it was assigned to (blocks are decided before combat; this only happens to Volley-free cases)
      U.splice(i, 1);
    }
  }
}
function gateHit(s, n, ev) {
  s.gate -= n; emit(s, ev, { t: 'gate', n, gate: s.gate });
  if (s.gate <= 0 && s.winner === null) { s.gate = Math.max(0, s.gate); s.winner = s.att; emit(s, ev, { t: 'end', winner: s.winner }); }
}

function beginBlocks(s, ev) {
  for (const m of field(s)) m.blockedBy = null;
  s.phase = 'block'; s.bi = 0; s.toMove = s.def;
  emit(s, ev, { t: 'charge', side: s.att, n: sentList(s).length });
  nextBlock(s, ev);
}
// the next Wall unit to assign, or combat when none is left or nothing is left to block
function nextBlock(s, ev) {
  while (s.bi < wall(s).length && !canBlock(s, wall(s)[s.bi])) s.bi++;
  if (s.bi < wall(s).length && blockable(s).length) return;
  resolveCombat(s, ev);
}
function resolveCombat(s, ev) {
  const F = field(s), Wl = wall(s);
  emit(s, ev, { t: 'combat' });
  const pairs = [];
  F.forEach((m, i) => { if (m.sent) pairs.push([m, m.blockedBy != null ? Wl[m.blockedBy] : null]); });
  for (const [m, b] of pairs) {
    if (b) {
      const ia = F.indexOf(m), ib = Wl.indexOf(b), da = m.atk, db = b.atk;
      b.tired = s.round;
      emit(s, ev, { t: 'clash', uid: m.uid, tuid: b.uid });
      hurt(s, s.def, ib, da, ev); hurt(s, s.att, ia, db, ev);
    } else {
      emit(s, ev, { t: 'strike', uid: m.uid });
      gateHit(s, m.card === 'RM' ? 2 * m.atk : m.atk, ev);
      if (s.winner !== null) break;
    }
  }
  sweep(s, ev);
  for (const m of field(s)) { m.sent = false; m.blockedBy = null; }
  if (s.winner === null) startDefender(s, ev);
}
function endDefender(s, ev) {
  if (wall(s).some(m => m.card === 'SO') && field(s).length) { s.phase = 'shoot'; s.si = 0; emit(s, ev, { t: 'volley' }); return nextShot(s, ev); }
  endRound(s, ev);
}
function nextShot(s, ev) {
  const shooters = wall(s).filter(m => m.card === 'SO');
  if (s.si < shooters.length && field(s).length) return;
  endRound(s, ev);
}
function endRound(s, ev) {
  if (s.round >= ROUNDS) { s.winner = s.def; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startAttacker(s, ev);
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a) + ' in ' + s.phase);
  const me = s.toMove, P = s.p[me];
  if (s.phase === 'block') {
    const w = wall(s)[s.bi];
    if (a.a >= 0) { field(s)[a.a].blockedBy = s.bi; emit(s, ev, { t: 'block', uid: w.uid, tuid: field(s)[a.a].uid }); }
    s.bi++;
    return nextBlock(s, ev);
  }
  if (s.phase === 'shoot') {
    const sh = wall(s).filter(m => m.card === 'SO')[s.si];
    emit(s, ev, { t: 'shot', uid: sh.uid, tuid: field(s)[a.i].uid });
    hurt(s, s.att, a.i, 1, ev); sweep(s, ev);
    s.si++;
    return nextShot(s, ev);
  }
  if (a.t === 'end') {
    emit(s, ev, { t: 'endturn', side: me });
    if (s.phase === 'att') { if (sentList(s).length) beginBlocks(s, ev); else startDefender(s, ev); }
    else endDefender(s, ev);
    return;
  }
  if (a.t === 'send') { P.units[a.i].sent = true; emit(s, ev, { t: 'send', side: me, uid: P.units[a.i].uid }); return; }
  const c = CARDS[a.card];
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
  emit(s, ev, { t: 'play', side: me, card: a.card, a });
  if (c.kind === 'Unit') {
    const m = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: P.role === 'D', fresh: true, sent: false };
    P.units.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    return;
  }
  if (a.card === 'VO') { hurt(s, s.def, a.i, 2, ev); sweep(s, ev); }
  else if (a.card === 'RU') { P.units[a.i].ready = true; emit(s, ev, { t: 'rush', uid: P.units[a.i].uid }); }
  else if (a.card === 'SN') { hurt(s, s.att, a.i, 2, ev); sweep(s, ev); }
  else if (a.card === 'OI') { for (let i = 0; i < field(s).length; i++) hurt(s, s.att, i, 2, ev); sweep(s, ev); }
  else if (a.card === 'RP') { const g = Math.min(GATE, s.gate + 3); emit(s, ev, { t: 'repair', n: g - s.gate, gate: g }); s.gate = g; }
  else if (a.card === 'AD' || a.card === 'DD') { draw(s, me, ev); draw(s, me, ev); }
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
