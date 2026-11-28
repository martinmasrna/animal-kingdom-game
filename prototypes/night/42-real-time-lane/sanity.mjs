// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, step, CARDS, DECK } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const W = { t: 'wait' };
function base({ myHand, oppHand, myMana, oppMana, tick = 100 }) {
  const s = newMatch({ seed: 11 });
  s.tick = tick; s.uid = 500; s.units = []; s.mana = [myMana, oppMana];
  const rest = (h) => h.concat(DECK.filter(id => !h.includes(id)));
  s.queue = [rest(myHand), rest(oppHand)];
  s.seen = [[], s.queue[1].slice()]; // his whole cycle has been seen, so his queue is known
  return s;
}
const unit = (uid, side, card, x, extra = {}) => { const c = CARDS[card]; return { uid, side, card, x, hp: c.hp, max: c.hp, atk: c.atk, spd: c.spd, rng: c.rng, wall: c.kind === 'wall', ...extra }; };

export const POSITIONS = [
  {
    name: 'lethal: his base on 1, empty lane, he cannot pay for an answer in time; send the Runner',
    make() { const s = base({ myHand: ['RUN', 'TAN', 'WAL', 'GRU'], oppHand: ['TAN', 'WAL', 'BRU', 'BLA'], myMana: 5, oppMana: 0 }); s.base[1] = 1; return s; },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: a.t === 'play' && a.card === 'RUN', got: a }; },
  },
  {
    name: "don't waste: never Blast an empty lane (ten decisions, nothing on his side)",
    make() { return base({ myHand: ['BLA', 'TAN', 'WAL', 'GRU'], oppHand: ['TAN', 'WAL', 'BRU', 'BLA'], myMana: 10, oppMana: 0 }); },
    ok(s, bot, rng) {
      let t = s; const got = [];
      for (let k = 0; k < 10; k++) {
        const a = bot(t, 0, rng); got.push(a);
        if (a.t === 'play' && a.card === 'BLA' && !t.units.some(u => u.side === 1 && Math.abs(u.x - a.x) <= 1.5)) return { pass: false, got };
        t = step(t, [a, W]); t = step(t, [W, W]);
      }
      return { pass: true, got };
    },
  },
  {
    name: 'free value: three Swarm units two steps from my base, Blast in hand: Blast them',
    make() { const s = base({ myHand: ['BLA', 'TAN', 'WAL', 'BRU'], oppHand: ['TAN', 'WAL', 'BRU', 'GRU'], myMana: 3, oppMana: 0 }); s.units = [unit(1, 1, 'SWA', 2), unit(2, 1, 'SWA', 2), unit(3, 1, 'SWA', 2)]; return s; },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: a.t === 'play' && a.card === 'BLA' && Math.abs(a.x - 2) <= 1.5, got: a }; },
  },
];

export function runSanity(expert, tries = 5) {
  const rows = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, tries]]) {
      let pass = 0, last = null;
      for (let k = 0; k < n; k++) { const r = P.ok(P.make(), bot, makeRng(101 + k)); if (r.pass) pass++; last = r.got; }
      rows.push({ position: P.name, bot: bn, pass: pass === n, passed: pass, of: n, last });
    }
  }
  return rows;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const rows = runSanity(expertBot(EXPERT));
  for (const r of rows) console.log(`${r.pass ? 'ok  ' : 'FAIL'} ${r.bot.padEnd(6)} ${r.passed}/${r.of} ${r.position}  ${r.pass ? '' : JSON.stringify(r.last)}`);
  const bad = rows.filter(r => r.bot === 'expert' && !r.pass).length;
  console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
}
