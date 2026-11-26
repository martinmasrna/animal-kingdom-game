// Toy 4: one card each per round, chosen blind, then revealed. Three kinds in a circle:
//   Quick interrupts Heavy (the Heavy is cancelled, the Quick lands),
//   Heavy breaks Guard (the Heavy lands in full),
//   Guard stops Quick (the Quick is blocked, the Guard deals its number back).
// Same kind: two strikes both land; two guards do nothing. Draw 1 a round; the
// played cards are shuffled back in when the deck runs out. Pure from the outside.

export let HP = 20;
export const ROUND_LIMIT = 60;
export function setRules(r) { if (r.hp != null) HP = r.hp; }

export const CARDS = {};
for (const n of [1, 2, 3]) CARDS['Q' + n] = { id: 'Q' + n, kind: 'Quick', n };
for (const n of [4, 5, 6]) CARDS['H' + n] = { id: 'H' + n, kind: 'Heavy', n };
for (const n of [1, 2, 3]) CARDS['G' + n] = { id: 'G' + n, kind: 'Guard', n };
export const DECK = { Q1: 1, Q2: 1, Q3: 1, H4: 1, H5: 1, H6: 1, G1: 1, G2: 1, G3: 1 };

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

function newPlayer() { return { hp: HP, maxHp: HP, hand: [], deck: deckList(), played: [], line: [] }; }
function clonePlayer(p) { return { ...p, hand: p.hand.slice(), deck: p.deck.slice(), played: p.played.slice(), line: p.line.slice() }; }
export function clone(s) { return { ...s, p: [clonePlayer(s.p[0]), clonePlayer(s.p[1])] }; }

function emit(s, ev, e) { if (ev) { e.round = s.round; ev.push(e); } }
function draw(s, side, n) {
  const p = s.p[side]; let d = 0;
  for (let i = 0; i < n; i++) {
    if (!p.deck.length && p.played.length) { p.deck = shuffleInPlace(s, p.played); p.played = []; }
    if (!p.deck.length) break;
    p.hand.push(p.deck.shift()); d++;
  }
  return d;
}

export function newMatch({ seed }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, winner: null, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  draw(s, 0, 3); draw(s, 1, 3);
  mStartRound(s, null);
  return s;
}
function mStartRound(s, ev) {
  s.round++;
  emit(s, ev, { t: 'round' });
  for (const side of [0, 1]) { s.p[side].line = []; const drew = draw(s, side, 1); emit(s, ev, { t: 'start', side, drew }); }
}

export function validSet(s, side, ids) { return ids.length === 1 && s.p[side].hand.includes(ids[0]); }

// What card a of one side does to card b of the other: damage dealt by a, and how.
export function clash(a, b) {
  const A = CARDS[a], B = CARDS[b];
  if (A.kind === 'Guard') return B.kind === 'Quick' ? { dmg: A.n, how: 'counter' } : { dmg: 0, how: B.kind === 'Heavy' ? 'broken' : 'idle' };
  if (A.kind === 'Quick') return B.kind === 'Guard' ? { dmg: 0, how: 'blocked' } : { dmg: A.n, how: B.kind === 'Heavy' ? 'interrupt' : 'hit' };
  // Heavy
  if (B.kind === 'Quick') return { dmg: 0, how: 'interrupted' };
  return { dmg: A.n, how: B.kind === 'Guard' ? 'break' : 'hit' };
}

function mCommit(s, choices, ev) {
  if (s.winner !== null) throw new Error('commit: match over');
  for (const i of [0, 1]) if (!validSet(s, i, choices[i])) throw new Error('commit: illegal for side ' + i + ': ' + choices[i]);
  for (const i of [0, 1]) {
    const p = s.p[i], id = choices[i][0];
    p.hand.splice(p.hand.indexOf(id), 1);
    p.line = [id];
    emit(s, ev, { t: 'reveal', side: i, cards: [id] });
  }
  const a = choices[0][0], b = choices[1][0];
  const r = [clash(a, b), clash(b, a)];
  for (const i of [0, 1]) {
    emit(s, ev, { t: 'clash', side: i, card: i ? b : a, how: r[i].how, dmg: r[i].dmg });
    if (r[i].dmg) { s.p[1 - i].hp -= r[i].dmg; emit(s, ev, { t: 'hit', side: i, card: i ? b : a, dmg: r[i].dmg }); }
  }
  const x = s.p[0].hp <= 0, y = s.p[1].hp <= 0;
  if (x || y) { s.winner = x && y ? 'draw' : x ? 1 : 0; emit(s, ev, { t: 'end', winner: s.winner }); }
  for (const p of s.p) { p.played.push(...p.line); p.line = []; }
  if (s.winner === null) {
    if (s.round >= ROUND_LIMIT) { s.winner = 'draw'; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    mStartRound(s, ev);
  }
}

export function commit(s, choices, ev) { const t = clone(s); mCommit(t, choices, ev); return t; }
export function _commit(t, choices) { mCommit(t, choices, null); return t; }

export function deckSummary(s, side) {
  const p = s.p[side], cnt = (a) => a.reduce((m, x) => (m[x] = (m[x] || 0) + 1, m), {});
  const gone = cnt(p.played.concat(p.line)), h = cnt(p.hand), d = cnt(p.deck);
  return Object.entries(DECK).map(([id, total]) => ({ id, total, played: gone[id] || 0, inHand: h[id] || 0, inDeck: d[id] || 0, unseen: total - (gone[id] || 0) }));
}
