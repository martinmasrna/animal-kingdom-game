// node stats.mjs [deals] [bot]: the three hero pairings with the default decks, each deal
// played from both seats. Prints win rate, game length, how games end, first-player win rate,
// the cards each pair of decks share, and Expert against Greedy as a strength check.
import { DEFAULT_DECKS, HERO_IDS, HEROES } from './src/engine.js';
import { runAll, pairingGames, summarize } from './sim.mjs';

const N = +(process.argv[2] || 200), BOT = process.argv[3] || 'expert';
const pct = (x) => (100 * x).toFixed(0) + '%';
const shared = (a, b) => { const n = {}; for (const id of a) n[id] = (n[id] || 0) + 1; let k = 0; for (const id of b) if (n[id] > 0) { n[id]--; k++; } return k; };
const D = DEFAULT_DECKS;
const pairs = [['P', 'A'], ['P', 'M'], ['A', 'M']];
let all = [], allRes = [];
for (const [a, b] of pairs) {
  const games = pairingGames(a, D[a], b, D[b], N, 1000, BOT);
  const res = await runAll(games);
  all = all.concat(games); allRes = allRes.concat(res);
  const r = summarize(games, res);
  console.log(`${HEROES[a].name} vs ${HEROES[b].name}: ${pct(r.a)}-${pct(1 - r.a)}  ${r.turns.toFixed(1)} turns each  by 50 ${pct(r.gain)}  by 0 ${pct(r.kill)}  draws ${pct(r.draws)}  first player ${pct(r.first)}  shared cards ${shared(D[a], D[b])}/20  slowest turn ${r.maxMs} ms  (${r.n} games)`);
}
const t = summarize(all, allRes);
// what each hero does with its tools, over all its games
for (const h of HERO_IDS) {
  const xs = allRes.flatMap(r => r.sides.filter(x => x.hero === h)), wins = allRes.flatMap(r => r.sides.map((x, k) => x.hero === h && r.winner === k));
  const fire = xs.flatMap(x => x.fire);
  const avg = (f) => (xs.reduce((n, x) => n + f(x), 0) / xs.length).toFixed(2);
  console.log(`${HEROES[h].name}: hero card played in ${pct(xs.filter(x => x.heroCard).length / xs.length)} of games, power ${avg(x => x.uses)} uses a game, reached fatigue in ${pct(xs.filter(x => x.fatigue > 0).length / xs.length)}` + (fire.length ? `, Fireballs cast ${(fire.length / xs.length).toFixed(2)} a game (damage ${[1, 3, 6, 10].map(d => d + ':' + fire.filter(x => x === d).length).join(' ')})` : ''));
}
console.log(`all: ${t.turns.toFixed(1)} turns each, by 50 ${pct(t.gain)}, by 0 ${pct(t.kill)}, draws ${pct(t.draws)}, first player ${pct(t.first)}`);
if (BOT === 'expert') {
  // strength check: Expert against Greedy, every hero, mirror decks per pairing
  let g = [], meta = [];
  for (const h of HERO_IDS) for (const o of HERO_IDS) { const gs = pairingGames(h, D[h], o, D[o], Math.ceil(N / 4), 9000); for (const x of gs) { x.bots = x.aSide === 0 ? ['expert', 'greedy'] : ['greedy', 'expert']; } g = g.concat(gs); }
  const r = summarize(g, await runAll(g));
  console.log(`Expert vs Greedy: ${pct(r.a)} (${r.n} games)`);
}
