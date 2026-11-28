// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays out its whole turn from the position; Expert is tried with several seeds.
import { newMatch, act, key } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
const unit = (card, atk, hp, ready = true) => ({ uid: Math.floor(Math.random() * 1e9), card, atk, hp, max: hp, ready });
// a mid-game position, seat 1 to move, both decks at 14, both hands set by the test
function base() {
  const s = newMatch({ seed: 7, first: 1 });
  for (const p of s.p) { p.deck = p.deck.concat(p.hand).slice(0, 14); p.hand = []; p.board = []; p.discard = []; p.maxMana = p.mana = 5; }
  s.p[1].hand = ['ST', 'GU']; s.p[0].hand = ['RA', 'LI', 'H2'];
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
// 1. lethal: his deck holds 3, my ready Raider can attack; his Guard invites a trade
check('lethal: Raider at a 3-card deck', () => { const s = base(); s.p[0].deck = s.p[0].deck.slice(0, 3); s.p[1].board = [unit('RA', 3, 2)]; s.p[0].board = [unit('GU', 1, 4)]; return s; },
  (r) => r.end.winner === 1);
// 2. lethal through Burn 3: his deck holds 3, I hold Burn 3 and 3 mana, no board
check('lethal: Burn 3 at a 3-card deck', () => { const s = base(); s.p[0].deck = s.p[0].deck.slice(0, 3); s.p[1].hand = ['B3', 'LI']; s.p[1].mana = 3; return s; },
  (r) => r.end.winner === 1);
// 3. don't kill yourself: my deck holds 1, Draw 2 and Recover in hand, mana for one of them,
//    a full discard to recover from (Draw 2 draws from the empty deck and loses at once)
check('deck of 1: never Draw 2', () => { const s = base(); s.p[1].deck = s.p[1].deck.slice(0, 1); s.p[1].hand = ['D2', 'RC']; s.p[1].mana = 2; s.p[1].discard = ['BI', 'HE', 'LI', 'RA', 'ST', 'GU']; return s; },
  (r) => !r.acts.some(a => a.card === 'D2'));
// 4. the free trade of this game: his ready Raider would burn the last 3 cards of my deck next
//    turn. My ready Line kills it and lives, and next turn Line and Big (played this turn)
//    reach his deck; going face leaves the Raider to finish me. (The spec's plain Line-into-Raider
//    trade is not free here: played out by Expert from both sides, face won 19% and the trade 7%
//    from that position, so it is not a position a person never gets wrong.)
check('kill the unit that would empty my deck', () => { const s = base(); s.p[1].deck = s.p[1].deck.slice(0, 3); s.p[0].deck = s.p[0].deck.slice(0, 6);
  s.p[1].board = [unit('LI', 3, 4), unit('BI', 5, 6, false)]; s.p[0].board = [unit('RA', 3, 2)]; s.p[1].hand = []; return s; },
  (r) => r.acts.some(a => a.t === 'attack' && a.to === 0));
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
