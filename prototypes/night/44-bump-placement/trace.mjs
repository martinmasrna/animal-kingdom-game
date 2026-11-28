// node trace.mjs [seed]: one Expert mirror game, every action with the position it was taken in.
import { newMatch, act, CARDS, SPACES } from './src/engine.js';
import { makeRng, expertBot, EXPERT } from './src/bot.js';
const ex = expertBot(EXPERT); const rng = makeRng(+process.argv[2] || 5);
let s = newMatch({ seed: +process.argv[2] || 501 });
let k = 0;
while (s.winner === null && k < 900) {
  const P = s.p[s.toAct];
  const a = ex(s, rng); const ev = [];
  const sp = s.spaces.map(x => x ? CARDS[x.card].str + (x.side === s.toAct ? 'm' : 'h') : '.').join(' ');
  const d = a.t === 'place' ? `place ${CARDS[a.card].name}(${CARDS[a.card].str}) on ${SPACES[a.space].name}${a.tgt >= 0 ? ' shoving ' + SPACES[a.tgt].name : ''}` : a.t === 'discard' ? 'discard ' + CARDS[a.card].name : 'PASS';
  console.log(`R${s.round} P${s.toAct} pts ${P.points}-${s.p[1 - s.toAct].points} mana ${P.mana} hand[${P.hand.map(h => CARDS[h].str).join('')}] spaces[${sp}] => ${d}`);
  s = act(s, a, ev); k++;
}
console.log('winner', s.winner, 'first', s.first, s.p.map(p => p.points));
