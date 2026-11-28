// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const unit = (uid, card, extra = {}) => ({ uid, card, atk: CARDS[card].atk, hp: CARDS[card].hp, dmg: 0, fresh: false, ex: false, ...extra });
function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.uid = 100; s.turn = 0; s.toAct = 0; s.phase = 'main'; s.attacked = false; s.attackers = [];
  for (const p of s.p) { p.board = []; p.hand = []; p.mana = p.maxMana = 5; p.life = 20; }
  return s;
}
// runs the mover's actions until its side stops acting (end of turn or an attack waiting for blocks)
function turnOf(bot, s, rng) {
  const me = s.toAct, out = [];
  let t = s;
  for (let k = 0; k < 30 && t.winner === null && t.toAct === me; k++) {
    const a = bot(t, rng); out.push(a);
    if (a.t === 'end') break;
    t = act(t, a);
  }
  return { acts: out, t };
}
export const POSITIONS = [
  {
    name: 'lethal: he is on 5 with no ready unit, my ready Line and Striker attack',
    make() { const s = base(); s.p[1].life = 5; s.p[0].board = [unit(1, 'LIN'), unit(2, 'STR')]; s.p[1].board = [unit(3, 'BIG', { ex: true })]; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'attack' && a.units.length === 2, got: a }; },
  },
  {
    name: 'free block: his Striker attacks, my ready Line blocks it',
    make() { const s = base(); s.turn = 1; s.phase = 'block'; s.toAct = 0; s.attacked = true; s.p[1].board = [unit(1, 'STR', { ex: true })]; s.attackers = [1]; s.p[0].board = [unit(2, 'LIN')]; return s; },
    ok(s, bot, rng) { const a = bot(s, rng); return { pass: a.t === 'block' && a.pairs.some(([b, x]) => b === 2 && x === 1), got: a }; },
  },
  {
    name: "don't waste: never Hit 4 a unit that Hit 2 destroys",
    make() { const s = base(); s.p[0].hand = ['H2', 'H4']; s.p[0].mana = s.p[0].maxMana = 4; s.p[1].board = [unit(1, 'RAI')]; s.p[0].board = [unit(2, 'LIN')]; return s; },
    ok(s, bot, rng) {
      const { acts } = turnOf(bot, s, rng); let t = s, bad = false;
      for (const a of acts) { if (a.t === 'play' && a.card === 'H4') { const u = t.p[1].board.find(x => x.uid === a.tgt); if (u && u.hp - u.dmg <= 2 && t.p[0].hand.includes('H2')) bad = true; } if (a.t === 'end') break; t = act(t, a); }
      return { pass: !bad, got: acts };
    },
  },
  {
    name: "don't throw a unit away: my lone Striker never attacks into his ready Line",
    make() { const s = base(); s.p[0].board = [unit(1, 'STR')]; s.p[1].board = [unit(2, 'LIN')]; s.p[0].hand = []; return s; },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: !acts.some(a => a.t === 'attack'), got: acts }; },
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
