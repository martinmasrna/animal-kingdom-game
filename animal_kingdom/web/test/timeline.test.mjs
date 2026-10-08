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

test('what removed a unit strikes from the very unit the engine names, never another copy of its card', () => {
  let n = 0;
  for (const { views } of matches) for (let i = 1; i < views.length; i++) {
    const fresh = newEvents(views[i - 1], views[i]); if (!fresh) continue;
    const named = fresh.filter(e => e.cause_iid != null && ['remove', 'bounce', 'to_deck'].includes(e.e) && e.cr);
    const struck = plan(views[i - 1], views[i]).filter(s => s.step && s.step.by && ['remove', 'bounce', 'to_deck'].includes(s.step.kind));
    for (const s of struck) {
      const e = named.find(e => e.cr === s.step.cr && e.card === s.step.card); if (!e) continue;
      assert.ok(s.view.game.board[s.step.by].some(u => u.iid === e.cause_iid), `strikes from unit ${e.cause_iid}`); n++;
    }
  }
  assert.ok(n > 5, `enough covered (${n})`);
});

test("what one effect puts down lands in one beat, and only the opponent's own plays are revealed (a Sardine swarm is neither)", () => {
  for (const { views } of matches) for (let i = 1; i < views.length; i++) {
    const fresh = newEvents(views[i - 1], views[i]); if (!fresh) continue;
    const them = views[i].you === 'A' ? 'B' : 'A', places = fresh.filter(e => e.e === 'place');
    const steps = plan(views[i - 1], views[i]).map(s => s.step).filter(Boolean);
    const groups = places.filter((e, k) => !e.cause || !(k && places[k - 1].cause === e.cause && places[k - 1].cause_iid === e.cause_iid && fresh.indexOf(places[k - 1]) === fresh.indexOf(e) - 1));
    const roams = fresh.filter(e => e.e === 'roam' && e.to).length;   // a roaming animal lands where it went too
    assert.equal(steps.filter(s => s.kind === 'land').length, groups.length + roams, 'one landing per play, per effect or per roam');
    assert.equal(steps.filter(s => s.kind === 'reveal').length, places.filter(e => e.player === them && ((e.from_hand && !e.cause) || e.reveal)).length, 'reveals');
  }
});

test('a strength change shows on a unit already on the board, from its flash on', () => {
  let seen = 0;
  const unitIn = (board, iid) => { for (const st of Object.values(board)) for (const u of st) if (u.iid === iid) return u; return null; };
  for (const { name, views } of matches) for (let i = 1; i < views.length; i++) {
    const prev = views[i - 1], next = views[i];
    if (!prev.game || !next.game || !newEvents(prev, next)) continue;
    const p = plan(prev, next), sum = {};
    for (const { view, step } of p) {
      if (!step || step.kind !== 'strength') continue;
      for (const ch of step.changes) if (ch.iid) sum[ch.iid] = (sum[ch.iid] || 0) + ch.n;
      for (const [iid, n] of Object.entries(sum)) {
        const before = unitIn(prev.game.board, +iid), now = unitIn(view.game.board, +iid);
        if (!before || !now) continue;
        assert.equal(now.str, before.str + n, `${name} view ${i}: ${now.id} shows ${now.str}, was ${before.str}, changed by ${n}`);
        seen++;
      }
    }
  }
  assert.ok(seen > 0, 'some strength change on a unit already on the board');
});
