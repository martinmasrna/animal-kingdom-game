// 29 Hidden runner: asymmetric. The Runner moves secretly on a 4x4 grid, announcing only the kind
// of move, and is shown at the end of rounds 3, 6 and 9; the Hunter's two visible pawns search and
// corner it. Both sides play costed move cards from their own 12-card decks.
// The engine keeps `poss`, the nodes the Runner could be on given everything public, so a Hunter
// (bot or page) reads only that, never `runner`. Pure from the outside: act() clones the state.

export const N = 4, ROUNDS = 12, REVEALS = [3, 6, 9], ECAP = 5, EGAIN = 2;
// The one rule changed after the first gate: Sprint reaches 2, not 3 (see report.json).
export const SPRINT = 2;
const rc = (n) => [Math.floor(n / N), n % N];
const at = (r, c) => (r >= 0 && r < N && c >= 0 && c < N) ? r * N + c : -1;
export const ADJ = [], DIAG = [], DIST = [];
for (let n = 0; n < N * N; n++) {
  const [r, c] = rc(n);
  ADJ[n] = [at(r - 1, c), at(r + 1, c), at(r, c - 1), at(r, c + 1)].filter(x => x >= 0);
  DIAG[n] = [at(r - 1, c - 1), at(r - 1, c + 1), at(r + 1, c - 1), at(r + 1, c + 1)].filter(x => x >= 0);
  DIST[n] = []; for (let m = 0; m < N * N; m++) { const [a, b] = rc(m); DIST[n][m] = Math.abs(a - r) + Math.abs(b - c); }
}
const DIRS = [[-1, 0], [1, 0], [0, -1], [0, 1]];

export const RCARDS = {
  STEP: { id: 'STEP', name: 'Step', cost: 0, text: 'Move 1 or stay.' },
  DASH: { id: 'DASH', name: 'Dash', cost: 1, text: 'Move 1 or 2 in a straight line.' },
  SLIP: { id: 'SLIP', name: 'Slip', cost: 1, text: 'Move 1 diagonally.' },
  HIDE: { id: 'HIDE', name: 'Hide', cost: 1, text: 'Stay; Searches this round answer no.' },
  SMOK: { id: 'SMOK', name: 'Smoke', cost: 2, text: 'Move 1 or stay; skip the next reveal.' },
  DOUB: { id: 'DOUB', name: 'Double', cost: 2, text: 'Step twice.' },
};
export const HCARDS = {
  SPR: { id: 'SPR', name: 'Sprint', cost: 1, text: 'One pawn moves up to 2 instead of 1.' },
  SEA: { id: 'SEA', name: 'Search', cost: 1, text: 'Name a node: is the Runner on it or next to it?' },
  FLA: { id: 'FLA', name: 'Flare', cost: 3, text: 'The Runner is shown now.' },
  BLO: { id: 'BLO', name: 'Block', cost: 1, text: 'Block a node for 3 rounds.' },
};
export const RDECK = { DASH: 4, SLIP: 3, HIDE: 2, SMOK: 1, DOUB: 2 };
export const HDECK = { SPR: 4, SEA: 4, FLA: 2, BLO: 2 };

const list = (m) => { const out = []; for (const [id, k] of Object.entries(m)) for (let i = 0; i < k; i++) out.push(id); return out; };
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleWith(r, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
export const bits = (mask) => { const out = []; for (let n = 0; n < N * N; n++) if (mask & (1 << n)) out.push(n); return out; };

export function clone(s) {
  return { ...s, pawns: s.pawns.slice(), moved: s.moved.slice(), blocks: s.blocks.map(b => ({ ...b })), R: { ...s.R, hand: s.R.hand.slice(), deck: s.R.deck.slice() }, H: { ...s.H, hand: s.H.hand.slice(), deck: s.H.deck.slice() }, kinds: s.kinds.slice() };
}
function emit(s, ev, e) { if (ev) ev.push(e); }

// seatR plays the Runner (seat 0 or 1); the other seat hunts.
export function newMatch({ seed, seatR = 0 } = {}) {
  const s = { seed: (seed >>> 0) || 1, round: 0, phase: 'start', seatR, turn: seatR, first: seatR, winner: null, runner: -1, pawns: [at(N - 1, 0), at(N - 1, N - 1)], moved: [false, false], cardUsed: false,
    blocks: [], hide: false, skip: false, poss: 0, kinds: [], lastSeen: null, search: null,
    R: { energy: 2, hand: [], deck: list(RDECK) }, H: { energy: 2, hand: [], deck: list(HDECK) } };
  const r = () => rand(s);
  for (const P of [s.R, s.H]) { shuffleWith(r, P.deck); for (let i = 0; i < 3; i++) P.hand.push(P.deck.shift()); }
  for (let c = 0; c < N; c++) s.poss |= 1 << at(0, c);
  return s;
}
export const roleOf = (s, seat) => seat === s.seatR ? 'R' : 'H';
const blocked = (s, n) => s.blocks.some(b => b.node === n);
const free = (s, n) => !s.pawns.includes(n) && !blocked(s, n);

// Where a Runner on n can end with a card of this kind (given pawns and blocks now).
export function reach(s, n, kind) {
  const out = new Set();
  const step = (m) => { const o = [m]; for (const x of ADJ[m]) if (free(s, x)) o.push(x); return o; };
  if (kind === 'STEP' || kind === 'SMOK') step(n).forEach(x => out.add(x));
  else if (kind === 'HIDE') out.add(n);
  else if (kind === 'SLIP') DIAG[n].forEach(x => { if (free(s, x)) out.add(x); });
  else if (kind === 'DOUB') step(n).forEach(x => step(x).forEach(y => out.add(y)));
  else if (kind === 'DASH') {
    const [r, c] = rc(n);
    for (const [dr, dc] of DIRS) { const a = at(r + dr, c + dc); if (a < 0 || !free(s, a)) continue; out.add(a); const b = at(r + 2 * dr, c + 2 * dc); if (b >= 0 && free(s, b)) out.add(b); }
  }
  return [...out];
}
const pawnReach = (s, p, k) => { const out = []; for (let n = 0; n < N * N; n++) if (DIST[s.pawns[p]][n] <= k) out.push(n); return out; };

// Actions. Runner: { t: 'start', to } · { t: 'run', card, to } (card 'STEP' is the free basic move)
// Hunter: { t: 'move', pawn, to } · { t: 'card', card: 'SPR', pawn, to } · { t: 'card', card: 'SEA', node }
//         { t: 'card', card: 'FLA' } · { t: 'card', card: 'BLO', node } · { t: 'done' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const out = [];
  if (s.phase === 'start') { for (let c = 0; c < N; c++) out.push({ t: 'start', to: at(0, c) }); return out; }
  if (s.phase === 'run') {
    const kinds = ['STEP', ...new Set(s.R.hand.filter(id => RCARDS[id].cost <= s.R.energy))];
    for (const k of kinds) for (const to of reach(s, s.runner, k)) out.push({ t: 'run', card: k, to });
    return out;
  }
  for (let p = 0; p < 2; p++) if (!s.moved[p]) for (const to of [s.pawns[p], ...ADJ[s.pawns[p]]]) out.push({ t: 'move', pawn: p, to });
  if (!s.cardUsed) for (const id of new Set(s.H.hand)) {
    if (HCARDS[id].cost > s.H.energy) continue;
    if (id === 'SPR') { for (let p = 0; p < 2; p++) if (!s.moved[p]) for (const to of pawnReach(s, p, SPRINT)) if (DIST[s.pawns[p]][to] >= 2) out.push({ t: 'card', card: id, pawn: p, to }); }
    else if (id === 'FLA') out.push({ t: 'card', card: id });
    else for (let n = 0; n < N * N; n++) out.push({ t: 'card', card: id, node: n });
  }
  out.push({ t: 'done' });
  return out;
}

function startRound(s, ev) {
  s.round++;
  for (const P of [s.R, s.H]) { P.energy = Math.min(ECAP, P.energy + EGAIN); if (P.deck.length) P.hand.push(P.deck.shift()); }
  s.hide = false; s.search = null; s.phase = 'run'; s.turn = s.seatR;
  emit(s, ev, { t: 'round', round: s.round });
}
function landPawn(s, p, to, ev) {
  s.pawns[p] = to; s.moved[p] = true;
  emit(s, ev, { t: 'pawn', pawn: p, to });
  if (to === s.runner) { s.winner = 1 - s.seatR; emit(s, ev, { t: 'caught', node: to }); emit(s, ev, { t: 'end', winner: s.winner }); return; }
  s.poss &= ~(1 << to);
}
function show(s, why, ev) { s.poss = 1 << s.runner; s.lastSeen = { node: s.runner, round: s.round }; emit(s, ev, { t: 'show', node: s.runner, why }); }
function endRound(s, ev) {
  if (REVEALS.includes(s.round)) { if (s.skip) { s.skip = false; emit(s, ev, { t: 'smoked' }); } else show(s, 'reveal', ev); }
  s.blocks = s.blocks.filter(b => b.until > s.round);
  if (s.round >= ROUNDS) { s.winner = s.seatR; s.timeout = true; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startRound(s, ev);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (s.phase === 'start') {
    if (a.t !== 'start' || Math.floor(a.to / N) !== 0) throw new Error('bad start');
    s.runner = a.to; emit(s, ev, { t: 'start' });
    startRound(s, ev); return;
  }
  if (s.phase === 'run') {
    if (a.t !== 'run') throw new Error('bad run');
    const c = RCARDS[a.card];
    if (a.card !== 'STEP' && (!s.R.hand.includes(a.card) || c.cost > s.R.energy)) throw new Error('cannot play ' + a.card);
    const prevPoss = bits(s.poss);
    if (!reach(s, s.runner, a.card).includes(a.to)) throw new Error('bad destination');
    if (a.card !== 'STEP') { s.R.energy -= c.cost; s.R.hand.splice(s.R.hand.indexOf(a.card), 1); }
    if (a.card === 'HIDE') s.hide = true;
    if (a.card === 'SMOK') s.skip = true;
    s.runner = a.to;
    let poss = 0; for (const n of prevPoss) for (const m of reach(s, n, a.card)) poss |= 1 << m;
    s.poss = poss; s.kinds.push(a.card);
    emit(s, ev, { t: 'run', card: a.card, to: a.to });
    s.phase = 'hunt'; s.turn = 1 - s.seatR; s.moved = [false, false]; s.cardUsed = false;
    return;
  }
  // the Hunter
  if (a.t === 'done') { emit(s, ev, { t: 'done' }); return endRound(s, ev); }
  if (a.t === 'move') {
    if (s.moved[a.pawn] || !(a.to === s.pawns[a.pawn] || ADJ[s.pawns[a.pawn]].includes(a.to))) throw new Error('bad move');
    landPawn(s, a.pawn, a.to, ev);
  } else if (a.t === 'card') {
    const c = HCARDS[a.card];
    if (s.cardUsed || !s.H.hand.includes(a.card) || c.cost > s.H.energy) throw new Error('cannot play ' + a.card);
    s.H.energy -= c.cost; s.H.hand.splice(s.H.hand.indexOf(a.card), 1); s.cardUsed = true;
    emit(s, ev, { t: 'hcard', card: a.card, node: a.node, pawn: a.pawn, to: a.to });
    if (a.card === 'SPR') { if (s.moved[a.pawn] || DIST[s.pawns[a.pawn]][a.to] > SPRINT) throw new Error('bad sprint'); landPawn(s, a.pawn, a.to, ev); }
    else if (a.card === 'FLA') show(s, 'flare', ev);
    else if (a.card === 'BLO') { s.blocks.push({ node: a.node, until: s.round + 3 }); emit(s, ev, { t: 'block', node: a.node }); }
    else if (a.card === 'SEA') {
      const near = a.node === s.runner || ADJ[a.node].includes(s.runner);
      const yes = near && !s.hide;
      let m = 1 << a.node; for (const x of ADJ[a.node]) m |= 1 << x;
      if (!s.hide) s.poss = yes ? (s.poss & m) : (s.poss & ~m);
      s.search = { node: a.node, yes };
      emit(s, ev, { t: 'search', node: a.node, yes });
    }
  } else throw new Error('bad hunter action');
  if (s.winner === null && s.moved[0] && s.moved[1] && s.cardUsed) endRound(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

// What the mover cannot see. The Hunter: where the Runner is (drawn from `poss`) and the Runner's
// cards. The Runner: the Hunter's cards. Both: deck orders.
export function determinize(s, seat, r) {
  const t = clone(s);
  t.seed = (r() * 4294967296) >>> 0;
  const other = roleOf(s, seat) === 'R' ? t.H : t.R;
  const pool = shuffleWith(r, other.hand.concat(other.deck));
  other.hand = pool.slice(0, other.hand.length); other.deck = pool.slice(other.hand.length);
  shuffleWith(r, (roleOf(s, seat) === 'R' ? t.R : t.H).deck);
  if (roleOf(s, seat) === 'H' && t.phase !== 'start') { const P = bits(t.poss); t.runner = P[Math.floor(r() * P.length)]; }
  return t;
}
export function actionKey(s, a) {
  if (a.t === 'start') return 's' + a.to;
  if (a.t === 'run') return a.card + a.to;
  if (a.t === 'move') return 'm' + a.pawn + ':' + a.to;
  if (a.t === 'done') return 'd';
  return a.card + (a.node ?? '') + (a.pawn ?? '') + ':' + (a.to ?? '');
}
