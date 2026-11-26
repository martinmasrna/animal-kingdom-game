// Hidden-information duels. Same line and moves as duelkit, but each player has a shuffled
// deck (several copies of each move), holds a hidden hand, plays one card a turn and draws
// one. When the deck is empty the played cards are reshuffled into it. The other player
// sees everything you played, the size of your hand and of your deck, never the cards in them.
// sample(s, side, rng) deals a full state consistent with what `side` can see (for the bots).
function shuffle(rng, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

export function hiddenDuel(o) {
  const L = o.len ?? 4, HP = o.hp ?? 10, H = o.hand ?? 3;
  const DECK = o.deck ?? { F: 3, B: 3, S: 3, G: 3 };
  const S = o.strike ?? 3, J = o.jab ?? 1;
  const list = []; for (const [c, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) list.push(c);
  const KINDS = Object.keys(DECK);
  const clone = (s) => ({ ...s, pos: s.pos.slice(), hp: s.hp.slice(), guard: s.guard.slice(), hand: s.hand.map(h => h.slice()), deck: s.deck.map(d => d.slice()), used: s.used.map(u => u.slice()) });
  function draw(s, side, rng) {
    if (!s.deck[side].length) { s.deck[side] = shuffle(rng || Math.random, s.used[side]); s.used[side] = []; }
    if (s.deck[side].length) s.hand[side].push(s.deck[side].shift());
  }
  const g = {
    name: o.name,
    init(rng) {
      const s = { pos: [0, L - 1], hp: [HP, HP], guard: [0, 0], hand: [[], []], deck: [shuffle(rng, list.slice()), shuffle(rng, list.slice())], used: [[], []], turn: 0, ply: 0, seed: Math.floor(rng() * 2 ** 31) };
      for (const side of [0, 1]) for (let i = 0; i < H; i++) draw(s, side);
      return s;
    },
    toMove: (s) => s.turn,
    moves(s) { return [...new Set(s.hand[s.turn])]; },
    play(s, c) {
      const t = clone(s), me = t.turn, op = 1 - me;
      t.guard[me] = 0;
      const dir = t.pos[op] > t.pos[me] ? 1 : -1, dist = Math.abs(t.pos[op] - t.pos[me]);
      if (c === 'F' && dist > 1) t.pos[me] += dir;
      else if (c === 'B') { const n = t.pos[me] - dir; if (n >= 0 && n < L) t.pos[me] = n; }
      else if (c === 'S' && dist === 1) { if (t.guard[op]) t.guard[op] = 0; else t.hp[op] -= S; }
      else if (c === 'J' && dist <= 2) t.hp[op] -= J;
      else if (c === 'G') t.guard[me] = 1;
      t.hand[me].splice(t.hand[me].indexOf(c), 1);
      t.used[me].push(c);
      // deterministic reshuffle from the state's own seed, so a sampled world stays a fixed world
      let sd = t.seed = (t.seed * 1103515245 + 12345) & 0x7fffffff;
      draw(t, me, () => ((sd = (sd * 1103515245 + 12345) & 0x7fffffff) / 0x80000000));
      t.turn = op; t.ply++;
      return t;
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= (o.maxPly ?? 200)) return 'draw'; return null; },
    evaluate(s, side) { return 10 * (s.hp[side] - s.hp[1 - side]); },
    // A world consistent with side's view: the other hand and both deck orders re-dealt.
    sample(s, side, rng) {
      const t = clone(s), op = 1 - side;
      const pool = shuffle(rng, t.hand[op].concat(t.deck[op]));
      t.hand[op] = pool.slice(0, t.hand[op].length); t.deck[op] = pool.slice(t.hand[op].length);
      t.deck[side] = shuffle(rng, t.deck[side]);
      t.seed = Math.floor(rng() * 2 ** 31);
      return t;
    },
  };
  return g;
}
