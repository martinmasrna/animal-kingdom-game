// node sanity.mjs [playouts]: set positions a person never gets wrong, for Greedy and Expert.
// Each asks for the next action (a whole Hunter round for the Search position); Expert runs 5 times.
import { newMatch, act, DIST, ADJ } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

const node = (r, c) => r * 4 + c;
const mask = (...ns) => ns.reduce((m, n) => m | (1 << n), 0);
// seat 0 is the Runner in every position; `as` says whose move it is
function base({ phase, runner, pawns, poss, rHand = ['DASH', 'SLIP', 'DOUB'], hHand = ['SPR', 'SEA', 'BLO'], round = 4 }) {
  const s = newMatch({ seed: 77, seatR: 0 });
  Object.assign(s, { phase, round, runner, pawns, poss, moved: [false, false], cardUsed: false, turn: phase === 'run' ? 0 : 1 });
  s.R.hand = rHand; s.R.energy = 4; s.H.hand = hHand; s.H.energy = 4;
  return s;
}
function hunterRound(bot, s, rng) { const acts = []; let t = s; for (let k = 0; k < 6 && t.winner === null && t.phase === 'hunt'; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); } return { acts, end: t }; }
const POSITIONS = [
  { name: 'Hunter lethal: the Runner was just shown at a corner next to a pawn, both exits covered: move onto it',
    s: () => base({ phase: 'hunt', runner: node(0, 0), pawns: [node(0, 1), node(1, 0)], poss: mask(node(0, 0)) }),
    ok: (s, rng, bot) => act(s, bot(s, rng)).winner === 1 },
  { name: "Runner don't blunder: shown at the centre, pawns two away: never end next to a pawn when a node out of reach exists",
    s: () => base({ phase: 'run', runner: node(1, 1), pawns: [node(3, 1), node(1, 3)], poss: mask(node(1, 1)) }),
    ok: (s, rng, bot) => { const a = bot(s, rng); return Math.min(DIST[s.pawns[0]][a.to], DIST[s.pawns[1]][a.to]) >= 2; } },
  { name: 'free Search: only two nodes possible, both out of every pawn\'s reach, only Searches in hand and energy that would cap anyway: Search one of them this round',
    s: () => base({ phase: 'hunt', runner: node(0, 0), pawns: [node(3, 3), node(3, 2)], poss: mask(node(0, 0), node(0, 3)), hHand: ['SEA', 'SEA'] }),
    ok: (s, rng, bot) => hunterRound(bot, s, rng).acts.some(a => a.card === 'SEA' && [a.node, ...ADJ[a.node]].filter(n => n === node(0, 0) || n === node(0, 3)).length === 1) },
];
export function runSanity({ iters = 1500, quiet = false } = {}) {
  const expert = expertBot({ iters });
  const results = []; let expertPass = true;
  for (const P of POSITIONS) {
    const g = P.ok(P.s(), makeRng(1), greedyBot);
    let e = 0; for (let k = 0; k < 5; k++) if (P.ok(P.s(), makeRng(100 + k), expert)) e++;
    results.push({ position: P.name, greedy: g, expert: `${e}/5` });
    if (e < 5) expertPass = false;
    if (!quiet) console.log(`${e === 5 ? 'ok  ' : 'FAIL'} expert ${e}/5 · greedy ${g ? 'ok' : 'fails'} · ${P.name}`);
  }
  return { results, expertPass };
}
if (import.meta.url === `file://${process.argv[1]}`) { const r = runSanity({ iters: +process.argv[2] || 1500 }); console.log(r.expertPass ? 'all pass' : 'FAILURES'); }
