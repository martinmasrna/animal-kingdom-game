// node sanity.mjs: set positions a person never gets wrong (lethal through a Rally, never Sway a
// Neutral already at 3 toward you, pull a big Neutral to your side when it is free), for Greedy and
// Expert. Expert is asked on five different seeds and must pass every one. Seat 0 to act.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

function base({ hand = [], mana = 3, slots = [[3, 0], [3, 0], [3, 0]], myLife = 15, hisLife = 15 }) {
  const s = newMatch({ seed: 41, first: 0 });
  s.turnNo = 2 * mana - 1; s.toAct = 0;
  s.p[0].hand = hand.slice(); s.p[0].mana = s.p[0].maxMana = mana; s.p[1].maxMana = mana;
  s.p[0].life = myLife; s.p[1].life = hisLife;
  s.slots = slots.map(([atk, loy], k) => ({ uid: 9000 + k, atk, loy }));
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
const show = (acts) => acts.map(a => a.t === 'play' ? CARDS[a.card].name + (a.slot !== undefined ? '→N' + (a.slot + 1) : '') : 'end').join(', ');
const POSITIONS = [
  // (as specified, Sway 1 on a 4-attack Neutral at 0 was lethal at the end of the turn; with the hit
  // moved to the start of the next turn the lethal line is Rally)
  { name: 'lethal: he is on 4, a 4-attack Neutral at 1 toward me, Rally and Sway 1 in hand: Rally it',
    make: () => base({ hand: ['S1', 'RAL', 'SHD'], mana: 3, slots: [[2, -1], [4, 1], [3, -2]], hisLife: 4 }),
    ok: (r) => r.after.winner === 0 },
  { name: "don't waste: no Sway on a Neutral already at 3 toward me",
    make: () => base({ hand: ['S1', 'S2'], mana: 3, slots: [[5, 3], [2, 0], [3, -1]] }),
    ok: (r) => !r.acts.some(a => a.t === 'play' && a.card.startsWith('S') && a.card !== 'SHD' && a.card !== 'SPR' && a.slot === 0) },
  { name: 'free swing: a 5-attack Neutral at 1 toward him and Sway 2 in hand: pull it to my side',
    make: () => base({ hand: ['S2'], mana: 2, slots: [[5, -1], [2, 0], [2, 1]] }),
    ok: (r) => r.acts.some(a => a.card === 'S2' && a.slot === 0) },
];
export function runSanity(seeds = 5) {
  const expert = expertBot(EXPERT), out = [];
  for (const P of POSITIONS) {
    for (const [bn, bot, n] of [['greedy', greedyBot, 1], ['expert', expert, seeds]]) {
      let passed = 0, ex = '', bad = '';
      for (let k = 0; k < n; k++) { const r = turnOf(bot, P.make(), makeRng(100 + k)); if (P.ok(r)) passed++; else if (!bad) bad = show(r.acts); if (k === 0) ex = show(r.acts); }
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
