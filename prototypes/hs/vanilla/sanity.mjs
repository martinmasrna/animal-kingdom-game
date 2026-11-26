// node sanity.mjs [topN] [playouts] [seed]: set positions a person never gets wrong (no face burn on turn 1, lethal, lethal through the Coin, a free trade), for Greedy and Expert.
// Set positions a person would never get wrong.
import { newMatch, act } from './src/engine.js';
import { greedyBot, rolloutBot, makeRng } from './src/bot.js';
const expert = rolloutBot(+process.argv[2] || 6, +process.argv[3] || 12, 8), rng = makeRng(+process.argv[4] || 1);
const base = () => { const s = newMatch({ seed: 7, first: 1 }); s.turn = 1; return s; };
const show = (acts) => acts.map(a => a.t === 'play' ? `play ${a.card}${a.target ? '→' + (a.target.side === 1 ? 'own' : 'his') + (a.target.i < 0 ? ' face' : ' m' + a.target.i) : ''}` : `attack m${a.from}→${a.to < 0 ? 'face' : 'm' + a.to}`).join(', ') || '(nothing)';
let bad = 0;
const check = (name, s, ok) => { for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) { const a = b(s, rng); const pass = ok(a); if (!pass) bad++; console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(a)}`); } };
// 1. turn 1, hand: Deal 2 and a 2/1, 1 mana, empty boards: should play the 2/1, never burn face
{ const s = base(); s.p[1].hand = ['S1', 'M1', 'M4']; s.p[1].mana = s.p[1].maxMana = 1; s.p[0].board = []; s.p[1].board = [];
  check('turn 1, Deal 2 or a 2/1', s, a => !a.some(x => x.card === 'S1')); }
// 2. lethal: he is at 7, I have a ready 3/4 and Deal 3 + Deal 2 with 3 mana, he has a 6/7 to tempt a trade
{ const s = base(); s.p[0].hp = 7; s.p[1].hand = ['S2', 'S1', 'M3']; s.p[1].mana = s.p[1].maxMana = 3;
  s.p[1].board = [{ uid: 900, card: 'M3', atk: 3, hp: 4, max: 4, ready: true }]; s.p[0].board = [{ uid: 901, card: 'M6', atk: 6, hp: 7, max: 7, ready: true }, { uid: 902, card: 'M1', atk: 2, hp: 1, max: 1, ready: true }];
  check('lethal 3 + 3 + 2 into 7', s, a => { let t = s; for (const x of a) { if (t.winner !== null) break; t = act(t, x); } return t.winner === 1; }); }
// 3. lethal with the Coin: he is at 6, I hold Deal 6 (4 mana) with 3 mana and the Coin
{ const s = base(); s.p[0].hp = 6; s.p[1].hand = ['S4', 'COIN']; s.p[1].mana = s.p[1].maxMana = 3; s.p[1].board = []; s.p[0].board = [];
  check('lethal through the Coin', s, a => { let t = s; for (const x of a) { if (t.winner !== null) break; t = act(t, x); } return t.winner === 1; }); }
// 4. a free kill: his 2/1 against my ready 3/4, no lethal: should not hit face and leave the 2/1? (a person trades here)
{ const s = base(); s.p[1].hand = []; s.p[1].mana = s.p[1].maxMana = 2; s.p[1].board = [{ uid: 903, card: 'M3', atk: 3, hp: 4, max: 4, ready: true }]; s.p[0].board = [{ uid: 904, card: 'M1', atk: 2, hp: 1, max: 1, ready: true }];
  check('free kill of a 2/1 with a 3/4', s, a => a.some(x => x.t === 'attack' && x.to === 0)); }
console.log(bad ? bad + ' failures' : 'all pass');
