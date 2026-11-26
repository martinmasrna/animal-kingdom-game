// Toy 2: rounds of alternating face-up plays, resolved all at once by speed.
// Each round: both draw 3 and gain 6 energy (start 10, cap 10). Players take turns
// playing one card or passing; two passes in a row end the round, and everything
// played resolves fastest first. Pure from the outside: transitions clone the state.

export const HP = 30, MAX_E = 10, ROUND_LIMIT = 30;
export let GAIN = 6, DRAW = 3, GUARD_RATE = 2, STRIKES_FIRST = true, CARRY = true;
export function setRules(r) { if (r.gain != null) GAIN = r.gain; if (r.draw != null) DRAW = r.draw; if (r.strikesFirst != null) STRIKES_FIRST = r.strikesFirst; if (r.carry != null) CARRY = r.carry; if (r.guardRate != null) { GUARD_RATE = r.guardRate; buildCards(); } }

// Speed: higher resolves sooner. A strike or guard costing c has speed 7 - c.
export const CARDS = {};
function buildCards() {
  for (let c = 1; c <= 6; c++) CARDS['S' + c] = { id: 'S' + c, kind: 'Strike', cost: c, n: c, speed: 7 - c };
  for (let c = 1; c <= 4; c++) CARDS['G' + c] = { id: 'G' + c, kind: 'Guard', cost: c, n: Math.max(1, Math.round(GUARD_RATE * c)), speed: 7 - c };
  CARDS.SW = { id: 'SW', kind: 'Sword', cost: 3, n: 2, speed: 5 };
}
buildCards();
export const DECK = { S2: 3, S3: 3, S4: 3, S5: 3, S6: 3, G1: 3, G2: 3, G3: 3, G4: 3, SW: 3 };

export function deckList() {
  const out = [];
  for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id);
  return out;
}
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

function newPlayer() { return { hp: HP, maxHp: HP, mana: MAX_E, block: 0, sword: 0, hand: [], deck: deckList(), played: [], line: [] }; }
function clonePlayer(p) { return { ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice(), line: p.line.slice() }; }
export function clone(s) { return { ...s, p: [clonePlayer(s.p[0]), clonePlayer(s.p[1])] }; }

function emit(s, ev, e) { if (ev) { e.round = s.round; ev.push(e); } }
function draw(s, side, n) {
  const p = s.p[side]; let d = 0;
  for (let i = 0; i < n && p.deck.length; i++) { p.hand.push(p.deck.shift()); d++; }
  return d;
}
export function strikeDmg(p, id) { return CARDS[id].n + p.sword; }

export function newMatch({ seed }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, starter: 0, toAct: 0, passes: 0, winner: null, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  draw(s, 0, 3); draw(s, 1, 3);
  s.starter = rand(s) < 0.5 ? 1 : 0; // flipped by the first round start
  mStartRound(s, null);
  return s;
}

function mStartRound(s, ev) {
  s.round++;
  s.starter = 1 - s.starter;
  s.toAct = s.starter; s.passes = 0;
  emit(s, ev, { t: 'round', starter: s.starter });
  for (const side of [0, 1]) {
    const p = s.p[side];
    const before = p.mana;
    if (s.round > 1) p.mana = CARRY ? Math.min(MAX_E, p.mana + GAIN) : GAIN;
    p.block = 0; p.line = [];
    const drew = draw(s, side, DRAW);
    emit(s, ev, { t: 'start', side, mana: p.mana, gain: p.mana - before, drew });
  }
}

export function canPlay(s, id) {
  if (s.winner !== null || !CARDS[id]) return false;
  const p = s.p[s.toAct];
  if (CARDS[id].kind === 'Sword' && (p.sword || p.line.includes('SW'))) return false;
  return p.hand.includes(id) && CARDS[id].cost <= p.mana;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  return [null].concat([...new Set(s.p[s.toAct].hand)].filter(id => canPlay(s, id)));
}

function mPlay(s, id, ev) {
  if (!canPlay(s, id)) throw new Error('play: illegal ' + id);
  const side = s.toAct, p = s.p[side];
  p.mana -= CARDS[id].cost;
  p.hand.splice(p.hand.indexOf(id), 1);
  p.line.push(id);
  emit(s, ev, { t: 'play', side, card: id, mana: p.mana });
  s.passes = 0;
  s.toAct = 1 - side;
}

function mPass(s, ev) {
  if (s.winner !== null) throw new Error('pass: match over');
  emit(s, ev, { t: 'pass', side: s.toAct });
  s.passes++;
  if (s.passes >= 2) { mResolve(s, ev); return; }
  s.toAct = 1 - s.toAct;
}

// Everything played this round, fastest first. At one speed, guards and swords go up
// before that speed's strikes land; strikes of one speed land together.
function mResolve(s, ev) {
  emit(s, ev, { t: 'resolve' });
  for (let sp = 6; sp >= 1 && s.winner === null; sp--) {
    const at = [0, 1].map(i => s.p[i].line.filter(id => CARDS[id].speed === sp));
    if (!at[0].length && !at[1].length) continue;
    emit(s, ev, { t: 'step', speed: sp });
    const upFirst = (c) => c.kind === 'Sword' || (c.kind === 'Guard' && !STRIKES_FIRST);
    const raise = (first) => { for (const i of [0, 1]) for (const id of at[i]) {
      const c = CARDS[id], p = s.p[i];
      if (upFirst(c) !== first) continue;
      if (c.kind === 'Guard') { p.block += c.n; emit(s, ev, { t: 'guard', side: i, card: id, n: c.n, block: p.block }); }
      if (c.kind === 'Sword') { p.sword = c.n; emit(s, ev, { t: 'sword', side: i, card: id }); }
    } };
    raise(true);
    const dmgIn = [0, 0];
    for (const i of [0, 1]) {
      const p = s.p[i], o = s.p[1 - i];
      for (const id of at[i]) {
        if (CARDS[id].kind !== 'Strike') continue;
        const total = strikeDmg(p, id);
        const absorbed = Math.min(o.block, total);
        o.block -= absorbed;
        if (absorbed) emit(s, ev, { t: 'stop', side: 1 - i, card: id, n: absorbed, block: o.block });
        const dmg = total - absorbed;
        if (dmg) { o.hp -= dmg; dmgIn[1 - i] += dmg; emit(s, ev, { t: 'hit', side: i, card: id, dmg }); }
      }
    }
    for (const i of [0, 1]) if (dmgIn[i] && s.p[i].sword) { s.p[i].sword = 0; emit(s, ev, { t: 'drop', side: i }); }
    raise(false);
    checkWin(s, ev);
  }
  for (const p of s.p) { p.played.push(...p.line); p.line = []; p.block = 0; }
  if (s.winner === null) {
    if (s.round >= ROUND_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    mStartRound(s, ev);
  }
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].hp <= 0, b = s.p[1].hp <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}

// act(s, id) plays a card; act(s, null) passes.
export function act(s, id, ev) { const t = clone(s); if (id === null) mPass(t, ev); else mPlay(t, id, ev); return t; }
export function _act(t, id) { if (id === null) mPass(t, null); else mPlay(t, id, null); return t; }

export function deckSummary(s, side) {
  const p = s.p[side], cnt = (a) => a.reduce((m, x) => (m[x] = (m[x] || 0) + 1, m), {});
  const gone = cnt(p.played.concat(p.line)), h = cnt(p.hand), d = cnt(p.deck);
  return Object.entries(DECK).map(([id, total]) => ({ id, total, played: gone[id] || 0, inHand: h[id] || 0, inDeck: d[id] || 0, unseen: total - (gone[id] || 0) }));
}
