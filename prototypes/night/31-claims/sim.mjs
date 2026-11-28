// node sim.mjs [games=400] [budget=3000]: the machine gate for Claims. Expert against Random,
// Greedy and Racer (seats alternated on the same deals), Expert against itself for the first
// player's rate, every Expert decision compared with Greedy's; writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync } from 'node:fs';
import os from 'node:os';
import { newMatch, act, legalActions } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, sameDecision } from './src/bot.js';

const N = +(process.argv[2] || 400), BUDGET = +(process.argv[3] || 3000);

function play(names, seed, budget) {
  const ex = expertBot({ budget });
  const make = (n) => n === 'random' ? randomBot : n === 'greedy' ? (s) => greedyBot(s) : n === 'racer' ? (s) => racerBot(s) : ex;
  const bots = names.map(make), rng = makeRng(seed * 7 + 3);
  let s = newMatch({ seed }), dec = 0, same = 0;
  while (s.winner === null) {
    const who = s.toMove, a = bots[who](s, rng);
    if (names[who] === 'expert' && legalActions(s).length > 1) { dec++; if (sameDecision(s, a, greedyBot(s))) same++; }
    s = act(s, a);
  }
  return { winner: s.winner, first: s.first, cap: s.cap, turns: s.turnNo, dec, same };
}

if (!isMainThread) {
  const { jobs, budget } = workerData;
  for (const j of jobs) parentPort.postMessage({ j, r: play(j.names, j.seed, budget) });
  parentPort.postMessage({ done: true });
} else {
  const pairs = [['expert', 'random'], ['expert', 'greedy'], ['expert', 'racer'], ['expert', 'expert']];
  const jobs = [];
  for (const [a, b] of pairs) for (let g = 0; g < N; g++) {
    const aSide = g % 2, names = aSide === 0 ? [a, b] : [b, a];
    jobs.push({ pair: a + '-' + b, aSide, names, seed: 10007 + (g >> 1) });
  }
  const W = Math.max(1, os.cpus().length - 1), out = [];
  const t0 = Date.now();
  await Promise.all([...Array(W).keys()].map(w => new Promise((res, rej) => {
    const wk = new Worker(new URL(import.meta.url), { workerData: { jobs: jobs.filter((_, k) => k % W === w), budget: BUDGET } });
    wk.on('message', m => { if (m.done) res(); else out.push(m); });
    wk.on('error', rej);
  })));
  const rep = { game: '31 Claims', games: N, budget: BUDGET, seconds: Math.round((Date.now() - t0) / 1000), matchups: {}, gate: {} };
  let capped = 0, all = 0, dec = 0, same = 0;
  for (const [a, b] of pairs) {
    const rs = out.filter(m => m.j.pair === a + '-' + b);
    let wa = 0, dr = 0, turns = 0, fw = 0, fd = 0;
    for (const { j, r } of rs) {
      all++; if (r.cap) capped++; turns += r.turns; dec += r.dec; same += r.same;
      if (r.winner === 'draw') { dr++; fd++; } else { if (r.winner === j.aSide) wa++; if (r.winner === r.first) fw++; }
    }
    rep.matchups[a + '-' + b] = { games: rs.length, expertWins: wa, draws: dr, expertRate: +((wa + dr / 2) / rs.length).toFixed(3), firstPlayerRate: +((fw + fd / 2) / rs.length).toFixed(3), avgTurns: +(turns / rs.length).toFixed(1) };
  }
  const m = rep.matchups;
  rep.gate = {
    expertVsRandom: m['expert-random'].expertRate, expertVsGreedy: m['expert-greedy'].expertRate, expertVsRacer: m['expert-racer'].expertRate,
    firstPlayerRateExpertMirror: m['expert-expert'].firstPlayerRate,
    turnCapRate: +(capped / all).toFixed(4),
    expertEqualsGreedy: +(same / dec).toFixed(3), expertDecisions: dec,
  };
  const g = rep.gate;
  rep.gate.fails = [
    ...['expertVsRandom', 'expertVsGreedy', 'expertVsRacer'].filter(k => g[k] < 0.7).map(k => k + ' under 70%'),
    ...(g.turnCapRate > 0.02 ? ['turn cap over 2%'] : []),
    ...(g.expertEqualsGreedy > 0.9 ? ['Expert equals Greedy over 90%'] : []),
    ...(g.firstPlayerRateExpertMirror < 0.3 || g.firstPlayerRateExpertMirror > 0.7 ? ['first player outside 30-70%'] : []),
  ];
  try { rep.sanity = (await import('./sanity.mjs')).results; } catch (e) { rep.sanity = 'sanity.mjs failed: ' + e.message; }
  writeFileSync(new URL('report.json', import.meta.url), JSON.stringify(rep, null, 2));
  console.log(JSON.stringify(rep, null, 2));
}
