// 25 Range duel: two fighters on a line of spaces 1..7 choose a move at the same time; speed
// decides who acts first, range whether it hits, energy pays. Simultaneous: each turn both sides
// submit one move and the turn resolves when both are in: submit(s, side, a, ev).

export const SPACES = 7, LIFE = 12, ENERGY0 = 3, GAIN = 2, ENERGY_MAX = 6, START_HAND = 4, TURNS = 20, GUARD = 3;
// mv: spaces moved toward (+) or away (-); dir: the mover picks toward or away
export const CARDS = {
  JAB: { id: 'JAB', name: 'Jab', cost: 0, speed: 1, mv: 0, rng: [1, 1], dmg: 1 },
  PUN: { id: 'PUN', name: 'Punch', cost: 1, speed: 2, mv: 1, rng: [1, 1], dmg: 3 },
  KIC: { id: 'KIC', name: 'Kick', cost: 1, speed: 3, mv: 0, rng: [1, 2], dmg: 3 },
  LUN: { id: 'LUN', name: 'Lunge', cost: 2, speed: 3, mv: 2, rng: [1, 1], dmg: 4 },
  SWE: { id: 'SWE', name: 'Sweep', cost: 2, speed: 4, mv: 0, rng: [1, 2], dmg: 3, push: 1 },
  SHO: { id: 'SHO', name: 'Shot', cost: 2, speed: 2, mv: -1, rng: [3, 4], dmg: 2 },
  GUA: { id: 'GUA', name: 'Guard', cost: 1, speed: 1, mv: 0, guard: GUARD },
  STEP: { id: 'STEP', name: 'Step', cost: 0, speed: 3, mv: 1, dir: true, basic: true },
  REST: { id: 'REST', name: 'Rest', cost: 0, speed: 5, mv: 0, rest: 1, basic: true },
};
export const DECK = { JAB: 3, PUN: 3, KIC: 3, LUN: 2, SWE: 2, SHO: 2, GUA: 1 };
export const deckList = () => { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; };

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer(pos) { return { pos, life: LIFE, energy: ENERGY0, rest: 0, hand: [], deck: deckList(), discard: [] }; }
export function clone(s) {
  return { ...s, need: s.need.slice(), moves: s.moves.slice(), last: s.last, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice() })) };
}
function emit(ev, e) { if (ev) ev.push(e); }
function draw1(s, side) {
  const p = s.p[side];
  if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(s, p.discard); p.discard = []; }
  p.hand.push(p.deck.shift());
}
export function newMatch({ seed } = {}) {
  const s = { seed: (seed >>> 0) || 1, turn: 0, need: [true, true], moves: [null, null], winner: null, capped: false, last: null, p: [newPlayer(2), newPlayer(6)] };
  for (const p of s.p) { shuffleInPlace(s, p.deck); for (let i = 0; i < START_HAND; i++) draw1(s, s.p.indexOf(p)); }
  startTurn(s);
  return s;
}
function startTurn(s) {
  s.turn++;
  for (const p of s.p) { p.energy = Math.min(ENERGY_MAX, p.energy + GAIN + p.rest); p.rest = 0; }
  s.need = [true, true]; s.moves = [null, null];
}
export const dist = (s) => Math.abs(s.p[0].pos - s.p[1].pos);

// Actions: { t: 'move', card, dir } — card is a hand card or a basic (STEP, REST); dir is +1 (toward) or -1 (away), for Step only
export function legalActions(s, side) {
  if (s.winner !== null || !s.need[side]) return [];
  const P = s.p[side], out = [{ t: 'move', card: 'STEP', dir: 1 }, { t: 'move', card: 'STEP', dir: -1 }, { t: 'move', card: 'REST' }];
  for (const id of new Set(P.hand)) if (CARDS[id].cost <= P.energy) out.push({ t: 'move', card: id });
  return out;
}
export function canSubmit(s, side, a) {
  if (s.winner !== null || !s.need[side] || !a || a.t !== 'move') return false;
  const c = CARDS[a.card], P = s.p[side];
  if (!c) return false;
  if (!c.basic && !P.hand.includes(a.card)) return false;
  if (c.dir && a.dir !== 1 && a.dir !== -1) return false;
  return c.cost <= P.energy;
}
// where a fighter ends after moving `n` toward (+) or away (-) the other, who stands still
function moved(s, side, n) {
  const me = s.p[side], o = s.p[1 - side], toward = Math.sign(o.pos - me.pos);
  let pos = me.pos + toward * n;
  pos = Math.max(1, Math.min(SPACES, pos));
  if (n > 0) { if (toward > 0) pos = Math.min(pos, o.pos - 1); else pos = Math.max(pos, o.pos + 1); }
  return pos;
}
const moveOf = (a) => { const c = CARDS[a.card]; return c.dir ? c.mv * a.dir : c.mv; };
function mSubmit(s, side, a, ev) {
  if (!canSubmit(s, side, a)) throw new Error('illegal ' + JSON.stringify(a) + ' for ' + side);
  s.moves[side] = { ...a }; s.need[side] = false;
  if (s.need[0] || s.need[1]) return;
  resolve(s, ev);
}
function resolve(s, ev) {
  const mv = s.moves, guard = [0, 0], cancelled = [false, false], hits = [];
  for (const side of [0, 1]) {
    const c = CARDS[mv[side].card], P = s.p[side];
    P.energy -= c.cost;
    if (!c.basic) { P.hand.splice(P.hand.indexOf(c.id), 1); P.discard.push(c.id); }
    if (c.guard) guard[side] = c.guard;
  }
  emit(ev, { t: 'reveal', moves: [{ ...mv[0] }, { ...mv[1] }], pos: [s.p[0].pos, s.p[1].pos] });
  const speeds = [...new Set([CARDS[mv[0].card].speed, CARDS[mv[1].card].speed])].sort((a, b) => a - b);
  for (const sp of speeds) {
    const now = [0, 1].filter(side => CARDS[mv[side].card].speed === sp && !cancelled[side]);
    if (!now.length) continue;
    // movement: one alone moves freely; two at once share the free spaces between them
    if (now.length === 1) { const side = now[0], n = moveOf(mv[side]); if (n) { s.p[side].pos = moved(s, side, n); emit(ev, { t: 'move', side, pos: s.p[side].pos }); } }
    else {
      const n0 = moveOf(mv[0]), n1 = moveOf(mv[1]), free = dist(s) - 1;
      let a0 = n0, a1 = n1;
      if (n0 > 0 && n1 > 0 && n0 + n1 > free) {
        const half = Math.floor(free / 2);
        if (n0 <= half) { a0 = n0; a1 = Math.min(n1, free - n0); }
        else if (n1 <= half) { a1 = n1; a0 = Math.min(n0, free - n1); }
        else a0 = a1 = half;
      }
      // the one moving away goes first so the other can follow into the space it leaves
      const order = a0 < 0 ? [0, 1] : a1 < 0 ? [1, 0] : [0, 1];
      for (const side of order) { const n = side === 0 ? a0 : a1; if (n) { s.p[side].pos = moved(s, side, n); emit(ev, { t: 'move', side, pos: s.p[side].pos }); } }
    }
    // attacks, all at once at this speed
    const d = dist(s), landed = [];
    for (const side of now) {
      const c = CARDS[mv[side].card];
      if (c.rest) { s.p[side].rest = c.rest; continue; }
      if (!c.dmg) continue;
      if (d >= c.rng[0] && d <= c.rng[1]) landed.push(side);
      else emit(ev, { t: 'miss', side, card: c.id });
    }
    for (const side of landed) {
      const c = CARDS[mv[side].card], o = 1 - side, n = Math.max(0, c.dmg - guard[o]);
      s.p[o].life -= n; hits.push({ side, n });
      emit(ev, { t: 'hit', side, target: o, card: c.id, n, life: s.p[o].life });
      if (CARDS[mv[o].card].speed > sp) { cancelled[o] = true; emit(ev, { t: 'cancel', side: o, card: mv[o].card }); }
      if (c.push) { const p0 = s.p[o].pos, away = Math.sign(s.p[o].pos - s.p[side].pos); s.p[o].pos = Math.max(1, Math.min(SPACES, s.p[o].pos + away * c.push)); if (s.p[o].pos !== p0) emit(ev, { t: 'push', side: o, pos: s.p[o].pos }); }
    }
  }
  s.last = { moves: [{ ...mv[0] }, { ...mv[1] }], hits, cancelled };
  for (const side of [0, 1]) draw1(s, side);
  const a = s.p[0].life <= 0, b = s.p[1].life <= 0;
  if (a || b) s.winner = a && b ? 'draw' : a ? 1 : 0;
  else if (s.turn >= TURNS) s.winner = s.p[0].life === s.p[1].life ? 'draw' : s.p[0].life > s.p[1].life ? 0 : 1;
  if (s.winner !== null) { s.need = [false, false]; emit(ev, { t: 'end', winner: s.winner }); return; }
  startTurn(s);
}
export function submit(s, side, a, ev) { const t = clone(s); mSubmit(t, side, a, ev); return t; }
export function _submit(t, side, a) { mSubmit(t, side, a, null); return t; }
export const actionKey = (a) => a.card + (a.dir ? (a.dir > 0 ? '+' : '-') : '');
