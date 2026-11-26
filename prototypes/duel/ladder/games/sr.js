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
    winner(s) { if (s.hp[0] <= 0) return 1; if (s.hp[1] <= 0) return 0; if (s.ply >= (o.maxTurns ?? 400)) return 'draw'; return null; },
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

// ---------------------------------------------------------------------------------------------
// Bots made for this game (a skill ladder that fits a deckbuilder):
//   rule    : buy the most expensive card you can afford, never scrap, always hit his face.
//   plan    : a sensible strategy: scrap Scouts then Vipers; early on buy economy, later combat;
//             Outposts at 4; always destroy his Outposts when you can, the rest at his face.
//   rollout : for each possible decision, play the rest of the match out many times with `plan`
//             on both sides (deck orders re-dealt from what it can see) and take the decision
//             that wins most often. Time-boxed.
const turnNo = (s) => Math.floor(s.ply / 2);
export function ruleBot(g, s) {
  const ms = g.moves(s);
  if (s.phase === 'scrap') return 'X-';
  if (s.phase === 'buy') { const buys = ms.filter(m => m !== 'B-').sort((a, b) => CARD[b[1]].cost - CARD[a[1]].cost); return buys[0] || 'B-'; }
  return 'A-';
}
export function planBot(g, s) {
  const me = s.turn, ms = g.moves(s);
  if (s.phase === 'scrap') {
    for (const c of ['C', 'V']) if (ms.includes('X' + c)) return 'X' + c;
    return 'X-';
  }
  if (s.phase === 'buy') {
    const all = s.hand[me].concat(s.deck[me], s.disc[me]);
    const n = (c) => all.filter(x => x === c).length;
    const can = (c) => ms.includes('B' + c);
    const early = turnNo(s) < 5;
    if (can('H')) return 'BH';
    if (can('O') && n('O') + s.bases[me] < 2) return 'BO';
    if (can('X') && early && n('X') < 2) return 'BX';
    if (can('E') && early && n('E') < 3) return 'BE';
    if (can('F')) return 'BF';
    return 'B-';
  }
  if (ms.includes('AO')) return 'AO';
  return 'A-';
}
export function rolloutBot(ms = 300) {
  return (g, s, rng) => {
    const side = g.toMove(s), opts = g.moves(s);
    if (opts.length === 1) return opts[0];
    const deadline = Date.now() + ms;
    const score = new Map(opts.map(m => [m, 0])), n = new Map(opts.map(m => [m, 0]));
    let i = 0;
    while (Date.now() < deadline || i < opts.length * 4) {
      const m = opts[i++ % opts.length];
      let t = g.play(g.sample(s, side, rng), m);
      let guard = 0;
      while (g.winner(t) === null && guard++ < 3000) t = g.play(t, planBot(g, t));
      const w = g.winner(t);
      const v = w === side ? 1 : w === 'draw' || w === null ? 0.5 : 0;
      score.set(m, score.get(m) + v + 0.001 * (t.hp[side] - t.hp[1 - side]));
      n.set(m, n.get(m) + 1);
      if (i > 4000) break;
    }
    let best = opts[0], bv = -Infinity;
    for (const m of opts) { const v = score.get(m) / Math.max(1, n.get(m)); if (v > bv) { bv = v; best = m; } }
    return best;
  };
}

// Probe strategies: buy only Fighters (as many as trade allows), never scrap; hit face, or break bases first.
export function fighterFace(g, s) {
  if (s.phase === 'scrap') return 'X-';
  if (s.phase === 'buy') return g.moves(s).includes('BF') ? 'BF' : 'B-';
  return 'A-';
}
export function fighterBase(g, s) {
  if (s.phase === 'scrap') return 'X-';
  if (s.phase === 'buy') return g.moves(s).includes('BF') ? 'BF' : 'B-';
  return g.moves(s).includes('AO') ? 'AO' : 'A-';
}
export function econBot(g, s) {
  const me = s.turn, ms = g.moves(s);
  if (s.phase === 'scrap') { for (const c of ['C', 'V']) if (ms.includes('X' + c)) return 'X' + c; return 'X-'; }
  if (s.phase === 'buy') {
    const all = s.hand[me].concat(s.deck[me], s.disc[me]);
    const n = (c) => all.filter(x => x === c).length;
    if (ms.includes('BH')) return 'BH';
    if (ms.includes('BX') && n('X') < 2) return 'BX';
    if (ms.includes('BE') && n('E') < 4) return 'BE';
    return 'B-';
  }
  return 'A-';
}
export function outpostBot(g, s) {
  const ms = g.moves(s);
  if (s.phase === 'scrap') return 'X-';
  if (s.phase === 'buy') { if (ms.includes('BO')) return 'BO'; if (ms.includes('BE')) return 'BE'; return 'B-'; }
  return ms.includes('AO') ? 'AO' : 'A-';
}
