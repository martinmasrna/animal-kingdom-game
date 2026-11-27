// Bot-vs-bot games for the numbers and the deck search. playGame is one game; runAll() plays a list of them
// split over worker threads; pairingGames() lays out a pairing on both seats of the same deals.
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';
import { cpus } from 'node:os';
import { newMatch, _act, _endTurn, WIN, CARDS } from './src/engine.js';
import { makeRng, greedyBot, rolloutBot } from './src/bot.js';

export const BOTS = { greedy: () => greedyBot, expert: () => rolloutBot() };
// 'x:TOPN:R:DEPTH' is an Expert with other settings, for tuning
const bot = (name) => name.startsWith('x:') ? rolloutBot(...name.split(':').slice(1).map(Number)) : BOTS[name]();

// One game: side 0 plays hero h0 with deck d0 and bot b0. Returns the winner, how and the length.
export function playGame({ seed, first, heroes, decks, bots }) {
  const rng = makeRng(seed * 7 + 1), B = bots.map(bot);
  const s = newMatch({ seed, first, heroes, decks });
  let maxMs = 0;
  while (s.winner === null) {
    const t0 = Date.now();
    const acts = B[s.turn](s, rng);
    maxMs = Math.max(maxMs, Date.now() - t0);
    for (const a of acts) { _act(s, a); if (s.winner !== null) break; }
    if (s.winner !== null) break;
    _endTurn(s);
  }
  const how = s.winner === 'draw' ? 'draw' : s.p[s.winner].energy >= WIN ? 'gain' : 'kill';
  const sides = s.p.map(p => ({ hero: p.hero, heroCard: p.played.some(id => CARDS[id].hero), uses: p.uses, fatigue: p.fatigue, fire: p.played.filter(id => CARDS[id].fire !== undefined).map(id => CARDS[id].dmg) }));
  return { winner: s.winner, how, turns: s.turnNo, first: s.first, maxMs, sides };
}

// games: a list of playGame arguments. Runs them over the cores; resolves to the results in order.
export function runAll(games, threads = Math.max(1, cpus().length - 1)) {
  if (games.length < 40) return Promise.resolve(games.map(playGame));
  const chunks = Array.from({ length: threads }, () => []);
  games.forEach((g, i) => chunks[i % threads].push([i, g]));
  return Promise.all(chunks.filter(c => c.length).map(c => new Promise((res, rej) => {
    const w = new Worker(new URL(import.meta.url), { workerData: c });
    w.on('message', res); w.on('error', rej);
  }))).then(parts => { const out = []; for (const p of parts) for (const [i, r] of p) out[i] = r; return out; });
}
if (!isMainThread) parentPort.postMessage(workerData.map(([i, g]) => [i, playGame(g)]));

// A pairing on n deals, each played from both seats: hero A on side 0 then on side 1.
export function pairingGames(hA, dA, hB, dB, n, seed0 = 1, bot = 'greedy') {
  const out = [];
  for (let k = 0; k < n; k++) for (const aSide of [0, 1]) {
    const heroes = aSide === 0 ? [hA, hB] : [hB, hA], decks = aSide === 0 ? [dA, dB] : [dB, dA];
    out.push({ seed: seed0 + k, first: k % 2, heroes, decks, bots: [bot, bot], aSide });
  }
  return out;
}
export function summarize(games, results) {
  let a = 0, draws = 0, turns = 0, gain = 0, kill = 0, firstWins = 0, maxMs = 0;
  results.forEach((r, i) => {
    const g = games[i];
    if (r.winner === 'draw') draws++; else { if (r.winner === g.aSide) a++; if (r.winner === r.first) firstWins++; }
    turns += r.turns; if (r.how === 'gain') gain++; if (r.how === 'kill') kill++; maxMs = Math.max(maxMs, r.maxMs);
  });
  const n = results.length;
  return { n, a: (a + draws / 2) / n, draws: draws / n, turns: turns / n / 2, gain: gain / n, kill: kill / n, first: firstWins / (n - draws || 1), maxMs };
}
