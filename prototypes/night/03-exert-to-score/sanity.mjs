// node sanity.mjs [playouts]: set positions a person never gets wrong, for Greedy and Expert.
// Each position is played out action by action until the bot ends its turn; Expert runs 5 times.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

let U = 9000;
const unit = (card, o = {}) => { const c = CARDS[card]; return { uid: U++, card, str: c.str, hp: c.hp, max: c.hp, sc: c.sc, ex: false, fresh: false, ...o }; };
function base({ mePts = 0, himPts = 0, hand = [], mana = 0, mine = [], his = [], hisHand = ['RUN', 'RUN', 'RUN'] }) {
  const s = newMatch({ seed: 77, first: 0 });
  s.turnNo = 9; s.turn = 0;
  Object.assign(s.p[0], { pts: mePts, hand, mana, maxMana: mana, board: mine });
  Object.assign(s.p[1], { pts: himPts, hand: hisHand, board: his });
  return s;
}
function turnOf(bot, s, rng) {
  const acts = []; let t = s;
  for (let k = 0; k < 20 && t.winner === null && t.turn === s.turn; k++) { const a = bot(t, rng); acts.push({ a, before: t }); t = act(t, a); }
  return { acts, end: t };
}
const POSITIONS = [
  { name: 'lethal: at 17 with ready Score-2 and Score-1 units, an exerted enemy to tempt: score both',
    s: () => base({ mePts: 17, himPts: 12, mine: [unit('LIN'), unit('RUN')], his: [unit('RUN', { ex: true })] }),
    ok: ({ end }) => end.winner === 0 },
  { name: 'free trade: ready Line 3/3 against an exerted Runner 1/1 that is his only scorer, him at 17: challenge it',
    s: () => base({ mePts: 10, himPts: 17, mine: [unit('LIN')], his: [unit('RUN', { ex: true })], hisHand: [] }),
    ok: ({ acts }) => acts.some(x => x.a.t === 'chal') },
  { name: "don't waste: Hit 2 and Hit 4 in hand, 4 mana, enemy Runner 1/1 and Line 3/3: never Hit 4 the Runner",
    s: () => base({ hand: ['H2', 'H4'], mana: 4, his: [unit('RUN', { ex: true }), unit('LIN', { ex: true })] }),
    ok: ({ acts }) => !acts.some(x => x.a.card === 'H4' && x.before.p[1].board[x.a.target.i].card === 'RUN') },
];
export function runSanity({ iters = 10000, quiet = false } = {}) {
  const expert = expertBot({ iters });
  const results = []; let expertPass = true;
  for (const P of POSITIONS) {
    const g = P.ok(turnOf(greedyBot, P.s(), makeRng(1)));
    let e = 0; for (let k = 0; k < 5; k++) if (P.ok(turnOf(expert, P.s(), makeRng(100 + k)))) e++;
    results.push({ position: P.name, greedy: g, expert: `${e}/5` });
    if (e < 5) expertPass = false;
    if (!quiet) console.log(`${e === 5 ? 'ok  ' : 'FAIL'} expert ${e}/5 · greedy ${g ? 'ok' : 'fails'} · ${P.name}`);
  }
  return { results, expertPass };
}
if (import.meta.url === `file://${process.argv[1]}`) { const r = runSanity({ iters: +process.argv[2] || 10000 }); console.log(r.expertPass ? 'all pass' : 'FAILURES'); }
