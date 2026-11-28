// node quick.mjs A B games [playouts depth]: a quick head-to-head, seats alternated.
import { newMatch, _act } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, playoutBot, expertBot, EXPERT } from './src/bot.js';
const [A, B, n = 20, po, dp] = process.argv.slice(2);
const ex = expertBot({ ...EXPERT, ...(po ? { playouts: +po } : {}), ...(dp ? { depth: +dp } : {}) });
const BOTS = { random: randomBot, greedy: greedyBot, racer: racerBot, playout: playoutBot, expert: ex };
let aw = 0, fw = 0, turns = 0, t0 = Date.now(), dec = 0;
for (let g = 0; g < +n; g++) {
  const rng = makeRng(g + 77); let s = newMatch({ seed: 500 + (g >> 1) }); const aSide = g % 2; const names = []; names[aSide] = A; names[1 - aSide] = B;
  let k = 0; while (s.winner === null && k < 6000) { const a = BOTS[names[s.toAct]](s, rng); if (names[s.toAct] === 'expert') dec++; _act(s, a); k++; }
  if (s.winner === aSide) aw++; else if (s.winner === 'draw') aw += .5; if (s.winner === s.first) fw++; turns += s.turnNo;
}
console.log(`${A} vs ${B}: ${aw}/${n} (${(aw / n * 100).toFixed(0)}%), first ${fw}/${n}, avg turns ${(turns / n).toFixed(1)}, ${((Date.now() - t0) / 1000).toFixed(1)}s, ${((Date.now() - t0) / Math.max(1, dec)).toFixed(1)} ms/decision`);
