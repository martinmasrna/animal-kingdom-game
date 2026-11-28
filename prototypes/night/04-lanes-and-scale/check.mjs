// node check.mjs: the page plays. (1) full games through the engine's action API (act, isLegal),
// the one the page uses; (2) the built index.html in headless Chrome, a random clicker playing
// whole games against Expert through the page's own buttons, with no script errors.
import { createRequire } from 'node:module';
import { existsSync, readdirSync } from 'node:fs';
import { newMatch, act, isLegal, legalActions } from './src/engine.js';
import { makeRng, randomBot, expertBot } from './src/bot.js';

// (1) engine: random legal actions from the full legal list against Expert
const ex = expertBot({ iters: 300, c: 0.7, plies: 4 });
for (let g = 0; g < 20; g++) {
  const rng = makeRng(g + 1); let s = newMatch({ seed: 300 + g }), n = 0;
  while (s.winner === null) {
    const a = s.toMove === g % 2 ? (g < 10 ? randomBot(s, rng) : legalActions(s)[Math.floor(rng() * legalActions(s).length)]) : ex(s, rng);
    if (!isLegal(s, a)) throw new Error('illegal action from a bot');
    s = act(s, a);
    if (++n > 5000) throw new Error('engine game did not end');
  }
}
console.log('engine: 20 full games through act/isLegal');

// (2) the page
const PUP = '/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core';
const CH = process.env.HOME + '/.cache/puppeteer/chrome';
if (!existsSync(PUP) || !existsSync(CH)) { console.log('page: puppeteer not available, skipped'); process.exit(0); }
const puppeteer = createRequire(import.meta.url)(PUP);
const ver = readdirSync(CH).sort().pop();
const exe = `${CH}/${ver}/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ['--no-sandbox'] });
const errors = [];
let games = 0, clicks = 0, botMax = 0;
for (const vp of [{ width: 1512, height: 800 }, { width: 390, height: 844, isMobile: true, hasTouch: true }]) {
  const page = await browser.newPage();
  await page.setViewport(vp);
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto('file://' + new URL('./index.html', import.meta.url).pathname + '#fast');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (overflow) errors.push(`horizontal overflow at ${vp.width}px`);
  const t0 = Date.now();
  for (let k = 0; k < 4000 && Date.now() - t0 < 240000; k++) {
    const r = await page.evaluate(() => {
      const vis = (el) => el && el.offsetParent !== null;
      const any = (sel) => [...document.querySelectorAll(sel)].filter(vis);
      const pick = (a) => a[Math.floor(Math.random() * a.length)];
      if (document.querySelector('#over.show')) return 'over';
      const pk = document.querySelector('#pick.show');
      if (pk) { const c = any('#pick [data-pick]:not(.chosen)'); const go = document.getElementById('pickgo'); if (c.length && Math.random() < 0.6) { c[0].click(); return 'pick'; } (go || document.getElementById('pickno')).click(); return 'pickdone'; }
      const t = any('.tgt'); if (t.length) { pick(t).click(); return 'tgt'; }
      const two = ['up', 'down'].map(id => document.getElementById(id)).filter(b => b && !b.disabled); if (two.length && any('#hand .card.sel').length) { pick(two).click(); return 'act'; }
      const toss = any('#hand .card.toss'); if (toss.length) { pick(toss).click(); return 'toss'; }
      const opts = [...any('.unit.can'), ...any('#hand .card.ok')];
      const end = ['endturn', 'pass', 'allow'].map(id => document.getElementById(id)).find(b => b && !b.disabled);
      if (opts.length && Math.random() < 0.85) { pick(opts).click(); return 'act'; }
      if (end && !end.disabled) { end.click(); return 'end'; }
      return 'wait';
    });
    if (r === 'over') {
      games++;
      if (games % 2 === 1) { await page.evaluate(() => document.getElementById('rematch').click()); await new Promise(r => setTimeout(r, 300)); continue; }
      break;
    }
    if (r !== 'wait') clicks++;
    const ms = r === 'wait' ? 120 : 40; await new Promise(res => setTimeout(res, ms));
  }
  botMax = Math.max(botMax, await page.evaluate(() => window.__botMs.max));
  await page.close();
}
await browser.close();
console.log(`page: ${games} games finished by clicking (${clicks} clicks), Expert's slowest move ${Math.round(botMax)} ms, ${errors.length} errors`);
for (const e of errors) console.log('  error: ' + e);
process.exitCode = errors.length || games < 4 || botMax > 2000 ? 1 : 0;
