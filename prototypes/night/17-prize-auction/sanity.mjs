// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which plays a mixed strategy). sim.mjs runs the same checks into report.json.
import { newMatch, coinOf } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ myHand, myDeck = [], myDiscard = [], oppHand, oppDeck = [], oppDiscard = [], pot, prizes }) {
  const s = newMatch({ seed: 5 });
  s.phase = 'bid'; s.need = [true, true]; s.bids = [null, null]; s.pot = pot; s.prizes = prizes; s.round = 16 - prizes.length;
  s.p[0] = { hand: myHand, deck: myDeck, discard: myDiscard, won: [] };
  s.p[1] = { hand: oppHand, deck: oppDeck, discard: oppDiscard, won: [] };
  return s;
}
const bidValue = (a) => a.t === 'bid' ? coinOf(a.cards) : -1;

export const POSITIONS = [
  {
    name: "don't overpay: his hand is empty, Point 3 up: bid exactly 1",
    make() { return base({ myHand: ['C3', 'C2', 'C1', 'C1'], myDeck: ['C1', 'C1'], oppHand: [], oppDeck: ['C1', 'C1', 'C2'], oppDiscard: ['C1', 'C1', 'C1', 'C1', 'C2'], pot: ['P3'], prizes: ['C2', 'P2', 'C3', 'P5'] }); },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: bidValue(a) === 1, got: bidValue(a) }; },
  },
  {
    name: 'Debt alone: bids come back and the lower bidder takes it, so outbid everything he could bid',
    make() { return base({ myHand: ['C3', 'C2', 'C1', 'C1', 'C1'], myDeck: ['C1', 'C1', 'C1'], oppHand: ['C1', 'C1', 'C1'], oppDeck: ['C1', 'C1', 'C1', 'C2', 'C2'], pot: ['DEBT'], prizes: ['C2', 'P2', 'C3', 'P5', 'P3'] }); },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: bidValue(a) >= 6, got: bidValue(a) }; }, // his best three cards bid at most 2 + 2 + 1 = 5
  },
  {
    name: 'lethal: the last prize decides the game and my coin beats his largest possible bid: bid above it',
    make() {
      // points so far: me 5 (Point 5), him 7 (Point 3 + Point 2 + Point 2); the last prize is Point 3
      return base({ myHand: ['C3', 'C3', 'C2', 'C1'], myDeck: ['C1', 'C1'], myDiscard: ['P5', 'C1', 'C1', 'C1', 'C2'], oppHand: ['C1', 'C1'], oppDeck: ['C2', 'C1', 'C1'], oppDiscard: ['P3', 'P2', 'P2', 'C1', 'C1', 'C2'], pot: ['P3'], prizes: [] });
    },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: bidValue(a) > 3, got: bidValue(a) }; }, // his best two cards: 2 + 1 = 3
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
