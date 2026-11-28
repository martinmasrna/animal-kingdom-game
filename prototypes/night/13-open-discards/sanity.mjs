// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays out its whole turn from the position; Expert is tried with several seeds.
import { newMatch, act, key } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
let U = 9000;
const unit = (card, atk, hp, ready = true) => ({ uid: U++, card, atk, hp, max: hp, ready });
// a mid-game position, seat 1 to move with `mana`, empty boards and discards, hands set by the test
function base(mana = 5) {
  const s = newMatch({ seed: 7, first: 1 });
  for (const p of s.p) { p.deck = p.deck.concat(p.hand).slice(0, 14); p.hand = []; p.board = []; p.discard = []; p.maxMana = 5; }
  s.p[0].hand = ['RA', 'LI', 'H2'];
  s.p[1].mana = mana; s.p[1].took = false;
  s.turn = s.toMove = 1; s.turnNo = 10;
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
const won = (r) => r.end.winner === 1;
// 1. turn 1, 1 mana, Hit 2 and a Striker in hand, empty boards: never Hit 2 at his face (it
//    would also hand him the Hit 2)
check('turn 1: no Hit 2 at the face', () => { const s = newMatch({ seed: 11, first: 1 }); s.p[1].hand = ['H2', 'ST', 'HE']; return s; },
  (r) => !r.acts.some(a => a.card === 'H2'));
// 2. lethal: he is at 7, my ready Line and Hit 3 + Hit 2 with 3 mana; his Huge invites a trade
check('lethal 3 + 3 + 2 into 7', () => { const s = base(3); s.p[0].hp = 7; s.p[1].hand = ['H3', 'H2', 'LI']; s.p[1].board = [unit('LI', 3, 4)]; s.p[0].board = [unit('HU', 6, 7), unit('ST', 2, 1)]; return s; }, won);
// 3. lethal through the Coin: he is at 6, I hold Hit 6 (4 mana) with 3 mana and the Coin
check('lethal through the Coin', () => { const s = base(3); s.p[0].hp = 6; s.p[1].hand = ['H6', 'COIN']; return s; }, won);
// 4. lethal from the discard: he is at 3, his Hit 3 lies in his discard, I have 3 mana and a Line in hand
check('lethal: his Hit 3 from his discard', () => { const s = base(3); s.p[0].hp = 3; s.p[0].discard = ['H3', 'ST']; s.p[1].hand = ['LI']; return s; }, won);
// 5. a free trade: his Striker (2/1) against my ready Line (3/4), no lethal, and no damage spell
//    left anywhere he can reach (his hand, his deck, my discard), so nothing punishes the
//    wounded Line: kill it
check('free trade: Line into Striker', () => { const s = base(2); s.p[0].hand = ['HU', 'BI', 'HE']; s.p[0].deck = s.p[0].deck.map(() => 'HU'); s.p[1].hand = ['HU', 'BI']; s.p[1].board = [unit('LI', 3, 4)]; s.p[0].board = [unit('ST', 2, 1)]; return s; },
  (r) => r.acts.some(a => a.t === 'attack' && a.to === 0));
// 6. don't waste: 4 mana, nothing in hand, his discard holds a Line (3 + 1) and a Huge (6 + 1):
//    take the Line rather than leave the mana unspent
check('spend idle mana on his discarded Line', () => { const s = base(4); s.p[1].hand = []; s.p[0].discard = ['LI', 'HU']; return s; },
  (r) => r.acts.some(a => a.t === 'play' && a.disc && a.card === 'LI'));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
