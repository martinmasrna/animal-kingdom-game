// node sim.mjs [games] [workers]: the night run's machine gate for 37 Price tracks.
// Expert against every trivial bot (seats alternated, both seats on the same deals), Expert
// against itself for the first-player rate, the turn-cap rate, how often Expert's choice equals
// Greedy's, whether coin binds (how often it sits at its cap), and how games end.
// Writes report.json (keeping its "report" key).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import { newMatch, _act, CARDS, COIN_CAP, actionKey, counts } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, candidates, EXPERT } from './src/bot.js';
import { runSanity } from './sanity.mjs';

const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, expert: expertBot(EXPERT) };

// at the end of a turn: what the player left unused
function endStats(s, m) {
  const P = s.p[s.toAct];
  m.turns++; m.coinLeft += P.coin; if (P.coin >= COIN_CAP) m.atCapEnd++; if (P.coin >= 4) m.coinFourPlus++;
  if (P.hand.some(id => CARDS[id].kind !== 'good' && CARDS[id].cost > P.coin)) m.pricedOut++;
  if (P.hand.some(id => CARDS[id].kind !== 'good')) m.actionHeld++;
  const c = counts(P.hand); m.goodsHeld += c.X + c.Y + c.Z;
}
function playGame(aName, bName, g, seed0) {
  const rng = makeRng(seed0 * 7919 + g * 31 + 1);
  let s = newMatch({ seed: seed0 + (g >> 1) * 2 + 1 });
  const aSide = g % 2, names = [];
  names[aSide] = aName; names[1 - aSide] = bName;
  let agree = 0, decisions = 0, steps = 0;
  const m = { turns: 0, coinLeft: 0, atCapEnd: 0, atCapStart: 0, coinFourPlus: 0, pricedOut: 0, actionHeld: 0, goodsHeld: 0, sells: 0, soldCards: 0, sellPrice: 0, boosts: 0, crashes: 0, spies: 0, noSellTurns: 0 };
  let soldThisTurn = false, lastTurn = -1;
  while (s.winner === null && steps < 5000) {
    const who = names[s.toAct], bot = BOTS[who];
    const a = bot(s, rng);
    if (who === 'expert' && bName !== 'expert' && candidates(s).length > 1) {
      decisions++;
      if (actionKey(greedyBot(s, rng)) === actionKey(a)) agree++;
    }
    if (who === 'expert') {
      if (s.turnNo !== lastTurn) { lastTurn = s.turnNo; if (s.p[s.toAct].coin >= COIN_CAP) m.atCapStart++; }
      if (a.t === 'sell') { m.sells++; m.soldCards += a.n; m.sellPrice += s.price[a.good] * a.n; soldThisTurn = true; }
      if (a.t === 'play') { if (a.card === 'BOO') m.boosts++; if (a.card === 'CRA') m.crashes++; if (a.card === 'SPY') m.spies++; }
      if (a.t === 'end') { endStats(s, m); if (!soldThisTurn) m.noSellTurns++; soldThisTurn = false; }
    }
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
    const out = { concept: '37-price-tracks', expert: EXPERT, pairings: {}, gate: {}, cost: {}, sanity: null, report: prev.report || null };
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
      expertTurnsMeasured: T, coinCap: COIN_CAP,
      turnsStartingAtCoinCap: +(M.atCapStart / T).toFixed(3), turnsEndingAtCoinCap: +(M.atCapEnd / T).toFixed(3), turnsEndingWithFourPlusCoin: +(M.coinFourPlus / T).toFixed(3),
      coinLeftPerTurn: +(M.coinLeft / T).toFixed(2),
      turnsWithAnActionCardPricedOut: +(M.pricedOut / T).toFixed(3), turnsEndingWithAnActionCardHeld: +(M.actionHeld / T).toFixed(3),
      boostsPerTurn: +(M.boosts / T).toFixed(3), crashesPerTurn: +(M.crashes / T).toFixed(3), spiesPerTurn: +(M.spies / T).toFixed(3),
      turnsWithoutASale: +(M.noSellTurns / T).toFixed(3), cardsPerSale: +(M.soldCards / M.sells).toFixed(2), pricePerCardSold: +(M.sellPrice / M.soldCards).toFixed(2),
      goodsHeldAtTurnEnd: +(M.goodsHeld / T).toFixed(2),
    };
    writeFileSync(RP, JSON.stringify(out, null, 2));
    console.log(JSON.stringify({ pairings: out.pairings, gate: out.gate, cost: out.cost }, null, 1));
  }
}
