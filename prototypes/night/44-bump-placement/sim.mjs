// node sim.mjs [games] [workers] [mirrorGames]: the night run's machine gate for 44 Bump placement. Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, how often Expert's choice equals
// Greedy's, and whether mana binds. Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync } from 'node:fs';
import { newMatch, _act, CARDS, BASE_MANA, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

// does mana bind? At a player's first placement decision of each round: do the cards in hand cost
// more than the mana there is (the player must choose); when it passes: mana left while a card it
// could not afford stayed in hand. The mana is 4 a round (7 after Fund) and does not carry over.
function probeStart(s, cs) {
  const P = s.p[s.toAct];
  const cost = P.hand.reduce((a, id) => a + CARDS[id].cost, 0);
  cs.turns++; if (cost > P.mana) cs.constrained++;
  if (P.mana > BASE_MANA) cs.atCap++;
  cs.manaAvail += P.mana;
}
function probeEnd(s, cs) {
  const P = s.p[s.toAct];
  cs.unspent += P.mana;
  if (P.mana > 0 && P.hand.some(id => CARDS[id].cost > P.mana)) cs.leftWhileBlocked++;
}

function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0, bumps = 0;
  const seen = new Set();
  const cs = { turns: 0, constrained: 0, atCap: 0, unspent: 0, manaAvail: 0, leftWhileBlocked: 0 };
  while (s.winner === null && steps < 6000) {
    const who = names[s.toAct], bot = BOTS[who];
    if (s.phase === 'place' && !seen.has(s.round + ':' + s.toAct)) { seen.add(s.round + ':' + s.toAct); if (who === 'expert') probeStart(s, cs); }
    const a = bot(s, rng);
    if (a.t === 'place' && s.spaces[a.space]) bumps++;
    if (who === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      if (actionKey(greedyBot(s, rng)) === actionKey(a)) agree++;
    }
    if (a.t === 'pass' && who === 'expert') probeEnd(s, cs);
    _act(s, a); steps++;
  }
  return { winner: s.winner, aSide, first: s.first, turns: s.round, capped: !!s.capped || s.winner === null, byLimit: s.byLimit, bumps, agree, decisions, cs, points: s.p.map(p => p.points) };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 4), NM = +(process.argv[4] || 200);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'racer', N], ['expert', 'expert', NM], ['greedy', 'greedy', 1000]];
  const jobs = [];
  pairs.forEach(([a, b, n], k) => { for (let g = 0; g < n; g++) jobs.push({ pair: a + '-' + b, a, b, g, seed0: 1000 * (k + 1) }); });
  const buckets = Array.from({ length: NW }, () => []);
  jobs.forEach((j, i) => buckets[i % NW].push(j));
  const res = {}; let left = NW, doneN = 0; const t0 = Date.now();
  for (const b of buckets) {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: b } });
    w.on('message', (m) => {
      if (m.done) { if (--left === 0) finish(); return; }
      (res[m.pair] = res[m.pair] || []).push(m.r);
      if (++doneN % 50 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const out = { concept: '44-bump-placement', expert: EXPERT, pairings: {}, gate: {}, costBinding: {} };
    let capped = 0, total = 0, agree = 0, dec = 0, mirror = { games: 0, byLimit: 0, bumps: 0, rounds: 0, winPts: 0, losePts: 0 };
    const cs = { turns: 0, constrained: 0, atCap: 0, unspent: 0, manaAvail: 0, leftWhileBlocked: 0 };
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, fw = 0, fd = 0, turns = 0, cp = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === r.first) fw++; else if (r.winner === 'draw') fd++;
        turns += r.turns; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions;
        if (pair === 'expert-expert') { for (const k in cs) cs[k] += r.cs[k]; mirror.games++; if (r.byLimit) mirror.byLimit++; mirror.bumps += r.bumps; mirror.rounds += r.turns; mirror.winPts += Math.max(...r.points); mirror.losePts += Math.min(...r.points); }
      }
      if (pair.startsWith('expert-')) { capped += cp; total += rs.length; }
      out.pairings[pair] = { games: rs.length, endedByRound12: rs.filter(r => r.byLimit).length, aWinRate: +((aw + d / 2) / rs.length).toFixed(4), draws: d, firstPlayerWinRate: +((fw + fd / 2) / rs.length).toFixed(4), avgTurns: +(turns / rs.length).toFixed(1), capped: cp };
    }
    const P = out.pairings;
    const minVs = Math.min(...['random', 'greedy', 'racer'].map(b => P['expert-' + b].aWinRate));
    out.gate = {
      expertMinWinRateVsTrivial: minVs,
      expertVsTrivialPass: minVs >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02, cappedCountedOver: 'every game Expert plays (no safety cap exists: round 12 is the designed end and counts as an ending)',
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      firstPlayerWinRateExpertMirror: P['expert-expert'].firstPlayerWinRate,
      firstPlayerPass: P['expert-expert'].firstPlayerWinRate >= 0.3 && P['expert-expert'].firstPlayerWinRate <= 0.7,
      seconds: Math.round((Date.now() - t0) / 1000),
    };
    out.costBinding = {
      measuredIn: 'Expert mirror, both seats, every round',
      rounds: cs.turns,
      handCostsMoreThanManaRate: +(cs.constrained / cs.turns).toFixed(3),
      fundedRoundRate: +(cs.atCap / cs.turns).toFixed(3),
      unspentManaShare: +(cs.unspent / cs.manaAvail).toFixed(3),
      passedWithManaLeftAndADearerCardHeldRate: +(cs.leftWhileBlocked / cs.turns).toFixed(3),
    };
    out.mirror = { games: mirror.games, endedByRound12: mirror.byLimit, avgRounds: +(mirror.rounds / mirror.games).toFixed(2), bumpsPerRound: +(mirror.bumps / mirror.rounds).toFixed(2), avgWinnerPoints: +(mirror.winPts / mirror.games).toFixed(1), avgLoserPoints: +(mirror.losePts / mirror.games).toFixed(1) };
    out.sanity = runSanity(expertBot(EXPERT)).map(({ position, bot, pass, passed, of }) => ({ position, bot, pass, passed, of }));
    out.gate.setPositionsPass = out.sanity.filter(r => r.bot === 'expert').every(r => r.pass);
    out.gate.allPass = out.gate.expertVsTrivialPass && out.gate.cappedPass && out.gate.agreementPass && out.gate.firstPlayerPass && out.gate.setPositionsPass;
    try { const prev = JSON.parse(readFileSync(new URL('./report.json', import.meta.url), 'utf8')); if (prev.report) out.report = prev.report; } catch (e) {}
    writeFileSync(new URL('./report.json', import.meta.url), JSON.stringify(out, null, 2) + '\n');
    console.log(JSON.stringify(out, null, 2));
  }
}
