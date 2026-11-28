// node sanity.mjs [playouts]: set positions a person never gets wrong, for Greedy and Expert.
// Each position asks for the next action; Expert runs 5 times.
import { newMatch, act, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

let U = 9000;
const unit = (card, readyAt, o = {}) => { const c = CARDS[card]; return { uid: U++, card, atk: c.atk, hp: c.hp, max: c.hp, rec: c.rec, readyAt, ...o }; };
function base({ myPos = 20, hisPos = 22, myLife = 20, hisLife = 20, hand = [], mine = [], his = [], hisHand = ['QUI', 'RAI', 'LIN'] }) {
  const s = newMatch({ seed: 77, first: 0 });
  s.turn = 0; s.top = 0;
  Object.assign(s.p[0], { pos: myPos, life: myLife, hand, board: mine });
  Object.assign(s.p[1], { pos: hisPos, life: hisLife, hand: hisHand, board: his });
  return s;
}
const POSITIONS = [
  { name: 'lethal: he is at 3, my Raider is ready, his Quick 2/1 tempts a free kill: attack him',
    s: () => base({ hisLife: 3, hand: ['LIN'], mine: [unit('RAI', 18)], his: [unit('QUI', 20)] }),
    ok: (a, s) => act(s, a).winner === 0 },
  { name: 'free trade: my ready Heavy 5/6 against his ready Quick 2/1 (his only card), I am at 2 and he acts next: attack the Quick',
    s: () => base({ myPos: 20, hisPos: 20, myLife: 2, hisLife: 9, hand: ['GUA', 'LIN'], mine: [unit('HEA', 18), unit('RAI', 23)], his: [unit('QUI', 19)], hisHand: [] }),
    ok: (a) => a.t === 'atk' && a.j === 0 },
  { name: "don't waste: Hit 3 and Hit 6 in hand, his Quick 2/1 and Heavy 5/6: never Hit 6 the Quick",
    s: () => base({ hand: ['H3', 'H6'], his: [unit('QUI', 20), unit('HEA', 24)] }),
    ok: (a) => !(a.t === 'play' && a.card === 'H6' && a.target.i === 0) },
  { name: "don't waste: Haste in hand, my Line already ready: never Haste it",
    s: () => base({ hand: ['HAS', 'GUA'], mine: [unit('LIN', 18)], his: [unit('GUA', 30)] }),
    ok: (a) => !(a.t === 'play' && a.card === 'HAS') },
];
export function runSanity({ iters = 6000, quiet = false } = {}) {
  const expert = expertBot({ iters });
  const results = []; let expertPass = true;
  for (const P of POSITIONS) {
    let s = P.s(); const g = P.ok(greedyBot(s, makeRng(1)), s);
    let e = 0; for (let k = 0; k < 5; k++) { s = P.s(); if (P.ok(expert(s, makeRng(100 + k)), s)) e++; }
    results.push({ position: P.name, greedy: g, expert: `${e}/5` });
    if (e < 5) expertPass = false;
    if (!quiet) console.log(`${e === 5 ? 'ok  ' : 'FAIL'} expert ${e}/5 · greedy ${g ? 'ok' : 'fails'} · ${P.name}`);
  }
  return { results, expertPass };
}
if (import.meta.url === `file://${process.argv[1]}`) { const r = runSanity({ iters: +process.argv[2] || 6000 }); console.log(r.expertPass ? 'all pass' : 'FAILURES'); }
