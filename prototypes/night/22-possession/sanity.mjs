// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert. The Expert
// plays a mixed strategy, so each position asks it 12 times and every answer must pass.
import { newMatch, options } from './src/engine.js';
import { greedyBot, matrixExpert, makeRng, EXPERT } from './src/bot.js';

const expert = matrixExpert(EXPERT), rng = makeRng(17);
const base = (play = 6) => { const s = newMatch({ seed: 61, first: 0 }); s.play = play; return s; };
let bad = 0;
const check = (name, side, mk, ok) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const picks = [];
    for (let k = 0; k < (bn === 'expert' ? 12 : 1); k++) picks.push(b(mk(), side, rng));
    const pass = picks.every(ok);
    if (!pass && bn === 'expert') bad++;
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${[...new Set(picks)].map(p => `${p}×${picks.filter(x => x === p).length}`).join(' ')}`);
  }
};
// 1. free goal: I have the ball in range (zone 7) and he has no stamina, so he cannot Block: Shoot
check('free goal', 0, () => { const s = base(); s.poss = 0; s.ball = 7; s.p[1].stamina = 0; s.p[0].hand = ['PASS', 'LONG', 'TACKLE', 'DRIBBLE']; return s; }, (o) => o === 'SHOOT');
// 2. don't waste: he has no stamina and can only Walk; Tackle (1) and Press (2) both stop it: never Press
check('no Press against a Walk-only attacker', 1, () => { const s = base(); s.poss = 0; s.ball = 4; s.p[0].stamina = 0; s.p[1].hand = ['TACKLE', 'PRESS', 'PASS', 'LONG']; return s; }, (o) => o !== 'PRESS');
// 3. last play, level, he has the ball in range: Block (a goal loses, anything else is a draw at best)
check('Block on the last play', 1, () => { const s = base(19); s.goals = [1, 1]; s.poss = 0; s.ball = 7; s.p[0].stamina = 3; s.p[1].stamina = 3; s.p[1].hand = ['TACKLE', 'PRESS', 'INTERCEPT', 'PASS']; return s; }, (o) => o === 'BLOCK');
console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
