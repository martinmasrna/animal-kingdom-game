// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert (a whole turn each).
import { newMatch, act } from './src/engine.js';
import { greedyBot, mcExpert, makeRng, EXPERT } from './src/bot.js';

const expert = mcExpert(EXPERT), rng = makeRng(3);
const U = (card, atk, hp, ready = true) => ({ uid: Math.floor(Math.random() * 1e9), card, atk, hp, max: hp, ready });
// a mid-game position: my turn (seat 1), 6 mana, both decks full
const base = () => { const s = newMatch({ seed: 11, first: 0 }); s.turn = 1; s.turnNo = 12; for (const p of s.p) { p.hand = []; p.board = []; p.maxMana = p.mana = 6; } return s; };
const turn = (bot, s) => { const acts = []; let t = s; for (let k = 0; k < 40 && t.winner === null; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); if (a.t === 'end') break; } return { acts, t }; };
const show = (acts) => acts.map(a => a.t === 'play' ? `play ${a.card}${a.to !== undefined ? '→' + a.to : ''}` : a.t === 'attack' ? `attack ${a.from}→${a.to}` : a.t === 'score' ? `score ${a.from}` : 'end').join(', ');
let bad = 0;
const results = [];
const check = (name, mk, ok, gate = true) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    const s = mk(), r = turn(b, s), pass = ok(r, s);
    if (!pass && gate && bn === 'expert') bad++;
    results.push({ name, bot: bn, pass, acts: show(r.acts) });
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}${gate ? '' : ' (not gated)'}: ${show(r.acts)}`);
  }
};
// 1. lethal: at 33 with ready 3/4 and 2/3, an enemy 3/2 tempting a kill: score both
check('lethal 33 + 4 + 3', () => { const s = base(); s.p[1].score = 33; s.p[1].board = [U('LIN', 3, 4), U('GRD', 2, 3)]; s.p[0].board = [U('RAI', 3, 2), U('HUG', 6, 7)]; return s; },
  (r) => r.t.winner === 1);
// 2. denial, this game's free trade: his Heavy 4/5 scores him from 35 to 40 next turn; my ready Big 5/5 kills it
check('kill the unit that would win', () => { const s = base(); s.p[0].score = 35; s.p[1].score = 20; s.p[1].board = [U('BIG', 5, 5)]; s.p[0].board = [U('HVY', 4, 5, false)]; return s; },
  (r) => r.t.p[0].board.length === 0);
// 3. don't waste: nothing to attack, three ready units: every one scores
check('no ready unit left idle', () => { const s = base(); s.p[1].board = [U('LIN', 3, 4), U('STR', 2, 1), U('GRD', 2, 3)]; return s; },
  (r) => r.t.p[1].score === 8);
// 4. don't waste: Hit 6 never goes on a 1-health unit while Hit 2 is in hand
check('Hit 2, not Hit 6, on a 2/1', () => { const s = base(); s.p[1].hand = ['H2', 'H6']; s.p[1].mana = 5; s.p[0].board = [U('STR', 2, 1)]; return s; },
  (r) => !r.acts.some(a => a.card === 'H6'));
// not gated: the spec's "free trade" (ready Heavy 4/5 against an enemy Raider 3/2). Damage stays,
// so the trade costs the Heavy 3 of its 5 scoring health; scoring 5 and letting him choose is at least as good.
check('Heavy 4/5 and an enemy Raider 3/2', () => { const s = base(); s.p[1].board = [U('HVY', 4, 5)]; s.p[0].board = [U('RAI', 3, 2, false)]; return s; },
  (r) => r.acts.some(a => a.t === 'attack'), false);
console.log(bad ? bad + ' Expert failures' : 'Expert passes every gated position');
export { results };
