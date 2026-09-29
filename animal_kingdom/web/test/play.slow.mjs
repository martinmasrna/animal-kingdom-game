// A real match against the bot through the live server, played by clicking like a player: every one of your turns is
// checked against the game state, controls keep their painting on hover, and the match runs to the end without errors.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, screenMismatches } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));

async function startMatch(deck, botDeck) {
  const page = await browser.newPage();
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/favicon/.test(m.text())) page.errors.push(m.text()); });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  await page.evaluate(d => localStorage.setItem('ak:deck', d), deck);
  await page.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  await page.click(`[data-k="level"][data-v="easy"]`); await wait(100);
  await page.click(`[data-k="botDeck"][data-v="${botDeck}"]`); await wait(100);
  await page.click('#go');
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase !== 'lobby', { timeout: 10000 });
  if (await page.$('#ready')) await page.click('#ready');
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 10000 });
  return page;
}

// Click an element's centre (handles go stale: the board redraws under the pointer).
const tap = async (page, sel) => { const el = await page.$(sel); if (!el) return false; const b = await el.boundingBox(); if (!b) return false;
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); return true; };
const state = page => page.evaluate(() => { const { V } = window.__ak(), G = V.game;
  return { phase: V.phase, mine: G && G.toAct === V.you, pend: G && G.pending && (G.pending.kind === 'mulligan' ? 'mulligan' : G.pending.mode), version: V.version }; });

async function playOut(page, maxSteps = 500) {
  let hovered = false;
  for (let i = 0; i < maxSteps; i++) {
    const s = await state(page);
    if (s.phase === 'match_over') return;
    if (s.phase === 'game_over') { await tap(page, '#nextg'); await wait(400); continue; }
    if (!s.mine) { await wait(150); continue; }
    await page.mouse.move(2, 2);
    assert.deepEqual(await page.evaluate(screenMismatches), [], `your turn, step ${i}`);
    if (s.pend === 'mulligan') { await tap(page, '#skip'); }
    else if (s.pend) { if (!(await tap(page, '#board .cr.tgt') || await tap(page, '#board .mouth.tgt') || await tap(page, '#opts [data-o]') ||
        await tap(page, '#hand .hc.pick') || await tap(page, '#choicebar [data-x]') || await tap(page, '#skip') || await tap(page, '#hand .hc.can'))) assert.fail(`stuck on a ${s.pend} choice`); }
    else {
      if (!hovered && await page.$('#tbtn.can') && await page.$('#deck.can')) {   // the painted controls keep their image on hover
        for (const [sel, img] of [['#tbtn', 'btn_a'], ['#deck', 'deck_lit']]) {
          const b = await (await page.$(sel)).boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await wait(100);
          assert.match(await page.$eval(sel, e => getComputedStyle(e).backgroundImage), new RegExp(img), `${sel} keeps its painting on hover`);
        }
        hovered = true; await page.mouse.move(2, 2);
      }
      const cards = await page.$$('#hand .hc.can');
      if (cards.length && Math.random() < 0.75) {
        await tap(page, '#hand .hc.can'); await wait(80);
        if (!(await tap(page, '#board .cr.tgt') || await tap(page, '#board .mouth.tgt'))) await page.keyboard.press('Escape');
      } else if (!(await tap(page, '#deck.can'))) { if (!(await tap(page, '#tbtn.can'))) await tap(page, '#hand .hc.can'); }
    }
    await page.waitForFunction(v => window.__ak().V.version !== v, { timeout: 8000 }, s.version).catch(() => {});
  }
  assert.fail('the match did not end');
}

for (const [deck, bot] of [['cats_midrange', 'canine_buff_tempo'], ['egg_control', 'colony_food_swarm'], ['aggro_hq_rush', 'ramp']]) {
  test(`a best-of-3 by clicks: ${deck} against ${bot}`, { timeout: 600000 }, async () => {
    const page = await startMatch(deck, bot);
    await playOut(page);
    assert.deepEqual(page.errors, []);
    await page.close();
  });
}
