// Toy 10: a fight between two fixed decks where my turn changes his options.
// Each turn: draw DRAW, play up to PLAYS cards, discard the rest (reshuffle an empty deck).
// Cards:
//   S Strike : 1 damage.
//   C Cut    : put a Wound into his discard pile.
//   B Bandage: remove a Wound in your hand or discard pile from your deck for good (if any).
//   T Stagger: he plays 1 card fewer next turn.
//   W Wound  : does nothing; it only takes up a slot in your hand.
function shuffle(rng, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const lcg = (s) => () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

export function fight(o = {}) {
  const HP = o.hp ?? 15, DRAW = o.draw ?? 4, PLAYS = o.plays ?? 2, DECK = o.deck ?? { S: 4, C: 3, B: 3 };
  const list = []; for (const [c, k] of Object.entries(DECK)) for (let i = 0; i < k; i++) list.push(c);
  const clone = (s) => ({ ...s, hp: s.hp.slice(), stag: s.stag.slice(), hand: s.hand.map(h => h.slice()), deck: s.deck.map(d => d.slice()), disc: s.disc.map(d => d.slice()) });
  function draw(s, side, n) {
    const r = lcg(s.seed = (s.seed * 1103515245 + 12345) & 0x7fffffff);
    for (let i = 0; i < n; i++) {
      if (!s.deck[side].length) { s.deck[side] = shuffle(r, s.disc[side]); s.disc[side] = []; }
      if (s.deck[side].length) s.hand[side].push(s.deck[side].shift());
    }
  }
  // Stagger costs the victim a play next turn; the very first turn of the match has FIRST plays.
  function begin(s) { const me = s.turn; draw(s, me, DRAW); s.left = Math.max(0, (s.ply === 0 ? (o.first ?? PLAYS) : PLAYS) - s.stag[me]); s.stag[me] = 0; if (s.left === 0) { s.disc[me].push(...s.hand[me]); s.hand[me] = []; s.turn = 1 - me; s.ply++; begin(s); } }
  function end(s) { const me = s.turn; s.disc[me].push(...s.hand[me]); s.hand[me] = []; s.turn = 1 - me; s.ply++; begin(s); }
  const g = {
    init(rng) { const s = { hp: [HP, HP], stag: [0, 0], hand: [[], []], deck: [shuffle(rng, list.slice()), shuffle(rng, list.slice())], disc: [[], []], turn: 0, ply: 0, left: PLAYS, seed: Math.floor(rng() * 2 ** 31) }; begin(s); return s; },
    toMove: (s) => s.turn,
    moves(s) { return [...new Set(s.hand[s.turn].filter(c => c !== 'W'))].concat(['-']); },
    play(s, c) {
      const t = clone(s), me = t.turn, op = 1 - me;
      if (c === '-') { end(t); return t; }
      t.hand[me].splice(t.hand[me].indexOf(c), 1);
      t.disc[me].push(c);
      if (c === 'S') t.hp[op] -= 1;
      else if (c === 'C') t.disc[op].push('W');
      else if (c === 'T') t.stag[op] += 1;
      else if (c === 'B') { let i = t.hand[me].indexOf('W'); if (i >= 0) t.hand[me].splice(i, 1); else { i = t.disc[me].indexOf('W'); if (i >= 0) t.disc[me].splice(i, 1); } }
      if (t.hp[op] <= 0) return t;
      t.left--;
      if (t.left <= 0 || !t.hand[me].some(x => x !== 'W')) end(t);
      return t;
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= (o.maxTurns ?? 300)) return 'draw'; return null; },
    evaluate(s, side) {
      const wounds = (q) => s.hand[q].concat(s.deck[q], s.disc[q]).filter(x => x === 'W').length;
      return (s.hp[side] - s.hp[1 - side]) + (o.wWeight ?? 0.7) * (wounds(1 - side) - wounds(side)) + 0.5 * (s.stag[1 - side] - s.stag[side]);
    },
    sample(s, side, rng) { const t = clone(s); for (const q of [0, 1]) t.deck[q] = shuffle(rng, t.deck[q]); t.seed = Math.floor(rng() * 2 ** 31); return t; },
  };
  // probe strategies and bots made for this game
  const pick = (pref) => (gg, s) => { const ms = gg.moves(s); for (const c of pref) if (ms.includes(c)) return c; return '-'; };
  g.bots = {
    strikeFirst: pick(['S', 'C', 'T', 'B']),
    cutFirst: pick(['C', 'S', 'T', 'B']),
    staggerFirst: pick(['T', 'S', 'C', 'B']),
    healFirst: (gg, s) => (s.hand[s.turn].includes('W') && gg.moves(s).includes('B') ? 'B' : pick(['S', 'C', 'T', 'B'])(gg, s)),
  };
  return g;
}
