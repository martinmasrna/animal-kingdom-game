// node sanity.mjs [budget] [seed]: set positions a person never gets wrong, for Greedy and Expert:
// the cheapest card that wins a round the opponent passed, passing when ahead of a passed opponent,
// playing the card that wins the match.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const direct = import.meta.url === `file://${process.argv[1]}`;
const expert = expertBot({ budget: (direct && +process.argv[2]) || 3000 }), rng = makeRng((direct && +process.argv[3]) || 1);
let uid = 900;
const card = (id, owner, power) => ({ uid: uid++, id, power: power ?? CARDS[id].power, owner });
// side 1 to act, side 0 has passed
const base = (round) => { const s = newMatch({ seed: 9, first: 1 }); s.round = round; s.turn = s.toMove = 1; s.passed = [true, false]; return s; };
const show = (a) => a.t === 'pass' ? 'pass' : 'play ' + a.card;
export const results = [];
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', (s) => greedyBot(s)], ['expert', expert]]) {
    const s = mk(), a = b(s, rng), pass = ok(a, act(s, a));
    results.push({ position: name, bot: bn, pass, chose: show(a) });
    if (direct) console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(a)}`);
  }
};
// 1. cheapest win: round 1, he passed 2 ahead; Troop (1 mana, 3) and Big (5 mana, 11) in hand: Troop
check('cheapest win', () => { const s = base(1); s.table = [[card('Squad', 0), card('Troop', 0)], [card('Squad', 1), card('Grunt', 1)]]; s.p[1].hand = ['Troop', 'Big', 'Heavy', 'Grunt']; s.purse = [12, 14]; return s; },
  (a) => a.t === 'play' && a.card === 'Troop');
// 2. don't waste: round 2, he passed and I am ahead: pass
check('pass when ahead', () => { const s = base(2); s.wins = [1, 0]; s.table = [[card('Heavy', 0)], [card('Big', 1)]]; s.p[1].hand = ['Troop', 'Squad', 'Heavy']; s.purse = [6, 8]; return s; },
  (a) => a.t === 'pass');
// 3. lethal: round 3 at one round each, he passed on 10, I am on 5 with Heavy in hand and 3 mana: play it
check('Heavy for the match', () => { const s = base(3); s.wins = [1, 1]; s.table = [[card('Heavy', 0), card('Troop', 0)], [card('Squad', 1)]]; s.p[1].hand = ['Heavy', 'Grunt']; s.purse = [2, 3]; return s; },
  (a, t) => a.t === 'play' && a.card === 'Heavy');
if (direct) { const bad = results.filter(r => !r.pass).length; console.log(bad ? bad + ' failures' : 'all pass'); }
