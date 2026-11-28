// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays out its whole turn (combat included) from the position; Expert is tried with
// several seeds.
import { newMatch, act, key } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
let U = 1000;
const unit = (card, atk, hp) => ({ uid: U++, card, atk, hp, max: hp });
// seat 1 to move (it wins at -5), mid-game, empty lanes, hands set by each test
function base() {
  const s = newMatch({ seed: 11, first: 1 });
  for (const p of s.p) { p.deck = p.deck.concat(p.hand).slice(0, 18); p.hand = []; p.slots = [null, null, null, null]; p.maxMana = p.mana = 4; }
  s.p[0].hand = ['RA', 'LI', 'H2'];
  s.turn = s.toMove = 1; s.turnNo = 8; s.scale = 0;
  return s;
}
function turnOf(bot, s, rng) {
  const me = s.turn, acts = [];
  let t = s;
  while (t.winner === null && t.turn === me && acts.length < 40) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
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
// 1. lethal: the scale leans 3 my way, lane 4 is open, the other lanes hold his units; Raider and 2 mana
check('lethal: Raider into the open lane', () => {
  const s = base(); s.scale = -3; s.p[1].mana = 2; s.p[1].hand = ['RA', 'WA'];
  s.p[0].slots = [unit('LI', 2, 4), unit('HE', 3, 5), unit('WA', 0, 4), null]; return s;
}, (r) => r.end.winner === 1);
// 2. free kill: his Lancer 3/2 in lane 2 faces my empty slot; Heavy in hand kills it in this combat
check('free kill: Heavy opposite the Lancer', () => {
  const s = base(); s.p[1].hand = ['HE']; s.p[0].slots = [null, unit('LA', 3, 2), null, null]; return s;
}, (r) => r.acts.some(a => a.card === 'HE' && a.lane === 1));
// 3. don't waste: my Raider in lane 1 is hitting the scale; his Wall stands in lane 3 opposite my
//    empty slot; Shift is my only card. Never shift the Raider onto the Wall.
check('never Shift onto a Wall', () => {
  const s = base(); s.p[1].hand = ['SF']; s.p[1].mana = 1; s.p[1].slots = [unit('RA', 2, 2), null, null, null]; s.p[0].slots = [null, null, unit('WA', 0, 4), null]; return s;
}, (r) => !r.acts.some(a => a.card === 'SF' && a.to === 2));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
