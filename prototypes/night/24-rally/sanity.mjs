// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.server = 0; s.toAct = 0; s.rally = [];
  s.p[0].hand = ['PUS', 'DRI', 'SLI', 'SMA', 'LOB']; s.p[1].hand = ['PUS', 'DIG', 'LOB', 'DRI', 'SLI'];
  for (const p of s.p) { p.stamina = 6; p.points = 1; p.games = 1; }
  return s;
}
export const POSITIONS = [
  {
    name: 'free point: he has 0 stamina, so only Push (Reach 2) is payable: serve with Pace 3 or more',
    make() { const s = base(); s.p[1].stamina = 0; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'shot' && CARDS[a.card].pace >= 3, got: a }; },
  },
  {
    name: 'lethal: match point (2 games, 3 points), he has 0 stamina: serve with Pace 3 or more',
    make() { const s = base(); s.p[1].stamina = 0; s.p[0].games = 2; s.p[0].points = 3; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); const t = act(s, a); return { pass: t.winner === 0, got: a }; },
  },
  {
    name: "don't waste: answering a Pace 1 shot with Push and Dig as the only legal returns: Push, which is free",
    make() { const s = base(); s.server = 1; s.rally = [{ card: 'PUS', side: 1 }]; s.toAct = 0; s.p[0].hand = ['PUS', 'DIG', 'SMA', 'ACE']; s.p[0].stamina = 2; s.p[1].hand = ['DRI', 'SLI', 'LOB', 'SMA']; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'shot' && a.card === 'PUS', got: a }; },
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
  for (const r of rows) console.log(`${r.pass ? 'ok  ' : 'FAIL'} ${r.bot.padEnd(6)} ${r.passed}/${r.of} ${r.position}  ${JSON.stringify(r.last)}`);
  const bad = rows.filter(r => r.bot === 'expert' && !r.pass).length;
  console.log(bad ? bad + ' Expert failures' : 'Expert passes every position');
}
