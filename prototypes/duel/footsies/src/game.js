// A family of perfect-information duels. Two fighters on a line, alternate turns,
// everything visible, no luck. Each player holds the same set of moves; a move played
// is spent until all are spent, then all come back ("cycle"). Parameters pick the variant.
//
// Moves (any subset):
//   F  forward 1 (not into the other fighter)
//   B  back 1 (not off the line)
//   J  jab: J dmg at distance <= 2
//   S  strike: S dmg at distance 1; stopped by a raised guard
//   G  guard: until your next turn, the next strike against you is stopped
//   P  push: at distance 1, the other fighter is pushed back 1 (2 if pushPower); into the wall = 1 damage
export function duel(o) {
  const L = o.len ?? 5, HP = o.hp ?? 10, CARDS = o.cards ?? ['F', 'B', 'J', 'S'];
  const J = o.jab ?? 1, S = o.strike ?? 3;
  const FULL = (1 << CARDS.length) - 1;
  const start = o.start ?? [0, L - 1];
  return {
    name: o.name,
    init() { return { pos: start.slice(), hp: [HP, HP], hand: [FULL, FULL], guard: [0, 0], turn: 0, ply: 0 }; },
    toMove: (s) => s.turn,
    moves(s) { const out = []; for (let i = 0; i < CARDS.length; i++) if (s.hand[s.turn] & (1 << i)) out.push(i); return out; },
    play(s, m) {
      const me = s.turn, op = 1 - me;
      const pos = s.pos.slice(), hp = s.hp.slice(), hand = s.hand.slice(), guard = s.guard.slice();
      guard[me] = 0; // my guard lasted until my turn
      const dir = pos[op] > pos[me] ? 1 : -1, dist = Math.abs(pos[op] - pos[me]);
      const c = CARDS[m];
      if (c === 'F' && dist > 1) pos[me] += dir;
      else if (c === 'B') { const n = pos[me] - dir; if (n >= 0 && n < L) pos[me] = n; }
      else if (c === 'J' && dist <= 2) hp[op] -= J;
      else if (c === 'S' && dist === 1) { if (guard[op]) guard[op] = 0; else hp[op] -= S; }
      else if (c === 'G') guard[me] = 1;
      else if (c === 'P' && dist === 1) {
        for (let k = 0; k < (o.pushPower ?? 1); k++) { const n = pos[op] + dir; if (n < 0 || n >= L) { hp[op] -= 1; break; } pos[op] = n; }
      }
      hand[me] &= ~(1 << m);
      if (!hand[me]) hand[me] = FULL;
      return { pos, hp, hand, guard, turn: op, ply: s.ply + 1 };
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= (o.maxPly ?? 200)) return o.timeoutWinner ? (s.hp[0] === s.hp[1] ? 'draw' : s.hp[0] > s.hp[1] ? 0 : 1) : 'draw'; return null; },
    evaluate(s, side) { return 10 * (s.hp[side] - s.hp[1 - side]); },
  };
}

// The game that passed the bot ladder (variant s5): a line of 4 cells, 10 health,
// four moves: Forward, Back, Strike (3 damage at distance 1, stopped by a guard), Guard.
export const GAME = duel({ name: 'Footsies', len: 4, cards: ['F', 'B', 'S', 'G'] });
