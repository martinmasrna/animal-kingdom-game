// The tutorial's coach (static/tutorial.js): which lesson shows when, and what a forced lesson lets happen.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { current, gate } from '../static/tutorial.js';

const CARDS = { lion: { text: '' }, cape_buffalo: { text: '' }, dire_wolf: { text: '' }, jaguar: { text: 'Roar: remove an adjacent enemy of strength 4 or less.' } };
const u = (id, owner) => [{ id, owner, str: 7 }];
const view = (g = {}) => ({ you: 'A', phase: 'playing', game: { round: 1, current: 'A', toAct: 'A', pending: null, actionsLeft: 2, board: {}, hand: [],
  history: [], legal: { place: { lion: [['cr', '1,1'], ['cr', '1,2'], ['cr', '1,3']] }, draw: true }, ...g } });
const fresh = () => ({ seen: new Set(), shown: {} });

test('the opening names what is on screen, one Next at a time, with nothing else to click', () => {
  const t = fresh(), ids = [];
  for (let L = current(view(), null, CARDS, t); L && L.next; L = current(view(), null, CARDS, t)) { ids.push(L.id); assert.deepEqual(L.only, {}); t.seen.add(L.id); }
  assert.deepEqual(ids, ['welcome', 'yourden', 'theirden', 'foodcount', 'cards']);
});

test('the first lessons walk the first turn, ringing every place the rules allow', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'cards'].forEach(id => t.seen.add(id));
  assert.equal(current(view(), null, CARDS, t).id, 'lion');
  assert.deepEqual(current(view(), 'lion', CARDS, t).only, { card: 'lion' }, 'all three crossroads by the den');
  const L = current(view({ board: { '1,2': u('lion', 'A') }, legal: { place: { cape_buffalo: [['cr', '1,1'], ['cr', '1,2'], ['cr', '1,3'], ['cr', '2,2']] }, draw: true } }), 'cape_buffalo', CARDS, t);   // 1,2 is the Lion's own
  assert.equal(L.id, 'buffalo'); assert.deepEqual(L.only, { card: 'cape_buffalo', picked: true, crs: ['1,1', '1,3', '2,2'] }); assert.deepEqual(L.at, { cr: '2,2' }, 'the coach stands beside the rightmost ring');
});

test('the Wolf goes on the food region the first animals started, wherever that is', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'cards'].forEach(id => t.seen.add(id));
  const place = { dire_wolf: [['cr', '1,1'], ['cr', '2,2'], ['cr', '2,3']] }, hand = [{ id: 'dire_wolf' }];
  const upper = current(view({ round: 2, hand, board: { '1,2': u('lion', 'A'), '1,3': u('cape_buffalo', 'A') }, legal: { place, draw: true } }), null, CARDS, t);
  assert.deepEqual(upper.only, { card: 'dire_wolf', picked: true, crs: ['2,2', '2,3'] });
  const lower = current(view({ round: 2, hand, board: { '1,2': u('lion', 'A'), '2,2': u('cape_buffalo', 'A') }, legal: { place, draw: true } }), null, CARDS, t);
  assert.deepEqual(lower.only, { card: 'dire_wolf', picked: true, crs: ['1,1'] });
});

test('a forced lesson narrows the moves to its card and crossroad, or the deck, and never ends the turn', () => {
  const d = gate({ places: { lion: [['cr', '1,1'], ['cr', '1,2']], dire_wolf: [['cr', '1,1']] } }, { card: 'lion', crs: ['1,2'] });
  assert.deepEqual(d.places, { lion: [['cr', '1,2']] }); assert.ok(d.noDraw && d.noPass);
  const e = gate({ places: { lion: [['cr', '1,1']] } }, { deck: true });
  assert.deepEqual(e.places, {}); assert.ok(!e.noDraw);
});

test('nothing is taught off your turn, and a lesson read once stays away after you act', () => {
  const t = fresh();
  assert.equal(current(view({ round: 2, current: 'B', toAct: 'B', legal: null }), null, CARDS, t), null);
  assert.equal(current(view({ current: 'B', toAct: 'B', legal: null }), null, CARDS, t).id, 'watch', 'the opponent\'s first turn is announced');
  const board = { '1,1': u('dire_wolf', 'A'), '1,2': u('lion', 'A'), '2,1': u('jaguar', 'A'), '2,2': u('cape_buffalo', 'A') };
  const r4 = { round: 4, board, legal: { place: {}, draw: true } };
  t.seen.add('actions');
  assert.equal(current(view(r4), null, CARDS, t).id, 'food');
  assert.equal(current(view({ ...r4, history: [{ seat: 'A' }] }), null, CARDS, t), null, 'gone after your next move');
});

test('the open den is pointed out whenever it can be taken', () => {
  const t = fresh(); ['lion', 'lion2', 'buffalo', 'wolf', 'draw', 'actions', 'corner', 'food', 'cover', 'roar'].forEach(id => t.seen.add(id));
  const L = current(view({ round: 6, legal: { place: { lion: [['hq', 'B']] }, draw: true } }), null, CARDS, t);
  assert.equal(L.id, 'den'); assert.deepEqual(L.at, { den: 'B' });
});

test('a Roar asking for a target is explained beside its choice', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'cards'].forEach(id => t.seen.add(id));
  const L = current(view({ round: 4, pending: { mode: 'choice', kind: 'target', source: 'jaguar', options: [] }, legal: { place: {}, draw: false } }), null, CARDS, t);
  assert.equal(L.id, 'target'); assert.deepEqual(L.at, { prompt: true });
});
