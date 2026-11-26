// node selftest.mjs [--quick]
// Unit checks of the rules, then bot matches in parallel workers. Uses the same src/engine.js and src/bot.js the page is built from.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { availableParallelism } from 'node:os';
import * as E from './src/engine.js';
import * as B from './src/bot.js';

const MAX_ROUNDS = 60;
const evalArg = process.argv.find((a) => a.startsWith('--eval='));
const EVAL_OVERRIDE = evalArg ? JSON.parse(evalArg.slice(7)) : null;
if (EVAL_OVERRIDE) Object.assign(B.EVAL, EVAL_OVERRIDE);
const hpArg = process.argv.find((a) => a.startsWith('--hp='));
const HP_OVERRIDE = hpArg ? hpArg.slice(5).split(',').map(Number) : null;
const deckArg = process.argv.find((a) => a.startsWith('--deck='));
const DECK_OVERRIDE = deckArg ? deckArg.slice(7) : null;   // e.g. Heavy:Haymaker=2,Slash=2;Quick:Meditate=1,Smash=2
function applyDeck(spec) {
  if (!spec) return;
  for (const part of spec.split(';')) { const [hero, list] = part.split(':'); for (const kv of list.split(',')) { const [c, n] = kv.split('='); E.DECKS[hero][c] = +n; } }
  for (const h of ['Heavy', 'Quick']) if (E.deckList(h).length !== 20) throw new Error(h + ' deck is not 20 cards');
}
applyDeck(DECK_OVERRIDE);
function applyHp(hp) { if (hp) { E.HEROES.Heavy.hp = hp[0]; E.HEROES.Quick.hp = hp[1]; } }
applyHp(HP_OVERRIDE);

// ---------------------------------------------------------------- matches
function checkInvariants(s) {
  for (const q of s.p) {
    if (!(q.hp <= q.maxHp)) throw new Error('health above start');
    if (q.mana < 0 || q.mana > E.MANA_CAP || !Number.isInteger(q.mana)) throw new Error('mana out of range ' + q.mana);
    if (!(q.pos >= 0 && q.pos < 9)) throw new Error('position off the area');
    if (q.hand.length + q.deck.length + q.discard.length !== 20) throw new Error('cards not conserved');
    const h = q.hand.slice();
    for (const k of q.known) { const i = h.indexOf(k); if (i < 0) throw new Error('known card not in hand'); h.splice(i, 1); }
    const all = [...q.hand, ...q.deck, ...q.discard].sort().join();
    if (all !== E.deckList(q.hero).sort().join()) throw new Error('deck contents changed');
    if (q.sharpen < 0) throw new Error('sharpen negative');
  }
  if (s.over !== (s.p[0].hp <= 0 || s.p[1].hp <= 0)) throw new Error('over flag wrong');
}

function playMatch(heroes, seed, pickers) {
  const rng = E.makeRng(seed * 7919 + 13);
  let s = E.newMatch(heroes[0], heroes[1], seed);
  const st = { outcomes: {}, cols: [[0, 0, 0], [0, 0, 0]], rounds: 0, fatigue: [0, 0], fatigueRounds: 0 };
  while (!s.over && s.round < MAX_ROUNDS) {
    s = E.startRound(s);
    for (let side = 0; side < 2; side++) if (s.fatigueTaken[side]) st.fatigue[side] = (st.fatigue[side] || 0) + s.fatigueTaken[side];
    if (s.over) { checkInvariants(s); st.endedByFatigue = true; break; }
    const ch = [pickers[0](s, 0, rng), pickers[1](s, 1, rng)];
    for (let side = 0; side < 2; side++) { const err = E.checkChoice(s, side, ch[side]); if (err) throw new Error('picker made illegal choice: ' + err); }
    const before = s;
    const r = E.resolveRound(s, ch);
    s = r.state;
    if (before.p[0].pos !== s.p[0].pos && !E.NEIGHBOURS[before.p[0].pos].includes(s.p[0].pos)) throw new Error('illegal move');
    checkInvariants(s);
    for (const e of r.events) {
      if (e.k === 'attack') { const k = e.outcome === 'miss' ? 'miss-' + e.reason : e.outcome; st.outcomes[k] = (st.outcomes[k] || 0) + 1; }
      if (e.k === 'cancel' && E.isAttack(e.card)) st.outcomes.cancelled = (st.outcomes.cancelled || 0) + 1;
    }
    for (let side = 0; side < 2; side++) st.cols[side][E.colOf(s.p[side].pos)]++;
    if (s.p[0].deck.length === 0 && s.p[1].deck.length === 0) st.fatigueRounds++;
  }
  st.rounds = s.round;
  st.over = s.over;
  st.winner = s.winner;
  if (!s.over) st.stall = { hp: s.p.map((q) => q.hp), cols: s.p.map((q) => E.colOf(q.pos)), decks: s.p.map((q) => q.deck.length), hands: s.p.map((q) => q.hand.length) };
  return st;
}

const PICKERS = {
  bot: (s, side, rng) => B.botChoose(s, side, rng).choice,
  random: (s, side, rng) => B.randomChoose(s, side, rng),
  greedy: (s, side) => B.greedyChoose(s, side),
};

function runJob(job) {
  const pickers = [PICKERS[job.p0], PICKERS[job.p1]];
  try { return { job, ...playMatch(job.heroes, job.seed, pickers) }; }
  catch (err) { return { job, crash: String(err && err.stack || err) }; }
}

if (!isMainThread) {
  if (workerData.eval) Object.assign(B.EVAL, workerData.eval);
  applyHp(workerData.hp);
  applyDeck(workerData.deck);
  const out = workerData.jobs.map(runJob);
  parentPort.postMessage(out);
} else {
  main();
}

// ---------------------------------------------------------------- unit checks
function unitChecks() {
  const results = [];
  const check = (name, cond) => results.push([name, !!cond]);
  const base = (h0 = 'Heavy', h1 = 'Quick') => {
    const s = E.newMatch(h0, h1, 1);
    // unit checks run at fixed health (Heavy 34, Quick 26), independent of the current hero numbers
    for (const q of s.p) { q.hand = []; q.deck = E.deckList(q.hero); q.discard = []; q.known = []; q.mana = 10; q.hp = q.maxHp = q.hero === 'Heavy' ? 34 : 26; }
    s.round = 1;
    return s;
  };
  const give = (s, side, cards) => { for (const c of cards) { E.deckList(s.p[side].hero); const i = s.p[side].deck.indexOf(c); if (i >= 0) s.p[side].deck.splice(i, 1); s.p[side].hand.push(c); } };
  const T = (c, r) => E.tileOf(c, r);
  const M = (...t) => E.maskOf(t);
  const run = (s, c0, c1) => E.resolveRound(s, [c0, c1]);
  const none = { actions: [], step: null };
  const att = (ev, side) => ev.filter((e) => e.k === 'attack' && e.side === side);

  // order of a round
  {
    const s = base('Quick', 'Quick');
    give(s, 0, ['Lunge', 'Slash', 'Smash', 'Bolt']); give(s, 1, ['Bolt']);
    s.p[0].pos = T(0, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }, { card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null },
      { actions: [{ card: 'Bolt', tiles: M(T(0, 0)) }], step: T(1, 1) });
    const phases = r.events.filter((e) => e.k === 'phase').map((e) => e.ph);
    check('round order: reveal, fast, step, normal, slow', phases.join() === 'reveal,fast,step,normal,slow');
    const seq = r.events.filter((e) => e.k === 'attack' || e.k === 'step').map((e) => e.k === 'step' ? 'step' : e.card);
    check('fast attack before steps, normal and slow after', seq.join() === 'Jab,step,Bolt,Smash');
  }
  // fast hits start tile, normal/slow hit tile after the step
  {
    const s = base();
    give(s, 0, ['Lunge', 'Slash']); s.p[0].pos = T(0, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }], step: null }, { actions: [], step: T(0, 0) });
    check('Fast attack hits the tile the enemy stood on at the start', att(r.events, 0)[0].outcome === 'hit' && r.state.p[1].hp === 22);
    const s2 = base(); give(s2, 0, ['Slash']); s2.p[0].pos = T(0, 1); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: null }, { actions: [], step: T(1, 1) });
    const a2 = att(r2.events, 0)[0];
    check('Normal attack hits where he stands after stepping (missed: he left the column)', a2.outcome === 'miss' && a2.reason === 'moved' && r2.state.p[1].hp === 26);
    const s3 = base(); give(s3, 0, ['Smash']); s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Smash', tiles: M(1, 2, 4, 5) }], step: null }, { actions: [], step: T(0, 2) });
    check('Slow attack hits the tile after the step', att(r3.events, 0)[0].outcome === 'hit' && r3.state.p[1].hp === 18);
  }
  // legal shapes
  {
    const ok = (card, tiles) => { const s = base(); give(s, 0, [card]); return E.checkChoice(s, 0, { actions: [{ card, tiles: E.maskOf(tiles) }], step: null }) === null; };
    check('Jab: any one front tile, nothing else', ok('Jab', [0]) && ok('Jab', [2]) && !ok('Jab', [3]) && !ok('Jab', [0, 1]));
    check('Slash: only the whole front column', ok('Slash', [0, 1, 2]) && !ok('Slash', [0]) && !ok('Slash', [3, 4, 5]));
    check('Lunge: one whole lane (all three tiles)', ok('Lunge', [0, 3, 6]) && ok('Lunge', [2, 5, 8]) && !ok('Lunge', [0, 3]) && !ok('Lunge', [0, 1, 2]) && !ok('Lunge', [0]));
    check('Flurry: two different front tiles', ok('Flurry', [0, 1]) && ok('Flurry', [0, 2]) && !ok('Flurry', [0]) && !ok('Flurry', [0, 3]) && !ok('Flurry', [0, 1, 2]));
    check('Smash: a 2x2 block anywhere', ok('Smash', [0, 1, 3, 4]) && ok('Smash', [1, 2, 4, 5]) && ok('Smash', [3, 4, 6, 7]) && ok('Smash', [4, 5, 7, 8]) && !ok('Smash', [0, 2, 3, 5]) && !ok('Smash', [0, 1, 6, 7]) && !ok('Smash', [0, 1, 2, 3]));
    check('Haymaker: the whole front and middle columns', ok('Haymaker', [0, 1, 2, 3, 4, 5]) && !ok('Haymaker', [0, 1, 2, 3, 4, 5, 6, 7, 8]) && !ok('Haymaker', [0, 1, 2]));
    check('Bolt: any single tile', [0, 1, 2, 3, 4, 5, 6, 7, 8].every((t) => ok('Bolt', [t])) && !ok('Bolt', [0, 1]));
    check('Blast: one whole lane', ok('Blast', [0, 3, 6]) && ok('Blast', [2, 5, 8]) && !ok('Blast', [0, 1, 2]) && !ok('Blast', [0, 3]));
    check('shape counts 3,1,3,3,4,1,9,3', ['Jab', 'Slash', 'Lunge', 'Flurry', 'Smash', 'Haymaker', 'Bolt', 'Blast'].map((c) => E.SHAPES[c].length).join() === '3,1,3,3,4,1,9,3');
  }
  // melee needs the front column when it resolves; ranged works from anywhere
  {
    const s = base(); give(s, 0, ['Slash']); s.p[0].pos = T(1, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: T(0, 1) }, none);
    check('melee Normal works after stepping into the front', att(r.events, 0)[0].outcome === 'hit');
    const s2 = base(); s2.p[0].pos = T(1, 1); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }], step: T(0, 1) }, none);
    check('melee Fast from the middle does nothing even when stepping forward, mana spent', att(r2.events, 0)[0].outcome === 'nothing' && r2.state.p[0].mana === 9 && r2.state.p[1].hp === 26);
    const s3 = base(); give(s3, 0, ['Slash']); s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: T(1, 1) }, none);
    check('melee Normal after stepping out of the front does nothing, card spent', att(r3.events, 0)[0].outcome === 'nothing' && r3.state.p[0].discard.includes('Slash') && r3.state.p[0].mana === 8);
    const s4 = base(); give(s4, 0, ['Bolt', 'Blast']); s4.p[0].pos = T(2, 0); s4.p[1].pos = T(2, 2);
    const r4 = run(s4, { actions: [{ card: 'Bolt', tiles: M(T(2, 2)) }, { card: 'Blast', tiles: M(2, 5, 8) }], step: null }, none);
    check('ranged works from the back to the back', att(r4.events, 0).every((e) => e.outcome === 'hit') && r4.state.p[1].hp === 26 - 10);
  }
  // a miss does nothing and cancels nothing
  {
    const s = base(); give(s, 0, ['Slash']); give(s, 1, ['Smash']); s.p[0].pos = T(0, 0); s.p[1].pos = T(1, 1);
    const r = run(s, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: null }, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: T(0, 1) });
    // Quick steps into the front, Slash (Normal) hits it -> cancels the Smash. Now the miss case:
    const s2 = base(); give(s2, 0, ['Bolt']); give(s2, 1, ['Smash']); s2.p[0].pos = T(0, 0); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Bolt', tiles: M(T(2, 2)) }], step: null }, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null });
    check('a miss deals nothing and cancels nothing', att(r2.events, 0)[0].outcome === 'miss' && r2.state.p[1].hp === 26 && att(r2.events, 1)[0].outcome === 'hit');
    check('a hit cancels the Slow card (control case)', r.events.some((e) => e.k === 'cancel' && e.card === 'Smash'));
  }
  // guards
  {
    const s = base(); give(s, 1, ['Lunge']); s.p[0].pos = T(0, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Block', tiles: 0 }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }, { card: 'Lunge', tiles: M(1, 4, 7) }], step: null });
    const a = att(r.events, 1);
    check('Block stops only the first Light hit', a[0].outcome === 'blocked' && a[1].outcome === 'hit' && r.state.p[0].hp === 30);
    const s2 = base(); give(s2, 0, ['Parry']); give(s2, 1, ['Lunge']); s2.p[0].pos = T(0, 1); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Parry', tiles: 0 }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }, { card: 'Lunge', tiles: M(1, 4, 7) }], step: null });
    const a2 = att(r2.events, 1);
    check('Parry stops only the first Light hit and its attacker takes 3', a2[0].outcome === 'blocked' && a2[1].outcome === 'hit' && r2.state.p[0].hp === 30 && r2.state.p[1].hp === 23);
    const s3 = base(); give(s3, 0, ['Brace']); give(s3, 1, ['Lunge', 'Slash']); s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Brace', tiles: 0 }], step: null }, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }, { card: 'Slash', tiles: M(0, 1, 2) }], step: null });
    check('Brace stops every Light hit, across steps', att(r3.events, 1).every((e) => e.outcome === 'blocked') && r3.state.p[0].hp === 34);
    const s4 = base(); give(s4, 0, ['Brace']); give(s4, 1, ['Smash']); s4.p[0].pos = T(0, 1); s4.p[1].pos = T(0, 1);
    const r4 = run(s4, { actions: [{ card: 'Brace', tiles: 0 }], step: null }, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null });
    check('Heavy attacks ignore guards', att(r4.events, 1)[0].outcome === 'hit' && r4.state.p[0].hp === 26);
    const s6 = base(); give(s6, 0, ['Parry']); give(s6, 1, ['Smash']); s6.p[0].pos = T(0, 1); s6.p[1].pos = T(0, 1);
    const r6 = run(s6, { actions: [{ card: 'Parry', tiles: 0 }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }, { card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null });
    check('Parry reflect deals 3 but cancels nothing', r6.state.p[1].hp === 23 && !r6.events.some((e) => e.k === 'cancel') && att(r6.events, 1)[1].outcome === 'hit');
  }
  // Flurry is two separate hits on two tiles
  {
    const s = base(); give(s, 1, ['Flurry']); s.p[0].pos = T(0, 0); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Block', tiles: 0 }], step: null }, { actions: [{ card: 'Flurry', tiles: M(0, 1) }], step: null });
    check('Flurry: only the hit on his tile can land (Block stops it)', att(r.events, 1)[0].outcome === 'blocked' && r.state.p[0].hp === 34);
    const s2 = base(); give(s2, 1, ['Flurry']); s2.p[0].pos = T(0, 2); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, none, { actions: [{ card: 'Flurry', tiles: M(1, 2) }], step: null });
    check('Flurry: one hit of 2 on the tile he stands on', r2.state.p[0].hp === 32);
    const s3 = base(); give(s3, 1, ['Flurry']); s3.p[0].pos = T(1, 0); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, none, { actions: [{ card: 'Flurry', tiles: M(0, 1) }], step: null });
    check('Flurry: misses when he is on neither tile', att(r3.events, 1)[0].outcome === 'miss' && r3.state.p[0].hp === 34);
  }
  // cancelling
  {
    const s = base('Quick', 'Quick'); give(s, 0, ['Smash', 'Bandage']); give(s, 1, ['Slash']); s.p[0].pos = T(0, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }, { card: 'Bandage', tiles: 0 }], step: null }, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: null });
    const q = r.state.p[0];
    check('damage cancels unresolved Slow cards: back to hand, mana stays spent', q.hand.includes('Smash') && q.hand.includes('Bandage') && q.mana === 4 && r.state.p[1].hp === 26 && q.known.length === 2);
    const s2 = base('Quick', 'Quick'); give(s2, 0, ['Slash']); give(s2, 1, ['Slash', 'Lunge']); s2.p[0].pos = T(0, 1); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Slash', tiles: M(0, 1, 2) }], step: null }, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }], step: null });
    check('Fast and Normal cards are never cancelled', att(r2.events, 0)[0].outcome === 'hit');
    const s3 = base('Quick', 'Quick'); give(s3, 0, ['Smash']); give(s3, 1, ['Smash']); s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null });
    check('Slow attacks in the same step do not cancel each other', att(r3.events, 0)[0].outcome === 'hit' && att(r3.events, 1)[0].outcome === 'hit');
  }
  // Heavy's passive
  {
    const s = base('Heavy', 'Quick'); give(s, 0, ['Smash']); s.p[0].pos = T(0, 1); s.p[1].pos = T(0, 1);
    const r = run(s, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }], step: null });
    check('Heavy: 2 damage does not cancel his Smash', att(r.events, 0)[0].outcome === 'hit' && r.state.p[1].hp === 18);
    const s2 = base('Heavy', 'Quick'); give(s2, 0, ['Smash']); give(s2, 1, ['Lunge']); s2.p[0].pos = T(0, 1); s2.p[1].pos = T(0, 1);
    const r2 = run(s2, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }], step: null });
    check('Heavy: 4 damage does cancel', r2.events.some((e) => e.k === 'cancel' && e.card === 'Smash'));
    const s3 = base('Heavy', 'Quick'); give(s3, 0, ['Smash']); s3.p[1].sharpen = 1; s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }], step: null });
    check('Heavy: a sharpened Jab (3) cancels', r3.events.some((e) => e.k === 'cancel'));
    const s4 = base('Quick', 'Quick'); give(s4, 0, ['Smash']); s4.p[0].pos = T(0, 1); s4.p[1].pos = T(0, 1);
    const r4 = run(s4, { actions: [{ card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, { actions: [{ card: 'Jab', tiles: M(T(0, 1)) }], step: null });
    check('Quick: 2 damage cancels', r4.events.some((e) => e.k === 'cancel'));
  }
  // Quick's passive
  {
    check('Quick: first Fast action costs 1 less', E.choiceCost('Quick', [{ card: 'Jab' }, { card: 'Block' }]) === 1 && E.choiceCost('Quick', [{ card: 'Lunge' }]) === 2);
    check('Quick: only the first Fast action; never on Normal or Slow', E.choiceCost('Quick', [{ card: 'Slash' }]) === 2 && E.choiceCost('Quick', [{ card: 'Lunge' }, { card: 'Jab' }]) === 3);
    check('Heavy: no discount', E.choiceCost('Heavy', [{ card: 'Jab' }, { card: 'Block' }]) === 2);
    const s = base('Quick', 'Heavy'); give(s, 0, ['Lunge']); s.p[0].mana = 2;
    check('Quick: Lunge affordable with 2 mana', E.checkChoice(s, 0, { actions: [{ card: 'Lunge', tiles: M(0, 3, 6) }], step: null }) === null);
  }
  // steps
  {
    const s = base();
    const legal = (from) => { s.p[0].pos = from; return [0, 1, 2, 3, 4, 5, 6, 7, 8].filter((t) => E.checkChoice(s, 0, { actions: [], step: t }) === null); };
    check('steps from the centre: 4 orthogonal tiles', legal(4).join() === '1,3,5,7');
    check('steps from a corner: 2 tiles, never diagonal, never off the area', legal(0).join() === '1,3' && legal(8).join() === '5,7');
    check('steps from an edge: 3 tiles', legal(T(0, 1)).join() === '0,2,4');
    s.p[0].pos = 4;
    const stayStep = E.checkChoice(s, 0, { actions: [], step: 4 });
    s.p[0].pos = 0;
    check('no step to the own tile or two away', stayStep !== null && E.checkChoice(s, 0, { actions: [], step: 6 }) !== null && E.checkChoice(s, 0, { actions: [], step: 2 }) !== null);
  }
  // decks
  {
    const count = (h) => { const d = {}; for (const c of E.deckList(h)) d[c] = (d[c] || 0) + 1; return d; };
    const h = count('Heavy'), q = count('Quick');
    check('Heavy grid deck: base minus 1 Slash, 1 Flurry, 1 Smash, plus 2 Bolt, 1 Blast; then 1 Haymaker for 1 Slash',
      E.deckList('Heavy').length === 20 && h.Slash === 2 && h.Flurry === 1 && h.Smash === 2 && h.Bolt === 2 && h.Blast === 1 && h.Lunge === 1 && h.Haymaker === 2 && h.Parry === 2 && h.Brace === 2 && h.Meditate === 1 && h.Bandage === 2 && h.Sharpen === 1 && h.Study === 1);
    check('Quick grid deck: base minus 1 Slash, 1 Flurry, 1 Smash, plus 2 Bolt, 1 Blast; then 1 Meditate for 1 Smash',
      E.deckList('Quick').length === 20 && q.Slash === 2 && q.Flurry === 2 && q.Smash === 2 && q.Bolt === 2 && q.Blast === 1 && q.Lunge === 3 && !q.Haymaker && q.Parry === 3 && q.Brace === 1 && q.Meditate === 1 && q.Bandage === 1 && q.Sharpen === 1 && q.Study === 1);
    const m = E.newMatch('Heavy', 'Quick', 5), r1 = E.startRound(m);
    check('opening hand 4, then draw 1 in round 1; mana 10', m.p[0].hand.length === 4 && r1.p[0].hand.length === 5 && r1.p[0].mana === 10);
  }
  // reach: melee reaches the back column now, still only from the attacker's front column
  {
    const s = base(); give(s, 0, ['Haymaker']); s.p[0].pos = T(0, 1); s.p[1].pos = T(1, 2);
    const r = run(s, { actions: [{ card: 'Haymaker', tiles: M(0, 1, 2, 3, 4, 5) }], step: null }, { actions: [], step: T(2, 2) });
    check('Haymaker: a hero in the middle column dodges it by stepping back', att(r.events, 0)[0].outcome === 'miss' && r.state.p[1].hp === 26);
    const sf = base(); give(sf, 0, ['Haymaker']); sf.p[0].pos = T(0, 1); sf.p[1].pos = T(0, 2);
    const rf = run(sf, { actions: [{ card: 'Haymaker', tiles: M(0, 1, 2, 3, 4, 5) }], step: null }, { actions: [], step: T(1, 2) });
    check('Haymaker: a hero in the front column cannot step out of it', att(rf.events, 0)[0].outcome === 'hit' && rf.state.p[1].hp === 14);
    const ss = base(); give(ss, 0, ['Smash']); ss.p[0].pos = T(0, 1); ss.p[1].pos = T(2, 2);
    const rs = run(ss, { actions: [{ card: 'Smash', tiles: M(4, 5, 7, 8) }], step: null }, none);
    check('Smash reaches the back column', att(rs.events, 0)[0].outcome === 'hit' && rs.state.p[1].hp === 18);
    const s2 = base(); give(s2, 0, ['Lunge']); s2.p[0].pos = T(0, 0); s2.p[1].pos = T(2, 0);
    const r2 = run(s2, { actions: [{ card: 'Lunge', tiles: M(0, 3, 6) }], step: null }, none);
    check('Lunge hits the back tile of its lane', att(r2.events, 0)[0].outcome === 'hit' && r2.state.p[1].hp === 22);
    const s3 = base(); give(s3, 0, ['Haymaker']); s3.p[0].pos = T(1, 1); s3.p[1].pos = T(1, 2);
    const r3 = run(s3, { actions: [{ card: 'Haymaker', tiles: M(0, 1, 2, 3, 4, 5) }], step: null }, none);
    check('Haymaker from the middle column does nothing', att(r3.events, 0)[0].outcome === 'nothing' && r3.state.p[1].hp === 26);
  }
  // fatigue
  {
    const s = base('Heavy', 'Quick');
    s.p[0].deck = []; s.p[0].discard = E.deckList('Heavy');
    const r1 = E.startRound(s), r2 = E.startRound(r1), r3 = E.startRound(r2);
    check('fatigue: empty deck deals 1, then 2, then 3, instead of drawing', r1.p[0].hp === 33 && r2.p[0].hp === 31 && r3.p[0].hp === 28 && r3.fatigueTaken[0] === 3 && r3.p[0].hand.length === 0);
    check('fatigue: counted per hero; a hero who still draws takes none', r3.p[1].hp === 26 && r3.fatigueTaken[1] === 0 && r3.p[1].hand.length === 3);
    const d = base('Quick', 'Quick');
    for (const q of d.p) { q.deck = []; q.discard = E.deckList('Quick'); q.hp = 1; }
    const rd = E.startRound(d);
    check('fatigue: both at 0 in the same round is a draw', rd.over && rd.winner === 'draw');
    const w = base('Quick', 'Quick');
    for (const q of w.p) { q.deck = []; q.discard = E.deckList('Quick'); }
    w.p[0].hp = 1; w.p[1].hp = 5;
    const rw = E.startRound(w);
    check('fatigue: a hero at 0 loses at the start of the round', rw.over && rw.winner === 1);
  }
  // other basics
  {
    const s = base(); s.p[1].pos = T(0, 1); s.p[0].pos = T(0, 1);
    check('a basic only once a round', E.checkChoice(s, 0, { actions: [{ card: 'Jab', tiles: 1 << 1 }, { card: 'Jab', tiles: 1 << 1 }], step: null }) !== null);
    s.p[0].mana = 1;
    check('total cost must be affordable', E.checkChoice(s, 0, { actions: [{ card: 'Jab', tiles: 1 << 1 }, { card: 'Block', tiles: 0 }], step: null }) !== null);
    const s2 = base('Quick', 'Quick'); give(s2, 0, ['Lunge']); give(s2, 1, ['Lunge']); s2.p[0].pos = T(0, 1); s2.p[1].pos = T(0, 1); s2.p[0].hp = 4; s2.p[1].hp = 4;
    const r2 = run(s2, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }], step: null }, { actions: [{ card: 'Lunge', tiles: M(1, 4, 7) }], step: null });
    check('both at 0 in the same step: draw', r2.state.over && r2.state.winner === 'draw');
    const s3 = base('Quick', 'Quick'); give(s3, 0, ['Sharpen', 'Smash']); s3.p[0].pos = T(0, 1); s3.p[1].pos = T(0, 1);
    const r3 = run(s3, { actions: [{ card: 'Sharpen', tiles: 0 }, { card: 'Smash', tiles: M(0, 1, 3, 4) }], step: null }, none);
    check('Sharpen counts from later steps (same-step Smash deals 8), stacks after', r3.state.p[1].hp === 18 && r3.state.p[0].sharpen === 1);
    const s4 = base('Quick', 'Quick'); give(s4, 0, ['Bandage']); s4.p[0].hp = 24;
    const r4 = run(s4, { actions: [{ card: 'Bandage', tiles: 0 }], step: null }, none);
    check('Bandage never above starting health', r4.state.p[0].hp === 26);
    const s5 = base('Quick', 'Quick'); s5.p[0].deck = []; give(s5, 0, []); s5.p[0].hand = ['Study']; s5.p[0].discard = E.deckList('Quick'); s5.p[0].discard.splice(s5.p[0].discard.indexOf('Study'), 1);
    const r5 = E.startRound(s5);
    check('empty deck: nothing drawn, fatigue 1 instead', r5.p[0].hand.length === 1 && r5.p[0].hp === 25);
  }
  // the bot sees only public information
  {
    const s = E.startRound(E.newMatch('Heavy', 'Quick', 9));
    const v = B.publicView(s, 0);
    const str = JSON.stringify(v);
    check('public view hides the opponent hand and deck order', v.op.hand === undefined && v.op.deck === undefined && v.op.handCount === s.p[1].hand.length && !('deck' in v.me));
    const s2 = E.cloneState(s); s2.p[1].hand = s2.p[1].hand.map(() => 'Haymaker' === s2.p[1].hand[0] ? 'Slash' : 'Slash');
    s2.p[1].deck = E.shuffle(s2.p[1].deck, E.makeRng(99));
    const a = B.botChoose(s, 0, E.makeRng(42)).choice, b = B.botChoose(s2, 0, E.makeRng(42)).choice;
    check('bot choice is identical when only hidden information differs', JSON.stringify(a) === JSON.stringify(b) && str.length > 0);
  }
  return results;
}

// ---------------------------------------------------------------- main
var currentHp;
async function runPool(jobs) {
  const n = Math.max(1, availableParallelism() - 1);
  const chunks = Array.from({ length: n }, () => []);
  jobs.forEach((j, i) => chunks[i % n].push(j));
  const parts = await Promise.all(chunks.filter((c) => c.length).map((c) => new Promise((res, rej) => {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: c, eval: EVAL_OVERRIDE, hp: currentHp ?? HP_OVERRIDE, deck: DECK_OVERRIDE } });
    w.once('message', res); w.once('error', rej);
  })));
  return parts.flat();
}

const pct = (a, b) => (b ? (100 * a / b).toFixed(1) + '%' : 'n/a');

// node selftest.mjs --sweep=31,28:30,29:... --n=300  ->  Heavy v Quick bot matches per health setting, both seats
async function sweep(arg, n) {
  for (const pair of arg.split(':')) {
    currentHp = pair.split(',').map(Number);
    const jobs = [];
    for (let i = 0; i < n; i++) jobs.push({ set: 'sweep', heroes: i % 2 ? ['Heavy', 'Quick'] : ['Quick', 'Heavy'], p0: 'bot', p1: 'bot', seed: 100000 + i });
    const res = await runPool(jobs);
    let h = 0, q = 0, d = 0, u = 0, crash = 0, rounds = 0;
    for (const r of res) {
      if (r.crash) { crash++; continue; }
      rounds += r.rounds;
      if (!r.over) u++; else if (r.winner === 'draw') d++; else if (r.job.heroes[r.winner] === 'Heavy') h++; else q++;
    }
    console.log(`${DECK_OVERRIDE ? 'decks ' + DECK_OVERRIDE + ', ' : ''}Heavy ${currentHp[0]} / Quick ${currentHp[1]}: ${res.length} matches, Heavy ${pct(h, h + q)} of decided, Quick ${pct(q, h + q)}, draws ${d}, unfinished ${u}, crashes ${crash}, avg ${(rounds / res.length).toFixed(1)} rounds`);
  }
}

async function main() {
  const sweepArg = process.argv.find((a) => a.startsWith('--sweep='));
  if (sweepArg) { const nArg = process.argv.find((a) => a.startsWith('--n=')); return sweep(sweepArg.slice(8), nArg ? +nArg.slice(4) : 300); }
  const quick = process.argv.includes('--quick');
  const t0 = Date.now();
  const unit = unitChecks();
  const failed = unit.filter((u) => !u[1]);
  console.log(`Unit checks: ${unit.length - failed.length}/${unit.length} pass`);
  for (const [name, ok] of unit) console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}`);

  const nArg = process.argv.find((a) => a.startsWith('--n='));
  const nBvB = nArg ? +nArg.slice(4) : quick ? 100 : 500, nRef = nArg ? +nArg.slice(4) : quick ? 100 : 500;
  const pairs = [['Heavy', 'Heavy'], ['Heavy', 'Quick'], ['Quick', 'Heavy'], ['Quick', 'Quick']];
  const jobs = [];
  let seed = 1;
  for (const heroes of pairs) for (let i = 0; i < nBvB; i++) jobs.push({ set: 'bvb', heroes, p0: 'bot', p1: 'bot', seed: seed++ });
  for (const ref of ['random', 'greedy']) for (let i = 0; i < nRef; i++) {
    const heroes = pairs[i % 4], botSide = (i >> 2) % 2;
    jobs.push({ set: ref, heroes, botSide, p0: botSide === 0 ? 'bot' : ref, p1: botSide === 0 ? ref : 'bot', seed: seed++ });
  }
  const res = await runPool(jobs);

  const crashes = res.filter((r) => r.crash);
  const bvb = res.filter((r) => r.job.set === 'bvb' && !r.crash);
  const unfinished = bvb.filter((r) => !r.over);
  console.log(`\nBot vs bot: ${bvb.length + crashes.filter((r) => r.job.set === 'bvb').length} matches (${nBvB} per pairing, ${MAX_ROUNDS}-round limit)`);
  console.log(`  crashes or illegal states: ${crashes.length}`);
  for (const c of crashes.slice(0, 3)) console.log('   ', c.job.set, c.job.heroes.join('-'), 'seed', c.job.seed, c.crash.split('\n')[0]);
  console.log(`  matches not ended within ${MAX_ROUNDS} rounds: ${unfinished.length} (${pct(unfinished.length, bvb.length)})`);
  if (unfinished.length) {
    const decksEmpty = unfinished.filter((r) => r.stall.decks[0] === 0 && r.stall.decks[1] === 0).length;
    const someoneBack = unfinished.filter((r) => r.stall.cols.some((c) => c === 2)).length;
    const someoneNotFront = unfinished.filter((r) => r.stall.cols.some((c) => c > 0)).length;
    console.log(`    with both decks empty at round ${MAX_ROUNDS}: ${decksEmpty}; a hero out of the front column: ${someoneNotFront}; a hero in the back column: ${someoneBack}`);
    for (const r of unfinished.slice(0, 3)) console.log(`    e.g. ${r.job.heroes.join(' v ')} seed ${r.job.seed}: health ${r.stall.hp.join('/')}, columns ${r.stall.cols.join('/')}, hands ${r.stall.hands.join('/')}`);
  }
  const ended = bvb.filter((r) => r.over);
  const avg = (xs) => xs.reduce((a, b) => a + b, 0) / (xs.length || 1);
  console.log(`  average match length: ${avg(ended.map((r) => r.rounds)).toFixed(1)} rounds (ended matches), ${avg(bvb.map((r) => r.rounds)).toFixed(1)} counting unfinished as ${MAX_ROUNDS}`);
  const hq = bvb.filter((r) => r.job.heroes[0] !== r.job.heroes[1]);
  let hw = 0, qw = 0, dr = 0, un = 0;
  for (const r of hq) {
    if (!r.over) { un++; continue; }
    if (r.winner === 'draw') { dr++; continue; }
    if (r.job.heroes[r.winner] === 'Heavy') hw++; else qw++;
  }
  console.log(`  Heavy v Quick (${hq.length}): Heavy wins ${pct(hw, hq.length)}, Quick wins ${pct(qw, hq.length)}, draws ${pct(dr, hq.length)}, unfinished ${pct(un, hq.length)}; of decided matches Heavy ${pct(hw, hw + qw)}, Quick ${pct(qw, hw + qw)}`);
  const withFat = bvb.filter((r) => r.fatigue[0] + r.fatigue[1] > 0).length;
  console.log(`  matches where fatigue dealt damage: ${pct(withFat, bvb.length)}; ended by fatigue at the start of a round: ${pct(bvb.filter((r) => r.endedByFatigue).length, bvb.length)}; longest match ${Math.max(...bvb.map((r) => r.rounds))} rounds`);
  for (const [h0, h1] of pairs.filter(([a, b]) => a === b)) {
    const ms = bvb.filter((r) => r.job.heroes[0] === h0 && r.job.heroes[1] === h1);
    const w0 = ms.filter((r) => r.over && r.winner === 0).length, w1 = ms.filter((r) => r.over && r.winner === 1).length;
    console.log(`  ${h0} mirror (${ms.length}): first seat ${pct(w0, ms.length)}, second seat ${pct(w1, ms.length)}, draws ${pct(ms.filter((r) => r.winner === 'draw').length, ms.length)}, unfinished ${pct(ms.filter((r) => !r.over).length, ms.length)}`);
  }
  const oc = {};
  for (const r of bvb) for (const [k, v] of Object.entries(r.outcomes)) oc[k] = (oc[k] || 0) + v;
  const totalAtt = (oc.hit || 0) + (oc.blocked || 0) + (oc['miss-moved'] || 0) + (oc['miss-never'] || 0) + (oc.nothing || 0);
  console.log(`  attacks resolved: ${totalAtt}`);
  console.log(`    hit ${pct(oc.hit || 0, totalAtt)} | miss, target moved ${pct(oc['miss-moved'] || 0, totalAtt)} | miss, never there ${pct(oc['miss-never'] || 0, totalAtt)} | stopped by a guard ${pct(oc.blocked || 0, totalAtt)} | nothing, attacker out of front ${pct(oc.nothing || 0, totalAtt)}`);
  console.log(`    plus Slow attacks cancelled before resolving: ${oc.cancelled || 0} (${pct(oc.cancelled || 0, totalAtt + (oc.cancelled || 0))} of all attacks played)`);
  const colsBy = { Heavy: [0, 0, 0], Quick: [0, 0, 0] };
  for (const r of bvb) for (let side = 0; side < 2; side++) for (let c = 0; c < 3; c++) colsBy[r.job.heroes[side]][c] += r.cols[side][c];
  for (const h of ['Heavy', 'Quick']) {
    const t = colsBy[h].reduce((a, b) => a + b, 0);
    console.log(`  ${h} column at end of round: front ${pct(colsBy[h][0], t)}, middle ${pct(colsBy[h][1], t)}, back ${pct(colsBy[h][2], t)}`);
  }

  for (const ref of ['random', 'greedy']) {
    const ms = res.filter((r) => r.job.set === ref && !r.crash);
    const w = ms.filter((r) => r.over && r.winner === r.job.botSide).length;
    const l = ms.filter((r) => r.over && r.winner === 1 - r.job.botSide).length;
    const d = ms.filter((r) => r.over && r.winner === 'draw').length;
    console.log(`\nBot vs ${ref} player (${ms.length} matches, all pairings, both seats): bot wins ${pct(w, ms.length)}, loses ${pct(l, ms.length)}, draws ${pct(d, ms.length)}, unfinished ${pct(ms.length - w - l - d, ms.length)}; average ${avg(ms.map((r) => r.rounds)).toFixed(1)} rounds`);
  }
  console.log(`\nHealth: Heavy ${E.HEROES.Heavy.hp}, Quick ${E.HEROES.Quick.hp}. Bot settings: ${JSON.stringify(B.BOT_PARAMS)}, evaluation ${JSON.stringify(B.EVAL)}. Took ${((Date.now() - t0) / 1000).toFixed(0)} s.`);
  if (failed.length || crashes.length) process.exitCode = 1;
}
