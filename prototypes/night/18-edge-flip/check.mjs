// node check.mjs: the page actually plays. (1) Full games through legalActions/act, the API the
// page uses, every action checked legal; (2) Expert's move time with the page's settings;
// (3) index.html in headless Chrome: cards placed by clicks over several turns, no script errors.
import { newMatch, act, legalActions, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, fillerBot, expertBot } from './src/bot.js';
import { existsSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };
{
  let games = 0, steps = 0, illegal = 0;
  for (let g = 0; g < 300; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const pool = [randomBot, greedyBot, fillerBot], bots = [pool[g % 3], pool[(g + 1) % 3]];
    while (s.winner === null && steps < 1e6) {
      const a = bots[s.turn](s, rng);
      if (!legalActions(s).some(x => actionKey(x) === actionKey(a))) illegal++;
      s = act(s, a); steps++;
    }
    games++;
  }
  say(illegal === 0 && games === 300, `300 full games through act(), ${steps} actions, ${illegal} not in legalActions`);
}
{
  const E = expertBot({ playouts: 900, timeMs: 1400 }), rng = makeRng(9);
  let s = newMatch({ seed: 99 }), worst = 0, n = 0;
  while (s.winner === null) {
    let a;
    if (s.turn === 1) { const t0 = Date.now(); a = E(s, rng); worst = Math.max(worst, Date.now() - t0); n++; } else a = greedyBot(s, rng);
    s = act(s, a);
  }
  say(worst < 2000, `Expert page settings: ${n} decisions, slowest ${worst} ms`);
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
      await new Promise(r => setTimeout(r, 1500));
      let placed = 0, ends = 0;
      const t0 = Date.now();
      while (Date.now() - t0 < 60000 && ends < 4) {
        const over = await page.$eval('#over', el => el.classList.contains('show'));
        if (over) break;
        const did = await page.evaluate(() => {
          const end = document.querySelector('#end'); if (!end || end.disabled) return null;
          const card = document.querySelector('#hand .card.ok:not(.coin)');
          if (card) { card.click(); card.click(); const cell = document.querySelector('.cell.can'); if (cell) { cell.click(); return 'place'; } }
          document.querySelector('#end').click(); return 'end';
        });
        if (did === 'place') placed++; if (did === 'end') ends++;
        await new Promise(r => setTimeout(r, did ? 800 : 300));
      }
      const tiles = await page.$$eval('.tile', els => els.length);
      const over = await page.$eval('#over', el => el.classList.contains('show'));
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      say(placed >= 3 && (ends >= 2 || over), `${vp.width}x${vp.height}: ${placed} cards placed by clicks, ${ends} turns ended, ${tiles} tiles on the grid${over ? ', game over' : ''}`);
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
