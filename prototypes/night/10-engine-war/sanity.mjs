// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (a whole turn each).
import { newMatch, act } from './src/engine.js';
import { greedyBot, mcExpert, makeRng, EXPERT } from './src/bot.js';

const expert = mcExpert(EXPERT), rng = makeRng(9);
let uid = 7000;
const post = (card, hp) => ({ uid: uid++, card, hp });
// my buy phase on turn 9 (hand already played), seat 0, with the coin and damage given
const base = (coin, dmg) => { const s = newMatch({ seed: 31, first: 0 }); s.turn = 0; s.turnNo = 9; const P = s.p[0]; P.discard.push(...P.hand); P.hand = []; P.trash = 0; P.coin = coin; P.dmg = dmg; return s; };
const turn = (bot, s) => { const acts = []; let t = s; for (let k = 0; k < 40 && t.winner === null; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); if (a.t === 'end') break; } return { acts, t }; };
const show = (s, acts) => acts.map(a => a.t === 'buy' ? `buy ${s.row[a.i]}` : a.t === 'shoot' ? `shoot ${a.i}` : a.t).join(', ');
let bad = 0;
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const s = mk(), r = turn(b, s), pass = ok(r, s);
    if (!pass && bn === 'expert') bad++;
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(s, r.acts)}`);
  }
};
// 1. denial: he is at 17 with a Big Post (yield 3) that wins him the game next turn; I have 7 damage
check('shoot the Post that would win', () => { const s = base(2, 7); s.p[1].points = 17; s.p[1].posts = [post('BPOST', 7)]; return s; },
  (r) => r.t.p[1].posts.length === 0);
// 2. don't waste damage: 6 damage against two Health-5 Posts: destroy one
check('6 damage, two Health-5 Posts', () => { const s = base(0, 6); s.p[1].posts = [post('POST', 5), post('POST', 5)]; return s; },
  (r) => r.t.p[1].posts.length === 1);
// 3. don't waste coin: 8 coin and a Big Post in the row: buy something
check('8 coin and a Big Post in the row', () => { const s = base(8, 0); s.row[2] = 'BPOST'; return s; },
  (r) => r.acts.some(a => a.t === 'buy'));
console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
