// Track: two fighters on a line of 7 cells, 10 health each, alternate turns, everything visible.
// Each player holds the same four moves; a move played is spent until all four are spent,
// then all four come back. Forward 1, Back 1, Jab (1 damage at distance 1 or 2),
// Strike (3 damage at distance 1). A move that can't do anything is still spent.
const L = 7, HP = 10;
const CARDS = ['F', 'B', 'J', 'S'];
const FULL = (1 << CARDS.length) - 1;

export default {
  init() { return { pos: [1, 5], hp: [HP, HP], hand: [FULL, FULL], turn: 0, ply: 0 }; },
  toMove: (s) => s.turn,
  moves(s) { const out = []; for (let i = 0; i < CARDS.length; i++) if (s.hand[s.turn] & (1 << i)) out.push(i); return out; },
  play(s, m) {
    const me = s.turn, op = 1 - me;
    const pos = s.pos.slice(), hp = s.hp.slice(), hand = s.hand.slice();
    const dir = pos[op] > pos[me] ? 1 : -1, dist = Math.abs(pos[op] - pos[me]);
    const c = CARDS[m];
    if (c === 'F' && dist > 1) pos[me] += dir;
    if (c === 'B') { const n = pos[me] - dir; if (n >= 0 && n < L) pos[me] = n; }
    if (c === 'J' && dist <= 2) hp[op] -= 1;
    if (c === 'S' && dist === 1) hp[op] -= 3;
    hand[me] &= ~(1 << m);
    if (!hand[me]) hand[me] = FULL;
    return { pos, hp, hand, turn: op, ply: s.ply + 1 };
  },
  winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= 200) return 'draw'; return null; },
  evaluate(s, side) { return 10 * (s.hp[side] - s.hp[1 - side]); },
};
