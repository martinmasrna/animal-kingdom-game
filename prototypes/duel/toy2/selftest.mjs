// node selftest.mjs [n] [guardRate] [gain] [draw]: the bot against greedy and random players and itself, both seats.
import { newMatch, act, CARDS, setRules } from './src/engine.js';
import { makeRng, botAct, greedyAct, randomAct } from './src/bot.js';

const N = +(process.argv[2] || 200);
setRules({ guardRate: process.argv[3] ? +process.argv[3] : null, gain: process.argv[4] ? +process.argv[4] : null, draw: process.argv[5] ? +process.argv[5] : null, carry: process.env.CARRY ? process.env.CARRY === '1' : null, strikesFirst: process.env.SF ? process.env.SF === '1' : null });
const players = { bot: (s, r) => botAct(s, r), greedy: (s) => greedyAct(s), random: (s, r) => randomAct(s, r) };

function match(a, b, seed) {
  let s = newMatch({ seed });
  const rng = makeRng(seed * 7 + 3), who = [a, b];
  const firstStarter = s.starter;
  let plays = 0, guards = 0, swords = 0, actions = 0, rounds;
  while (s.winner === null) {
    const id = players[who[s.toAct]](s, rng);
    if (id) { plays++; if (CARDS[id].kind === 'Guard') guards++; if (CARDS[id].kind === 'Sword') swords++; }
    actions++;
    s = act(s, id);
  }
  return { winner: s.winner, firstStarter, rounds: s.round, plays, guards, swords };
}

function series(a, b) {
  let wa = 0, wb = 0, d = 0, st = 0, rounds = 0, plays = 0, guards = 0, swords = 0;
  for (let i = 0; i < N; i++) {
    const swap = i % 2 === 1;
    const r = match(swap ? b : a, swap ? a : b, 1000 + i);
    const aSide = swap ? 1 : 0;
    if (r.winner === 'draw') d++; else if (r.winner === aSide) wa++; else wb++;
    if (r.winner === r.firstStarter) st++;
    rounds += r.rounds; plays += r.plays; guards += r.guards; swords += r.swords;
  }
  console.log(`${a} vs ${b}: ${a} ${(100 * wa / N).toFixed(0)}%, ${b} ${(100 * wb / N).toFixed(0)}%, draws ${d}; first-round starter wins ${(100 * st / N).toFixed(0)}%; ${(rounds / N).toFixed(1)} rounds; guards ${(100 * guards / plays).toFixed(0)}% of plays, swords ${(100 * swords / plays).toFixed(0)}%`);
}
console.log(`guard rate ${process.argv[3] || 2}, gain ${process.argv[4] || 6}, draw ${process.argv[5] || 3}`);
if (!process.env.ONLY) { series('bot', 'random'); series('bot', 'greedy'); }
series('bot', 'bot');
