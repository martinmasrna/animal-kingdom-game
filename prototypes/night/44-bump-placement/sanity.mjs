// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.round = 5; s.starter = 0; s.toAct = 0; s.phase = 'place';
  s.spaces = [null, null, null, null, null];
  for (const p of s.p) { p.hand = ['WOR', 'FOR']; p.mana = 4; p.passed = false; p.points = 8; p.fund = false; }
  return s;
}
// the mover's placements until it passes (or the round ends)
function turnOf(bot, s, rng) {
  const me = s.toAct, out = [];
  let t = s;
  for (let k = 0; k < 20 && t.winner === null && t.toAct === me && t.phase === 'place' && t.round === s.round; k++) { const a = bot(t, rng); out.push(a); t = act(t, a); if (a.t === 'pass') break; }
  return { acts: out, t };
}
export const POSITIONS = [
  {
    name: 'lethal: on 17, he has passed with a Worker on Score 3; my Hand (1 mana) bumps it',
    make() { const s = base(); s.p[0].points = 17; s.p[1].passed = true; s.spaces[0] = { card: 'WOR', side: 1 }; s.p[0].hand = ['HAN']; s.p[0].mana = 1; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'place' && a.space === 0, got: a }; },
  },
  {
    name: 'free bump: his Worker on Score 3, my Hand in hand: take it',
    make() { const s = base(); s.spaces[0] = { card: 'WOR', side: 1 }; s.p[0].hand = ['HAN', 'WOR']; s.p[0].mana = 2; s.p[1].hand = ['WOR', 'WOR', 'HAN']; s.p[1].mana = 1; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'place' && a.space === 0, got: a }; },
  },
  {
    name: "don't waste: he has passed, Score 3 is the one open space: take it with the Worker, never the Chief",
    make() { const s = base(); s.p[1].passed = true; s.spaces = [null, { card: 'HAN', side: 0 }, { card: 'HAN', side: 0 }, { card: 'FOR', side: 0 }, { card: 'WOR', side: 0 }]; s.p[0].hand = ['CHI', 'WOR']; s.p[0].mana = 5; return s; },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: !acts.some(a => a.t === 'place' && a.card === 'CHI') && acts.some(a => a.t === 'place' && a.space === 0), got: acts }; },
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
