// node check.mjs: the page actually plays. (1) Full games through submit(), the API the page uses,
// every action checked legal; (2) Expert's move time with the page's settings; (3) index.html in
// headless Chrome: bids clicked through several rounds, no script errors.
import { newMatch, submit, canSubmit } from './src/engine.js';
import { makeRng, randomBot, greedyBot, expertBot } from './src/bot.js';
import { existsSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };
{
  let games = 0, steps = 0, illegal = 0;
  for (let g = 0; g < 300; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const bots = g % 2 ? [randomBot, greedyBot] : [greedyBot, randomBot];
    while (s.winner === null && steps < 1e6) {
      const acts = [0, 1].map(side => s.need[side] ? bots[side](s, side, rng) : null);
      for (const side of [0, 1]) if (acts[side] && s.need[side]) { if (!canSubmit(s, side, acts[side])) { illegal++; break; } s = submit(s, side, acts[side]); steps++; }
      if (illegal) break;
    }
    games++;
  }
  say(illegal === 0 && games === 300, `300 full games through submit(), ${steps} submissions, ${illegal} illegal`);
}
{
  const E = expertBot({ worlds: 16, timeMs: 1500 }), rng = makeRng(9);
  let s = newMatch({ seed: 99 }), worst = 0, n = 0;
  while (s.winner === null) {
    const acts = [0, 1].map(side => { if (!s.need[side]) return null; if (side === 1) { const t0 = Date.now(); const a = E(s, 1, rng); worst = Math.max(worst, Date.now() - t0); n++; return a; } return greedyBot(s, 0); });
    for (const side of [0, 1]) if (acts[side] && s.need[side]) s = submit(s, side, acts[side]);
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
      let bids = 0;
      const t0 = Date.now();
      while (Date.now() - t0 < 90000 && bids < 6) {
        const did = await page.evaluate(() => {
          const go = document.querySelector('#go');
          if (!go || go.disabled && !go.classList.contains('drop')) return null;
          const cards = [...document.querySelectorAll('#hand .card.can')];
          if (go.classList.contains('drop')) { const k = +go.textContent.split('/')[1]; for (let i = 0; i < k; i++) { const c = [...document.querySelectorAll('#hand .card.can:not(.sel)')]; c[c.length - 1].click(); } document.querySelector('#go').click(); return 'drop'; }
          if (cards[0]) cards[0].click(); const c2 = document.querySelectorAll('#hand .card.can:not(.sel)'); if (c2[0]) c2[0].click();
          document.querySelector('#go').click(); return 'bid';
        });
        if (did === 'bid') bids++;
        await new Promise(r => setTimeout(r, did ? 600 : 300));
      }
      const rounds = await page.$$eval('#round i.done', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      say(bids >= 3 && rounds >= 3, `${vp.width}x${vp.height}: ${bids} bids clicked, ${rounds} rounds done`);
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
