// Duel: Grid. Pure rules engine: state in, state out. No DOM, no globals, no Math.random.
// Tiles of one hero's area: t = col * 3 + row. col 0 front, 1 middle, 2 back. row 0, 1, 2 are the three lanes.

export const HEROES = {
  Heavy: { hp: 26, regen: 3, passive: 'Unstoppable', passiveText: 'Damage of 2 or less never cancels your cards.' },
  Quick: { hp: 34, regen: 4, passive: 'Light feet', passiveText: 'Your first Fast action each round costs 1 less.' },
};

export const MANA_CAP = 10;
export const BASICS = ['Jab', 'Block'];

// kind: light | heavy | defence | setup
export const CARDS = {
  Jab:      { cost: 1, speed: 'fast',   kind: 'light',   dmg: 2,  melee: true,  basic: true, text: '2 dmg to one front tile' },
  Block:    { cost: 1, speed: 'fast',   kind: 'defence', guard: 'block', basic: true, text: 'Guard: stops the first Light hit' },
  Slash:    { cost: 2, speed: 'normal', kind: 'light',   dmg: 4,  melee: true,  text: '4 dmg to the whole front column' },
  Lunge:    { cost: 3, speed: 'fast',   kind: 'light',   dmg: 4,  melee: true,  text: '4 dmg to one whole lane' },
  Flurry:   { cost: 3, speed: 'normal', kind: 'light',   dmg: 2,  melee: true,  hits: 2, text: '2 dmg to each of two front tiles' },
  Smash:    { cost: 4, speed: 'slow',   kind: 'heavy',   dmg: 8,  melee: true,  text: '8 dmg to any 2x2 block' },
  Haymaker: { cost: 6, speed: 'slow',   kind: 'heavy',   dmg: 12, melee: true,  text: '12 dmg to his front and middle columns' },
  Bolt:     { cost: 2, speed: 'normal', kind: 'light',   dmg: 3,  melee: false, text: '3 dmg to any one tile' },
  Blast:    { cost: 5, speed: 'slow',   kind: 'heavy',   dmg: 7,  melee: false, text: '7 dmg to one whole lane' },
  Parry:    { cost: 2, speed: 'fast',   kind: 'defence', guard: 'parry', text: 'Guard: stops the first Light hit, attacker takes 3' },
  Brace:    { cost: 2, speed: 'fast',   kind: 'defence', guard: 'brace', text: 'Guard: stops every Light hit' },
  Meditate: { cost: 0, speed: 'slow',   kind: 'setup',   text: 'Gain 3 mana' },
  Bandage:  { cost: 2, speed: 'slow',   kind: 'setup',   text: 'Heal 5' },
  Sharpen:  { cost: 3, speed: 'slow',   kind: 'setup',   text: 'Your hits deal +1 for the match' },
  Study:    { cost: 2, speed: 'normal', kind: 'setup',   text: 'Draw 2 cards' },
};

// Grid version decks: base lists with 1 Slash and 1 Flurry swapped for 2 Bolt, and 1 Smash for 1 Blast;
// then Heavy swaps 1 Haymaker for 1 Slash, and Quick 1 Meditate for 1 Smash.
export const DECKS = {
  Heavy: { Slash: 2, Lunge: 1, Flurry: 1, Bolt: 2, Smash: 2, Blast: 1, Haymaker: 2, Parry: 2, Brace: 2, Meditate: 1, Bandage: 2, Sharpen: 1, Study: 1 },
  Quick: { Slash: 2, Lunge: 3, Flurry: 2, Bolt: 2, Smash: 2, Blast: 1, Parry: 3, Brace: 1, Meditate: 1, Bandage: 1, Sharpen: 1, Study: 1 },
};
export const CARD_ORDER = ['Jab', 'Block', 'Slash', 'Lunge', 'Flurry', 'Bolt', 'Smash', 'Blast', 'Haymaker', 'Parry', 'Brace', 'Meditate', 'Bandage', 'Sharpen', 'Study'];

export const SPEEDS = ['fast', 'normal', 'slow'];
export const isAttack = (card) => CARDS[card].kind === 'light' || CARDS[card].kind === 'heavy';

export const colOf = (t) => (t / 3) | 0;
export const rowOf = (t) => t % 3;
export const tileOf = (col, row) => col * 3 + row;
export const maskOf = (tiles) => tiles.reduce((m, t) => m | (1 << t), 0);
export const tilesOf = (mask) => { const r = []; for (let t = 0; t < 9; t++) if ((mask >> t) & 1) r.push(t); return r; };
export const popcount = (m) => { let c = 0; while (m) { m &= m - 1; c++; } return c; };

// Every legal target shape of each attack, as tile bitmasks on the enemy area.
const S = (...tiles) => maskOf(tiles);
export const SHAPES = {
  Jab:      [S(0), S(1), S(2)],
  Slash:    [S(0, 1, 2)],
  Lunge:    [S(0, 3, 6), S(1, 4, 7), S(2, 5, 8)],
  Flurry:   [S(0, 1), S(0, 2), S(1, 2)],
  Smash:    [S(0, 1, 3, 4), S(1, 2, 4, 5), S(3, 4, 6, 7), S(4, 5, 7, 8)],
  Haymaker: [S(0, 1, 2, 3, 4, 5)],
  Bolt:     [S(0), S(1), S(2), S(3), S(4), S(5), S(6), S(7), S(8)],
  Blast:    [S(0, 3, 6), S(1, 4, 7), S(2, 5, 8)],
};

export const NEIGHBOURS = [];
for (let t = 0; t < 9; t++) {
  const c = colOf(t), r = rowOf(t), n = [];
  if (c > 0) n.push(tileOf(c - 1, r));
  if (c < 2) n.push(tileOf(c + 1, r));
  if (r > 0) n.push(tileOf(c, r - 1));
  if (r < 2) n.push(tileOf(c, r + 1));
  NEIGHBOURS.push(n);
}
export const START_TILE = tileOf(1, 1);

// ---------- seeded random ----------
// mulberry32; the state is a uint32 carried in an object so callers can thread it.
export function makeRng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  next.state = () => a;
  return next;
}
export function shuffle(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = (rng() * (i + 1)) | 0;
    const x = arr[i]; arr[i] = arr[j]; arr[j] = x;
  }
  return arr;
}
export function deckList(hero) {
  const out = [];
  for (const c of CARD_ORDER) for (let i = 0; i < (DECKS[hero][c] || 0); i++) out.push(c);
  return out;
}

// ---------- state ----------
function newPlayer(hero, rng) {
  const deck = shuffle(deckList(hero), rng);
  const hand = deck.splice(0, 4);
  return { hero, hp: HEROES[hero].hp, maxHp: HEROES[hero].hp, regen: HEROES[hero].regen, mana: MANA_CAP,
    deck, hand, discard: [], known: [], sharpen: 0, pos: START_TILE, fatigue: 0 };
}

export function newMatch(hero0, hero1, seed) {
  const rng = makeRng(seed);
  const p = [newPlayer(hero0, rng), newPlayer(hero1, rng)];
  return { round: 0, over: false, winner: null, p };
}

function clonePlayer(q) {
  return { hero: q.hero, hp: q.hp, maxHp: q.maxHp, regen: q.regen, mana: q.mana, deck: q.deck.slice(), hand: q.hand.slice(),
    discard: q.discard.slice(), known: q.known.slice(), sharpen: q.sharpen, pos: q.pos, fatigue: q.fatigue };
}
export function cloneState(s) {
  return { round: s.round, over: s.over, winner: s.winner, p: [clonePlayer(s.p[0]), clonePlayer(s.p[1])] };
}

function removeOne(arr, x) { const i = arr.indexOf(x); if (i >= 0) { arr.splice(i, 1); return true; } return false; }
function drawCards(q, n) { for (let i = 0; i < n && q.deck.length; i++) q.hand.push(q.deck.shift()); }

// Start of a round: both regain mana and draw 1. A hero with an empty deck takes fatigue instead: 1, then 2, then 3...
// s.fatigueTaken records what each hero took this round (0 if he drew).
export function startRound(state) {
  const s = cloneState(state);
  s.round++;
  s.fatigueTaken = [0, 0];
  s.p.forEach((q, side) => {
    q.mana = Math.min(MANA_CAP, q.mana + q.regen);
    if (q.deck.length) drawCards(q, 1);
    else { q.fatigue++; q.hp -= q.fatigue; s.fatigueTaken[side] = q.fatigue; }
  });
  const dead0 = s.p[0].hp <= 0, dead1 = s.p[1].hp <= 0;
  if (dead0 || dead1) { s.over = true; s.winner = dead0 && dead1 ? 'draw' : dead0 ? 1 : 0; }
  return s;
}

// ---------- choices ----------
// choice = { actions: [{ card, tiles }], step: null | destination tile }.  tiles is a bitmask (0 for non-attacks).
export function choiceCost(hero, actions) {
  let cost = 0, discounted = hero !== 'Quick';
  for (const a of actions) {
    let c = CARDS[a.card].cost;
    if (!discounted && CARDS[a.card].speed === 'fast') { c = Math.max(0, c - 1); discounted = true; }
    cost += c;
  }
  return cost;
}

// Returns null when legal, else a reason.
export function checkChoice(state, side, choice) {
  const q = state.p[side];
  if (!choice || !Array.isArray(choice.actions)) return 'no choice';
  if (choice.actions.length > 2) return 'more than 2 actions';
  const hand = q.hand.slice();
  const usedBasic = {};
  for (const a of choice.actions) {
    const C = CARDS[a.card];
    if (!C) return 'unknown card ' + a.card;
    if (C.basic) { if (usedBasic[a.card]) return a.card + ' used twice'; usedBasic[a.card] = true; }
    else if (!removeOne(hand, a.card)) return a.card + ' not in hand';
    if (isAttack(a.card)) { if (!SHAPES[a.card].includes(a.tiles)) return 'illegal target for ' + a.card; }
    else if (a.tiles) return a.card + ' takes no target';
  }
  if (choiceCost(q.hero, choice.actions) > q.mana) return 'not enough mana';
  if (choice.step != null && !NEIGHBOURS[q.pos].includes(choice.step)) return 'illegal step';
  return null;
}

// Where the attacker stands when an action of this speed resolves.
export function posAtSpeed(pos, step, speed) { return speed === 'fast' || step == null ? pos : step; }

// ---------- resolution ----------
function snap(s) {
  return s.p.map((q) => ({ hp: q.hp, mana: q.mana, pos: q.pos, sharpen: q.sharpen, hand: q.hand.length, deck: q.deck.length }));
}

// resolveRound(state, [choice0, choice1], { log }) -> { state, events }
// Order: reveal and pay, Fast, both steps, Normal, Slow. Within a step everything is simultaneous.
export function resolveRound(state, choices, opts) {
  const log = !opts || opts.log !== false;
  const s = cloneState(state);
  const ev = log ? [] : null;
  const round = s.round;
  for (let side = 0; side < 2; side++) {
    const err = checkChoice(s, side, choices[side]);
    if (err) throw new Error('illegal choice for side ' + side + ': ' + err);
  }
  const startPos = [s.p[0].pos, s.p[1].pos];
  const acts = [[], []];
  for (let side = 0; side < 2; side++) {
    const q = s.p[side], ch = choices[side];
    const cost = choiceCost(q.hero, ch.actions);
    q.mana -= cost;
    for (const a of ch.actions) {
      const C = CARDS[a.card];
      if (!C.basic) { removeOne(q.hand, a.card); removeOne(q.known, a.card); }
      acts[side].push({ card: a.card, tiles: a.tiles || 0, speed: C.speed, status: 'pending' });
    }
    if (ev) ev.push({ k: 'reveal', round, side, actions: ch.actions.map((a) => ({ card: a.card, tiles: a.tiles || 0 })), step: ch.step == null ? null : ch.step, from: q.pos, cost });
  }
  if (ev) ev.push({ k: 'phase', round, ph: 'reveal', snap: snap(s) });
  const guards = [[], []];

  const finish = (side, a) => { a.status = 'done'; if (!CARDS[a.card].basic) s.p[side].discard.push(a.card); };

  for (const ph of ['fast', 'step', 'normal', 'slow']) {
    if (ph === 'step') {
      for (let side = 0; side < 2; side++) {
        const st = choices[side].step;
        if (st != null) {
          if (ev) ev.push({ k: 'step', round, ph, side, from: s.p[side].pos, to: st });
          s.p[side].pos = st;
        }
      }
      if (ev) ev.push({ k: 'phase', round, ph, snap: snap(s) });
      continue;
    }
    const dmg = [0, 0], attackHits = [[], []], heal = [0, 0], sharpenAdd = [0, 0], meditate = [0, 0], draw = [0, 0];
    // guards go up first, so they meet attacks of the same step
    for (let side = 0; side < 2; side++) for (const a of acts[side]) {
      if (a.speed !== ph || a.status !== 'pending' || CARDS[a.card].kind !== 'defence') continue;
      guards[side].push({ type: CARDS[a.card].guard, card: a.card, used: false });
      finish(side, a);
      if (ev) ev.push({ k: 'guard', round, ph, side, card: a.card });
    }
    // attacks, each attacker's in the order played
    for (let side = 0; side < 2; side++) {
      const P = s.p[side], D = s.p[1 - side], d = 1 - side;
      for (const a of acts[side]) {
        if (a.speed !== ph || a.status !== 'pending' || !isAttack(a.card)) continue;
        const C = CARDS[a.card];
        finish(side, a);
        if (C.melee && colOf(P.pos) !== 0) {
          if (ev) ev.push({ k: 'attack', round, ph, side, card: a.card, tiles: a.tiles, outcome: 'nothing', at: D.pos, from: P.pos });
          continue;
        }
        const hitMasks = C.hits === 2 ? tilesOf(a.tiles).map((t) => 1 << t) : [a.tiles];
        let result = null;
        for (const m of hitMasks) {
          if (!((m >> D.pos) & 1)) continue;
          if (C.kind === 'light') {
            const g = guards[d].find((x) => !x.used);
            if (g) {
              if (g.type !== 'brace') g.used = true;
              if (g.type === 'parry') dmg[side] += 3;
              result = { outcome: 'blocked', guard: g.card, reflect: g.type === 'parry' ? 3 : 0 };
              continue;
            }
          }
          const amount = C.dmg + P.sharpen;
          dmg[d] += amount;
          attackHits[d].push(amount);
          result = { outcome: 'hit', amount };
        }
        if (!result) result = { outcome: 'miss', reason: ((a.tiles >> startPos[d]) & 1) ? 'moved' : 'never' };
        if (ev) ev.push({ k: 'attack', round, ph, side, card: a.card, tiles: a.tiles, at: D.pos, from: P.pos, startAt: startPos[d], ...result });
      }
    }
    // setup cards of this step
    for (let side = 0; side < 2; side++) for (const a of acts[side]) {
      if (a.speed !== ph || a.status !== 'pending') continue;
      finish(side, a);
      if (a.card === 'Study') draw[side] += 2;
      else if (a.card === 'Meditate') meditate[side] += 3;
      else if (a.card === 'Bandage') heal[side] += 5;
      else if (a.card === 'Sharpen') sharpenAdd[side] += 1;
    }
    // apply everything of the step together: damage, then healing for a hero still standing
    for (let side = 0; side < 2; side++) {
      const q = s.p[side];
      q.hp -= dmg[side];
      if (heal[side] && q.hp > 0) {
        const before = q.hp;
        q.hp = Math.min(q.maxHp, q.hp + heal[side]);
        if (ev) ev.push({ k: 'setup', round, ph, side, card: 'Bandage', value: q.hp - before });
      } else if (heal[side] && ev) ev.push({ k: 'setup', round, ph, side, card: 'Bandage', value: 0 });
      if (meditate[side]) {
        const before = q.mana;
        q.mana = Math.min(MANA_CAP, q.mana + meditate[side]);
        if (ev) ev.push({ k: 'setup', round, ph, side, card: 'Meditate', value: q.mana - before });
      }
      if (draw[side]) {
        const before = q.hand.length;
        drawCards(q, draw[side]);
        if (ev) ev.push({ k: 'setup', round, ph, side, card: 'Study', value: q.hand.length - before });
      }
      if (sharpenAdd[side]) {
        q.sharpen += sharpenAdd[side];
        if (ev) ev.push({ k: 'setup', round, ph, side, card: 'Sharpen', value: q.sharpen });
      }
    }
    // cancelling: damage from an attack cancels this hero's unresolved Slow cards (only later steps are affected)
    if (ph !== 'slow') {
      for (let side = 0; side < 2; side++) {
        const q = s.p[side];
        const cancels = attackHits[side].some((x) => x > 0 && !(q.hero === 'Heavy' && x <= 2));
        if (!cancels) continue;
        for (const a of acts[side]) {
          if (a.speed !== 'slow' || a.status !== 'pending') continue;
          a.status = 'cancelled';
          q.hand.push(a.card); q.known.push(a.card);
          if (ev) ev.push({ k: 'cancel', round, ph, side, card: a.card });
        }
      }
    }
    if (ev) ev.push({ k: 'phase', round, ph, snap: snap(s) });
    const dead0 = s.p[0].hp <= 0, dead1 = s.p[1].hp <= 0;
    if (dead0 || dead1) {
      s.over = true;
      s.winner = dead0 && dead1 ? 'draw' : dead0 ? 1 : 0;
      // anything still pending never resolves; played cards are spent
      for (let side = 0; side < 2; side++) for (const a of acts[side]) if (a.status === 'pending') finish(side, a);
      if (ev) ev.push({ k: 'end', round, ph, winner: s.winner });
      break;
    }
  }
  return { state: s, events: ev };
}

// ---------- full legal choice enumeration (used by the random player and by tests) ----------
export function actionSets(q) {
  const opts = BASICS.slice();
  for (const c of q.hand) if (!opts.includes(c)) opts.push(c);
  const sets = [[]];
  for (let i = 0; i < opts.length; i++) {
    sets.push([opts[i]]);
    for (let j = i; j < opts.length; j++) {
      if (i === j && (CARDS[opts[i]].basic || q.hand.filter((x) => x === opts[i]).length < 2)) continue;
      sets.push([opts[i], opts[j]]);
    }
  }
  return sets.filter((set) => choiceCost(q.hero, set.map((card) => ({ card }))) <= q.mana);
}

export function allLegalChoices(state, side) {
  const q = state.p[side];
  const steps = [null, ...NEIGHBOURS[q.pos]];
  const out = [];
  for (const set of actionSets(q)) {
    let combos = [[]];
    for (const card of set) {
      const masks = isAttack(card) ? SHAPES[card] : [0];
      const next = [];
      for (const c of combos) for (const m of masks) next.push([...c, { card, tiles: m }]);
      combos = next;
    }
    for (const actions of combos) for (const step of steps) out.push({ actions, step });
  }
  return out;
}
