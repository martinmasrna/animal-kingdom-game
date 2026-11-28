// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (a whole turn each).
import { newMatch, act } from './src/engine.js';
import { greedyBot, mcExpert, makeRng, EXPERT } from './src/bot.js';

const expert = mcExpert(EXPERT), rng = makeRng(13);
let uid = 9000;
const U = (card, power) => ({ uid: uid++, card, power });
const site = (thr, win, run, mine, his) => ({ thr, win, run, uid: uid++, u: [mine, his] });
// a mid-game position: seat 0 to move, 5 mana, empty hands, three quiet sites
const base = () => {
  const s = newMatch({ seed: 41, first: 0 }); s.turnNo = 9;
  for (const p of s.p) { p.hand = []; p.maxMana = p.mana = 5; }
  s.sites = [site(13, 5, 3, [], []), site(12, 5, 2, [U('PAWN', 1)], []), site(14, 6, 3, [], [U('PAWN', 1)])];
  return s;
};
const turn = (bot, s) => { const acts = []; let t = s; for (let k = 0; k < 40 && t.winner === null; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); if (a.t === 'end') break; } return { acts, t }; };
const show = (acts) => acts.map(a => a.t === 'unit' ? `${a.card}@${a.slot}` : a.t === 'strike' || a.t === 'boost' ? `${a.t} ${a.slot}:${a.i}` : a.t === 'move' ? `move ${a.from}→${a.slot}` : a.t).join(', ');
let bad = 0;
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const s = mk(), r = turn(b, s), pass = ok(r, s);
    if (!pass && bn === 'expert') bad++;
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(r.acts)}`);
  }
};
// 1. lethal: at 12 points I lead a Winner-3 site 6 to 3 at threshold 10: a Pawn breaks it and wins
check('a Pawn breaks the site and wins', () => { const s = base(); s.p[0].points = 12; s.p[0].hand = ['PAWN', 'SQUAD']; s.sites[0] = site(10, 3, 1, [U('HEAVY', 6)], [U('SQUAD', 3)]); return s; },
  (r) => r.t.winner === 0);
// 2. don't break a site you are losing: he is at 12 and leads a Winner-3 site 7 to 2 at 9 of 10;
//    my Pawn there would break it and hand him the game
check('never break the site he wins', () => { const s = base(); s.p[1].points = 12; s.p[0].hand = ['PAWN']; s.sites[0] = site(10, 3, 1, [U('SQUAD', 2)], [U('BIG', 7)]); return s; },
  (r) => r.t.winner !== 1);
// 2b. the same mid-game, where it does not end the game: his Heavy (6) alone on a site at
//     threshold 10; my Force (4) there would break it for him; anywhere else it costs nothing
check('never break a site for him mid-game', () => { const s = base(); s.p[0].hand = ['FORCE']; s.sites[0] = site(10, 4, 1, [], [U('HEAVY', 6)]); return s; },
  (r) => !r.acts.some(a => a.t === 'unit' && a.slot === 0));
// 3. free Strike: his only unit on a site I lead is a Squad (3); I hold Strike and nothing else
check('Strike his only unit at my site', () => { const s = base(); s.p[0].hand = ['STRIKE']; s.p[0].mana = 2; s.sites[1] = site(12, 5, 2, [U('HEAVY', 6)], [U('SQUAD', 3)]); return s; },
  (r) => r.t.sites[1] && r.t.sites[1].u[1].length === 0);
console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
