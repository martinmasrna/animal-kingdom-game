// node sim.mjs [games] [workers]: the night run's machine gate for 25 Range duel.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for fighter A's rate (there is no first player; the start is mirrored), the
// turn-cap rate (20 turns, then life decides), and how often Expert's move equals Greedy's.
// There is no racer: nothing here can be raced. Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync } from 'node:fs';
import { newMatch, _submit, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, expert: expertBot(EXPERT) };

function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  const s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0;
  while (s.winner === null && steps < 1000) {
    // both sides are asked before either submits: neither sees the other's move
    const acts = [0, 1].map(side => s.need[side] ? BOTS[names[side]](s, side, rng) : null);
    for (const side of [0, 1]) {
      if (!acts[side]) continue;
      if (names[side] === 'expert' && aName === 'expert' && bName !== 'expert') {
        decisions++;
        if (actionKey(greedyBot(s, side)) === actionKey(acts[side])) agree++;
      }
    }
    for (const side of [0, 1]) if (acts[side] && s.need[side]) _submit(s, side, acts[side]);
    steps++;
  }
  return { winner: s.winner, aSide, turns: s.turn, capped: s.winner === null, timeout: s.p[0].life > 0 && s.p[1].life > 0, agree, decisions };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 4);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'expert', Math.min(N, 200)], ['greedy', 'greedy', 1000]];
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
      if (++doneN % 100 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const out = { concept: '25-range-duel', expert: EXPERT, note: 'no first player: the first-player check reads fighter A\'s win rate (the start is mirrored); capped = games with no result (impossible: turn 20 decides on life); decidedOnLifeAtTurn20 counts the games that went the distance', pairings: {}, gate: {} };
    let capped = 0, total = 0, agree = 0, dec = 0;
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, sa = 0, turns = 0, cp = 0, to = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === 0) sa++; else if (r.winner === 'draw') sa += 0.5;
        turns += r.turns; if (r.capped) cp++; if (r.timeout) to++;
        agree += r.agree; dec += r.decisions;
      }
      if (pair.startsWith('expert-')) { capped += cp; total += rs.length; }
      out.pairings[pair] = { games: rs.length, aWinRate: +((aw + d / 2) / rs.length).toFixed(4), draws: d, seatAWinRate: +(sa / rs.length).toFixed(4), avgTurns: +(turns / rs.length).toFixed(1), capped: cp, decidedOnLifeAtTurn20: to };
    }
    const P = out.pairings;
    const minVs = Math.min(...['random', 'greedy'].map(b => P['expert-' + b].aWinRate));
    out.gate = {
      expertMinWinRateVsTrivial: minVs,
      expertVsTrivialPass: minVs >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02, cappedCountedOver: 'the games Expert plays',
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      firstPlayerWinRateExpertMirror: P['expert-expert'].seatAWinRate,
      firstPlayerPass: P['expert-expert'].seatAWinRate >= 0.3 && P['expert-expert'].seatAWinRate <= 0.7,
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
