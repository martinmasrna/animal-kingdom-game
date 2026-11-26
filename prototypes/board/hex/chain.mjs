// node chain.mjs [games]: the 70% chain as it stands, each bot against the one directly below it,
// then the candidates for a level above Expert. Faster than ladder.mjs's full table.
import { BOTS, rate } from './ladder.mjs';
import { rolloutBot } from './src/bot.js';
const n = +(process.argv[2] || 400);
const steps = [['easy', 'random'], ['cluster', 'easy'], ['normal', 'cluster'], ['hard', 'normal'], ['expert', 'hard'], ['centrePlus', 'expert'], ['big search', 'expert']];
const B = { ...BOTS, 'big search': rolloutBot(12, 24, 30) };
for (const [a, b] of steps) { const t0 = Date.now(); console.log(`${a.padEnd(10)} beats ${b.padEnd(7)} ${(100 * rate(B[a], B[b], a === 'big search' ? n / 2 : n)).toFixed(1)}%  (${((Date.now() - t0) / 1000).toFixed(0)}s)`); }
