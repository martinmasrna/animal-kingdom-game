// node sanity.mjs [budget] [seed]: set positions a person never gets wrong, for Greedy and Expert:
// a free challenge, lethal, not dying for nothing, a free trade, not wasting the turn.
import { newMatch, act } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const direct = import.meta.url === `file://${process.argv[1]}`;
const expert = expertBot({ budget: (direct && +process.argv[2]) || 3000 }), rng = makeRng((direct && +process.argv[3]) || 1);
const base = () => { const s = newMatch({ seed: 7, first: 1 }); s.p[0].hand = []; s.p[1].hand = []; s.p[0].board = []; s.p[1].board = []; s.p[0].coin = s.p[1].coin = false; return s; };
const unit = (uid, name, ready) => { const c = { Striker: [2, 1], Guard: [1, 4], Raider: [3, 2], Line: [3, 4], Heavy: [5, 6] }[name]; return { uid, name, real: name, up: true, atk: c[0], hp: c[1], max: c[1], ready }; };
// the bot's whole turn (claims answered with a pass), from side 1
function turnOf(bot, s) {
  const acts = [];
  for (let k = 0; k < 30 && s.winner === null; k++) {
    if (s.pending && s.toMove === 0) { s = act(s, { t: 'pass' }); continue; }
    const a = bot(s, rng); acts.push(a);
    if (a.t === 'end') break;
    s = act(s, a);
  }
  return { acts, s };
}
const show = (a) => a.t === 'play' ? `claim ${a.name}${a.card !== a.name ? ' (with ' + a.card + ')' : ''}${a.target ? '→' + (a.target.side === 1 ? 'own ' : '') + (a.target.i < 0 ? 'player' : 'unit ' + a.target.i) : ''}` : a.t === 'attack' ? `attack ${a.from}→${a.to < 0 ? 'player' : a.to}` : a.t;
export const results = [];
const check = (name, mk, ok, whole) => {
  for (const [bn, b] of [['greedy', (s) => greedyBot(s)], ['expert', expert]]) {
    const s = mk(), r = whole ? turnOf(b, s) : { acts: [b(s, rng)] };
    const pass = ok(r);
    results.push({ position: name, bot: bn, pass, chose: r.acts.map(show).join(', ') });
    if (direct) console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${r.acts.map(show).join(', ')}`);
  }
};
// 1. free challenge: all three of his Blasts lie face-up in his discard and he claims Blast at me
check('free challenge', () => { const s = base(); s.turn = 0; s.p[0].discard = ['Blast', 'Blast', 'Blast']; s.p[0].hand = ['Line', 'Guard']; s.p[0].mana = 4;
  s.pending = { side: 0, card: 'Striker', name: 'Blast', target: { side: 1, i: -1, uid: null } }; s.toMove = 1; return s; }, r => r.acts[0].t === 'challenge');
// 2. lethal: he is on 5, I hold Blast with 4 mana: claim it honestly at him
check('lethal Blast into 5', () => { const s = base(); s.p[0].life = 5; s.p[1].hand = ['Blast', 'Guard', 'Line']; s.p[1].mana = s.p[1].maxMana = 4; s.turn = s.toMove = 1; return s; },
  r => { const a = r.acts[0]; return a.t === 'play' && a.card === 'Blast' && a.name === 'Blast' && a.target && a.target.side === 0 && a.target.i < 0; });
// 3. don't die for nothing: I am on 3 with two Heavies about to swing for lethal; he claims Guard
check('on 3 life, no challenge', () => { const s = base(); s.turn = 0; s.p[1].life = 3; s.p[0].life = 8; s.p[1].board = [unit(910, 'Heavy', false), unit(911, 'Heavy', false)];
  s.p[0].hand = ['Line', 'Raider']; s.p[0].mana = 2; s.pending = { side: 0, card: 'Striker', name: 'Guard', target: null }; s.toMove = 1; return s; }, r => r.acts[0].t === 'pass');
// 4. a free trade: my ready Line against his Striker, nothing in hand: kill the Striker
check('free trade', () => { const s = base(); s.p[1].board = [unit(920, 'Line', true)]; s.p[0].board = [unit(921, 'Striker', false)]; s.p[1].mana = s.p[1].maxMana = 2; s.turn = s.toMove = 1; return s; },
  r => r.acts.some(a => a.t === 'attack' && a.to === 0), true);
// 5. don't waste the turn: 3 mana, a Line in hand, empty table: put something on the board
check('use the mana', () => { const s = base(); s.p[1].hand = ['Line']; s.p[1].mana = s.p[1].maxMana = 3; s.turn = s.toMove = 1; return s; },
  r => r.acts.some(a => a.t === 'play'), true);
if (direct) { const bad = results.filter(r => !r.pass).length; console.log(bad ? bad + ' failures' : 'all pass'); }
