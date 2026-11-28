// Wave defense: one player against the game's threat deck walking down three lanes toward a Wall,
// with Defenders and spells from a deck that grows by one card every four rounds.
// Pure from the outside: act() clones the state.

export const WALL = 20, ROWS = 4, LANES = 3, HAND_MAX = 7, MANA_CAP = 8, ROUND_CAP = 60;
export const REWARD_ROUNDS = [4, 8, 12];

export const THREATS = {
  Runner: { id: 'Runner', atk: 1, hp: 2 },
  Grunt: { id: 'Grunt', atk: 2, hp: 3 },
  Swift: { id: 'Swift', atk: 2, hp: 2, swift: true },
  Brute: { id: 'Brute', atk: 3, hp: 6 },
  Tank: { id: 'Tank', atk: 1, hp: 10 },
  Boss: { id: 'Boss', atk: 5, hp: 8 },
};
export const TIERS = [
  { Runner: 4, Grunt: 4 },
  { Grunt: 2, Swift: 3, Brute: 3 },
  { Brute: 2, Tank: 2, Swift: 1, Boss: 3 },
];
export const CARDS = {
  Guard: { id: 'Guard', name: 'Guard', kind: 'Defender', cost: 1, atk: 1, hp: 5, shoot: 0 },
  Shooter: { id: 'Shooter', name: 'Shooter', kind: 'Defender', cost: 2, atk: 0, hp: 2, shoot: 1 },
  Hit3: { id: 'Hit3', name: 'Hit 3', kind: 'Hit', cost: 1, dmg: 3 },
  Repair: { id: 'Repair', name: 'Repair', kind: 'Wall', cost: 2, heal: 4 },
  Draw2: { id: 'Draw2', name: 'Draw 2', kind: 'Draw', cost: 1, draw: 2 },
  Heavy: { id: 'Heavy', name: 'Heavy', kind: 'Defender', cost: 4, atk: 3, hp: 8, shoot: 0 },
  Cannon: { id: 'Cannon', name: 'Cannon', kind: 'Defender', cost: 4, atk: 0, hp: 3, shoot: 3 },
  Twin: { id: 'Twin', name: 'Twin', kind: 'Defender', cost: 3, atk: 1, hp: 3, shoot: 2 },
  Bomb: { id: 'Bomb', name: 'Bomb', kind: 'Bomb', cost: 3, dmg: 2 },
  Freeze: { id: 'Freeze', name: 'Freeze', kind: 'Freeze', cost: 2 },
  Rebuild: { id: 'Rebuild', name: 'Rebuild', kind: 'Wall', cost: 3, heal: 8 },
  Hit6: { id: 'Hit6', name: 'Hit 6', kind: 'Hit', cost: 3, dmg: 6 },
};
export const START = { Guard: 3, Shooter: 3, Hit3: 3, Repair: 1, Draw2: 2 };
export const POOL = ['Heavy', 'Cannon', 'Twin', 'Bomb', 'Freeze', 'Rebuild', 'Hit6'];
export const lanesOf = (id) => ['Defender', 'Bomb', 'Freeze'].includes(CARDS[id].kind);

// three independent streams: the threat order (setup only), the player's shuffles, the reward offers
export function rng(s, key) {
  let t = (s[key] = (s[key] + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleIn(s, key, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng(s, key) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export function clone(s) {
  return { ...s, lanes: s.lanes.map(L => L.map(t => ({ ...t }))), slots: s.slots.map(d => d && { ...d }), threatDeck: s.threatDeck.slice(),
    deck: s.deck.slice(), hand: s.hand.slice(), discard: s.discard.slice(), offer: s.offer && s.offer.slice(), frozen: s.frozen.slice(), freezeNext: s.freezeNext.slice() };
}
function emit(ev, e) { if (ev) ev.push(e); }
// the page shows a round in steps: a copy of the table at each step's end (only when events are wanted)
function snap(s, ev, step) { if (ev) ev.push({ t: 'snap', step, s: clone(s) }); }

// flatMana: the one rule change after the first gate (mana is the same every round); null plays the spec.
export const FLAT_MANA = 4;
export function newMatch({ seed, flatMana = FLAT_MANA }) {
  seed = (seed >>> 0) || 1;
  const s = { flatMana, seedThreat: seed, seedDeck: (seed * 2654435761) >>> 0, seedReward: (seed * 40503 + 12345) >>> 0, uid: 1,
    round: 0, wall: WALL, mana: 0, phase: 'play', result: null, winner: null, cap: false,
    lanes: [[], [], []], slots: [null, null, null], threatDeck: [], deck: [], hand: [], discard: [], offer: null, frozen: [false, false, false], freezeNext: [false, false, false], toMove: 0, turn: 0 };
  TIERS.forEach((tier, k) => {
    const a = []; for (const [id, n] of Object.entries(tier)) for (let i = 0; i < n; i++) a.push({ id, tier: k + 1 });
    s.threatDeck.push(...shuffleIn(s, 'seedThreat', a));
  });
  for (const [id, n] of Object.entries(START)) for (let i = 0; i < n; i++) s.deck.push(id);
  shuffleIn(s, 'seedDeck', s.deck);
  startRound(s, null);
  return s;
}

function draw(s, ev) {
  if (s.hand.length >= HAND_MAX) return;
  if (!s.deck.length) { if (!s.discard.length) return; s.deck = shuffleIn(s, 'seedDeck', s.discard); s.discard = []; emit(ev, { t: 'reshuffle' }); }
  s.hand.push(s.deck.shift()); emit(ev, { t: 'draw' });
}
const threatsLeft = (s) => s.lanes.reduce((n, L) => n + L.length, 0);
function checkEnd(s, ev) {
  if (s.result) return true;
  if (s.wall <= 0) { s.result = 'loss'; s.winner = 'loss'; s.phase = 'over'; emit(ev, { t: 'end', result: 'loss' }); return true; }
  if (!s.threatDeck.length && !threatsLeft(s)) { s.result = 'win'; s.winner = 'win'; s.phase = 'over'; emit(ev, { t: 'end', result: 'win' }); return true; }
  return false;
}
function sweep(s, ev) {
  for (let l = 0; l < LANES; l++) {
    const L = s.lanes[l];
    for (let i = L.length - 1; i >= 0; i--) if (L[i].hp <= 0) { emit(ev, { t: 'die', lane: l, uid: L[i].uid, id: L[i].id }); L.splice(i, 1); }
    const d = s.slots[l];
    if (d && d.hp <= 0) { emit(ev, { t: 'fall', lane: l, uid: d.uid, id: d.id }); s.discard.push(d.id); s.slots[l] = null; }
  }
}
function hitThreat(s, lane, uid, n, ev) { const t = s.lanes[lane].find(x => x.uid === uid); if (!t) return; t.hp -= n; emit(ev, { t: 'hit', lane, uid, n }); }

// A round up to the player's turn: advance, attack, spawn, then mana and two cards.
function startRound(s, ev) {
  s.round++;
  emit(ev, { t: 'round', round: s.round });
  if (s.round > ROUND_CAP) { s.cap = true; s.result = 'loss'; s.winner = 'loss'; s.phase = 'over'; emit(ev, { t: 'end', result: 'loss' }); return; }
  s.frozen = s.freezeNext; s.freezeNext = [false, false, false];
  // advance, nearest threats first; only one threat stands in row 1 of a lane
  for (let l = 0; l < LANES; l++) {
    if (s.frozen[l]) continue;
    const L = s.lanes[l].slice().sort((a, b) => a.row - b.row);
    for (const t of L) {
      if (t.row === 1) continue;
      const from = t.row;
      let to = t.row - (THREATS[t.id].swift ? 2 : 1);
      if (to <= 1) to = s.lanes[l].some(x => x !== t && x.row === 1) ? 2 : 1;
      t.row = Math.min(from, to);
      if (t.row !== from) emit(ev, { t: 'move', lane: l, uid: t.uid, from, to: t.row });
    }
  }
  snap(s, ev, 'advance');
  // attack
  for (let l = 0; l < LANES; l++) {
    const t = s.lanes[l].find(x => x.row === 1);
    if (!t) continue;
    const d = s.slots[l];
    if (d) { emit(ev, { t: 'clash', lane: l, uid: t.uid, duid: d.uid }); d.hp -= t.atk; t.hp -= d.atk; emit(ev, { t: 'dhit', lane: l, uid: d.uid, n: t.atk }); if (d.atk) emit(ev, { t: 'hit', lane: l, uid: t.uid, n: d.atk }); }
    else { s.wall -= t.atk; emit(ev, { t: 'wall', lane: l, uid: t.uid, n: t.atk }); }
  }
  sweep(s, ev);
  snap(s, ev, 'attack');
  if (checkEnd(s, ev)) return;
  // spawn
  const k = s.round >= 7 ? 2 : 1;
  for (let i = 0; i < k && s.threatDeck.length; i++) {
    const c = s.threatDeck.shift();
    let lane = 0; for (let l = 1; l < LANES; l++) if (s.lanes[l].length < s.lanes[lane].length) lane = l;
    const T = THREATS[c.id], t = { uid: s.uid++, id: c.id, atk: T.atk, hp: T.hp, max: T.hp, row: ROWS };
    s.lanes[lane].push(t); emit(ev, { t: 'spawn', lane, uid: t.uid, id: c.id });
  }
  s.mana = s.flatMana || Math.min(s.round, MANA_CAP);
  s.phase = 'play';
  snap(s, ev, 'spawn');
  draw(s, ev); draw(s, ev);
}

// Actions: { t: 'play', card, lane } for Defenders, Bomb and Freeze; { t: 'play', card, lane, uid } for
// Hit (the threat's uid); { t: 'play', card } otherwise; { t: 'end' }; in the reward phase
// { t: 'reward', card } with card null for none.
export function legalActions(s) {
  if (s.result) return [];
  if (s.phase === 'reward') return s.offer.map(card => ({ t: 'reward', card })).concat([{ t: 'reward', card: null }]);
  const out = [{ t: 'end' }];
  for (const card of new Set(s.hand)) {
    const c = CARDS[card];
    if (c.cost > s.mana) continue;
    if (c.kind === 'Hit') { for (let l = 0; l < LANES; l++) for (const t of s.lanes[l]) out.push({ t: 'play', card, lane: l, uid: t.uid }); }
    else if (lanesOf(card)) for (let l = 0; l < LANES; l++) out.push({ t: 'play', card, lane: l });
    else out.push({ t: 'play', card });
  }
  return out;
}

function mAct(s, a, ev) {
  if (s.result) throw new Error('game over');
  if (a.t === 'reward') {
    if (s.phase !== 'reward') throw new Error('no reward now');
    if (a.card) { if (!s.offer.includes(a.card)) throw new Error('not offered'); s.discard.push(a.card); }
    emit(ev, { t: 'reward', card: a.card });
    s.offer = null;
    startRound(s, ev);
    return;
  }
  if (s.phase !== 'play') throw new Error('not the play phase');
  if (a.t === 'end') {
    // shoot
    for (let l = 0; l < LANES; l++) {
      const d = s.slots[l];
      if (!d || !d.shoot) continue;
      let near = null; for (const t of s.lanes[l]) if (!near || t.row < near.row) near = t;
      if (near) { emit(ev, { t: 'shoot', lane: l, duid: d.uid, uid: near.uid }); hitThreat(s, l, near.uid, d.shoot, ev); }
    }
    sweep(s, ev);
    snap(s, ev, 'shoot');
    if (checkEnd(s, ev)) return;
    if (REWARD_ROUNDS.includes(s.round)) {
      s.offer = []; for (let i = 0; i < 3; i++) s.offer.push(POOL[Math.floor(rng(s, 'seedReward') * POOL.length)]);
      s.phase = 'reward'; emit(ev, { t: 'offer', offer: s.offer.slice() });
      return;
    }
    startRound(s, ev);
    return;
  }
  if (a.t !== 'play') throw new Error('unknown action');
  const c = CARDS[a.card], k = s.hand.indexOf(a.card);
  if (!c || k < 0 || c.cost > s.mana) throw new Error('illegal play');
  if ((lanesOf(a.card) || c.kind === 'Hit') && !(a.lane >= 0 && a.lane < LANES)) throw new Error('bad lane');
  if (c.kind === 'Hit' && !s.lanes[a.lane].some(t => t.uid === a.uid)) throw new Error('bad target');
  s.mana -= c.cost; s.hand.splice(k, 1);
  emit(ev, { t: 'play', card: a.card, lane: a.lane, uid: a.uid });
  if (c.kind === 'Defender') {
    const old = s.slots[a.lane];
    if (old) { emit(ev, { t: 'fall', lane: a.lane, uid: old.uid, id: old.id, replaced: true }); s.discard.push(old.id); }
    s.slots[a.lane] = { uid: s.uid++, id: a.card, atk: c.atk, hp: c.hp, max: c.hp, shoot: c.shoot };
    emit(ev, { t: 'place', lane: a.lane, uid: s.slots[a.lane].uid });
    return;
  }
  s.discard.push(a.card);
  if (c.kind === 'Hit') hitThreat(s, a.lane, a.uid, c.dmg, ev);
  else if (c.kind === 'Bomb') for (const t of s.lanes[a.lane].slice()) hitThreat(s, a.lane, t.uid, c.dmg, ev);
  else if (c.kind === 'Freeze') { s.freezeNext[a.lane] = true; emit(ev, { t: 'freeze', lane: a.lane }); }
  else if (c.kind === 'Wall') { const n = Math.min(c.heal, WALL - s.wall); s.wall += n; emit(ev, { t: 'heal', n }); }
  else if (c.kind === 'Draw') { for (let i = 0; i < c.draw; i++) draw(s, ev); }
  sweep(s, ev);
  checkEnd(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
// How a finished game ranks for the pair comparison: a win beats a loss, then more Wall, then more rounds.
export const rank = (s) => (s.result === 'win' ? 1e6 : 0) + Math.max(0, s.wall) * 1000 + s.round;
