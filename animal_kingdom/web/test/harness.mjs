// Shared set-up for the browser tests: a private server on a free port (games not logged) and a headless browser.
import { spawn } from 'node:child_process';
import { readdirSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import net from 'node:net';
import puppeteer from 'puppeteer-core';

const REPO = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const PY = process.env.AK_PYTHON || join(REPO, '.venv', ...(process.platform === 'win32' ? ['Scripts', 'python.exe'] : ['bin', 'python']));
// Chrome for Testing when it is installed (`npx @puppeteer/browsers install chrome@stable`, into ~/.cache/puppeteer): Google's
// automation build, a separate app, so a focus blocker that polices Google Chrome (Cold Turkey quit every test browser on
// Martin's Mac, 2026-11-04) leaves it alone. Otherwise the installed Google Chrome.
function chromeForTesting() {
  const root = join(homedir(), '.cache', 'puppeteer', 'chrome');
  if (!existsSync(root)) return null;
  for (const v of readdirSync(root).sort().reverse()) {
    const dir = join(root, v);
    const app = readdirSync(dir).find(d => d.startsWith('chrome-'));
    if (!app) continue;
    const exe = process.platform === 'win32' ? join(dir, app, 'chrome.exe')
      : process.platform === 'darwin' ? join(dir, app, 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing')
      : join(dir, app, 'chrome');
    if (existsSync(exe)) return exe;
  }
  return null;
}
const CHROME = process.env.CHROME || chromeForTesting() || (process.platform === 'win32' ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
                                                                                           : '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');

const freePort = () => new Promise(res => { const s = net.createServer(); s.listen(0, () => { const { port } = s.address(); s.close(() => res(port)); }); });

export async function startServer(env = {}) {   // env: extra variables for the server (a test's AK_DB, say)
  const port = await freePort();
  // The server exits when its stdin closes, so a test process that dies without reaching after() takes it down too
  // (otherwise each killed run left a server running for days).
  const boot = 'import os, sys, threading, runpy; threading.Thread(target=lambda: (sys.stdin.read(), os._exit(0)), daemon=True).start(); '
    + `sys.argv = ['server', '--port', '${port}', '--no-open']; runpy.run_module('animal_kingdom.web.server', run_name='__main__')`;
  const proc = spawn(PY, ['-c', boot],
    { cwd: REPO, env: { ...process.env, AK_NO_GAME_LOGS: '1', AK_BOT_PAUSE: '0', ...env }, stdio: ['pipe', 'ignore', 'ignore'] });
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(`http://localhost:${port}/`); if (r.ok) return { url: `http://localhost:${port}`, stop: () => proc.kill() }; } catch { }
    await new Promise(r => setTimeout(r, 100));
  }
  proc.kill(); throw new Error('server did not start');
}

export async function openBrowser() {
  // root (a cloud container) can't run Chrome's sandbox
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', defaultViewport: { width: 1512, height: 800 },
    args: process.getuid?.() === 0 ? ['--no-sandbox'] : [] });
  // Chrome's crash reporter (chrome_crashpad_handler) inherits its stdout and stderr and can outlive it; our end of those
  // pipes then keeps the test process alive for minutes after its last test (a hang seen on 2026-10-04). Close our end.
  const close = b.close.bind(b), proc = b.process();
  b.close = async () => { await close(); proc?.stdout?.destroy(); proc?.stderr?.destroy(); };
  return b;
}

// A console error from another server (the Google Fonts stylesheet, when the network hiccups) is not the game's.
export const offsite = m => /^https?:\/\//.test(m.location()?.url || '') && !/^https?:\/\/(localhost|127\.0\.0\.1)[:/]/.test(m.location().url);

