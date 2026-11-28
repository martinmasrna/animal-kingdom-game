// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which plays a mixed strategy). sim.mjs runs the same checks into report.json.
import { newMatch, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ pos = [3, 4], life = [12, 12], energy = [4, 4], myHand, oppHand, oppDeck, oppDiscard = [] }) {
  const s = newMatch({ seed: 21 });
  s.turn = 6; s.need = [true, true]; s.moves = [null, null];
  s.p[0] = { pos: pos[0], life: life[0], energy: energy[0], rest: 0, hand: myHand, deck: ['JAB', 'PUN', 'KIC', 'SWE'], discard: [] };
  s.p[1] = { pos: pos[1], life: life[1], energy: energy[1], rest: 0, hand: oppHand, deck: oppDeck, discard: oppDiscard };
  return s;
}
export const POSITIONS = [
  {
    name: 'lethal: he is on 1 at distance 1 (his Guard is spent): Jab, speed 1, lands before anything',
    make() { return base({ pos: [3, 4], life: [12, 1], myHand: ['JAB', 'PUN', 'LUN', 'KIC'], oppHand: ['PUN', 'KIC', 'JAB', 'SWE'], oppDeck: ['LUN', 'SHO', 'PUN', 'KIC'], oppDiscard: ['GUA'] }); },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: a.card === 'JAB', got: a }; },
  },
  {
    name: "don't waste: never Shot at distance 1 (stepping back 1 leaves him at 2, outside 3-4)",
    make() { return base({ pos: [3, 4], myHand: ['SHO', 'KIC', 'SWE', 'JAB'], oppHand: ['PUN', 'KIC', 'JAB', 'SWE'], oppDeck: ['LUN', 'SHO', 'PUN', 'GUA'] }); },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: a.card !== 'SHO', got: a }; },
  },
  {
    name: "don't pay for nothing: at distance 5 nothing reaches; never pay for a card that neither moves nor hits (Kick, Sweep, Guard)",
    make() { return base({ pos: [1, 6], energy: [3, 4], myHand: ['KIC', 'SWE', 'GUA', 'JAB', 'LUN'], oppHand: ['PUN', 'KIC', 'JAB', 'SWE'], oppDeck: ['LUN', 'SHO', 'PUN', 'GUA'] }); },
    ok(s, bot, rng) { const a = bot(s, 0, rng); return { pass: !['KIC', 'SWE', 'GUA'].includes(a.card), got: a }; },
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
