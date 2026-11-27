// node sanity.mjs: set positions a person never gets wrong, for Greedy and Expert. Every bot
// shipped on the page passes all of them.
import { newMatch, act, endTurn, CARDS } from './src/engine.js';
import { greedyBot, rolloutBot, makeRng } from './src/bot.js';
const expert = rolloutBot(), rng = makeRng(1);
let UID = 900;
const mk = (card, ready = true, extra = {}) => { const c = CARDS[card]; return { uid: UID++, card, atk: c.atk, hp: c.hp, max: c.hp, ready, ...extra }; };
// side 1 to move, his side 0; heroes [his, mine]
const base = (heroes = ['A', 'P'], mana = 10) => {
  const s = newMatch({ seed: 7, first: 1, heroes }); s.turn = 1;
  for (const p of s.p) { p.hand = []; p.board = []; }
  s.p[1].mana = s.p[1].maxMana = mana; return s;
};
const show = (acts) => acts.map(a => a.t === 'play' ? `play ${a.card}${a.target ? '→' + (a.target.side === 1 ? 'own' : 'his') + (a.target.i < 0 ? ' face' : ' m' + a.target.i) : ''}`
  : a.t === 'power' ? 'power' + (a.target ? '→m' + a.target.i : '') : `attack m${a.from}→${a.to < 0 ? 'face' : 'm' + a.to}`).join(', ') || '(nothing)';
const run = (s, acts, end = false) => { let t = s; for (const x of acts) { if (t.winner !== null) break; t = act(t, x); } if (end && t.winner === null) t = endTurn(t); return t; };
const wins = (s) => (a) => run(s, a, true).winner === 1;
let bad = 0;
const check = (name, s, ok) => {
  for (const [bn, b] of [['greedy', greedyBot], ['expert', expert]]) {
    let a, pass;
    try { a = b(s, rng); pass = ok(a); } catch (e) { a = []; pass = false; console.log(e.message); }
    if (!pass) bad++;
    console.log(`${pass ? 'ok  ' : 'FAIL'} ${bn.padEnd(6)} ${name}: ${show(a)}`);
  }
};

// lethal on board: he is at 7, my ready 4/5 and 3/4, his 6/7 tempts a trade
{ const s = base(); s.p[0].energy = 7; s.p[1].board = [mk('m4'), mk('m3')]; s.p[0].board = [mk('m6')]; s.p[1].hand = ['m2a', 'c3'];
  check('lethal on board, 4 + 3 into 7', s, wins(s)); }
// lethal with a spell: he is at 7, my ready 3/4, Deal 3 and Deal 2 with 3 mana
{ const s = base(['A', 'P'], 3); s.p[0].energy = 7; s.p[1].hand = ['s2', 's1', 'm3']; s.p[1].board = [mk('m3')]; s.p[0].board = [mk('m6'), mk('m1a')];
  check('lethal with spells, 3 + 3 + 2 into 7', s, wins(s)); }
// lethal through the Coin: he is at 6, Deal 6 (4 mana) with 3 mana and the Coin
{ const s = base(['A', 'P'], 3); s.p[0].energy = 6; s.p[1].hand = ['s4', 'COIN'];
  check('lethal through the Coin', s, wins(s)); }
// lethal with the hero power: Pyromancer, he is at 4, my ready 3/4, 3 mana: power, Baby Fireball for 1
{ const s = base(['A', 'P'], 3); s.p[0].energy = 4; s.p[1].board = [mk('m3')];
  check('lethal with a Fireball from the power', s, wins(s)); }
// lethal through a Taunt: he is at 6 behind a 2/4 Taunt; my ready 4/5, 3/4, 3/4: break it, swing 6
{ const s = base(['A', 'P'], 0); s.p[0].energy = 6; s.p[1].board = [mk('m4'), mk('m3'), mk('m3')]; s.p[0].board = [mk('t3')];
  check('lethal through a Taunt', s, wins(s)); }
// lethal through a Taunt impossible: he is at 7 behind a 3/5 Taunt; my ready 3/4, 3/4, Deal 2, 1 mana: no face burn
{ const s = base(['A', 'P'], 1); s.p[0].energy = 7; s.p[1].board = [mk('m3'), mk('m3')]; s.p[0].board = [mk('t4')]; s.p[1].hand = ['s1', 'm4'];
  check('no lethal through a 3/5 Taunt, no burn at face', s, a => !a.some(x => x.t === 'play' && x.target && x.target.i < 0)); }
// a free trade: his 2/1 against my ready 3/4, no lethal
{ const s = base(['A', 'P'], 0); s.p[1].board = [mk('m3')]; s.p[0].board = [mk('m1a')];
  check('free kill of a 2/1 with a 3/4', s, a => a.some(x => x.t === 'attack' && x.to === 0)); }
// turn 1, Deal 2 and a 2/1, empty boards: never burn face
{ const s = base(['A', 'P'], 1); s.p[1].hand = ['s1', 'm1a', 'm4']; s.p[1].powered = true;
  check('turn 1, empty boards: no face burn', s, a => !a.some(x => x.card === 's1' && x.target.i < 0)); }
// turn 2 with his 2/1 on the board, Deal 2 and a 2/3 in hand: the burn goes at the 2/1 if anywhere
{ const s = base(['A', 'P'], 2); s.p[1].hand = ['s1', 'm2b', 'm4']; s.p[0].board = [mk('m1a')];
  check('his 2/1 on the board: no face burn', s, a => !a.some(x => x.card === 's1' && x.target.i < 0)); }
// the 50 line: I am at 46 with Gain 5 (3 mana) and a 3/4
{ const s = base(['A', 'M'], 3); s.p[1].energy = 46; s.p[1].hand = ['m3', 'j3']; s.p[0].board = [mk('m4')];
  check('reach 50 with Gain 5 from 46', s, wins(s)); }
// the 50 line at the end of the turn: I am at 49, a 2/3 that gains 1 at turn end, 3 mana: anything but a loss
{ const s = base(['A', 'M'], 3); s.p[1].energy = 47; s.p[1].hand = ['e3', 'g3']; s.p[0].board = [mk('m4')];
  check('reach 50 with the 3/3 gain 3 from 47', s, wins(s)); }
// the Mage's fatigue: deck empty, fatigue 4 next, at 45, 3 mana: the power draws, fatigue gains 5
{ const s = base(['A', 'M'], 3); s.p[1].energy = 45; s.p[1].deck = []; s.p[1].fatigue = 4;
  check('Mage reaches 50 through fatigue', s, wins(s)); }
// his 50 line: he is at 49 with a 2/3 that gains 1 at turn end; I hold Deal 3 and a 3/4: kill the gainer
{ const s = base(['A', 'P'], 3); s.p[0].energy = 49; s.p[0].board = [mk('e3')]; s.p[1].hand = ['s2', 'm3'];
  check('kill his gainer before he crosses 50', s, a => run(s, a).p[0].board.length === 0); }
// unused mana goes into the power: Mage, 3 mana, nothing in hand
{ const s = base(['A', 'M'], 3);
  check('Mage, 3 mana, empty hand: power', s, a => a.some(x => x.t === 'power')); }
// Pyromancer, 3 mana, a 3-drop... no: 2 mana and only a 4-drop in hand
{ const s = base(['A', 'P'], 2); s.p[1].hand = ['m4'];
  check('Pyromancer, 2 mana, nothing to play: power', s, a => a.some(x => x.t === 'power')); }
// Angel Warrior, 1 mana, a minion on board, only a 4-drop in hand
{ const s = base(['P', 'A'], 1); s.p[1].hand = ['m4']; s.p[1].board = [mk('m3', false)];
  check('Angel Warrior, 1 mana spare: power', s, a => a.some(x => x.t === 'power')); }
console.log(bad ? bad + ' failures' : 'all pass');
process.exit(bad ? 1 : 0);
