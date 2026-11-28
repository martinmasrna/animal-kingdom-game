// node sanity.mjs: set positions a person never gets wrong (take lethal through pitching, don't
// pitch a card for nothing, take a free trade), for Greedy and Expert. Expert is asked on five
// different seeds and must pass every one.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base(hand, myBoard = [], hisBoard = [], myLife = 20, hisLife = 20) {
  const s = newMatch({ seed: 11, first: 0 });
  s.p[0].hand = hand.slice(); s.p[0].pool = 0; s.p[0].life = myLife; s.p[1].life = hisLife;
  let uid = 9000;
  const mk = (id, ready, hp) => ({ uid: uid++, card: id, atk: CARDS[id].atk, hp: hp ?? CARDS[id].hp, max: CARDS[id].hp, ready });
  s.p[0].board = myBoard.map(([id, r, hp]) => mk(id, r, hp)); s.p[1].board = hisBoard.map(([id, r, hp]) => mk(id, r, hp));
  return s;
}
// the bot's whole turn: its actions until it ends the turn (or the match ends)
function turnOf(bot, s, rng) {
  let t = s; const acts = [];
  for (let k = 0; k < 40 && t.winner === null && t.toAct === s.toAct; k++) {
    const a = bot(t, rng); acts.push(a);
    if (a.t === 'end') { return { acts, before: t, after: act(t, a) }; }
    t = act(t, a);
  }
  return { acts, before: t, after: t };
}
const show = (acts) => acts.map(a => a.t === 'pitch' ? 'pitch ' + CARDS[a.card].name : a.t === 'play' ? 'play ' + CARDS[a.card].name + (a.tgt ? (a.tgt.i < 0 ? '→player' : '→u' + a.tgt.i) : '') : a.t === 'attack' ? `attack u${a.from}→${a.to < 0 ? 'player' : 'u' + a.to}` : 'end').join(', ');

const POSITIONS = [
  { name: 'lethal: he is on 5, Hit 5 and two Pips in hand (pitch both, Hit 5 at him)',
    make: () => base(['H5', 'PIP', 'PIP'], [], [['RAI', true]], 20, 5),
    ok: (r) => r.after.winner === 0 },
  // (with Hit 5 as the third card, pitching it for nothing is right: it cycles the card that pays
  // worst for the one drawn instead, 43% against 34% in Greedy play-outs; a Pip is worth keeping)
  { name: "don't overpay: Raider and two Pips in hand, empty boards (no card pitched for nothing)",
    make: () => base(['RAI', 'PIP', 'PIP']),
    ok: (r) => { const pitched = r.acts.filter(a => a.t === 'pitch').map(a => CARDS[a.card].pitch); const left = r.before.p[0].pool; return r.acts.some(a => a.t === 'play') && !pitched.some(p => left >= p); } },
  { name: 'free trade: my ready Line against his Raider, I am on 12',
    make: () => base([], [['LIN', true]], [['RAI', true]], 12, 20),
    ok: (r) => r.acts.some(a => a.t === 'attack' && a.from === 0 && a.to === 0) },
];

export function runSanity(seeds = 5) {
  const expert = expertBot(EXPERT), out = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, seeds]]) {
      let passed = 0, ex = '', bad = '';
      for (let k = 0; k < n; k++) { const r = turnOf(bot, P.make(), makeRng(100 + k)); if (P.ok(r)) passed++; else if (!bad) bad = show(r.acts); if (k === 0) ex = show(r.acts); }
      ex = bad || ex;
      out.push({ position: P.name, bot: bn, pass: passed === n, passed, of: n, example: ex });
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
