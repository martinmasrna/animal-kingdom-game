// Toy 8: Strike or Train. 20 health, deck of 6 (3 Strike, 3 Train). Draw 3, play 1, discard the rest.
// Strike: 1 damage. Train: add a Strike+ (2 damage) to your discard pile. Strike+: 2 damage.
function shuffle(rng, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const lcg = (s) => () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);
export function train(o = {}) {
  const HP = o.hp ?? 20, DRAW = o.draw ?? 3, PLAYS = o.plays ?? 1, DECK = o.deck ?? { S: 3, T: 3 };
  const DMG = { S: 1, P: 2 };
  const list = []; for (const [c, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) list.push(c);
  const clone = (s) => ({ ...s, hp: s.hp.slice(), hand: s.hand.map(h => h.slice()), deck: s.deck.map(d => d.slice()), disc: s.disc.map(d => d.slice()) });
  function draw(s, side, n) {
    const r = lcg(s.seed = (s.seed * 1103515245 + 12345) & 0x7fffffff);
    for (let i = 0; i < n; i++) {
      if (!s.deck[side].length) { s.deck[side] = shuffle(r, s.disc[side]); s.disc[side] = []; }
      if (s.deck[side].length) s.hand[side].push(s.deck[side].shift());
    }
  }
  const owned = (s, side, c) => s.hand[side].concat(s.deck[side], s.disc[side]).filter(x => x === c).length;
  return {
    init(rng) { const s = { left: PLAYS, hp: [HP, HP], hand: [[], []], deck: [shuffle(rng, list.slice()), shuffle(rng, list.slice())], disc: [[], []], turn: 0, ply: 0, seed: Math.floor(rng() * 2 ** 31) }; draw(s, 0, DRAW); return s; },
    toMove: (s) => s.turn,
    moves(s) {
      const h = s.hand[s.turn], out = [];
      for (const c of new Set(h)) {
        if (c !== 'X') { out.push(c); continue; }
        // Thin: remove another card in hand from the deck for good
        const rest = h.slice(); rest.splice(rest.indexOf('X'), 1);
        for (const r of new Set(rest)) out.push('X' + r);
        if (!rest.length) out.push('X'); // nothing else in hand: Thin does nothing
      }
      return out;
    },
    play(s, c) {
      const t = clone(s), me = t.turn, op = 1 - me;
      const card = c[0];
      if (card === 'T') t.disc[me].push('P');
      else if (card === 'X') { t.hand[me].splice(t.hand[me].indexOf('X'), 1); if (c[1]) t.hand[me].splice(t.hand[me].indexOf(c[1]), 1); t.disc[me].push('X'); }
      else t.hp[op] -= DMG[card];
      if (card !== 'X') { t.hand[me].splice(t.hand[me].indexOf(card), 1); t.disc[me].push(card); }
      t.left--; t.ply++;
      if (t.left > 0 && t.hand[me].length) return t;
      t.disc[me].push(...t.hand[me]); t.hand[me] = [];
      t.turn = op; t.left = PLAYS; draw(t, op, DRAW);
      return t;
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= 200) return 'draw'; return null; },
    evaluate(s, side) { return (s.hp[side] - s.hp[1 - side]) + (o.pWeight ?? 1.5) * (owned(s, side, 'P') - owned(s, 1 - side, 'P')); },
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
