// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays from the position until the decision is made; Expert is tried with several seeds.
import { newMatch, act, key } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
let U = 9000;
const unit = (card, atk, hp, o = {}) => ({ uid: U++, card, atk, hp, max: hp, ready: true, fresh: false, sent: false, ...o });
// round 6, seat 0 attacks, both hands set by the test
function base() {
  const s = newMatch({ seed: 7, attacker: 0 });
  s.round = 6; s.turnNo = 11; s.p[0].mana = 6; s.p[1].mana = 6;
  s.p[0].hand = []; s.p[1].hand = ['GU', 'PI'];
  return s;
}
// the mover's actions until control passes (or the game ends)
function turnOf(bot, s, rng) {
  const me = s.toMove, acts = [];
  let t = s;
  while (t.winner === null && t.toMove === me && acts.length < 40) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
  return { acts, end: t };
}
let bad = 0;
function check(name, mk, ok) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) { const s = mk(); const r = turnOf(b, s, makeRng(100 + k)); if (ok(r, s)) pass++; else sample = r.acts.map(key).join(' '); }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
// 1. lethal: the Gate is on 4, two ready Climbers (cannot be blocked), a Wall of two Pikes: send both
check('lethal: two Climbers at a Gate on 4', () => { const s = base(); s.gate = 4; s.p[0].units = [unit('CL', 2, 1), unit('CL', 2, 1)]; s.p[1].units = [unit('PI', 3, 4), unit('PI', 3, 4)]; return s; },
  (r) => r.end.winner === 0);
// 2. a free block: a Grunt (2/2) is sent alone, the Wall holds a Pike (3/4): block it (the Pike kills it and lives)
check('free block: Pike on a Grunt', () => { const s = base(); s.gate = 15; s.p[0].units = [unit('GR', 2, 2)]; s.p[1].units = [unit('PI', 3, 4)]; let t = act(s, { t: 'send', i: 0 }); t = act(t, { t: 'end' }); return t; },
  (r) => r.acts[0].t === 'block' && r.acts[0].a === 0);
// 3. don't waste: the Defender's turn, Gate at 20, hand Repair and Pike, 3 mana: never Repair
check('no Repair at a full Gate', () => { const s = base(); s.gate = 20; s.p[0].units = [unit('GR', 2, 2)]; s.p[1].units = []; s.p[1].hand = ['RP', 'PI']; let t = act(s, { t: 'end' }); t.p[1].mana = 3; return t; },
  (r) => !r.acts.some(a => a.card === 'RP'));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
