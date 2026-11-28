// node check.mjs: the page actually plays. (1) Full games through legalActions/act, the API the
// page uses, every action checked legal; (2) Expert's move time with the page's settings;
// (3) index.html in headless Chrome at 1512x800 and 390x844: turns clicked through as a person
// would, no script errors, no horizontal scroll, a screenshot each.
import { newMatch, act, legalActions, actionKey } from './src/engine.js';
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
    while (s.winner === null && k < 5000) {
      const a = pair[s.toAct](s, rng);
      if (!legalActions(s).some(x => actionKey(x) === actionKey(a))) illegal++;
      s = act(s, a); steps++; k++;
    }
    if (s.winner === null) unfinished++;
    games++;
  }
  say(illegal === 0 && unfinished === 0, `${games} full games through act(), ${steps} actions, ${illegal} not in legalActions, ${unfinished} unfinished`);
}
{
  const E = expertBot({ ...EXPERT, timeMs: 1300 }), rng = makeRng(9);
  let worst = 0, n = 0, tot = 0;
  for (let g = 0; g < 2; g++) {
    let s = newMatch({ seed: 99 + g });
    while (s.winner === null) {
      let a;
      if (s.toAct === 0) { const t0 = Date.now(); a = E(s, rng); const d = Date.now() - t0; worst = Math.max(worst, d); tot += d; n++; } else a = greedyBot(s, rng);
      s = act(s, a);
    }
  }
  say(worst < 2000, `Expert at the page's settings: ${n} decisions, mean ${(tot / n).toFixed(0)} ms, slowest ${worst} ms`);
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
      let clicks = 0, ends = 0;
      const t0 = Date.now();
      while (Date.now() - t0 < 40000 && ends < 4) {
        if (await page.$eval('#over', el => el.classList.contains('show'))) break;
        // as a person: play what is playable (a targeted card on the first Neutral offered), end the turn
        const did = await page.evaluate(() => {
          const q = (sel) => document.querySelector(sel);
          if (window.__game.busy || window.__game.s.toAct !== 0) return null;
          const sel = q('#hand .card.sel');
          if (sel) { const t = q('.tok.tgt'); if (t) { t.click(); return 'target'; } sel.click(); return 'unselect'; }
          const ok = q('#hand .card.ok'); if (ok) { ok.click(); return 'card'; }
          const e = q('#endturn'); if (e && !e.disabled) { e.click(); return 'end'; }
          return null;
        });
        if (did) { clicks++; if (did === 'end') ends++; }
        await new Promise(r => setTimeout(r, did ? 350 : 500));
      }
      const units = await page.$$eval('.tok', els => els.length);
      const w = await page.evaluate(() => document.documentElement.scrollWidth);
      const turn = await page.evaluate(() => window.__game.s.turnNo);
      say(ends >= 3 || (await page.$eval('#over', el => el.classList.contains('show'))), `${vp.width}x${vp.height}: ${clicks} clicks, ${ends} turns ended by click, match at turn ${turn}, ${units} Neutrals on the field`);
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
