// 33 Time track: no turns. Whoever is behind on a shared time track (0-60) takes the next action;
// on a shared space the marker that arrived last acts. Every action costs time: a card its time
// cost, an attack 1, a draw 2. Units recover on the same clock. Life 20; at 60/60 higher life wins.
// Pure from the outside: act() clones the state.

export const END = 60, LIFE = 20, BOARD = 6, HAND = 8, ENTER = 3;

export const CARDS = {
  QUI: { id: 'QUI', name: 'Quick', kind: 'Unit', time: 2, atk: 2, hp: 1, rec: 2 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'Unit', time: 3, atk: 3, hp: 2, rec: 3 },
  GUA: { id: 'GUA', name: 'Guard', kind: 'Unit', time: 3, atk: 1, hp: 5, rec: 4 },
  LIN: { id: 'LIN', name: 'Line', kind: 'Unit', time: 5, atk: 3, hp: 4, rec: 3 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'Unit', time: 7, atk: 5, hp: 6, rec: 4 },
  SLO: { id: 'SLO', name: 'Slow', kind: 'Unit', time: 9, atk: 7, hp: 8, rec: 5 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'Hit', time: 3, dmg: 3 },
  H6: { id: 'H6', name: 'Hit 6', kind: 'Hit', time: 6, dmg: 6 },
  HAS: { id: 'HAS', name: 'Haste', kind: 'Haste', time: 1 },
};
export const DECK = { QUI: 3, RAI: 3, GUA: 3, LIN: 3, HEA: 3, SLO: 2, H3: 3, H6: 2, HAS: 2 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleWith(r, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { pos: 0, life: LIFE, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }

// Who acts: the marker further behind; on the same space, the one on top; nobody on 60 acts.
function whoActs(s) {
  const a = s.p[0].pos, b = s.p[1].pos;
  if (a >= END && b >= END) return null;
  if (a >= END) return 1; if (b >= END) return 0;
  return a < b ? 0 : b < a ? 1 : s.top;
}
function settle(s, ev) {
  if (s.winner !== null) return;
  const d0 = s.p[0].life <= 0, d1 = s.p[1].life <= 0;
  if (d0 || d1) { s.winner = d0 && d1 ? 'draw' : d0 ? 1 : 0; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  const w = whoActs(s);
  if (w === null) {
    const a = s.p[0].life, b = s.p[1].life;
    s.winner = a > b ? 0 : b > a ? 1 : 'draw'; s.timeout = true; emit(s, ev, { t: 'end', winner: s.winner }); return;
  }
  s.turn = w;
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, n: 0, turn: 0, top: 0, first: 0, winner: null, p: [newPlayer(), newPlayer()] };
  const r = () => rand(s);
  for (const p of s.p) { shuffleWith(r, p.deck); for (let i = 0; i < 4; i++) p.hand.push(p.deck.shift()); }
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  s.top = s.first; s.turn = s.first;
  return s;
}

export const isReady = (s, side, m) => s.p[side].pos >= m.readyAt;
// Actions: { t: 'play', card, target? {side, i} (i = -1: the player) } · { t: 'atk', i, j } (j = -1: the player)
//          { t: 'draw' } · { t: 'wait' } (forward 1, only when nothing else is legal)
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'Hit') {
      out.push({ t: 'play', card: id, target: { side: 1 - me, i: -1 } });
      for (const side of [0, 1]) s.p[side].board.forEach((_, i) => out.push({ t: 'play', card: id, target: { side, i } }));
    } else P.board.forEach((_, i) => out.push({ t: 'play', card: id, target: { side: me, i } }));
  }
  P.board.forEach((m, i) => { if (isReady(s, me, m)) { out.push({ t: 'atk', i, j: -1 }); O.board.forEach((_, j) => out.push({ t: 'atk', i, j })); } });
  if (P.deck.length && P.hand.length < HAND) out.push({ t: 'draw' });
  if (!out.length) out.push({ t: 'wait' });
  return out;
}

function move(s, side, n, ev) {
  const P = s.p[side], O = s.p[1 - side];
  const from = P.pos; P.pos = Math.min(END, P.pos + n);
  if (P.pos === O.pos) s.top = side;
  emit(s, ev, { t: 'move', side, from, to: P.pos });
}
function hit(s, side, i, n, ev) {
  if (i < 0) { s.p[side].life -= n; emit(s, ev, { t: 'hit', side, i, n, hp: s.p[side].life }); return; }
  const m = s.p[side].board[i]; m.hp -= n; emit(s, ev, { t: 'hit', side, i, n, hp: m.hp, uid: m.uid });
}
function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  s.n++;
  if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card)) throw new Error('illegal play ' + a.card);
    P.hand.splice(P.hand.indexOf(a.card), 1);
    const tuid = a.target && a.target.i >= 0 ? s.p[a.target.side].board[a.target.i].uid : null;
    emit(s, ev, { t: 'play', side: me, card: a.card, target: a.target, tuid });
    move(s, me, c.time, ev);
    if (c.kind === 'Unit') {
      if (P.board.length >= BOARD) throw new Error('board full');
      const m = { uid: UID++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, rec: c.rec, readyAt: P.pos + ENTER };
      P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    } else if (c.kind === 'Hit') {
      const { side, i } = a.target;
      if (i >= 0 && !s.p[side].board[i]) throw new Error('bad target');
      if (i < 0 && side === me) throw new Error('bad target');
      hit(s, side, i, c.dmg, ev); sweep(s, ev);
    } else {
      const m = P.board[a.target.i]; if (!m || a.target.side !== me) throw new Error('bad target');
      m.readyAt = P.pos; emit(s, ev, { t: 'haste', side: me, uid: m.uid });
    }
  } else if (a.t === 'atk') {
    const m = P.board[a.i];
    if (!m || !isReady(s, me, m)) throw new Error('illegal attack');
    const tuid = a.j >= 0 ? O.board[a.j].uid : null;
    if (a.j >= 0 && !O.board[a.j]) throw new Error('bad target');
    emit(s, ev, { t: 'atk', side: me, uid: m.uid, j: a.j, tuid });
    move(s, me, 1, ev);
    m.readyAt = P.pos + m.rec;
    if (a.j < 0) hit(s, 1 - me, -1, m.atk, ev);
    else { const d = O.board[a.j], da = d.atk; hit(s, 1 - me, a.j, m.atk, ev); hit(s, me, a.i, da, ev); }
    sweep(s, ev);
  } else if (a.t === 'draw') {
    if (!P.deck.length || P.hand.length >= HAND) throw new Error('illegal draw');
    P.hand.push(P.deck.shift()); emit(s, ev, { t: 'draw', side: me });
    move(s, me, 2, ev);
  } else if (a.t === 'wait') { move(s, me, 1, ev); }
  else throw new Error('unknown action');
  settle(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

export function determinize(s, me, r) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffleWith(r, O.hand.concat(O.deck));
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffleWith(r, t.p[me].deck);
  return t;
}
const sig = (s, side, m) => m.card + m.hp + ':' + Math.max(0, m.readyAt - s.p[side].pos);
export function actionKey(s, a) {
  const me = s.turn;
  if (a.t === 'draw' || a.t === 'wait') return a.t;
  if (a.t === 'play') return 'p' + a.card + (a.target ? (a.target.side === me ? 'o' : 'h') + (a.target.i < 0 ? 'P' : sig(s, a.target.side, s.p[a.target.side].board[a.target.i])) : '');
  return 'a' + sig(s, me, s.p[me].board[a.i]) + '>' + (a.j < 0 ? 'P' : sig(s, 1 - me, s.p[1 - me].board[a.j]));
}
