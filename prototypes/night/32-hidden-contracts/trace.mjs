// node trace.mjs [seed]: one Expert mirror game, every action with the position it was taken in.
import { newMatch, act, CARDS, CONTRACTS } from './src/engine.js';
import { makeRng, expertBot, EXPERT } from './src/bot.js';
const ex = expertBot(EXPERT); const rng = makeRng(+process.argv[2] || 5);
let s = newMatch({ seed: +process.argv[2] || 501 });
const u = (x) => `${CARDS[x.card].name}${x.atk}/${x.hp}${x.ready ? '' : 'z'}`;
let k = 0;
while (s.winner === null && k < 900) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  const a = ex(s, rng); const ev = [];
  const d = a.t === 'play' ? 'play ' + CARDS[a.card].name + (a.tgt ? ' -> ' + u(O.board.find(x => x.uid === a.tgt)) : '') : a.t === 'attack' ? 'attack ' + u(P.board.find(x => x.uid === a.from)) + ' -> ' + u(O.board.find(x => x.uid === a.to)) : a.t === 'swap' ? 'swap ' + a.c : 'END';
  console.log(`T${s.turnNo} P${s.toAct} pts ${P.points}-${O.points} m${P.mana}/${P.maxMana} holds[${P.contracts}] hand[${P.hand.map(h => CARDS[h].name)}] mine[${P.board.map(u)}] his[${O.board.map(u)}] => ${d}`);
  s = act(s, a, ev);
  for (const e of ev) if (e.t === 'score') console.log(`   * P${e.side} scores ${e.c} +${e.pts} -> ${e.points}`);
  k++;
}
console.log('winner', s.winner, 'first', s.first);
