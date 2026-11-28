// 32 Hidden contracts. A unit board with no life: points come only from two face-down contracts
// each player holds; a contract whose condition is true at the start of its owner's turn is
// revealed and scores. First to 10. Units attack enemy units only.
// Pure from the outside: act() clones the state.

export const TARGET = 10, MAX_MANA = 10, BOARD = 6, HELD = 2, TURN_CAP = 120;

export const CARDS = {
  STR: { id: 'STR', name: 'Striker', kind: 'unit', cost: 1, atk: 2, hp: 1 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2 },
  GUA: { id: 'GUA', name: 'Guard', kind: 'unit', cost: 2, atk: 2, hp: 3 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 4 },
  HEA: { id: 'HEA', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 5 },
  BIG: { id: 'BIG', name: 'Big', kind: 'unit', cost: 5, atk: 5, hp: 5 },
  HUG: { id: 'HUG', name: 'Huge', kind: 'unit', cost: 6, atk: 6, hp: 7 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'hit', cost: 1, dmg: 2 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'hit', cost: 2, dmg: 3 },
  H6: { id: 'H6', name: 'Hit 6', kind: 'hit', cost: 4, dmg: 6 },
  COIN: { id: 'COIN', name: 'Coin', kind: 'coin', cost: 0 },
};
export const DECK = { STR: 3, RAI: 3, GUA: 3, LIN: 3, HEA: 3, BIG: 3, HUG: 3, H2: 3, H3: 3, H6: 3 };

// conditions are read at the start of the owner's turn
export const CONTRACTS = {
  CROWD: { id: 'CROWD', name: 'Crowd', pts: 3, text: 'You control 4 or more units', test: (s, me) => s.p[me].board.length >= 4 },
  TOWER: { id: 'TOWER', name: 'Tower', pts: 2, text: 'You control a unit with 6 or more health', test: (s, me) => s.p[me].board.some(u => u.hp >= 6) },
  CLEAN: { id: 'CLEAN', name: 'Clean', pts: 3, text: 'The opponent controls no units', test: (s, me) => s.p[1 - me].board.length === 0 },
  MORE: { id: 'MORE', name: 'More', pts: 2, text: 'You control more units than the opponent', test: (s, me) => s.p[me].board.length > s.p[1 - me].board.length },
  HUNTER: { id: 'HUNTER', name: 'Hunter', pts: 2, text: 'You destroyed 2 or more enemy units during your last turn', test: (s, me) => s.p[me].killsLast >= 2 },
  FORCE: { id: 'FORCE', name: 'Force', pts: 3, text: "Your units' total attack is 10 or more", test: (s, me) => s.p[me].board.reduce((a, u) => a + u.atk, 0) >= 10 },
  SPREAD: { id: 'SPREAD', name: 'Spread', pts: 2, text: 'You control units of 3 different costs', test: (s, me) => new Set(s.p[me].board.map(u => CARDS[u.card].cost)).size >= 3 },
  PATIENCE: { id: 'PATIENCE', name: 'Patience', pts: 2, text: 'You hold 6 or more cards in hand', test: (s, me) => s.p[me].hand.length >= 6 },
};
export const CONTRACT_IDS = Object.keys(CONTRACTS);

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// contracts: held (face-down to the opponent), cdeck (the contract deck), revealed (scored, public),
// buried (paid away face-down: hidden from the opponent)
function newPlayer() { return { points: 0, mana: 0, maxMana: 0, hand: [], deck: deckList(), board: [], contracts: [], cdeck: CONTRACT_IDS.slice(), revealed: [], buried: [], killsLast: 0, kills: 0 }; }
const cu = (u) => ({ uid: u.uid, card: u.card, atk: u.atk, hp: u.hp, max: u.max, ready: u.ready });
export function clone(s) {
  return { seed: s.seed, turnNo: s.turnNo, turn: s.turn, toAct: s.toAct, first: s.first, winner: s.winner, capped: s.capped, uid: s.uid, swapped: s.swapped,
    p: s.p.map(p => ({ points: p.points, mana: p.mana, maxMana: p.maxMana, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(cu), contracts: p.contracts.slice(), cdeck: p.cdeck.slice(), revealed: p.revealed.slice(), buried: p.buried.slice(), killsLast: p.killsLast, kills: p.kills })) };
}
function emit(s, ev, e) { if (ev) { e.turnNo = s.turnNo; ev.push(e); } }
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  s.p[1 - side].points += 1; emit(s, ev, { t: 'empty', side, points: s.p[1 - side].points });
}
function drawContract(s, side, ev) { const p = s.p[side]; if (p.contracts.length < HELD && p.cdeck.length) { p.contracts.push(p.cdeck.shift()); emit(s, ev, { t: 'cdraw', side }); } }

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toAct: 0, first: 0, winner: null, capped: false, uid: 1, swapped: false, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) { shuffleInPlace(s, p.deck); shuffleInPlace(s, p.cdeck); }
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (const side of [0, 1]) for (let i = 0; i < HELD; i++) drawContract(s, side, null);
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < 4; i++) draw(s, 1 - s.first, null);
  s.p[1 - s.first].hand.push('COIN');
  s.turn = s.toAct = s.first;
  startTurn(s, null);
  return s;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].points >= TARGET, b = s.p[1].points >= TARGET;
  let w = null;
  if (a || b) w = a && b ? (s.p[0].points === s.p[1].points ? 'draw' : s.p[0].points > s.p[1].points ? 0 : 1) : a ? 0 : 1;
  else if (s.p.every(p => !p.contracts.length && !p.cdeck.length)) w = s.p[0].points === s.p[1].points ? 'draw' : s.p[0].points > s.p[1].points ? 0 : 1;
  if (w === null) return false;
  s.winner = w; emit(s, ev, { t: 'end', winner: w });
  return true;
}
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  s.swapped = false;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  for (const u of p.board) u.ready = true;
  draw(s, side, ev);
  if (checkWin(s, ev)) return;
  // contracts: every held one whose condition holds now scores, then the hand of contracts refills
  const done = p.contracts.filter(c => CONTRACTS[c].test(s, side));
  for (const c of done) { p.contracts.splice(p.contracts.indexOf(c), 1); p.revealed.push(c); p.points += CONTRACTS[c].pts; emit(s, ev, { t: 'score', side, c, pts: CONTRACTS[c].pts, points: p.points }); }
  for (let i = 0; i < done.length; i++) drawContract(s, side, ev);
  p.killsLast = 0; p.kills = 0;
  checkWin(s, ev);
}

// Actions: { t: 'play', card, tgt } (tgt: an enemy unit's uid, for Hit cards)
//          { t: 'attack', from, to } (own unit uid -> enemy unit uid)
//          { t: 'swap', c } pay 1 mana: bury the held contract c face-down and draw a replacement (once a turn)
//          { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [], seen = new Set();
  for (const id of P.hand) {
    if (seen.has(id)) continue; seen.add(id);
    const c = CARDS[id];
    if (c.cost > P.mana) continue;
    if (c.kind === 'unit') { if (P.board.length < BOARD) out.push({ t: 'play', card: id }); }
    else if (c.kind === 'coin') out.push({ t: 'play', card: id });
    else for (const u of O.board) out.push({ t: 'play', card: id, tgt: u.uid });
  }
  for (const u of P.board) if (u.ready && u.atk > 0) for (const d of O.board) out.push({ t: 'attack', from: u.uid, to: d.uid });
  if (!s.swapped && P.mana >= 1 && P.cdeck.length) for (const c of new Set(P.contracts)) out.push({ t: 'swap', c });
  out.push({ t: 'end' });
  return out;
}
export const actionKey = (a) => a.t === 'play' ? 'p' + a.card + (a.tgt ? ':' + a.tgt : '') : a.t === 'attack' ? 'a' + a.from + '>' + a.to : a.t === 'swap' ? 's' + a.c : 'e';

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) {
      emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1);
      if (side !== s.turn) s.p[s.turn].kills++;
    }
  }
}
function hit(s, side, u, n, ev) { u.hp -= n; emit(s, ev, { t: 'hit', side, uid: u.uid, n, hp: u.hp }); }

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  if (a.t === 'end') return mEndTurn(s, ev);
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    const c = CARDS[a.card], k = P.hand.indexOf(a.card);
    if (k < 0 || c.cost > P.mana) throw new Error('illegal play ' + a.card);
    if (c.kind === 'unit' && P.board.length >= BOARD) throw new Error('board full');
    let tu = null;
    if (c.kind === 'hit') { tu = O.board.find(u => u.uid === a.tgt); if (!tu) throw new Error('bad target'); }
    P.mana -= c.cost; P.hand.splice(k, 1);
    emit(s, ev, { t: 'play', side: me, card: a.card, tgt: a.tgt, mana: P.mana });
    if (c.kind === 'unit') { const u = { uid: s.uid++, card: a.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false }; P.board.push(u); emit(s, ev, { t: 'summon', side: me, uid: u.uid }); }
    else if (c.kind === 'coin') { P.mana += 1; emit(s, ev, { t: 'coin', side: me, mana: P.mana }); }
    else { hit(s, 1 - me, tu, c.dmg, ev); sweep(s, ev); }
  } else if (a.t === 'attack') {
    const u = P.board.find(x => x.uid === a.from), d = O.board.find(x => x.uid === a.to);
    if (!u || !u.ready || !d) throw new Error('illegal attack');
    u.ready = false;
    emit(s, ev, { t: 'attack', side: me, uid: u.uid, to: d.uid });
    const back = d.atk;
    hit(s, 1 - me, d, u.atk, ev);
    if (back > 0) hit(s, me, u, back, ev);
    sweep(s, ev);
  } else if (a.t === 'swap') {
    const k = P.contracts.indexOf(a.c);
    if (s.swapped || P.mana < 1 || k < 0 || !P.cdeck.length) throw new Error('illegal swap');
    P.mana -= 1; s.swapped = true;
    P.contracts.splice(k, 1); P.buried.push(a.c);
    emit(s, ev, { t: 'swap', side: me, mana: P.mana });
    drawContract(s, me, ev);
  } else throw new Error('unknown action');
  checkWin(s, ev);
}
function mEndTurn(s, ev) {
  emit(s, ev, { t: 'endturn', side: s.turn });
  s.p[s.turn].killsLast = s.p[s.turn].kills;
  if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = s.toAct = 1 - s.turn;
  startTurn(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
