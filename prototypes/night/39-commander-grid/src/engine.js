// 39 Commander grid. A 5x6 grid; each side has a Commander that fights too; units deploy next to
// it, then move and strike orthogonally (a piece may move and then attack in one turn). Kill the enemy Commander. From round 15 each Commander
// takes growing damage at the start of its turn, so the game ends.
// Pure from the outside: act() clones the state.

export const COLS = 5, ROWS = 6, MAX_MANA = 8, CMD_HP = 15, CMD_ATK = 2, BLEED_FROM = 15, TURN_CAP = 80;
// The one rule changed after the gate (see report.json): a piece may move and then attack in the
// same turn. Under the spec's rule (move OR attack) a piece that steps next to an enemy is hit first
// by everything around it, so nobody approaches and the round-15 damage, which reaches the first
// player's Commander first, decides 96% of Expert games. false restores the spec's rule.
export const MOVE_THEN_ATTACK = true;

export const CARDS = {
  CMD: { id: 'CMD', name: 'Commander', kind: 'cmd', cost: 0, atk: CMD_ATK, hp: CMD_HP },
  PAW: { id: 'PAW', name: 'Pawn', kind: 'unit', cost: 1, atk: 1, hp: 2 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2 },
  GUA: { id: 'GUA', name: 'Guard', kind: 'unit', cost: 2, atk: 1, hp: 5 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 3, move: 2 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 5 },
  LAN: { id: 'LAN', name: 'Lancer', kind: 'unit', cost: 4, atk: 3, hp: 3, lance: true },
  H3: { id: 'H3', name: 'Hit 3', kind: 'hit', cost: 2, dmg: 3, range: 2 },
  RAL: { id: 'RAL', name: 'Rally', kind: 'rally', cost: 1 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0 },
};
export const DECK = { PAW: 4, RAI: 4, GUA: 3, LIN: 3, HEA: 3, LAN: 2, H3: 3, RAL: 2 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export const rc = (cell) => [Math.floor(cell / COLS), cell % COLS];
export const cellOf = (r, c) => r * COLS + c;
export const dist = (a, b) => { const [r1, c1] = rc(a), [r2, c2] = rc(b); return Math.abs(r1 - r2) + Math.abs(c1 - c2); };
const NB = []; // orthogonal neighbours of every cell
for (let i = 0; i < COLS * ROWS; i++) { const [r, c] = rc(i), n = []; if (r > 0) n.push(i - COLS); if (r < ROWS - 1) n.push(i + COLS); if (c > 0) n.push(i - 1); if (c < COLS - 1) n.push(i + 1); NB.push(n); }
export const neighbours = (cell) => NB[cell];
// cells exactly 2 away in a straight line (the Lancer's reach)
const LN = [];
for (let i = 0; i < COLS * ROWS; i++) { const [r, c] = rc(i), n = []; for (const [dr, dc] of [[2, 0], [-2, 0], [0, 2], [0, -2]]) { const R = r + dr, C = c + dc; if (R >= 0 && R < ROWS && C >= 0 && C < COLS) n.push(cellOf(R, C)); } LN.push(n); }
export const lanceCells = (cell) => LN[cell];

function newPlayer() { return { mana: 0, maxMana: 0, hand: [], deck: deckList() }; }
const cp = (u) => ({ uid: u.uid, card: u.card, side: u.side, atk: u.atk, hp: u.hp, max: u.max, cell: u.cell, acted: u.acted, moved: u.moved, fresh: u.fresh });
export function clone(s) {
  return { seed: s.seed, turnNo: s.turnNo, turn: s.turn, toAct: s.toAct, first: s.first, winner: s.winner, capped: s.capped, uid: s.uid,
    p: s.p.map(p => ({ mana: p.mana, maxMana: p.maxMana, hand: p.hand.slice(), deck: p.deck.slice() })), pieces: s.pieces.map(cp) };
}
function emit(s, ev, e) { if (ev) { e.turnNo = s.turnNo; ev.push(e); } }
function draw(s, side, ev) { const p = s.p[side]; if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); } }
export const cmdOf = (s, side) => s.pieces.find(u => u.card === 'CMD' && u.side === side);
export const pieceAt = (s, cell) => s.pieces.find(u => u.cell === cell) || null;
export const pieceById = (s, uid) => s.pieces.find(u => u.uid === uid) || null;
export function occupancy(s) { const g = new Array(COLS * ROWS).fill(null); for (const u of s.pieces) g[u.cell] = u; return g; }
export const round = (s) => Math.ceil(s.turnNo / 2);

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toAct: 0, first: 0, winner: null, capped: false, uid: 3, p: [newPlayer(), newPlayer()], pieces: [] };
  s.pieces.push({ uid: 1, card: 'CMD', side: 0, atk: CMD_ATK, hp: CMD_HP, max: CMD_HP, cell: cellOf(0, 2), acted: false, moved: false, fresh: false });
  s.pieces.push({ uid: 2, card: 'CMD', side: 1, atk: CMD_ATK, hp: CMD_HP, max: CMD_HP, cell: cellOf(ROWS - 1, 2), acted: false, moved: false, fresh: false });
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.toAct = s.first;
  startTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = cmdOf(s, 0).hp <= 0, b = cmdOf(s, 1).hp <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const u of s.pieces) if (u.side === side) { u.acted = false; u.moved = false; u.fresh = false; }
  const r = round(s);
  if (r >= BLEED_FROM) { const c = cmdOf(s, side), n = r - BLEED_FROM + 1; c.hp -= n; emit(s, ev, { t: 'bleed', side, uid: c.uid, n, hp: c.hp }); }
  draw(s, side, ev);
  checkWin(s, ev);
}

// the cells a piece may move to: 1 step to an empty cell (Line: up to 2 steps through empty cells)
export function moveCells(s, u, occ = occupancy(s)) {
  const steps = CARDS[u.card].move || 1, out = new Set();
  let frontier = [u.cell];
  for (let k = 0; k < steps; k++) {
    const next = [];
    for (const c of frontier) for (const n of NB[c]) if (!occ[n] && !out.has(n)) { out.add(n); next.push(n); }
    frontier = next;
  }
  return [...out];
}
// the enemy pieces a piece may attack: orthogonally adjacent ones; the Lancer: exactly 2 away in a line
export function attackTargets(s, u, occ = occupancy(s)) {
  const out = [];
  for (const c of CARDS[u.card].lance ? LN[u.cell] : NB[u.cell]) { const d = occ[c]; if (d && d.side !== u.side) out.push(d.uid); }
  return out;
}
// acted: it has attacked (or, under the spec's rule, done anything); moved: it has moved
export const canAct = (u) => !u.acted && !u.fresh;
export const canMove = (u) => !u.acted && !u.moved && !u.fresh;
export const hasActed = (u) => u.acted || u.moved;
export function deployCells(s, side, occ = occupancy(s)) { return NB[cmdOf(s, side).cell].filter(c => !occ[c]); }

// Actions: { t: 'play', card, cell } a unit onto an empty cell next to your Commander
//          { t: 'play', card: 'H3', tgt } 3 damage to an enemy piece within 2 cells of your Commander
//          { t: 'play', card: 'RAL', tgt } one of your pieces that has acted may act again
//          { t: 'play', card: 'COIN' }
//          { t: 'move', from, to } (to: a cell)   { t: 'attack', from, to } (to: an enemy piece's uid)
//          a piece may move, then attack; attacking ends its turn
//          { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], out = [], occ = occupancy(s), seen = new Set();
  const myCmd = cmdOf(s, me);
  for (const id of P.hand) {
    if (seen.has(id)) continue; seen.add(id);
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'unit') for (const cell of NB[myCmd.cell]) { if (!occ[cell]) out.push({ t: 'play', card: id, cell }); }
    else if (c.kind === 'hit') { for (const u of s.pieces) if (u.side !== me && dist(u.cell, myCmd.cell) <= c.range) out.push({ t: 'play', card: id, tgt: u.uid }); }
    else if (c.kind === 'rally') { for (const u of s.pieces) if (u.side === me && hasActed(u)) out.push({ t: 'play', card: id, tgt: u.uid }); }
    else out.push({ t: 'play', card: id });
  }
  for (const u of s.pieces) if (u.side === me && canAct(u)) {
    for (const to of attackTargets(s, u, occ)) out.push({ t: 'attack', from: u.uid, to });
    if (canMove(u)) for (const to of moveCells(s, u, occ)) out.push({ t: 'move', from: u.uid, to });
  }
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'play' ? 'p' + a.card + ':' + (a.cell ?? a.tgt ?? '') : a.t === 'end' ? 'e' : a.t[0] + a.from + '>' + a.to;

function sweep(s, ev) {
  for (let i = s.pieces.length - 1; i >= 0; i--) { const u = s.pieces[i]; if (u.hp <= 0 && u.card !== 'CMD') { emit(s, ev, { t: 'die', side: u.side, uid: u.uid, card: u.card, cell: u.cell }); s.pieces.splice(i, 1); } }
}
function hit(s, u, n, ev) { u.hp -= n; emit(s, ev, { t: 'hit', side: u.side, uid: u.uid, n, hp: u.hp }); }

function mAct(s, a, ev, trust = false) {
  if (s.winner !== null) throw new Error('match over');
  if (a.t === 'end') return mEndTurn(s, ev);
  const me = s.turn, P = s.p[me];
  if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    const myCmd = cmdOf(s, me);
    let tu = null;
    if (c.kind === 'unit') { if (!NB[myCmd.cell].includes(a.cell) || pieceAt(s, a.cell)) throw new Error('bad cell'); }
    else if (c.kind === 'hit') { tu = pieceById(s, a.tgt); if (!tu || tu.side === me || dist(tu.cell, myCmd.cell) > c.range) throw new Error('bad target'); }
    else if (c.kind === 'rally') { tu = pieceById(s, a.tgt); if (!tu || tu.side !== me || !hasActed(tu)) throw new Error('bad rally'); }
    P.mana -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, cell: a.cell, tgt: a.tgt, mana: P.mana });
    if (c.kind === 'unit') {
      const u = { uid: s.uid++, card: a.card, side: me, atk: c.atk, hp: c.hp, max: c.hp, cell: a.cell, acted: false, moved: false, fresh: true };
      s.pieces.push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid, cell: a.cell });
    } else if (c.kind === 'hit') { hit(s, tu, c.dmg, ev); sweep(s, ev); }
    else if (c.kind === 'rally') { tu.acted = false; tu.moved = false; emit(s, ev, { t: 'rally', side: me, uid: tu.uid }); }
    else { P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
  } else if (a.t === 'move') {
    const u = pieceById(s, a.from);
    if (!trust && (!u || u.side !== me || !canMove(u) || !moveCells(s, u).includes(a.to))) throw new Error('illegal move');
    emit(s, ev, { t: 'move', side: me, uid: u.uid, from: u.cell, to: a.to });
    u.cell = a.to; u.moved = true; if (!MOVE_THEN_ATTACK) u.acted = true;
  } else if (a.t === 'attack') {
    const u = pieceById(s, a.from);
    if (!trust && (!u || u.side !== me || !canAct(u) || !attackTargets(s, u).includes(a.to))) throw new Error('illegal attack');
    const d = pieceById(s, a.to);
    u.acted = true;
    emit(s, ev, { t: 'attack', side: me, uid: u.uid, to: d.uid, lance: !!CARDS[u.card].lance });
    const back = d.atk;
    hit(s, d, u.atk, ev);
    if (!CARDS[u.card].lance && back > 0) hit(s, u, back, ev);
    sweep(s, ev);
  } else throw new Error('unknown action');
  checkWin(s, ev);
}
function mEndTurn(s, ev) {
  emit(s, ev, { t: 'endturn', side: s.turn });
  if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toAct = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
// the bots' own fast path: their actions come from legalActions or the fixed rules, so the
// move and attack checks are skipped
export function _act(t, a) { mAct(t, a, null, true); return t; }
