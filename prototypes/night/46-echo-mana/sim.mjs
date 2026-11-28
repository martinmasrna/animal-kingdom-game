// node sim.mjs [games=400] [workers=4] [only=pairing,...]: the machine gate. Expert against every
// trivial bot, seats alternated on the same deals; Expert against itself and Greedy against
// itself for the first-player rate; turn caps; how often Expert's choice equals Greedy's; and
// whether mana binds (how often it sits at the cap or the floor, how often a player ends a turn
// with mana left and a card it could have played, how often a card in hand costs more than the
// mana left). Each finished game is appended to sim-progress.jsonl and a rerun skips the games
// already there, so a killed run resumes. Writes report.json (keeping its "report" key).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';
import { newMatch, act, isLegal, CARDS, BOARD, MAX_MANA, MIN_MANA } from './src/engine.js';
import { makeRng, expertBot, cands, EXPERT, TRIVIAL, meaning } from './src/bot.js';

// what a turn's end says about mana: its total, what is left, whether a card in hand could still
// have been played (a choice to leave mana), whether a card in hand cost more than was left
function manaAtEnd(s) {
  const P = s.p[s.turn];
  const real = P.hand.filter(id => id !== 'COIN' && (CARDS[id].kind !== 'Unit' || P.board.length < BOARD));
  return { mana: P.mana - (P.hand.includes('COIN') ? 0 : 0), left: P.left, spent: P.spent, couldPlay: real.some(id => CARDS[id].cost <= P.left), priced: real.some(id => CARDS[id].cost > P.left) };
}
function playGame(bots, seed, rngSeed, track) {
  const rng = makeRng(rngSeed);
  let s = newMatch({ seed });
  let dec = 0, same = 0, ms = 0, maxMs = 0, steps = 0;
  const m = { turns: 0, atCap: 0, atFloor: 0, sumMana: 0, sumSpent: 0, leftWithPlay: 0, priced: 0, starts: 0 };
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
    if (a.t === 'end') {
      const e = manaAtEnd(s);
      m.turns++; m.sumMana += e.mana; m.sumSpent += e.spent;
      if (e.mana >= MAX_MANA) m.atCap++; if (e.mana <= MIN_MANA) m.atFloor++;
      if (e.left > 0 && e.couldPlay) m.leftWithPlay++;
      if (e.priced) m.priced++;
    }
    s = act(s, a);
    if (++steps > 20000) throw new Error('runaway game');
  }
  return { winner: s.winner, first: s.first, turns: s.turnNo, capped: !!s.capped, dec, same, ms, maxMs, m };
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
  pair('greedy-starver', 'greedy', 'starver', N, 12000, false);
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
    const M = { turns: 0, atCap: 0, atFloor: 0, sumMana: 0, sumSpent: 0, leftWithPlay: 0, priced: 0 };
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
      firstPlayerWinRate: +(fw / Math.max(1, decided)).toFixed(3), turnCapRate: +(capped / n).toFixed(3), avgTurns: +(turns / n).toFixed(1),
      ...(dec ? { expertDecisions: dec, sameAsGreedy: +(same / dec).toFixed(3), expertMsPerMove: +(ms / dec).toFixed(1), expertMaxMs: Math.round(maxMs) } : {}),
      mana: { turns: M.turns, meanMana: +(M.sumMana / M.turns).toFixed(2), meanSpent: +(M.sumSpent / M.turns).toFixed(2), atCap: +(M.atCap / M.turns).toFixed(3), atFloor: +(M.atFloor / M.turns).toFixed(3),
        leftManaWithAPlayableCard: +(M.leftWithPlay / M.turns).toFixed(3), heldACardItCouldNotAfford: +(M.priced / M.turns).toFixed(3) },
    };
  }
  const P = report.pairings, ex = triv.map(t => 'expert-' + t).filter(k => P[k]);
  const allDec = ex.reduce((a, k) => a + P[k].expertDecisions, 0), allSame = ex.reduce((a, k) => a + P[k].sameAsGreedy * P[k].expertDecisions, 0);
  const capRate = Math.max(...Object.values(P).map(p => p.turnCapRate));
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
