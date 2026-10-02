// Recorded bot matches (both seats) played through the client with animations on, at a player's pace (2026-10-02: a
// comment swallowed the stones' positions and every income fruit flew from the window's corner, with no test failing).
// While they play, every animated element is sampled: a moving piece must have a real position and stay near the stage.
// Once each view's steps have played out and settled, the screen must match the view (screenMismatches) and no
// finite animation may still be running. MATCHES=n plays more; PHONE=1 plays upright on a phone.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, recordMatches, gamePage, feed, screenMismatches } from './harness.mjs';
const wait = ms => new Promise(r => setTimeout(r, ms));
const N = +(process.env.MATCHES || 2), PHONE = process.env.PHONE;
test('moving pieces stay on the board, and every step settles to the view', { timeout: 3600000 }, async () => {
const matches = recordMatches(N), server = await startServer(), b = await openBrowser();
const problems = [];
for (const m of matches) {
  const p = await gamePage(b, server.url, { still: false });
  if (PHONE) await p.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
  await p.evaluate(() => { window.__bad = [];
    const W = innerWidth, H = innerHeight, seen = new Set();
    setInterval(() => { for (const a of document.getAnimations()) {
      const el = a.effect && a.effect.target; if (!el || !el.isConnected || a.playState !== 'running') continue;
      const s = getComputedStyle(el); if (s.display === 'none' || +s.opacity < 0.05) continue;
      const r = el.getBoundingClientRect(), cx = r.x + r.width / 2, cy = r.y + r.height / 2;
      const id = (el.className.baseVal ?? el.className) + ' ' + (a.animationName || '');
      const msg = !Number.isFinite(cx) ? 'no position' : (cx < -80 || cx > W + 80 || cy < -80 || cy > H + 80) && !/bounce|leave|drawcard|fly|reveal|intro|cardsheen|pitfall/.test(id) ? `off screen at ${Math.round(cx)},${Math.round(cy)}`
        : (r.x < 2 && r.y < 2 && r.width < 60 && r.width > 0) ? `in the window's corner (${Math.round(r.x)},${Math.round(r.y)})` : null;
      if (msg && !seen.has(id + msg.slice(0, 12))) { seen.add(id + msg.slice(0, 12)); window.__bad.push(`${id}: ${msg}`); } } }, 60); });
  for (let i = 0; i < m.views.length; i++) {
    await feed(p, m.views[i]);
    await wait(250);
    for (let k = 0; k < 80 && await p.evaluate(() => window.__ak().PB.busy); k++) await wait(100);
    await wait(i === m.views.length - 1 ? 4500 : 1200);   // a step's last animations (the end: the den's beat and the result's entrance)
    if (i % 3 === 0 || i === m.views.length - 1) {
      const bad = await p.evaluate(screenMismatches);
      const stuck = await p.evaluate(() => document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.getComputedTiming().endTime !== Infinity && a.effect.target && a.effect.target.isConnected)
        .map(a => `${a.animationName || 'anim'} on ${a.effect.target.className}`).slice(0, 3));
      for (const x of bad) problems.push({ match: m.name, view: i, kind: 'screen', x });
      for (const x of stuck) problems.push({ match: m.name, view: i, kind: 'still running 1.2 s after its step', x });
    }
    const moved = await p.evaluate(() => window.__bad.splice(0));
    for (const x of moved) problems.push({ match: m.name, view: i, kind: 'motion', x });
  }
  for (const e of p.errors) problems.push({ match: m.name, kind: 'page error', x: e });
  await p.close();
}
await b.close(); server.stop();
assert.deepEqual(problems, []);
});
