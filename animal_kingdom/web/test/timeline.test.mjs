// The animation timeline (static/timeline.js): the steps a new view plays, each with the board, the food and the hands as
// they stood after it.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { plan } from '../static/timeline.js';

// `count`: each seat's hand size; `hand`: the seat's own cards
const view = (hand, count, foodB, events) => ({ id: 'M', you: 'A', phase: 'playing', rematches: 0,
  game: { board: {}, food: { A: 15, B: foodB }, income: { A: 0, B: 0 }, handCount: count, hand, current: 'A',
    history: [], events } });

test('a raid from the hand leaves the hand before anything of it plays (Martin, 2026-11-22: the card came back during its raid)', () => {
  const raider = { iid: 7, id: 'flight_3', str: 3 }, other = { iid: 8, id: 'wisp_1', str: 2 };
  const prev = view([raider, other], { A: 2, B: 4 }, 15, [{ seq: 1, e: 'turn_start', player: 'A' }]);
  const next = view([other], { A: 1, B: 4 }, 12, [...prev.game.events,
    { seq: 2, e: 'raid', player: 'A', iid: 7, card: 'flight_3', den: 'B', to: 'A', str: 3, n: 3, from_hand: true }]);
  const steps = plan(prev, next);
  assert.ok(steps.length > 1, 'the raid plays as a step');
  for (const { view: v } of steps) assert.deepEqual(v.game.hand.map(h => h.iid), [8], 'the raider is out of the hand in every step');
});

test("their raid from the hand takes a card off their hand's count as it plays", () => {
  const prev = { ...view([], { A: 4, B: 0 }, 15, [{ seq: 1, e: 'turn_start', player: 'B' }]), you: 'B' };
  const next = { ...view([], { A: 3, B: 0 }, 15, [...prev.game.events,
    { seq: 2, e: 'raid', player: 'A', iid: 9, card: 'flight_2', den: 'B', to: 'A', str: 2, n: 2, from_hand: true }]), you: 'B' };
  for (const { view: v, step } of plan(prev, next)) if (step) assert.equal(v.game.handCount.A, 3);
});

test('the food a raid steals or fatigue costs lands in the other den in the same step (Martin, 2026-11-24)', () => {
  const raider = { iid: 7, id: 'flight_3', str: 3 };
  const prev = view([raider], { A: 1, B: 4 }, 15, [{ seq: 1, e: 'turn_start', player: 'A' }]);
  const next = view([], { A: 0, B: 4 }, 10, [...prev.game.events,
    { seq: 2, e: 'raid', player: 'A', iid: 7, card: 'flight_3', den: 'B', str: 3, n: 3, from_hand: true, to: 'A' },
    { seq: 3, e: 'food', player: 'B', n: -2, fatigue: 2, to: 'A' }]);
  next.game.food.A = 20;
  const taken = plan(prev, next).filter(s => s.step && s.step.kind === 'raid');
  assert.deepEqual(taken.map(s => [s.step.den, s.step.to, s.step.n]), [['B', 'A', 3], ['B', 'A', 2]]);
  assert.deepEqual(taken.map(s => s.view.game.food), [{ A: 18, B: 12 }, { A: 20, B: 10 }]);
});

test("their chosen target plays as an aim step from its source, before the effect; your own plays none (you aimed it)", () => {
  const hunter = { iid: 5, id: 'hunter_5', owner: 'B', str: 4 }, prey = { iid: 6, id: 'wisp_3', owner: 'A', str: 6 };
  const base = (events, board) => ({ ...view([], { A: 3, B: 3 }, 15, events), game: { ...view([], { A: 3, B: 3 }, 15, events).game, board } });
  const prev = base([{ seq: 1, e: 'turn_start', player: 'B' }], { '3,2': [hunter], '2,2': [prey] });
  const aim = (player, seq) => ({ seq, e: 'aim', player, cr: '2,2', iid: 6, card: 'wisp_3', cause: 'hunter_5', cause_iid: 5 });
  const hit = seq => ({ seq, e: 'strength', iid: 6, card: 'wisp_3', owner: 'A', n: -4, cause: 'hunter_5', cause_iid: 5 });
  const theirs = plan(prev, base([...prev.game.events, aim('B', 2), hit(3)], { '3,2': [hunter], '2,2': [{ ...prey, str: 2 }] })).filter(s => s.step);
  assert.deepEqual(theirs.map(s => s.step.kind), ['aim']);
  assert.deepEqual([theirs[0].step.from, theirs[0].step.cr, theirs[0].step.player], ['3,2', '2,2', 'B']);
  assert.equal(theirs[0].view.game.board['2,2'][0].str, 6, 'the arrow shows before the effect');
  const mine = plan(prev, base([...prev.game.events, aim('A', 2), hit(3)], prev.game.board)).filter(s => s.step);
  assert.deepEqual(mine.map(s => s.step.kind), []);
});

test("a leader's passive firing plays as a trigger step before what it does (Martin, 2026-11-24: the Assassin's draw went by unseen)", () => {
  const raider = { iid: 7, id: 'flight_1', str: 1 }, drawn = { iid: 9, id: 'wisp_1', str: 2 };
  const prev = view([raider], { A: 1, B: 4 }, 15, [{ seq: 1, e: 'turn_start', player: 'A' }]);
  const next = view([drawn], { A: 1, B: 4 }, 14, [...prev.game.events,
    { seq: 2, e: 'raid', player: 'A', iid: 7, card: 'flight_1', den: 'B', to: 'A', str: 1, n: 1, from_hand: true },
    { seq: 3, e: 'leader_trigger', player: 'A', card: 'assassin_legend' },
    { seq: 4, e: 'draw', player: 'A', cards: [[9, 'wisp_1']] }]);
  const kinds = plan(prev, next).filter(s => s.step).map(s => s.step.kind);
  assert.deepEqual(kinds.slice(kinds.indexOf('trigger')), ['trigger', 'draw']);
  assert.equal(plan(prev, next).find(s => s.step && s.step.kind === 'trigger').step.player, 'A');
});
