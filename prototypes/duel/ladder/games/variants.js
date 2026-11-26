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
