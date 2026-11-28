// node sim.mjs [games] [workers]: the night run's machine gate for 34 Pitch to pay.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, how often Expert's choice equals
// Greedy's, and whether paying binds (what is left in hand and in the pool when a turn ends).
// Writes report.json (keeping its "report" key).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { newMatch, _act, CARDS, BOARD, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

// at the end of a turn: what the player left unused
function endStats(s, m) {
  const P = s.p[s.toAct];
  m.turns++; m.poolLeft += P.pool; if (P.pool > 0) m.poolLeftTurns++;
  m.handLeft += P.hand.length; if (P.hand.length === 0) m.handEmptied++;
  // a card that could be played if paying were free, still in hand
  if (P.hand.some(id => CARDS[id].kind === 'spell' || P.board.length < BOARD)) m.unplayedPlayable++;
  // a card that could not be paid for even pitching every other card in hand
  const sum = P.hand.reduce((x, id) => x + CARDS[id].pitch, 0);
  if (P.hand.some(id => CARDS[id].cost > P.pool + sum - CARDS[id].pitch)) m.unaffordable++;
}
function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0, pitchAgree = 0, pitchDec = 0;
  const m = { turns: 0, poolLeft: 0, poolLeftTurns: 0, handLeft: 0, handEmptied: 0, unplayedPlayable: 0, unaffordable: 0, pitches: 0, plays: 0, wastedPitches: 0 };
  let pitchedThisTurn = [];
  while (s.winner === null && steps < 5000) {
    const who = names[s.toAct], bot = BOTS[who];
    const a = bot(s, rng);
    if (who === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      const gA = greedyBot(s, rng);
      if (actionKey(gA) === actionKey(a)) agree++;
      if (a.t === 'pitch' || gA.t === 'pitch') { pitchDec++; if (actionKey(gA) === actionKey(a)) pitchAgree++; }
    }
    if (who === 'expert') {
      if (a.t === 'pitch') { m.pitches++; pitchedThisTurn.push(CARDS[a.card].pitch); }
      if (a.t === 'play') m.plays++;
      if (a.t === 'end') { endStats(s, m); m.wastedPitches += pitchedThisTurn.filter(p => s.p[s.toAct].pool >= p).length; pitchedThisTurn = []; }
    }
    _act(s, a); steps++;
  }
  return { winner: s.winner, aSide, first: s.first, turns: s.turnNo, capped: !!s.capped || s.winner === null, agree, decisions, pitchAgree, pitchDec, m };
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
    const out = { concept: '34-pitch-to-pay', expert: EXPERT, pairings: {}, gate: {}, cost: {}, sanity: null, report: prev.report || null }; // report: the verdict, the loop notes, the rule change and the as-specified run
    let capped = 0, total = 0, agree = 0, dec = 0, pa = 0, pd = 0;
    const M = {};
    for (const [pair, rs] of Object.entries(res)) {
      let aw = 0, d = 0, fw = 0, turns = 0, cp = 0;
      for (const r of rs) {
        if (r.winner === 'draw') d++; else if (r.winner === r.aSide) aw++;
        if (r.winner === r.first) fw++;
        turns += r.turns; if (r.capped) cp++;
        agree += r.agree; dec += r.decisions; pa += r.pitchAgree; pd += r.pitchDec;
        if (pair.startsWith('expert')) for (const [k, v] of Object.entries(r.m)) M[k] = (M[k] || 0) + v;
      }
      const n = rs.length; capped += cp; total += n;
      out.pairings[pair] = { games: n, aWinRate: +((aw + d / 2) / n).toFixed(4), draws: d, firstPlayerWinRate: +(fw / n).toFixed(4), avgTurns: +(turns / n).toFixed(1), capped: cp };
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
      expertTurnsMeasured: T,
      pitchesPerTurn: +(M.pitches / T).toFixed(2), playsPerTurn: +(M.plays / T).toFixed(2),
      turnsEndingWithManaLeft: +(M.poolLeftTurns / T).toFixed(3), manaLeftPerTurn: +(M.poolLeft / T).toFixed(2),
      pitchesWhoseManaWentUnused: +(M.wastedPitches / M.pitches).toFixed(3),
      cardsLeftInHandPerTurn: +(M.handLeft / T).toFixed(2), turnsHandEmptied: +(M.handEmptied / T).toFixed(3),
      turnsEndingWithAPlayableCardKept: +(M.unplayedPlayable / T).toFixed(3),
      turnsWithACardUnpayableEvenPitchingAll: +(M.unaffordable / T).toFixed(3),
      expertGreedyAgreementOnPitchDecisions: +(pa / pd).toFixed(4), pitchDecisions: pd,
    };
    writeFileSync(RP, JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ pairings: out.pairings, gate: out.gate, cost: out.cost }, null, 1));
  }
}
