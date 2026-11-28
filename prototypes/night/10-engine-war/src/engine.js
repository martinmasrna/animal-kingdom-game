// Engine war. A deckbuilder with a face-up market row of five. Points come only from Posts on
// the table, each yielding its points at the start of its owner's turn; the opponent shoots Posts
// with damage. First to 20 at the start of a turn wins; when the market deck runs out the round is
// finished and the higher score wins.
// Pure from the outside: act() clones the state; _act() mutates (for the bots' play-outs).

export const TARGET = 20, ROW = 5, HAND = 5, TURN_LIMIT = 120;

export const CARDS = {
  COIN: { id: 'COIN', name: 'Coin', cost: 0, coin: 1 },
  SHOT: { id: 'SHOT', name: 'Shot', cost: 0, dmg: 1 },
  COIN2: { id: 'COIN2', name: 'Coin 2', cost: 3, coin: 2 },
  SHOT2: { id: 'SHOT2', name: 'Shot 2', cost: 3, dmg: 2 },
  SHOT4: { id: 'SHOT4', name: 'Shot 4', cost: 6, dmg: 4 },
  DRAW: { id: 'DRAW', name: 'Draw', cost: 4, coin: 1, draw: 2 },
  SPOST: { id: 'SPOST', name: 'Small Post', cost: 3, post: true, hp: 3, yld: 1 },
  POST: { id: 'POST', name: 'Post', cost: 5, post: true, hp: 5, yld: 2 },
  BPOST: { id: 'BPOST', name: 'Big Post', cost: 8, post: true, hp: 7, yld: 3 },
  WPOST: { id: 'WPOST', name: 'Wall Post', cost: 4, post: true, hp: 6, yld: 0, wall: true },
  TRASH: { id: 'TRASH', name: 'Trash', cost: 2, trash: true },
};
export const START = { COIN: 7, SHOT: 3 };
export const MARKET = { COIN2: 6, SHOT2: 5, SHOT4: 3, DRAW: 4, SPOST: 5, POST: 5, BPOST: 3, WPOST: 3, TRASH: 2 };

const list = (o) => { const out = []; for (const [id, k] of Object.entries(o)) for (let i = 0; i < k; i++) out.push(id); return out; };
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { points: 0, deck: list(START), hand: [], discard: [], played: [], posts: [], coin: 0, dmg: 0, trash: 0 }; }
export function clone(s) {
  return { ...s, mdeck: s.mdeck.slice(), row: s.row.slice(), p: s.p.map(p => ({ ...p, deck: p.deck.slice(), hand: p.hand.slice(), discard: p.discard.slice(), played: p.played.slice(), posts: p.posts.map(x => ({ ...x })) })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.turnNo; ev.push(e); } }

// Draw one card, shuffling the discard into a new deck when the deck is empty.
function drawOne(s, side, ev) {
  const p = s.p[side];
  if (!p.deck.length) { if (!p.discard.length) return null; p.deck = shuffleInPlace(s, p.discard); p.discard = []; emit(s, ev, { t: 'reshuffle', side }); }
  const c = p.deck.shift(); p.hand.push(c); return c;
}

export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, capped: false, lastTurn: -1, mdeck: list(MARKET), row: [], p: [newPlayer(), newPlayer()] };
  shuffleInPlace(s, s.mdeck);
  for (const p of s.p) shuffleInPlace(s, p.deck);
  for (let i = 0; i < ROW; i++) s.row.push(s.mdeck.shift());
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) drawOne(s, s.first, null);
  for (let i = 0; i < HAND; i++) drawOne(s, 1 - s.first, null);
  s.turn = s.first;
  startTurn(s, null);
  return s;
}

function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  emit(s, ev, { t: 'turn', side });
  const y = p.posts.reduce((a, x) => a + CARDS[x.card].yld, 0);
  if (y) { p.points += y; emit(s, ev, { t: 'yield', side, n: y, points: p.points }); }
  if (p.points >= TARGET) { s.winner = side; emit(s, ev, { t: 'end', winner: side }); return; }
  p.trash = p.hand.filter(c => c === 'TRASH').length;
  if (!p.trash) playHand(s, ev);
}
// Play every card in hand (a Draw plays the two cards it draws; a Trash drawn that way waits for its choice).
function playHand(s, ev) {
  const side = s.turn, p = s.p[side];
  while (p.hand.length) {
    const id = p.hand.shift(), c = CARDS[id];
    if (c.trash) { p.played.push(id); p.trash++; continue; } // drawn while playing: its choice comes next
    if (c.post) { const x = { uid: UID++, card: id, hp: c.hp }; p.posts.push(x); emit(s, ev, { t: 'post', side, card: id, uid: x.uid }); continue; }
    p.played.push(id);
    if (c.coin) p.coin += c.coin;
    if (c.dmg) p.dmg += c.dmg;
    emit(s, ev, { t: 'play', side, card: id });
    if (c.draw) for (let k = 0; k < c.draw; k++) drawOne(s, side, ev);
  }
}
const wallUp = (P) => P.posts.some(x => CARDS[x.card].wall);
export const phase = (s) => s.p[s.turn].trash > 0 ? 'trash' : 'buy';

// Actions: { t: 'trash', from: 'hand'|'discard', card } or { t: 'trash', card: null } (keep all),
// { t: 'buy', i } (row index), { t: 'shoot', i } (enemy Post index), { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const me = s.turn, P = s.p[me], O = s.p[1 - me], out = [];
  if (P.trash > 0) {
    const handNow = P.hand.slice(); const ti = handNow.indexOf('TRASH'); if (ti >= 0) handNow.splice(ti, 1);
    for (const id of new Set(handNow)) out.push({ t: 'trash', from: 'hand', card: id });
    for (const id of new Set(P.discard)) out.push({ t: 'trash', from: 'discard', card: id });
    out.push({ t: 'trash', card: null });
    return out;
  }
  s.row.forEach((id, i) => { if (id && CARDS[id].cost <= P.coin) out.push({ t: 'buy', i }); });
  const wall = wallUp(O);
  O.posts.forEach((x, i) => { if (x.hp <= P.dmg && (!wall || CARDS[x.card].wall)) out.push({ t: 'shoot', i }); });
  out.push({ t: 'end' });
  return out;
}

function endTurn(s, ev) {
  const me = s.turn, P = s.p[me];
  P.discard.push(...P.played, ...P.hand); P.played = []; P.hand = []; P.coin = 0; P.dmg = 0;
  for (let k = 0; k < HAND; k++) drawOne(s, me, null);
  if (s.lastTurn >= 0 && s.turnNo >= s.lastTurn) {
    const a = s.p[0].points, b = s.p[1].points;
    s.winner = a === b ? 'draw' : a > b ? 0 : 1; emit(s, ev, { t: 'end', winner: s.winner, by: 'market' }); return;
  }
  if (s.turnNo >= TURN_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  s.turn = 1 - s.turn;
  startTurn(s, ev);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'trash') {
    if (P.trash <= 0) throw new Error('no trash pending');
    const ti = P.hand.indexOf('TRASH');
    if (ti >= 0) { P.hand.splice(ti, 1); P.played.push('TRASH'); }
    P.trash--;
    if (a.card) {
      const pile = a.from === 'hand' ? P.hand : P.discard, i = pile.indexOf(a.card);
      if (i < 0) throw new Error('nothing to trash');
      pile.splice(i, 1);
      if (a.card === 'TRASH' && a.from === 'hand') P.trash--;
      emit(s, ev, { t: 'trash', side: me, card: a.card, from: a.from });
    }
    if (P.trash <= 0) { P.trash = 0; playHand(s, ev); }
    return;
  }
  if (P.trash > 0) throw new Error('trash first');
  if (a.t === 'end') { endTurn(s, ev); return; }
  if (a.t === 'buy') {
    const id = s.row[a.i];
    if (!id || CARDS[id].cost > P.coin) throw new Error('illegal buy');
    P.coin -= CARDS[id].cost; P.discard.push(id);
    s.row[a.i] = s.mdeck.length ? s.mdeck.shift() : null;
    emit(s, ev, { t: 'buy', side: me, card: id, i: a.i, coin: P.coin, refill: s.row[a.i] });
    if (!s.mdeck.length && s.lastTurn < 0) {
      // the market deck has run out: finish the round so both players have had the same number of turns
      s.lastTurn = me === s.first ? s.turnNo + 1 : s.turnNo;
      emit(s, ev, { t: 'marketout', lastTurn: s.lastTurn });
    }
    return;
  }
  if (a.t === 'shoot') {
    const x = O.posts[a.i];
    if (!x || x.hp > P.dmg || (wallUp(O) && !CARDS[x.card].wall)) throw new Error('illegal shoot');
    P.dmg -= x.hp; O.posts.splice(a.i, 1); O.discard.push(x.card);
    emit(s, ev, { t: 'shoot', side: me, i: a.i, uid: x.uid, card: x.card, dmg: P.dmg });
    return;
  }
  throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

export function key(s) {
  const P = s.p[s.turn];
  return JSON.stringify([s.turn, s.winner, s.row, s.p.map(p => [p.points, p.coin, p.dmg, p.trash, p.posts.map(x => x.card).sort(), p.discard.slice().sort().join()]), P.hand.slice().sort()]);
}
// Everything the mover cannot see dealt again: the opponent's hand and deck together, the mover's
// own deck, the market deck.
export function determinize(s, me, rng) {
  const t = clone(s), O = t.p[1 - me], P = t.p[me];
  const pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(P.deck, rng); shuffle(t.mdeck, rng);
  t.seed = (rng() * 4294967296) >>> 0; // future reshuffles unknown too
  return t;
}
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
