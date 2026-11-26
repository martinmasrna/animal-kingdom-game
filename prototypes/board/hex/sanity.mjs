// node sanity.mjs [playouts] [seed]: set positions a person never gets wrong (close the winning triangle, no chip damage for nothing, break his winning triangle), for Hard and Expert.
import { newMatch, playAction, endTurn, GOAL } from './src/engine.js';
import { greedyTurn, rolloutBot, makeRng } from './src/bot.js';
const R = +process.argv[2] || 12, seed = +process.argv[3] || 1;
const expert = rolloutBot(6, R, 8), rng = makeRng(seed);
const base = () => { const s = newMatch({ seed: 7, first: 1 }); s.turn = 1; s.board = Array(14).fill(null); return s; };
const u = (side, hp) => ({ side, card: 'U' + hp, hp, max: hp });
let bad = 0;
const check = (name, s, ok) => { for (const [bn, b] of [['greedy', s => greedyTurn(s)], ['expert', expert]]) { const a = b(s, rng); const pass = ok(a, s); if (!pass) bad++; console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${a.map(m => m.card + '@' + m.tile).join(', ') || '(nothing)'}`); } };
const after = (s, a) => { let t = s; for (const m of a) t = playAction(t, m.card, m.tile); return t; };
// 1. win now: I am at 19 food, hold tiles 0 and 1, a unit on 3 completes region [0,1,3]
{ const s = base(); s.p[1].food = GOAL - 1; s.board[0] = u(1, 2); s.board[1] = u(1, 2); s.p[1].hand = ['U1', 'S1']; s.p[1].mana = s.p[1].maxMana = 2;
  check('close a triangle to win', s, (a) => { const t = endTurn(after(s, a)); return t.winner === 1; }); }
// 2. no point striking: his lone 5 in a corner region far from anything, I hold a Strike 1 and nothing else to do with it
{ const s = base(); s.board[13] = u(0, 5); s.p[1].hand = ['S1', 'S1']; s.p[1].mana = s.p[1].maxMana = 2;
  check('do not chip a 5 for nothing', s, (a) => !a.some(m => m.card === 'S1')); }
// 3. stop his win: he is at 19 food holding triangle [0,1,3] (all three his); I hold a Strike 2 and his units are 2s
{ const s = base(); s.p[0].food = GOAL - 1; s.board[0] = u(0, 2); s.board[1] = u(0, 2); s.board[3] = u(0, 2); s.p[1].hand = ['S2', 'U1']; s.p[1].mana = s.p[1].maxMana = 2;
  check('break the triangle he wins with', s, (a) => { const t = after(s, a); return [0, 1, 3].some(i => !t.board[i] || t.board[i].side !== 0); }); }
console.log(bad ? bad + ' failures' : 'all pass');
