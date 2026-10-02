// The end's beat (board.js, app.js startBeat): a den taken falls apart, and each game of a match gets its own, a rematch
// included (it reuses the match's id and result count: the second ending used to keep the first one's den).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url, { still: false }); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));

// the lab's view as a game that just ended by `winner` taking the other's den, or as the next game in play
const feedEnd = (winnerIsYou, version) => page.evaluate(async (won, version) => {
  const v = await fetch('/static/lab/mid.json').then(r => r.json()), o = v.you === 'A' ? 'B' : 'A', w = won ? v.you : o;
  v.version = version; v.phase = 'game_over'; v.results = [{ winner: w }]; v.score = { [v.you]: won ? 1 : 0, [o]: won ? 0 : 1 };
  v.game.result = { winner: w, reason: 'hq_capture' };
  v.game.events = [{ e: 'capture', player: w, den: won ? o : v.you, card: 'lion', iid: 990, str: 7, seq: 1 }];
  window.__ak.feed(v);
}, winnerIsYou, version);
const feedPlaying = version => page.evaluate(async version => {
  const v = await fetch('/static/lab/mid.json').then(r => r.json()); v.version = version; v.results = []; v.game.events = [];
  window.__ak.feed(v);
}, version);
const fallen = () => page.evaluate(() => [...document.querySelectorAll('#board .dcount.fall')].map(g => g.classList.contains('A') ? 'yours' : 'theirs'));

test('a rematch ending on your den collapses your den, not the last game\'s', async () => {
  await feedPlaying(100); await wait(300);
  await feedEnd(true, 101); await wait(3500);
  assert.deepEqual(await fallen(), ['theirs'], 'the first game: their den falls');
  await feedPlaying(102); await wait(500);   // Rematch: the same match, its results cleared
  assert.deepEqual(await fallen(), [], 'a new game starts whole');
  await feedEnd(false, 103); await wait(3500);
  assert.deepEqual(await fallen(), ['yours'], 'the rematch: your den falls');
  assert.deepEqual(page.errors, []);
});
