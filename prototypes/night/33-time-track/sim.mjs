// node sim.mjs [games] [playouts]: the machine gate. Expert against each trivial bot and itself,
// seats alternated on shared deals, spread over worker threads; writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { cpus } from 'node:os';
import { writeFileSync } from 'node:fs';
import { newMatch, act, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, sensible } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const N = +(process.argv[2] || 400), ITERS = +(process.argv[3] || 3000);
const MATCHUPS = [['expert', 'random'], ['expert', 'greedy'], ['expert', 'racer'], ['expert', 'expert']];
const TRIVIAL = ['random', 'greedy', 'racer'];

function playGame(mi, g, iters) {
  const [an, bn] = MATCHUPS[mi];
  const ex = expertBot({ iters });
  const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: ex };
  const rng = makeRng(7919 * (mi + 1) + 104729 * g + 13);
  const aSide = g % 2;
  let s = newMatch({ seed: 5000 + (g >> 1) });
  const first = s.first;
  let dec = 0, same = 0;
  while (s.winner === null) {
    const name = s.turn === aSide ? an : bn;
    const a = BOTS[name](s, rng);
    if (name === 'expert' && sensible(s).length > 1) { dec++; if (actionKey(s, greedyBot(s, rng)) === actionKey(s, a)) same++; }
    s = act(s, a);
  }
  return { mi, g, winner: s.winner, aSide, first, turns: s.n, capped: !!s.capped, clock: !!s.timeout, dec, same };
}

if (!isMainThread) {
  const out = workerData.jobs.map(([mi, g]) => { const x = playGame(mi, g, workerData.iters); parentPort.postMessage({ tick: 1 }); return x; });
  parentPort.postMessage({ out });
} else {
  const t0 = Date.now();
  const jobs = [];
  for (let mi = 0; mi < MATCHUPS.length; mi++) for (let g = 0; g < N; g++) jobs.push([mi, g]);
  const W = Math.max(1, cpus().length - 2), slices = Array.from({ length: W }, () => []);
  jobs.forEach((j, k) => slices[k % W].push(j));
  let ticks = 0;
  const parts = await Promise.all(slices.map(js => new Promise((res, rej) => {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: js, iters: ITERS } });
    w.on('message', m => { if (m.tick) { if (++ticks % 50 === 0) console.log(`${ticks}/${jobs.length} games, ${Math.round((Date.now() - t0) / 1000)}s`); } else res(m.out); }); w.on('error', rej);
  })));
  const res = parts.flat();
  const matchups = MATCHUPS.map(([an, bn], mi) => {
    const R = res.filter(x => x.mi === mi);
    let aw = 0, bw = 0, dr = 0, fw = 0, turns = 0, capped = 0, clock = 0;
    for (const x of R) {
      if (x.winner === 'draw') { dr++; fw += 0.5; }
      else { if (x.winner === x.aSide) aw++; else bw++; if (x.winner === x.first) fw++; }
      turns += x.turns; if (x.capped) capped++; if (x.clock) clock++;
    }
    return { a: an, b: bn, games: R.length, aWins: aw, bWins: bw, draws: dr, aRate: +((aw + dr / 2) / R.length).toFixed(4), firstPlayerRate: +(fw / R.length).toFixed(4), avgActions: +(turns / R.length).toFixed(2), capped, endedOnClock: clock };
  });
  const dec = res.reduce((n, x) => n + x.dec, 0), same = res.reduce((n, x) => n + x.same, 0);
  const allGames = res.length, cappedAll = res.filter(x => x.capped).length;
  const eve = matchups.find(m => m.a === 'expert' && m.b === 'expert');
  const sanity = runSanity({ iters: 6000, quiet: true });
  const gate = {
    expertVsTrivial: Object.fromEntries(TRIVIAL.map(t => [t, matchups.find(m => m.b === t).aRate])),
    expertBeatsTrivial70: TRIVIAL.every(t => matchups.find(m => m.b === t).aRate >= 0.7),
    setPositionsPass: sanity.expertPass,
    turnCapShare: +(cappedAll / allGames).toFixed(4), turnCapOK: cappedAll / allGames <= 0.02,
    greedyAgreement: +(same / dec).toFixed(4), greedyAgreementOK: same / dec <= 0.9,
    firstPlayerRateExpertMirror: eve.firstPlayerRate, firstPlayerOK: eve.firstPlayerRate >= 0.3 && eve.firstPlayerRate <= 0.7,
  };
  gate.alive = gate.expertBeatsTrivial70 && gate.setPositionsPass && gate.turnCapOK && gate.greedyAgreementOK && gate.firstPlayerOK;
  const report = { firstPlayer: 'the player whose marker starts on top', turnCap: 'none needed: every action moves a marker at least 1 toward 60', concept: '33 Time track', gamesPerMatchup: N, expertPlayouts: ITERS, pageExpertPlayouts: 5000, agreementCountedOn: 'Expert decisions with 2+ sensible options, all Expert games', decisions: dec, matchups, sanity: sanity.results, gate, seconds: Math.round((Date.now() - t0) / 1000) };
  writeFileSync(new URL('report.json', import.meta.url), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ matchups, gate }, null, 1));
}
