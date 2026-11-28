// node check.mjs: the page actually plays. (1) Full games through step(), the API the page uses,
// every action checked legal; (2) Expert's move time with the page's settings; (3) index.html in
// headless Chrome: the clock runs, cards are played by clicks, no script errors.
import { newMatch, step, canPlay } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot, DECIDE_EVERY } from './src/bot.js';
import { existsSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };
const W = { t: 'wait' };
{
  let games = 0, ticks = 0, illegal = 0;
  for (let g = 0; g < 200; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const bots = g % 2 ? [randomBot, greedyBot] : [greedyBot, randomBot];
    while (s.winner === null) {
      const acts = s.tick % DECIDE_EVERY === 0 ? [bots[0](s, 0, rng), bots[1](s, 1, rng)] : [W, W];
      for (const side of [0, 1]) if (!canPlay(s, side, acts[side])) illegal++;
      s = step(s, acts); ticks++;
    }
    games++;
  }
  say(illegal === 0 && games === 200, `200 full games through step(), ${ticks} ticks, ${illegal} illegal actions`);
}
{
  const E = expertBot({ playouts: 600, horizon: 40, timeMs: 220 }), rng = makeRng(9);
  let s = newMatch({ seed: 99 }), worst = 0, n = 0;
  while (s.winner === null) {
    let a = W;
    if (s.tick % DECIDE_EVERY === 0) { const t0 = Date.now(); a = E(s, 1, rng); worst = Math.max(worst, Date.now() - t0); n++; }
    s = step(s, [s.tick % DECIDE_EVERY === 0 ? greedyBot(s, 0) : W, a]);
  }
  say(worst < 400, `Expert page settings: ${n} decisions, slowest ${worst} ms (one decision a second)`);
}
{
  const PUP = '/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
  const CHROME = process.env.HOME + '/.cache/puppeteer/chrome/mac_arm-157.0.8103.38/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
  if (!existsSync(PUP) || !existsSync(CHROME)) say(false, 'puppeteer or Chrome for Testing not found');
  else {
    const { default: puppeteer } = await import(PUP);
    const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
    const errors = [];
    for (const vp of [{ width: 1512, height: 800 }, { width: 390, height: 844 }]) {
      const page = await browser.newPage();
      await page.setViewport(vp);
      page.on('pageerror', (e) => errors.push(String(e)));
      page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
      await page.goto('file://' + new URL('./index.html', import.meta.url).pathname);
      await new Promise(r => setTimeout(r, 1200));
      const c0 = await page.$eval('#clock', el => el.textContent);
      let plays = 0;
      for (let k = 0; k < 14; k++) {
        const did = await page.evaluate(() => {
          const cards = [...document.querySelectorAll('#hand .card.ok')];
          const unit = cards.find(c => !/Wall|Blast/.test(c.textContent));
          if (unit) { unit.click(); return 'unit'; }
          const bl = cards.find(c => /Blast/.test(c.textContent));
          if (bl) { bl.click(); return 'blast'; }
          return null;
        });
        if (did === 'blast') { const r = await page.$eval('#lane', el => { const b = el.getBoundingClientRect(); return { x: b.left + b.width * 0.7, y: b.top + b.height * 0.3 }; }); await page.mouse.click(r.x, r.y); }
        if (did) plays++;
        await new Promise(r => setTimeout(r, 1000));
      }
      const c1 = await page.$eval('#clock', el => el.textContent);
      const units = await page.$$eval('.u', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      say(c0 !== c1 && plays >= 2, `${vp.width}x${vp.height}: clock ${c0} -> ${c1}, ${plays} card clicks, ${units} units on the lane`);
      say(w <= vp.width, `${vp.width}x${vp.height}: no horizontal scroll (${w})`);
      await page.screenshot({ path: new URL(`./shot-${vp.width}.png`, import.meta.url).pathname });
      await page.close();
    }
    await browser.close();
    say(errors.length === 0, `no script errors${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`);
  }
}
console.log(fails ? fails + ' checks failed' : 'all checks pass');
process.exit(fails ? 1 : 0);
