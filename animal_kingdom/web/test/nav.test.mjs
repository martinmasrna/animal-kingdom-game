// Home's navigation (static/app.js): the corner piece (you, Collection, the gear and its list), Feedback on every screen
// outside a match (a tab on the edge where it's free, a square beside Back where a side panel holds the edge), and the
// leaderboard as the profile's tab.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));
const shown = (page, sel) => page.$eval(sel, e => getComputedStyle(e).display !== 'none').catch(() => false);

test('the corner piece: you, Collection, and a gear listing How to play, News and Settings', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' }); await wait(500);
  assert.deepEqual(await page.$$eval('.home .top > *', els => els.map(e => e.getAttribute('href') || e.id)), ['#/profile', '#/collection', 'gearbtn']);
  await page.click('#gearbtn'); await page.waitForSelector('.chooser.gear');
  assert.deepEqual(await page.$$eval('.chooser.gear .slab', els => els.map(e => e.textContent.trim())), ['How to play', 'News', 'Settings']);
  await page.click('#learn2'); await page.waitForSelector('.chooser.lessons');   // How to play: the lessons, in its place
  await page.click('#gearbtn'); await wait(200);
  assert.equal(await page.$('.home .chooser'), null, 'the gear closes what it opened');
  await page.close();
});

test('Feedback: a tab where the edge is free, beside Back where a side panel holds it', async () => {
  const page = await browser.newPage();
  for (const [hash, tab] of [['#/', true], ['#/news', true], ['#/settings', true], ['#/collection', false], ['#/profile', false]]) {
    await page.goto(`${server.url}/${hash}`, { waitUntil: 'networkidle0' }); await wait(400);
    assert.equal(await shown(page, '#ftab'), tab, `${hash}: the tab`);
    assert.equal(!!(await page.$('.sfoot .fbx')), !tab, `${hash}: the square beside Back`);
  }
  await page.close();
});

test('the leaderboard is the profile\'s tab, and its old address leads there', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/leaderboard`, { waitUntil: 'networkidle0' }); await page.waitForSelector('#lboard .lr');
  assert.equal(await page.evaluate(() => location.hash), '#/profile/leaderboard');
  assert.equal(await page.$eval('.ptab.on', e => e.textContent), 'Leaderboard');
  await page.click('.ptab:not(.on)'); await page.waitForSelector('.hbody .none, .hbody .hlist');
  assert.equal(await page.$eval('.ptab.on', e => e.textContent), 'Match history');
  await page.close();
});
