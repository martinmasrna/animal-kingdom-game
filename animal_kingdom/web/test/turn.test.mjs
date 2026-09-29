// Unit tests for turn.js: the den's pit states, held regions, what changed on the board, and income flights.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pitStates, heldRegions, boardChanges, incomeFlights } from '../static/turn.js';

const u = (iid, owner, str = 3, id = 'lion') => ({ iid, id, owner, str });

test('pits fill ten fruit each from the bottom, ghosts continue where the ripe fruit stop', () => {
  const p = pitStates(43, 25, 100);
  assert.equal(p.length, 10);
  assert.deepEqual(p.slice(0, 6), [{ ripe: 10, ghost: 0 }, { ripe: 10, ghost: 0 }, { ripe: 10, ghost: 0 }, { ripe: 10, ghost: 0 }, { ripe: 3, ghost: 7 }, { ripe: 0, ghost: 10 }]);
  assert.deepEqual(p[6], { ripe: 0, ghost: 8 });
  assert.deepEqual(p.slice(7), [{ ripe: 0, ghost: 0 }, { ripe: 0, ghost: 0 }, { ripe: 0, ghost: 0 }]);
  const total = p.reduce((a, x) => a + x.ripe, 0), ghosts = p.reduce((a, x) => a + x.ghost, 0);
  assert.equal(total, 43); assert.equal(ghosts, 25);
});

test('pits never hold more than the win total, ghosts included', () => {
  const p = pitStates(93, 30, 100);
  assert.equal(p.reduce((a, x) => a + x.ripe + x.ghost, 0), 100);
  assert.deepEqual(p[9], { ripe: 3, ghost: 7 });
  assert.equal(pitStates(130, 10, 100).reduce((a, x) => a + x.ripe, 0), 100);
  assert.deepEqual(pitStates(0, 0, 100).every(x => x.ripe === 0 && x.ghost === 0), true);
});

test('a region is held when the top unit of all four corners is one player\'s', () => {
  const regions = [{ id: 'R1', c: [1, 1], food: 10 }, { id: 'R2', c: [2, 1], food: 15 }];
  const board = { '1,1': [u(1, 'A')], '2,1': [u(2, 'A')], '1,2': [u(3, 'A')], '2,2': [u(9, 'B'), u(4, 'A')], '3,1': [u(5, 'B')], '3,2': [u(6, 'A')] };
  assert.deepEqual(heldRegions(regions, board).map(r => [r.id, r.owner]), [['R1', 'A']]);
  board['2,2'].push(u(7, 'B'));   // covered: the top decides
  assert.deepEqual(heldRegions(regions, board), []);
});

test('a new top unit lands; one placed on a unit also covers it', () => {
  const before = { '1,1': [u(1, 'A')], '2,2': [u(2, 'B')] };
  const after = { '1,1': [u(1, 'A')], '2,2': [u(2, 'B'), u(3, 'A')], '3,3': [u(4, 'A')] };
  const ch = boardChanges(before, after);
  assert.deepEqual([...ch.landed].sort(), ['2,2', '3,3']);
  assert.deepEqual([...ch.covered], ['2,2']);
  assert.deepEqual(ch.leaving, []);
});

test('a unit gone from the board leaves: removed, or bounced when a bounce effect names it', () => {
  const before = { '1,1': [u(1, 'A', 3, 'mouse')], '2,1': [u(2, 'B', 5, 'fox')] };
  const after = {};
  const ch = boardChanges(before, after, [{ k: 'bounce', card: 'fox', owner: 'B' }]);
  assert.deepEqual(ch.leaving.map(l => [l.cr, l.how]), [['1,1', 'removed'], ['2,1', 'bounce']]);
});

test('a unit moved under another is still on the board, so it does not leave', () => {
  const before = { '1,1': [u(1, 'A')] }, after = { '1,1': [u(1, 'A'), u(2, 'B')] };
  assert.deepEqual(boardChanges(before, after).leaving, []);
});

test('a strength change is noted up or down, on units still on the board', () => {
  const before = { '1,1': [u(1, 'A', 3)], '2,1': [u(2, 'A', 5)] }, after = { '1,1': [u(1, 'A', 4)], '2,1': [u(2, 'A', 2)] };
  assert.deepEqual([...boardChanges(before, after).strength], [[1, 'up'], [2, 'down']]);
});

test('with no previous view nothing changed', () => {
  const ch = boardChanges(null, { '1,1': [u(1, 'A')] });
  assert.equal(ch.landed.size + ch.covered.size + ch.leaving.length + ch.strength.size, 0);
});

test('one fruit flies per food gained, from the held stones, to the pit it fills', () => {
  const f = incomeFlights(18, 43, 100, [{ food: 15 }, { food: 10 }]);
  assert.equal(f.length, 25);
  assert.deepEqual([f[0].pit, f[1].pit, f[2].pit, f[24].pit], [1, 1, 2, 4]);   // food 18 is in pit 1; the 25th fruit makes food 43
  assert.equal(f.filter(x => x.from === 0).length, 15);
  assert.ok(f.every((x, j) => x.delay === j * 0.035));
});

test('no flights without a held stone, a gain, or room below the win total', () => {
  assert.deepEqual(incomeFlights(10, 40, 100, []), []);
  assert.deepEqual(incomeFlights(40, 40, 100, [{ food: 10 }]), []);
  assert.equal(incomeFlights(95, 125, 100, [{ food: 15 }, { food: 15 }]).length, 5);
});
