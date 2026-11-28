// Junk war: a market deckbuilder where points are scored by playing cards and the main attack is
// pushing Junk into the opponent's deck. Pure from the outside: act() clones the state.

export const TARGET = 25, ROW = 5, HAND = 5, JUNK = 30, TURN_CAP = 200;

export const CARDS = {
  Coin: { id: 'Coin', name: 'Coin', cost: 0, coin: 1 },
  Score: { id: 'Score', name: 'Score', cost: 0, points: 1 },
  Junk: { id: 'Junk', name: 'Junk', cost: 0 },
  Coin2: { id: 'Coin2', name: 'Coin 2', cost: 3, coin: 2 },
  Coin3: { id: 'Coin3', name: 'Coin 3', cost: 6, coin: 3 },
  Score2: { id: 'Score2', name: 'Score 2', cost: 4, points: 2 },
  Score4: { id: 'Score4', name: 'Score 4', cost: 8, points: 4 },
  Draw: { id: 'Draw', name: 'Draw', cost: 3, draw: 2 },
  Foul: { id: 'Foul', name: 'Foul', cost: 3, coin: 1, junkTop: 1 },
  Foul2: { id: 'Foul2', name: 'Foul 2', cost: 5, points: 1, junkDiscard: 2 },
  Purge: { id: 'Purge', name: 'Purge', cost: 3, purge: 2 },
  Clean: { id: 'Clean', name: 'Clean', cost: 2, coin: 1, clean: 1 },
  Thief: { id: 'Thief', name: 'Thief', cost: 5, coin: 2, steal: 1 },
};
export const MARKET = { Coin2: 6, Coin3: 4, Score2: 5, Score4: 3, Draw: 4, Foul: 5, Foul2: 3, Purge: 4, Clean: 4, Thief: 2 };
export const START = { Coin: 7, Score: 3 };

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleIn(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const list = (o) => { const a = []; for (const [id, n] of Object.entries(o)) for (let i = 0; i < n; i++) a.push(id); return a; };

// knownTop: how many cards on top of the deck everyone knows (Junk put there by Foul);
// knownJunk: how many of the hand everyone knows are such Junk.
function newPlayer() { return { points: 0, deck: list(START), hand: [], discard: [], played: [], removed: [], knownTop: 0, knownJunk: 0 }; }
export function clone(s) {
  return { ...s, market: s.market.slice(), row: s.row.slice(), p: s.p.map(p => ({ ...p, deck: p.deck.slice(), hand: p.hand.slice(), discard: p.discard.slice(), played: p.played.slice(), removed: p.removed.slice() })) };
}
function emit(ev, e) { if (ev) ev.push(e); }

function draw(s, side, ev) {
  const P = s.p[side];
  if (!P.deck.length) {
    if (!P.discard.length) return false;
    P.deck = shuffleIn(s, P.discard); P.discard = []; P.knownTop = 0;
    emit(ev, { t: 'reshuffle', side });
  }
  const c = P.deck.shift();
  if (P.knownTop > 0) { P.knownTop--; P.knownJunk++; }
  P.hand.push(c); emit(ev, { t: 'draw', side });
  return true;
}
export function newMatch({ seed, first }) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, toMove: 0, first: 0, winner: null, cap: false, phase: 'play', coin: 0, purgeLeft: 0,
    market: list(MARKET), row: [], junk: JUNK, marketOut: false, p: [newPlayer(), newPlayer()] };
  shuffleIn(s, s.market);
  for (let i = 0; i < ROW; i++) s.row.push(s.market.shift());
  for (const P of s.p) shuffleIn(s, P.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  for (let i = 0; i < 3; i++) draw(s, s.first, null);
  for (let i = 0; i < HAND; i++) draw(s, 1 - s.first, null);
  s.turn = s.toMove = s.first; s.turnNo = 1;
  return s;
}

function score(s, side, n, ev) {
  s.p[side].points += n; emit(ev, { t: 'points', side, n });
  if (s.p[side].points >= TARGET && s.winner === null) { s.winner = side; emit(ev, { t: 'end', winner: side }); }
}

// Actions, by the player to move:
//   play phase:  { t: 'play', card }  (every card in hand must be played; the phase ends when the hand is empty)
//   purge phase: { t: 'purge', card } removes a card from hand, { t: 'stop' } removes no more
//   buy phase:   { t: 'buy', i } (row index), { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn];
  if (s.phase === 'play') return [...new Set(P.hand)].map(card => ({ t: 'play', card }));
  if (s.phase === 'purge') return [...new Set(P.hand)].map(card => ({ t: 'purge', card })).concat([{ t: 'stop' }]);
  const out = [{ t: 'end' }];
  s.row.forEach((id, i) => { if (id && CARDS[id].cost <= s.coin) out.push({ t: 'buy', i }); });
  return out;
}

function afterPlay(s) { if (s.phase === 'play' && !s.p[s.turn].hand.length) s.phase = 'buy'; }
function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  if (a.t === 'play') {
    if (s.phase !== 'play') throw new Error('not the play phase');
    const k = P.hand.indexOf(a.card); if (k < 0) throw new Error('not in hand');
    P.hand.splice(k, 1); P.played.push(a.card);
    if (a.card === 'Junk' && P.knownJunk > 0) P.knownJunk--;
    const c = CARDS[a.card];
    emit(ev, { t: 'play', side: me, card: a.card });
    if (c.coin) { s.coin += c.coin; emit(ev, { t: 'coin', side: me, n: c.coin }); }
    if (c.points) score(s, me, c.points, ev);
    if (c.draw) for (let i = 0; i < c.draw; i++) draw(s, me, ev);
    if (c.junkTop) for (let i = 0; i < c.junkTop && s.junk > 0; i++) { s.junk--; O.deck.unshift('Junk'); O.knownTop++; emit(ev, { t: 'junk', side: 1 - me, where: 'top' }); }
    if (c.junkDiscard) for (let i = 0; i < c.junkDiscard && s.junk > 0; i++) { s.junk--; O.discard.push('Junk'); emit(ev, { t: 'junk', side: 1 - me, where: 'discard' }); }
    if (c.steal) { const n = Math.min(c.steal, O.points); if (n) { O.points -= n; emit(ev, { t: 'points', side: 1 - me, n: -n }); score(s, me, n, ev); } }
    if (c.clean) {
      let k2 = P.hand.indexOf('Junk');
      if (k2 >= 0) { P.hand.splice(k2, 1); if (P.knownJunk > 0) P.knownJunk--; P.removed.push('Junk'); emit(ev, { t: 'remove', side: me, card: 'Junk', from: 'hand' }); }
      else if ((k2 = P.discard.indexOf('Junk')) >= 0) { P.discard.splice(k2, 1); P.removed.push('Junk'); emit(ev, { t: 'remove', side: me, card: 'Junk', from: 'discard' }); }
    }
    if (c.purge && P.hand.length) { s.phase = 'purge'; s.purgeLeft = c.purge; return; }
    afterPlay(s);
    return;
  }
  if (a.t === 'purge' || a.t === 'stop') {
    if (s.phase !== 'purge') throw new Error('not purging');
    if (a.t === 'purge') {
      const k = P.hand.indexOf(a.card); if (k < 0) throw new Error('not in hand');
      P.hand.splice(k, 1); P.removed.push(a.card);
      if (a.card === 'Junk' && P.knownJunk > 0) P.knownJunk--;
      emit(ev, { t: 'remove', side: me, card: a.card, from: 'hand' });
      s.purgeLeft--;
    }
    if (a.t === 'stop' || s.purgeLeft <= 0 || !P.hand.length) { s.phase = 'play'; s.purgeLeft = 0; afterPlay(s); }
    return;
  }
  if (s.phase !== 'buy') throw new Error('not the buy phase');
  if (a.t === 'buy') {
    const id = s.row[a.i];
    if (!id || CARDS[id].cost > s.coin) throw new Error('cannot buy');
    s.coin -= CARDS[id].cost; P.discard.push(id);
    s.row[a.i] = s.market.length ? s.market.shift() : null;
    emit(ev, { t: 'buy', side: me, card: id, i: a.i, refill: s.row[a.i] });
    if (!s.market.length && !s.marketOut) { s.marketOut = true; emit(ev, { t: 'marketOut' }); }
    return;
  }
  if (a.t === 'end') {
    P.discard.push(...P.played); P.played = []; P.discard.push(...P.hand); P.hand = []; P.knownJunk = 0; s.coin = 0;
    for (let i = 0; i < HAND; i++) draw(s, me, ev);
    emit(ev, { t: 'endturn', side: me });
    // the market ran out: the round finishes with the second player's turn
    if (s.marketOut && me === 1 - s.first) {
      const a0 = s.p[0].points, a1 = s.p[1].points;
      s.winner = a0 === a1 ? 'draw' : a0 > a1 ? 0 : 1; emit(ev, { t: 'end', winner: s.winner }); return;
    }
    if (s.turnNo >= TURN_CAP) { s.winner = 'draw'; s.cap = true; emit(ev, { t: 'end', winner: 'draw' }); return; }
    s.turn = s.toMove = 1 - me; s.turnNo++; s.phase = 'play';
    emit(ev, { t: 'turn', side: s.turn });
    if (!s.p[s.turn].hand.length) s.phase = 'buy';
    return;
  }
  throw new Error('unknown action ' + a.t);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
// every card a player owns, wherever it is
export const owned = (P) => P.deck.concat(P.hand, P.discard, P.played);
