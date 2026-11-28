// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// A position is played until the turn ends or a pending spell resolves; Expert is tried with
// several seeds.
import { newMatch, act, key } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
// mid-game, seat 1's turn, both at 14 life, nothing stored, hands set by the test
function base() {
  const s = newMatch({ seed: 31, first: 1 });
  for (const p of s.p) { p.deck = p.deck.concat(p.hand).slice(0, 16); p.hand = []; p.life = 14; p.maxMana = p.mana = 6; p.stored = 0; p.sieges = []; }
  s.p[0].hand = ['BO', 'WA', 'ST']; s.p[0].mana = 0;
  s.turn = s.toMove = 1; s.turnNo = 11;
  return s;
}
// play seat `me` until it no longer has the move in this turn (or the game ends)
function run(bot, s, me, rng) {
  const acts = []; let t = s; const turn = s.turnNo;
  while (t.winner === null && t.toMove === me && t.turnNo === turn && acts.length < 30) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
  return { acts, end: t };
}
let bad = 0;
function check(name, mk, me, ok) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) { const s = mk(); const r = run(b, s, me, makeRng(100 + k)); if (ok(r, s)) pass++; else sample = r.acts.map(key).join(' '); }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
// 1. lethal: he is on 5 with nothing stored; I hold Blast, Study and Ward with 3 mana
check('lethal: Blast into 5 life', () => { const s = base(); s.p[0].life = 5; s.p[1].hand = ['BL', 'ST', 'WA']; s.p[1].mana = 3; return s; }, 1,
  (r) => r.end.winner === 1);
// 2. free response: he casts Barrage at me; I hold Cancel with 3 stored
check('Cancel his Barrage', () => {
  const s = base(); s.turn = 0; s.p[0].hand = ['BA', 'BO']; s.p[0].mana = 6; s.p[1].hand = ['CA', 'WA', 'BO']; s.p[1].stored = 3; s.p[1].mana = 0;
  s.toMove = 0; return act(s, { t: 'cast', card: 'BA' });
}, 1, (r) => r.acts[0] && r.acts[0].t === 'respond' && r.acts[0].card === 'CA');
// 3. don't waste: he casts Study; I hold Ward with 1 stored. Never Ward a Study.
check('never Ward a Study', () => {
  const s = base(); s.turn = 0; s.p[0].hand = ['ST', 'BO']; s.p[0].mana = 6; s.p[1].hand = ['WA', 'BO']; s.p[1].stored = 1; s.p[1].mana = 0;
  s.toMove = 0; return act(s, { t: 'cast', card: 'ST' });
}, 1, (r) => !r.acts.some(a => a.t === 'respond'));
// 4. don't waste: no Response in hand and nothing stored against me: cast Blast, Drain and Bolt (6 mana), store nothing
check('no Response held: spend the mana', () => { const s = base(); s.p[1].hand = ['BL', 'DR', 'BO']; return s; }, 1,
  (r) => ['BL', 'DR', 'BO'].every(c => r.acts.some(a => a.t === 'cast' && a.card === c)));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
