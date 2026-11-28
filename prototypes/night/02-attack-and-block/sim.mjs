// node sim.mjs [games] [workers]: the night run's machine gate for 02 Attack and block.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, and how often Expert's choice
// equals Greedy's. Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync } from 'node:fs';
import { newMatch, _act, clone, legalActions, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0;
  while (s.winner === null && steps < 5000) {
    const who = names[s.toAct], bot = BOTS[who];
    const a = bot(s, rng);
    if (who === 'expert' && aName === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      if (actionKey(greedyBot(s, rng)) === actionKey(a)) agree++;
    }
    _act(s, a); steps++;
  }
  return { winner: s.winner, aSide, first: s.first, turns: s.turnNo, capped: !!s.capped || s.winner === null, agree, decisions };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 4);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'racer', N], ['expert', 'expert', Math.min(N, 200)], ['greedy', 'greedy', 1000]];
  const jobs = [];
  pairs.forEach(([a, b, n], k) => { for (let g = 0; g < n; g++) jobs.push({ pair: a + '-' + b, a, b, g, seed0: 1000 * (k + 1) }); });
  // interleave so every worker gets a fair share of the slow games
  const buckets = Array.from({ length: NW }, () => []);
  jobs.forEach((j, i) => buckets[i % NW].push(j));
  const res = {}; let left = NW, doneN = 0; const t0 = Date.now();
  for (const b of buckets) {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: b } });
    w.on('message', (m) => {
      if (m.done) { if (--left === 0) finish(); return; }
      (res[m.pair] = res[m.pair] || []).push(m.r);
      if (++doneN % 100 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const out = { concept: '02-attack-and-block', expert: EXPERT, pairings: {}, gate: {} };
    let capped = 0, total = 0, agree = 0, dec = 0;
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, fw = 0, fd = 0, turns = 0, cp = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === r.first) fw++; else if (r.winner === 'draw') fd++;
        turns += r.turns; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions;
      }
      if (pair.startsWith('expert-')) { capped += cp; total += rs.length; }
      out.pairings[pair] = { games: rs.length, aWinRate: +((aw + d / 2) / rs.length).toFixed(4), draws: d, firstPlayerWinRate: +((fw + fd / 2) / rs.length).toFixed(4), avgTurns: +(turns / rs.length).toFixed(1), capped: cp };
    }
    const P = out.pairings;
    const minVs = Math.min(...['random', 'greedy', 'racer'].map(b => P['expert-' + b].aWinRate));
    out.gate = {
      expertMinWinRateVsTrivial: minVs,
      expertVsTrivialPass: minVs >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02, cappedCountedOver: 'the games Expert plays',
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      firstPlayerWinRateExpertMirror: P['expert-expert'].firstPlayerWinRate,
      firstPlayerPass: P['expert-expert'].firstPlayerWinRate >= 0.3 && P['expert-expert'].firstPlayerWinRate <= 0.7,
      seconds: Math.round((Date.now() - t0) / 1000),
    };
    out.sanity = runSanity(expertBot(EXPERT)).map(({ position, bot, pass, passed, of }) => ({ position, bot, pass, passed, of }));
    out.gate.setPositionsPass = out.sanity.filter(r => r.bot === 'expert').every(r => r.pass);
    out.gate.allPass = out.gate.expertVsTrivialPass && out.gate.cappedPass && out.gate.agreementPass && out.gate.firstPlayerPass && out.gate.setPositionsPass;
    // keep the verdict and the loop notes written after the last run
    try { const prev = JSON.parse(readFileSync(new URL('./report.json', import.meta.url), 'utf8')); if (prev.report) out.report = prev.report; } catch (e) {}
    writeFileSync(new URL('./report.json', import.meta.url), JSON.stringify(out, null, 2) + '\n');
    console.log(JSON.stringify(out, null, 2));
  }
}
