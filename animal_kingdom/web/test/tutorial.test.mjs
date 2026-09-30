// The tutorial's coach (static/tutorial.js): which lesson shows when, and what a forced lesson lets happen.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { current, gate, held } from '../static/tutorial.js';

const CARDS = { squirrel: { text: 'Roar: gain 10 food.' }, jaguar: { text: 'Roar: remove an adjacent enemy of strength 4 or less.' }, lynx: { text: 'Roar: if you control another Cat, draw 1.' }, lion: { text: '' }, cape_buffalo: { text: '' }, dire_wolf: { text: '' }, jaguar: { text: 'Roar: remove an adjacent enemy of strength 4 or less.' } };
const u = (id, owner) => [{ id, owner, str: 7 }];
const view = (g = {}, bot = 'tutorial') => ({ you: 'A', phase: 'playing', seats: { A: {}, B: { bot } }, game: { round: 1, current: 'A', toAct: 'A', pending: null, actionsLeft: 2, board: {}, hand: [],
  history: [], legal: { place: { lion: [['cr', '1,1'], ['cr', '1,2'], ['cr', '1,3']] }, draw: true }, ...g } });
const fresh = () => ({ seen: new Set(), shown: {} });

test('the opening names what is on screen, one Next at a time, with nothing else to click', () => {
  const t = fresh(), ids = [];
  for (let L = current(view(), null, CARDS, t); L && L.next; L = current(view(), null, CARDS, t)) { ids.push(L.id); assert.deepEqual(L.only, {}); t.seen.add(L.id); }
  assert.deepEqual(ids, ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards']);
});

test('the first lessons walk the first turn, ringing every place the rules allow', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards'].forEach(id => t.seen.add(id));
  assert.equal(current(view(), null, CARDS, t).id, 'lion');
  assert.deepEqual(current(view(), 'lion', CARDS, t).only, { card: 'lion' }, 'all three crossroads by the den');
  const L = current(view({ board: { '1,2': u('lion', 'A') }, legal: { place: { cape_buffalo: [['cr', '1,1'], ['cr', '1,2'], ['cr', '1,3'], ['cr', '2,2']] }, draw: true } }), 'cape_buffalo', CARDS, t);   // 1,2 is the Lion's own
  assert.equal(L.id, 'buffalo'); assert.deepEqual(L.only, { card: 'cape_buffalo', picked: true, crs: ['1,1', '1,3', '2,2'] }); assert.deepEqual(L.at, { rings: true }, 'the coach stands beside the whole group of rings');
});

test('the Wolf goes on the food region the first animals started, wherever that is', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'patch'].forEach(id => t.seen.add(id));
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
  const r4 = { round: 5, board, legal: { place: {}, draw: true } };
  t.seen.add('actions');
  const food = current(view(r4), null, CARDS, t);
  assert.equal(food.id, 'food'); assert.ok(food.next, 'a line that only tells waits for Next');
  t.seen.add('food'); assert.equal(current(view(r4), null, CARDS, t).id, 'empty', 'then, with nothing to place, points at the deck');
});

test('the open den is pointed out whenever it can be taken', () => {
  const t = fresh(); ['lion', 'lion2', 'buffalo', 'wolf', 'draw', 'actions', 'corner', 'food', 'free', 'cover', 'roar'].forEach(id => t.seen.add(id));
  const L = current(view({ round: 6, legal: { place: { lion: [['hq', 'B']] }, draw: true } }), null, CARDS, t);
  assert.equal(L.id, 'den'); assert.deepEqual(L.at, { den: 'B' });
});

test('a Roar asking for a target is explained beside its choice', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards'].forEach(id => t.seen.add(id));
  const L = current(view({ round: 4, pending: { mode: 'choice', kind: 'target', source: 'jaguar', options: [] }, legal: { place: {}, draw: false } }), null, CARDS, t);
  assert.equal(L.id, 'target'); assert.deepEqual(L.at, { prompt: true });
});

test('the last corner of the first patch is a step of its own: any card, only that crossroad, until it is done', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'patch', 'actions'].forEach(id => t.seen.add(id));
  const board = { '1,3': u('lion', 'A'), '2,3': u('cape_buffalo', 'A'), '2,2': u('dire_wolf', 'A') };
  const place = { jaguar: [['cr', '1,2'], ['cr', '2,1']], lion: [['cr', '1,2'], ['cr', '1,1']] };
  for (const round of [3, 4]) {   // still asked on turn 4 if turn 3 went elsewhere
    const L = current(view({ round, board, hand: [{ id: 'jaguar' }, { id: 'lion' }], legal: { place, draw: true } }), null, CARDS, t);
    assert.equal(L.id, 'corner'); assert.deepEqual(L.only, { crs: ['1,2'] });
  }
  const d = gate({ places: place }, { crs: ['1,2'] });
  assert.deepEqual(d.places, { jaguar: [['cr', '1,2']], lion: [['cr', '1,2']] });
});

test('with nothing to place, the coach points at the deck, every time', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'patch', 'actions', 'free'].forEach(id => t.seen.add(id));
  const stuck = view({ round: 5, board: { '1,3': u('lion', 'A') }, hand: [], legal: { place: {}, draw: true } });
  assert.equal(current(stuck, null, CARDS, t).id, 'empty');
  assert.equal(current(stuck, null, CARDS, t).id, 'empty', 'never used up');
});

test('covering and Roar are each done once by hand: the Pup beside the patch, then the Lynx', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'patch', 'actions', 'food'].forEach(id => t.seen.add(id));
  const board = { '1,1': u('dire_wolf', 'A'), '1,2': u('lion', 'A'), '2,1': u('lion', 'A'), '2,2': u('cape_buffalo', 'A'), '3,2': [{ id: 'pup', owner: 'B', str: 1 }] };
  const cover = current(view({ round: 3, board, hand: [{ id: 'cape_buffalo' }], legal: { place: { cape_buffalo: [['cr', '3,2'], ['cr', '3,1']] }, draw: true } }), null, CARDS, t);
  assert.equal(cover.id, 'cover'); assert.deepEqual(cover.only, { card: 'cape_buffalo', picked: true, crs: ['3,2'] });
  const covered = [{ seat: 'A', kind: 'place', card: 'cape_buffalo', fx: [{ k: 'cover' }] }];
  const g4 = { round: 4, board, history: covered, hand: [{ id: 'lynx' }], legal: { place: { lynx: [['cr', '3,1'], ['cr', '1,3']] }, draw: true } };
  const info = current(view(g4), null, CARDS, t);
  assert.equal(info.id, 'roarinfo'); assert.equal(info.read, 'lynx', 'the card is shown large beside the explanation'); t.seen.add('roarinfo');
  const roar = current(view(g4), null, CARDS, t);
  assert.equal(roar.id, 'roar'); assert.deepEqual(roar.only, { card: 'lynx', picked: true, crs: ['3,1', '1,3'] });
  const roared = current(view({ round: 4, board, history: [...covered, { seat: 'A', kind: 'place', card: 'lynx', fx: [] }], hand: [], legal: { place: {}, draw: true } }), null, CARDS, t);
  assert.equal(roared.id, 'roared'); assert.ok(roared.next);
});

// ---- lesson 2
const v2 = g => view(g, 'tutorial2');
const falcon = { id: 'eagle', owner: 'B', str: 5 }, squirrel = { id: 'squirrel', owner: 'A', str: 3 };

test('lesson 2 holds each teaching card back until its own step', () => {
  const V = v2({ hand: [{ id: 'black_mamba' }, { id: 'eagle' }, { id: 'lion' }] });
  assert.deepEqual(held(V, null), ['lynx', 'squirrel', 'black_mamba', 'eagle', 'tiger']);
  assert.ok(!held(V, { only: { card: 'black_mamba' } }).includes('black_mamba'), 'released while its step shows');
  assert.deepEqual(held(view({}), null), [], 'lesson 1 holds nothing');
});

test('lesson 2 puts each animal on its one crossroad, the Eagle anywhere', () => {
  const t = fresh(); t.seen.add('intro2');
  assert.deepEqual(current(v2({ hand: [{ id: 'lion' }] }), null, CARDS, t).only, { card: 'lion', picked: true, crs: ['1,2'] });
  ['lion', 'glow', 'lynx', 'eagleinfo'].forEach(id => t.seen.add(id));
  const L = current(v2({ round: 2, board: { '5,1': [{ id: 'dire_wolf', owner: 'B', str: 7 }] }, hand: [{ id: 'eagle' }], legal: { place: { eagle: [['cr', '1,1'], ['cr', '4,3'], ['cr', '5,1'], ['cr', '3,2']] }, draw: true } }), null, CARDS, t);
  assert.equal(L.id, 'eagle'); assert.deepEqual(L.only.crs, ['1,1', '4,3'], 'anywhere empty, but the spots the lesson needs later');
});

test('a covered Squirrel is shown, then uncovered by the Jaguar placed next to the Falcon', () => {
  const t = fresh(); ['intro2', 'glow', 'lynx', 'lion', 'eagleinfo', 'eagle', 'buffalo2', 'draw2', 'squirrelinfo', 'squirrel', 'foodroar', 'mambainfo'].forEach(id => t.seen.add(id));
  const board = { '1,2': u('lion', 'A'), '2,2': [squirrel, falcon] };
  const hist = [{ seat: 'A', kind: 'place', card: 'squirrel', fx: [] }, { seat: 'B', kind: 'place', card: 'eagle', fx: [{ k: 'cover', card: 'squirrel' }] }];
  const g = { round: 3, board, history: hist, hand: [{ id: 'black_mamba' }], legal: { place: { black_mamba: [['cr', '1,1'], ['cr', '2,1'], ['cr', '1,3']] }, draw: true } };
  const covered = current(v2(g), null, CARDS, t);
  assert.equal(covered.id, 'covered'); assert.deepEqual(covered.at, { cr: '2,2' }); t.seen.add('covered');
  const jag = current(v2(g), null, CARDS, t);
  assert.equal(jag.id, 'mamba'); assert.deepEqual(jag.only.crs, ['2,1'], 'only the empty crossroads next to the Falcon');
  const back = current(v2({ ...g, board: { '1,2': u('lion', 'A'), '2,2': [squirrel] } }), null, CARDS, t);
  assert.equal(back.id, 'uncovered');
});

test('after the Roar, lesson 1 marches on the den: only the furthest crossroads, then only the den', () => {
  const t = fresh(); ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'lion', 'lion2', 'buffalo', 'wolf', 'draw', 'actions', 'corner', 'food', 'cover', 'roarinfo', 'roar', 'roared', 'free'].forEach(id => t.seen.add(id));
  const hist = [{ seat: 'A', kind: 'place', card: 'lynx', fx: [] }];
  const march = current(view({ round: 5, history: hist, board: { '3,2': u('lion', 'A') }, legal: { place: { lion: [['cr', '2,1'], ['cr', '4,2'], ['cr', '3,1']] }, draw: true } }), null, CARDS, t);
  assert.equal(march.id, 'march'); assert.deepEqual(march.only, { crs: ['4,2'] });
  const den = current(view({ round: 6, history: hist, legal: { place: { lion: [['cr', '4,1'], ['hq', 'B']] }, draw: true } }), null, CARDS, t);
  assert.equal(den.id, 'den');
  assert.deepEqual(gate({ places: { lion: [['cr', '4,1'], ['hq', 'B']] } }, den.only).places, { lion: [['hq', 'B']] });
});
