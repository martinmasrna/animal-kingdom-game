// The smallest deck duel (Toy 7). Two heroes, 10 health. A deck of 6: 3 Strike, 3 Invest.
// Alternate turns. Each turn: draw 2 (reshuffle the discard into an empty deck), play one,
// discard the other. Strike: 1 damage, +1 for each of your Investments on the table.
// Invest: put an Investment on the table; it stays for the rest of the fight.
// Variant `target`: a Strike may hit one of his Investments instead of him; it is destroyed.
function shuffle(rng, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const lcg = (s) => () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

export function minimal(o = {}) {
  const HP = o.hp ?? 10, DRAW = o.draw ?? 2, PLAYS = o.plays ?? 1, DECK = o.deck ?? { S: 3, I: 3 };
  const list = []; for (const [c, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) list.push(c);
  const clone = (s) => ({ ...s, hp: s.hp.slice(), inv: s.inv.slice(), hand: s.hand.map(h => h.slice()), deck: s.deck.map(d => d.slice()), disc: s.disc.map(d => d.slice()) });
  function draw(s, side, n) {
    const r = lcg(s.seed = (s.seed * 1103515245 + 12345) & 0x7fffffff);
    for (let i = 0; i < n; i++) {
      if (!s.deck[side].length) { s.deck[side] = shuffle(r, s.disc[side]); s.disc[side] = []; }
      if (s.deck[side].length) s.hand[side].push(s.deck[side].shift());
    }
  }
  return {
    init(rng) {
      const s = { left: PLAYS, hp: [HP, HP], inv: [0, 0], hand: [[], []], deck: [shuffle(rng, list.slice()), shuffle(rng, list.slice())], disc: [[], []], turn: 0, ply: 0, seed: Math.floor(rng() * 2 ** 31) };
      draw(s, 0, DRAW);
      return s;
    },
    toMove: (s) => s.turn,
    moves(s) {
      const me = s.turn, out = [];
      for (const c of new Set(s.hand[me])) {
        if (c === 'S') { out.push('S'); if (o.target && s.inv[1 - me] > 0) out.push('S>I'); }
        else out.push(c);
      }
      return out;
    },
    play(s, m) {
      const t = clone(s), me = t.turn, op = 1 - me;
      const c = m[0];
      if (m === 'S') t.hp[op] -= 1 + t.inv[me];
      else if (m === 'S>I') t.inv[op] -= 1;
      else if (c === 'I') t.inv[me] += 1;
      t.hand[me].splice(t.hand[me].indexOf(c), 1);
      t.disc[me].push(c);
      t.left--; t.ply++;
      if (t.left > 0 && t.hand[me].length) return t;          // more plays this turn
      t.disc[me].push(...t.hand[me]); t.hand[me] = [];        // the rest is discarded
      t.turn = op; t.left = PLAYS;
      draw(t, op, DRAW);
      return t;
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= 200) return 'draw'; return null; },
    evaluate(s, side) { return (s.hp[side] - s.hp[1 - side]) + (o.invWeight ?? 1.5) * (s.inv[side] - s.inv[1 - side]); },
    sample(s, side, rng) {
      const t = clone(s), op = 1 - side;
      t.deck[side] = shuffle(rng, t.deck[side]);
      const pool = shuffle(rng, t.hand[op].concat(t.deck[op]));
      t.hand[op] = pool.slice(0, t.hand[op].length); t.deck[op] = pool.slice(t.hand[op].length);
      t.seed = Math.floor(rng() * 2 ** 31);
      return t;
    },
  };
}
