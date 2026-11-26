// node selftest.mjs [n] [expertDepth] [rules as JSON]: the bot ladder for Toy 6, plus what the matches look like.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { cpus } from 'node:os';
import { newMatch, resolve, setRules, R } from './src/engine.js';
import { makeRng, randomBot, weakBot, mixBot } from './src/bot.js';

const bots = (ed) => ({ random: randomBot, weak: weakBot, d1: mixBot(1), d2: mixBot(2), d3: mixBot(3), normal: mixBot(1), expert: mixBot(ed) });

function match(B, a, b, seed) {
  const rng = makeRng(seed * 7919 + 1);
  let s = newMatch(); const who = [a, b]; const counts = {}; let maxMs = 0;
  while (s.winner === null) {
    const t0 = Date.now();
    const acts = [B[who[0]](s, 0, rng), B[who[1]](s, 1, rng)];
    maxMs = Math.max(maxMs, Date.now() - t0);
    for (const x of acts) counts[x] = (counts[x] || 0) + 1;
    s = resolve(s, acts);
  }
  return { winner: s.winner, rounds: s.round - 1, counts, maxMs };
}

if (!isMainThread) {
  const { a, b, seeds, ed, rules } = workerData;
  setRules(rules);
  const B = bots(ed);
  parentPort.postMessage(seeds.map(seed => { const swap = seed % 2 === 1; const r = match(B, swap ? b : a, swap ? a : b, seed); return { ...r, aSide: swap ? 1 : 0 }; }));
} else {
  const n = +(process.argv[2] || 200), ed = +(process.argv[3] || 3), rules = JSON.parse(process.argv[4] || '{}');
  setRules(rules);
  console.log('rules', JSON.stringify(R), 'expert depth', ed);
  const steps = process.env.STEPS ? JSON.parse(process.env.STEPS) : [['weak', 'random'], ['normal', 'weak'], ['expert', 'normal']];
  const Wn = Math.max(1, cpus().length - 1);
  for (const [a, b] of steps) {
    const chunks = Array.from({ length: Wn }, () => []);
    for (let i = 0; i < n; i++) chunks[i % Wn].push(i + 1);
    const res = (await Promise.all(chunks.filter(c => c.length).map(seeds => new Promise((ok, bad) => {
      const w = new Worker(new URL(import.meta.url), { workerData: { a, b, seeds, ed, rules } });
      w.on('message', ok); w.on('error', bad);
    })))).flat();
    const aw = res.filter(r => r.winner === r.aSide).length, bw = res.filter(r => r.winner === 1 - r.aSide).length, d = res.filter(r => r.winner === 'draw').length;
    const rounds = res.reduce((x, r) => x + r.rounds, 0) / n;
    const tot = {}; for (const r of res) for (const [k, v] of Object.entries(r.counts)) tot[k] = (tot[k] || 0) + v;
    const all = Object.values(tot).reduce((x, y) => x + y, 0);
    const mix = ['F', 'B', 'S', 'G', 'Z', 'L', 'T'].map(k => `${k} ${(100 * (tot[k] || 0) / all).toFixed(0)}%`).join(' ');
    console.log(`${a} v ${b}: ${a} ${(100 * aw / n).toFixed(0)}%  ${b} ${(100 * bw / n).toFixed(0)}%  draws ${d} | ${rounds.toFixed(1)} rounds | actions ${mix} | slowest ${Math.max(...res.map(r => r.maxMs))} ms`);
  }
}
