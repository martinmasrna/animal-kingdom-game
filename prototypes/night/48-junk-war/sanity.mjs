// node sanity.mjs [budget] [seed]: set positions a person never gets wrong, for Greedy and Expert:
// don't end a buy with 8 coin and Score 4 in the row, Purge the two Junk rather than a Coin,
// on 22 points with nothing to fear buy the Score 4 rather than Coin 3.
import { newMatch, act } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const direct = import.meta.url === `file://${process.argv[1]}`;
const expert = expertBot({ budget: (direct && +process.argv[2]) || 1000 }), rng = makeRng((direct && +process.argv[3]) || 1);
const base = () => { const s = newMatch({ seed: 5, first: 1 }); s.turn = s.toMove = 1; return s; };
const show = (s, a) => a.t === 'buy' ? 'buy ' + s.row[a.i] : a.t === 'purge' ? 'purge ' + a.card : a.t === 'play' ? 'play ' + a.card : a.t;
export const results = [];
const check = (name, mk, ok, steps = 1) => {
  for (const [bn, b] of [['greedy', (s) => greedyBot(s)], ['expert', expert]]) {
    let s = mk(); const acts = [];
    for (let k = 0; k < steps && s.winner === null; k++) { const a = b(s, rng); acts.push(show(s, a)); s = act(s, a); if (a.t === 'end') break; }
    const pass = ok(acts);
    results.push({ position: name, bot: bn, pass, chose: acts.join(', ') });
    if (direct) console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${acts.join(', ')}`);
  }
};
// 1. don't waste: 8 coin in the buy phase, Score 4 in the row
check('8 coin, Score 4 in the row', () => { const s = base(); s.p[1].hand = []; s.phase = 'buy'; s.coin = 8; s.row = ['Score4', 'Clean', 'Foul', 'Score2', 'Coin2']; s.p[1].points = 6; s.p[0].points = 7; return s; },
  (acts) => acts[0] !== 'end');
// 2. free clean: Purge with two Junk and two Coins in hand: remove both Junk
check('Purge the Junk', () => { const s = base(); s.p[1].hand = ['Purge', 'Junk', 'Junk', 'Coin', 'Coin']; s.phase = 'play'; return s; },
  (acts) => acts.filter(a => a.startsWith('purge')).length === 2 && acts.filter(a => a === 'purge Junk').length === 2, 4);
// 3. lethal buy: 22 points, 8 coin, Score 4 and Coin 3 in the row, the Junk pile empty
check('Score 4 on 22 points', () => { const s = base(); s.p[1].hand = []; s.phase = 'buy'; s.coin = 8; s.junk = 0; s.row = ['Coin3', 'Score4', 'Draw', 'Clean', 'Score2']; s.p[1].points = 22; s.p[0].points = 18; return s; },
  (acts) => acts[0] === 'buy Score4');
if (direct) { const bad = results.filter(r => !r.pass).length; console.log(bad ? bad + ' failures' : 'all pass'); }
