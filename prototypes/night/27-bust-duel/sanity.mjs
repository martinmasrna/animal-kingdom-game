// node sanity.mjs [playouts]: set positions a person never gets wrong, for Greedy and Expert.
// Each asks for the next action; Expert runs 5 times.
import { newMatch, CARDS } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

function line(ids) { let pow = 0, strain = 0; for (const id of ids) { pow += CARDS[id].pow; strain += CARDS[id].str; } return { line: ids, pow, strain }; }
function base({ me = {}, him = {} }) {
  const s = newMatch({ seed: 77, first: 0 });
  s.round = 6; s.phase = 'line'; s.turn = 0; s.rfirst = 1;
  Object.assign(s.p[0], { life: 10, deck: ['S1', 'R3', 'S2', 'CR', 'S1', 'S4'], disc: ['S1', 'S2'] }, me);
  Object.assign(s.p[1], { life: 10, deck: ['S1', 'S2', 'S3'], disc: [] }, him);
  return s;
}
const POSITIONS = [
  { name: "don't push for nothing: he busted, my line is 11 (the most damage, coin for any card) at strain 3: Stop",
    s: () => base({ me: line(['S2', 'R3', 'R3', 'R3']), him: { ...line(['CR', 'R3', 'R3']), bust: true } }),
    ok: (a) => a.t === 'stop' },
  { name: 'free draw: no strain card left in my draw pile, he is still drawing: Draw',
    s: () => base({ me: { ...line(['S2', 'R3', 'CR']), deck: ['S1', 'S2', 'S1', 'S3'] }, him: line(['S2', 'S3']) }),
    ok: (a) => a.t === 'draw' },
  { name: 'lethal: he stopped on 2 life, I lead by 2 at strain 3: Stop',
    s: () => base({ me: line(['S2', 'R3', 'R3', 'R3']), him: { ...line(['S2', 'R3', 'R3', 'S1']), stop: true, life: 2 } }),
    ok: (a) => a.t === 'stop' },
];
export function runSanity({ iters = 3000, quiet = false } = {}) {
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
if (import.meta.url === `file://${process.argv[1]}`) { const r = runSanity({ iters: +process.argv[2] || 3000 }); console.log(r.expertPass ? 'all pass' : 'FAILURES'); }
