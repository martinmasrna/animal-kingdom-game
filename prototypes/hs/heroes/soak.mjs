// node soak.mjs [games] [seconds]: random legal decks, random heroes, Greedy (and every tenth
// game Expert) on both sides; fails on any exception or a game that ends without a winner.
import { POOL, HERO_IDS, COPIES, DECK_SIZE } from './src/engine.js';
import { makeRng } from './src/bot.js';
import { runAll } from './sim.mjs';

const N = +(process.argv[2] || 3000), SECONDS = +(process.argv[3] || 600);
const rng = makeRng(77), ids = POOL.map(c => c.id);
const deck = () => { const d = []; while (d.length < DECK_SIZE) { const id = ids[Math.floor(rng() * ids.length)]; if (d.filter(x => x === id).length < COPIES) d.push(id); } return d; };
const games = [];
for (let g = 0; g < N; g++) {
  const b = g % 10 === 0 ? 'expert' : 'greedy';
  games.push({ seed: g + 1, first: g % 2, heroes: [HERO_IDS[Math.floor(rng() * 3)], HERO_IDS[Math.floor(rng() * 3)]], decks: [deck(), deck()], bots: [b, b] });
}
const timer = setTimeout(() => { console.log('time limit hit'); process.exit(2); }, SECONDS * 1000);
const res = await runAll(games);
clearTimeout(timer);
const draws = res.filter(r => r.winner === 'draw').length, none = res.filter(r => r.winner === null || r.winner === undefined).length;
const gain = res.filter(r => r.how === 'gain').length;
console.log(`${res.length} games, no exception; without a winner ${none}; draws (turn limit) ${draws} (${(100 * draws / res.length).toFixed(2)}%); by 50 ${(100 * gain / res.length).toFixed(0)}%; avg ${(res.reduce((n, r) => n + r.turns, 0) / res.length / 2).toFixed(1)} turns each; slowest turn ${Math.max(...res.map(r => r.maxMs))} ms`);
process.exit(none ? 1 : 0);
