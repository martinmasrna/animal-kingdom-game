// 09 Momentum rope: no units. A shared marker on a track from -8 to +8 and a velocity from -4 to +4.
// Cards shove the marker now or add velocity, which moves it at the end of every turn. Seat 0 wins
// at +8, seat 1 at -8; after 12 rounds the side the marker is on wins.
// Pure from the outside: act() clones the state.

export const END = 8, VMAX = 4, MAX_MANA = 8, ROUNDS = 12;

export const CARDS = {
  SHO: { id: 'SHO', name: 'Shove', cost: 1, text: 'Marker 1 forward now.' },
  JOL: { id: 'JOL', name: 'Jolt', cost: 2, text: 'Marker 2 forward now.' },
  HEA: { id: 'HEA', name: 'Heave', cost: 2, text: 'Velocity 1 forward.' },
  BIG: { id: 'BIG', name: 'Big Heave', cost: 4, text: 'Velocity 2 forward.' },
  CHK: { id: 'CHK', name: 'Check', cost: 3, text: 'Velocity becomes 0.' },
  REV: { id: 'REV', name: 'Reverse', cost: 5, text: 'Velocity changes sign.' },
  ANC: { id: 'ANC', name: 'Anchor', cost: 2, text: 'Until your next turn, the marker cannot move toward your end.' },
  SUR: { id: 'SUR', name: 'Surge', cost: 3, text: 'The marker moves by the velocity now.' },
  DR2: { id: 'DR2', name: 'Draw 2', cost: 2, text: 'Draw 2 cards.' },
  COIN: { id: 'COIN', name: 'Coin', cost: 0, text: '1 mana this turn.' },
};
export const DECK = { SHO: 3, JOL: 3, HEA: 4, BIG: 3, CHK: 3, REV: 2, ANC: 3, SUR: 2, DR2: 3 };
export const fwd = (side) => side === 0 ? 1 : -1;

export function deckList() { const out = []; for (const [id, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) out.push(id); return out; }
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleWith(r, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

function newPlayer() { return { mana: 0, maxMana: 0, dry: 0, hand: [], deck: deckList(), anchor: false }; }
export function clone(s) { return { ...s, p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice() })) }; }
function emit(s, ev, e) { if (ev) ev.push(e); }

// Move the marker by d (signed); an anchor stops any move toward its owner's end.
function move(s, d, why, ev) {
  if (!d || s.winner !== null) return;
  if (d < 0 && s.p[0].anchor) { emit(s, ev, { t: 'blocked', side: 0, d, why }); return; }
  if (d > 0 && s.p[1].anchor) { emit(s, ev, { t: 'blocked', side: 1, d, why }); return; }
  const from = s.pos;
  s.pos = Math.max(-END, Math.min(END, s.pos + d));
  emit(s, ev, { t: 'move', from, to: s.pos, why });
  if (s.pos >= END) win(s, 0, ev); else if (s.pos <= -END) win(s, 1, ev);
}
function win(s, w, ev) { if (s.winner === null) { s.winner = w; emit(s, ev, { t: 'end', winner: w }); } }
const clampV = (v) => Math.max(-VMAX, Math.min(VMAX, v));
function draw(s, side, ev) {
  const p = s.p[side];
  if (p.deck.length) { p.hand.push(p.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  emit(s, ev, { t: 'dry', side }); move(s, -fwd(side), 'dry', ev);
}

export function newMatch({ seed, first } = {}) {
  const s = { seed: (seed >>> 0) || 1, turnNo: 0, turn: 0, first: 0, winner: null, pos: 0, vel: 0, p: [newPlayer(), newPlayer()] };
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
function startTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++;
  p.anchor = false;
  emit(s, ev, { t: 'turn', side });
  p.maxMana = Math.min(MAX_MANA, p.maxMana + 1);
  p.mana = p.maxMana;
  draw(s, side, ev);
}

// Actions: { t: 'play', card } · { t: 'end' }
export function legalActions(s) {
  if (s.winner !== null) return [];
  const P = s.p[s.turn], out = [];
  for (const id of new Set(P.hand)) if (CARDS[id].cost <= P.mana) out.push({ t: 'play', card: id });
  out.push({ t: 'end' });
  return out;
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const me = s.turn, P = s.p[me], f = fwd(me);
  if (a.t === 'end') {
    emit(s, ev, { t: 'endturn', side: me });
    move(s, s.vel, 'vel', ev);
    if (s.winner !== null) return;
    if (s.turnNo >= 2 * ROUNDS) {
      // on exactly 0, the player the velocity points toward loses (+ points at seat 1's end)
      const w = s.pos > 0 ? 0 : s.pos < 0 ? 1 : s.vel > 0 ? 0 : s.vel < 0 ? 1 : 'draw';
      s.timeout = true; win(s, w, ev); return;
    }
    s.turn = 1 - me; startTurn(s, ev); return;
  }
  const c = CARDS[a.card];
  if (!c || !P.hand.includes(a.card) || c.cost > P.mana) throw new Error('illegal play ' + a.card);
  P.mana -= c.cost; P.hand.splice(P.hand.indexOf(a.card), 1);
  emit(s, ev, { t: 'play', side: me, card: a.card });
  switch (a.card) {
    case 'SHO': move(s, f, 'card', ev); break;
    case 'JOL': move(s, 2 * f, 'card', ev); break;
    case 'HEA': s.vel = clampV(s.vel + f); break;
    case 'BIG': s.vel = clampV(s.vel + 2 * f); break;
    case 'CHK': s.vel = 0; break;
    case 'REV': s.vel = -s.vel; break;
    case 'ANC': P.anchor = true; break;
    case 'SUR': move(s, s.vel, 'card', ev); break;
    case 'DR2': draw(s, me, ev); draw(s, me, ev); break;
    case 'COIN': P.mana += 1; break;
  }
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
export function actionKey(s, a) { return a.t === 'end' ? 'e' : a.card; }
