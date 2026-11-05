// Share links (docs/share-links.md): a replay link and a deck link opened in a fresh browser (no profile, nothing stored),
// a bad link of each kind, and the Share actions on the match history and on a deck.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { startServer, openBrowser, recordMatches, offsite } from './harness.mjs';
import { encodeDeck } from '../static/deckcode.js';

let server, browser, views;
const wait = ms => new Promise(r => setTimeout(r, ms));
const TOKEN = 'tok3nTok3nTok3nT';
const pool = JSON.parse(readFileSync(new URL('../../data/cards.json', import.meta.url))).cards.filter(c => c.status === 'collectible');
const C = Object.fromEntries(pool.map(c => [c.id, { ...c, str: c.base_strength === 'dynamic' ? '*' : c.base_strength }]));
const LIST = pool.slice(0, 10).flatMap(c => [c.id, c.id, c.id]);
const CODE = encodeDeck('Linked deck', LIST, C).match(/AK1:(\S+)/)[1];

// A page in its own browser context: a visitor who has never opened the game.
async function freshPage(intercept = () => false) {
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !offsite(m) && !/favicon|404/.test(m.text())) page.errors.push(m.text()); });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.setRequestInterception(true);
  page.on('request', async r => { await intercept(r); if (!r.isInterceptResolutionHandled()) r.continue(); });   // intercept answers a request it takes
  page.ctx = ctx;
  return page;
}

before(async () => {
  server = await startServer(); browser = await openBrowser();
  views = recordMatches(1).find(m => m.name.endsWith('_A.json')).views;
  for (const v of views) {   // the server adds the opponent's hand to a replay
    const ids = Object.keys(v.lists.B);
    v.game.oppHand = Array.from({ length: v.game.handCount.B }, (_, i) => ({ iid: 900 + i, id: ids[i % ids.length], str: 1 }));
  }
});
after(async () => { await browser?.close(); server?.stop(); });

test('a shared replay opens in a fresh browser, read-only, and Home leads home', async () => {
  const page = await freshPage(r => r.url().includes(`/api/replay/${TOKEN}`)
    && r.respond({ contentType: 'application/json', headers: { 'X-AK-Shared': '1' }, body: JSON.stringify(views) }));
  await page.goto(`${server.url}/#/replay/${TOKEN}`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('#rbar.on');
  assert.equal(await page.$('#rtake'), null, 'no Play from here for a visitor');
  assert.equal(await page.$eval('#rbar .out', a => [a.textContent, a.getAttribute('href')].join(' ')), 'Home #/');
  assert.ok(await page.evaluate(() => !!localStorage.getItem('ak:key')), 'the visitor got a guest profile, as on any first visit');
  await page.click('#rbar .out'); await page.waitForFunction(() => location.hash === '#/');
  await wait(200);
  assert.equal(await page.$('#rbar.on'), null, 'the replay is gone');
  assert.deepEqual(page.errors, []);
  await page.ctx.close();
});

test('a bad replay link says so and goes home', async () => {
  const page = await freshPage();
  await page.goto(`${server.url}/#/replay/not-a-real-token`, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => location.hash === '#/');
  assert.match(await page.$eval('#toast', e => e.textContent), /can't be replayed/);
  await page.ctx.close();
});

test('a deck link shows the list to a fresh browser and one tap puts it in the collection', async () => {
  const page = await freshPage();
  await page.goto(`${server.url}/#/deck/${CODE}?n=${encodeURIComponent('Linked deck')}`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('#dimport');
  assert.equal(await page.$eval('.hhead .ptab', e => e.textContent), 'Linked deck');
  assert.ok((await page.$$eval('.dlink .st', els => els.length)) >= 10, 'the list, card by card');
  await page.click('#dimport');
  await page.waitForFunction(() => location.hash.startsWith('#/collection'));
  await page.waitForFunction(() => [...document.querySelectorAll('.dtile')].some(e => e.textContent.includes('Linked deck')));
  // saved in the profile on the server, not only on the page
  const me = await page.evaluate(async () => (await fetch('/api/me', { headers: { 'X-AK-Key': localStorage.getItem('ak:key') } })).json());
  const d = me.decks.find(x => x.name === 'Linked deck');
  assert.ok(d, 'the deck is in the profile');
  assert.equal(Object.values(d.cards).reduce((a, b) => a + b, 0), 30);
  assert.deepEqual(page.errors, []);
  await page.ctx.close();
});

test('a bad deck link says so and goes home', async () => {
  const page = await freshPage();
  await page.goto(`${server.url}/#/deck/AAAA`, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => location.hash === '#/');
  assert.match(await page.$eval('#toast', e => e.textContent), /holds no cards/);
  await page.ctx.close();
});

test('Share on a match in the history asks for a link and hands it on; Share on a deck hands on a deck link', async () => {
  let shared = 0;
  const page = await freshPage(async r => {
    const url = r.url();
    if (url.endsWith('/api/replay/AAA-0/share')) { shared++; return r.respond({ contentType: 'application/json', body: JSON.stringify({ token: TOKEN }) }); }
    if (url.includes('/api/replay/AAA-0/lists')) return r.respond({ status: 404, body: '' });
    if (url.endsWith('/api/profile') || url.endsWith('/api/me')) {
      const res = await fetch(url, { method: r.method(), headers: r.headers(), body: r.postData() });
      const body = await res.json(), p = body.profile || body;
      p.history = [{ match: 'AAA-0', ended: 1790700000, kind: 'bot', my_deck: 'Cats', opp: 'Bot (Expert)', opp_deck: 'Giants', won: 1, lost: 0, my_cover: '', opp_cover: '' }];
      p.records = [{ deck: 'Cats', cover: '', won: 1, lost: 0 }];
      r.respond({ status: res.status, contentType: 'application/json', body: JSON.stringify(body) }); return true;
    }
    return false;
  });
  await page.evaluateOnNewDocument(() => { navigator.clipboard.writeText = t => { window.__copied = t; return Promise.resolve(); }; });
  await page.goto(`${server.url}/#/ladder/history`, { waitUntil: 'networkidle0' });
  await page.click('.ladder .hr .hshare');
  await page.waitForFunction(() => window.__copied);
  assert.equal(shared, 1);
  assert.equal(await page.evaluate(() => location.hash), '#/ladder/history', 'Share opens no replay');
  assert.equal(await page.evaluate(() => window.__copied), `${server.url}/#/replay/${TOKEN}`);
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.click('.dtile'); await page.waitForSelector('#dshare');
  await page.evaluate(() => { window.__copied = null; document.getElementById('dshare').click(); });
  await page.waitForFunction(() => window.__copied);
  assert.match(await page.evaluate(() => window.__copied), new RegExp(`^${server.url}/#/deck/[A-Za-z0-9_-]+\\?n=`));
  await page.ctx.close();
});
