// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (a whole turn each).
import { newMatch, act, count } from './src/engine.js';
import { greedyBot, mcExpert, makeRng, EXPERT } from './src/bot.js';

const expert = mcExpert(EXPERT), rng = makeRng(5);
let uid = 5000;
const P = (side, card, power, extra = {}) => ({ uid: uid++, side, card, power, struck: false, ...extra });
// a mid-game position: seat 0 to move (Base at cell 2, enemy Base at cell 22), 5 mana, empty hands
const base = () => { const s = newMatch({ seed: 21, first: 0 }); s.turnNo = 11; for (const p of s.p) { p.hand = []; p.maxMana = p.mana = 5; } return s; };
const turn = (bot, s) => { const acts = []; let t = s; for (let k = 0; k < 40 && t.winner === null; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); if (a.t === 'end') break; } return { acts, t }; };
const show = (acts) => acts.map(a => a.t === 'place' ? `place ${a.card}@${a.cell}` : a.t === 'strike' ? `strike ${a.from}→${a.to}` : a.t === 'cut' ? `cut ${a.to}` : a.t).join(', ');
let bad = 0;
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const s = mk(), r = turn(b, s), pass = ok(r, s);
    if (!pass && bn === 'expert') bad++;
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(r.acts)}`);
  }
};
// 1. lethal: my chain 7-12-17 ends in a Heavy next to his Base (22): strike it
check('Heavy next to the enemy Base', () => { const s = base(); s.cells[7] = P(0, 'LINE', 2); s.cells[12] = P(0, 'LINE', 2); s.cells[17] = P(0, 'HEAVY', 4); s.cells[21] = P(1, 'SQUAD', 3); s.cells[23] = P(1, 'BIG', 6); return s; },
  (r) => r.t.winner === 0);
// 2. cut: his Heavy at 7 stands next to my Base and destroys it next turn; it hangs on a Post (12)
//    and a Line (17); I hold Cut: cut the chain
check('cut the chain that kills my Base', () => { const s = base(); s.p[0].hand = ['CUT', 'POST']; s.cells[17] = P(1, 'LINE', 2); s.cells[12] = P(1, 'POST', 1); s.cells[7] = P(1, 'HEAVY', 4); s.cells[3] = P(0, 'LINE', 2); return s; },
  (r) => r.t.winner === 0 || !(r.t.cells[7] && r.t.cells[7].side === 1));
// 3. cut, the spec's case on the last turn: his Line at 17 is the only link to three Posts
//    (12, 11, 13) and the piece count decides now: destroy the link
check('cut the one link to three pieces (last turn)', () => { const s = base(); s.turnNo = 24; s.p[0].hand = ['CUT', 'POST']; s.cells[7] = P(0, 'SQUAD', 3); s.cells[17] = P(1, 'LINE', 2); s.cells[12] = P(1, 'POST', 1); s.cells[11] = P(1, 'POST', 1); s.cells[13] = P(1, 'POST', 1); return s; },
  (r) => r.t.winner === 0);
// 4. don't waste: my Line (2) next to his Heavy (4), nothing else to do: never strike it
check('never strike a stronger piece', () => { const s = base(); s.cells[7] = P(0, 'LINE', 2); s.cells[12] = P(1, 'HEAVY', 4); s.cells[17] = P(1, 'LINE', 2); return s; },
  (r) => !r.acts.some(a => a.t === 'strike' && a.from === 7 && a.to === 12));
console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
