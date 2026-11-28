// node check.mjs: the page plays. (1) In node, full games through the same calls the page makes
// (newMatch, legalActions, act with an event list), random clicks against the page's Expert.
// (2) In Chrome for Testing, index.html loads with no script error and a person's clicks
// (random legal ones) play a whole game to the end screen; screenshots at desktop and phone size.
import { newMatch, legalActions, act } from './src/engine.js';
import { makeRng, mcExpert, EXPERT } from './src/bot.js';
import { existsSync } from 'node:fs';

const rng = makeRng(42), expert = mcExpert({ ...EXPERT, timeMs: 1200, minPlayouts: 300 });
let worst = 0;
for (let g = 0; g < 4; g++) {
  let s = newMatch({ seed: 900 + g, first: g % 2 });
  for (let k = 0; k < 5000 && s.winner === null; k++) {
    let a;
    if (s.turn === 0) { const o = legalActions(s); a = o[Math.floor(rng() * o.length)]; }
    else { const t0 = Date.now(); a = expert(s, rng); worst = Math.max(worst, Date.now() - t0); }
    const ev = []; s = act(s, a, ev);
  }
  if (s.winner === null) throw new Error('game did not end');
  console.log(`node game ${g}: winner ${s.winner} after ${s.turnNo} turns`);
}
console.log(`slowest Expert decision ${worst} ms`);

const PUP = '/Users/martin/Work/fun/animal-kingdom/game/animal_kingdom/web/test/node_modules/puppeteer-core/lib/puppeteer/puppeteer-core.js';
const CHROME = process.env.HOME + '/.cache/puppeteer/chrome/mac_arm-157.0.8103.38/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
if (!existsSync(PUP) || !existsSync(CHROME)) { console.log('no puppeteer: browser check skipped'); process.exit(0); }
const { default: puppeteer } = await import(PUP);
const killer = setTimeout(() => { console.log('browser check timed out'); process.exit(1); }, 420000);
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox'] });
const errors = [];
const page = await browser.newPage();
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
await page.evaluateOnNewDocument(() => { const st = window.setTimeout; window.setTimeout = (f, ms, ...r) => st(f, (ms || 0) / 8, ...r); });
await page.setViewport({ width: 1512, height: 800 });
await page.goto('file://' + new URL('index.html', import.meta.url).pathname);
await new Promise(r => setTimeout(r, 800));
await page.screenshot({ path: new URL('shot-desktop.png', import.meta.url).pathname });
const t0 = Date.now();
let clicks = 0;
while (Date.now() - t0 < 300000) {
  const over = await page.$eval('#over', el => el.classList.contains('show'));
  if (over) break;
  const did = await page.evaluate(() => {
    const en = document.querySelector('#endturn:not([disabled])');
    if (!en) return 'wait';
    const pick = (sel) => { const a = [...document.querySelectorAll(sel)]; return a[Math.floor(Math.random() * a.length)]; };
    const tg = pick('.tgt'); if (tg) { tg.click(); return 'target'; }
    const r = Math.random();
    const c = pick('#hand .card.ok'); if (c && r < 0.5) { c.click(); return 'card'; }
    const u = pick('.minion.can'); if (u && r < 0.9) { u.click(); return 'unit'; }
    en.click(); return 'end';
  });
  if (did !== 'wait') clicks++;
  if (Date.now() - (globalThis.lastLog || 0) > 30000) { globalThis.lastLog = Date.now(); console.log(`  ${Math.round((Date.now() - t0) / 1000)}s: ${clicks} clicks, last ${did}`); }
  if (clicks === 12) await page.screenshot({ path: new URL('shot-desktop-play.png', import.meta.url).pathname });
  await new Promise(r => setTimeout(r, did === 'wait' ? 150 : 60));
}
const over = await page.$eval('#over', el => el.classList.contains('show') ? el.textContent : null);
await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
await new Promise(r => setTimeout(r, 300));
await page.screenshot({ path: new URL('shot-phone.png', import.meta.url).pathname });
await browser.close(); clearTimeout(killer);
console.log(`browser: ${clicks} clicks, end screen: ${over ? over.trim() : 'NOT REACHED'}, script errors: ${errors.length ? errors.join(' | ') : 'none'}`);
if (!over || errors.length) process.exit(1);
