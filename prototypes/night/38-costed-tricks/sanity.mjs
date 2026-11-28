// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot makes one play from the position (or, for lethal, plays out the rest of the hand
// against Greedy); Expert is tried with several seeds.
import { newMatch, act, key, deckList } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
// hand 1 (trump A), trick 3 of 8, seat 1 to play; hands set by the test
function base({ mine, his, trick = 2, prizes = [1, 1, 2, 2, 3, 1, 3, 2], energy = 6 }) {
  const s = newMatch({ seed: 41, first: 0 });
  s.trick = trick; s.prizes = prizes.slice(); s.trump = 'A';
  s.p[1].hand = mine.slice(); s.p[0].hand = his.slice();
  for (const k of [0, 1]) { const p = s.p[k]; p.rest = deckList().filter(c => !p.hand.includes(c)); p.energy = energy; p.seen = []; p.voids = []; }
  s.p[0].score = 3; s.p[1].score = 3;
  return s;
}
let bad = 0;
function check(name, mk, ok, whole = false) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) {
      const s = mk(), rng = makeRng(100 + k), acts = [];
      let t = s;
      do { const a = t.toMove === 1 ? b(t, rng) : greedyBot(t, rng); if (t.toMove === 1) acts.push(a); t = act(t, a); } while (whole && t.winner === null && t.hand === s.hand);
      if (ok(acts, t)) pass++; else sample = acts.map(key).join(' ');
    }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
// 1. free trick: he led face-down to a 2-point trick; a free face-up card (C1) takes it
check('free trick: answer a face-down lead with a free card', () => {
  const s = base({ mine: ['C1', 'B6', 'A5', 'D3', 'C4', 'B2'], his: ['A6', 'B5', 'C3', 'D4', 'D2', 'D1'] });
  s.leader = 0; s.toMove = 0; return act(s, { t: 'play', card: 'D1', up: false });
}, (acts) => acts[0].up && ['C1', 'B2'].includes(acts[0].card));
// 2. don't overpay: he led B3 face-up to a 2-point trick; B4 (1) and B6 (3) both take it
check('two cards win: play the cheaper', () => {
  const s = base({ mine: ['B4', 'B6', 'A2', 'C5', 'D1', 'C2'], his: ['A6', 'C6', 'D5', 'B1', 'D6'] });
  s.p[0].hand.push('B3'); s.leader = 0; s.toMove = 0; return act(s, { t: 'play', card: 'B3', up: true });
}, (acts) => acts[0].card === 'B4');
// 3. lethal: I am on 18, he on 10; I lead the next-to-last trick, worth 2, holding the top trump
//    A6 and energy for it; leading it face-up takes the trick and the match
check('on 18: lead the top trump to the 2-point trick', () => {
  const s = base({ mine: ['A6', 'C1'], his: ['A5', 'B6'], trick: 6, prizes: [1, 1, 2, 2, 3, 1, 2, 3], energy: 3 });
  s.p[1].score = 18; s.p[0].score = 10; s.leader = 1; s.toMove = 1; return s;
}, (acts, end) => end.winner === 1, true);
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
