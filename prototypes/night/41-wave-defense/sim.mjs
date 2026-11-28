// node sim.mjs [seeds=400] [budget=600] [versions=spec,flat4]: the machine gate for Wave defense, one player against the
// game. Expert, Greedy and Random play the same seeded games (same threat order, same first deck
// order, same reward offers). A pair goes to whoever ends better: a win beats a loss; two wins,
// more Wall; two losses, more rounds survived (the Wall is 0 in both). Expert must take 70% of the
// decided pairs against each trivial bot. Run for the spec's rules (mana = round, cap 8) and for
// the one rule change (mana 4 every round); writes report.json.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { writeFileSync, readFileSync, existsSync } from 'node:fs';
import os from 'node:os';
import { newMatch, act, legalActions } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot, sameDecision } from './src/bot.js';

const N = +(process.argv[2] || 400), BUDGET = +(process.argv[3] || 600);
const ALL = { spec: null, flat4: 4 }, ONLY = (process.argv[4] || 'spec,flat4').split(',');
const VERSIONS = Object.fromEntries(Object.entries(ALL).filter(([k]) => ONLY.includes(k)));

function play(name, seed, flatMana, budget) {
  const bot = name === 'random' ? randomBot : name === 'greedy' ? (s) => greedyBot(s) : expertBot({ budget });
  const rng = makeRng(seed * 13 + 1);
  let s = newMatch({ seed, flatMana }), dec = 0, same = 0;
  while (!s.result) {
    const a = bot(s, rng);
    if (name === 'expert' && legalActions(s).length > 1) { dec++; if (sameDecision(s, a, greedyBot(s))) same++; }
    s = act(s, a);
  }
  return { result: s.result, wall: Math.max(0, s.wall), round: s.round, cap: s.cap, dec, same };
}
// +1 when a ends better than b, -1 when worse, 0 when even
function better(a, b) {
  if (a.result !== b.result) return a.result === 'win' ? 1 : -1;
  if (a.result === 'win') return Math.sign(a.wall - b.wall);
  return Math.sign(a.round - b.round);
}

if (!isMainThread) {
  for (const j of workerData.jobs) parentPort.postMessage({ j, r: play(j.bot, j.seed, j.flat, workerData.budget) });
  parentPort.postMessage({ done: true });
} else {
  const jobs = [];
  for (const [v, flat] of Object.entries(VERSIONS)) for (let g = 0; g < N; g++) for (const bot of ['expert', 'greedy', 'random']) jobs.push({ v, flat, bot, seed: 30001 + g });
  const W = Math.max(1, os.cpus().length - 1), out = [], t0 = Date.now();
  // the slow Expert jobs spread evenly over the workers
  jobs.sort((a, b) => (a.bot === 'expert' ? 0 : 1) - (b.bot === 'expert' ? 0 : 1));
  await Promise.all([...Array(W).keys()].map(w => new Promise((res, rej) => {
    const wk = new Worker(new URL(import.meta.url), { workerData: { jobs: jobs.filter((_, k) => k % W === w), budget: BUDGET } });
    wk.on('message', m => { if (m.done) res(); else out.push(m); });
    wk.on('error', rej);
  })));
  // a run of some versions keeps the others' numbers from the report already written
  const old = existsSync(new URL('report.json', import.meta.url)) ? JSON.parse(readFileSync(new URL('report.json', import.meta.url), 'utf8')) : null;
  const rep = { game: '41 Wave defense', seeds: N, budget: BUDGET, versions: old && old.versions ? old.versions : {} };
  for (const v of Object.keys(VERSIONS)) {
    const by = (bot) => { const m = new Map(); for (const { j, r } of out) if (j.v === v && j.bot === bot) m.set(j.seed, r); return m; };
    const E = by('expert'), G = by('greedy'), R = by('random');
    const stat = (M) => { const rs = [...M.values()]; const wins = rs.filter(r => r.result === 'win'); return { games: rs.length, winRate: +(wins.length / rs.length).toFixed(3), avgWallOnWins: +(wins.reduce((n, r) => n + r.wall, 0) / Math.max(1, wins.length)).toFixed(2), avgRounds: +(rs.reduce((n, r) => n + r.round, 0) / rs.length).toFixed(1), capped: rs.filter(r => r.cap).length }; };
    const pairs = (O) => { let w = 0, l = 0, t = 0; for (const [seed, e] of E) { const b = better(e, O.get(seed)); if (b > 0) w++; else if (b < 0) l++; else t++; } return { expertBetter: w, expertWorse: l, even: t, decided: w + l, expertShareOfDecided: w + l ? +(w / (w + l)).toFixed(3) : null }; };
    let dec = 0, same = 0; for (const r of E.values()) { dec += r.dec; same += r.same; }
    const res = { expert: stat(E), greedy: stat(G), random: stat(R), vsGreedy: pairs(G), vsRandom: pairs(R), expertEqualsGreedy: +(same / dec).toFixed(3), expertDecisions: dec };
    res.turnCapRate = +([...E.values(), ...G.values(), ...R.values()].filter(r => r.cap).length / (3 * N)).toFixed(4);
    res.fails = [
      ...(['vsGreedy', 'vsRandom'].filter(k => res[k].expertShareOfDecided === null || res[k].expertShareOfDecided < 0.7).map(k => 'Expert ' + k + ' under 70% of decided pairs')),
      ...(res.greedy.winRate >= 0.95 && res.greedy.avgWallOnWins >= 19 ? ['Greedy wins nearly every game at nearly full Wall: a fixed rule solves it'] : []),
      ...(res.expertEqualsGreedy > 0.9 ? ['Expert equals Greedy over 90%'] : []),
      ...(res.turnCapRate > 0.02 ? ['round cap over 2%'] : []),
    ];
    res.seconds = Math.round((Date.now() - t0) / 1000); res.ranAt = new Date().toISOString();
    rep.versions[v] = res;
  }
  try { rep.sanity = (await import('./sanity.mjs')).results; } catch (e) { rep.sanity = 'sanity.mjs failed: ' + e.message; }
  writeFileSync(new URL('report.json', import.meta.url), JSON.stringify(rep, null, 2));
  console.log(JSON.stringify(rep, null, 2));
}
