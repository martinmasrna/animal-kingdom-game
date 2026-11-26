// Rules engine for the Duel prototype, versions Hidden and Open (RULES.md).
// Pure from the outside: every exported transition clones the state, changes the
// clone and returns it. Randomness comes only from state.seed. Events (for the
// log) are pushed into an optional array; the state never holds the log.

export const SPEEDS = ['Fast', 'Normal', 'Slow'];
export const BASICS = ['Jab', 'Block'];
export const MANA_CAP = 10;
export const ROUND_LIMIT = 60;

export const HEROES = {
  Heavy: { hp: 31, regen: 3, passive: 'Unstoppable: damage of 2 or less never cancels his cards.' },
  Quick: { hp: 28, regen: 4, passive: 'Light feet: his first Fast action each turn costs 1 less.' },
};

// kind: Light | Heavy | Defence | Setup
export const CARDS = {
  Jab: { cost: 1, speed: 'Fast', kind: 'Light', dmg: 2, hits: 1, basic: true, text: '2 damage.' },
  Block: { cost: 1, speed: 'Fast', kind: 'Defence', basic: true, text: 'Stops the first Light hit.' },
  Slash: { cost: 2, speed: 'Normal', kind: 'Light', dmg: 4, hits: 1, text: '4 damage.' },
  Lunge: { cost: 3, speed: 'Fast', kind: 'Light', dmg: 4, hits: 1, text: '4 damage.' },
  Flurry: { cost: 3, speed: 'Normal', kind: 'Light', dmg: 2, hits: 2, text: 'Two hits of 2.' },
  Smash: { cost: 4, speed: 'Slow', kind: 'Heavy', dmg: 8, hits: 1, text: '8 damage.' },
  Haymaker: { cost: 6, speed: 'Slow', kind: 'Heavy', dmg: 12, hits: 1, text: '12 damage.' },
  Parry: { cost: 2, speed: 'Fast', kind: 'Defence', text: 'Stops the first Light hit; attacker takes 3.' },
  Brace: { cost: 2, speed: 'Fast', kind: 'Defence', text: 'Stops every Light hit.' },
  Meditate: { cost: 0, speed: 'Slow', kind: 'Setup', text: 'Gain 3 mana.' },
  Bandage: { cost: 2, speed: 'Slow', kind: 'Setup', text: 'Heal 5.' },
  Sharpen: { cost: 3, speed: 'Slow', kind: 'Setup', text: 'All your hits deal 1 more, for good.' },
  Study: { cost: 2, speed: 'Normal', kind: 'Setup', text: 'Draw 2 cards.' },
};
export const KIND_LABEL = { Light: 'Light attack', Heavy: 'Heavy attack', Defence: 'Defence', Setup: 'Setup' };

export const DECKS = {
  Heavy: { Slash: 2, Lunge: 1, Flurry: 2, Smash: 3, Haymaker: 3, Parry: 2, Brace: 2, Meditate: 1, Bandage: 2, Sharpen: 1, Study: 1 },
  Quick: { Slash: 3, Lunge: 3, Flurry: 3, Smash: 2, Parry: 3, Brace: 1, Meditate: 2, Bandage: 1, Sharpen: 1, Study: 1 },
};

export function isAttack(name) { const k = CARDS[name].kind; return k === 'Light' || k === 'Heavy'; }

export function deckList(hero) {
  const out = [];
  for (const [n, c] of Object.entries(DECKS[hero])) for (let i = 0; i < c; i++) out.push(n);
  return out;
}

// ---------- randomness (mulberry32 on state.seed) ----------
export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

// ---------- state ----------
function newPlayer(hero) {
  const h = HEROES[hero];
  return {
    hero, hp: h.hp, maxHp: h.hp, regen: h.regen, mana: MANA_CAP,
    hand: [], deck: deckList(hero), discard: [], known: [],
    guards: [], winding: [], committed: [], lastRound: [],
    sharpen: 0, actions: 0, usedBasics: [], fastUsed: false, turns: 0,
  };
}
function clonePlayer(p) {
  return {
    ...p, hand: p.hand.slice(), deck: p.deck.slice(), discard: p.discard.slice(), known: p.known.slice(),
    guards: p.guards.map(g => ({ ...g })), winding: p.winding.slice(),
    committed: p.committed.map(a => ({ ...a })), lastRound: p.lastRound,
    usedBasics: p.usedBasics.slice(),
  };
}
export function clone(s) { return { ...s, p: [clonePlayer(s.p[0]), clonePlayer(s.p[1])] }; }

function emit(s, ev, e) {
  if (!ev) return;
  e.round = s.round;
  if (s.version === 'hidden' && s.stepIdx >= 0) e.step = SPEEDS[s.stepIdx];
  ev.push(e);
}

function removeOne(arr, name) { const i = arr.indexOf(name); if (i >= 0) { arr.splice(i, 1); return true; } return false; }

function mDraw(s, side, n) {
  const p = s.p[side]; let drawn = 0;
  for (let i = 0; i < n; i++) { if (!p.deck.length) break; p.hand.push(p.deck.shift()); drawn++; }
  return drawn;
}

function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].hp <= 0, b = s.p[1].hp <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}

// Damage of one attack hit cancels the defender's unresolved Slow cards,
// except damage of 2 or less against Heavy (Unstoppable).
export function hitCancels(defender, dmg) { return dmg > 0 && !(defender.hero === 'Heavy' && dmg <= 2); }

// Cost of taking `names` in order, given whether a Fast action was already taken this turn.
export function seqCost(p, names, fastUsed = p.fastUsed) {
  let total = 0, fast = fastUsed;
  for (const n of names) {
    let c = CARDS[n].cost;
    if (CARDS[n].speed === 'Fast' && !fast) { fast = true; if (p.hero === 'Quick') c = Math.max(0, c - 1); }
    total += c;
  }
  return total;
}

function countNames(arr) { const m = {}; for (const n of arr) m[n] = (m[n] || 0) + 1; return m; }

export function newMatch({ version, heroes, seed }) {
  const s = {
    version, seed: (seed >>> 0) || 1, round: 0, turnNo: 0, turn: 0, first: 0,
    winner: null, stepIdx: -1, p: [newPlayer(heroes[0]), newPlayer(heroes[1])],
  };
  for (const p of s.p) shuffleInPlace(s, p.deck);
  mDraw(s, 0, 4); mDraw(s, 1, 4);
  if (version === 'open') {
    s.first = rand(s) < 0.5 ? 0 : 1;
    mDraw(s, 1 - s.first, 1);
    s.turn = s.first;
    mStartTurn(s, null);
  } else {
    mStartRound(s, null);
  }
  return s;
}
// Events of the opening (first round / first turn start), for the log.
export function openingEvents(s) {
  const ev = [];
  if (s.version === 'open') {
    ev.push({ t: 'first', side: s.first, round: s.round });
    ev.push({ t: 'turn', side: s.turn, n: s.turnNo, round: s.round });
    ev.push({ t: 'start', side: s.turn, gain: 0, mana: s.p[s.turn].mana, drew: 1, round: s.round });
  } else {
    ev.push({ t: 'round', round: 1 });
    for (const i of [0, 1]) ev.push({ t: 'start', side: i, gain: 0, mana: s.p[i].mana, drew: 1, round: 1 });
  }
  return ev;
}

// =====================================================================
// Version 1: Hidden
// =====================================================================

function mStartRound(s, ev) {
  s.round++;
  emit(s, ev, { t: 'round' });
  for (const i of [0, 1]) {
    const p = s.p[i];
    const before = p.mana;
    p.mana = Math.min(MANA_CAP, p.mana + p.regen);
    const drew = mDraw(s, i, 1);
    p.guards = []; p.committed = []; p.fastUsed = false; p.actions = 0; p.usedBasics = [];
    emit(s, ev, { t: 'start', side: i, gain: p.mana - before, mana: p.mana, drew });
  }
}

export function validSet(s, side, names) {
  if (!Array.isArray(names) || names.length > 2) return false;
  const p = s.p[side];
  const need = {};
  for (const n of names) {
    if (!CARDS[n]) return false;
    if (CARDS[n].basic) { if (need[n]) return false; need[n] = 1; continue; }
    need[n] = (need[n] || 0) + 1;
  }
  const have = countNames(p.hand);
  for (const n in need) if (!CARDS[n].basic && (have[n] || 0) < need[n]) return false;
  return seqCost(p, names, false) <= p.mana;
}

function sameCat(a, b) {
  const ka = CARDS[a].kind, kb = CARDS[b].kind;
  return CARDS[a].speed === CARDS[b].speed && ((ka === 'Light' && kb === 'Light') || (ka === 'Defence' && kb === 'Defence'));
}

// Every legal choice for a round: nothing, one action, or two. Order is kept only
// where it can change the outcome (two Light attacks or two guards of the same speed).
export function legalSets(s, side) {
  const p = s.p[side];
  const counts = countNames(p.hand);
  const opts = Object.keys(counts).sort().concat(BASICS);
  const res = [[]];
  for (let i = 0; i < opts.length; i++) {
    const a = opts[i];
    if (!validSet(s, side, [a])) continue;
    res.push([a]);
    if (!CARDS[a].basic && counts[a] >= 2 && validSet(s, side, [a, a])) res.push([a, a]);
    for (let j = i + 1; j < opts.length; j++) {
      const b = opts[j];
      if (!validSet(s, side, [a, b])) continue;
      res.push([a, b]);
      if (sameCat(a, b)) res.push([b, a]);
    }
  }
  return res;
}

function mCommit(s, choices, ev) {
  if (s.version !== 'hidden' || s.winner !== null || s.stepIdx >= 0) throw new Error('commit: not choosing');
  for (const i of [0, 1]) if (!validSet(s, i, choices[i])) throw new Error('commit: illegal set for side ' + i + ': ' + JSON.stringify(choices[i]));
  for (const i of [0, 1]) {
    const p = s.p[i];
    p.mana -= seqCost(p, choices[i], false);
    for (const n of choices[i]) if (!CARDS[n].basic) { removeOne(p.hand, n); removeOne(p.known, n); }
    p.committed = choices[i].map(n => ({ name: n, status: 'pending' }));
    p.actions = choices[i].length;
    emit(s, ev, { t: 'reveal', side: i, acts: choices[i].slice(), mana: p.mana });
  }
  s.stepIdx = 0;
}

function mResolveStep(s, ev) {
  if (s.stepIdx < 0) throw new Error('resolveStep: nothing to resolve');
  const speed = SPEEDS[s.stepIdx];
  const acts = [0, 1].map(i => s.p[i].committed.filter(a => a.status === 'pending' && CARDS[a.name].speed === speed));
  // 1. guards of this step go up first, so they face this step's attacks too
  for (const i of [0, 1]) for (const a of acts[i]) if (CARDS[a.name].kind === 'Defence') {
    s.p[i].guards.push({ type: a.name, used: false });
    emit(s, ev, { t: 'guard', side: i, card: a.name });
  }
  // 2. all hits of the step, worked out against the state at the start of the step
  const dmg = [0, 0], heal = [0, 0], cancelling = [false, false];
  for (const i of [0, 1]) {
    const att = s.p[i], j = 1 - i, def = s.p[j];
    for (const a of acts[i]) {
      const c = CARDS[a.name];
      if (c.kind !== 'Light' && c.kind !== 'Heavy') continue;
      for (let h = 0; h < c.hits; h++) {
        const d = c.dmg + att.sharpen;
        if (c.kind === 'Light') {
          const g = def.guards.find(g => g.type === 'Brace' || !g.used);
          if (g) {
            if (g.type !== 'Brace') g.used = true;
            emit(s, ev, { t: 'stop', side: j, guard: g.type, card: a.name, hit: h, hits: c.hits });
            if (g.type === 'Parry') { dmg[i] += 3; emit(s, ev, { t: 'parry', side: j, dmg: 3 }); }
            continue;
          }
        }
        dmg[j] += d;
        if (hitCancels(def, d)) cancelling[j] = true;
        emit(s, ev, { t: 'hit', side: i, card: a.name, dmg: d, hit: h, hits: c.hits });
      }
    }
  }
  // 3. setups of this step
  const mana = [0, 0], sharpen = [0, 0], draws = [0, 0];
  for (const i of [0, 1]) for (const a of acts[i]) {
    const n = a.name;
    if (n === 'Meditate') mana[i] += 3;
    else if (n === 'Bandage') heal[i] += 5;
    else if (n === 'Sharpen') sharpen[i] += 1;
    else if (n === 'Study') draws[i] += 2;
  }
  // 4. apply everything together
  for (const i of [0, 1]) {
    const p = s.p[i];
    const hpBefore = p.hp;
    p.hp = Math.min(p.maxHp, p.hp - dmg[i] + heal[i]);
    if (heal[i]) emit(s, ev, { t: 'heal', side: i, amount: Math.max(0, Math.min(p.maxHp, hpBefore - dmg[i] + heal[i]) - (hpBefore - dmg[i])), hp: p.hp });
    if (mana[i]) { const b = p.mana; p.mana = Math.min(MANA_CAP, p.mana + mana[i]); emit(s, ev, { t: 'meditate', side: i, amount: p.mana - b, mana: p.mana }); }
    if (sharpen[i]) { p.sharpen += sharpen[i]; emit(s, ev, { t: 'sharpen', side: i, total: p.sharpen }); }
    if (draws[i]) { const d = mDraw(s, i, draws[i]); emit(s, ev, { t: 'study', side: i, drew: d }); }
    for (const a of acts[i]) a.status = 'done';
  }
  // 5. cancelling: only later steps are affected
  for (const i of [0, 1]) if (cancelling[i]) {
    const p = s.p[i];
    for (const a of p.committed) if (a.status === 'pending' && CARDS[a.name].speed === 'Slow') {
      a.status = 'cancelled';
      p.hand.push(a.name); p.known.push(a.name);
      emit(s, ev, { t: 'cancel', side: i, card: a.name });
    }
  }
  const over = checkWin(s, ev);
  s.stepIdx++;
  if (over || s.stepIdx >= SPEEDS.length) mFinishRound(s, ev);
}

function mFinishRound(s, ev) {
  for (const p of s.p) {
    for (const a of p.committed) if (a.status !== 'cancelled' && !CARDS[a.name].basic) p.discard.push(a.name);
    p.lastRound = p.committed;
    p.committed = [];
    p.guards = [];
  }
  s.stepIdx = -1;
  if (s.winner === null) mStartRound(s, ev);
}

export function commitRound(s, choices, ev) { const t = clone(s); mCommit(t, choices, ev); return t; }
export function resolveStep(s, ev) { const t = clone(s); mResolveStep(t, ev); return t; }
export function playRound(s, choices, ev) {
  const t = clone(s); mCommit(t, choices, ev);
  while (t.stepIdx >= 0) mResolveStep(t, ev);
  return t;
}
// in-place variants for search (callers pass their own clone)
export function _playRoundInPlace(t, choices) { mCommit(t, choices, null); while (t.stepIdx >= 0) mResolveStep(t, null); return t; }

// =====================================================================
// Version 2: Open
// =====================================================================

function mStartTurn(s, ev) {
  const side = s.turn, p = s.p[side];
  s.turnNo++; s.round = s.turnNo; p.turns++;
  emit(s, ev, { t: 'turn', side, n: s.turnNo });
  p.guards = [];
  while (p.winding.length && s.winner === null) {
    const n = p.winding.shift();
    emit(s, ev, { t: 'unwind', side, card: n });
    mResolveOpen(s, side, n, ev);
    p.discard.push(n);
  }
  if (s.winner !== null) return;
  const before = p.mana;
  p.mana = Math.min(MANA_CAP, p.mana + p.regen);
  const drew = mDraw(s, side, 1);
  p.actions = 0; p.usedBasics = []; p.fastUsed = false;
  emit(s, ev, { t: 'start', side, gain: p.mana - before, mana: p.mana, drew });
}

function mResolveOpen(s, side, name, ev) {
  const c = CARDS[name], p = s.p[side], o = s.p[1 - side];
  if (c.kind === 'Light' || c.kind === 'Heavy') {
    for (let h = 0; h < c.hits && s.winner === null; h++) {
      const d = c.dmg + p.sharpen;
      if (c.kind === 'Light') {
        const g = o.guards.find(g => g.type === 'Brace' || !g.used);
        if (g) {
          if (g.type !== 'Brace') g.used = true;
          emit(s, ev, { t: 'stop', side: 1 - side, guard: g.type, card: name, hit: h, hits: c.hits });
          if (g.type === 'Parry') { p.hp -= 3; emit(s, ev, { t: 'parry', side: 1 - side, dmg: 3 }); checkWin(s, ev); }
          continue;
        }
      }
      o.hp -= d;
      emit(s, ev, { t: 'hit', side, card: name, dmg: d, hit: h, hits: c.hits });
      if (hitCancels(o, d) && o.winding.length) {
        for (const w of o.winding) { o.hand.push(w); o.known.push(w); emit(s, ev, { t: 'cancel', side: 1 - side, card: w }); }
        o.winding = [];
      }
      checkWin(s, ev);
    }
  } else if (c.kind === 'Defence') {
    p.guards.push({ type: name, used: false });
    emit(s, ev, { t: 'guard', side, card: name });
  } else if (name === 'Meditate') {
    const b = p.mana; p.mana = Math.min(MANA_CAP, p.mana + 3);
    emit(s, ev, { t: 'meditate', side, amount: p.mana - b, mana: p.mana });
  } else if (name === 'Bandage') {
    const b = p.hp; p.hp = Math.min(p.maxHp, p.hp + 5);
    emit(s, ev, { t: 'heal', side, amount: p.hp - b, hp: p.hp });
  } else if (name === 'Sharpen') {
    p.sharpen++; emit(s, ev, { t: 'sharpen', side, total: p.sharpen });
  } else if (name === 'Study') {
    const d = mDraw(s, side, 2); emit(s, ev, { t: 'study', side, drew: d });
  }
}

export function canPlay(s, name) {
  if (s.version !== 'open' || s.winner !== null) return false;
  const p = s.p[s.turn];
  if (p.actions >= 2 || !CARDS[name]) return false;
  if (CARDS[name].basic) { if (p.usedBasics.includes(name)) return false; }
  else if (!p.hand.includes(name)) return false;
  return seqCost(p, [name]) <= p.mana;
}
export function openLegalActions(s) {
  if (s.version !== 'open' || s.winner !== null) return [];
  const p = s.p[s.turn];
  if (p.actions >= 2) return [];
  const opts = Object.keys(countNames(p.hand)).sort().concat(BASICS);
  return opts.filter(n => canPlay(s, n));
}

function mPlay(s, name, ev) {
  if (!canPlay(s, name)) throw new Error('playAction: illegal ' + name);
  const side = s.turn, p = s.p[side], c = CARDS[name];
  p.mana -= seqCost(p, [name]);
  if (c.speed === 'Fast') p.fastUsed = true;
  p.actions++;
  if (c.basic) p.usedBasics.push(name); else { removeOne(p.hand, name); removeOne(p.known, name); }
  emit(s, ev, { t: 'play', side, card: name, mana: p.mana });
  if (c.speed === 'Slow') { p.winding.push(name); emit(s, ev, { t: 'wind', side, card: name }); return; }
  mResolveOpen(s, side, name, ev);
  if (!c.basic) p.discard.push(name);
}
function mEndTurn(s, ev) {
  if (s.version !== 'open' || s.winner !== null) throw new Error('endTurn: match over');
  s.turn = 1 - s.turn;
  mStartTurn(s, ev);
}

export function playAction(s, name, ev) { const t = clone(s); mPlay(t, name, ev); return t; }
export function endTurn(s, ev) { const t = clone(s); mEndTurn(t, ev); return t; }
export function _playInPlace(t, name) { mPlay(t, name, null); return t; }
export function _endTurnInPlace(t) { mEndTurn(t, null); return t; }

// =====================================================================
// Public information and invariants
// =====================================================================

// Cards of `side` that are face up: resolved, winding, or committed this round (not cancelled).
export function playedCards(s, side) {
  const p = s.p[side];
  const out = p.discard.concat(p.winding);
  for (const a of p.committed) if (a.status !== 'cancelled' && !CARDS[a.name].basic) out.push(a.name);
  return out;
}

// Per card of a list: total copies, played so far, known in hand, unseen.
export function deckSummary(s, side) {
  const p = s.p[side];
  const played = countNames(playedCards(s, side)), known = countNames(p.known);
  const inHand = countNames(p.hand), inDeck = countNames(p.deck);
  return Object.entries(DECKS[p.hero]).map(([name, total]) => ({
    name, total, played: played[name] || 0, known: known[name] || 0,
    unseen: total - (played[name] || 0) - (known[name] || 0),
    inHand: inHand[name] || 0, inDeck: inDeck[name] || 0,
  }));
}

export function checkInvariants(s) {
  const errs = [];
  for (const i of [0, 1]) {
    const p = s.p[i];
    const tag = 'side ' + i + ': ';
    if (!(p.hp <= p.maxHp)) errs.push(tag + 'hp above max ' + p.hp);
    if (!Number.isInteger(p.mana) || p.mana < 0 || p.mana > MANA_CAP) errs.push(tag + 'mana out of range ' + p.mana);
    if (p.actions > 2) errs.push(tag + 'more than 2 actions');
    if (p.sharpen < 0) errs.push(tag + 'negative sharpen');
    const all = countNames(p.hand.concat(p.deck, playedCards(s, i)));
    const want = DECKS[p.hero];
    for (const n of new Set(Object.keys(all).concat(Object.keys(want)))) if ((all[n] || 0) !== (want[n] || 0)) errs.push(tag + 'card count of ' + n + ' is ' + (all[n] || 0) + ', list has ' + (want[n] || 0));
    const hand = countNames(p.hand), known = countNames(p.known);
    for (const n in known) if ((hand[n] || 0) < known[n]) errs.push(tag + 'known card not in hand ' + n);
    for (const g of p.guards) if (!['Block', 'Parry', 'Brace'].includes(g.type)) errs.push(tag + 'bad guard');
    if (s.version === 'hidden' && p.winding.length) errs.push(tag + 'winding in Hidden');
    if (s.version === 'open' && s.winner === null && i === s.turn && p.winding.length > p.actions) errs.push(tag + 'winding cards older than this turn');
  }
  if (s.winner === null && (s.p[0].hp <= 0 || s.p[1].hp <= 0)) errs.push('a hero is at 0 but the match goes on');
  return errs;
}
