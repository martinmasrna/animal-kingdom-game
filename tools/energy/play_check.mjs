import puppeteer from 'puppeteer-core';
const CHROME = '/Users/martin/.cache/puppeteer/chrome/mac_arm-157.0.8103.38/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const URL = process.argv[2] || 'http://localhost:8010';
const GAMES = Number(process.argv[3] || 1);
const wait = ms => new Promise(r => setTimeout(r, ms));
const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', defaultViewport: { width: 1512, height: 800 } });
const page = await b.newPage();
const errs = [];
page.on('pageerror', e => errs.push('PAGEERR ' + e.message));
page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE ' + m.text().slice(0, 160)); });
const tap = async sel => { const el = await page.$(sel); if (!el) return false; const bb = await el.boundingBox(); if (!bb) return false; await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2); return true; };
const state = () => page.evaluate(() => { const { V } = window.__ak(), G = V && V.game; return { phase: V && V.phase, mine: G && G.toAct === V.you, pend: G && G.pending && (G.pending.kind === 'mulligan' ? 'mulligan' : G.pending.mode), version: V && V.version, round: G && G.round, left: G && G.actionsLeft, places: G && G.placesLeft, food: G && G.food }; });
const out = [];
for (let g = 0; g < GAMES; g++) {
  await page.goto(URL + '/#/', { waitUntil: 'networkidle0' }); await wait(800);
  await tap('#go');
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 20000 });
  let steps = 0, placed = 0, drew = 0, maxPlaces = 0, s;
  for (; steps < 700; steps++) {
    s = await state();
    if (s.phase === 'match_over' || s.phase === 'game_over') break;
    if (!s.mine) { await wait(200); continue; }
    await page.mouse.move(2, 2);
    if (s.pend === 'mulligan') await tap('#skip');
    else if (s.pend) { await tap('#board .cr.tgt') || await tap('#board .mouth.tgt') || await tap('#opts [data-o]') || await tap('#hand .hc.pick') || await tap('#opts .hc') || await tap('#choicebar [data-x]') || await tap('#skip') || await tap('#hand .hc.can'); }
    else {
      const cards = await page.$$('#hand .hc.can');
      if (cards.length && Math.random() < 0.8) { await tap('#hand .hc.can'); await wait(90);
        if (await tap('#board .cr.tgt') || await tap('#board .mouth.tgt')) placed++; else await page.keyboard.press('Escape'); }
      else if (await tap('#deck.can')) drew++;
      else if (!(await tap('#tbtn.can'))) await tap('#hand .hc.can');
    }
    await page.waitForFunction(v => window.__ak().V.version !== v, { timeout: 8000 }, s.version).catch(() => {});
  }
  out.push({ phase: s.phase, steps, placed, drew, round: s.round, food: s.food });
  await page.screenshot({ path: '/private/tmp/claude-501/-Users-martin-Work-fun-animal-kingdom/be2aaccf-182e-4604-b7fb-1337872dc257/scratchpad/e-game-end.png' });
}
console.log(JSON.stringify({ out, errs: errs.slice(0, 6) }));
await b.close();
