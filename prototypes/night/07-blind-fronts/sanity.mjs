// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays the rest of the round from the position (the opponent has passed); Expert is
// tried with several seeds.
import { newMatch, act, key, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
// round 3, seat 1 to place, fronts valued 1, 2, 3 left to right; seat 0 has passed
function base() {
  const s = newMatch({ seed: 21, first: 0 });
  s.round = 3; s.lead = 0; s.phase = 'place'; s.values = [1, 2, 3];
  for (const p of s.p) { p.deck = p.deck.concat(p.hand); p.hand = []; p.placed = [[], [], []]; p.passed = false; }
  s.p[0].passed = true; s.p[0].energy = 0; s.p[0].hand = ['TR', 'SQ', 'EL'];
  s.p[0].score = 4; s.p[1].score = 4; s.p[1].energy = 5;
  s.toMove = 1;
  return s;
}
function roundOf(bot, s, rng) {
  const acts = []; let t = s;
  while (t.winner === null && t.round === s.round && acts.length < 30) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
  return { acts, end: t };
}
let bad = 0;
function check(name, mk, ok) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) { const s = mk(); const r = roundOf(b, s, makeRng(100 + k)); if (ok(r, s)) pass++; else sample = r.acts.map(key).join(' '); }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
const at = (r, f) => r.acts.filter(a => a.t === 'place' && a.front === f);
// 1. free front: he passed with a cost-1 card at the 2-front and a cost-2 card at the 3-front,
//    nothing at the 1-front; I hold Scout, Squad and Feint. The Scout takes the 1-front for nothing.
check('free front: Scout to the empty 1-front', () => {
  const s = base(); s.p[0].placed = [[], ['TR'], ['SQ']]; s.p[1].hand = ['SC', 'SQ', 'FE']; return s;
}, (r) => at(r, 0).some(a => a.card === 'SC'));
// 2. don't waste: he passed with nothing at the 3-front and the rest locked up; I hold Heavy,
//    Troop and Feint. Take the 3-front with a cheap card, never the Heavy.
check('empty 3-front: never the Heavy', () => {
  const s = base(); s.p[0].placed = [['HE', 'EL'], ['HE'], []]; s.p[1].hand = ['HE', 'TR', 'FE']; return s;
}, (r) => at(r, 2).length > 0 && !at(r, 2).some(a => a.card === 'HE'));
// 3. lethal: I am on 10 and he on 6, he passed with no energy and nothing at the 2-front.
check('lethal: take the empty 2-front', () => {
  const s = base(); s.p[1].score = 10; s.p[0].score = 6; s.p[0].placed = [['SQ'], [], ['EL']]; s.p[1].hand = ['TR', 'FE', 'SQ']; s.p[1].energy = 2; return s;
}, (r) => r.end.winner === 1);
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
