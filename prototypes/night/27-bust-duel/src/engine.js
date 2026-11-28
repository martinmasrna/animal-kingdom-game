// 27 Bust duel: both players push their luck from their own decks into lines side by side,
// alternating one draw at a time; strain 4 busts a line to 0 power. The higher line hits the other
// for the difference (1 to 5); then each buys one market card with its line's power.
// Pure from the outside: act() clones the state.

export const LIFE = 15, ROUNDS = 15, BUST = 4, MARKET = 5, BUST_COIN = 2;

export const CARDS = {
  S1: { id: 'S1', name: 'Step 1', pow: 1, str: 0, cost: 0 },
  S2: { id: 'S2', name: 'Step 2', pow: 2, str: 0, cost: 0 },
  R3: { id: 'R3', name: 'Risk 3', pow: 3, str: 1, cost: 0 },
  CR: { id: 'CR', name: 'Crack', pow: 0, str: 2, cost: 0 },
  S3: { id: 'S3', name: 'Step 3', pow: 3, str: 0, cost: 3 },
  S4: { id: 'S4', name: 'Step 4', pow: 4, str: 0, cost: 5 },
  B6: { id: 'B6', name: 'Big 6', pow: 6, str: 1, cost: 6 },
  CA: { id: 'CA', name: 'Calm', pow: 1, str: -1, cost: 3 },
  SP: { id: 'SP', name: 'Spoil', pow: 1, str: 0, cost: 4, text: 'On draw: the opponent\'s line gains 1 strain.' },
  PE: { id: 'PE', name: 'Peek', pow: 1, str: 0, cost: 2, text: 'On draw: look at the top card of your deck.' },
  TR: { id: 'TR', name: 'Trim', pow: 0, str: 0, cost: 3, text: 'When bought: remove a card in your discard pile from the game.' },
  SU: { id: 'SU', name: 'Surge', pow: 8, str: 2, cost: 7 },
};
export const START = { S1: 4, S2: 3, R3: 2, CR: 1 };
export const MARKET_DECK = { S3: 4, S4: 3, B6: 3, CA: 3, SP: 3, PE: 2, TR: 2, SU: 2 };

const list = (m) => { const out = []; for (const [id, k] of Object.entries(m)) for (let i = 0; i < k; i++) out.push(id); return out; };
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleWith(r, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { life: LIFE, deck: list(START), disc: [], line: [], gone: [], pow: 0, strain: 0, bust: false, stop: false, peek: null }; }
export function clone(s) {
  return { ...s, market: s.market.slice(), mdeck: s.mdeck.slice(), order: s.order.slice(), p: s.p.map(p => ({ ...p, deck: p.deck.slice(), disc: p.disc.slice(), line: p.line.slice(), gone: p.gone.slice() })) };
}
function emit(s, ev, e) { if (ev) ev.push(e); }

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, round: 1, first: 0, rfirst: 0, turn: 0, phase: 'line', winner: null, market: [], mdeck: list(MARKET_DECK), order: [], last: null, p: [newPlayer(), newPlayer()] };
  const r = () => rand(s);
  for (const p of s.p) shuffleWith(r, p.deck);
  shuffleWith(r, s.mdeck);
  s.market = s.mdeck.splice(0, MARKET);
  s.first = rand(s) < 0.5 ? 0 : 1;
  if (first === 0 || first === 1) s.first = first;
  s.rfirst = s.turn = s.first;
  return s;
}

const done = (P) => P.bust || P.stop;
export const linePower = (P) => P.bust ? 0 : P.pow;
const canDraw = (P) => P.deck.length + P.disc.length > 0;

// Actions: line phase { t: 'draw' } { t: 'stop' } · buy phase { t: 'buy', i } { t: 'pass' } · trim phase { t: 'trim', card }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn];
  if (s.phase === 'line') return canDraw(P) ? [{ t: 'draw' }, { t: 'stop' }] : [{ t: 'stop' }];
  if (s.phase === 'buy') {
    const coin = P.bust ? BUST_COIN : P.pow, out = [{ t: 'pass' }];
    s.market.forEach((id, i) => { if (CARDS[id].cost <= coin) out.push({ t: 'buy', i }); });
    return out;
  }
  return [...new Set(P.disc)].map(card => ({ t: 'trim', card }));
}

function checkBust(s, side, ev) {
  const P = s.p[side];
  if (!P.bust && P.strain >= BUST) { P.bust = true; emit(s, ev, { t: 'bust', side }); }
}
function reveal(s, me, ev) {
  const P = s.p[me], O = s.p[1 - me];
  if (!P.deck.length) { P.deck = shuffleWith(() => rand(s), P.disc); P.disc = []; P.peek = null; emit(s, ev, { t: 'reshuffle', side: me }); }
  const id = P.deck.shift(), c = CARDS[id];
  if (P.peek !== null) P.peek = null;
  P.line.push(id); P.pow += c.pow; P.strain += c.str;
  emit(s, ev, { t: 'reveal', side: me, card: id });
  if (id === 'SP') { O.strain += 1; emit(s, ev, { t: 'spoil', side: 1 - me }); checkBust(s, 1 - me, ev); }
  if (id === 'PE' && P.deck.length) { P.peek = P.deck[0]; emit(s, ev, { t: 'peek', side: me }); }
  checkBust(s, me, ev);
}
// after a line action: the other player acts if still in, else this one, else the clash
function nextInLine(s, ev) {
  const me = s.turn, a = s.p[me], b = s.p[1 - me];
  if (!done(b)) { s.turn = 1 - me; return; }
  if (!done(a)) return;
  clash(s, ev);
}
function clash(s, ev) {
  const A = linePower(s.p[0]), B = linePower(s.p[1]);
  let loser = null, n = 0;
  if (A !== B) { loser = A < B ? 0 : 1; n = Math.max(1, Math.min(5, Math.abs(A - B))); s.p[loser].life -= n; }
  s.last = { pow: [A, B], loser, n };
  emit(s, ev, { t: 'clash', pow: [A, B], loser, n });
  if (loser !== null && s.p[loser].life <= 0) { s.winner = 1 - loser; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  s.phase = 'buy';
  s.order = loser === null ? [s.rfirst, 1 - s.rfirst] : [loser, 1 - loser];
  s.turn = s.order[0];
}
function nextBuyer(s, ev) {
  if (s.turn === s.order[0]) { s.turn = s.order[1]; s.phase = 'buy'; return; }
  endRound(s, ev);
}
function endRound(s, ev) {
  for (const P of s.p) { P.disc.push(...P.line); P.line = []; P.pow = 0; P.strain = 0; P.bust = false; P.stop = false; }
  if (s.round >= ROUNDS) {
    const a = s.p[0].life, b = s.p[1].life;
    s.winner = a > b ? 0 : b > a ? 1 : 'draw'; s.timeout = true; emit(s, ev, { t: 'end', winner: s.winner }); return;
  }
  s.round++; s.rfirst = 1 - s.rfirst; s.turn = s.rfirst; s.phase = 'line';
  emit(s, ev, { t: 'round', round: s.round, first: s.rfirst });
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me];
  if (s.phase === 'line') {
    if (a.t === 'draw') { if (!canDraw(P)) throw new Error('cannot draw'); reveal(s, me, ev); }
    else if (a.t === 'stop') { P.stop = true; emit(s, ev, { t: 'stop', side: me }); }
    else throw new Error('bad line action');
    nextInLine(s, ev);
  } else if (s.phase === 'buy') {
    if (a.t === 'pass') { emit(s, ev, { t: 'pass', side: me }); return nextBuyer(s, ev); }
    if (a.t !== 'buy') throw new Error('bad buy action');
    const id = s.market[a.i], coin = P.bust ? BUST_COIN : P.pow;
    if (!id || CARDS[id].cost > coin) throw new Error('cannot buy');
    s.market.splice(a.i, 1);
    if (s.mdeck.length) s.market.splice(a.i, 0, s.mdeck.shift());
    emit(s, ev, { t: 'buy', side: me, card: id });
    if (id === 'TR' && P.disc.length) { s.phase = 'trim'; s.pendingTrim = true; return; }
    P.disc.push(id);
    nextBuyer(s, ev);
  } else {
    if (a.t !== 'trim' || !P.disc.includes(a.card)) throw new Error('bad trim');
    P.disc.splice(P.disc.indexOf(a.card), 1); P.gone.push(a.card);
    emit(s, ev, { t: 'trim', side: me, card: a.card });
    P.disc.push('TR');
    nextBuyer(s, ev);
  }
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }

// What the mover cannot see: the order of every deck (its own top card stays if it peeked), the
// market deck, and the engine's future shuffles.
export function determinize(s, me, r) {
  const t = clone(s);
  t.seed = (r() * 4294967296) >>> 0;
  for (const side of [0, 1]) {
    const P = t.p[side];
    if (side === me && P.peek !== null && P.deck.length) { const top = P.deck.shift(); shuffleWith(r, P.deck); P.deck.unshift(top); }
    else { shuffleWith(r, P.deck); if (side !== me) P.peek = null; }
  }
  shuffleWith(r, t.mdeck);
  return t;
}
export function actionKey(s, a) { return a.t === 'buy' ? 'b' + s.market[a.i] : a.t === 'trim' ? 'x' + a.card : a.t; }
