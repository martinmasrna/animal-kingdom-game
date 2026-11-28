// 42 Real-time lane: one lane from A's base (0) to B's base (12). Mana flows by the clock and an
// eight-card deck cycles through a hand of four. Time runs in ticks (0.5 s); both players act in
// the same tick and the tick resolves both at once: step(s, [actionA, actionB], ev).

export const LEN = 12, BASE = 20, TICKS = 360, OVERTIME = 120, MANA0 = 5, MANA_MAX = 10, MANA_EVERY = 4, HAND = 4, BLAST_R = 1.5, BLAST_DMG = 8;
export const SPAWN = [0.5, 11.5];
export const DIR = [1, -1];

export const CARDS = {
  RUN: { id: 'RUN', name: 'Runner', kind: 'unit', cost: 2, hp: 4, atk: 1, spd: 1.0, rng: 0.5 },
  GRU: { id: 'GRU', name: 'Grunt', kind: 'unit', cost: 3, hp: 10, atk: 2, spd: 0.5, rng: 0.5 },
  SHO: { id: 'SHO', name: 'Shooter', kind: 'unit', cost: 3, hp: 4, atk: 1, spd: 0.5, rng: 3 },
  BRU: { id: 'BRU', name: 'Brute', kind: 'unit', cost: 4, hp: 14, atk: 3, spd: 0.4, rng: 0.5 },
  TAN: { id: 'TAN', name: 'Tank', kind: 'unit', cost: 5, hp: 30, atk: 1, spd: 0.3, rng: 0.5 },
  SWA: { id: 'SWA', name: 'Swarm', kind: 'unit', cost: 3, hp: 2, atk: 1, spd: 0.8, rng: 0.5, n: 3 },
  BLA: { id: 'BLA', name: 'Blast', kind: 'blast', cost: 3 },
  WAL: { id: 'WAL', name: 'Wall', kind: 'wall', cost: 4, hp: 20, atk: 0, spd: 0, rng: 0 },
};
export const DECK = ['RUN', 'GRU', 'SHO', 'BRU', 'TAN', 'SWA', 'BLA', 'WAL'];

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export function newMatch({ seed } = {}) {
  const s = { seed: (seed >>> 0) || 1, uid: 1, tick: 0, winner: null, capped: false, base: [BASE, BASE], mana: [MANA0, MANA0], queue: [DECK.slice(), DECK.slice()], seen: [[], []], units: [] };
  for (const q of s.queue) shuffleInPlace(s, q);
  return s;
}
export function clone(s) {
  return { ...s, base: s.base.slice(), mana: s.mana.slice(), queue: [s.queue[0].slice(), s.queue[1].slice()], seen: [s.seen[0].slice(), s.seen[1].slice()], units: s.units.map(u => ({ ...u })) };
}
export const hand = (s, side) => s.queue[side].slice(0, HAND);
export const nextCard = (s, side) => s.queue[side][HAND];
const half = (side, x) => side === 0 ? x >= SPAWN[0] && x <= LEN / 2 : x >= LEN / 2 && x <= SPAWN[1];
export const wallSpots = (side) => { const out = []; for (let x = 0.5; x <= 6.0001; x += 0.5) out.push(side === 0 ? x : LEN - x); return out; };
export const blastSpots = () => { const out = []; for (let x = 0.5; x <= 11.5001; x += 0.5) out.push(x); return out; };

// Actions: { t: 'wait' } or { t: 'play', card, x } (x: where a Wall stands or a Blast lands)
export function canPlay(s, side, a) {
  if (!a || a.t !== 'play') return true;
  const c = CARDS[a.card];
  if (!c || !hand(s, side).includes(a.card) || s.mana[side] < c.cost) return false;
  if (c.kind === 'wall') return typeof a.x === 'number' && half(side, a.x);
  if (c.kind === 'blast') return typeof a.x === 'number' && a.x >= 0 && a.x <= LEN;
  return true;
}
export function legalActions(s, side) {
  if (s.winner !== null) return [];
  const out = [{ t: 'wait' }];
  for (const id of hand(s, side)) {
    const c = CARDS[id];
    if (s.mana[side] < c.cost) continue;
    if (c.kind === 'unit') out.push({ t: 'play', card: id });
    else if (c.kind === 'wall') for (const x of wallSpots(side)) out.push({ t: 'play', card: id, x });
    else for (const x of blastSpots()) out.push({ t: 'play', card: id, x });
  }
  return out;
}

function emit(ev, e) { if (ev) ev.push(e); }
function spawn(s, side, c, x, ev) {
  const n = c.n || 1;
  for (let i = 0; i < n; i++) {
    const u = { uid: s.uid++, side, card: c.id, x, hp: c.hp, max: c.hp, atk: c.atk, spd: c.spd, rng: c.rng, wall: c.kind === 'wall' };
    s.units.push(u); emit(ev, { t: 'spawn', side, uid: u.uid, card: c.id });
  }
}
// the tick: mana, both plays, every unit acts, all damage at once
function mStep(s, acts, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (s.tick > 0 && s.tick % MANA_EVERY === 0) for (const side of [0, 1]) s.mana[side] = Math.min(MANA_MAX, s.mana[side] + 1);
  const blasts = [];
  for (const side of [0, 1]) {
    const a = acts[side];
    if (!a || a.t !== 'play') continue;
    if (!canPlay(s, side, a)) throw new Error('illegal play ' + JSON.stringify(a));
    const c = CARDS[a.card], q = s.queue[side];
    s.mana[side] -= c.cost;
    q.splice(q.indexOf(a.card), 1); q.push(a.card); s.seen[side].push(a.card);
    emit(ev, { t: 'play', side, card: a.card, x: a.x });
    if (c.kind === 'blast') blasts.push({ side, x: a.x });
    else spawn(s, side, c, c.kind === 'wall' ? a.x : SPAWN[side], ev);
  }
  const dmgU = new Map(), dmgB = [0, 0];
  for (const b of blasts) for (const u of s.units) if (u.side !== b.side && Math.abs(u.x - b.x) <= BLAST_R + 1e-9) { dmgU.set(u, (dmgU.get(u) || 0) + BLAST_DMG); emit(ev, { t: 'blast', side: b.side, x: b.x, uid: u.uid }); }
  if (blasts.length) for (const b of blasts) emit(ev, { t: 'boom', side: b.side, x: b.x });
  // nearest enemy unit ahead of each side's units, from positions before anyone moves
  const U = s.units, moves = [];
  for (const u of U) {
    if (u.wall) continue;
    const d = DIR[u.side];
    let near = null, nd = Infinity;
    for (const e of U) { if (e.side === u.side) continue; const dist = (e.x - u.x) * d; if (dist >= -1e-9 && dist < nd) { nd = dist; near = e; } }
    if (near && nd <= u.rng + 1e-9) { dmgU.set(near, (dmgU.get(near) || 0) + u.atk); emit(ev, { t: 'atk', uid: u.uid, tgt: near.uid }); continue; }
    const baseDist = d === 1 ? LEN - u.x : u.x;
    if (!near && baseDist <= u.rng + 1e-9) { dmgB[1 - u.side] += u.atk; emit(ev, { t: 'atk', uid: u.uid, base: 1 - u.side }); continue; }
    let nx = u.x + d * u.spd;
    if (near) nx = d === 1 ? Math.min(nx, near.x) : Math.max(nx, near.x);
    nx = Math.min(SPAWN[1], Math.max(SPAWN[0], nx));
    moves.push([u, nx]);
  }
  for (const [u, nx] of moves) u.x = Math.round(nx * 1000) / 1000;
  // two fronts that walked through each other meet halfway
  let fa = -Infinity, fb = Infinity;
  for (const u of U) if (u.side === 0) fa = Math.max(fa, u.x); else fb = Math.min(fb, u.x);
  if (fa > fb + 1e-9) {
    const m = Math.round((fa + fb) / 2 * 1000) / 1000;
    for (const u of U) { if (u.side === 0 && u.x > m && !u.wall) u.x = m; if (u.side === 1 && u.x < m && !u.wall) u.x = m; }
  }
  for (const [u, n] of dmgU) { u.hp -= n; emit(ev, { t: 'hit', uid: u.uid, n }); }
  for (const side of [0, 1]) if (dmgB[side]) { s.base[side] -= dmgB[side]; emit(ev, { t: 'base', side, n: dmgB[side], hp: s.base[side] }); }
  for (let i = U.length - 1; i >= 0; i--) if (U[i].hp <= 0) { emit(ev, { t: 'die', uid: U[i].uid, side: U[i].side }); U.splice(i, 1); }
  s.tick++;
  const a0 = s.base[0] <= 0, a1 = s.base[1] <= 0;
  if (a0 || a1) s.winner = a0 && a1 ? 'draw' : a0 ? 1 : 0;
  else if (s.tick >= TICKS && s.base[0] !== s.base[1]) s.winner = s.base[0] > s.base[1] ? 0 : 1;
  else if (s.tick >= TICKS + OVERTIME) { s.winner = 'draw'; s.capped = true; }
  if (s.winner !== null) emit(ev, { t: 'end', winner: s.winner });
}
export function step(s, acts, ev) { const t = clone(s); mStep(t, acts, ev); return t; }
export function _step(t, acts) { mStep(t, acts, null); return t; }
export const actionKey = (a) => a.t === 'wait' ? 'w' : a.card + (a.x !== undefined ? '@' + a.x : '');
