// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Expert is tried with several seeds.
import { newMatch, act, key, ante, lineCost } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
// round 3, seat 0 leads; both lines bought and their spends shown; betting about to start
function base(myLine, hisLine, { myChips = 15, hisChips = 15 } = {}) {
  const s = newMatch({ seed: 21, first: 0 });
  s.round = 3; s.lead = 0; s.phase = 'bet'; s.toMove = 0; s.checks = 0;
  const A = ante(3);
  for (const [k, line, chips] of [[0, myLine, myChips], [1, hisLine, hisChips]]) {
    const p = s.p[k]; p.deck = p.deck.concat(p.hand); p.hand = [];
    for (const id of line) p.deck.splice(p.deck.indexOf(id), 1);
    p.hand = p.deck.splice(0, 5 - line.length);
    p.line = line.slice(); p.spent = lineCost(line); p.contrib = A; p.chips = chips; p.raised = false;
  }
  s.pot = 2 * A;
  return s;
}
let bad = 0;
function check(name, mk, run, ok) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) { const s = mk(); const acts = run(b, s, makeRng(100 + k)); if (ok(acts, s)) pass++; else sample = acts.map(key).join(' '); }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
const one = (b, s, rng) => [b(s, rng)];
// 1. a line that beats anything his shown spend can buy (Top + High = 14 against a spend of 0,
//    which buys at most 4): first to act, bet
check('free win, first to act: bet', () => base(['TO', 'HI'], ['LO', 'LO']), one, (a) => a[0].t === 'bet');
// 2. the same line facing his bet: raise, never fold
check('free win, facing a bet: raise', () => { let s = base(['TO', 'HI'], ['LO', 'LO']); s.lead = 1; s.toMove = 1; s = act(s, { t: 'bet' }); return s; }, one, (a) => a[0].t === 'raise');
// 3. lethal: he has 2 chips left behind and my line cannot lose: bet (a call puts him out)
check('lethal: bet into his last 2 chips', () => base(['TO', 'HI'], ['MI', 'LO'], { hisChips: 2 }), one, (a) => a[0].t === 'bet');
// 4. don't waste: a hand of Bluff, Bluff, Mid, High, Low at the buy, against Greedy: a Bluff
//    bought into a line that then only checks and calls buys nothing; buy one only to bet
check('a Bluff is bought only to bet', () => { const s = newMatch({ seed: 33, first: 0 }); const p = s.p[0]; p.deck = p.deck.concat(p.hand); p.hand = [];
    for (const id of ['BL', 'BL', 'MI', 'HI', 'LO']) { p.deck.splice(p.deck.indexOf(id), 1); p.hand.push(id); } return s; },
  (b, s, rng) => { const acts = []; let t = s; while (t.winner === null && t.round === s.round && acts.length < 20) { const a = t.toMove === 0 ? b(t, rng) : greedyBot(t); if (t.toMove === 0) acts.push(a); t = act(t, a); } return acts; },
  (acts) => !acts[0].line.includes('BL') || acts.some(a => a.t === 'bet' || a.t === 'raise'));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
