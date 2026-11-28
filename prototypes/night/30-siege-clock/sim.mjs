// node sim.mjs [games=400] [workers=4] [only=pairing,...]: the machine gate for an asymmetric game.
// Expert against every trivial bot, Expert taking each role in half the games (the Racer exists
// only as an Attacker, so against it Expert always defends); Expert against itself and Greedy
// against itself for the role check (the Attacker's win rate must lie within 30-70%); turn
// caps (none possible: the game ends after ten rounds); how often Expert's choice equals
// Greedy's; whether mana binds. Each finished game is appended to sim-progress.jsonl and a rerun
// skips the games already there. Writes report.json (keeping its "report" and "sanity" keys).
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, appendFileSync, existsSync, readFileSync } from 'node:fs';
import { newMatch, act, isLegal, CARDS, GATE } from './src/engine.js';
import { makeRng, expertBot, cands, EXPERT, TRIVIAL, meaning } from './src/bot.js';

function manaAtEnd(s) {
  const P = s.p[s.toMove];
  const useful = (id) => !((id === 'RP' && s.gate >= GATE) || ((id === 'AD' || id === 'DD') && !P.deck.length));
  const real = P.hand.filter(useful);
  return { left: P.mana, couldPlay: real.some(id => CARDS[id].cost <= P.mana), priced: real.some(id => CARDS[id].cost > P.mana) };
}
function playGame(bots, seed, rngSeed, attacker, track) {
  const rng = makeRng(rngSeed);
  let s = newMatch({ seed, attacker });
  let dec = 0, same = 0, ms = 0, maxMs = 0, steps = 0;
  const m = { turns: 0, leftWithPlay: 0, priced: 0, sumLeft: 0 };
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
    if (a.t === 'end') { const e = manaAtEnd(s); m.turns++; m.sumLeft += e.left; if (e.left > 0 && e.couldPlay) m.leftWithPlay++; if (e.priced) m.priced++; }
    s = act(s, a);
    if (++steps > 20000) throw new Error('runaway game');
  }
  return { winner: s.winner, att: s.att, rounds: s.round, gate: s.gate, dec, same, ms, maxMs, m };
}

const mk = (name) => name === 'expert' ? expertBot(EXPERT) : TRIVIAL[name];

if (!isMainThread) {
  for (const j of workerData.jobs) parentPort.postMessage({ ...j, r: playGame([mk(j.b0), mk(j.b1)], j.seed, j.rngSeed, j.att, j.track) });
  parentPort.postMessage('done');
} else {
  const N = +(process.argv[2] || 400), W = +(process.argv[3] || 4), only = process.argv[4] ? process.argv[4].split(',') : null;
  const jobs = [];
  // aSeat: the seat of bot a; att: the Attacker's seat. roles: 'both' alternates bot a's role
  // game by game, 'D' makes bot a always the Defender.
  const pair = (name, a, b, n, seed0, track, roles = 'both') => {
    if (only && !only.includes(name)) return;
    for (let g = 0; g < n; g++) {
      const aSeat = (g >> 1) % 2, aAttacks = roles === 'D' ? false : g % 2 === 0;
      const att = aAttacks ? aSeat : 1 - aSeat;
      jobs.push({ name, aSeat, att, b0: aSeat === 0 ? a : b, b1: aSeat === 0 ? b : a, seed: seed0 + g, rngSeed: seed0 * 31 + g, track: track ? aSeat : -1 });
    }
  };
  pair('expert-random', 'expert', 'random', N, 1000, true);
  pair('expert-greedy', 'expert', 'greedy', N, 2000, true);
  pair('expert-racer', 'expert', 'racer', N, 3000, true, 'D');
  pair('expert-expert', 'expert', 'expert', N, 9000, false);
  pair('greedy-greedy', 'greedy', 'greedy', 2000, 10000, false);
  pair('greedy-random', 'greedy', 'random', N, 11000, false);
  pair('greedy-racer', 'greedy', 'racer', N, 12000, false, 'D');
  const PROG = new URL('./sim-progress.jsonl', import.meta.url), id = (j) => j.name + ':' + j.seed + ':' + j.aSeat + ':' + j.att;
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
    let aw = 0, attW = 0, aAtt = 0, aAttW = 0, aDef = 0, aDefW = 0, rounds = 0, gate = 0, dec = 0, same = 0, ms = 0, maxMs = 0;
    const M = { turns: 0, leftWithPlay: 0, priced: 0, sumLeft: 0 };
    for (const j of rs) {
      const r = j.r, aWon = r.winner === j.aSeat;
      if (aWon) aw++;
      if (r.winner === r.att) attW++;
      if (j.att === j.aSeat) { aAtt++; if (aWon) aAttW++; } else { aDef++; if (aWon) aDefW++; }
      rounds += r.rounds; gate += r.gate; dec += r.dec; same += r.same; ms += r.ms; maxMs = Math.max(maxMs, r.maxMs);
      for (const k of Object.keys(M)) M[k] += r.m[k];
    }
    const n = rs.length;
    report.pairings[name] = {
      games: n, aWinRate: +(aw / n).toFixed(3), aWinRateAsAttacker: aAtt ? +(aAttW / aAtt).toFixed(3) : null, aWinRateAsDefender: aDef ? +(aDefW / aDef).toFixed(3) : null,
      attackerWinRate: +(attW / n).toFixed(3), turnCapRate: 0, avgRounds: +(rounds / n).toFixed(1), avgGateLeft: +(gate / n).toFixed(1),
      ...(dec ? { expertDecisions: dec, sameAsGreedy: +(same / dec).toFixed(3), expertMsPerMove: +(ms / dec).toFixed(1), expertMaxMs: Math.round(maxMs) } : {}),
      mana: { turns: M.turns, meanLeftAtEnd: +(M.sumLeft / M.turns).toFixed(2), leftManaWithAPlayableCard: +(M.leftWithPlay / M.turns).toFixed(3), heldACardItCouldNotAfford: +(M.priced / M.turns).toFixed(3) },
    };
  }
  const P = report.pairings, ex = Object.keys(TRIVIAL).map(t => 'expert-' + t).filter(k => P[k]);
  const allDec = ex.reduce((a, k) => a + P[k].expertDecisions, 0), allSame = ex.reduce((a, k) => a + P[k].sameAsGreedy * P[k].expertDecisions, 0);
  const role = P['expert-expert'] ? P['expert-expert'].attackerWinRate : null;
  report.gate = { ...Object.fromEntries(ex.map(k => [k, P[k].aWinRate])), attackerWinRate: role, turnCapRate: 0, sameAsGreedy: +(allSame / Math.max(1, allDec)).toFixed(3) };
  const g = report.gate;
  report.gate.fails = [
    ...ex.filter(k => P[k].aWinRate < 0.7).map(k => `${k} ${P[k].aWinRate} < 0.70`),
    ...(role !== null && (role < 0.3 || role > 0.7) ? [`attacker (role) win rate ${role} outside 0.30-0.70`] : []),
    ...(g.sameAsGreedy > 0.9 ? [`same as Greedy ${g.sameAsGreedy} > 0.90`] : []),
  ];
  if (old.report) report.report = old.report;
  if (old.sanity) report.sanity = old.sanity;
  writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
