// Possession. A ball on zones 0 to 8; A scores at 8, B at 0. Each play both players choose at once,
// the one in possession an attacking option, the other a defending one, each priced in stamina; the
// pair is looked up in one table. Most goals after 20 plays wins.
// Pure from the outside: play() clones the state; _play() mutates (for the bots' play-outs).

export const ZONES = 9, MID = 4, PLAYS = 20, HALF = 10, STAMINA = 10, REFILL = 4, HAND = 4;

export const OPTS = {
  WALK: { id: 'WALK', name: 'Walk', side: 'att', cost: 0, basic: true },
  SHOOT: { id: 'SHOOT', name: 'Shoot', side: 'att', cost: 1, basic: true },
  PASS: { id: 'PASS', name: 'Pass', side: 'att', cost: 1 },
  LONG: { id: 'LONG', name: 'Long', side: 'att', cost: 2 },
  DRIBBLE: { id: 'DRIBBLE', name: 'Dribble', side: 'att', cost: 1 },
  STAND: { id: 'STAND', name: 'Stand', side: 'def', cost: 0, basic: true },
  BLOCK: { id: 'BLOCK', name: 'Block', side: 'def', cost: 1, basic: true },
  TACKLE: { id: 'TACKLE', name: 'Tackle', side: 'def', cost: 1 },
  INTERCEPT: { id: 'INTERCEPT', name: 'Intercept', side: 'def', cost: 1 },
  PRESS: { id: 'PRESS', name: 'Press', side: 'def', cost: 2 },
};
export const ATT = ['WALK', 'SHOOT', 'PASS', 'LONG', 'DRIBBLE'], DEF = ['STAND', 'BLOCK', 'TACKLE', 'INTERCEPT', 'PRESS'];
// outcome: a number = zones gained, 'T' = turnover, 'G' = goal
export const TABLE = {
  WALK: { STAND: 0, BLOCK: 1, TACKLE: 'T', INTERCEPT: 1, PRESS: 'T' },
  PASS: { STAND: 2, BLOCK: 2, TACKLE: 'T', INTERCEPT: 'T', PRESS: 'T' },
  LONG: { STAND: 3, BLOCK: 3, TACKLE: 3, INTERCEPT: 'T', PRESS: 3 },
  DRIBBLE: { STAND: 1, BLOCK: 1, TACKLE: 1, INTERCEPT: 1, PRESS: 'T' },
  SHOOT: { STAND: 'G', BLOCK: 'T', TACKLE: 'G', INTERCEPT: 'G', PRESS: 'G' },
};
export const DECK = { PASS: 3, LONG: 2, DRIBBLE: 3, TACKLE: 3, INTERCEPT: 3, PRESS: 2 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(rnd, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export function clone(s) { return { ...s, hist: s.hist.slice(), goals: s.goals.slice(), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice() })) }; }
function draw(s, side) {
  const p = s.p[side];
  if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(() => rand(s), p.discard); p.discard = []; }
  p.hand.push(p.deck.shift());
}

// s.first: the side with possession at kickoff
export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, play: 0, ball: MID, poss: 0, first: 0, goals: [0, 0], winner: null, capped: false, last: null, hist: [],
    p: [0, 1].map(() => ({ stamina: STAMINA, hand: [], deck: deckList(), discard: [] })) };
  for (const p of s.p) shuffleInPlace(() => rand(s), p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  s.poss = s.first;
  for (const side of [0, 1]) for (let i = 0; i < HAND; i++) draw(s, side);
  return s;
}

export const inRange = (s, side) => side === 0 ? s.ball >= ZONES - 3 : s.ball <= 2;
export const role = (s, side) => s.poss === side ? 'att' : 'def';
// The options `side` may choose now: the basics of its role (Shoot only in range) and the cards of
// its role in hand, each only if its stamina pays for it. Every option once.
export function options(s, side) {
  const p = s.p[side], r = role(s, side), out = [];
  for (const id of (r === 'att' ? ATT : DEF)) {
    const o = OPTS[id];
    if (o.cost > p.stamina) continue;
    if (o.basic) { if (id === 'SHOOT' && !inRange(s, side)) continue; out.push(id); }
    else if (p.hand.includes(id)) out.push(id);
  }
  return out;
}

// Both choices revealed and applied. ev (optional) collects what happened.
function mPlay(s, choice, ev) {
  if (s.winner !== null) throw new Error('match over');
  const att = s.poss, def = 1 - att, a = choice[att], d = choice[def];
  if (!options(s, att).includes(a) || !options(s, def).includes(d)) throw new Error('illegal option ' + a + '/' + d);
  for (const side of [0, 1]) {
    const id = choice[side], p = s.p[side];
    p.stamina -= OPTS[id].cost;
    if (!OPTS[id].basic) { p.hand.splice(p.hand.indexOf(id), 1); p.discard.push(id); }
  }
  s.hist.push({ att, a, d, r: inRange(s, att) }); // every revealed pair, public
  const r = TABLE[a][d], from = s.ball;
  let out;
  if (r === 'G') { s.goals[att]++; s.ball = MID; s.poss = def; out = 'goal'; }
  else if (r === 'T') { s.poss = def; out = 'turnover'; }
  else { s.ball = att === 0 ? Math.min(ZONES - 1, s.ball + r) : Math.max(0, s.ball - r); out = r; }
  for (const side of [0, 1]) if (!OPTS[choice[side]].basic) draw(s, side);
  s.play++;
  s.last = { att, a, d, out, from, to: s.ball };
  if (ev) ev.push({ t: 'play', ...s.last, play: s.play });
  if (s.play === HALF) { for (const p of s.p) p.stamina = Math.min(STAMINA, p.stamina + REFILL); if (ev) ev.push({ t: 'refill' }); }
  if (s.play >= PLAYS) { s.winner = s.goals[0] === s.goals[1] ? 'draw' : s.goals[0] > s.goals[1] ? 0 : 1; if (ev) ev.push({ t: 'end', winner: s.winner }); }
}
export function play(s, choice, ev) { const t = clone(s); mPlay(t, choice, ev); return t; }
export function _play(t, choice) { mPlay(t, choice, null); return t; }

// What `me` cannot see dealt again: the opponent's hand and deck reshuffled together (its discard
// pile is public), and `me`'s own deck.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const pool = shuffleInPlace(rng, O.hand.concat(O.deck));
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffleInPlace(rng, P.deck);
  t.seed = (rng() * 4294967296) >>> 0; // future reshuffles unknown too
  return t;
}
