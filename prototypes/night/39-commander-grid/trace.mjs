// node trace.mjs seed [expertSide] [opp]: one game, every action with the position it was taken in.
import { newMatch, _act, CARDS, rc, cmdOf, pieceById } from './src/engine.js';
import { makeRng, expertBot, greedyBot, racerBot, EXPERT } from './src/bot.js';
const ex = expertBot(EXPERT); const rng = makeRng(5);
const seed = +process.argv[2] || 501, es = process.argv[3] === undefined ? 0 : +process.argv[3], opp = process.argv[4] || 'greedy';
const O = { greedy: greedyBot, racer: racerBot, expert: ex }[opp];
let s = newMatch({ seed });
const pc = (u) => `${u.card === 'CMD' ? 'CMD' : CARDS[u.card].name}${u.atk}/${u.hp}@${rc(u.cell).join('')}`;
let k = 0;
while (s.winner === null && k < 900) {
  const who = s.toAct === es ? 'E' : 'G';
  const a = who === 'E' ? ex(s, rng) : O(s, rng);
  const P = s.p[s.toAct];
  const d = a.t === 'play' ? 'play ' + CARDS[a.card].name + (a.cell !== undefined ? '@' + rc(a.cell).join('') : '') + (a.tgt ? '->' + pc(pieceById(s, a.tgt)) : '') : a.t === 'end' ? 'END' : a.t + ' ' + pc(pieceById(s, a.from)) + '->' + (a.t === 'move' ? rc(a.to).join('') : pc(pieceById(s, a.to)));
  if (a.t === 'end' || who === 'E') console.log(`T${s.turnNo} ${who}${s.toAct} m${P.mana} hand[${P.hand.map(h => CARDS[h].name).join(',')}] mine[${s.pieces.filter(u => u.side === s.toAct).map(pc)}] his[${s.pieces.filter(u => u.side !== s.toAct).map(pc)}] => ${d}`);
  else console.log(`   ${who}: ${d}`);
  _act(s, a); k++;
}
console.log('winner', s.winner, 'first', s.first, 'expert side', es);
