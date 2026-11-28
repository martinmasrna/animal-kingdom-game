// node sim.mjs [games] [workers] [mirrorGames]: the night run's machine gate for 24 Rally. Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, how often Expert's choice equals
// Greedy's, and whether mana binds. Writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync } from 'node:fs';
import { newMatch, _act, CARDS, actionKey, lastShot } from './src/engine.js';
import { makeRng, randomBot, greedyBot, saverBot, expertBot, EXPERT } from './src/bot.js';
import { legalActions } from './src/engine.js';
const candidates = (s) => legalActions(s);
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, saver: saverBot, expert: expertBot(EXPERT) };

// does stamina bind? At every Expert shot: is a card it could otherwise play (Reach enough) out of
// reach of its stamina; at the end of each game: the stamina it never spent.
function probeShot(s, cs) {
  const P = s.p[s.toAct], l = lastShot(s);
  const fits = P.hand.filter(id => !l || CARDS[id].reach >= CARDS[l.card].pace);
  cs.turns++;
  if (fits.some(id => CARDS[id].cost > P.stamina)) cs.constrained++;
  if (P.stamina === 0) cs.atCap++;
}

function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0, games = 0;
  const cs = { turns: 0, constrained: 0, atCap: 0, unspent: 0, manaAvail: 0, leftWhileBlocked: 0, serverPoints: 0, points: 0 };
  while (s.winner === null && steps < 6000) {
    const who = names[s.toAct], bot = BOTS[who];
    if (who === 'expert') probeShot(s, cs);
    const a = bot(s, rng);
    const before = s.gameNo, server = s.server, pts = s.p[0].points + s.p[1].points + 10 * (s.p[0].games + s.p[1].games), sp = s.p[server].points + 10 * s.p[server].games;
    if (who === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      if (actionKey(greedyBot(s, rng)) === actionKey(a)) agree++;
    }
    const stam = [s.p[0].stamina, s.p[1].stamina];
    _act(s, a); steps++;
    if (s.gameNo !== before || s.winner !== null) { for (const x of [0, 1]) if (names[x] === 'expert') { cs.unspent += stam[x]; cs.manaAvail += 10; } }
    const pts2 = s.p[0].points + s.p[1].points + 10 * (s.p[0].games + s.p[1].games);
    if (pts2 !== pts || s.gameNo !== before || s.winner !== null) { cs.points++; if (s.p[server].points + 10 * s.p[server].games > sp || s.winner === server) cs.serverPoints++; }
  }
  return { winner: s.winner, aSide, first: s.first, turns: s.turnNo, capped: !!s.capped || s.winner === null, agree, decisions, cs, games: s.gameNo };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 4), NM = +(process.argv[4] || 200);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'saver', N], ['expert', 'expert', NM], ['greedy', 'greedy', 1000], ['saver', 'saver', 1000]];
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
      if (++doneN % 50 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const out = { concept: '24-rally', expert: EXPERT, pairings: {}, gate: {}, costBinding: {} };
    let capped = 0, total = 0, agree = 0, dec = 0;
    const cs = { turns: 0, constrained: 0, atCap: 0, unspent: 0, manaAvail: 0, leftWhileBlocked: 0, serverPoints: 0, points: 0 };
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, fw = 0, fd = 0, turns = 0, cp = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === r.first) fw++; else if (r.winner === 'draw') fd++;
        turns += r.turns; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions;
        if (pair === 'expert-expert') for (const k in cs) cs[k] += r.cs[k];
      }
      if (pair.startsWith('expert-')) { capped += cp; total += rs.length; }
      out.pairings[pair] = { games: rs.length, aWinRate: +((aw + d / 2) / rs.length).toFixed(4), draws: d, firstPlayerWinRate: +((fw + fd / 2) / rs.length).toFixed(4), avgTurns: +(turns / rs.length).toFixed(1), capped: cp };
    }
    const P = out.pairings;
    const minVs = Math.min(...['random', 'greedy', 'saver'].map(b => P['expert-' + b].aWinRate));
    out.gate = {
      expertMinWinRateVsTrivial: minVs,
      expertVsTrivialPass: minVs >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02, cappedCountedOver: 'every game Expert plays (no cap is needed: a point ends within ten shots)', firstPlayerMeans: 'the first server',
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      firstPlayerWinRateExpertMirror: P['expert-expert'].firstPlayerWinRate,
      firstPlayerPass: P['expert-expert'].firstPlayerWinRate >= 0.3 && P['expert-expert'].firstPlayerWinRate <= 0.7,
      seconds: Math.round((Date.now() - t0) / 1000),
    };
    out.costBinding = {
      measuredIn: 'Expert mirror, both seats, every shot',
      shots: cs.turns,
      aFittingCardUnaffordableRate: +(cs.constrained / cs.turns).toFixed(3),
      atZeroStaminaRate: +(cs.atCap / cs.turns).toFixed(3),
      unspentStaminaShareAtGameEnd: +(cs.unspent / cs.manaAvail).toFixed(3),
      serverWinsPointRate: +(cs.serverPoints / cs.points).toFixed(3),
    };
    out.sanity = runSanity(expertBot(EXPERT)).map(({ position, bot, pass, passed, of }) => ({ position, bot, pass, passed, of }));
    out.gate.setPositionsPass = out.sanity.filter(r => r.bot === 'expert').every(r => r.pass);
    out.gate.allPass = out.gate.expertVsTrivialPass && out.gate.cappedPass && out.gate.agreementPass && out.gate.firstPlayerPass && out.gate.setPositionsPass;
    try { const prev = JSON.parse(readFileSync(new URL('./report.json', import.meta.url), 'utf8')); if (prev.report) out.report = prev.report; } catch (e) {}
    writeFileSync(new URL('./report.json', import.meta.url), JSON.stringify(out, null, 2) + '\n');
    console.log(JSON.stringify(out, null, 2));
  }
}
