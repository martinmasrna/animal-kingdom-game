// Roam in the client (keywords.md): the timeline moves the animal from where it stood to where it went, and a den taken by
// roaming takes nothing from the hand. No real card roams yet, so these views are made by hand.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { plan } from '../static/timeline.js';
import { KEYWORDS } from '../static/card.js';

const view = (board, events, extra = {}) => ({ id: 'm', you: 'A', phase: 'playing', results: [], game: {
  board, food: { A: 0, B: 0 }, handCount: { A: 2, B: 3 }, hand: [{ iid: 9, id: 'lion', str: 7 }, { iid: 10, id: 'lion', str: 7 }],
  current: 'A', history: [], events, ...extra } });
const wolf = { iid: 5, id: 'gray_wolf', owner: 'A', str: 4 }, mouse = { iid: 6, id: 'mouse', owner: 'B', str: 2 };

test('a roam moves the animal along its path and lands it there, covering what it beat', () => {
  const prev = view({ '1,2': [wolf], '2,2': [mouse] }, [{ e: 'turn_start', player: 'A', seq: 1 }]);
  const next = view({ '2,2': [mouse, wolf] }, [{ e: 'turn_start', player: 'A', seq: 1 },
    { e: 'roam', player: 'A', iid: 5, card: 'gray_wolf', cr: '1,2', to: '2,2', seq: 2 },
    { e: 'cover', cr: '2,2', iid: 6, card: 'mouse', owner: 'B', by: 5, seq: 3 }]);
  const steps = plan(prev, next);
  assert.equal(steps.length, 2);
  assert.deepEqual(steps[0].step, { kind: 'land', dur: 0.5, cr: '2,2', card: 'gray_wolf', player: 'A', from: '1,2' });
  assert.deepEqual(steps[0].view.game.board, { '2,2': [mouse, wolf] });
  assert.equal(steps[0].view.game.handCount.A, 2, 'nothing left the hand');
});

test('a den taken by roaming leaves the hand alone', () => {
  const prev = view({ '4,2': [wolf] }, [{ e: 'turn_start', player: 'A', seq: 1 }]);
  const next = view({ '4,2': [wolf] }, [{ e: 'turn_start', player: 'A', seq: 1 },
    { e: 'roam', player: 'A', iid: 5, card: 'gray_wolf', cr: '4,2', to: null, den: 'B', seq: 2 },
    { e: 'capture', player: 'A', iid: 5, card: 'gray_wolf', den: 'B', str: 4, roam: true, seq: 3 }]);
  const steps = plan(prev, next).map(s => s.step).filter(Boolean);
  assert.deepEqual(steps.map(s => s.kind), ['capture']);
  assert.equal(plan(prev, next)[0].view.game.handCount.A, 2);
});

test('the new keywords are explained', () => {
  for (const k of ['Roam', 'Reach', 'Poison', 'Dawn', 'Dusk']) assert.ok(KEYWORDS[k], k);
});
