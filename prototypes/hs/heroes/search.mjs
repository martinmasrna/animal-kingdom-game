// node search.mjs [rounds] [deals] [minutes]: hill-climb the three default decks with Greedy.
// Each step tries one-copy swaps (one card out, another in) for one hero, scores each against
// the other two heroes' current decks on the same deals (both seats), re-checks the best on fresh
// deals and keeps it if it still beats the current list. Writes search-result.json.
import { writeFileSync } from 'node:fs';
import { DEFAULT_DECKS, HERO_IDS, POOL, COPIES } from './src/engine.js';
import { runAll, pairingGames, summarize } from './sim.mjs';
import { makeRng } from './src/bot.js';

const ROUNDS = +(process.argv[2] || 3), N = +(process.argv[3] || 150), MINUTES = +(process.argv[4] || 20);
const STEPS = 4, CANDS = 36, t0 = Date.now();
const late = () => Date.now() - t0 > MINUTES * 60e3;
const rng = makeRng(42);
const decks = Object.fromEntries(HERO_IDS.map(h => [h, DEFAULT_DECKS[h].slice()]));
async function score(h, deck, seed) {
  let games = [];
  for (const o of HERO_IDS) if (o !== h) games = games.concat(pairingGames(h, deck, o, decks[o], N, seed));
  return summarize(games, await runAll(games)).a;
}
function swaps(deck) {
  const out = [], ids = POOL.map(c => c.id);
  for (let k = 0; k < CANDS; k++) {
    const d = deck.slice(), i = Math.floor(rng() * d.length);
    const opts = ids.filter(id => id !== d[i] && d.filter(x => x === id).length < COPIES);
    d[i] = opts[Math.floor(rng() * opts.length)];
    out.push(d.sort());
  }
  return out;
}
const diff = (a, b) => { const n = {}; for (const x of b) n[x] = (n[x] || 0) + 1; return a.filter(x => !(n[x]-- > 0)); };
let seed = 100000;
for (let r = 0; r < ROUNDS && !late(); r++) for (const h of HERO_IDS) {
  let cur = await score(h, decks[h], seed);
  for (let st = 0; st < STEPS && !late(); st++) {
    seed += 1000;
    const cands = swaps(decks[h]), base = await score(h, decks[h], seed);
    let best = null, bv = base;
    for (const d of cands) { const v = await score(h, d, seed); if (v > bv) { bv = v; best = d; } }
    if (!best) break;
    // fresh deals for the winner and the current list, against the winner's curse
    seed += 1000;
    const vb = await score(h, best, seed), vc = await score(h, decks[h], seed);
    if (vb <= vc) { console.log(`round ${r + 1} ${h}: best swap did not hold (${(100 * vb).toFixed(1)} vs ${(100 * vc).toFixed(1)})`); continue; }
    console.log(`round ${r + 1} ${h}: ${(100 * vc).toFixed(1)} -> ${(100 * vb).toFixed(1)}  out ${diff(decks[h], best)} in ${diff(best, decks[h])}`);
    decks[h] = best; cur = vb;
  }
  writeFileSync(new URL('search-result.json', import.meta.url), JSON.stringify(decks, null, 1));
}
for (const h of HERO_IDS) console.log(h, JSON.stringify(decks[h]));
console.log('minutes', ((Date.now() - t0) / 60e3).toFixed(1));
