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
    { seq: 2, e: 'raid', player: 'A', iid: 7, card: 'flight_3', den: 'B', str: 3, n: 3, from_hand: true }]);
  const steps = plan(prev, next);
  assert.ok(steps.length > 1, 'the raid plays as a step');
  for (const { view: v } of steps) assert.deepEqual(v.game.hand.map(h => h.iid), [8], 'the raider is out of the hand in every step');
});

test("their raid from the hand takes a card off their hand's count as it plays", () => {
  const prev = { ...view([], { A: 4, B: 0 }, 15, [{ seq: 1, e: 'turn_start', player: 'B' }]), you: 'B' };
  const next = { ...view([], { A: 3, B: 0 }, 15, [...prev.game.events,
    { seq: 2, e: 'raid', player: 'A', iid: 9, card: 'flight_2', den: 'B', str: 2, n: 2, from_hand: true }]), you: 'B' };
  for (const { view: v, step } of plan(prev, next)) if (step) assert.equal(v.game.handCount.A, 3);
});
