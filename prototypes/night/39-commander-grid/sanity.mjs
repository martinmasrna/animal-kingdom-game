// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act, CARDS, cellOf, cmdOf, pieceById } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const unit = (uid, card, side, cell, extra = {}) => ({ uid, card, side, atk: CARDS[card].atk, hp: CARDS[card].hp, max: CARDS[card].hp, cell, acted: false, moved: false, fresh: false, ...extra });
function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.uid = 100; s.turn = 0; s.toAct = 0; s.turnNo = 9;
  s.pieces = s.pieces.filter(u => u.card === 'CMD');
  for (const u of s.pieces) { u.hp = 15; u.acted = false; u.moved = false; u.fresh = false; }
  for (const p of s.p) { p.hand = []; p.mana = p.maxMana = 5; }
  return s;
}
function turnOf(bot, s, rng) {
  const me = s.toAct, out = [];
  let t = s;
  for (let k = 0; k < 40 && t.winner === null && t.toAct === me; k++) { const a = bot(t, rng); out.push(a); if (a.t === 'end') break; t = act(t, a); }
  return { acts: out, t };
}
export const POSITIONS = [
  {
    name: 'lethal: his Commander on 3 health next to my ready Raider',
    make() { const s = base(); cmdOf(s, 1).hp = 3; s.pieces.push(unit(10, 'RAI', 0, cellOf(4, 2))); s.pieces.push(unit(11, 'HEA', 1, cellOf(4, 1))); s.p[0].hand = ['GUA']; return s; },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: t.winner === 0, got: acts }; },
  },
  {
    name: 'free trade: my ready Heavy next to his Pawn takes it',
    make() { const s = base(); s.pieces.push(unit(10, 'HEA', 0, cellOf(2, 2))); s.pieces.push(unit(11, 'PAW', 1, cellOf(3, 2))); return s; },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: !pieceById(t, 11), got: acts }; },
  },
  {
    name: "don't waste: never Hit 3 his 1-health Pawn that my Pawn next to it kills for free",
    make() { const s = base(); s.pieces.push(unit(10, 'PAW', 0, cellOf(1, 1))); s.pieces.push(unit(11, 'PAW', 1, cellOf(1, 2), { hp: 1 })); s.p[0].hand = ['H3']; return s; },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: !acts.some(a => a.t === 'play' && a.card === 'H3' && a.tgt === 11), got: acts }; },
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
