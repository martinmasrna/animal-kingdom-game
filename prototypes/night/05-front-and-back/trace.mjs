// node trace.mjs [seed]: one Expert mirror game, every action with the position it was taken in.
import { newMatch, _act, CARDS } from './src/engine.js';
import { makeRng, expertBot, EXPERT } from './src/bot.js';
const ex = expertBot(EXPERT); const rng = makeRng(+process.argv[2] || 5);
let s = newMatch({ seed: +process.argv[2] || 501 });
const u = (x) => `${CARDS[x.card].name}${x.atk}/${x.hp}${x.ready ? '' : 'z'}`;
const name = (P, uid) => { const x = P.front.concat(P.back).find(v => v.uid === uid); return x ? u(x) : uid === 0 ? 'FACE' : '?'; };
let k = 0;
while (s.winner === null && k < 600) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  const a = ex(s, rng);
  const d = a.t === 'play' ? 'play ' + CARDS[a.card].name + (a.tgt ? ' -> ' + name(O, a.tgt) : '') : a.t === 'attack' ? 'attack ' + name(P, a.from) + ' -> ' + name(O, a.to) : 'END';
  console.log(`T${s.turnNo} P${s.toAct} life ${P.life}-${O.life} mana ${P.mana}/${P.maxMana} hand[${P.hand.map(h => CARDS[h].name).join(',')}] F[${P.front.map(u)}] B[${P.back.map(u)}] | his F[${O.front.map(u)}] B[${O.back.map(u)}]  => ${d}`);
  _act(s, a); k++;
}
console.log('winner', s.winner, 'first', s.first);
