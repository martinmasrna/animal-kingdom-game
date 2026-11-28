// node check.mjs: the page plays. (1) full games through the engine's action API (act, isLegal),
// the one the page uses; (2) the built index.html in headless Chrome at 1512x800 and 390x844,
// a random clicker playing whole games against Expert through the page's own buttons, with no
// script errors, no horizontal overflow, and Expert's slowest move under 2 seconds.
import { createRequire } from 'node:module';
import { existsSync, readdirSync } from 'node:fs';
import { newMatch, act, isLegal, legalActions } from './src/engine.js';
import { makeRng, randomBot, expertBot } from './src/bot.js';

const ex = expertBot({ K: 16, S: 2, KR: 8 });
for (let g = 0; g < 20; g++) {
  const rng = makeRng(g + 1); let s = newMatch({ seed: 300 + g }), n = 0;
  while (s.winner === null) {
    const a = s.toMove === g % 2 ? randomBot(s, rng) : ex(s, rng);
    if (!isLegal(s, a)) throw new Error('illegal action from a bot');
    s = act(s, a);
    if (++n > 5000) throw new Error('engine game did not end');
  }
}
console.log('engine: 20 full games through act/isLegal');

const PUP = '/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core';
const CH = process.env.HOME + '/.cache/puppeteer/chrome';
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
  await page.goto('file://' + new URL('./index.html', import.meta.url).pathname + (vp.width > 500 ? '' : '#fast'));
  await new Promise(r => setTimeout(r, 300));
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) errors.push(`horizontal overflow at ${vp.width}px`);
  await page.screenshot({ path: new URL(`./shot-${vp.width}.png`, import.meta.url).pathname });
  // the rules panel opens and closes
  await page.evaluate(() => { document.getElementById('rulesbtn').click(); });
  if (!(await page.evaluate(() => document.getElementById('rules').classList.contains('show')))) errors.push('rules panel did not open');
  await page.evaluate(() => { document.getElementById('rules').click(); });
  let mine = 0, shotAt = 0, battleShot = false;
  const t0 = Date.now();
  for (let k = 0; k < 6000 && Date.now() - t0 < 240000; k++) {
    const r = await page.evaluate(() => {
      const vis = (el) => el && el.offsetParent !== null;
      const any = (sel) => [...document.querySelectorAll(sel)].filter(vis);
      const pick = (a) => a[Math.floor(Math.random() * a.length)];
      if (document.querySelector('#over.show')) return 'over';
      const opts = [...any('#shop .card.ok'), ...any('.dk.rm'), ...any('#tools button:not([disabled])')];
      if (opts.length) { const f = document.getElementById('fight'); pick(f && !f.disabled && Math.random() < 0.3 ? [f] : opts).click(); return 'act'; }
      return document.getElementById('front0') && document.getElementById('front1') ? 'battle' : 'wait';
    });
    if (r === 'over') {
      games++; mine++;
      if (mine === 1) { await page.evaluate(() => document.getElementById('rematch').click()); await new Promise(r => setTimeout(r, 300)); continue; }
      break;
    }
    if (r === 'battle' && !battleShot) { battleShot = true; await page.screenshot({ path: new URL(`./shot-${vp.width}-battle.png`, import.meta.url).pathname }); }
    if (r === 'battle') { await new Promise(res => setTimeout(res, 100)); continue; }
    if (r !== 'wait') clicks++;
    if (r !== 'wait' && mine === 0 && ++shotAt === 9) await page.screenshot({ path: new URL(`./shot-${vp.width}-play.png`, import.meta.url).pathname });
    await new Promise(res => setTimeout(res, r === 'wait' ? 100 : 30));
  }
  botMax = Math.max(botMax, await page.evaluate(() => window.__botMs.max));
  await page.close();
}
await browser.close();
console.log(`page: ${games} games finished by clicking (${clicks} clicks), Expert's slowest move ${Math.round(botMax)} ms, ${errors.length} errors`);
for (const e of errors) console.log('  error: ' + e);
process.exitCode = errors.length || games < 4 || botMax > 2000 ? 1 : 0;
