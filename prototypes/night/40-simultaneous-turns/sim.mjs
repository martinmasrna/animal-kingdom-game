// node sim.mjs [games] [workers]: the night run's machine gate for 40 Simultaneous turns.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for seat A's rate (there is no first player), the round-cap rate, how often
// Expert's plan equals Greedy's, and whether mana binds. Writes report.json (keeping its "report" key).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { newMatch, _act, CARDS, BOARD, MAX_MANA, planKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

function planStats(s, pl, m) {
  const P = s.p[s.toAct];
  let cost = 0, units = 0; const rest = P.hand.slice();
  for (const x of pl.plays) { cost += CARDS[x.card].cost; if (CARDS[x.card].kind === 'unit') units++; rest.splice(rest.indexOf(x.card), 1); }
  const left = P.mana - cost;
  m.rounds++; m.manaLeft += left; if (left > 0) m.manaLeftRounds++; if (P.mana >= MAX_MANA) m.atCap++;
  if (rest.some(id => CARDS[id].cost > left)) m.cardPricedOut++;
  if (!rest.length) m.handEmptied++;
  m.cardsPlayed += pl.plays.length; m.attacks += pl.attacks.length; m.unitAttacks += pl.attacks.filter(a => a.to !== -1).length;
}
function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0;
  const m = { rounds: 0, manaLeft: 0, manaLeftRounds: 0, atCap: 0, cardPricedOut: 0, handEmptied: 0, cardsPlayed: 0, attacks: 0, unitAttacks: 0 };
  while (s.winner === null && steps < 1000) {
    const who = names[s.toAct], bot = BOTS[who];
    const a = bot(s, rng);
    if (who === 'expert') {
      planStats(s, a, m);
      if (bName !== 'expert' && candidates(s).length > 1) { decisions++; if (planKey(greedyBot(s)) === planKey(a)) agree++; }
    }
    _act(s, a); steps++;
  }
  return { winner: s.winner, aSide, rounds: s.round, capped: !!s.capped || s.winner === null, agree, decisions, m };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 3);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'racer', N], ['expert', 'expert', Math.min(N, 400)], ['greedy', 'greedy', 1000], ['racer', 'racer', 1000], ['greedy', 'racer', 1000]];
  const jobs = [];
  pairs.forEach(([a, b, n], k) => { for (let g = 0; g < n; g++) jobs.push({ pair: a + '-' + b, a, b, g, seed0: 1000 * (k + 1) }); });
  const buckets = Array.from({ length: NW }, () => []);
  jobs.forEach((j, i) => buckets[i % NW].push(j));
  const res = {}; let left = NW, doneN = 0; const t0 = Date.now();
  for (const b of buckets) {
    const w = new Worker(new URL(import.meta.url), { workerData: { jobs: b } });
    w.on('message', (msg) => {
      if (msg.done) { if (--left === 0) finish(); return; }
      (res[msg.pair] = res[msg.pair] || []).push(msg.r);
      if (++doneN % 200 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const RP = new URL('./report.json', import.meta.url);
    const prev = existsSync(RP) ? JSON.parse(readFileSync(RP, 'utf8')) : {};
    const out = { concept: '40-simultaneous-turns', expert: EXPERT, pairings: {}, gate: {}, cost: {}, sanity: null, report: prev.report || null };
    let capped = 0, total = 0, agree = 0, dec = 0; const M = {};
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, s0 = 0, rounds = 0, cp = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === 0) s0++; else if (r.winner === 'draw') s0 += 0.5;
        rounds += r.rounds; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions;
        for (const [k, v] of Object.entries(r.m)) M[k] = (M[k] || 0) + v;
      }
      const n = rs.length; capped += cp; total += n;
      out.pairings[pair] = { games: n, aWinRate: +((aw + d / 2) / n).toFixed(4), draws: d, seatAWinRate: +(s0 / n).toFixed(4), avgRounds: +(rounds / n).toFixed(1), capped: cp };
    }
    const trivial = ['random', 'greedy', 'racer'].map(b => out.pairings['expert-' + b].aWinRate);
    const san = runSanity(); out.sanity = san;
    const fp = out.pairings['expert-expert'].seatAWinRate;
    out.gate = {
      expertMinWinRateVsTrivial: Math.min(...trivial), expertVsTrivialPass: Math.min(...trivial) >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02,
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      seatAWinRateExpertMirror: fp, seatPass: fp >= 0.3 && fp <= 0.7,
      setPositionsPass: san.filter(x => x.bot === 'expert').every(x => x.pass),
      drawsCountHalf: true, seconds: Math.round((Date.now() - t0) / 1000),
    };
    out.gate.allPass = out.gate.expertVsTrivialPass && out.gate.cappedPass && out.gate.agreementPass && out.gate.seatPass && out.gate.setPositionsPass;
    const T = M.rounds;
    out.cost = {
      expertPlansMeasured: T, manaCap: MAX_MANA,
      roundsAtManaCap: +(M.atCap / T).toFixed(3),
      roundsEndingWithManaUnspent: +(M.manaLeftRounds / T).toFixed(3), manaUnspentPerRound: +(M.manaLeft / T).toFixed(2),
      roundsWithACardInHandPricedOut: +(M.cardPricedOut / T).toFixed(3),
      roundsHandEmptied: +(M.handEmptied / T).toFixed(3),
      cardsPlayedPerRound: +(M.cardsPlayed / T).toFixed(2), attacksAtUnitsShare: +(M.unitAttacks / Math.max(1, M.attacks)).toFixed(3),
    };
    writeFileSync(RP, JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ pairings: out.pairings, gate: out.gate, cost: out.cost }, null, 1));
  }
}
