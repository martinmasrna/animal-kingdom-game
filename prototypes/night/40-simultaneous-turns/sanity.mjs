// node sanity.mjs: set positions a person never gets wrong (lethal when nothing can stop it, a free
// trade, no Hit 6 on a 2-health unit with Hit 2 in hand), for Greedy and Expert. Expert is asked
// on five different seeds and must pass every one. Seat 0 plans; seat 1 is the opponent.
import { newMatch, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ hand = [], mana = 5, mine = [], his = [], hisHand = [], myLife = 20, hisLife = 20 }) {
  const s = newMatch({ seed: 21 });
  s.round = mana; s.toAct = 0; s.plans = [null, null];
  s.p[0].hand = hand.slice(); s.p[0].mana = mana; s.p[0].life = myLife;
  s.p[1].hand = hisHand.slice(); s.p[1].mana = mana; s.p[1].life = hisLife;
  let uid = 9000;
  const mk = (id) => ({ uid: uid++, card: id, atk: CARDS[id].atk, hp: CARDS[id].hp, max: CARDS[id].hp, ready: true });
  s.p[0].board = mine.map(mk); s.p[1].board = his.map(mk);
  return s;
}
const show = (s, pl) => {
  const name = (side, uid) => uid === -1 ? (side === 1 ? 'him' : 'me') : CARDS[s.p[side].board.find(u => u.uid === uid).card].name;
  return [...pl.plays.map(x => CARDS[x.card].name + (x.tgt ? '→' + name(x.tgt.side, x.tgt.uid) : '')), ...pl.attacks.map(a => CARDS[s.p[0].board.find(u => u.uid === a.from).card].name + '→' + name(1, a.to))].join(', ') || '(nothing)';
};
const POSITIONS = [
  { name: 'lethal: he is on 4 with an empty hand and a Line; my two ready Raiders go at him',
    make: () => base({ hand: ['GRD'], mana: 4, mine: ['RAI', 'RAI'], his: ['LIN'], hisLife: 4 }),
    ok: (s, pl) => pl.attacks.length === 2 && pl.attacks.every(a => a.to === -1) },
  { name: 'free trade: my ready Heavy against his Raider, his hand empty: attack it',
    make: () => base({ hand: [], mana: 4, mine: ['HEV'], his: ['RAI'] }),
    ok: (s, pl) => pl.attacks.some(a => a.to === s.p[1].board[0].uid) },
  { name: "don't waste: his Raider (2 health) and Heavy; Hit 2 and Hit 6 in hand, 5 mana: no Hit 6 on the Raider",
    make: () => base({ hand: ['H2', 'H6'], mana: 5, mine: ['LIN'], his: ['RAI', 'HEV'], hisHand: ['STR', 'GRD'] }),
    ok: (s, pl) => !pl.plays.some(x => x.card === 'H6' && x.tgt.uid !== -1 && s.p[x.tgt.side].board.find(u => u.uid === x.tgt.uid).hp <= 2) },
];

export function runSanity(seeds = 5) {
  const expert = expertBot(EXPERT), out = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, seeds]]) {
      let passed = 0, ex = '', bad = '';
      for (let k = 0; k < n; k++) { const s = P.make(), pl = bot(s, makeRng(100 + k)); if (P.ok(s, pl)) passed++; else if (!bad) bad = show(s, pl); if (k === 0) ex = show(s, pl); }
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
