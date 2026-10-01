// The animation timeline (static/timeline.js), checked on whole recorded bot matches (record_views.py: exactly what a
// browser receives), no browser: between any two views the steps rebuild the new view's board, food and hands from the
// events alone, and the order is the game's.
import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import { recordMatches } from './harness.mjs';
import { plan, newEvents } from '../static/timeline.js';

let matches;
before(() => { matches = recordMatches(7); });
const ids = board => Object.fromEntries(Object.entries(board).map(([cr, st]) => [cr, st.map(u => u.iid)]).filter(([, l]) => l.length).sort());

test('between every pair of views the steps rebuild the new board, food and hand from the events', () => {
  let pairs = 0, steps = 0;
  for (const { name, views } of matches) for (let i = 1; i < views.length; i++) {
    const prev = views[i - 1], next = views[i];
    if (!prev.game || !next.game || !newEvents(prev, next)) continue;
    const p = plan(prev, next);
    assert.equal(p[p.length - 1].view, next, 'the last step is the new view itself');
    if (p.length < 2) continue;
    const last = p[p.length - 2].view.game;
    assert.deepEqual(ids(last.board), ids(next.game.board), `${name} view ${i}: the board`);
    assert.deepEqual(last.food, next.game.food, `${name} view ${i}: the food`);
    assert.deepEqual(last.handCount, next.game.handCount, `${name} view ${i}: the hand counts`);
    assert.deepEqual(last.hand.map(h => h.iid).sort(), next.game.hand.map(h => h.iid).sort(), `${name} view ${i}: your hand`);
    pairs++; steps += p.length - 1;
  }
  assert.ok(pairs > 100 && steps > pairs, `enough covered (${pairs} view changes, ${steps} steps)`);
});

test("'Your turn' comes after everything the opponent did, and before what your turn's start sets off", () => {
  for (const { views } of matches) for (let i = 1; i < views.length; i++) {
    const kinds = plan(views[i - 1], views[i]).map(s => s.step && s.step.kind).filter(Boolean);
    const t = kinds.indexOf('yourturn');
    if (t < 0) continue;
    const before = plan(views[i - 1], views[i]).slice(0, t).map(s => s.step);
    assert.ok(before.every(s => s.kind !== 'reveal' || s.player !== views[i].you), 'only the opponent acts before your turn');
    assert.equal(kinds.lastIndexOf('reveal') < t || !kinds.slice(t).includes('reveal'), true, 'no opponent card is revealed after it');
  }
});

test('an opponent placement is shown large, then lands; a view with nothing new is just itself', () => {
  let seen = 0;
  for (const { views } of matches) for (let i = 1; i < views.length; i++) {
    const p = plan(views[i - 1], views[i]).map(s => s.step).filter(Boolean);
    p.forEach((s, j) => { if (s.kind === 'reveal') { seen++; assert.equal(p[j + 1].kind, 'land'); assert.equal(p[j + 1].cr, s.cr); } });
  }
  assert.ok(seen > 10);
  const v = matches[0].views[5];
  assert.equal(plan(v, v).length, 1);
});
