// node check.mjs: the page actually plays. (1) Full games through act(), the API the page uses,
// every plan checked by planError; (2) Expert's move time with the page's settings; (3) index.html
// in headless Chrome at 1512x800 and 390x844: rounds planned and played by clicks as a person
// would, no script errors, no horizontal scroll, a screenshot each.
import { newMatch, act, planError } from './src/engine.js';
import { makeRng, randomBot, greedyBot, racerBot, expertBot, EXPERT } from './src/bot.js';
import { existsSync, readdirSync } from 'node:fs';

let fails = 0;
const say = (ok, msg) => { if (!ok) fails++; console.log((ok ? 'ok   ' : 'FAIL ') + msg); };
{
  let games = 0, steps = 0, illegal = 0, unfinished = 0;
  const bots = [randomBot, greedyBot, racerBot];
  for (let g = 0; g < 300; g++) {
    const rng = makeRng(g + 1); let s = newMatch({ seed: g + 1 });
    const pair = [bots[g % 3], bots[(g + 1) % 3]];
    let k = 0;
    while (s.winner === null && k < 1000) { const a = pair[s.toAct](s, rng); if (planError(s, s.toAct, a)) illegal++; s = act(s, a); steps++; k++; }
    if (s.winner === null) unfinished++;
    games++;
  }
  say(illegal === 0 && unfinished === 0, `${games} full games through act(), ${steps} plans, ${illegal} illegal, ${unfinished} unfinished`);
}
{
  const E = expertBot({ ...EXPERT, timeMs: 1500 }), rng = makeRng(9);
  let worst = 0, n = 0, tot = 0;
  for (let g = 0; g < 4; g++) {
    let s = newMatch({ seed: 99 + g });
    while (s.winner === null) {
      let a;
      if (s.toAct === 1) { const t0 = Date.now(); a = E(s, rng); const d = Date.now() - t0; worst = Math.max(worst, d); tot += d; n++; } else a = greedyBot(s, rng);
      s = act(s, a);
    }
  }
  say(worst < 2000, `Expert at the page's settings: ${n} plans, mean ${(tot / n).toFixed(0)} ms, slowest ${worst} ms`);
}
{
  const PUP = '/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
  const base = process.env.HOME + '/.cache/puppeteer/chrome/';
  const ver = existsSync(base) ? readdirSync(base).find(d => d.startsWith('mac_arm')) : null;
  const CHROME = ver && base + ver + '/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
  if (!existsSync(PUP) || !CHROME || !existsSync(CHROME)) say(false, 'puppeteer or Chrome for Testing not found');
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
      let clicks = 0, gos = 0, shot = false;
      const t0 = Date.now();
      while (Date.now() - t0 < 60000 && gos < 5) {
        if (await page.$eval('#over', el => el.classList.contains('show'))) break;
        // as a person: play the unit cards that fit, every Hit at the enemy player, every unit at the enemy player, Go
        const did = await page.evaluate(() => {
          const q = (sel) => document.querySelector(sel);
          if (window.__game.busy) return null;
          const sel = q('#hand .card.sel');
          if (sel) { q('#hero1x').click(); return 'spell'; }
          const ok = q('#hand .card.ok'); if (ok) { ok.click(); return 'card'; }
          const su = q('#board0 .unit.sel'); if (su) { q('#hero1x').click(); return 'attack'; }
          const u = [...document.querySelectorAll('#board0 .unit.can')].find(el => !window.__game.plan.attacks.has(+el.dataset.uid));
          if (u) { u.click(); return 'pick'; }
          const g = q('#endturn'); if (g && !g.disabled) { g.click(); return 'go'; }
          return null;
        });
        if (did) { clicks++; if (did === 'go') gos++; }
        if (did === 'go' && gos === 3 && !shot) { await new Promise(r => setTimeout(r, 1700)); await page.screenshot({ path: new URL(`./shot-${vp.width}-reveal.png`, import.meta.url).pathname }); shot = true; }
        await new Promise(r => setTimeout(r, did ? 250 : 400));
      }
      const units = await page.$$eval('.unit', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      const round = await page.evaluate(() => window.__game.s.round);
      const over = await page.$eval('#over', el => el.classList.contains('show'));
      say(gos >= 4 || over, `${vp.width}x${vp.height}: ${clicks} clicks, ${gos} rounds planned and played by click, round ${round}, ${units} units on the board`);
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
