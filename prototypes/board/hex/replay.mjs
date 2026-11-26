// node replay.mjs <dir of saved games (JSON, one per game)>: replays each game from its seed and
// moves in the engine and prints the board after every turn, each side's plays, and food.
// Units are shown as A3 (the human, side 0) and b3 (the bot); `.` is empty.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { newMatch, playAction, endTurn, CARDS, ROW_LENGTHS, heldRegions } from './src/engine.js';

const dir = process.argv[2];
const files = readdirSync(dir, { recursive: true }).filter(f => f.endsWith('.json')).map(f => join(dir, f));
const cell = (u) => u ? (u.side === 0 ? 'A' : 'b') + u.hp : ' .';
function show(s) {
  let k = 0, out = '';
  for (const n of ROW_LENGTHS) { out += '  '.repeat(4 - n) + s.board.slice(k, k + n).map(u => cell(u).padStart(2)).join('  ') + '\n'; k += n; }
  return out;
}
for (const f of files) {
  const g = JSON.parse(readFileSync(f, 'utf8'));
  const d = g.data || g; // tool dumps may wrap the body
  let s = newMatch({ seed: d.seed, first: d.first });
  console.log(`=== ${f}: ${d.first === 0 ? 'human' : 'bot'} first, winner ${d.winner === 0 ? 'human' : d.winner === 1 ? 'bot' : d.winner}`);
  let plays = [];
  for (const m of d.moves) {
    if (m[0] === 'end') {
      const who = s.turn === 0 ? 'human' : 'bot  ';
      const held = heldRegions(s, s.turn).length;
      console.log(`turn ${String(s.turnNo).padStart(2)} ${who} mana ${s.p[s.turn].maxMana}: ${plays.join(', ') || '(nothing)'}  | holds ${held}`);
      s = endTurn(s);
      console.log(show(s) + `  food human ${s.p[0].food}, bot ${s.p[1].food}`);
      plays = [];
      if (s.winner !== null) break;
    } else {
      const [, card, tile] = m;
      const c = CARDS[card];
      const target = s.board[tile];
      plays.push(c.kind === 'Unit' ? `U${c.n}@${tile}${target ? '(over own ' + target.hp + ')' : ''}` : `S${c.n}@${tile}(on ${target ? target.hp : '?'})`);
      s = playAction(s, card, tile);
    }
  }
}
