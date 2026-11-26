// node ladder.mjs <game> [n] [expertMs] [normalDepth]
// Runs the three ladder steps (weak v random, normal v weak, expert v normal), n matches
// each with sides swapped, spread over worker threads. Prints win rates and timings.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { cpus } from 'node:os';
import { randomBot, greedyBot, depthBot, timedBot, pimcBot, pimcTimed, makeRng } from './bots.js';

const MAX_PLIES = 3000;

async function loadGame(name) {
  const { variants } = await import('./games/variants.js');
  if (variants[name]) return variants[name];
  return (await import(`./games/${name}.js`)).default;
}

function makeBot(spec, g) {
  if (g && g.bots && g.bots[spec]) return g.bots[spec];
  if (spec === 'random') return randomBot;
  if (spec === 'weak') return greedyBot;
  let m;
  if ((m = spec.match(/^p(\d+)x(\d+)$/))) return pimcBot(+m[1], +m[2]);
  if ((m = spec.match(/^pt(\d+)k(\d+)$/))) return pimcTimed(+m[1], +m[2]);
  if (spec.startsWith('d')) return depthBot(+spec.slice(1));
  if (spec.startsWith('t')) return timedBot(+spec.slice(1));
  throw new Error('bot ' + spec);
}

function playMatch(g, bots, seed) {
  const rng = makeRng(seed);
  let s = g.init(rng), plies = 0, maxMs = 0;
  while (g.winner(s) === null && plies < MAX_PLIES) {
    const t0 = Date.now();
    const m = bots[g.toMove(s)](g, s, rng);
    maxMs = Math.max(maxMs, Date.now() - t0);
    s = g.play(s, m); plies++;
  }
  const w = g.winner(s);
  return { winner: w === null ? 'draw' : w, plies, maxMs };
}

if (!isMainThread) {
  const { game, a, b, seeds } = workerData;
  const g = await loadGame(game);
  const A = makeBot(a, g), B = makeBot(b, g);
  const out = [];
  for (const seed of seeds) {
    const swap = seed % 2 === 1;
    const r = playMatch(g, swap ? [B, A] : [A, B], seed);
    const aSide = swap ? 1 : 0;
    out.push({ aWon: r.winner === aSide, bWon: r.winner === 1 - aSide, draw: r.winner === 'draw', plies: r.plies, maxMs: r.maxMs, firstWon: r.winner === 0 });
  }
  parentPort.postMessage(out);
} else {
  const [game, nArg, expertMs, normalDepth] = process.argv.slice(2);
  const n = +(nArg || 100), T = expertMs || '300', ND = normalDepth || '3';
  const steps = process.env.STEPS ? JSON.parse(process.env.STEPS) : [['weak', 'random'], ['d' + ND, 'weak'], ['t' + T, 'd' + ND]];
  const W = Math.max(1, cpus().length - 1);
  for (const [a, b] of steps) {
    const t0 = Date.now();
    const chunks = Array.from({ length: W }, () => []);
    for (let i = 0; i < n; i++) chunks[i % W].push(i + 1);
    const res = (await Promise.all(chunks.filter(c => c.length).map(seeds => new Promise((ok, bad) => {
      const w = new Worker(new URL(import.meta.url), { workerData: { game, a, b, seeds } });
      w.on('message', ok); w.on('error', bad);
    })))).flat();
    const aw = res.filter(r => r.aWon).length, bw = res.filter(r => r.bWon).length, d = res.filter(r => r.draw).length;
    const plies = res.reduce((x, r) => x + r.plies, 0) / res.length;
    const maxMs = Math.max(...res.map(r => r.maxMs));
    const first = res.filter(r => r.firstWon).length;
    console.log(`${game}: ${a} v ${b}: ${a} ${(100 * aw / n).toFixed(0)}%  ${b} ${(100 * bw / n).toFixed(0)}%  draws ${d}  | ${plies.toFixed(0)} plies, first mover wins ${(100 * first / n).toFixed(0)}%, slowest move ${maxMs} ms, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
}
