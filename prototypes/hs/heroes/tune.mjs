// node tune.mjs A B [deals]: bot A against bot B (names as in sim.mjs, e.g. expert, greedy,
// x:8:16:8:200), every hero pairing with the default decks, both seats on the same deals.
import { DEFAULT_DECKS as D, HERO_IDS } from './src/engine.js';
import { runAll, pairingGames, summarize } from './sim.mjs';
const [A, B] = [process.argv[2] || 'expert', process.argv[3] || 'greedy'], N = +(process.argv[4] || 40);
let g = [];
for (const h of HERO_IDS) for (const o of HERO_IDS) for (const x of pairingGames(h, D[h], o, D[o], N, 7000)) { x.bots = x.aSide === 0 ? [A, B] : [B, A]; g.push(x); }
const r = summarize(g, await runAll(g));
console.log(`${A} vs ${B}: ${(100 * r.a).toFixed(1)}% of ${r.n} games, slowest turn ${r.maxMs} ms`);
