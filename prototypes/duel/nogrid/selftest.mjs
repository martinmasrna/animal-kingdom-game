// node selftest.mjs [--quick]
// Unit checks of the rules, then bot-versus-bot, bot-versus-random and
// bot-versus-greedy matches, on the same engine and bot the page uses (src/).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import os from 'node:os';
import * as E from './src/engine.js';
import * as B from './src/bot.js';

// ---------------------------------------------------------------- policies
function randomHidden(s, side, rng) {
  const seen = new Map();
  for (const set of E.legalSets(s, side)) seen.set(set.slice().sort().join('+'), set);
  const sets = [...seen.values()];
  return sets[Math.floor(rng() * sets.length)];
}
function setDamage(p, set) {
  let d = 0;
  for (const n of set) { const c = E.CARDS[n]; if (E.isAttack(n)) d += (c.dmg + p.sharpen) * c.hits; }
  return d;
}
function greedyHidden(s, side) {
  const p = s.p[side];
  let best = [], bd = 0, bc = 0;
  for (const set of E.legalSets(s, side)) {
    if (!set.every(E.isAttack)) continue;
    const d = setDamage(p, set), c = E.seqCost(p, set, false);
    if (d > bd || (d === bd && c < bc)) { best = set; bd = d; bc = c; }
  }
  return best;
}
// Open policies plan their turn at its start and play it one action at a time.
function openSequences(s) {
  const out = [[]];
  for (const a of E.openLegalActions(s)) {
    const t = E.playAction(s, a);
    out.push([a]);
    for (const b of E.openLegalActions(t)) out.push([a, b]);
  }
  return out;
}
function makeOpenPlanner(choose) {
  let plan = null, planTurn = -1;
  return (s, rng) => {
    if (planTurn !== s.turnNo) { plan = choose(s, rng).slice(); planTurn = s.turnNo; }
    while (plan.length && !E.canPlay(s, plan[0])) plan.shift();
    return plan.length ? plan.shift() : null;
  };
}
const randomOpen = () => makeOpenPlanner((s, rng) => { const q = openSequences(s); return q[Math.floor(rng() * q.length)]; });
const greedyOpen = () => makeOpenPlanner((s) => {
  const p = s.p[s.turn];
  let best = [], bd = 0, bc = 0;
  for (const q of openSequences(s)) {
    if (!q.every(E.isAttack)) continue;
    const d = setDamage(p, q), c = E.seqCost(p, q, false);
    if (d > bd || (d === bd && c < bc)) { best = q; bd = d; bc = c; }
  }
  return best;
});

function makePolicy(kind, version) {
  if (version === 'hidden') {
    if (kind === 'bot') return (s, side, rng) => B.botHidden(s, side, rng);
    if (kind === 'random') return (s, side, rng) => randomHidden(s, side, rng);
    return (s, side) => greedyHidden(s, side);
  }
  if (kind === 'bot') return (s, rng) => B.botOpenAction(s, rng);
  return kind === 'random' ? randomOpen() : greedyOpen();
}

// ---------------------------------------------------------------- one match
function runMatch(job) {
  const { version, heroes, kinds, seed } = job;
  const rng = B.makeRng(seed * 7919 + 13);
  const pol = kinds.map(k => makePolicy(k, version));
  const res = { ...job, winner: null, length: 0, error: null, first: null, sets: {}, botMs: [] };
  try {
    let s = E.newMatch({ version, heroes, seed });
    res.first = s.first;
    let guard = 0;
    if (version === 'hidden') {
      while (s.winner === null) {
        if (s.round > E.ROUND_LIMIT) { res.error = 'no result within ' + E.ROUND_LIMIT + ' rounds'; break; }
        const ch = [0, 1].map(i => {
          const t0 = performance.now();
          const c = pol[i](s, i, rng);
          if (kinds[i] === 'bot') { res.botMs.push(performance.now() - t0); const k = c.join('+') || '(nothing)'; res.sets[k] = (res.sets[k] || 0) + 1; }
          return c;
        });
        s = E.playRound(s, ch);
        const errs = E.checkInvariants(s);
        if (errs.length) { res.error = errs.join('; '); break; }
      }
      res.length = s.round;
    } else {
      let turnSeq = [];
      while (s.winner === null) {
        if (Math.max(s.p[0].turns, s.p[1].turns) > E.ROUND_LIMIT) { res.error = 'no result within ' + E.ROUND_LIMIT + ' turns each'; break; }
        if (++guard > 10000) { res.error = 'runaway loop'; break; }
        const side = s.turn;
        const t0 = performance.now();
        const a = pol[side](s, rng);
        if (kinds[side] === 'bot') res.botMs.push(performance.now() - t0);
        if (a === null) {
          if (kinds[side] === 'bot') { const k = turnSeq.join('+') || '(nothing)'; res.sets[k] = (res.sets[k] || 0) + 1; }
          turnSeq = [];
          s = E.endTurn(s);
        } else { turnSeq.push(a); s = E.playAction(s, a); }
        const errs = E.checkInvariants(s);
        if (errs.length) { res.error = errs.join('; '); break; }
      }
      res.length = (s.p[0].turns + s.p[1].turns) / 2;
    }
    res.winner = s.winner;
  } catch (e) { res.error = 'crash: ' + (e && e.stack || e); }
  res.botMs = res.botMs.length ? [Math.max(...res.botMs), res.botMs.reduce((a, b) => a + b, 0), res.botMs.length] : [0, 0, 0];
  return res;
}

// ---------------------------------------------------------------- unit checks
const checks = [];
function check(name, fn) {
  try { const r = fn(); checks.push([name, r === true ? null : String(r)]); }
  catch (e) { checks.push([name, 'threw ' + e.message]); }
}
function hiddenState(h0, h1, hand0, hand1, mana = [10, 10]) {
  const s = E.newMatch({ version: 'hidden', heroes: [h0, h1], seed: 1 });
  s.p[0].hand = hand0.slice(); s.p[1].hand = hand1.slice();
  s.p[0].mana = mana[0]; s.p[1].mana = mana[1];
  return s;
}
const eq = (a, b, what) => (a === b ? true : `${what}: expected ${b}, got ${a}`);
const all = (...rs) => rs.find(r => r !== true) ?? true;

// The unit checks below were written against health 34 (Heavy) and 26 (Quick). Health is a
// tuning number, so they run at those values whatever the engine currently uses.
function unitChecks() {
  const saved = [E.HEROES.Heavy.hp, E.HEROES.Quick.hp];
  E.HEROES.Heavy.hp = 34; E.HEROES.Quick.hp = 26;
  try { return unitChecksAtBaseHealth(); }
  finally { E.HEROES.Heavy.hp = saved[0]; E.HEROES.Quick.hp = saved[1]; }
}
function unitChecksAtBaseHealth() {
  check('Block stops only the first Light hit (Flurry deals 2 through Block)', () => {
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Flurry'], []), [['Flurry'], ['Block']]);
    return eq(s.p[1].hp, 26 - 2, 'defender hp');
  });
  check('Parry stops the first Light hit only and its attacker takes 3', () => {
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Flurry'], ['Parry']), [['Flurry'], ['Parry']]);
    return all(eq(s.p[1].hp, 24, 'defender hp'), eq(s.p[0].hp, 23, 'attacker hp'));
  });
  check('Brace stops every Light hit (Jab, Lunge and Flurry)', () => {
    const a = E.playRound(hiddenState('Quick', 'Quick', ['Lunge'], ['Brace']), [['Jab', 'Lunge'], ['Brace']]);
    const b = E.playRound(hiddenState('Quick', 'Quick', ['Flurry'], ['Brace']), [['Flurry'], ['Brace']]);
    return all(eq(a.p[1].hp, 26, 'hp after Jab+Lunge'), eq(b.p[1].hp, 26, 'hp after Flurry'));
  });
  check('Guards are used in the order played (Block then Parry vs one Slash: no reflect)', () => {
    const a = E.playRound(hiddenState('Quick', 'Quick', ['Slash'], ['Parry']), [['Slash'], ['Block', 'Parry']]);
    const b = E.playRound(hiddenState('Quick', 'Quick', ['Slash'], ['Parry']), [['Slash'], ['Parry', 'Block']]);
    return all(eq(a.p[0].hp, 26, 'attacker hp (Block first)'), eq(b.p[0].hp, 23, 'attacker hp (Parry first)'));
  });
  check('Heavy attacks ignore guards (Smash through Brace, Haymaker through Block)', () => {
    const a = E.playRound(hiddenState('Quick', 'Heavy', ['Smash'], ['Brace']), [['Smash'], ['Brace']]);
    const b = E.playRound(hiddenState('Quick', 'Heavy', ['Haymaker'], []), [['Haymaker'], ['Block']]);
    return all(eq(a.p[1].hp, 26, 'hp after Smash'), eq(b.p[1].hp, 22, 'hp after Haymaker'));
  });
  check('Flurry is two separate hits of 2 (two hit events, 4 damage, Sharpen adds to each)', () => {
    const ev = [];
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Flurry'], []), [['Flurry'], []], ev);
    const t = hiddenState('Quick', 'Quick', ['Flurry'], []); t.p[0].sharpen = 1;
    const u = E.playRound(t, [['Flurry'], []]);
    return all(eq(ev.filter(e => e.t === 'hit').length, 2, 'hits'), eq(s.p[1].hp, 22, 'hp'), eq(u.p[1].hp, 20, 'hp with Sharpen'));
  });
  check('Damage cancels unresolved Slow cards only: back to hand, mana stays spent, Normal still resolves', () => {
    // side 1 (Quick) plays Slash + Smash; side 0 Jabs in the Fast step
    const s0 = hiddenState('Quick', 'Quick', [], ['Slash', 'Smash']);
    const s = E.playRound(s0, [['Jab'], ['Slash', 'Smash']]);
    return all(eq(s.p[0].hp, 22, 'Slash still lands'), eq(s.p[1].hp, 24, 'Jab lands'),
      eq(s.p[1].hand.includes('Smash'), true, 'Smash back in hand'), eq(s.p[1].known.includes('Smash'), true, 'Smash publicly known'),
      eq(s.p[1].mana, Math.min(10, 10 - 6 + 4), 'mana spent stays spent (then +4 regen)'), eq(s.p[0].hp, 22, 'Smash did not hit'));
  });
  check('Cancelling caused by a step affects only later steps (both Smash in the Slow step: both land)', () => {
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Smash'], ['Smash']), [['Smash'], ['Smash']]);
    return all(eq(s.p[0].hp, 18, 'hp 0'), eq(s.p[1].hp, 18, 'hp 1'));
  });
  check("Heavy's Unstoppable: Jab and Flurry hits of 2 cancel nothing; 3 (sharpened Jab) and Lunge do", () => {
    const a = E.playRound(hiddenState('Quick', 'Heavy', [], ['Smash']), [['Jab'], ['Smash']]);
    const b = E.playRound(hiddenState('Quick', 'Heavy', ['Flurry'], ['Smash']), [['Flurry'], ['Smash']]);
    const c0 = hiddenState('Quick', 'Heavy', [], ['Smash']); c0.p[0].sharpen = 1;
    const c = E.playRound(c0, [['Jab'], ['Smash']]);
    const d = E.playRound(hiddenState('Quick', 'Heavy', ['Lunge'], ['Smash']), [['Lunge'], ['Smash']]);
    return all(eq(a.p[0].hp, 18, 'Smash after Jab'), eq(b.p[0].hp, 18, 'Smash after Flurry'),
      eq(c.p[0].hp, 26, 'Smash after sharpened Jab'), eq(d.p[0].hp, 26, 'Smash after Lunge'));
  });
  check("Quick's Light feet: first Fast action costs 1 less, once per turn, never below 0", () => {
    const q = hiddenState('Quick', 'Heavy', ['Lunge'], ['Lunge'], [2, 2]);
    const r1 = eq(E.validSet(q, 0, ['Lunge']), true, 'Quick Lunge at 2 mana');
    const r2 = eq(E.validSet(q, 1, ['Lunge']), false, 'Heavy Lunge at 2 mana');
    const r3 = eq(E.seqCost(q.p[0], ['Jab', 'Lunge'], false), 3, 'Jab+Lunge');
    const r4 = eq(E.seqCost(q.p[0], ['Slash', 'Jab'], false), 2, 'Slash+Jab');
    let o = E.newMatch({ version: 'open', heroes: ['Quick', 'Quick'], seed: 3 });
    const m = o.p[o.turn].mana;
    o = E.playAction(o, 'Jab'); o = E.playAction(o, 'Block');
    const r5 = eq(o.p[o.turn].mana, m - 1, 'Open: Jab free, Block full price');
    return all(r1, r2, r3, r4, r5);
  });
  check('Same-step actions resolve together in Hidden (both at 2 hp, both Jab: draw)', () => {
    const s0 = hiddenState('Quick', 'Heavy', [], []); s0.p[0].hp = 2; s0.p[1].hp = 2;
    const s = E.playRound(s0, [['Jab'], ['Jab']]);
    return eq(s.winner, 'draw', 'winner');
  });
  check('A kill in an earlier step stops later steps (Lunge kills before the Slow Smash)', () => {
    const s0 = hiddenState('Quick', 'Quick', ['Lunge'], ['Smash']); s0.p[1].hp = 4;
    const s = E.playRound(s0, [['Lunge'], ['Smash']]);
    return all(eq(s.winner, 0, 'winner'), eq(s.p[0].hp, 26, 'Smash never resolved'));
  });
  check("Parry's 3 damage cancels nothing (attacker's Smash still lands)", () => {
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Slash', 'Smash'], ['Parry']), [['Slash', 'Smash'], ['Parry']]);
    return all(eq(s.p[0].hp, 23, 'attacker took 3'), eq(s.p[1].hp, 18, 'Smash landed'));
  });
  check('Meditate respects the cap of 10', () => {
    const s = E.playRound(hiddenState('Quick', 'Quick', ['Meditate'], [], [9, 10]), [['Meditate'], []]);
    const o0 = E.newMatch({ version: 'open', heroes: ['Heavy', 'Heavy'], seed: 9 });
    o0.p[o0.turn].hand.push('Meditate'); o0.p[o0.turn].mana = 9;
    let o = E.playAction(o0, 'Meditate'); o = E.endTurn(o); o = E.endTurn(o);
    return all(eq(s.p[0].mana, 10, 'Hidden mana'), eq(o.p[o0.turn].mana, 10, 'Open mana'));
  });
  check('Bandage does not heal above starting health', () => {
    const s0 = hiddenState('Heavy', 'Quick', ['Bandage'], []); s0.p[0].hp = 32;
    const s = E.playRound(s0, [['Bandage'], []]);
    return eq(s.p[0].hp, 34, 'hp');
  });
  check('An empty deck draws nothing and nothing else happens', () => {
    const s0 = hiddenState('Quick', 'Quick', ['Slash'], ['Slash']); s0.p[0].deck = []; s0.p[1].deck = [];
    const ev = [];
    const s = E.playRound(s0, [[], []], ev);
    return all(eq(s.p[0].hand.length, 1, 'hand size'), eq(s.p[0].hp, 26, 'no fatigue'), eq(ev.filter(e => e.t === 'start' && e.drew === 0).length, 2, 'draw events with 0'));
  });
  check('Open: a winding card resolves at the start of its owner\'s next turn', () => {
    const o0 = E.newMatch({ version: 'open', heroes: ['Quick', 'Quick'], seed: 5 });
    const me = o0.turn; o0.p[me].hand.push('Smash');
    let o = E.playAction(o0, 'Smash');
    const r1 = eq(o.p[1 - me].hp, 26, 'no damage yet');
    o = E.endTurn(o);
    const r2 = eq(o.p[1 - me].hp, 26, 'no damage during his turn');
    o = E.endTurn(o);
    return all(r1, r2, eq(o.p[1 - me].hp, 18, 'Smash landed at my turn start'), eq(o.p[me].winding.length, 0, 'winding empty'));
  });
  check('Open: damage cancels a winding card, it returns to hand, the mana stays spent', () => {
    const o0 = E.newMatch({ version: 'open', heroes: ['Quick', 'Quick'], seed: 5 });
    const me = o0.turn; o0.p[me].hand.push('Smash');
    let o = E.playAction(o0, 'Smash');
    const manaAfter = o.p[me].mana;
    o = E.endTurn(o); o = E.playAction(o, 'Jab'); o = E.endTurn(o);
    return all(eq(o.p[1 - me].hp, 26, 'Smash never landed'), eq(o.p[me].hand.filter(n => n === 'Smash').length >= 1, true, 'Smash in hand'),
      eq(o.p[me].mana, Math.min(10, manaAfter + 4), 'mana spent stays spent'));
  });
  check('Open: Heavy\'s winding card survives a Jab, not a Slash', () => {
    const mk = () => { const o0 = E.newMatch({ version: 'open', heroes: ['Heavy', 'Heavy'], seed: 5 }); const me = o0.turn; o0.p[me].hand.push('Smash'); o0.p[1 - me].hand.push('Slash'); return [o0, me]; };
    let [a, me] = mk(); a = E.endTurn(E.playAction(a, 'Smash')); a = E.endTurn(E.playAction(a, 'Jab'));
    let [b] = mk(); b = E.endTurn(E.playAction(b, 'Smash')); b = E.endTurn(E.playAction(b, 'Slash'));
    return all(eq(a.p[1 - me].hp, 26, 'Smash landed after Jab'), eq(b.p[1 - me].hp, 34, 'Smash cancelled by Slash'));
  });
  check('Open: a guard lasts until the start of its owner\'s next turn', () => {
    const o0 = E.newMatch({ version: 'open', heroes: ['Quick', 'Quick'], seed: 5 });
    const me = o0.turn;
    let o = E.endTurn(E.playAction(o0, 'Block'));
    o = E.endTurn(E.playAction(o, 'Jab'));
    const r1 = eq(o.p[me].hp, 26, 'Jab stopped on his turn');
    const r2 = eq(o.p[me].guards.length, 0, 'guard gone at my turn start');
    return all(r1, r2);
  });
  check('The bot never sees hidden information (publicView blanks hand, decks, seed)', () => {
    const s = E.newMatch({ version: 'hidden', heroes: ['Heavy', 'Quick'], seed: 77 });
    const v = B.publicView(s, 1);
    return all(eq(v.p[0].hand.every(x => x === null), true, 'his hand'), eq(v.p[0].deck.every(x => x === null), true, 'his deck'), eq(v.seed, 0, 'seed'));
  });
  check('The engine is pure: transitions never change their input', () => {
    const s = E.newMatch({ version: 'hidden', heroes: ['Heavy', 'Quick'], seed: 4 });
    const before = JSON.stringify(s);
    E.playRound(s, [['Jab'], ['Block']]); B.botHidden(s, 1, B.makeRng(1));
    const o = E.newMatch({ version: 'open', heroes: ['Heavy', 'Quick'], seed: 4 });
    const ob = JSON.stringify(o);
    E.endTurn(E.playAction(o, 'Jab')); B.botOpenAction(o, B.makeRng(1));
    return all(eq(JSON.stringify(s) === before, true, 'hidden state unchanged'), eq(JSON.stringify(o) === ob, true, 'open state unchanged'));
  });
  check('Same seed, same match (deterministic)', () => {
    const a = runMatch({ version: 'hidden', heroes: ['Heavy', 'Quick'], kinds: ['bot', 'bot'], seed: 123 });
    const b = runMatch({ version: 'hidden', heroes: ['Heavy', 'Quick'], kinds: ['bot', 'bot'], seed: 123 });
    return eq(a.winner === b.winner && a.length === b.length, true, 'repeat');
  });
}

// ---------------------------------------------------------------- worker
if (!isMainThread) {
  parentPort.postMessage(workerData.jobs.map(runMatch));
} else {
  main();
}

async function runJobs(jobs) {
  const n = Math.max(1, os.cpus().length - 1);
  const chunks = Array.from({ length: n }, () => []);
  jobs.forEach((j, i) => chunks[i % n].push(j));
  const parts = await Promise.all(chunks.filter(c => c.length).map(c => new Promise((res, rej) => {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: c } });
    w.once('message', res); w.once('error', rej);
  })));
  return parts.flat();
}

const pct = (a, b) => (b ? (100 * a / b).toFixed(1) + '%' : 'n/a');

async function main() {
  const quick = process.argv.includes('--quick');
  const N_BOT = quick ? 100 : 500;        // per hero pairing, so 4x in total
  const N_VS = quick ? 100 : 500;
  const t0 = Date.now();
  unitChecks();
  console.log('UNIT CHECKS');
  for (const [name, err] of checks) console.log((err ? '  FAIL ' : '  ok   ') + name + (err ? ' -- ' + err : ''));
  const failed = checks.filter(c => c[1]).length;
  console.log(`  ${checks.length - failed}/${checks.length} passed\n`);

  const pairings = [['Heavy', 'Heavy'], ['Heavy', 'Quick'], ['Quick', 'Heavy'], ['Quick', 'Quick']];
  const jobs = [];
  let seed = 1000;
  for (const version of ['hidden', 'open']) {
    for (const heroes of pairings) for (let i = 0; i < N_BOT; i++) jobs.push({ group: 'bot', version, heroes, kinds: ['bot', 'bot'], seed: seed++ });
    for (const opp of ['random', 'greedy']) for (let i = 0; i < N_VS; i++) {
      const heroes = pairings[i % 4], botSeat = (i >> 2) % 2;
      jobs.push({ group: opp, version, heroes, kinds: botSeat === 0 ? ['bot', opp] : [opp, 'bot'], botSeat, seed: seed++ });
    }
  }
  const results = await runJobs(jobs);

  for (const version of ['hidden', 'open']) {
    const R = results.filter(r => r.version === version);
    const bvb = R.filter(r => r.group === 'bot');
    const bad = bvb.filter(r => r.error);
    const unit = version === 'hidden' ? 'rounds' : 'turns per player';
    console.log(`=== ${version === 'hidden' ? 'Version 1: Hidden' : 'Version 2: Open'} ===`);
    console.log(`bot vs bot: ${bvb.length} matches (${N_BOT} per hero pairing, both seats)`);
    console.log(`  crashes or illegal states or unfinished: ${bad.length}`);
    for (const r of bad.slice(0, 5)) console.log(`    seed ${r.seed} ${r.heroes.join('/')}: ${r.error.split('\n')[0]}`);
    const ok = bvb.filter(r => !r.error);
    const lens = ok.map(r => r.length).sort((a, b) => a - b);
    console.log(`  average match length: ${(lens.reduce((a, b) => a + b, 0) / lens.length).toFixed(2)} ${unit} (median ${lens[lens.length >> 1]}, min ${lens[0]}, max ${lens[lens.length - 1]})`);
    for (const h of pairings) {
      const g = ok.filter(r => r.heroes.join() === h.join());
      console.log(`  ${h[0]} (seat 0) vs ${h[1]} (seat 1): seat 0 wins ${pct(g.filter(r => r.winner === 0).length, g.length)}, seat 1 wins ${pct(g.filter(r => r.winner === 1).length, g.length)}, draws ${pct(g.filter(r => r.winner === 'draw').length, g.length)}`);
    }
    const hq = ok.filter(r => r.heroes[0] !== r.heroes[1]);
    const heavyWins = hq.filter(r => r.winner !== 'draw' && r.heroes[r.winner] === 'Heavy').length;
    const quickWins = hq.filter(r => r.winner !== 'draw' && r.heroes[r.winner] === 'Quick').length;
    const draws = hq.filter(r => r.winner === 'draw').length;
    console.log(`  Heavy vs Quick (${hq.length} matches): Heavy wins ${pct(heavyWins, hq.length)}, Quick wins ${pct(quickWins, hq.length)}, draws ${pct(draws, hq.length)}`);
    console.log(`  draws over all bot-vs-bot matches: ${pct(ok.filter(r => r.winner === 'draw').length, ok.length)}`);
    if (version === 'open') {
      console.log(`  first player wins ${pct(ok.filter(r => r.winner === r.first).length, ok.length)} (mirrors only: ${pct(ok.filter(r => r.heroes[0] === r.heroes[1] && r.winner === r.first).length, ok.filter(r => r.heroes[0] === r.heroes[1]).length)})`);
    }
    const sets = {};
    let total = 0;
    for (const r of ok) for (const [k, c] of Object.entries(r.sets)) { sets[k] = (sets[k] || 0) + c; total += c; }
    const top = Object.entries(sets).sort((a, b) => b[1] - a[1]).slice(0, 6);
    console.log(`  most played ${version === 'hidden' ? 'action sets per round' : 'turns'} by the bot: ` + top.map(([k, c]) => `${k} ${pct(c, total)}`).join(', '));
    const ms = R.filter(r => r.botMs[2]);
    const maxMs = Math.max(...ms.map(r => r.botMs[0]));
    const avgMs = ms.reduce((a, r) => a + r.botMs[1], 0) / ms.reduce((a, r) => a + r.botMs[2], 0);
    console.log(`  bot think time on this Mac (node): average ${avgMs.toFixed(1)} ms, max ${maxMs.toFixed(0)} ms per ${version === 'hidden' ? 'round' : 'action'}`);
    for (const opp of ['random', 'greedy']) {
      const g = R.filter(r => r.group === opp);
      const err = g.filter(r => r.error).length;
      const w = g.filter(r => !r.error && r.winner === r.botSeat).length;
      const d = g.filter(r => !r.error && r.winner === 'draw').length;
      console.log(`bot vs ${opp === 'random' ? 'uniform random' : 'greedy'}: ${g.length} matches, bot wins ${pct(w, g.length)}, draws ${pct(d, g.length)}, errors ${err}`);
    }
    console.log('');
  }
  console.log(`done in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  if (failed || results.some(r => r.error && r.group === 'bot')) process.exitCode = 1;
}
