// 03 Exert to score: a points race to 20. A unit scores by exerting; only exerted units can be
// challenged, so scoring (or challenging) leaves a unit open through the opponent's next turn.
// Pure from the outside: act() clones the state. Every decision is one action, ending the turn included.

export const TARGET = 20, MAX_MANA = 10, BOARD = 6, TURN_LIMIT = 120;

export const CARDS = {
  RUN: { id: 'RUN', name: 'Runner', kind: 'Unit', cost: 1, str: 1, hp: 1, sc: 1 },
  SCO: { id: 'SCO', name: 'Scout', kind: 'Unit', cost: 2, str: 1, hp: 3, sc: 2 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'Unit', cost: 2, str: 3, hp: 2, sc: 0 },
  GUA: { id: 'GUA', name: 'Guard', kind: 'Unit', cost: 3, str: 2, hp: 5, sc: 1 },
  LIN: { id: 'LIN', name: 'Line', kind: 'Unit', cost: 3, str: 3, hp: 3, sc: 2 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'Unit', cost: 4, str: 4, hp: 5, sc: 2 },
  BIG: { id: 'BIG', name: 'Big', kind: 'Unit', cost: 5, str: 5, hp: 6, sc: 2 },
  STA: { id: 'STA', name: 'Star', kind: 'Unit', cost: 6, str: 3, hp: 6, sc: 4 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'Hit', cost: 1, dmg: 2 },
  H4: { id: 'H4', name: 'Hit 4', kind: 'Hit', cost: 3, dmg: 4 },
  D2: { id: 'D2', name: 'Draw 2', kind: 'Draw', cost: 2 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'Coin', cost: 0 },
};
export const DECK = { RUN: 3, SCO: 3, RAI: 3, GUA: 3, LIN: 3, HEA: 3, BIG: 2, STA: 2, H2: 3, H4: 2, D2: 3 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleWith(r, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { pts: 0, mana: 0, maxMana: 0, dry: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(m => ({ ...m })) })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  p.dry++; const n = 2 * p.dry; s.p[1 - side].pts += n; emit(s, ev, { t: 'dry', side, n });
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, p: [newPlayer(), newPlayer()] };
  const r = () => rand(s);
  for (const p of s.p) shuffleWith(r, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].pts >= TARGET, b = s.p[1].pts >= TARGET;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 0 : 1;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  for (const m of p.board) { m.ex = false; m.fresh = false; }
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  draw(s, side, ev);
  checkWin(s, ev);
}

// Actions: { t: 'play', card, target? {side, i} } · { t: 'score', i } · { t: 'chal', i, j } · { t: 'end' }
export const canAct = (m) => !m.ex && !m.fresh;
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'Unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'Hit') { for (const side of [0, 1]) s.p[side].board.forEach((_, i) => out.push({ t: 'play', card: id, target: { side, i } })); }
    else out.push({ t: 'play', card: id });
  }
  P.board.forEach((m, i) => {
    if (!canAct(m)) return;
    out.push({ t: 'score', i });
    O.board.forEach((d, j) => { if (d.ex) out.push({ t: 'chal', i, j }); });
  });
  out.push({ t: 'end' });
  return out;
}

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}
function hit(s, side, i, n, ev) { const m = s.p[side].board[i]; m.hp -= n; emit(s, ev, { t: 'hit', side, uid: m.uid, n, hp: m.hp }); }

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'end') {
    if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
    s.turn = 1 - me; startTurn(s, ev); return;
  }
  if (a.t === 'play') {
    const c = CARDS[a.card];
    if (!P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, target: a.target, tuid: a.target ? s.p[a.target.side].board[a.target.i].uid : null });
    if (c.kind === 'Unit') {
      if (P.board.length >= BOARD) throw new Error('board full');
      const m = { uid: UID++, card: a.card, str: c.str, hp: c.hp, max: c.hp, sc: c.sc, ex: false, fresh: true };
      P.board.push(m); emit(s, ev, { t: 'summon', side: me, uid: m.uid });
    } else if (c.kind === 'Coin') { P.mana += 1; }
    else if (c.kind === 'Draw') { draw(s, me, ev); draw(s, me, ev); }
    else { const { side, i } = a.target; if (!s.p[side].board[i]) throw new Error('bad target'); hit(s, side, i, c.dmg, ev); sweep(s, ev); }
  } else if (a.t === 'score') {
    const m = P.board[a.i];
    if (!m || !canAct(m)) throw new Error('illegal score');
    m.ex = true; P.pts += m.sc;
    emit(s, ev, { t: 'score', side: me, uid: m.uid, n: m.sc, pts: P.pts });
  } else if (a.t === 'chal') {
    const m = P.board[a.i], d = O.board[a.j];
    if (!m || !canAct(m) || !d || !d.ex) throw new Error('illegal challenge');
    m.ex = true;
    emit(s, ev, { t: 'chal', side: me, uid: m.uid, tuid: d.uid });
    const ds = d.str; hit(s, 1 - me, a.j, m.str, ev); hit(s, me, a.i, ds, ev); sweep(s, ev);
  } else throw new Error('unknown action');
  checkWin(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

// What the mover cannot see, redrawn: the opponent's hand and deck pooled and redealt, own deck reshuffled.
export function determinize(s, me, r) {
  const t = clone(s), O = t.p[1 - me];
  const pool = shuffleWith(r, O.hand.concat(O.deck));
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffleWith(r, t.p[me].deck);
  return t;
}
// An action described by what it does, so identical units or copies are one choice.
const sig = (m) => m.card + m.hp + (m.ex ? 'x' : '');
export function actionKey(s, a) {
  const P = s.p[s.turn], O = s.p[1 - s.turn];
  if (a.t === 'end') return 'e';
  if (a.t === 'play') return 'p' + a.card + (a.target ? (a.target.side === s.turn ? 'o' : 'h') + sig(s.p[a.target.side].board[a.target.i]) : '');
  if (a.t === 'score') return 's' + sig(P.board[a.i]);
  return 'c' + sig(P.board[a.i]) + '>' + sig(O.board[a.j]);
}
