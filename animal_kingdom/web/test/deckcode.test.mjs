// Unit tests for deck codes (static/deckcode.js) and the card numbers they rest on (static/cardnums.js).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { encodeDeck, decodeDeck } from '../static/deckcode.js';
import { CARD_NUMS } from '../static/cardnums.js';

const pool = JSON.parse(readFileSync(new URL('../../data/cards.json', import.meta.url))).cards.filter(c => c.status !== 'planned');   // a planned animal is no card yet
const C = Object.fromEntries(pool.map(c => [c.id, { ...c, str: c.base_strength === 'dynamic' ? '*' : c.base_strength }]));
const wisps = ['warlord_legend', ...[1, 2, 3, 4, 5, 6].flatMap(n => ['wisp_' + n, 'wisp_' + n]), ...[1, 2, 3, 5].flatMap(n => ['flight_' + n, 'flight_' + n]), 'cantrip_2', 'cantrip_2', 'spikes_3', 'spikes_3'];
const sorted = l => [...l].sort();

test('every card has a permanent number, once', () => {
  assert.equal(new Set(CARD_NUMS).size, CARD_NUMS.length, 'no card numbered twice');
  assert.deepEqual(pool.map(c => c.id).filter(id => !CARD_NUMS.includes(id)), [], 'every card in cards.json has a number (append new ones to cardnums.js)');
});

test('a deck survives its code, and the code is short', () => {
  const code = encodeDeck('Wisps', wisps, C), line = code.split('\n').pop();
  assert.ok(line.length < 50, `AK1 line is ${line.length} characters`);
  const d = decodeDeck(code, C);
  assert.equal(d.name, 'Wisps'); assert.deepEqual(sorted(d.list), sorted(wisps));
  assert.deepEqual(sorted(decodeDeck(line, C).list), sorted(wisps), 'the AK1 line alone is enough');
});

test('a readable list works without the code line (typed by hand or by an agent)', () => {
  const d = decodeDeck('### Agent wisps\n2x Wisp 3\n2x (1) Wisp 1\n1x Gorrak One-Eye\nnonsense line', C);
  assert.equal(d.name, 'Agent wisps'); assert.deepEqual(sorted(d.list), sorted(['wisp_3', 'wisp_3', 'wisp_1', 'wisp_1', 'warlord_legend']));
});

test('text without a deck is not a deck', () => {
  assert.equal(decodeDeck('hello', C), null); assert.equal(decodeDeck('AK1:!!!', C), null);
});
