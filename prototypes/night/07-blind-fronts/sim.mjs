// node sim.mjs [games=400] [workers=4]: the machine gate. Each finished game is appended to
// sim-progress.jsonl, and a rerun skips the games already there, so a killed run resumes. Expert against every trivial bot, seats
// alternated on the same deals; Expert against itself and Greedy against itself for the
// first-player rate; turn caps; how often Expert's choice equals Greedy's. Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';
import { newMatch, act, isLegal } from './src/engine.js';
import { makeRng, expertBot, cands, EXPERT, TRIVIAL, meaning } from './src/bot.js';

const length = (s) => s.turnNo ?? s.round ?? s.hand;
function playGame(bots, seed, rngSeed, track) {
  const rng = makeRng(rngSeed);
  let s = newMatch({ seed });
  let dec = 0, same = 0, ms = 0, maxMs = 0, steps = 0;
  while (s.winner === null) {
    const who = s.toMove;
    const t0 = performance.now();
    const a = bots[who](s, rng);
    const dt = performance.now() - t0;
    if (track === who) {
      ms += dt; if (dt > maxMs) maxMs = dt;
      if (cands(s).length > 1) { dec++; if (meaning(s, TRIVIAL.greedy(s, rng)) === meaning(s, a)) same++; }
    }
    if (!isLegal(s, a)) throw new Error('bot made an illegal move');
    s = act(s, a);
    if (++steps > 20000) throw new Error('runaway game');
  }
  return { winner: s.winner, first: s.first, turns: length(s), capped: !!s.capped, limit: !!s.limit, dec, same, ms, maxMs };
}

const mk = (name) => name === 'expert' ? expertBot(EXPERT) : TRIVIAL[name];

if (!isMainThread) {
  for (const j of workerData.jobs) parentPort.postMessage({ ...j, r: playGame([mk(j.b0), mk(j.b1)], j.seed, j.rngSeed, j.track) });
  parentPort.postMessage('done');
} else {
  const N = +(process.argv[2] || 400), W = +(process.argv[3] || 4);
  const jobs = [];
  const pair = (name, a, b, n, seed0, track) => {
    for (let g = 0; g < n; g++) {
      const aSeat = g % 2; // seats alternate; each deal is played from both seats
      jobs.push({ name, aSeat, b0: aSeat === 0 ? a : b, b1: aSeat === 0 ? b : a, seed: seed0 + (g >> 1), rngSeed: seed0 * 31 + g, track: track ? aSeat : -1 });
    }
  };
  const triv = Object.keys(TRIVIAL);
  triv.forEach((t, i) => pair('expert-' + t, 'expert', t, N, 1000 * (i + 1), true));
  pair('expert-expert', 'expert', 'expert', N, 9000, false);
  pair('greedy-greedy', 'greedy', 'greedy', 2000, 10000, false);
  pair('greedy-random', 'greedy', 'random', N, 11000, false);
  const PROG = new URL('./sim-progress.jsonl', import.meta.url), id = (j) => j.name + ':' + j.seed + ':' + j.aSeat;
  const results = existsSync(PROG) ? readFileSync(PROG, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)) : [];
  const done = new Set(results.map(id));
  const todo = jobs.filter(j => !done.has(id(j)));
  console.error(`${results.length} games already played, ${todo.length} to go`);
  const chunks = Array.from({ length: W }, () => []);
  todo.forEach((j, i) => chunks[i % W].push(j));
  const t0 = Date.now();
  await Promise.all(chunks.map(c => new Promise((res, rej) => {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: c } });
    w.on('message', (m) => { if (m === 'done') return res(); results.push(m); appendFileSync(PROG, JSON.stringify(m) + '\n'); });
    w.on('error', rej);
  })));
  const by = {};
  for (const j of results) (by[j.name] ||= []).push(j);
  const report = { games: N, expert: EXPERT, seconds: Math.round((Date.now() - t0) / 1000), pairings: {} };
  for (const [name, rs] of Object.entries(by)) {
    let aw = 0, dr = 0, fw = 0, capped = 0, limit = 0, turns = 0, dec = 0, same = 0, ms = 0, maxMs = 0;
    for (const j of rs) {
      const r = j.r;
      if (r.winner === 'draw') dr++; else if (r.winner === j.aSeat) aw++;
      if (r.winner === r.first) fw++;
      if (r.capped) capped++; if (r.limit) limit++;
      turns += r.turns; dec += r.dec; same += r.same; ms += r.ms; maxMs = Math.max(maxMs, r.maxMs);
    }
    const n = rs.length, decided = n - dr;
    report.pairings[name] = {
      games: n, aWinRate: +((aw + dr / 2) / n).toFixed(3), draws: dr,
      firstPlayerWinRate: +(fw / Math.max(1, decided)).toFixed(3), turnCapRate: +(capped / n).toFixed(3), ...(limit ? { roundLimitRate: +(limit / n).toFixed(3) } : {}), avgLength: +(turns / n).toFixed(1),
      ...(dec ? { expertDecisions: dec, sameAsGreedy: +(same / dec).toFixed(3), expertMsPerMove: +(ms / dec).toFixed(1), expertMaxMs: Math.round(maxMs) } : {}),
    };
  }
  const P = report.pairings, ex = triv.map(t => 'expert-' + t);
  const allDec = ex.reduce((a, k) => a + P[k].expertDecisions, 0), allSame = ex.reduce((a, k) => a + P[k].sameAsGreedy * P[k].expertDecisions, 0);
  const capRate = Math.max(...Object.values(P).map(p => p.turnCapRate));
  report.gate = { ...Object.fromEntries(ex.map(k => [k, P[k].aWinRate])), firstPlayerWinRate: P['expert-expert'].firstPlayerWinRate, turnCapRate: capRate, sameAsGreedy: +(allSame / allDec).toFixed(3) };
  const g = report.gate;
  report.gate.fails = [
    ...ex.filter(k => P[k].aWinRate < 0.7).map(k => `${k} ${P[k].aWinRate} < 0.70`),
    ...(g.firstPlayerWinRate < 0.3 || g.firstPlayerWinRate > 0.7 ? [`first player ${g.firstPlayerWinRate} outside 0.30-0.70`] : []),
    ...(capRate > 0.02 ? [`turn cap ${capRate} > 0.02`] : []),
    ...(g.sameAsGreedy > 0.9 ? [`same as Greedy ${g.sameAsGreedy} > 0.90`] : []),
  ];
  writeFileSync(new URL('./report.json', import.meta.url), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
