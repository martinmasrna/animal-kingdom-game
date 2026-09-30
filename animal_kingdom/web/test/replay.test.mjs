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
  for (const v of views) {   // the server adds the opponent's hand to a replay: any cards of theirs, one per card in hand
    const ids = Object.keys(v.lists.B);
    v.game.oppHand = Array.from({ length: v.game.handCount.B }, (_, i) => ({ iid: 900 + i, id: ids[i % ids.length], str: 1 }));
  }
  page = await browser.newPage();
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/favicon|409/.test(m.text())) page.errors.push(m.text()); });   // the 409 is the refused match
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.setRequestInterception(true);
  page.on('request', async r => {
    const url = r.url();
    if (url.includes('/api/replay/AAA-0')) return r.respond({ contentType: 'application/json', body: JSON.stringify(views) });   // the server's format: the list of views
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

test('the profile lists each match with both decks; the deck filter carries each deck\'s record and filters the matches', async () => {
  assert.deepEqual(await page.$$eval('.hhead .ddo', els => els.map(e => e.textContent.replace(/\s+/g, ' ').trim())), ['All decks 2–1', 'Cats 2–0', 'Egg 0–1']);
  assert.deepEqual(await page.$$eval('.prof .hr b', els => els.map(e => e.textContent)), ['Won', 'Won', 'Lost']);
  assert.deepEqual(await page.$$eval('.prof .hr:nth-child(2) .dk', els => els.map(e => e.textContent)), ['Cats', 'Ana#1234'], 'a person, not their deck\'s name');
  assert.ok(!(await page.$eval('.prof .hlist', e => e.textContent.includes('Her secret deck'))));
  assert.equal(await page.$$eval('.prof .hr:first-child .pm .face', els => els.length), 2, 'both decks as pieces');
  assert.equal(await page.$$eval('.prof .hr:last-child .pm .face', els => els.length), 2, 'a match from before covers finds the starters\' faces');
  await page.click('.hhead .dd .sel'); await page.click('.hhead .ddo[data-v="Egg"]');
  assert.deepEqual(await page.$$eval('.prof .hr .dk', els => els.map(e => e.textContent)), ['Egg', 'Cats']);
  await page.click('.hhead .dd .sel'); await page.click('.hhead .ddo[data-v=""]');
  assert.equal(await page.$$eval('.prof .hr', els => els.length), 3, 'all decks again');
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

test('stepping skips what changes nothing on screen; the bar marks each turn; the recent moves go back to a move', async () => {
  const look = v => JSON.stringify([v.phase, v.game.board, v.game.hand.map(h => h.id), (v.game.oppHand || []).map(h => h.id), v.game.food, v.game.current, v.game.round, v.game.toAct === v.you && v.game.pending]);
  const turns = views.filter((v, i) => i && v.game.round !== views[i - 1].game.round).length;
  assert.equal(await page.$$eval('#rtrack b', els => els.length), turns, 'a mark per turn');
  const b = await (await page.$('#rtrack')).boundingBox();
  await page.mouse.click(b.x + 1, b.y + b.height / 2);   // the start
  let prev = await page.evaluate(() => window.__ak().V);
  for (let k = 0; k < 40; k++) {
    await page.keyboard.press('ArrowRight');
    const v = await page.evaluate(() => window.__ak().V);
    if (v === prev || v.version === prev.version) break;
    assert.notEqual(look(v), look(prev), `step ${k} changed something`);
    prev = v;
  }
  await page.keyboard.press('ArrowLeft');   // off the result, which covers the board
  const n = await page.$$eval('#recent .hi', els => els.length);
  assert.ok(n > 1 && n <= 7, 'recent moves shown');
  const h = await page.$eval('#recent .hi', el => Number(el.dataset.h));
  await page.click('#recent .hi'); await wait(50);
  assert.equal(await page.evaluate(() => window.__ak().V.game.history.length), h + 1, 'back at that move');
});

test('the opponent\'s hand shows face up; the eye turns it back into card backs', async () => {
  const n = await page.evaluate(() => window.__ak().V.game.handCount.B);
  assert.equal(await page.$$eval('#opphand .oc', els => els.length), n);
  await page.click('#reye'); await wait(50);
  assert.equal(await page.$$eval('#opphand .oc', els => els.length), 0);
  assert.equal(await page.$$eval('#opphand .back', els => els.length), n);
  await page.click('#reye'); await wait(50);
  assert.equal(await page.$$eval('#opphand .oc', els => els.length), n);
});

test('the replay ends on the result, offers it again, and Leave goes back to the profile', async () => {
  const b = await (await page.$('#rtrack')).boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down();
  await page.mouse.move(b.x + b.width + 40, b.y + b.height / 2, { steps: 4 }); await page.mouse.up();   // dragged past the end: the last view
  await wait(100);
  assert.ok(await page.$('#endov.on #again'), 'Watch again');
  await page.click('#again'); await page.keyboard.press('Space'); await wait(50);
  assert.equal(await page.evaluate(() => window.__ak().V.game.history.length), 0, 'back at the start');
  await page.click('#rbar .out'); await page.waitForSelector('.prof');
});

test('no page errors', () => assert.deepEqual(page.errors, []));
