// node check.mjs: the page actually plays. (1) Full games through legalActions/act, the API the
// page uses, every action checked legal; (2) Expert's move time with the page's settings;
// (3) index.html loaded in headless Chrome, turns clicked through as a person would, no script errors.
import { newMatch, act, legalActions, actionKey } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, EXPERT } from './src/bot.js';
import { existsSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };

{
  let games = 0, steps = 0, illegal = 0, ended = 0;
  const pairs = [[randomBot, greedyBot], [greedyBot, racerBot], [randomBot, randomBot]];
  for (let g = 0; g < 300; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const bots = pairs[g % 3];
    while (s.winner === null && steps < 1e7) {
      const a = bots[s.toAct](s, rng);
      if (!legalActions(s).some(x => actionKey(x) === actionKey(a))) illegal++;
      s = act(s, a); steps++;
    }
    games++; if (s.winner !== null) ended++;
  }
  say(illegal === 0 && ended === 300, `300 full games through act(), ${steps} actions, ${illegal} not in legalActions, ${ended} ended`);
}
{
  const E = expertBot({ ...EXPERT, playouts: 2400, timeMs: 1200 }), rng = makeRng(9);
  let s = newMatch({ seed: 99 }), worst = 0, n = 0;
  while (s.winner === null) {
    let a;
    if (s.toAct === 1) { const t0 = Date.now(); a = E(s, rng); worst = Math.max(worst, Date.now() - t0); n++; } else a = greedyBot(s, rng);
    s = act(s, a);
  }
  say(worst < 2000, `Expert with the page's settings: ${n} decisions, slowest ${worst} ms`);
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
      let clicks = 0, botActs = 0, shot = false;
      const t0 = Date.now();
      while (Date.now() - t0 < 60000 && clicks < 50) {
        const over = await page.$eval('#over', el => el.classList.contains('show'));
        if (over) break;
        const did = await page.evaluate(() => {
          const q = (sel) => document.querySelector(sel);
          if (window.__game.busy() || window.__game.state().toAct !== 0 || window.__game.state().winner !== null) return null;
          const st = window.__game.state();
          if (st.phase === 'discard') { const c = q('#hand .card.ok'); if (c) { c.click(); return 'discard'; } }
          const tg = q('.placed.tgt') || q('.space.dest'); if (tg) { tg.click(); return 'space'; }
          if (Math.random() < 0.8) { const cards = [...document.querySelectorAll('#hand .card.ok:not(.sel)')]; if (cards.length) { cards[Math.floor(Math.random() * cards.length)].click(); return 'card'; } }
          const e = q('#pass:not([disabled])'); if (e) { e.click(); return 'pass'; }
          return null;
        });
        if (did) clicks++;
        if (clicks === 14 && !shot) { await page.screenshot({ path: new URL(`./shot-${vp.width}.png`, import.meta.url).pathname }); shot = true; }
        await new Promise(r => setTimeout(r, did ? 350 : 700));
      }
      botActs = await page.evaluate(() => document.querySelectorAll('.hist.s1').length);
      const round = await page.evaluate(() => window.__game.state().round);
      const units = await page.$$eval('.placed', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      if (!shot) await page.screenshot({ path: new URL(`./shot-${vp.width}.png`, import.meta.url).pathname });
      say(clicks >= 10, `${vp.width}x${vp.height}: ${clicks} clicks played, ${botActs} bot actions in the history, round ${round}, ${units} cards on the spaces`);
      say(w <= vp.width && h <= vp.height, `${vp.width}x${vp.height}: no scroll (page ${w}x${h})`);
      await page.close();
    }
    await browser.close();
    say(errors.length === 0, `no script errors${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`);
  }
}
console.log(fails ? fails + ' checks failed' : 'all checks pass');
process.exit(fails ? 1 : 0);
