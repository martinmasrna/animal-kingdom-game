// node sim.mjs [games] [workers]: the night run's machine gate for 15 Key pieces.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, how often Expert's choice equals
// Greedy's, how games end (three Keys or a deck run out), and whether mana binds.
// Writes report.json (keeping its "report" key).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { newMatch, _act, CARDS, BOARD, MAX_MANA, actionKey, isPiece } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

// at the end of a turn: what the player left unused
function endStats(s, m) {
  const P = s.p[s.toAct];
  m.turns++; m.manaLeft += P.mana; if (P.mana > 0) m.manaLeftTurns++; if (P.maxMana >= MAX_MANA) m.atCap++;
  if (P.hand.some(id => id !== 'COIN' && CARDS[id].cost > P.mana && (!isPiece(id) || P.board.length < BOARD))) m.pricedOut++;
  if (P.hand.every(id => id === 'COIN')) m.handEmptied++;
}
function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0;
  const m = { turns: 0, manaLeft: 0, manaLeftTurns: 0, atCap: 0, pricedOut: 0, handEmptied: 0, plays: 0 };
  while (s.winner === null && steps < 5000) {
    const who = names[s.toAct], bot = BOTS[who];
    const a = bot(s, rng);
    if (who === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      if (actionKey(greedyBot(s, rng)) === actionKey(a)) agree++;
    }
    if (who === 'expert') { if (a.t === 'play') m.plays++; if (a.t === 'end') endStats(s, m); }
    _act(s, a); steps++;
  }
  return { winner: s.winner, why: s.why, aSide, first: s.first, turns: s.turnNo, capped: !!s.capped || s.winner === null, agree, decisions, m };
}

if (!isMainThread) {
  const { jobs } = workerData;
  for (const j of jobs) parentPort.postMessage({ pair: j.pair, r: playGame(j.a, j.b, j.g, j.seed0) });
  parentPort.postMessage({ done: true });
} else if (import.meta.url === `file://${process.argv[1]}`) {
  const N = +(process.argv[2] || 400), NW = +(process.argv[3] || 3);
  const pairs = [['expert', 'random', N], ['expert', 'greedy', N], ['expert', 'racer', N], ['expert', 'expert', N], ['greedy', 'greedy', 1000], ['racer', 'racer', 1000], ['greedy', 'racer', 1000]];
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
      if (++doneN % 100 === 0) console.error(`${doneN}/${jobs.length} games, ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    });
    w.on('error', (e) => { console.error(e); process.exit(1); });
  }
  function finish() {
    const RP = new URL('./report.json', import.meta.url);
    const prev = existsSync(RP) ? JSON.parse(readFileSync(RP, 'utf8')) : {};
    const out = { concept: '15-key-pieces', expert: EXPERT, pairings: {}, gate: {}, cost: {}, sanity: null, report: prev.report || null };
    let capped = 0, total = 0, agree = 0, dec = 0;
    const M = {};
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, fw = 0, turns = 0, cp = 0; const why = {};
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === r.first) fw++;
        turns += r.turns; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions; why[r.why || 'cap'] = (why[r.why || 'cap'] || 0) + 1;
        if (pair.startsWith('expert')) for (const [k, v] of Object.entries(r.m)) M[k] = (M[k] || 0) + v;
      }
      const n = rs.length; capped += cp; total += n;
      out.pairings[pair] = { games: n, aWinRate: +((aw + d / 2) / n).toFixed(4), draws: d, firstPlayerWinRate: +(fw / n).toFixed(4), avgTurns: +(turns / n).toFixed(1), capped: cp, endedBy: why };
    }
    const trivial = ['random', 'greedy', 'racer'].map(b => out.pairings['expert-' + b].aWinRate);
    const san = runSanity();
    out.sanity = san;
    const fp = out.pairings['expert-expert'].firstPlayerWinRate;
    out.gate = {
      expertMinWinRateVsTrivial: Math.min(...trivial), expertVsTrivialPass: Math.min(...trivial) >= 0.7,
      cappedRate: +(capped / total).toFixed(4), cappedPass: capped / total <= 0.02,
      expertGreedyAgreement: +(agree / dec).toFixed(4), agreementDecisions: dec, agreementPass: agree / dec <= 0.9,
      firstPlayerWinRateExpertMirror: fp, firstPlayerPass: fp >= 0.3 && fp <= 0.7,
      setPositionsPass: san.filter(x => x.bot === 'expert').every(x => x.pass),
      seconds: Math.round((Date.now() - t0) / 1000),
    };
    out.gate.allPass = out.gate.expertVsTrivialPass && out.gate.cappedPass && out.gate.agreementPass && out.gate.firstPlayerPass && out.gate.setPositionsPass;
    const T = M.turns;
    out.cost = {
      expertTurnsMeasured: T, manaCap: MAX_MANA,
      turnsAtManaCap: +(M.atCap / T).toFixed(3),
      turnsEndingWithManaUnspent: +(M.manaLeftTurns / T).toFixed(3), manaUnspentPerTurn: +(M.manaLeft / T).toFixed(2),
      turnsWithACardInHandPricedOut: +(M.pricedOut / T).toFixed(3), turnsHandEmptied: +(M.handEmptied / T).toFixed(3),
      cardsPlayedPerTurn: +(M.plays / T).toFixed(2),
    };
    writeFileSync(RP, JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ pairings: out.pairings, gate: out.gate, cost: out.cost }, null, 1));
  }
}
