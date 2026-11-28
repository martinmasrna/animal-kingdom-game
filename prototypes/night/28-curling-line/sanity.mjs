// node sanity.mjs [budget] [seed]: set positions a person never gets wrong, for Greedy and Expert:
// the free takeout with Hit, no Any where a cheaper card reaches the same cell, drawing to the
// Mark for the match on the last throw.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const direct = import.meta.url === `file://${process.argv[1]}`;
const expert = expertBot({ budget: (direct && +process.argv[2]) || 1000 }), rng = makeRng((direct && +process.argv[3]) || 1);
// side 1 to throw, holding the hammer, on the given throw of the given end
const base = (throwNo, end) => { const s = newMatch({ seed: 3, hammer: 1 }); s.end = end; s.throwNo = throwNo; s.toMove = 1; s.stones = []; s.energy = [5, 5]; return s; };
const show = (a) => `${a.card ? CARDS[a.card].name : 'Lag'} to ${a.d}`;
export const results = [];
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', (s) => greedyBot(s)], ['expert', expert]]) {
    const s = mk(), a = b(s, rng), pass = ok(a, act(s, a), s);
    results.push({ position: name, bot: bn, pass, chose: show(a) });
    if (direct) console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(a)}`);
  }
};
// 1. free takeout: last throw of end 3, his only stone on the Mark, the path clear; Hit and Draw 9 in hand
check('free takeout', () => { const s = base(7, 3); s.stones = [{ uid: 90, owner: 0, cell: 9 }]; s.p[1].hand = ['Hit', 'Draw9', 'Guard']; s.score = [2, 1]; return s; },
  (a, t) => a.card === 'Hit' && t.lastEnd && t.lastEnd[0] === 1);
// 2. don't waste: last throw of end 2, his stone on 10; only a stone on 9 scores, and Draw 9 reaches it as well as Any
check('no Any for a cheap cell', () => { const s = base(7, 2); s.stones = [{ uid: 91, owner: 0, cell: 10 }]; s.p[1].hand = ['Any', 'Draw9', 'Short']; return s; },
  (a, t, s) => (a.card !== 'Any' || !s.p[1].hand.some(id => id !== 'Any' && CARDS[id].d === a.d)) && t.lastEnd && t.lastEnd[0] === 1);
// 3. lethal: last throw of the last end, level on points, his stone on 11 behind the Mark, the path clear: get closer and win
check('draw to the Mark for the match', () => { const s = base(7, 6); s.score = [3, 3]; s.stones = [{ uid: 93, owner: 0, cell: 11 }]; s.p[1].hand = ['Draw9', 'Hit', 'Guard']; return s; },
  (a, t) => t.winner === 1);
if (direct) { const bad = results.filter(r => !r.pass).length; console.log(bad ? bad + ' failures' : 'all pass'); }
