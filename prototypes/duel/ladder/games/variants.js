import { duel } from './duelkit.js';
// Candidate rule sets. Each is a full game; see duelkit.js for what the moves do.
export const variants = {
  v1: duel({ len: 4, cards: ['F', 'B', 'J', 'S'] }),
  v2: duel({ len: 5, cards: ['F', 'J', 'S'] }),
  v3: duel({ len: 5, cards: ['F', 'B', 'J', 'S', 'G'] }),
  v4: duel({ len: 4, cards: ['F', 'B', 'J', 'S', 'G', 'P'] }),
  v5: duel({ len: 5, cards: ['F', 'B', 'J', 'S'], timeoutWinner: true, maxPly: 60 }),
  v6: duel({ len: 5, cards: ['F', 'B', 'J', 'S', 'G'], timeoutWinner: true, maxPly: 60 }),
  v7: duel({ len: 5, cards: ['F', 'B', 'J', 'S', 'G', 'P'], timeoutWinner: true, maxPly: 60 }),
};
export const more = {
  s1: duel({ len: 4, cards: ['F', 'B', 'S'] }),
  s2: duel({ len: 4, cards: ['F', 'B', 'J', 'S'], hp: 6 }),
  s3: duel({ len: 3, cards: ['F', 'B', 'J', 'S'] }),
  s4: duel({ len: 5, cards: ['F', 'B', 'S', 'G'] }),
  s5: duel({ len: 4, cards: ['F', 'B', 'S', 'G'] }),
  s6: duel({ len: 4, cards: ['F', 'B', 'J', 'S', 'G'] }),
};
Object.assign(variants, more);
import { hiddenDuel } from './hiddenkit.js';
Object.assign(variants, {
  h1: hiddenDuel({ len: 4, deck: { F: 3, B: 3, S: 3, G: 3 }, hand: 3 }),
  h2: hiddenDuel({ len: 4, deck: { F: 3, B: 3, S: 3, G: 3 }, hand: 4 }),
  h3: hiddenDuel({ len: 5, deck: { F: 3, B: 3, J: 3, S: 3, G: 3 }, hand: 3 }),
  h4: hiddenDuel({ len: 4, deck: { F: 2, B: 2, S: 2, G: 2 }, hand: 3 }),
});
import { minimal } from './minimal.js';
Object.assign(variants, {
  m0: minimal({}),                 // investments can't be removed
  m1: minimal({ target: true }),   // a Strike may destroy one of his investments instead
});
Object.assign(variants, {
  m1d3: minimal({ target: true, draw: 3 }),
  m1d3h20: minimal({ target: true, draw: 3, hp: 20 }),
  m1d4p2: minimal({ target: true, draw: 4, plays: 2 }),
  m1d4p2h20: minimal({ target: true, draw: 4, plays: 2, hp: 20 }),
});
import { train } from './train.js';
Object.assign(variants, { t8: train({}) });
Object.assign(variants, {
  t8a: train({ draw: 4, plays: 2 }),
  t8b: train({ deck: { S: 2, T: 2, X: 2 } }),
  t8ab: train({ draw: 4, plays: 2, deck: { S: 2, T: 2, X: 2 } }),
});
import { sr, ruleBot, planBot, rolloutBot } from './sr.js';
Object.assign(variants, { sr30: sr({ hp: 30 }), sr40: sr({ hp: 40 }), sr50: sr({ hp: 50 }) });
for (const k of ['sr30', 'sr40', 'sr50']) variants[k].bots = { rule: ruleBot, plan: planBot, roll: rolloutBot(300), roll30: rolloutBot(30) };
