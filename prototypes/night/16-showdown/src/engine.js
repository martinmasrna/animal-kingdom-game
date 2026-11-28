// 16 Showdown. Each round both players secretly buy a line of up to 3 cards from a hand of 5 with
// 6 mana; the mana each spent is then shown, and they bet chips (their life) on whose line has
// more power. Pure from the outside: act() clones the state; step() mutates it.
// The buy is simultaneous: the round's lead buys first, hidden, then the other; no bot reads the
// opponent's line, and the spends become public only when both have bought.

export const CHIPS = 20, HAND = 5, LINE = 3, MANA = 6, BET = 2, ROUNDS = 20;
export const ante = (round) => round >= 11 ? 3 : round >= 6 ? 2 : 1;

export const CARDS = {
  LO: { id: 'LO', name: 'Low', cost: 0, power: 1 },
  MI: { id: 'MI', name: 'Mid', cost: 1, power: 3 },
  HI: { id: 'HI', name: 'High', cost: 2, power: 5 },
  TO: { id: 'TO', name: 'Top', cost: 4, power: 9 },
  BL: { id: 'BL', name: 'Bluff', cost: 3, power: 0 },
  MR: { id: 'MR', name: 'Mirror', cost: 2, power: null, text: 'Power equal to the opponent\'s highest card that is not a Mirror.' },
  SP: { id: 'SP', name: 'Spike', cost: 1, power: 2, text: 'If your line wins at showdown, the opponent also pays you 2 chips.' },
  SO: { id: 'SO', name: 'Solo', cost: 0, power: 4, text: 'Power 0 unless it is the only card in your line.' },
};
export const DECK = { LO: 4, MI: 4, HI: 4, TO: 3, BL: 3, MR: 2, SP: 2, SO: 2 };
export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// a card's power in a line, against the opponent's line (Solo alone, Mirror copying)
function basePower(id, line) { if (id === 'SO') return line.length === 1 ? 4 : 0; if (id === 'MR') return null; return CARDS[id].power; }
export function linePower(line, other) {
  let oppHigh = 0;
  for (const id of other) { const p = basePower(id, other); if (p !== null && p > oppHigh) oppHigh = p; }
  let t = 0;
  for (const id of line) { const p = basePower(id, line); t += p === null ? oppHigh : p; }
  return t;
}
export const lineCost = (line) => line.reduce((t, id) => t + CARDS[id].cost, 0);

// p.contrib: chips this player has put in the pot this round; p.raised: has raised this round;
// p.line / p.spent: this round's line and its cost (null until bought); p.unseen: cards in its
// discard pile the opponent never saw (folded lines)
function newPlayer() { return { chips: CHIPS, hand: [], deck: deckList(), discard: [], unseen: [], line: null, spent: null, contrib: 0, raised: false }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), unseen: p.unseen.slice(), line: p.line && p.line.slice() })), last: s.last && { ...s.last } };
}
function emit(s, ev, e) { if (ev) ev.push(e); }

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, turnNo: 0, first: 0, lead: 0, toMove: 0, phase: 'buy', winner: null, pot: 0, checks: 0, last: null, p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  startRound(s, null);
  return s;
}
function finishGame(s, w, ev) { if (s.winner === null) { s.winner = w; s.phase = 'over'; emit(s, ev, { t: 'end', winner: w }); } }
function drawUp(s, side, ev) {
  const p = s.p[side];
  while (p.hand.length < HAND) {
    if (!p.deck.length) { if (!p.discard.length) break; p.deck = shuffleInPlace(s, p.discard); p.discard = []; p.unseen = []; emit(s, ev, { t: 'reshuffle', side }); }
    p.hand.push(p.deck.shift());
  }
}
function startRound(s, ev) {
  s.round++; s.turnNo++;
  if (s.round > ROUNDS) { const a = s.p[0].chips, b = s.p[1].chips; return finishGame(s, a === b ? 'draw' : a > b ? 0 : 1, ev); }
  const A = ante(s.round), broke = [0, 1].filter(k => s.p[k].chips < A);
  if (broke.length) return finishGame(s, broke.length === 2 ? 'draw' : 1 - broke[0], ev);
  s.lead = (s.first + s.round - 1) % 2;
  s.pot = 0; s.checks = 0;
  for (const k of [0, 1]) { const p = s.p[k]; p.chips -= A; p.contrib = A; s.pot += A; p.line = null; p.spent = null; p.raised = false; drawUp(s, k, ev); }
  s.phase = 'buy'; s.toMove = s.lead;
  emit(s, ev, { t: 'round', round: s.round, lead: s.lead, ante: A });
}

// Actions: { t: 'buy', line: [ids] }  { t: 'check' }  { t: 'bet' }  { t: 'call' }  { t: 'raise' }  { t: 'fold' }
export function key(a) { return a.t === 'buy' ? 'buy:' + a.line.slice().sort().join(',') : a.t; }
const facing = (s) => s.p[1 - s.toMove].contrib - s.p[s.toMove].contrib;
function subMultiset(pick, pool) { const left = pool.slice(); for (const c of pick) { const k = left.indexOf(c); if (k < 0) return false; left.splice(k, 1); } return true; }
export function isLegal(s, a) {
  if (s.winner !== null || !a) return false;
  const P = s.p[s.toMove];
  if (s.phase === 'buy') return a.t === 'buy' && Array.isArray(a.line) && a.line.length <= LINE && subMultiset(a.line, P.hand) && lineCost(a.line) <= MANA;
  if (s.phase !== 'bet') return false;
  const f = facing(s);
  if (f === 0) return a.t === 'check' || (a.t === 'bet' && P.chips >= BET);
  if (a.t === 'call' || a.t === 'fold') return true;
  if (a.t === 'raise') return !P.raised && P.chips >= f + BET;
  return false;
}
// every distinct line a hand can buy (up to 3 cards, cost at most 6)
export function lines(hand) {
  const ids = [...new Set(hand)].sort(), cnt = ids.map(id => hand.filter(x => x === id).length), out = [];
  const rec = (k, cur) => {
    if (k === ids.length) { if (lineCost(cur) <= MANA) out.push(cur.slice()); return; }
    for (let take = 0; take <= cnt[k] && cur.length + take <= LINE; take++) { for (let j = 0; j < take; j++) cur.push(ids[k]); rec(k + 1, cur); cur.length -= take; }
  };
  rec(0, []);
  return out;
}
export function legalActions(s) {
  if (s.winner !== null) return [];
  if (s.phase === 'buy') return lines(s.p[s.toMove].hand).map(line => ({ t: 'buy', line }));
  return ['check', 'bet', 'call', 'raise', 'fold'].map(t => ({ t })).filter(a => isLegal(s, a));
}

function put(s, side, n) { const p = s.p[side]; n = Math.min(n, p.chips); p.chips -= n; p.contrib += n; s.pot += n; return n; }
function settle(s, winner, how, ev) {
  // a short call: what the caller could not match goes back to the other
  const [a, b] = [s.p[0].contrib, s.p[1].contrib];
  if (a !== b) { const hi = a > b ? 0 : 1, d = Math.abs(a - b); s.p[hi].chips += d; s.p[hi].contrib -= d; s.pot -= d; }
  const P0 = linePower(s.p[0].line, s.p[1].line), P1 = linePower(s.p[1].line, s.p[0].line);
  let spike = 0;
  if (winner === 'show') {
    winner = P0 === P1 ? 'split' : P0 > P1 ? 0 : 1;
    if (winner !== 'split') { const L = s.p[1 - winner]; spike = Math.min(L.chips, 2 * s.p[winner].line.filter(x => x === 'SP').length); L.chips -= spike; s.p[winner].chips += spike; }
  }
  const pot = s.pot;
  if (winner === 'split') { const second = 1 - s.lead, half = Math.floor(pot / 2); s.p[1 - second].chips += half; s.p[second].chips += pot - half; }
  else s.p[winner].chips += pot;
  s.last = { how, winner, pot, spike, lines: [s.p[0].line, s.p[1].line], power: [P0, P1], shown: how === 'show', folder: how === 'fold' ? 1 - winner : null };
  emit(s, ev, { t: 'settle', ...s.last });
  for (const k of [0, 1]) {
    const p = s.p[k];
    p.discard.push(...p.line);
    if (how === 'fold' && k === s.last.folder) p.unseen.push(...p.line);
  }
  s.pot = 0;
  const out = [0, 1].filter(k => s.p[k].chips <= 0);
  if (out.length) return finishGame(s, out.length === 2 ? 'draw' : 1 - out[0], ev);
  startRound(s, ev);
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a) + ' in ' + s.phase);
  const me = s.toMove, P = s.p[me];
  emit(s, ev, { t: 'act', side: me, a: a.t === 'buy' ? { t: 'buy', n: a.line.length } : a });
  if (s.phase === 'buy') {
    P.line = a.line.slice(); P.spent = lineCost(a.line);
    for (const id of a.line) P.hand.splice(P.hand.indexOf(id), 1);
    if (s.p[1 - me].line === null) { s.toMove = 1 - me; return; }
    s.phase = 'bet'; s.toMove = s.lead; s.turnNo++;
    emit(s, ev, { t: 'spent', spent: [s.p[0].spent, s.p[1].spent] });
    return;
  }
  const f = facing(s);
  if (a.t === 'check') { s.checks++; if (s.checks >= 2) return settle(s, 'show', 'show', ev); s.toMove = 1 - me; return; }
  if (a.t === 'bet') { put(s, me, BET); s.toMove = 1 - me; return; }
  if (a.t === 'raise') { put(s, me, f + BET); P.raised = true; s.toMove = 1 - me; return; }
  if (a.t === 'call') { put(s, me, f); return settle(s, 'show', 'show', ev); }
  if (a.t === 'fold') return settle(s, 1 - me, 'fold', ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
