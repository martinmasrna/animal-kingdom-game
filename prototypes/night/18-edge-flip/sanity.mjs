// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (five tries
// each for Expert, which is stochastic). sim.mjs runs the same checks into report.json.
import { newMatch, act, edgesOf } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const card = (id, owner, rot = 0) => ({ card: id, rot, e: edgesOf(id, rot), owner });
function base({ hand, mana, cells }) {
  const s = newMatch({ seed: 31, first: 0 });
  s.turn = 0; s.turnNo = 9; s.placed = false; s.passes = 0;
  s.grid = Array(16).fill(null);
  for (const [c, g] of Object.entries(cells)) s.grid[+c] = g;
  s.p[0].hand = hand; s.p[0].mana = s.p[0].maxMana = mana;
  s.p[1].hand = ['POI', 'PAI', 'EVE', 'SPE']; s.p[1].mana = s.p[1].maxMana = 5;
  return s;
}
// the mover's whole turn: its actions until it ends the turn or the game ends
function turnOf(bot, s, rng) {
  let t = s; const acts = [];
  for (let k = 0; k < 12 && t.winner === null && t.turn === 0; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); if (a.t === 'end') break; }
  return { t, acts };
}
export const POSITIONS = [
  {
    // late in the game, so the three cards taken cannot be taken back: the only other empty cell (15) touches none of them
    name: 'free flip: a cell touching three enemy 1-edges and a Crown in hand, nothing left that could take them back: take all three',
    make() {
      const cells = { 1: card('POI', 1), 4: card('POI', 1), 6: card('POI', 1), 9: card('BLO', 0) };
      for (const c of [0, 3, 8, 12, 13]) cells[c] = card('EVE', 0);
      for (const c of [2, 7, 10, 11, 14]) cells[c] = card('EVE', 1);
      return base({ hand: ['CRO', 'POI'], mana: 6, cells });
    },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: [1, 4, 5, 6].every(c => t.grid[c] && t.grid[c].owner === 0), got: acts }; },
  },
  {
    name: 'lethal: the last empty cell decides; place the Spear with its 4 on his 3 (a Point only draws)',
    make() {
      const cells = {};
      const mine = [0, 2, 5, 7, 8, 10, 13], his = [1, 3, 4, 6, 9, 12];
      for (const c of mine) cells[c] = card('EVE', 0);
      for (const c of his) cells[c] = card('EVE', 1);
      cells[11] = card('BLO', 1); cells[14] = card('BLO', 1);
      return base({ hand: ['SPE', 'POI'], mana: 3, cells });
    },
    ok(s, bot, rng) { const { t, acts } = turnOf(bot, s, rng); return { pass: t.winner === 0, got: acts }; },
  },
  {
    name: "don't waste: never a Crown in a sealed corner where a Point takes the same card",
    make() { return base({ hand: ['CRO', 'POI'], mana: 6, cells: { 1: card('EVE', 1), 4: card('BLO', 0) } }); },
    ok(s, bot, rng) { const { acts } = turnOf(bot, s, rng); return { pass: !acts.some(a => a.t === 'place' && a.card === 'CRO' && a.cell === 0), got: acts }; },
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
