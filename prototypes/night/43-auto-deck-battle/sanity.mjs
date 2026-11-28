// node sanity.mjs [tries=5]: set positions a person never gets wrong, for Greedy and Expert.
// Each bot plays its whole shop from the position; Expert is tried with several seeds.
import { newMatch, act, key, battle, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng, EXPERT, plans, oppNext } from './src/bot.js';

const TRIES = +(process.argv[2] || 5);
const expert = expertBot(EXPERT);
// round 4, seat 0 shopping with the deck, shop and gold set by the test
function base(deck, shop, gold, oppDeck = ['PI', 'BR', 'WA', 'GU', 'OP']) {
  const s = newMatch({ seed: 41 });
  s.round = 4; s.toMove = 0;
  const P = s.p[0]; P.deck = deck.slice(); P.shown = deck.slice(); P.shop = shop.slice(); P.gold = gold; P.removed = false;
  s.p[1].deck = oppDeck.slice(); s.p[1].shown = oppDeck.slice();
  return s;
}
function shopOf(bot, s, rng) {
  const acts = []; let t = s;
  while (t.winner === null && t.toMove === 0 && acts.length < 40) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
  return { acts, deck: t.p[0].deck, s: t };
}
let bad = 0;
function check(name, mk, ok) {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const tries = bn === 'expert' ? TRIES : 1;
    let pass = 0, sample = '';
    for (let k = 0; k < tries; k++) { const s = mk(); const r = shopOf(b, s, makeRng(100 + k)); if (ok(r, s)) pass++; else sample = r.acts.map(key).join(' ') + ' -> ' + r.deck.join(','); }
    const good = pass === tries; if (!good && bn === 'expert') bad++;
    console.log(`${good ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${pass}/${tries}${sample ? '  e.g. ' + sample : ''}`);
  }
}
const winRate = (deck, opp, n = 3000) => { const rng = makeRng(9); let w = 0; for (let i = 0; i < n; i++) if (battle(deck, opp, rng, null).winner === 0) w++; return w / n; };
// 1. don't waste: 6 gold, a deck of 5, four affordable cards in the shop: spend something
check('6 gold and room: spend it', () => base(['PI', 'PI', 'PI', 'BR', 'WA'], ['BR', 'WA', 'GU', 'PI'], 6), (r) => r.s.p[0].gold < 6);
// 2. free removal: a full deck of 10 with Pips, a Heavy in the shop, 5 gold: remove a Pip, buy the Heavy
const full = ['PI', 'PI', 'PI', 'PI', 'BR', 'WA', 'GU', 'OP', 'BO', 'RA'];
check('full deck: a Pip out, the Heavy in', () => base(full, ['HE', 'PI', 'WA', 'BR'], 5), (r) => r.deck.includes('HE') && r.deck.filter(x => x === 'PI').length === 3);
// 3. lethal: he is on 1 life, so any battle won ends the game: buy the deck most likely to win
//    the battle, not the one that would deal the most damage. His deck will change in his secret
//    shop, so each plan's chance is measured against 3000 of his possible next decks (the same
//    guesses at his buys the Expert makes, from shops dealt at random); the deck bought must win
//    within 3 points of the best plan's.
const opp3 = ['PI', 'BR', 'BO', 'HE', 'PI'];
const mk3 = () => { const s = base(['HE', 'BR', 'BO'], ['BO', 'OP', 'RA', 'BO'], 6, opp3); s.p[1].life = 1; return s; };
const winVsModel = (deck, n = 3000) => { const rng = makeRng(9); let w = 0; for (let i = 0; i < n; i++) if (battle(deck, oppNext(opp3, rng), rng, null).winner === 0) w++; return w / n; };
const all3 = plans(mk3().p[0], 6, mk3().p[0].shop).map(pl => ({ deck: pl.deck, w: winVsModel(pl.deck) }));
const best3 = Math.max(...all3.map(x => x.w));
check(`lethal: maximise the battle win (best plan ${best3.toFixed(3)})`, mk3, (r) => winVsModel(r.deck) >= best3 - 0.03);
console.log(bad ? bad + ' Expert failures' : 'all Expert positions pass');
process.exitCode = bad ? 1 : 0;
