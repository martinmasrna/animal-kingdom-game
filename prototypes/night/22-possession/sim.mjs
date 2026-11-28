// node sim.mjs [games] [workers]: the machine gate. Expert against every trivial bot, seats
// alternated on the same deals; Expert against itself for the rate at which the side with kickoff
// possession wins (this game has no first player); how often Expert's choice is Greedy's.
// Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync } from 'node:fs';
import { cpus } from 'node:os';
import { newMatch, _play, options } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, matrixExpert, EXPERT } from './src/bot.js';

const BOTS = { random: () => randomBot, greedy: () => greedyBot, racer: () => racerBot, expert: () => matrixExpert(EXPERT) };

function playGame(A, B, seed, aSide, track) {
  const rng = makeRng(seed * 7919 + aSide);
  const s = newMatch({ seed });
  const st = { cmp: 0, same: 0 };
  while (s.winner === null) {
    const ch = [0, 1].map(side => (side === aSide ? A : B)(s, side, rng));
    if (track && options(s, aSide).length > 1) { st.cmp++; if (greedyBot(s, aSide) === ch[aSide]) st.same++; }
    _play(s, ch);
  }
  return { winner: s.winner, aSide, first: s.first, goals: s.goals[0] + s.goals[1], ...st };
}
function runSlice({ a, b, games, seed0, track }) {
  const A = BOTS[a](), B = BOTS[b]();
  return games.map(g => playGame(A, B, seed0 + (g >> 1), g % 2, track));
}

if (!isMainThread) { parentPort.postMessage(runSlice(workerData)); }
else {
  const N = +(process.argv[2] || 400), W = +(process.argv[3] || Math.min(4, cpus().length));
  const pairings = [['expert', 'random'], ['expert', 'greedy'], ['expert', 'racer'], ['expert', 'expert'], ['greedy', 'greedy'], ['greedy', 'random']];
  const run = (a, b, track) => Promise.all([...Array(W)].map((_, w) => new Promise((res, rej) => {
    const games = []; for (let g = w; g < N; g += W) games.push(g);
    const wk = new Worker(new URL(import.meta.url), { workerData: { a, b, games, seed0: 10000, track } });
    wk.on('message', res); wk.on('error', rej);
  }))).then(parts => parts.flat());
  const t0 = Date.now(), report = { games: N, expert: EXPERT, pairings: {} };
  for (const [a, b] of pairings) {
    const rs = await run(a, b, a === 'expert' && b === 'greedy');
    const n = rs.length, w = rs.filter(r => r.winner === r.aSide).length, d = rs.filter(r => r.winner === 'draw').length;
    const fw = rs.filter(r => r.winner === r.first).length;
    const row = { n, aScore: +((w + d / 2) / n).toFixed(3), aWins: w, draws: d, aLosses: n - w - d,
      kickoffScore: +((fw + d / 2) / n).toFixed(3), capped: 0, avgGoals: +(rs.reduce((x, r) => x + r.goals, 0) / n).toFixed(2) };
    if (a === 'expert' && b === 'greedy') { const c = rs.reduce((x, r) => x + r.cmp, 0), sm = rs.reduce((x, r) => x + r.same, 0); row.decisionsCompared = c; row.agreement = +(sm / c).toFixed(3); }
    report.pairings[`${a}-${b}`] = row;
    console.log(`${a} vs ${b}:`, JSON.stringify(row), `${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  const P = report.pairings;
  report.gate = {
    expertVsRandom: P['expert-random'].aScore, expertVsGreedy: P['expert-greedy'].aScore, expertVsRacer: P['expert-racer'].aScore,
    capRate: 0, agreementWithGreedy: P['expert-greedy'].agreement, kickoffPossessionScoreExpertMirror: P['expert-expert'].kickoffScore,
  };
  const g = report.gate, fails = [];
  for (const k of ['expertVsRandom', 'expertVsGreedy', 'expertVsRacer']) if (g[k] < 0.7) fails.push(`${k} ${g[k]} < 0.70`);
  if (g.agreementWithGreedy > 0.9) fails.push(`Expert's choice equals Greedy's in ${g.agreementWithGreedy}`);
  if (g.kickoffPossessionScoreExpertMirror < 0.3 || g.kickoffPossessionScoreExpertMirror > 0.7) fails.push(`kickoff possession ${g.kickoffPossessionScoreExpertMirror} outside 0.30-0.70`);
  report.fails = fails; report.alive = fails.length === 0; report.seconds = Math.round((Date.now() - t0) / 1000);
  writeFileSync(new URL('report.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
  console.log(fails.length ? 'DEAD: ' + fails.join('; ') : 'ALIVE');
}
