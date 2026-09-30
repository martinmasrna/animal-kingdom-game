// The profile's match history and a match's replay: decks with their records filter the matches, a match opens its replay,
// and the replay steps through the views the player saw with nothing on the board to act on.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, recordMatches, screenMismatches } from './harness.mjs';

let server, browser, page, views;
const wait = ms => new Promise(r => setTimeout(r, ms));
const HISTORY = [
  { match: 'AAA-0', ended: 1790700000, kind: 'bot', my_deck: 'Cats', opp: 'Bot (Expert)', opp_deck: 'Ramp', won: 1, lost: 0, my_cover: 'king_theron', opp_cover: 'borealis' },
  { match: 'CCC-0', ended: 1790650000, kind: 'friend', my_deck: 'Cats', opp: 'Ana#1234', opp_deck: 'Her secret deck', won: 1, lost: 0, my_cover: 'king_theron', opp_cover: 'borealis' },
  { match: 'BBB-0', ended: 1790600000, kind: 'bot', my_deck: 'Egg', opp: 'Bot (Normal)', opp_deck: 'Cats', won: 0, lost: 1, my_cover: '', opp_cover: '' },
];
const RECORDS = [{ deck: 'Cats', cover: 'king_theron', won: 2, lost: 0 }, { deck: 'Egg', cover: '', won: 0, lost: 1 }];

before(async () => {
  server = await startServer(); browser = await openBrowser();
  views = recordMatches(1).find(m => m.name.endsWith('_A.json')).views;
  page = await browser.newPage();
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/favicon|409/.test(m.text())) page.errors.push(m.text()); });   // the 409 is the refused match
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.setRequestInterception(true);
  page.on('request', async r => {
    const url = r.url();
    if (url.includes('/api/replay/AAA-0')) return r.respond({ contentType: 'application/json', body: JSON.stringify({ views }) });
    if (url.includes('/api/replay/BBB-0')) return r.respond({ status: 409, contentType: 'text/plain', body: 'The cards have changed since this match, so it can\'t be replayed' });
    if (url.endsWith('/api/profile') || url.endsWith('/api/me')) {   // a profile with finished matches
      const res = await fetch(url, { method: r.method(), headers: r.headers(), body: r.postData() });
      const body = await res.json(), p = body.profile || body;
      Object.assign(p, { history: HISTORY, records: RECORDS });
      return r.respond({ status: res.status, contentType: 'application/json', body: JSON.stringify(body) });
    }
    r.continue();
  });
  await page.goto(`${server.url}/#/profile`, { waitUntil: 'networkidle0' });
});
after(async () => { await browser?.close(); server?.stop(); });

test('the profile lists each deck with its record and each match with both decks; a deck filters the matches', async () => {
  assert.deepEqual(await page.$$eval('.prof .rec', els => els.map(e => `${e.querySelector('b').textContent} ${e.querySelector('.wl').textContent}`)), ['Cats 2–0', 'Egg 0–1']);
  assert.deepEqual(await page.$$eval('.prof .hr b', els => els.map(e => e.textContent)), ['Won', 'Won', 'Lost']);
  assert.deepEqual(await page.$$eval('.prof .hr:nth-child(2) .dk', els => els.map(e => e.textContent)), ['Cats', 'Ana#1234'], 'a person, not their deck\'s name');
  assert.ok(!(await page.$eval('.prof .hlist', e => e.textContent.includes('Her secret deck'))));
  assert.equal(await page.$$eval('.prof .hr:first-child .pm .face', els => els.length), 2, 'both decks as pieces');
  assert.equal(await page.$$eval('.prof .hr:last-child .pm .face', els => els.length), 2, 'a match from before covers finds the starters\' faces');
  await page.click('.prof .rec[data-deck="Egg"]');
  assert.deepEqual(await page.$$eval('.prof .hr .dk', els => els.map(e => e.textContent)), ['Egg', 'Cats']);
  await page.click('.prof .rec[data-deck="Egg"]');
  assert.equal(await page.$$eval('.prof .hr', els => els.length), 3, 'clicked again, the filter clears');
});

test('a match that can no longer be replayed says so and stays on the profile', async () => {
  await page.click('.prof .hr:last-child'); await wait(300);
  assert.equal(await page.evaluate(() => location.hash), '#/profile');
  assert.match(await page.$eval('#toast', e => e.textContent), /can't be replayed/);
});

test('a match opens its replay: every view drawn right, nothing to act on, the controls step through it', async () => {
  await page.click('.prof .hr:first-child'); await page.waitForSelector('#rbar.on');
  await page.keyboard.press('Space');   // pause the playback
  assert.equal(await page.$eval('#menubtn', e => getComputedStyle(e).display), 'none', 'no Concede in a replay');
  for (let i = 0; i < Math.min(views.length, 60); i++) {
    const s = await page.evaluate(() => { const { V } = window.__ak(); return { turn: V.game.round, can: document.querySelectorAll('#hand .hc.can, #deck.can, #tbtn.can, #board .tgt').length }; });
    assert.equal(s.can, 0, `view ${i}: nothing is offered: ${await page.evaluate(() => [...document.querySelectorAll('#hand .hc.can, #deck.can, #tbtn.can, #board .tgt')].map(e => e.id || e.className.baseVal || e.className).join(' | '))}`);
    assert.deepEqual(await page.evaluate(screenMismatches), [], `view ${i}`);
    await page.keyboard.press('ArrowRight');
  }
  const i = await page.evaluate(() => window.__ak().V.version);
  await page.click('#rback'); await wait(50);
  assert.ok(await page.evaluate(() => window.__ak().V.version) < i, 'back one move');
});

test('the replay ends on the result, offers it again, and Leave goes back to the profile', async () => {
  await page.evaluate(() => { const t = document.getElementById('rtrack'), r = t.getBoundingClientRect(); t.dispatchEvent(new MouseEvent('click', { clientX: r.right, bubbles: true })); });
  await wait(100);
  assert.ok(await page.$('#endov.on #again'), 'Watch again');
  await page.click('#again'); await page.keyboard.press('Space'); await wait(50);
  assert.equal(await page.evaluate(() => window.__ak().V.game.history.length), 0, 'back at the start');
  await page.click('#rbar .out'); await page.waitForSelector('.prof');
});

test('no page errors', () => assert.deepEqual(page.errors, []));
