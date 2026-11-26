// Stripped-down Star Realms (Toy 9). Numbers from Star Realms, from memory.
// Start deck: 8 Scout (+1 trade), 2 Viper (+1 combat). Draw 5 (the very first turn: 3).
// Play the whole hand for free: trade and combat pools. Then, as separate decisions:
//   each Scrapper in hand: remove one card in hand or discard pile from the deck for good (or none);
//   buy any number of affordable market cards (they go to the discard pile);
//   split combat: destroy one of his Outposts for 5 combat (repeatable), rest to his health.
// Market: Explorer 2 (+2 trade), Fighter 2 (+3 combat), Heavy 5 (+6 combat),
//         Scrapper 3 (+1 trade, scrap one card), Outpost 4 (base, defense 5, +2 combat every turn).
function shuffle(rng, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const lcg = (s) => () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x80000000);

export const CARD = {
  C: { name: 'Scout', trade: 1, combat: 0 },
  V: { name: 'Viper', trade: 0, combat: 1 },
  E: { name: 'Explorer', cost: 2, trade: 2, combat: 0 },
  F: { name: 'Fighter', cost: 2, trade: 0, combat: 3 },
  H: { name: 'Heavy', cost: 5, trade: 0, combat: 6 },
  X: { name: 'Scrapper', cost: 3, trade: 1, combat: 0 },
  O: { name: 'Outpost', cost: 4, trade: 0, combat: 0, base: true },
};
const MARKET = ['E', 'F', 'H', 'X', 'O'];
const BASE_DEF = 5, BASE_COMBAT = 2;

export function sr(o = {}) {
  const HP = o.hp ?? 50;
  const start = []; for (let i = 0; i < 8; i++) start.push('C'); start.push('V', 'V');
  const clone = (s) => ({ ...s, hp: s.hp.slice(), bases: s.bases.slice(), hand: s.hand.map(h => h.slice()), deck: s.deck.map(d => d.slice()), disc: s.disc.map(d => d.slice()) });
  function draw(s, side, n) {
    const r = lcg(s.seed = (s.seed * 1103515245 + 12345) & 0x7fffffff);
    for (let i = 0; i < n; i++) {
      if (!s.deck[side].length) { s.deck[side] = shuffle(r, s.disc[side]); s.disc[side] = []; }
      if (s.deck[side].length) s.hand[side].push(s.deck[side].shift());
    }
  }
  // start of a turn: draw, play everything (Outposts go onto the table), set pools and scraps
  function begin(s, n) {
    const me = s.turn;
    draw(s, me, n);
    let trade = 0, combat = 0, scraps = 0;
    const keep = [];
    for (const c of s.hand[me]) {
      if (CARD[c].base) { s.bases[me]++; continue; }
      trade += CARD[c].trade; combat += CARD[c].combat; if (c === 'X') scraps++;
      keep.push(c);
    }
    s.hand[me] = keep;
    combat += BASE_COMBAT * s.bases[me];
    s.trade = trade; s.combat = combat; s.scraps = scraps; s.phase = scraps ? 'scrap' : 'buy';
  }
  function end(s) {
    const me = s.turn;
    s.disc[me].push(...s.hand[me]); s.hand[me] = [];
    s.turn = 1 - me; s.ply++;
    begin(s, 5);
  }
  return {
    init(rng) {
      const s = { hp: [HP, HP], bases: [0, 0], hand: [[], []], deck: [shuffle(rng, start.slice()), shuffle(rng, start.slice())], disc: [[], []], turn: 0, ply: 0, seed: Math.floor(rng() * 2 ** 31) };
      begin(s, 3);
      return s;
    },
    toMove: (s) => s.turn,
    moves(s) {
      const me = s.turn;
      if (s.phase === 'scrap') {
        const pool = new Set(s.hand[me].concat(s.disc[me]));
        return ['X-'].concat([...pool].map(c => 'X' + c));
      }
      if (s.phase === 'buy') return MARKET.filter(c => CARD[c].cost <= s.trade).map(c => 'B' + c).concat(['B-']);
      // attack
      const out = ['A-'];
      if (s.bases[1 - me] > 0 && s.combat >= BASE_DEF) out.push('AO');
      return out;
    },
    play(s, m) {
      const t = clone(s), me = t.turn, op = 1 - me;
      if (m[0] === 'X') {
        if (m !== 'X-') {
          const c = m[1];
          const i = t.hand[me].indexOf(c);
          if (i >= 0) t.hand[me].splice(i, 1);
          else t.disc[me].splice(t.disc[me].indexOf(c), 1);
        }
        t.scraps--; if (t.scraps <= 0) t.phase = 'buy';
        return t;
      }
      if (m[0] === 'B') {
        if (m === 'B-') { t.phase = 'attack'; return t; }
        const c = m[1]; t.trade -= CARD[c].cost; t.disc[me].push(c);
        return t;
      }
      // attack
      if (m === 'AO') { t.combat -= BASE_DEF; t.bases[op]--; t.disc[op].push('O'); return t; }
      t.hp[op] -= t.combat; t.combat = 0;
      if (t.hp[op] <= 0) return t;
      end(t);
      return t;
    },
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= 120) return 'draw'; return null; },
    evaluate(s, side) {
      const inc = (q) => {
        const all = s.hand[q].concat(s.deck[q], s.disc[q]);
        let t = 0, c = 0; for (const x of all) { if (CARD[x].base) { c += 1.5; continue; } t += CARD[x].trade; c += CARD[x].combat; }
        return 5 * (0.8 * t + c) / Math.max(1, all.length) + BASE_COMBAT * s.bases[q];
      };
      return (s.hp[side] - s.hp[1 - side]) + 3 * (inc(side) - inc(1 - side));
    },
    sample(s, side, rng) {
      const t = clone(s);
      for (const q of [0, 1]) t.deck[q] = shuffle(rng, t.deck[q]);
      t.seed = Math.floor(rng() * 2 ** 31);
      return t;
    },
  };
}
