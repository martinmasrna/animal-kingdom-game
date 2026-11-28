// node ladder.mjs [games=200] [tops=16,8] [budgetMin=90] [low=1] [progress=<file>] [calib=1]
// Skill ladder for 41-wave-defense, one player against the game: Random < Greedy < Expert N <
// Expert 4N < Expert top, where N is the gate's Expert budget (play-outs per decision) and top is
// 16N unless its games would take more than budgetMin CPU-minutes (projected from the 4N games),
// then the next entry of tops. Every rung plays the same `games` seeded games (the rules as gated:
// flat mana 4); each adjacent pair is compared game by game as the gate does (a win beats a loss;
// two wins, more Wall; two losses, more rounds), the stronger rung's score being (better + even/2)
// / games with a 95% Wilson interval. low=1 adds Expert N/4, compared with Expert N. Writes
// ladder.json after every rung.
import { writeFileSync, readFileSync, existsSync, appendFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { newMatch, act } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot } from './src/bot.js';

const NAME = '41-wave-defense', KNOB = 'play-out budget per decision (expertBot budget)';
const N = JSON.parse(readFileSync(new URL('./report.json', import.meta.url), 'utf8')).budget;
const args = Object.fromEntries(process.argv.slice(2).map(a => { const i = a.indexOf('='); return i < 0 ? [a, '1'] : [a.slice(0, i), a.slice(i + 1)]; }));
const G = +(args.games || 200), TOPS = (args.tops || '16,8').split(',').map(Number);
const BUDGET = +(args.budgetMin || 90) * 60, LOW = !!args.low, PROG = args.progress || null;
const here = (f) => new URL('./' + f, import.meta.url);
const sha = (f) => createHash('sha1').update(readFileSync(here(f))).digest('hex').slice(0, 12);
const cpu = () => { const u = process.cpuUsage(); return (u.user + u.system) / 1e6; };
const name = (k) => k === 0 ? 'Random' : k === -1 ? 'Greedy' : k === 1 ? 'Expert N' : k < 1 ? `Expert N/${1 / k}` : `Expert ${k}N`;
const make = (k) => k === 0 ? randomBot : k === -1 ? (s) => greedyBot(s) : expertBot({ budget: k * N });
function wilson(p, n, z = 1.96) {
  const d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
const cache = new Map();
if (PROG && existsSync(PROG)) for (const l of readFileSync(PROG, 'utf8').split('\n').filter(Boolean)) { const j = JSON.parse(l); cache.set(j.rung + '|' + j.seed, j); }
function play(k, seed) {
  const bot = make(k), rng = makeRng(seed * 13 + 1);
  let s = newMatch({ seed });
  while (!s.result) s = act(s, bot(s, rng));
  return { result: s.result, wall: Math.max(0, s.wall), round: s.round, cap: !!s.cap };
}
function better(a, b) {
  if (a.result !== b.result) return a.result === 'win' ? 1 : -1;
  if (a.result === 'win') return Math.sign(a.wall - b.wall);
  return Math.sign(a.round - b.round);
}
const seeds = Array.from({ length: G }, (_, g) => 70001 + g);
function runRung(k, n = G) {
  const w0 = Date.now(), rs = [];
  let cpuS = 0;
  for (const seed of seeds.slice(0, n)) {
    let r = cache.get(name(k) + '|' + seed);
    if (!r) {
      const c0 = cpu();
      r = { rung: name(k), seed, ...play(k, seed) }; r.cpu = +(cpu() - c0).toFixed(3);
      if (PROG) appendFileSync(PROG, JSON.stringify(r) + '\n');
    }
    rs.push(r); cpuS += r.cpu;
    if (rs.length % 20 === 0 || rs.length === n) console.log(`${NAME} ${name(k)}: ${rs.length}/${n}, ${(cpuS / rs.length).toFixed(2)} cpu-s/game, ${Math.round((Date.now() - w0) / 1000)}s`);
  }
  const wins = rs.filter(r => r.result === 'win');
  return { rung: name(k), games: n, winRate: +(wins.length / n).toFixed(3), avgWallOnWins: +(wins.reduce((a, r) => a + r.wall, 0) / Math.max(1, wins.length)).toFixed(2), capped: rs.filter(r => r.cap).length, cpuSecPerGame: +(cpuS / n).toFixed(3), results: rs };
}
function compare(hi, lo) {
  let w = 0, l = 0, e = 0;
  hi.results.forEach((r, i) => { const b = better(r, lo.results[i]); if (b > 0) w++; else if (b < 0) l++; else e++; });
  const n = hi.results.length, score = (w + e / 2) / n, [a, b] = wilson(score, n);
  return { pair: hi.rung + ' > ' + lo.rung, stronger: hi.rung, weaker: lo.rung, games: n, better: w, even: e, worse: l, score: +score.toFixed(3), ci95: [+a.toFixed(3), +b.toFixed(3)], evenRate: +(e / n).toFixed(3) };
}

if (args.calib) {
  const r = runRung(1, 2);
  console.log(JSON.stringify({ prototype: NAME, N, cpuSecPerGame: r.cpuSecPerGame }));
} else {
  const files = { engine: sha('src/engine.js'), bot: sha('src/bot.js') }, t0 = Date.now();
  const out = { prototype: NAME, knob: KNOB, N, rules: 'as gated (newMatch default: flat mana 4)', gamesPerRung: G, comparison: 'paired on the same seeds: a win beats a loss; two wins, more Wall; two losses, more rounds', score: 'stronger rung: (better + even/2) / games, 95% Wilson interval', files, started: new Date().toISOString(), complete: false, rungs: [], pairs: [] };
  const R = [];
  const strip = (r) => { const { results, ...x } = r; return x; };
  const save = () => writeFileSync(here('ladder.json'), JSON.stringify(out, null, 2) + '\n');
  for (const k of [0, -1, 1, 4]) {
    R.push(runRung(k)); out.rungs.push(strip(R.at(-1)));
    if (R.length > 1) out.pairs.push(compare(R.at(-1), R.at(-2)));
    save();
  }
  // a game at kN costs about k/4 of a game at 4N
  let top = TOPS[TOPS.length - 1];
  for (const k of TOPS) if (R.at(-1).cpuSecPerGame * k / 4 * G <= BUDGET) { top = k; break; }
  out.top = top; out.topChoice = { tried: TOPS, budgetCpuSec: BUDGET, projectedCpuSec: Math.round(R.at(-1).cpuSecPerGame * top / 4 * G) };
  R.push(runRung(top)); out.rungs.push(strip(R.at(-1))); out.pairs.push(compare(R.at(-1), R.at(-2)));
  out.pairs.push(compare(R.at(-1), R[0]));
  if (LOW) { const q = runRung(0.25); out.rungs.push(strip(q)); out.pairs.push(compare(R[2], q)); }
  out.filesChangedDuringRun = sha('src/engine.js') !== files.engine || sha('src/bot.js') !== files.bot;
  out.complete = true; out.finished = new Date().toISOString(); out.wallSeconds = Math.round((Date.now() - t0) / 1000);
  save();
  console.log(JSON.stringify(out.pairs.map(p => [p.pair, p.score, p.ci95, p.evenRate])));
}
