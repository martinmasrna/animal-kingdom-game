// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const unit = (uid, card, extra = {}) => ({ uid, card, atk: CARDS[card].atk, hp: CARDS[card].hp, max: CARDS[card].hp, ready: true, ranged: CARDS[card].ranged, ...extra });
function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.uid = 100; s.turn = 0; s.toAct = 0;
  for (const p of s.p) { p.front = []; p.back = []; p.hand = []; p.mana = p.maxMana = 5; p.life = 20; }
  return s;
}
// the mover's actions until it ends its turn
function turnOf(bot, s, rng) {
  const me = s.toAct, out = [];
  let t = s;
  for (let k = 0; k < 30 && t.winner === null && t.toAct === me; k++) { const a = bot(t, rng); out.push(a); if (a.t === 'end') break; t = act(t, a); }
  return { acts: out, t };
}
export const POSITIONS = [
  {
    name: 'lethal: his front is empty, he is on 4, my ready Raider (3) and Shooter (1) hit him',
    make() { const s = base(); s.p[1].life = 4; s.p[0].front = [unit(1, 'RAI')]; s.p[0].back = [unit(2, 'SHO')]; s.p[1].back = [unit(3, 'CAN')]; s.p[0].hand = ['WAL']; return s; },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: t.winner === 0, got: acts }; },
  },
  {
    name: 'free shot: my ready Gunner shoots his front Raider on 2 health',
    make() { const s = base(); s.p[0].back = [unit(1, 'GUN')]; s.p[1].front = [unit(2, 'RAI')]; s.p[1].life = 20; return s; },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: acts.some(a => a.t === 'attack' && a.from === 1 && a.to === 2), got: acts }; },
  },
  {
    name: "don't waste: never Hit 4 a 1-health unit while Hit 2 is in hand",
    make() { const s = base(); s.p[0].hand = ['H2', 'H4']; s.p[0].mana = s.p[0].maxMana = 4; s.p[1].front = [unit(2, 'STR')]; s.p[0].front = [unit(1, 'WAL', { ready: false })]; return s; },
    ok(s, bot, rng) {
      const { acts } = turnOf(bot, s, rng); let t = s, bad = false;
      for (const a of acts) {
        if (a.t === 'end') break;
        if (a.t === 'play' && a.card === 'H4') { const u = t.p[1].front.concat(t.p[1].back).find(x => x.uid === a.tgt); if (u && u.hp <= 2 && t.p[0].hand.includes('H2')) bad = true; }
        t = act(t, a);
      }
      return { pass: !bad, got: acts };
    },
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
