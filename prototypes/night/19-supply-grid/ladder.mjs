// node ladder.mjs [games=200] [tops=16,8] [budgetMin=90] [vsRandom=0] [progress=<file>] [calib=1]
// Skill ladder for 19-supply-grid (// generated ladder): Random < Greedy < Expert N < Expert 4N < Expert top, where
// N is the gate's Expert budget and top is 16N unless the 16N-vs-4N games would take more than
// budgetMin CPU-minutes (projected from the 4N-vs-N games), then the next entry of tops.
// Each adjacent pair plays `games` games, seats alternated on the same deals; the stronger rung's
// score (wins + draws/2) gets a 95% Wilson interval. vsRandom=n adds top vs Random over n games.
// Writes ladder.json after every pair. calib=1 writes nothing: two Greedy-Random games and two
// Expert N mirror games, and their CPU cost.
import { writeFileSync, readFileSync, existsSync, appendFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const NAME = '19-supply-grid';
import { newMatch, _act } from './src/engine.js';
import { makeRng, randomBot, greedyBot, mcExpert, EXPERT as X } from './src/bot.js';
const KNOB = 'playouts per action (mcExpert)', N = X.playouts;
const RANDOM = () => randomBot, GREEDY = () => greedyBot;
const EXPERT = (k) => mcExpert({ ...X, playouts: k * N });
function playGame(bots, seed, rngSeed) {
  const rng = makeRng(rngSeed), s = newMatch({ seed });
  while (s.winner === null) _act(s, bots[s.turn](s, rng));
  return { winner: s.winner, capped: !!s.capped };
}

// ---------- the ladder (shared by every prototype) ----------
const args = Object.fromEntries(process.argv.slice(2).map(a => { const i = a.indexOf('='); return i < 0 ? [a, '1'] : [a.slice(0, i), a.slice(i + 1)]; }));
const G = +(args.games || 200), TOPS = (args.tops || '16,8').split(',').map(Number);
const BUDGET = +(args.budgetMin || 90) * 60, VSR = +(args.vsRandom || 0), PROG = args.progress || null;
const here = (f) => new URL('./' + f, import.meta.url);
const sha = (f) => createHash('sha1').update(readFileSync(here(f))).digest('hex').slice(0, 12);
const cpu = () => { const u = process.cpuUsage(); return (u.user + u.system) / 1e6; };
const rung = (k) => k === 0 ? { name: 'Random' } : k === -1 ? { name: 'Greedy' } : { name: k === 1 ? 'Expert N' : `Expert ${k}N`, k };
const make = (r) => r.name === 'Random' ? RANDOM() : r.name === 'Greedy' ? GREEDY() : EXPERT(r.k);
function wilson(p, n, z = 1.96) {
  const d = 1 + z * z / n, c = (p + z * z / (2 * n)) / d, h = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d;
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
const cache = new Map();
if (PROG && existsSync(PROG)) for (const l of readFileSync(PROG, 'utf8').split('\n').filter(Boolean)) { const j = JSON.parse(l); cache.set(j.pair + '|' + j.g, j); }

// Game g of a pair: deal base + (g >> 1), so every deal is played twice with the seats swapped.
function runPair(hi, lo, games, base) {
  const label = hi.name + ' > ' + lo.name, w0 = Date.now();
  let w = 0, d = 0, l = 0, capped = 0, cpuS = 0, len = 0;
  for (let g = 0; g < games; g++) {
    let r = cache.get(label + '|' + g);
    if (!r) {
      const hiSeat = g % 2, bots = [];
      bots[hiSeat] = make(hi); bots[1 - hiSeat] = make(lo);
      const c0 = cpu(), res = playGame(bots, base + (g >> 1) * 2 + 1, base * 7919 + g * 31 + 1);
      r = { pair: label, g, hiSeat, winner: res.winner, capped: !!res.capped, cpu: +(cpu() - c0).toFixed(3) };
      if (PROG) appendFileSync(PROG, JSON.stringify(r) + '\n');
    }
    cpuS += r.cpu; if (r.capped) capped++;
    if (r.winner === r.hiSeat) w++; else if (r.winner === 1 - r.hiSeat) l++; else d++;
    if ((g + 1) % 20 === 0 || g + 1 === games) console.log(`${NAME} ${label}: ${g + 1}/${games}, score ${((w + d / 2) / (g + 1)).toFixed(3)}, ${(cpuS / (g + 1)).toFixed(2)} cpu-s/game, ${Math.round((Date.now() - w0) / 1000)}s`);
  }
  const score = (w + d / 2) / games, [a, b] = wilson(score, games);
  return { pair: label, stronger: hi.name, weaker: lo.name, games, wins: w, draws: d, losses: l, score: +score.toFixed(3), ci95: [+a.toFixed(3), +b.toFixed(3)], drawRate: +(d / games).toFixed(3), capped, cpuSecPerGame: +(cpuS / games).toFixed(3) };
}
// the gate's own Expert mirror (N against N), for its draw rate
function gateMirror() {
  try {
    const r = JSON.parse(readFileSync(here('report.json'), 'utf8')), P = r.pairings || r.matchups;
    const m = Array.isArray(P) ? P.find(x => x.a === 'expert' && x.b === 'expert') : P && P['expert-expert'];
    if (!m) return null;
    const n = m.n ?? m.games; return { games: n, draws: m.draws ?? 0, drawRate: +((m.draws ?? 0) / n).toFixed(3) };
  } catch (e) { return null; }
}

if (args.calib) {
  const t = runPair(rung(-1), rung(0), 2, 98000), r = runPair(rung(1), rung(1), 2, 99000);
  console.log(JSON.stringify({ prototype: NAME, N, trivialOk: t.games === 2, cpuSecPerMirrorGame: r.cpuSecPerGame }));
} else {
  const OUT = here('ladder.json'), files = { engine: sha('src/engine.js'), bot: sha('src/bot.js') };
  const out = { prototype: NAME, knob: KNOB, N, gamesPerPair: G, seatsAlternated: 'each deal played twice, seats swapped', score: 'stronger rung: (wins + draws/2) / games, 95% Wilson interval', files, started: new Date().toISOString(), complete: false, pairs: [] };
  const save = () => writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
  const t0 = Date.now();
  out.pairs.push(runPair(rung(-1), rung(0), G, 60000)); save();
  out.pairs.push(runPair(rung(1), rung(-1), G, 61000)); save();
  const p41 = runPair(rung(4), rung(1), G, 62000); out.pairs.push(p41); save();
  // the top rung: the first of TOPS whose games fit the budget; a game of kN against 4N costs
  // about (4 + k) / (4 + 1) times a game of 4N against N
  let top = TOPS[TOPS.length - 1];
  for (const k of TOPS) if (p41.cpuSecPerGame * (4 + k) / 5 * G <= BUDGET) { top = k; break; }
  out.top = top;
  out.topChoice = { tried: TOPS, budgetCpuSec: BUDGET, projectedCpuSec: Math.round(p41.cpuSecPerGame * (4 + top) / 5 * G) };
  out.pairs.push(runPair(rung(top), rung(4), G, 63000)); save();
  if (VSR) { out.pairs.push(runPair(rung(top), rung(0), VSR, 64000)); save(); }
  out.gateMirror = gateMirror();
  out.filesChangedDuringRun = sha('src/engine.js') !== files.engine || sha('src/bot.js') !== files.bot;
  out.complete = true; out.finished = new Date().toISOString(); out.wallSeconds = Math.round((Date.now() - t0) / 1000);
  save();
  console.log(JSON.stringify(out.pairs.map(p => [p.pair, p.score, p.ci95, p.drawRate])));
}
