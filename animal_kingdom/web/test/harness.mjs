// Shared set-up for the browser tests: a private server on a free port (games not logged), recorded view sequences,
// and a page that plays views through the client (window.__ak.feed) the way the socket delivers them.
import { spawn, execFileSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';
import puppeteer from 'puppeteer-core';

const REPO = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const PY = process.env.AK_PYTHON || join(REPO, '.venv', 'bin', 'python');
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const freePort = () => new Promise(res => { const s = net.createServer(); s.listen(0, () => { const { port } = s.address(); s.close(() => res(port)); }); });

export async function startServer() {
  const port = await freePort();
  const proc = spawn(PY, ['-m', 'animal_kingdom.web.server', '--port', String(port), '--no-open'],
    { cwd: REPO, env: { ...process.env, AK_NO_GAME_LOGS: '1' }, stdio: 'ignore' });
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(`http://localhost:${port}/`); if (r.ok) return { url: `http://localhost:${port}`, stop: () => proc.kill() }; } catch { }
    await new Promise(r => setTimeout(r, 100));
  }
  proc.kill(); throw new Error('server did not start');
}

// Bot-vs-bot matches recorded as the views one seat receives (record_views.py), both seats per match.
export function recordMatches(n = 7) {
  const dir = mkdtempSync(join(tmpdir(), 'ak-views-'));
  execFileSync(PY, ['-m', 'animal_kingdom.web.test.record_views', dir, '--matches', String(n)], { cwd: REPO, stdio: 'ignore' });
  return readdirSync(dir).filter(f => f.endsWith('.json')).sort().map(f => ({ name: f, views: JSON.parse(readFileSync(join(dir, f))) }));
}

export async function openBrowser() {
  return puppeteer.launch({ executablePath: CHROME, headless: 'new', defaultViewport: { width: 1512, height: 800 } });
}

// A game page showing the frozen lab view, ready to be fed; `still` asks for reduced motion, which the client honours by
// showing every change at once, so each view can be checked the moment it is drawn. Page errors are collected in page.errors.
export async function gamePage(browser, url, { still = true } = {}) {
  const page = await browser.newPage();
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !/favicon/.test(m.text())) page.errors.push(m.text()); });
  await page.goto(`${url}/#/lab/mid`, { waitUntil: 'networkidle0' });
  if (still) await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  return page;
}

export const feed = (page, view) => page.evaluate(v => window.__ak.feed(v), view);
