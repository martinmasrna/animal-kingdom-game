// node selftest.mjs [n]: the bot against a greedy and a random player, and against itself, both seats.
import { newMatch, playAction, endTurn, CARDS, TILES, unitsOf } from './src/engine.js';
import { makeRng, botTurn, greedyTurn, randomTurn } from './src/bot.js';

const N = +(process.argv[2] || 200);
const players = { bot: (s) => botTurn(s), greedy: (s) => greedyTurn(s), random: (s, r) => randomTurn(s, r) };

function match(a, b, seed) {
  let s = newMatch({ seed });
  const rng = makeRng(seed * 7 + 3), who = [a, b];
  const first = s.first;
  let strikes = 0, units = 0, fullTurns = 0, turns = 0;
  while (s.winner === null) {
    for (const m of players[who[s.turn]](s, rng)) { s = playAction(s, m.card, m.tile); CARDS[m.card].kind === 'Unit' ? units++ : strikes++; }
    if (!s.board.includes(null)) fullTurns++;
    turns++;
    s = endTurn(s);
  }
  return { winner: s.winner, first, turns: s.turnNo, strikes, units, fullTurns, turnsSeen: turns };
}

export function series(a, b, n = N) {
  let wa = 0, wb = 0, d = 0, firstWins = 0, turns = 0, st = 0, un = 0, full = 0, seen = 0;
  for (let i = 0; i < n; i++) {
    const swap = i % 2 === 1;
    const r = match(swap ? b : a, swap ? a : b, 1000 + i);
    const aSide = swap ? 1 : 0;
    if (r.winner === 'draw') d++; else if (r.winner === aSide) wa++; else wb++;
    if (r.winner === r.first) firstWins++;
    turns += r.turns; st += r.strikes; un += r.units; full += r.fullTurns; seen += r.turnsSeen;
  }
  console.log(`${a} vs ${b}: ${a} ${(100 * wa / n).toFixed(1)}%, ${b} ${(100 * wb / n).toFixed(1)}%, draws ${d}; first player wins ${(100 * firstWins / n).toFixed(1)}%; avg ${(turns / n).toFixed(1)} turns; strikes ${(100 * st / (st + un)).toFixed(0)}% of cards; board full after ${(100 * full / seen).toFixed(0)}% of turns`);
}
if (import.meta.url === `file://${process.argv[1]}`) {
  series('bot', 'random');
  series('bot', 'greedy');
  series('greedy', 'greedy');
  series('bot', 'bot');
}
