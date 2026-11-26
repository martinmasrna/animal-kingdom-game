// node selftest.mjs [n]: the bot against greedy and random players and itself, both seats.
import { newMatch, commit, CARDS, setRules } from './src/engine.js';
import { makeRng, botChoose, greedyChoose, randomChoose } from './src/bot.js';

const N = +(process.argv[2] || 100);
if (process.argv[3]) setRules({ guardRate: +process.argv[3] });
const players = { bot: (s, i, r) => botChoose(s, i, r), greedy: (s, i) => greedyChoose(s, i), random: (s, i, r) => randomChoose(s, i, r) };

function match(a, b, seed) {
  let s = newMatch({ seed });
  const rng = makeRng(seed * 7 + 3), who = [a, b];
  let plays = 0, guards = 0, swords = 0, wasted = 0;
  while (s.winner === null) {
    const ch = [players[who[0]](s, 0, rng), players[who[1]](s, 1, rng)];
    for (const set of ch) for (const id of set) { plays++; if (CARDS[id].kind === 'Guard') guards++; if (CARDS[id].kind === 'Sword') swords++; }
    s = commit(s, ch);
  }
  return { winner: s.winner, rounds: s.round, plays, guards, swords };
}

function series(a, b) {
  let wa = 0, wb = 0, d = 0, rounds = 0, plays = 0, guards = 0, swords = 0;
  for (let i = 0; i < N; i++) {
    const swap = i % 2 === 1;
    const r = match(swap ? b : a, swap ? a : b, 1000 + i);
    const aSide = swap ? 1 : 0;
    if (r.winner === 'draw') d++; else if (r.winner === aSide) wa++; else wb++;
    rounds += r.rounds; plays += r.plays; guards += r.guards; swords += r.swords;
  }
  console.log(`${a} vs ${b}: ${a} ${(100 * wa / N).toFixed(0)}%, ${b} ${(100 * wb / N).toFixed(0)}%, draws ${d}; ${(rounds / N).toFixed(1)} rounds; ${(plays / rounds / 2).toFixed(1)} cards per player per round; guards ${(100 * guards / plays).toFixed(0)}% of plays, swords ${(100 * swords / plays).toFixed(0)}%`);
}
console.log(`guard rate ${process.argv[3] || 2}`);
if (!process.env.ONLY) { series('bot', 'random'); series('bot', 'greedy'); }
series('bot', 'bot');
