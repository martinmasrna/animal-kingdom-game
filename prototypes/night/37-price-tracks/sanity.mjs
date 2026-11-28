// node sanity.mjs: set positions a person never gets wrong (sell to reach 40, never Boost a good
// you hold none of, Crash the good a Spy showed him holding four of), for Greedy and Expert.
// Expert is asked on five different seeds and must pass every one. Seat 0 to act.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ hand, coin = 2, price = { X: 4, Y: 4, Z: 4 }, pts = 0, hisPts = 0, hisHand = null, seen = false, round = 3, first = 0 }) {
  const s = newMatch({ seed: 51, first });
  s.round = round; s.turnNo = 2 * round - 1 + first; s.toAct = 0;
  s.p[0].hand = hand.slice(); s.p[0].coin = coin; s.p[0].pts = pts; s.p[1].pts = hisPts; s.price = { ...price };
  if (hisHand) s.p[1].hand = hisHand.slice();
  if (seen) s.p[1].seen = s.p[1].hand.slice();
  return s;
}
function turnOf(bot, s, rng) {
  let t = s; const acts = [];
  for (let k = 0; k < 20 && t.winner === null && t.toAct === s.toAct; k++) {
    const a = bot(t, rng); acts.push(a);
    if (a.t === 'end') return { acts, before: t, after: act(t, a) };
    t = act(t, a);
  }
  return { acts, before: t, after: t };
}
const show = (acts) => acts.map(a => a.t === 'sell' ? `sell ${a.n} ${a.good}` : a.t === 'play' ? CARDS[a.card].name + (a.good ? ' ' + a.good : '') : 'end').join(', ');
const POSITIONS = [
  // (reaching 40 ends the match at the end of the round, so the lethal turn is the second player's)
  { name: 'lethal: I play second this round, I am on 32 and he on 30, two Good Z in hand, Z at 4: sell them',
    make: () => base({ hand: ['Z', 'Z', 'X', 'Y', 'SPY'], coin: 2, pts: 32, hisPts: 30, first: 1 }),
    ok: (r) => r.after.winner === 0 },
  { name: "don't waste: no Boost on a good I hold none of (Z is the dearest; I hold X and Y)",
    make: () => base({ hand: ['X', 'X', 'Y', 'BOO', 'BOO'], coin: 4, price: { X: 4, Y: 3, Z: 7 } }),
    ok: (r) => !r.acts.some(a => a.t === 'play' && a.card === 'BOO' && a.good === 'Z') },
  { name: 'free crash: a Spy showed him four Good Z, I hold none and have 2 coin: Crash Z',
    make: () => base({ hand: ['X', 'Y', 'CRA', 'X', 'Y'], coin: 2, price: { X: 4, Y: 4, Z: 7 }, hisHand: ['Z', 'Z', 'Z', 'Z', 'X'], seen: true, pts: 10, hisPts: 12 }),
    ok: (r) => r.acts.some(a => a.card === 'CRA' && a.good === 'Z') },
];
export function runSanity(seeds = 5) {
  const expert = expertBot(EXPERT), out = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, seeds]]) {
      let passed = 0, ex = '', bad = '';
      for (let k = 0; k < n; k++) { const r = turnOf(bot, P.make(), makeRng(100 + k)); if (P.ok(r)) passed++; else if (!bad) bad = show(r.acts); if (k === 0) ex = show(r.acts); }
      out.push({ position: P.name, bot: bn, pass: passed === n, passed, of: n, example: bad || ex });
    }
  }
  return out;
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const res = runSanity();
  for (const r of res) console.log(`${r.pass ? 'ok  ' : 'FAIL'} ${r.bot.padEnd(6)} ${r.passed}/${r.of} ${r.position}: ${r.example}`);
  const bad = res.filter(r => r.bot === 'expert' && !r.pass).length;
  console.log(bad ? bad + ' Expert failures' : 'Expert passes every set position');
}
