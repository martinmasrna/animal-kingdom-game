// node selftest.mjs [n]: the bot against a greedy and a random player, and against itself, both seats.
import { newMatch, playAction, endTurn, CARDS } from './src/engine.js';
import { makeRng, botTurn, greedyTurn, randomTurn } from './src/bot.js';

const N = +(process.argv[2] || 300);
const players = { bot: (s, r) => botTurn(s, r), greedy: (s) => greedyTurn(s), random: (s, r) => randomTurn(s, r) };

function match(a, b, seed) {
  let s = newMatch({ seed });
  const rng = makeRng(seed * 7 + 3), who = [a, b];
  const firstSide = s.first;
  let guards = 0, strikes = 0, unspent = 0;
  while (s.winner === null) {
    const cards = players[who[s.turn]](s, rng);
    for (const id of cards) { s = playAction(s, id); CARDS[id].kind === 'Guard' ? guards++ : strikes++; if (s.winner !== null) break; }
    if (s.winner !== null) break;
    unspent += s.p[s.turn].mana;
    s = endTurn(s);
  }
  return { winner: s.winner, first: firstSide, turns: s.turnNo, guards, strikes, unspent };
}

function series(a, b) {
  let wa = 0, wb = 0, d = 0, firstWins = 0, turns = 0, g = 0, st = 0;
  for (let i = 0; i < N; i++) {
    const swap = i % 2 === 1;
    const r = match(swap ? b : a, swap ? a : b, 1000 + i);
    const aSide = swap ? 1 : 0;
    if (r.winner === 'draw') d++; else if (r.winner === aSide) wa++; else wb++;
    if (r.winner === r.first) firstWins++;
    turns += r.turns; g += r.guards; st += r.strikes;
  }
  console.log(`${a} vs ${b}: ${a} ${(100 * wa / N).toFixed(1)}%, ${b} ${(100 * wb / N).toFixed(1)}%, draws ${d}; first player wins ${(100 * firstWins / N).toFixed(1)}%; avg ${(turns / N).toFixed(1)} turns; guards ${(100 * g / (g + st)).toFixed(0)}% of cards played`);
}
series('bot', 'random');
series('bot', 'greedy');
series('greedy', 'greedy');
series('bot', 'bot');
