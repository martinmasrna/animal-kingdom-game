// What the client logs (static/log.js) reaches the server: a new player's first screens, Learn to play, and the
// tutorial's steps as they show, each kept by POST /api/events (web/events.py).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser({ newPlayer: true }); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));

test('a new player\'s screens and tutorial steps are sent and kept', async () => {
  const page = await browser.newPage(), sent = [];
  page.on('request', r => { if (r.url().endsWith('/api/events')) sent.push(...JSON.parse(r.postData()).events); });
  const kept = [];
  page.on('response', async r => { if (r.url().endsWith('/api/events')) kept.push((await r.json()).kept); });
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('#learn'); await page.click('#learn');
  await page.waitForSelector('.coach', { timeout: 15000 }); await wait(1500);
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));   // a flush, as when the page hides
  await wait(6000);
  const kinds = sent.map(e => e.kind);
  assert.ok(kinds.includes('screen'), 'screens');
  assert.ok(kinds.includes('learn_to_play'), 'Learn to play');
  assert.ok(sent.some(e => e.kind === 'tutorial_step' && e.data.lesson === 1 && e.data.step), 'a tutorial step with its lesson');
  assert.ok(kept.length && kept.every(n => n > 0), 'the server kept them');
  await page.close();
});
