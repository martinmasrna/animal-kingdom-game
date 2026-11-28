// node check.mjs: the page actually plays. (1) Full games through legalActions/act, the API the
// page uses, every action checked legal; (2) Expert's move time with the page's settings;
// (3) index.html loaded in headless Chrome, a few turns clicked through, no script errors.
import { newMatch, act, legalActions, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot } from './src/bot.js';
import { existsSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };

// (1) full games through the action API
{
  let games = 0, steps = 0, illegal = 0;
  for (let g = 0; g < 200; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const bots = g % 2 ? [randomBot, greedyBot] : [greedyBot, randomBot];
    while (s.winner === null && steps < 1e6) {
      const a = bots[s.toAct](s, rng);
      if (s.phase === 'main' && !legalActions(s).some(x => actionKey(x) === actionKey(a))) illegal++;
      s = act(s, a); steps++;
    }
    games++;
  }
  say(illegal === 0 && games === 200, `200 full games through act(), ${steps} actions, ${illegal} not in legalActions`);
}
// (2) Expert's move time with the page's settings
{
  const E = expertBot({ playouts: 3000, timeMs: 1500 }), rng = makeRng(9);
  let s = newMatch({ seed: 99 }), worst = 0, n = 0;
  while (s.winner === null) {
    let a;
    if (s.toAct === 0) { const t0 = Date.now(); a = E(s, rng); worst = Math.max(worst, Date.now() - t0); n++; } else a = greedyBot(s, rng);
    s = act(s, a);
  }
  say(worst < 2000, `Expert page settings: ${n} decisions, slowest ${worst} ms`);
}
// (3) the page in headless Chrome
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
      await new Promise(r => setTimeout(r, 1500));
      let clicks = 0;
      const t0 = Date.now();
      while (Date.now() - t0 < 25000 && clicks < 12) {
        const over = await page.$eval('#over', el => el.classList.contains('show'));
        if (over) break;
        // as a human: play the first playable card, attack with every ready unit, block nothing, end the turn
        const did = await page.evaluate(() => {
          const q = (sel) => document.querySelector(sel);
          if (q('#block')) { q('#block').click(); return 'block'; }
          const card = q('#hand .card.ok'); if (card && !card.textContent.includes('damage')) { card.click(); return 'card'; }
          const u = q('#board0 .unit.can'); if (u && !q('#attack')) { u.click(); return 'pick'; }
          if (q('#attack')) { q('#attack').click(); return 'attack'; }
          if (q('#end')) { q('#end').click(); return 'end'; }
          return null;
        });
        if (did) clicks++;
        await new Promise(r => setTimeout(r, did ? 400 : 600));
      }
      const units = await page.$$eval('.unit', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      say(clicks >= 6, `${vp.width}x${vp.height}: ${clicks} clicks played, ${units} units on the board, page width ${w}`);
      say(w <= vp.width, `${vp.width}x${vp.height}: no horizontal scroll`);
      await page.screenshot({ path: new URL(`./shot-${vp.width}.png`, import.meta.url).pathname });
      await page.close();
    }
    await browser.close();
    say(errors.length === 0, `no script errors${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`);
  }
}
console.log(fails ? fails + ' checks failed' : 'all checks pass');
process.exit(fails ? 1 : 0);
