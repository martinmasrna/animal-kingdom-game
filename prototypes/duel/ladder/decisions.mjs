// node decisions.mjs <game> [n]: how many of the expert's turns were real choices.
// forced = only one kind of card in hand; obvious = the weak (1-ply) bot would have played the same.
// Also prints one expert-vs-expert match move by move.
import { variants } from './games/variants.js';
import { makeRng, greedyBot, pimcTimed } from './bots.js';
const g = variants[process.argv[2]], n = +(process.argv[3] || 20), quiet = process.env.QUIET;
const E = pimcTimed(200, 16);
let turns = 0, forced = 0, same = 0;
for (let i = 0; i < n; i++) {
  const rng = makeRng(100 + i); let s = g.init(rng); const log = [];
  while (g.winner(s) === null && s.ply < 200) {
    const ms = g.moves(s); const m = E(g, s, rng);
    turns++; if (ms.length === 1) forced++; else if (greedyBot(g, s, makeRng(7)) === m) same++;
    if (i === 0 && !quiet) log.push(`${s.turn ? 'B' : 'A'} [${s.hand[s.turn].join('')}] ${m}  hp ${s.hp.join('/')}`);
    s = g.play(s, m);
  }
  if (i === 0 && !quiet) console.log(log.join('\n'));
}
console.log(`${process.argv[2]}: turns ${turns}: forced ${(100 * forced / turns).toFixed(0)}%, a choice the 1-ply bot also makes ${(100 * same / turns).toFixed(0)}%, choice where looking ahead changes the move ${(100 * (turns - forced - same) / turns).toFixed(0)}%`);
