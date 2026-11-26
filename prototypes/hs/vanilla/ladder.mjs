// node ladder.mjs [games]: the 70% test on the Vanilla HS. Every bot against every simpler one,
// both seats on the same deals; the chain is read off the table.
import { newMatch, act, endTurn } from './src/engine.js';
import { makeRng, randomBot, spendBot, faceBot, greedyBot, rolloutBot } from './src/bot.js';

const N = +(process.argv[2] || 400);
export const BOTS = { random: randomBot, spend: spendBot, face: faceBot, greedy: greedyBot, expert: rolloutBot(6, 12, 8) };

export function rate(a, b, n = N, seed0 = 5000) {
  let wa = 0, draws = 0, turns = 0;
  for (let g = 0; g < n; g++) {
    const rng = makeRng(seed0 * 7 + g);
    let s = newMatch({ seed: seed0 + (g >> 1) });
    const aSide = g % 2;
    while (s.winner === null) {
      for (const x of (s.turn === aSide ? a : b)(s, rng)) { s = act(s, x); if (s.winner !== null) break; }
      if (s.winner !== null) break;
      s = endTurn(s);
    }
    turns += s.turnNo;
    if (s.winner === 'draw') draws++; else if (s.winner === aSide) wa++;
  }
  return { r: (wa + draws / 2) / n, turns: turns / n };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const order = (process.argv[3] || Object.keys(BOTS).join(',')).split(',');
  for (let i = 1; i < order.length; i++) {
    const row = [];
    for (let j = 0; j < i; j++) { const { r, turns } = rate(BOTS[order[i]], BOTS[order[j]]); row.push(`${order[j]} ${(100 * r).toFixed(0)}% (${(turns / 2).toFixed(1)} turns each)`); }
    console.log(`${order[i].padEnd(7)} vs  ${row.join('  ')}`);
  }
}
