// node sim.mjs [games] [workers]: the machine gate. Expert against every trivial bot, seats
// alternated on the same deals; Expert against itself for the first player's rate; how often a
// game hits the turn cap; how often Expert's turn is the one Greedy would have played.
// Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync } from 'node:fs';
import { cpus } from 'node:os';
import { newMatch, clone, _act, key, legalActions } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, mcExpert, EXPERT } from './src/bot.js';

const BOTS = { random: () => randomBot, greedy: () => greedyBot, racer: () => racerBot, expert: () => mcExpert(EXPERT) };

// One game. aSide is bot A's seat. With track, Expert (bot A) is compared with Greedy on every
// turn where it had a choice: the position its whole turn leads to, and each single action.
function playGame(A, B, seed, aSide, track) {
  const rng = makeRng(seed * 7919 + aSide);
  const s = newMatch({ seed });
  const first = s.first;
  const st = { turnsCmp: 0, turnsSame: 0, actsCmp: 0, actsSame: 0 };
  let greedyEnd = null, lastTurn = -1;
  while (s.winner === null) {
    const side = s.turn, bot = side === aSide ? A : B;
    if (track && side === aSide && s.turnNo !== lastTurn) {
      lastTurn = s.turnNo; greedyEnd = null;
      if (legalActions(s).length > 1) {
        const t = clone(s);
        for (let k = 0; k < 200 && t.winner === null; k++) { const g = greedyBot(t); if (g.t === 'end') break; _act(t, g); }
        greedyEnd = t.winner === aSide ? 'win' : key(t);
      }
    }
    const a = bot(s, rng);
    if (track && side === aSide) {
      const opts = new Set(legalActions(s).map(x => { if (x.t === 'end') return 'end'; const t = clone(s); _act(t, x); return key(t); }));
      if (opts.size > 1) {
        const g = greedyBot(s), kk = (x) => { if (x.t === 'end') return 'end'; const t = clone(s); _act(t, x); return key(t); };
        st.actsCmp++; if (kk(g) === kk(a)) st.actsSame++;
      }
      if (greedyEnd !== null && (a.t === 'end')) { st.turnsCmp++; if (key(s) === greedyEnd) st.turnsSame++; greedyEnd = null; }
    }
    _act(s, a);
    if (track && greedyEnd !== null && s.winner === aSide) { st.turnsCmp++; if (greedyEnd === 'win') st.turnsSame++; greedyEnd = null; }
  }
  return { winner: s.winner, aSide, first, turns: s.turnNo, capped: !!s.capped, ...st };
}

function runSlice({ a, b, games, seed0, track }) {
  const A = BOTS[a](), B = BOTS[b]();
  return games.map(g => playGame(A, B, seed0 + (g >> 1), g % 2, track));
}

if (!isMainThread) { parentPort.postMessage(runSlice(workerData)); }
else {
  const N = +(process.argv[2] || 400), W = +(process.argv[3] || Math.min(4, cpus().length));
  const pairings = [['expert', 'random'], ['expert', 'greedy'], ['expert', 'racer'], ['expert', 'expert'], ['greedy', 'greedy']];
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
      firstPlayerScore: +((fw + d / 2) / n).toFixed(3), capped: rs.filter(r => r.capped).length, avgTurnsEach: +(rs.reduce((x, r) => x + r.turns, 0) / n / 2).toFixed(1) };
    if (a === 'expert' && b === 'greedy') {
      const sum = (f) => rs.reduce((x, r) => x + r[f], 0);
      row.turnsCompared = sum('turnsCmp'); row.turnAgreement = +(sum('turnsSame') / sum('turnsCmp')).toFixed(3);
      row.actionsCompared = sum('actsCmp'); row.actionAgreement = +(sum('actsSame') / sum('actsCmp')).toFixed(3);
    }
    report.pairings[`${a}-${b}`] = row;
    console.log(`${a} vs ${b}:`, JSON.stringify(row), `${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  const P = report.pairings, all = Object.values(P);
  const capRate = all.reduce((x, r) => x + r.capped, 0) / all.reduce((x, r) => x + r.n, 0);
  report.gate = {
    expertVsRandom: P['expert-random'].aScore, expertVsGreedy: P['expert-greedy'].aScore, expertVsRacer: P['expert-racer'].aScore,
    capRate: +capRate.toFixed(4), turnAgreementWithGreedy: P['expert-greedy'].turnAgreement, actionAgreementWithGreedy: P['expert-greedy'].actionAgreement,
    firstPlayerScoreExpertMirror: P['expert-expert'].firstPlayerScore,
  };
  const g = report.gate, fails = [];
  for (const k of ['expertVsRandom', 'expertVsGreedy', 'expertVsRacer']) if (g[k] < 0.7) fails.push(`${k} ${g[k]} < 0.70`);
  if (g.capRate > 0.02) fails.push(`turn cap in ${g.capRate} of games`);
  if (g.turnAgreementWithGreedy > 0.9) fails.push(`Expert's turn equals Greedy's in ${g.turnAgreementWithGreedy}`);
  if (g.firstPlayerScoreExpertMirror < 0.3 || g.firstPlayerScoreExpertMirror > 0.7) fails.push(`first player ${g.firstPlayerScoreExpertMirror} outside 0.30-0.70`);
  report.fails = fails; report.alive = fails.length === 0; report.seconds = Math.round((Date.now() - t0) / 1000);
  writeFileSync(new URL('report.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
  console.log(fails.length ? 'DEAD: ' + fails.join('; ') : 'ALIVE');
}
