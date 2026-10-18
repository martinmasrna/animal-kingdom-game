// News (static/news.js): no dot for a newcomer (a release from before they came is not theirs to catch up on), the
// gear's dot for a player from before the release while it is unread, the News screen with every release (the newest
// open), and the dot gone once News is opened. The player's age comes from the profile's `created`, so the server runs
// on a database file the test can backdate.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startServer, openBrowser } from './harness.mjs';

let server, browser, db;
before(async () => { db = join(mkdtempSync(join(tmpdir(), 'ak-news-')), 'web.db'); server = await startServer({ AK_DB: db }); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));
const RELEASES = readdirSync(new URL('../news/', import.meta.url)).filter(f => /^\d{4}-\d\d-\d\d\.md$/.test(f)).length;

test('no dot for a newcomer; the dot shows a player from before the release what is unread; News lists every release, the newest open; opening it clears the dot; Escape goes back', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' }); await wait(800);
  assert.equal(await page.$('#gearbtn .ndot'), null, 'a newcomer: no dot');
  execFileSync('sqlite3', [db, 'UPDATE profiles SET created = 0']);   // the same player, here since before every release
  await page.reload({ waitUntil: 'networkidle0' }); await wait(800);
  assert.ok(await page.$('#gearbtn .ndot'), 'the dot on the gear');
  await page.click('#gearbtn'); await page.waitForSelector('.chooser.gear a[href="#/news"] .ndot');   // and on News in its list
  await page.click('.chooser.gear a[href="#/news"]'); await page.waitForSelector('.news .nrel'); await wait(300);
  assert.equal((await page.$$('.news .nrel')).length, RELEASES);
  assert.equal((await page.$$('.news .nrel.open')).length, 1);
  assert.ok(await page.$eval('.news .nrel', e => e.classList.contains('open')), 'the newest open');
  await page.keyboard.press('Escape'); await page.waitForSelector('#gearbtn'); await wait(300);   // Escape is Back
  assert.equal(await page.$('#gearbtn .ndot'), null, 'read: no dot');
  await page.close();
});
