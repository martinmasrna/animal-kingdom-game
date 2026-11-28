// node sanity.mjs: set positions a person never gets wrong (break a Key when he holds all three,
// take a free trade, never Fetch a Key already held while another is missing), for Greedy and
// Expert. Expert is asked on five different seeds and must pass every one.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ hand = [], mana = 4, mine = [], his = [], deck = null, first = 0 }) {
  const s = newMatch({ seed: 31, first });
  s.turnNo = 2 * mana - 1 + first; s.toAct = 0;
  s.p[0].hand = hand.slice(); s.p[0].mana = s.p[0].maxMana = mana; s.p[1].maxMana = mana;
  if (deck) s.p[0].deck = deck.slice();
  let uid = 9000;
  const mk = (x) => { const [id, hp] = Array.isArray(x) ? x : [x]; return { uid: uid++, card: id, atk: CARDS[id].atk, hp: hp ?? CARDS[id].hp, max: CARDS[id].hp, ready: true }; };
  s.p[0].board = mine.map(mk); s.p[1].board = his.map(mk);
  return s;
}
function turnOf(bot, s, rng) {
  let t = s; const acts = [];
  for (let k = 0; k < 40 && t.winner === null && t.toAct === s.toAct; k++) {
    const a = bot(t, rng); acts.push(a);
    if (a.t === 'end') return { acts, before: t, after: act(t, a) };
    t = act(t, a);
  }
  return { acts, before: t, after: t };
}
const show = (s, acts) => acts.map(a => a.t === 'play' ? 'play ' + CARDS[a.card].name + (a.key ? ' (' + CARDS[a.key].name + ')' : '') + (a.tgt ? '→' + a.tgt.uid : '') : a.t === 'attack' ? `attack ${a.from}→${a.to}` : 'end').join(', ');

const POSITIONS = [
  { name: 'deny: he holds Key A (3 health), B and C; I hold Hit 3 with 2 mana: break Key A',
    make: () => base({ hand: ['H3', 'STR'], mana: 2, mine: [], his: ['KA', 'KB', 'KC', 'GRD'] }),
    ok: (r) => r.after.winner === null && r.after.p[1].board.filter(u => CARDS[u.card].kind === 'key').length < 3 },
  // (with no Keys anywhere the trade changes nothing: 79.5% against 80.1% over 1,500 full play-outs,
  // the deck-out order decides that position; here the Raider stands between me and three Keys)
  { name: 'free trade: I am second, hold Keys A and B and Key C in hand (3 mana); my ready Line against his Raider, which threatens Key A: attack it',
    make: () => base({ hand: ['KC', 'STR'], mana: 3, mine: ['LIN', 'KA', 'KB'], his: ['RAI'], first: 1 }),
    ok: (r) => r.acts.some(a => a.t === 'attack' && a.to === 9003) }, // his Raider is uid 9003
  { name: "don't waste: I hold Key A, Fetch in hand, Keys A, B and C in my deck: never Fetch Key A",
    make: () => base({ hand: ['FET'], mana: 2, mine: ['KA'], deck: ['STR', 'KA', 'KB', 'KC', 'LIN', 'RAI', 'HEV', 'GRD', 'H3', 'STR'] }),
    ok: (r) => !r.acts.some(a => a.card === 'FET' && a.key === 'KA') },
];

export function runSanity(seeds = 5) {
  const expert = expertBot(EXPERT), out = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, seeds]]) {
      let passed = 0, ex = '', bad = '';
      for (let k = 0; k < n; k++) { const s = P.make(), r = turnOf(bot, s, makeRng(100 + k)); if (P.ok(r)) passed++; else if (!bad) bad = show(s, r.acts); if (k === 0) ex = show(s, r.acts); }
      out.push({ position: P.name, bot: bn, pass: passed === n, passed, of: n, example: bad || ex });
    }
  }
  return out;
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const res = runSanity();
  for (const r of res) console.log(`${r.pass ? 'ok  ' : 'FAIL'} ${r.bot.padEnd(6)} ${r.passed}/${r.of} ${r.position}: ${r.example}`);
  const bad = res.filter(r => r.bot === 'expert' && !r.pass).length;
  console.log(bad ? bad + ' Expert failures' : 'Expert passes every set position');
}
