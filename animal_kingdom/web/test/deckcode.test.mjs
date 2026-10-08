// Unit tests for deck codes (static/deckcode.js) and the card numbers they rest on (static/cardnums.js).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { encodeDeck, decodeDeck } from '../static/deckcode.js';
import { CARD_NUMS } from '../static/cardnums.js';

const pool = JSON.parse(readFileSync(new URL('../../data/cards.json', import.meta.url))).cards;
const C = Object.fromEntries(pool.map(c => [c.id, { ...c, str: c.base_strength === 'dynamic' ? '*' : c.base_strength }]));
const colony = ['vesper', 'falstaff', 'queen_marabunta', 'queen_honoria', ...['nurse_bee', 'nurse_bumblebee', 'termite_queen', 'termite_king'].flatMap(id => [id, id]),
  ...['worker_ant', 'worker_bee', 'queen_bee', 'soldier_ant', 'guard_hornet', 'worker_wasp'].flatMap(id => [id, id, id])];
const sorted = l => [...l].sort();

test('every card has a permanent number, once', () => {
  assert.equal(new Set(CARD_NUMS).size, CARD_NUMS.length, 'no card numbered twice');
  assert.deepEqual(pool.map(c => c.id).filter(id => !CARD_NUMS.includes(id)), [], 'every card in cards.json has a number (append new ones to cardnums.js)');
});

test('a deck survives its code, and the code is short', () => {
  const code = encodeDeck('Colony copy', colony, C), line = code.split('\n').pop();
  assert.ok(line.length < 50, `AK1 line is ${line.length} characters`);
  const d = decodeDeck(code, C);
  assert.equal(d.name, 'Colony copy'); assert.deepEqual(sorted(d.list), sorted(colony));
  assert.deepEqual(sorted(decodeDeck(line, C).list), sorted(colony), 'the AK1 line alone is enough');
});

test('a readable list works without the code line (typed by hand or by an agent)', () => {
  const d = decodeDeck('### Agent cats\n3x Lion\n2x (1) Stray Cat\n1x King Theron\nnonsense line', C);
  assert.equal(d.name, 'Agent cats'); assert.deepEqual(sorted(d.list), sorted(['lion', 'lion', 'lion', 'house_cat', 'house_cat', 'king_theron']));
});

test('text without a deck is not a deck', () => {
  assert.equal(decodeDeck('hello', C), null); assert.equal(decodeDeck('AK1:!!!', C), null);
});
