// node sim.mjs [games=400] [workers=4] [only=pairing,...]: the machine gate for a game with no
// first player. Expert against every trivial bot, seats alternated on the same deals; Expert
// against itself and Greedy against itself for the seat check (seat A's win rate, read in place
// of the first player's); games that run all 12 rounds (the rules' own end, not a cap); how often
// Expert's choice equals Greedy's; and whether gold binds (what is left at the end of a shop, how
// often a shop ends with gold and an affordable card it did not buy, how often the deck sits at
// its cap of 10, rerolls and removals). Each finished game is appended to sim-progress.jsonl and
// a rerun skips the games already there. Writes report.json (keeping its "report" and "sanity" keys).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';
import { newMatch, act, isLegal, legalActions, CARDS, DECK_MAX, ROUNDS } from './src/engine.js';
import { makeRng, expertBot, EXPERT, TRIVIAL, meaning } from './src/bot.js';

function playGame(bots, seed, rngSeed, track) {
  const rng = makeRng(rngSeed);
  let s = newMatch({ seed });
  let dec = 0, same = 0, ms = 0, maxMs = 0, steps = 0;
  const m = { shops: 0, left: 0, leftWithBuy: 0, atCap: 0, rerolls: 0, removes: 0, buys: 0, spentOn: {} };
  while (s.winner === null) {
    const who = s.toMove;
    const t0 = performance.now();
    const a = bots[who](s, rng);
    const dt = performance.now() - t0;
    if (track === who) {
      ms += dt; if (dt > maxMs) maxMs = dt;
      if (legalActions(s).length > 1) { dec++; if (meaning(s, TRIVIAL.greedy(s, rng)) === meaning(s, a)) same++; }
    }
    if (!isLegal(s, a)) throw new Error('bot made an illegal move');
    const P = s.p[who];
    if (a.t === 'done') {
      m.shops++; m.left += P.gold;
      if (P.deck.length >= DECK_MAX) m.atCap++;
      if (P.gold > 0 && P.deck.length < DECK_MAX && P.shop.some(id => id && CARDS[id].cost <= P.gold)) m.leftWithBuy++;
    }
    if (a.t === 'reroll') m.rerolls++;
    if (a.t === 'remove') m.removes++;
    if (a.t === 'buy') { m.buys++; const id = P.shop[a.i]; m.spentOn[id] = (m.spentOn[id] || 0) + 1; }
    s = act(s, a);
    if (++steps > 20000) throw new Error('runaway game');
  }
  return { winner: s.winner, first: 0, rounds: s.round, full: s.round >= ROUNDS, lives: [s.p[0].life, s.p[1].life], dec, same, ms, maxMs, m };
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
      const aSeat = g % 2;
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
  const OUT = new URL('./report.json', import.meta.url);
  const old = existsSync(OUT) ? JSON.parse(readFileSync(OUT, 'utf8')) : {};
  const report = { games: N, expert: EXPERT, seconds: Math.round((Date.now() - t0) / 1000), pairings: {} };
  for (const [name, rs] of Object.entries(by)) {
    let aw = 0, dr = 0, seatA = 0, full = 0, rounds = 0, dec = 0, same = 0, ms = 0, maxMs = 0;
    const M = { shops: 0, left: 0, leftWithBuy: 0, atCap: 0, rerolls: 0, removes: 0, buys: 0 }, spentOn = {};
    for (const j of rs) {
      const r = j.r;
      if (r.winner === 'draw') { dr++; seatA += 0.5; } else { if (r.winner === j.aSeat) aw++; if (r.winner === 0) seatA++; }
      if (r.full) full++;
      rounds += r.rounds; dec += r.dec; same += r.same; ms += r.ms; maxMs = Math.max(maxMs, r.maxMs);
      for (const k of Object.keys(M)) M[k] += r.m[k];
      for (const [k, v] of Object.entries(r.m.spentOn)) spentOn[k] = (spentOn[k] || 0) + v;
    }
    const n = rs.length;
    report.pairings[name] = {
      games: n, aWinRate: +((aw + dr / 2) / n).toFixed(3), draws: dr, seatAWinRate: +(seatA / n).toFixed(3), turnCapRate: 0, wentAll12Rounds: +(full / n).toFixed(3), avgRounds: +(rounds / n).toFixed(1),
      ...(dec ? { expertDecisions: dec, sameAsGreedy: +(same / dec).toFixed(3), expertMsPerMove: +(ms / dec).toFixed(1), expertMaxMs: Math.round(maxMs) } : {}),
      gold: { shops: M.shops, meanGoldLeft: +(M.left / M.shops).toFixed(2), endedWithGoldAndAnAffordableCard: +(M.leftWithBuy / M.shops).toFixed(3), deckAtCap: +(M.atCap / M.shops).toFixed(3),
        rerollsPerShop: +(M.rerolls / M.shops).toFixed(2), removesPerShop: +(M.removes / M.shops).toFixed(2), buysPerShop: +(M.buys / M.shops).toFixed(2),
        boughtShare: Object.fromEntries(Object.entries(spentOn).sort((a, b) => b[1] - a[1]).map(([k, v]) => [CARDS[k].name, +(v / Math.max(1, M.buys)).toFixed(3)])) },
    };
  }
  const P = report.pairings, ex = triv.map(t => 'expert-' + t).filter(k => P[k]);
  const allDec = ex.reduce((a, k) => a + P[k].expertDecisions, 0), allSame = ex.reduce((a, k) => a + P[k].sameAsGreedy * P[k].expertDecisions, 0);
  const seat = P['expert-expert'] ? P['expert-expert'].seatAWinRate : null;
  report.gate = { ...Object.fromEntries(ex.map(k => [k, P[k].aWinRate])), seatAWinRate: seat, turnCapRate: 0, sameAsGreedy: +(allSame / Math.max(1, allDec)).toFixed(3) };
  const g = report.gate;
  report.gate.fails = [
    ...ex.filter(k => P[k].aWinRate < 0.7).map(k => `${k} ${P[k].aWinRate} < 0.70`),
    ...(seat !== null && (seat < 0.3 || seat > 0.7) ? [`seat A ${seat} outside 0.30-0.70`] : []),
    ...(g.sameAsGreedy > 0.9 ? [`same as Greedy ${g.sameAsGreedy} > 0.90`] : []),
  ];
  if (old.report) report.report = old.report;
  if (old.sanity) report.sanity = old.sanity;
  writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
