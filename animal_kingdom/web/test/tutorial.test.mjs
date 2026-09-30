// The tutorial's coach (static/tutorial.js): which lesson shows when, and what a forced lesson lets happen.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { current, gate } from '../static/tutorial.js';

const CARDS = { lion: { text: '' }, cape_buffalo: { text: '' }, dire_wolf: { text: '' }, jaguar: { text: 'Roar: remove an adjacent enemy of strength 4 or less.' } };
const u = (id, owner) => [{ id, owner, str: 7 }];
const view = (g = {}) => ({ you: 'A', phase: 'playing', game: { round: 1, current: 'A', toAct: 'A', pending: null, actionsLeft: 2, board: {}, hand: [],
  history: [], legal: { place: { lion: [['cr', '1,1'], ['cr', '1,2'], ['cr', '1,3']] }, draw: true }, ...g } });
const fresh = () => ({ seen: new Set(), shown: {} });

test('the first lessons walk the first turn: pick the Lion, then its one crossroad', () => {
  const t = fresh();
  assert.equal(current(view(), null, CARDS, t).id, 'lion');
  assert.deepEqual(current(view(), 'lion', CARDS, t).only, { card: 'lion', cr: '1,2' });
  assert.equal(current(view({ board: { '1,2': u('lion', 'A') } }), null, CARDS, t).id, 'buffalo');
});

test('a forced lesson narrows the moves to its card and crossroad, or the deck, and never ends the turn', () => {
  const d = gate({ places: { lion: [['cr', '1,1'], ['cr', '1,2']], dire_wolf: [['cr', '1,1']] } }, { card: 'lion', cr: '1,2' });
  assert.deepEqual(d.places, { lion: [['cr', '1,2']] }); assert.ok(d.noDraw && d.noPass);
  const e = gate({ places: { lion: [['cr', '1,1']] } }, { deck: true });
  assert.deepEqual(e.places, {}); assert.ok(!e.noDraw);
});

test('nothing is taught off your turn, and a lesson read once stays away after you act', () => {
  const t = fresh();
  assert.equal(current(view({ current: 'B', toAct: 'B', legal: null }), null, CARDS, t), null);
  const board = { '1,1': u('dire_wolf', 'A'), '1,2': u('lion', 'A'), '2,1': u('jaguar', 'A'), '2,2': u('cape_buffalo', 'A') };
  const r4 = { round: 4, board, legal: { place: {}, draw: true } };
  assert.equal(current(view(r4), null, CARDS, t).id, 'food');
  assert.equal(current(view({ ...r4, history: [{ seat: 'A' }] }), null, CARDS, t), null, 'gone after your next move');
});

test('the open den is pointed out whenever it can be taken', () => {
  const t = fresh(); ['lion', 'lion2', 'buffalo', 'wolf', 'draw', 'corner', 'food', 'cover', 'roar'].forEach(id => t.seen.add(id));
  const L = current(view({ round: 6, legal: { place: { lion: [['hq', 'B']] }, draw: true } }), null, CARDS, t);
  assert.equal(L.id, 'den'); assert.deepEqual(L.focus, { den: 'B' });
});
