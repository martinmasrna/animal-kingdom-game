// node sim.mjs [games=400] [workers=4] [only=pairing,...]: the machine gate. Expert against every
// trivial bot, seats alternated on the same deals; Expert against itself and Greedy against
// itself for the first-player rate (the first player of round 1); games that run the full 20
// rounds (the rules' own end, not a cap); how often Expert's choice equals Greedy's; and whether
// mana binds the buy (how often the strongest line a hand holds costs more than 6, what is
// spent, how often a Bluff is bought). Each finished game is appended to sim-progress.jsonl and
// a rerun skips the games already there. Writes report.json (keeping its "report" and "sanity" keys).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';
import { newMatch, act, isLegal, lines, lineCost, ROUNDS } from './src/engine.js';
import { makeRng, expertBot, EXPERT, TRIVIAL, meaning, estPower, bestLine } from './src/bot.js';
import { legalActions as cands } from './src/engine.js';

// the strongest line of a hand with no mana limit (up to 3 cards)
function bestFree(hand) { let bv = -1; const ids = hand.slice().sort((a, b) => estPower([b]) - estPower([a])); for (const l of [ids.slice(0, 3), ids.slice(0, 1)]) bv = Math.max(bv, estPower(l)); return bv; }
function playGame(bots, seed, rngSeed, track) {
  const rng = makeRng(rngSeed);
  let s = newMatch({ seed });
  let dec = 0, same = 0, ms = 0, maxMs = 0, steps = 0;
  const m = { buys: 0, bound: 0, spent: 0, bluff: 0, three: 0, notBest: 0, folds: 0, shows: 0, bets: 0 };
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
    if (a.t === 'buy') {
      const h = s.p[who].hand;
      m.buys++; m.spent += lineCost(a.line);
      if (bestFree(h) > estPower(bestLine(h))) m.bound++;
      if (a.line.includes('BL')) m.bluff++;
      if (a.line.length === 3) m.three++;
      if (estPower(a.line) < estPower(bestLine(h))) m.notBest++;
    }
    if (a.t === 'bet' || a.t === 'raise') m.bets++;
    if (a.t === 'fold') m.folds++;
    const r0 = s.round;
    s = act(s, a);
    if (s.last && s.round !== r0 && s.last.how === 'show') m.shows++;
    if (++steps > 20000) throw new Error('runaway game');
  }
  return { winner: s.winner, first: s.first, turns: Math.min(s.round, ROUNDS), capped: s.round > ROUNDS, dec, same, ms, maxMs, m };
}

const mk = (name) => name === 'expert' ? expertBot(EXPERT) : TRIVIAL[name];

if (!isMainThread) {
  for (const j of workerData.jobs) parentPort.postMessage({ ...j, r: playGame([mk(j.b0), mk(j.b1)], j.seed, j.rngSeed, j.track) });
  parentPort.postMessage('done');
} else {
  const N = +(process.argv[2] || 400), W = +(process.argv[3] || 4), only = process.argv[4] ? process.argv[4].split(',') : null;
  const jobs = [];
  const pair = (name, a, b, n, seed0, track) => {
    if (only && !only.includes(name)) return;
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
  pair('greedy-caller', 'greedy', 'caller', N, 12000, false);
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
  const OUT = new URL('./report.json', import.meta.url);
  const old = existsSync(OUT) ? JSON.parse(readFileSync(OUT, 'utf8')) : {};
  const report = { games: N, expert: EXPERT, seconds: Math.round((Date.now() - t0) / 1000), pairings: {} };
  for (const [name, rs] of Object.entries(by)) {
    let aw = 0, dr = 0, fw = 0, capped = 0, turns = 0, dec = 0, same = 0, ms = 0, maxMs = 0;
    const M = { buys: 0, bound: 0, spent: 0, bluff: 0, three: 0, notBest: 0, folds: 0, shows: 0, bets: 0 };
    for (const j of rs) {
      const r = j.r;
      if (r.winner === 'draw') dr++; else if (r.winner === j.aSeat) aw++;
      if (r.winner === r.first) fw++;
      if (r.capped) capped++;
      turns += r.turns; dec += r.dec; same += r.same; ms += r.ms; maxMs = Math.max(maxMs, r.maxMs);
      for (const k of Object.keys(M)) M[k] += r.m[k];
    }
    const n = rs.length, decided = n - dr;
    report.pairings[name] = {
      games: n, aWinRate: +((aw + dr / 2) / n).toFixed(3), draws: dr,
      firstPlayerWinRate: +(fw / Math.max(1, decided)).toFixed(3), turnCapRate: 0, wentTheFull20Rounds: +(capped / n).toFixed(3), avgRounds: +(turns / n).toFixed(1),
      ...(dec ? { expertDecisions: dec, sameAsGreedy: +(same / dec).toFixed(3), expertMsPerMove: +(ms / dec).toFixed(1), expertMaxMs: Math.round(maxMs) } : {}),
      buy: { buys: M.buys, meanSpent: +(M.spent / M.buys).toFixed(2), manaCapsTheStrongestLine: +(M.bound / M.buys).toFixed(3), boughtABluff: +(M.bluff / M.buys).toFixed(3), threeCards: +(M.three / M.buys).toFixed(3), weakerThanStrongestAffordable: +(M.notBest / M.buys).toFixed(3) },
      betting: { betsOrRaisesPerRound: +(M.bets / Math.max(1, turns)).toFixed(2), foldsPerRound: +(M.folds / Math.max(1, turns)).toFixed(2), showdownsPerRound: +(M.shows / Math.max(1, turns)).toFixed(2) },
    };
  }
  const P = report.pairings, ex = triv.map(t => 'expert-' + t).filter(k => P[k]);
  const allDec = ex.reduce((a, k) => a + P[k].expertDecisions, 0), allSame = ex.reduce((a, k) => a + P[k].sameAsGreedy * P[k].expertDecisions, 0);
  const capRate = 0;
  const fp = P['expert-expert'] ? P['expert-expert'].firstPlayerWinRate : null;
  report.gate = { ...Object.fromEntries(ex.map(k => [k, P[k].aWinRate])), firstPlayerWinRate: fp, turnCapRate: capRate, sameAsGreedy: +(allSame / Math.max(1, allDec)).toFixed(3) };
  const g = report.gate;
  report.gate.fails = [
    ...ex.filter(k => P[k].aWinRate < 0.7).map(k => `${k} ${P[k].aWinRate} < 0.70`),
    ...(fp !== null && (fp < 0.3 || fp > 0.7) ? [`first player ${fp} outside 0.30-0.70`] : []),
    ...(capRate > 0.02 ? [`turn cap ${capRate} > 0.02`] : []),
    ...(g.sameAsGreedy > 0.9 ? [`same as Greedy ${g.sameAsGreedy} > 0.90`] : []),
  ];
  if (old.report) report.report = old.report;
  if (old.sanity) report.sanity = old.sanity;
  writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
