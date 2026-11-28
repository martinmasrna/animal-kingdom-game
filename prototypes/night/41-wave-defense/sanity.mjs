// node sanity.mjs [budget] [seed]: set positions a person never gets wrong, for Greedy and Expert:
// finish the last threat, never Repair a full Wall, Bomb a lane of three 2-health threats.
import { newMatch, act, THREATS, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const direct = import.meta.url === `file://${process.argv[1]}`;
const expert = expertBot({ budget: (direct && +process.argv[2]) || 2000 }), rng = makeRng((direct && +process.argv[3]) || 1);
let uid = 900;
const threat = (id, row, hp) => ({ uid: uid++, id, atk: THREATS[id].atk, hp: hp ?? THREATS[id].hp, max: THREATS[id].hp, row });
const base = () => { const s = newMatch({ seed: 11 }); s.lanes = [[], [], []]; s.slots = [null, null, null]; s.hand = []; s.round = 9; s.mana = 5; s.wall = 20; return s; };
const show = (a) => a.t === 'play' ? `${CARDS[a.card].name}${a.lane !== undefined ? ' lane ' + a.lane : ''}${a.uid ? ' on ' + a.uid : ''}` : a.t === 'reward' ? 'reward ' + a.card : a.t;
export const results = [];
const check = (name, mk, ok) => {
  for (const [bn, b] of [['greedy', (s) => greedyBot(s)], ['expert', expert]]) {
    let s = mk(); const acts = [];
    for (let k = 0; k < 12 && !s.result && s.phase === 'play'; k++) { const a = b(s, rng); acts.push(a); if (a.t === 'end') break; s = act(s, a); }
    const pass = ok(acts, s);
    results.push({ position: name, bot: bn, pass, chose: acts.map(show).join(', ') });
    if (direct) console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${acts.map(show).join(', ')}`);
  }
};
// 1. lethal: the last threat stands in row 1 with 3 health, the threat deck is empty, Hit 3 in hand
check('finish the last threat', () => { const s = base(); s.threatDeck = []; s.lanes[1] = [threat('Grunt', 1, 3)]; s.hand = ['Hit3', 'Guard', 'Draw2']; s.mana = 2; return s; },
  (acts, s) => s.result === 'win');
// 2. don't waste: a full Wall, Repair in hand with mana to spare, threats far off: never Repair
check('no Repair on a full Wall', () => { const s = base(); s.lanes[0] = [threat('Grunt', 4)]; s.hand = ['Repair', 'Guard']; s.slots = [null, { uid: 950, id: 'Guard', atk: 1, hp: 5, max: 5, shoot: 0 }, null]; s.mana = 3; return s; },
  (acts) => !acts.some(a => a.card === 'Repair'));
// 3. free value: three threats with 2 health in one lane, Bomb in hand: Bomb that lane
check('Bomb three 2-health threats', () => { const s = base(); s.lanes[2] = [threat('Swift', 2), threat('Runner', 3), threat('Grunt', 4, 2)]; s.hand = ['Bomb']; s.mana = 3; return s; },
  (acts) => acts.some(a => a.card === 'Bomb' && a.lane === 2));
if (direct) { const bad = results.filter(r => !r.pass).length; console.log(bad ? bad + ' failures' : 'all pass'); }
