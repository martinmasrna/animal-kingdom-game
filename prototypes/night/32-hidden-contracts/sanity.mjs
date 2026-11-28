// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
// There is no one-move lethal here: contracts score only at the start of their owner's turn.
import { newMatch, act, CARDS, CONTRACTS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const unit = (uid, card, extra = {}) => ({ uid, card, atk: CARDS[card].atk, hp: CARDS[card].hp, max: CARDS[card].hp, ready: true, ...extra });
function base() {
  const s = newMatch({ seed: 7, first: 0 });
  s.uid = 100; s.turn = 0; s.toAct = 0; s.swapped = false;
  for (const p of s.p) { p.board = []; p.hand = []; p.mana = p.maxMana = 5; p.points = 4; p.kills = 0; p.killsLast = 0; }
  return s;
}
function turnOf(bot, s, rng) {
  const me = s.toAct, out = [];
  let t = s;
  for (let k = 0; k < 30 && t.winner === null && t.toAct === me; k++) { const a = bot(t, rng); out.push(a); if (a.t === 'end') break; t = act(t, a); }
  return { acts: out, t };
}
// my contracts: Tower and Spread; his: Crowd and More
function contracts(s, mine, his) { s.p[0].contracts = mine; s.p[0].cdeck = Object.keys(CONTRACTS).filter(c => !mine.includes(c)); s.p[1].contracts = his; s.p[1].cdeck = Object.keys(CONTRACTS).filter(c => !his.includes(c)); }
export const POSITIONS = [
  {
    name: 'free points: I hold Hunter; my ready Heavy and Line each destroy one of his two Strikers and survive: take both',
    make() { const s = base(); contracts(s, ['HUNTER', 'PATIENCE'], ['CROWD', 'MORE']); s.p[0].board = [unit(1, 'HEA'), unit(2, 'LIN')]; s.p[1].board = [unit(3, 'STR'), unit(4, 'STR')]; s.p[0].hand = ['GUA']; return s; },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: t.p[1].board.length === 0 || t.p[0].killsLast >= 2 || t.p[0].points > s.p[0].points, got: acts }; },
  },
  {
    name: 'free points: I hold Crowd with 3 units, a Striker in hand and room on the board: play it',
    make() { const s = base(); contracts(s, ['CROWD', 'TOWER'], ['SPREAD', 'MORE']); s.p[0].board = [unit(1, 'GUA', { ready: false }), unit(2, 'LIN', { ready: false }), unit(3, 'RAI', { ready: false })]; s.p[1].board = [unit(4, 'LIN')]; s.p[0].hand = ['STR']; s.p[0].mana = s.p[0].maxMana = 1; return s; },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: t.p[0].board.length >= 4, got: acts }; },
  },
  {
    name: "don't waste: never pay to replace a contract whose condition already holds (Crowd, 4 units on board)",
    make() { const s = base(); contracts(s, ['CROWD', 'PATIENCE'], ['TOWER', 'MORE']); s.p[0].board = [unit(1, 'GUA'), unit(2, 'GUA'), unit(3, 'LIN'), unit(4, 'STR')]; s.p[1].board = [unit(5, 'STR')]; s.p[0].hand = ['H2']; return s; },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: !acts.some(a => a.t === 'swap' && a.c === 'CROWD'), got: acts }; },
  },
  {
    name: "don't waste: never Hit 6 a 2-health unit while Hit 2 is in hand",
    make() { const s = base(); contracts(s, ['TOWER', 'SPREAD'], ['CROWD', 'MORE']); s.p[0].hand = ['H2', 'H6']; s.p[1].board = [unit(2, 'RAI')]; s.p[0].board = [unit(1, 'GUA', { ready: false })]; return s; },
    ok(s, bot, rng) {
      const { acts } = turnOf(bot, s, rng); let t = s, bad = false;
      for (const a of acts) {
        if (a.t === 'end') break;
        if (a.t === 'play' && a.card === 'H6') { const u = t.p[1].board.find(x => x.uid === a.tgt); if (u && u.hp <= 2 && t.p[0].hand.includes('H2')) bad = true; }
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
