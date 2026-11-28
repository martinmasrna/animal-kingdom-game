// node trace.mjs [seed]: one Expert mirror match, every shot with the position it was played in.
import { newMatch, act, CARDS } from './src/engine.js';
import { makeRng, expertBot, EXPERT } from './src/bot.js';
const ex = expertBot(EXPERT); const rng = makeRng(+process.argv[2] || 5);
let s = newMatch({ seed: +process.argv[2] || 501 });
let k = 0;
while (s.winner === null && k < 900) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  const a = ex(s, rng); const ev = [];
  const inc = s.rally.length ? CARDS[s.rally[s.rally.length - 1].card].pace : '-';
  const d = a.t === 'shot' ? `${CARDS[a.card].name}(p${CARDS[a.card].pace}/r${CARDS[a.card].reach}/c${CARDS[a.card].cost})` : 'LET GO';
  console.log(`G${s.gameNo} ${s.p[0].games}-${s.p[1].games} pts ${s.p[0].points}-${s.p[1].points} P${s.toAct}${s.rally.length ? '' : ' serves'} st ${P.stamina}/${O.stamina} incoming ${inc} hand[${P.hand.map(h => CARDS[h].pace + '/' + CARDS[h].reach).join(' ')}] => ${d}`);
  s = act(s, a, ev); k++;
  for (const e of ev) if (e.t === 'point') console.log(`   point P${e.side}`);
}
console.log('winner', s.winner, 'first', s.first);
