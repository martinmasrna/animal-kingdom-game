// 43 Auto deck battle. Each round both players shop in secret with 6 gold (buy from 4 random
// cards, reroll, remove a card from the deck), then the two decks fight themselves: shuffled,
// front card against front card, the next card stepping up when one falls. The side left with
// cards deals 1 damage plus 1 per card it still has, at most 4. Life 10; 12 rounds.
// Pure from the outside: act() clones the state; step() mutates it.

export const LIFE = 10, GOLD = 6, SHOP = 4, DECK_MAX = 10, ROUNDS = 12, REROLL = 1, REMOVE = 1, MAX_HIT = 4;

export const CARDS = {
  PI: { id: 'PI', name: 'Pip', cost: 1, atk: 1, hp: 2 },
  BR: { id: 'BR', name: 'Brawler', cost: 2, atk: 3, hp: 2 },
  WA: { id: 'WA', name: 'Wall', cost: 2, atk: 1, hp: 5 },
  BO: { id: 'BO', name: 'Bomb', cost: 3, atk: 2, hp: 1, text: 'When it falls, 3 damage to the enemy front card.' },
  OP: { id: 'OP', name: 'Opener', cost: 3, atk: 2, hp: 3, text: 'Enters: 2 damage to the enemy front card.' },
  RA: { id: 'RA', name: 'Rally', cost: 3, atk: 1, hp: 3, text: 'When it falls, your next front card gets +2/+2.' },
  GU: { id: 'GU', name: 'Guardian', cost: 3, atk: 2, hp: 4, text: 'Takes 1 less damage from each hit.' },
  HE: { id: 'HE', name: 'Heavy', cost: 4, atk: 4, hp: 6 },
};
export const POOL = Object.keys(CARDS);

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(rnd, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

// p.deck: the deck as it stands (it changes while its owner shops); p.shown: the deck as the
// opponent knows it (the deck at the start of the round, since shops are secret)
function newPlayer() { return { life: LIFE, deck: ['PI', 'PI', 'PI'], shown: ['PI', 'PI', 'PI'], gold: 0, shop: [], removed: false, done: false }; }
export function clone(s) {
  return { ...s, p: s.p.map(p => ({ ...p, deck: p.deck.slice(), shown: p.shown.slice(), shop: p.shop.slice() })), log: s.log };
}
function emit(s, ev, e) { if (ev) ev.push(e); }
function rollShop(s, side) { const p = s.p[side]; p.shop = []; for (let i = 0; i < SHOP; i++) p.shop.push(POOL[Math.floor(rand(s) * POOL.length)]); }

export function newMatch({ seed }) {
  const s = { seed: (seed >>> 0) || 1, round: 0, turnNo: 0, first: 0, toMove: 0, phase: 'shop', winner: null, log: null, p: [newPlayer(), newPlayer()] };
  startRound(s, null);
  return s;
}
function startRound(s, ev) {
  s.round++; s.turnNo++;
  for (const k of [0, 1]) { const p = s.p[k]; p.gold = GOLD; p.removed = false; p.done = false; p.shown = p.deck.slice(); rollShop(s, k); }
  s.phase = 'shop'; s.toMove = 0;
  emit(s, ev, { t: 'round', round: s.round });
}

// Actions (shop phase, the mover's own shop): { t: 'buy', i } shop slot i; { t: 'reroll' };
// { t: 'remove', card } one card of that kind out of the deck (once a round); { t: 'done' }
export function key(a) { return a.t === 'buy' ? 'b' + a.i : a.t === 'remove' ? 'r' + a.card : a.t; }
export function isLegal(s, a) {
  if (s.winner !== null || s.phase !== 'shop' || !a) return false;
  const P = s.p[s.toMove];
  if (a.t === 'done') return true;
  if (a.t === 'buy') return a.i >= 0 && a.i < P.shop.length && P.shop[a.i] !== null && CARDS[P.shop[a.i]].cost <= P.gold && P.deck.length < DECK_MAX;
  if (a.t === 'reroll') return P.gold >= REROLL;
  if (a.t === 'remove') return !P.removed && P.gold >= REMOVE && P.deck.includes(a.card);
  return false;
}
export function legalActions(s) {
  if (s.winner !== null || s.phase !== 'shop') return [];
  const P = s.p[s.toMove], out = [];
  P.shop.forEach((id, i) => { const a = { t: 'buy', i }; if (isLegal(s, a)) out.push(a); });
  if (isLegal(s, { t: 'reroll' })) out.push({ t: 'reroll' });
  for (const card of new Set(P.deck)) { const a = { t: 'remove', card }; if (isLegal(s, a)) out.push(a); }
  out.push({ t: 'done' });
  return out;
}

// ------------------------------------------------------------------ the battle
// One step: the two front cards hit each other at once; fallen cards leave; each side without a
// front card steps its next card up; then "when it falls" effects, then "enters" effects, each
// on the front cards as they now stand; repeat until nothing more falls.
const dmgTo = (c, n) => c.id === 'GU' ? Math.max(0, n - 1) : n;
function mk(id) { const c = CARDS[id]; return { id, atk: c.atk, hp: c.hp }; }
export function battle(deckA, deckB, rnd, log) {
  const q = [shuffleInPlace(rnd, deckA.slice()), shuffleInPlace(rnd, deckB.slice())];
  const front = [null, null];
  const say = (e) => { if (log) log.push(e); };
  const enter = (k, queue) => { if (!front[k] && q[k].length) { front[k] = mk(q[k].shift()); say({ t: 'enter', side: k, card: front[k].id, left: q[k].length }); if (front[k].id === 'OP') queue.push({ k, what: 'open' }); } };
  const settle = (queue) => {
    for (let guard = 0; guard < 50; guard++) {
      const falls = [];
      for (const k of [0, 1]) if (front[k] && front[k].hp <= 0) { say({ t: 'fall', side: k, card: front[k].id }); if (front[k].id === 'BO') falls.push({ k, what: 'bomb' }); if (front[k].id === 'RA') falls.push({ k, what: 'rally' }); front[k] = null; }
      const enters = [];
      for (const k of [0, 1]) enter(k, enters);
      const all = [...falls, ...queue.splice(0), ...enters];
      if (!all.length) return;
      for (const f of all) {
        if (f.what === 'bomb' || f.what === 'open') { const e = front[1 - f.k]; if (e) { const n = dmgTo(e, f.what === 'bomb' ? 3 : 2); e.hp -= n; say({ t: f.what, side: f.k, n, hp: e.hp }); } }
        if (f.what === 'rally') { const m = front[f.k]; if (m) { m.atk += 2; m.hp += 2; say({ t: 'rally', side: f.k, atk: m.atk, hp: m.hp }); } }
      }
    }
  };
  const start = []; enter(0, start); enter(1, start); settle(start);
  for (let steps = 0; steps < 300; steps++) {
    if (!front[0] || !front[1]) break;
    const a = front[0], b = front[1], na = dmgTo(b, a.atk), nb = dmgTo(a, b.atk);
    b.hp -= na; a.hp -= nb;
    say({ t: 'clash', n: [na, nb], hp: [a.hp, b.hp] });
    settle([]);
  }
  const left = [0, 1].map(k => (front[k] ? 1 : 0) + q[k].length);
  let winner = null;
  if (left[0] && !left[1]) winner = 0; else if (left[1] && !left[0]) winner = 1;
  const dmg = winner === null ? 0 : Math.min(MAX_HIT, 1 + left[winner]);
  say({ t: 'result', winner, dmg, left });
  return { winner, dmg, left };
}

function fight(s, ev) {
  const log = [];
  const r = battle(s.p[0].deck, s.p[1].deck, () => rand(s), log);
  if (r.winner !== null) s.p[1 - r.winner].life -= r.dmg;
  s.log = { round: s.round, decks: [s.p[0].deck.slice(), s.p[1].deck.slice()], steps: log, ...r };
  emit(s, ev, { t: 'battle', ...s.log });
  const dead = [0, 1].filter(k => s.p[k].life <= 0);
  if (dead.length) { s.winner = dead.length === 2 ? 'draw' : 1 - dead[0]; s.phase = 'over'; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  if (s.round >= ROUNDS) { const a = s.p[0].life, b = s.p[1].life; s.winner = a === b ? 'draw' : a > b ? 0 : 1; s.phase = 'over'; emit(s, ev, { t: 'end', winner: s.winner }); return; }
  startRound(s, ev);
}

function mAct(s, a, ev) {
  if (!isLegal(s, a)) throw new Error('illegal ' + key(a));
  const me = s.toMove, P = s.p[me];
  emit(s, ev, { t: 'shop', side: me, a });
  if (a.t === 'buy') { const id = P.shop[a.i]; P.gold -= CARDS[id].cost; P.deck.push(id); P.shop[a.i] = null; return; }
  if (a.t === 'reroll') { P.gold -= REROLL; rollShop(s, me); return; }
  if (a.t === 'remove') { P.gold -= REMOVE; P.deck.splice(P.deck.indexOf(a.card), 1); P.removed = true; return; }
  P.done = true;
  if (me === 0) { s.toMove = 1; return; }
  s.turnNo++;
  fight(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function step(t, a) { mAct(t, a, null); return t; }
