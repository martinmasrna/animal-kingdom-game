// Screenshots of the league-emblem prototype for review: home, the ladder and two ranked ends, desktop and phone.
// Not a test. node emblem_shots.mjs <out dir> (AK_PYTHON=<a venv python> from a worktree without its own .venv)
import { startServer, openBrowser, gamePage } from './harness.mjs';
const OUT = process.argv[2];
const wait = ms => new Promise(r => setTimeout(r, ms));
const L = (n, stars, of, extra = {}) => ({ league: n, name: `League ${n}`, top: n === 10, streak: 0, best: `League ${n}`, ...(n === 10 ? { rating: '2011' } : { stars, of }), ...extra });
const ME = L(6, 2, 5, { streak: 3 });
const server = await startServer(), browser = await openBrowser();
const SIZES = { desktop: { width: 1512, height: 800, deviceScaleFactor: 2 }, phone: { width: 393, height: 852, deviceScaleFactor: 3, isMobile: true, hasTouch: true } };
async function patched(patch) {
  const p = await browser.newPage(); p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message));
  await p.evaluateOnNewDocument(() => { try { localStorage.setItem('ak:play', JSON.stringify({ opp: 'ranked', level: 'Expert', botDeck: 'random', side: 'mine' })); } catch {} });
  await p.setRequestInterception(true);
  p.on('request', async req => {
    const path = new URL(req.url()).pathname;
    if (!patch[path] || req.method() !== 'GET') return req.continue();
    const r = await fetch(req.url(), { headers: req.headers() });
    req.respond({ status: r.status, contentType: 'application/json', body: JSON.stringify(patch[path](await r.json())) });
  });
  return p;
}
const board = j => ({ ...j, rows: [
  { name: 'Laras#0001', rating: '2213', league: L(10), bot: false },
  { name: 'Fish (Legendary Bot)', rating: '2175', bot: true, deck: 'fish' },
  { name: 'Okapi#4410', rating: null, league: L(9, 4, 5), bot: false },
  { name: 'Mira#0912', rating: null, league: L(8, 1, 5), bot: false },
  { name: 'Cats (Expert Bot)', rating: '1712', bot: true, deck: 'cats' },
  { name: 'Tomas#2207', rating: null, league: L(7, 3, 5), bot: false },
  { name: 'Martin#0002', rating: null, league: ME, bot: false, you: true },
  { name: 'Jana#7731', rating: null, league: L(5, 0, 5), bot: false },
  { name: 'Peter#1188', rating: null, league: L(4, 2, 5), bot: false },
  { name: 'Canines (Skilled Bot)', rating: '1335', bot: true, deck: 'canines' },
  { name: 'Eva#3021', rating: null, league: L(3, 1, 3), bot: false },
  { name: 'Ondro#5550', rating: null, league: L(2, 2, 3), bot: false },
  { name: 'Lucia#0404', rating: null, league: L(1, 0, 3), bot: false }] });
const errs = [];
for (const [sz, vp] of Object.entries(SIZES)) {
  const p = await patched({ '/api/me': me => ({ ...me, league: ME, rank: 7 }), '/api/leaderboard': board });
  await p.setViewport(vp);
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' }); await wait(800);
  await p.screenshot({ path: `${OUT}/home-${sz}.png` });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' }); await p.waitForSelector('#lboard .lr'); await wait(800); await p.evaluate(() => { document.querySelector('.hbody').scrollTop = 0; window.scrollTo(0, 0); }); await wait(200);
  await p.screenshot({ path: `${OUT}/ladder-${sz}.png` });
  errs.push(...p.errors); await p.close();
  for (const [name, extra] of [
    ['end-win', { rating: { before: '1512', after: '1530', delta: 18 }, league: { ...L(6, 4, 5, { streak: 3 }), line: '+2 stars (win streak): League 6, 4 of 5 stars' } }],
    ['end-loss', { lost: true, rating: { before: '1530', after: '1514', delta: -16 }, league: { ...L(6, 3, 5), line: '-1 star: League 6, 3 of 5 stars' } }],
    ['end-up', { rating: { before: '1580', after: '1601', delta: 21 }, league: { ...L(7, 0, 5, { streak: 4 }), line: 'Up to League 7, 0 stars' } }]]) {
    const g = await gamePage(browser, server.url); await g.setViewport(vp);
    await g.goto(g.url(), { waitUntil: 'networkidle0' });
    await g.evaluate(async extra => {
      const v = await fetch('/static/lab/mid.json').then(r => r.json()), o = v.you === 'A' ? 'B' : 'A';
      const w = extra.lost ? o : v.you; delete extra.lost;
      v.version += 50; v.phase = 'match_over'; v.results = [{ winner: w }]; v.score = { [w]: 1, [w === v.you ? o : v.you]: 0 };
      v.game.result = { winner: w, reason: 'food' }; v.ranked = true; Object.assign(v, extra); window.__ak.feed(v);
    }, extra);
    await g.waitForSelector('#lgline'); await wait(1200);
    await g.screenshot({ path: `${OUT}/${name}-${sz}.png` });
    errs.push(...g.errors); await g.close();
  }
}
console.log('errors:', JSON.stringify(errs));
await browser.close(); server.stop();
