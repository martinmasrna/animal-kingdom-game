// 24 Rally. Tennis points from a deck of shots: a return needs Reach at least the incoming shot's
// Pace, every shot costs stamina (10 a game), first to 4 points takes a game, first to 3 games the
// match. The server of a game serves all its points; it alternates every game.
// Pure from the outside: act() clones the state.

export const HAND = 5, STAMINA = 10, POINTS = 4, GAMES = 3;
// The one rule changed after the gate (see report.json): the serve passes to the other player after
// every point, not every game. Under the spec's rule the server loses long rallies by card count
// (it plays shots 1, 3, 5, 7, 9 and has no 11th), so the player serving three of five games loses
// the match 77% of the time against itself. false restores the spec's rule.
export let SERVE_EVERY_POINT = true;
export function setServeRule(v) { SERVE_EVERY_POINT = v; }

export const CARDS = {
  PUS: { id: 'PUS', name: 'Push', cost: 0, pace: 1, reach: 2 },
  DRI: { id: 'DRI', name: 'Drive', cost: 1, pace: 3, reach: 3 },
  SLI: { id: 'SLI', name: 'Slice', cost: 1, pace: 2, reach: 4 },
  LOB: { id: 'LOB', name: 'Lob', cost: 1, pace: 2, reach: 5 },
  DIG: { id: 'DIG', name: 'Dig', cost: 2, pace: 1, reach: 6 },
  SMA: { id: 'SMA', name: 'Smash', cost: 3, pace: 5, reach: 3 },
  ACE: { id: 'ACE', name: 'Ace', cost: 4, pace: 6, reach: 2 },
};
export const DECK = { PUS: 4, DRI: 4, SLI: 3, LOB: 2, DIG: 2, SMA: 3, ACE: 2 };

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { stamina: STAMINA, points: 0, games: 0, hand: [], deck: deckList(), discard: [] }; }
export function clone(s) {
  return { seed: s.seed, turnNo: s.turnNo, first: s.first, server: s.server, toAct: s.toAct, winner: s.winner, capped: s.capped, gameNo: s.gameNo,
    rally: s.rally.slice(), p: s.p.map(p => ({ stamina: p.stamina, points: p.points, games: p.games, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice() })) };
}
function emit(s, ev, e) { if (ev) { e.turnNo = s.turnNo; ev.push(e); } }
function drawUp(s, side, ev) {
  const p = s.p[side];
  while (p.hand.length < HAND) {
    if (!p.deck.length) { if (!p.discard.length) return; p.deck = shuffleInPlace(s, p.discard); p.discard = []; emit(s, ev, { t: 'reshuffle', side }); }
    p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side });
  }
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, first: 0, server: 0, toAct: 0, winner: null, capped: false, gameNo: 1, rally: [], p: [newPlayer(), newPlayer()] };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  s.server = s.toAct = s.first;
  for (const side of [0, 1]) drawUp(s, side, null);
  return s;
}

// the last shot of this point, or null before the serve
export const lastShot = (s) => s.rally.length ? s.rally[s.rally.length - 1] : null;
// a shot card may be played now: affordable, and (unless serving) its Reach at least the incoming Pace
export function canPlay(s, id) {
  const P = s.p[s.toAct], c = CARDS[id], l = lastShot(s);
  return c.cost <= P.stamina && (!l || c.reach >= CARDS[l.card].pace);
}

// Actions: { t: 'shot', card }   { t: 'concede' } (let the incoming shot go and lose the point)
// A side that has no legal shot loses the point at once, so there is always a shot to choose.
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.toAct], out = [];
  for (const id of new Set(P.hand)) if (canPlay(s, id)) out.push({ t: 'shot', card: id });
  if (s.rally.length) out.push({ t: 'concede' });
  return out;
}
export const actionKey = (a) => a.t === 'shot' ? 's' + a.card : 'c';

// the point goes to `side`: played shots to their discard piles, both draw up to 5; 4 points take
// the game (stamina back to 10, the other side serves next), 3 games the match
function pointTo(s, side, ev) {
  const W = s.p[side], L = s.p[1 - side];
  W.points++;
  emit(s, ev, { t: 'point', side, points: [s.p[0].points, s.p[1].points] });
  for (const r of s.rally) s.p[r.side].discard.push(r.card);
  s.rally = [];
  if (W.points >= POINTS) {
    W.games++; W.points = 0; L.points = 0;
    emit(s, ev, { t: 'game', side, games: [s.p[0].games, s.p[1].games] });
    if (W.games >= GAMES) { s.winner = side; emit(s, ev, { t: 'end', winner: side }); return; }
    s.gameNo++;
    if (!SERVE_EVERY_POINT) s.server = 1 - s.server;
    for (const p of s.p) p.stamina = STAMINA;
  }
  if (SERVE_EVERY_POINT) s.server = 1 - s.server;
  for (const x of [0, 1]) drawUp(s, x, ev);
  s.toAct = s.server;
  // a server with nothing it can pay for loses the point at once
  if (!s.p[s.server].hand.some(id => CARDS[id].cost <= s.p[s.server].stamina)) { emit(s, ev, { t: 'noserve', side: s.server }); pointTo(s, 1 - s.server, ev); }
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.toAct, P = s.p[me];
  s.turnNo++;
  if (a.t === 'concede') {
    if (!s.rally.length) throw new Error('the server must serve');
    emit(s, ev, { t: 'concede', side: me });
    return pointTo(s, 1 - me, ev);
  }
  const k = P.hand.indexOf(a.card);
  if (k < 0 || !canPlay(s, a.card)) throw new Error('illegal shot ' + a.card);
  P.hand.splice(k, 1); P.stamina -= CARDS[a.card].cost;
  s.rally.push({ card: a.card, side: me });
  emit(s, ev, { t: 'shot', side: me, card: a.card, serve: s.rally.length === 1, stamina: P.stamina });
  s.toAct = 1 - me;
  // a side with no legal return loses the point at once
  if (!legalActions(s).some(x => x.t === 'shot')) { emit(s, ev, { t: 'noreturn', side: s.toAct }); pointTo(s, me, ev); }
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
