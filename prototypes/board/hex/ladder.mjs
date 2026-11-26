// node ladder.mjs [games]: the 70% test. Each bot is the simplest found that beats the one
// below it in at least 70% of games (both seats, same deals for both). Prints every step.
import { newMatch, playAction, endTurn, clone, _play, CARDS, TILES, REGIONS, heldRegions, canPlay } from './src/engine.js';
import { makeRng, evaluate, greedyTurn, rolloutBot } from './src/bot.js';

const N = +(process.argv[2] || 400);

function legal(t) {
  const me = t.turn, out = [];
  for (const id of new Set(t.p[me].hand)) for (let i = 0; i < TILES; i++) if (canPlay(t, id, i)) out.push({ card: id, tile: i });
  return out;
}
const pick = (a, rng) => a[Math.floor(rng() * a.length)];

// Random: every step, a uniform choice among the legal plays and ending the turn.
function randomBot(s, rng) {
  const t = clone(s), moves = [];
  for (;;) {
    const opts = legal(t);
    const k = Math.floor(rng() * (opts.length + 1));
    if (k === opts.length) return moves;
    _play(t, opts[k].card, opts[k].tile); moves.push(opts[k]);
  }
}
// Easy: units only, each on a random empty tile; never strikes; spends what it can.
function easyBot(s, rng) {
  const t = clone(s), moves = [];
  for (;;) {
    const opts = legal(t).filter(m => CARDS[m.card].kind === 'Unit' && !t.board[m.tile]);
    if (!opts.length) return moves;
    const m = pick(opts, rng); _play(t, m.card, m.tile); moves.push(m);
  }
}
// Cluster: Easy, but each unit goes where it touches the most of my units (within a shared triangle).
const NB = Array.from({ length: TILES }, (_, i) => [...new Set(REGIONS.filter(r => r.includes(i)).flat())].filter(j => j !== i));
function clusterBot(s, rng) {
  const t = clone(s), me = t.turn, moves = [];
  for (;;) {
    const opts = legal(t).filter(m => CARDS[m.card].kind === 'Unit' && !t.board[m.tile]);
    if (!opts.length) return moves;
    let best = [], bv = -1;
    for (const m of opts) { const v = NB[m.tile].filter(j => t.board[j] && t.board[j].side === me).length; if (v > bv) { bv = v; best = [m]; } else if (v === bv) best.push(m); }
    const m = pick(best, rng); _play(t, m.card, m.tile); moves.push(m);
  }
}
// Normal: each play is the one that most raises (my held regions − his held regions) right now; ties random.
function normalBot(s, rng) {
  const t = clone(s), me = t.turn, moves = [];
  const score = (x) => heldRegions(x, me).length - heldRegions(x, 1 - me).length;
  for (;;) {
    const opts = legal(t);
    if (!opts.length) return moves;
    let best = [], bv = -Infinity;
    for (const m of opts) { const x = clone(t); _play(x, m.card, m.tile); const v = score(x); if (v > bv) { bv = v; best = [m]; } else if (v === bv) best.push(m); }
    const m = pick(best, rng); _play(t, m.card, m.tile); moves.push(m);
  }
}
// Hard: the region-potential greedy (partial triangles count, health counts a little).
const hardBot = (s) => greedyTurn(s);
const expertBot = rolloutBot(6, 4, 8);

export const BOTS = { random: randomBot, easy: easyBot, cluster: clusterBot, normal: normalBot, hard: hardBot, expert: expertBot };

export function rate(a, b, n = N, seed0 = 5000) {
  let wa = 0, draws = 0;
  for (let g = 0; g < n; g++) {
    const rng = makeRng(seed0 * 7 + g);
    let s = newMatch({ seed: seed0 + (g >> 1) }); // the same deal twice, once from each seat
    const aSide = g % 2;
    while (s.winner === null) {
      const bot = s.turn === aSide ? a : b;
      for (const m of bot(s, rng)) s = playAction(s, m.card, m.tile);
      if (s.winner !== null) break;
      s = endTurn(s);
    }
    if (s.winner === 'draw') draws++; else if (s.winner === aSide) wa++;
  }
  return (wa + draws / 2) / n;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  // every bot against every simpler one: the chain is read off this table
  const order = Object.keys(BOTS);
  for (let i = 1; i < order.length; i++) {
    const row = [];
    for (let j = 0; j < i; j++) row.push(`${order[j]} ${(100 * rate(BOTS[order[i]], BOTS[order[j]])).toFixed(0)}%`);
    console.log(`${order[i].padEnd(8)} vs  ${row.join('  ')}`);
  }
}
