// node sanity.mjs [playouts]: set positions a person never gets wrong, for Greedy and Expert.
// Each position is played out action by action until the bot ends its turn; Expert runs 5 times.
import { newMatch, act } from './src/engine.js';
import { greedyBot, expertBot, makeRng } from './src/bot.js';

function base({ pos = 0, vel = 0, hand = [], mana = 0, hisHand = ['SHO', 'HEA', 'CHK'] }) {
  const s = newMatch({ seed: 77, first: 0 });
  s.turnNo = 9; s.turn = 0; s.pos = pos; s.vel = vel;
  Object.assign(s.p[0], { hand, mana, maxMana: mana, anchor: false });
  Object.assign(s.p[1], { hand: hisHand, anchor: false });
  return s;
}
function turnOf(bot, s, rng) {
  const acts = []; let t = s;
  for (let k = 0; k < 20 && t.winner === null && t.turn === s.turn; k++) { const a = bot(t, rng); acts.push(a); t = act(t, a); }
  return { acts, end: t };
}
const played = (acts, id) => acts.some(a => a.card === id);
const POSITIONS = [
  { name: 'lethal: marker 6 forward, Jolt in hand and 2 mana: Jolt wins',
    s: () => base({ pos: 6, vel: -1, hand: ['JOL', 'HEA', 'ANC'], mana: 2 }),
    ok: ({ end }) => end.winner === 0 },
  { name: "don't waste: velocity 0, Check and Jolt in hand, 3 mana: never Check",
    s: () => base({ pos: 1, vel: 0, hand: ['CHK', 'JOL'], mana: 3 }),
    ok: ({ acts }) => !played(acts, 'CHK') },
  { name: "don't waste: the last turn of the game, marker 0, velocity 0 (nothing can move it toward me), Anchor and Heave in hand, 2 mana: Heave, never Anchor",
    s: () => { const s = base({ pos: 0, vel: 0, hand: ['ANC', 'HEA'], mana: 2, hisHand: [] }); s.turnNo = 24; return s; },
    ok: ({ acts }) => !played(acts, 'ANC') },
  { name: 'free swing: velocity 3 toward me, 5 mana and Reverse: Reverse',
    s: () => base({ pos: 0, vel: -3, hand: ['REV', 'SHO', 'JOL'], mana: 5 }),
    ok: ({ acts }) => played(acts, 'REV') },
];
export function runSanity({ iters = 1500, quiet = false } = {}) {
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
if (import.meta.url === `file://${process.argv[1]}`) { const r = runSanity({ iters: +process.argv[2] || 1500 }); console.log(r.expertPass ? 'all pass' : 'FAILURES'); }
