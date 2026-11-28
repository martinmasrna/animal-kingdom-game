// 38 Costed tricks. Trick-taking with follow-suit and trumps, where a face-up card costs energy by
// rank, any card can go face-down for free (and never wins), and each trick's prize is shown in
// advance. Pure from the outside: act() clones the state.

export const SUITS = ['A', 'B', 'C', 'D'], RANKS = [1, 2, 3, 4, 5, 6], HAND = 8, ENERGY = 10, TARGET = 20, HANDS = 5;
export const PRIZES = [1, 1, 1, 2, 2, 2, 3, 3];
export const suitOf = (c) => c[0], rankOf = (c) => +c[1];
export const costOf = (c) => { const r = rankOf(c); return r <= 2 ? 0 : r <= 4 ? 1 : r === 5 ? 2 : 3; };
export function deckList() { const out = []; for (const s of SUITS) for (const r of RANKS) out.push(s + r); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export function clone(s) {
  return { ...s, prizes: s.prizes.slice(), led: s.led && { ...s.led }, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), rest: p.rest.slice(), seen: p.seen.slice(), voids: p.voids.map(v => ({ ...v })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, hand: 0, first: 0, leader: 0, toMove: 0, trick: 0, trump: 'A', prizes: [], led: null, winner: null,
    p: [0, 1].map(() => ({ score: 0, energy: ENERGY, hand: [], rest: [], seen: [], voids: [] })) };
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  startHand(s, null);
  return s;
}
// each player shuffles its own 24 cards and deals itself 8; `rest` are its undealt cards, `seen`
// the cards it has shown face-up this hand, `voids` what its failures to follow suit proved
function startHand(s, ev) {
  s.hand++;
  for (const p of s.p) { const d = shuffleInPlace(s, deckList()); p.hand = d.slice(0, HAND); p.rest = d.slice(HAND); p.energy = ENERGY; p.seen = []; p.voids = []; }
  s.trump = SUITS[(s.hand - 1) % 4];
  s.prizes = shuffleInPlace(s, PRIZES.slice());
  s.trick = 0; s.led = null;
  s.leader = s.toMove = s.hand % 2 === 1 ? s.first : 1 - s.first;
  emit(s, ev, { t: 'hand', hand: s.hand, trump: s.trump, prizes: s.prizes.slice(), leader: s.leader });
}

// Actions: { t: 'play', card, up } — up: face-up, paying its cost; otherwise face-down for free.
export function key(a) { return (a.up ? 'u' : 'd') + a.card; }
// cards of the led suit the follower holds and can pay for
function mustFollow(s, P) { return s.led && s.led.up ? P.hand.filter(c => suitOf(c) === suitOf(s.led.card) && costOf(c) <= P.energy) : []; }
export function isLegal(s, a) {
  if (s.winner !== null || a.t !== 'play') return false;
  const P = s.p[s.toMove];
  if (!P.hand.includes(a.card)) return false;
  if (a.up && costOf(a.card) > P.energy) return false;
  if (s.led) { const f = mustFollow(s, P); if (f.length) return a.up && f.includes(a.card); }
  return true;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  const out = [];
  for (const c of s.p[s.toMove].hand) for (const up of [true, false]) { const a = { t: 'play', card: c, up }; if (isLegal(s, a)) out.push(a); }
  return out;
}
// who takes a trick: led and follow are { card, up }
export function trickWinner(s, led, fol, leader) {
  if (!led.up && !fol.up) return leader;
  if (!led.up) return 1 - leader;
  if (!fol.up) return leader;
  const lt = suitOf(led.card) === s.trump, ft = suitOf(fol.card) === s.trump;
  if (lt || ft) { if (lt && ft) return rankOf(fol.card) > rankOf(led.card) ? 1 - leader : leader; return ft ? 1 - leader : leader; }
  return suitOf(fol.card) === suitOf(led.card) && rankOf(fol.card) > rankOf(led.card) ? 1 - leader : leader;
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.toMove, P = s.p[me];
  if (s.led) { const f = mustFollow(s, P); if (!f.length && s.led.up) P.voids.push({ suit: suitOf(s.led.card), max: P.energy }); }
  P.hand.splice(P.hand.indexOf(a.card), 1);
  if (a.up) { P.energy -= costOf(a.card); P.seen.push(a.card); }
  emit(s, ev, { t: 'play', side: me, card: a.up ? a.card : null, up: a.up, cost: a.up ? costOf(a.card) : 0, own: a.card });
  if (!s.led) { s.led = { card: a.card, up: a.up }; s.toMove = 1 - me; return; }
  const w = trickWinner(s, s.led, a, s.leader);
  const prize = s.prizes[s.trick];
  s.p[w].score += prize;
  emit(s, ev, { t: 'trick', winner: w, prize, trick: s.trick, score: [s.p[0].score, s.p[1].score] });
  s.trick++; s.led = null; s.leader = s.toMove = w;
  if (s.trick < HAND) return;
  // end of hand
  const [x, y] = [s.p[0].score, s.p[1].score];
  if ((x >= TARGET || y >= TARGET) && x !== y) s.winner = x > y ? 0 : 1;
  else if (s.hand >= HANDS) { s.winner = x > y ? 0 : y > x ? 1 : 'draw'; s.limit = true; }
  if (s.winner !== null) { emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startHand(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
