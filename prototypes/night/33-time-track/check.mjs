// node check.mjs [seconds]: (1) full games through legalActions/act, the API the page uses, every
// action checked legal; (2) the built index.html in headless Chrome: no script errors while random
// clicks play it, plus screenshots at desktop and phone size in shots/.
import { mkdirSync } from 'node:fs';
import { newMatch, act, legalActions, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot } from './src/bot.js';

const CLICKABLE = '#hand .card.ok, .unit.can, .unit.tgt, .hero.tgt, #drawpile:not(:disabled), #wait, #rematch';
let fails = 0;
{
  const ex = expertBot({ iters: 600 }), bots = [randomBot, greedyBot, ex];
  for (let g = 0; g < 30; g++) {
    const rng = makeRng(g + 1), A = bots[g % 3], B = bots[(g + 1) % 3];
    let s = newMatch({ seed: 300 + g }), n = 0;
    while (s.winner === null && n < 5000) {
      const a = (s.turn === 0 ? A : B)(s, rng);
      if (!legalActions(s).some(x => actionKey(s, x) === actionKey(s, a))) { console.log('illegal action', a); fails++; break; }
      s = act(s, a); n++;
    }
    if (s.winner === null) { console.log('game did not end', g); fails++; }
  }
  console.log(`engine: 30 full games, ${fails} problems`);
}
const secs = +(process.argv[2] || 40);
const pup = await import('/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js');
const browser = await pup.default.launch({ headless: true, executablePath: process.env.HOME + '/.cache/puppeteer/chrome/mac_arm-157.0.8103.38/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' });
mkdirSync(new URL('shots/', import.meta.url), { recursive: true });
const errors = [];
for (const [name, vp] of [['desktop', { width: 1512, height: 800 }], ['phone', { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true }]]) {
  const page = await browser.newPage();
  await page.setViewport(vp);
  page.on('pageerror', e => errors.push(name + ': ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(name + ' console: ' + m.text()); });
  await page.goto(new URL('index.html', import.meta.url).href);
  await new Promise(r => setTimeout(r, 1500));
  let clicks = 0, shot = 0;
  const t0 = Date.now(), dur = name === 'desktop' ? secs * 1000 : secs * 500;
  while (Date.now() - t0 < dur) {
    const els = await page.$$(CLICKABLE);
    if (els.length) { const el = els[Math.floor(Math.random() * els.length)]; try { await el.click(); clicks++; } catch (e) {} }
    await new Promise(r => setTimeout(r, 200));
    if (clicks === 12 && shot === 0) { await page.screenshot({ path: new URL(`shots/${name}-mid.png`, import.meta.url).pathname }); shot = 1; }
  }
  await page.screenshot({ path: new URL(`shots/${name}-end.png`, import.meta.url).pathname });
  const scroll = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  if (scroll) errors.push(name + ': horizontal scroll');
  console.log(`${name}: ${clicks} clicks`);
  await page.close();
}
await browser.close();
console.log(errors.length ? 'page errors:\n' + errors.join('\n') : 'page: no script errors');
process.exit(fails || errors.length ? 1 : 0);
