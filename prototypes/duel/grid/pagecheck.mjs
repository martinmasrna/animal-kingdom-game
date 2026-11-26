// node pagecheck.mjs [outdir]: opens index.html in headless Chrome for Testing, plays full matches by clicking the page,
// checks for console errors and layout overflow at phone and desktop sizes, saves screenshots.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { homedir, tmpdir } from 'node:os';

const outDir = process.argv[2] || join(tmpdir(), 'duel-grid-pagecheck');
process.on('exit', () => { try { chrome.kill(); } catch {} });
mkdirSync(outDir, { recursive: true });
const pageUrl = new URL('./index.html', import.meta.url).href;

function findChrome() {
  const base = join(homedir(), '.cache/puppeteer/chrome');
  if (existsSync(base)) for (const v of readdirSync(base).filter((d) => d.startsWith('mac')).sort().reverse()) {
    const p = join(base, v, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
    if (existsSync(p)) return p;
  }
  throw new Error('no Chrome for Testing found');
}

const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(findChrome(), ['--headless=new', `--remote-debugging-port=${port}`, '--no-first-run', '--no-default-browser-check',
  `--user-data-dir=${join(outDir, 'profile-' + Date.now())}`, '--allow-file-access-from-files', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect() {
  for (let i = 0; i < 50; i++) {
    try { const r = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent('about:blank')}`, { method: 'PUT' }); if (r.ok) return (await r.json()).webSocketDebuggerUrl; } catch {}
    await sleep(200);
  }
  throw new Error('chrome did not start');
}

const wsUrl = await connect();
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0; const pending = new Map(); const problems = [];
ws.addEventListener('message', (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { const { res, rej } = pending.get(msg.id); pending.delete(msg.id); msg.error ? rej(new Error(msg.error.message)) : res(msg.result); }
  if (msg.method === 'Runtime.exceptionThrown') problems.push('exception: ' + JSON.stringify(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text));
  if (msg.method === 'Runtime.consoleAPICalled' && (msg.params.type === 'error' || msg.params.type === 'warning')) problems.push('console.' + msg.params.type + ': ' + msg.params.args.map((a) => a.value ?? a.description).join(' '));
  if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') problems.push('log: ' + msg.params.entry.text);
  if (msg.method === 'Network.requestWillBeSent' && !/^(file|data|about):/.test(msg.params.request.url)) problems.push('network request: ' + msg.params.request.url);
});
const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(outDir, name), Buffer.from(r.data, 'base64')); };
const viewport = (w, h, mobile) => send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });

await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable'); await send('Network.enable');

// In-page driver: clicks only. Reads app.mode just to know when to act.
const DRIVER = `
window.__drive = async function (opts) {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const A = window.__duel;
  const click = (el) => el && el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  const rnd = (xs) => xs[Math.floor(Math.random() * xs.length)];
  let rounds = 0, guard = 0, warnSeen = 0;
  while (A.mode !== 'over' && rounds < (opts.maxRounds || 80)) { guard++; if (A.errors.length) break;
    if (A.mode === 'choose') {
      while (!A.botChoice) await sleep(10);
      // pick up to two cards at random among the enabled ones, aim each attack, maybe step
      for (let k = 0; k < 2; k++) {
        const cards = [...document.querySelectorAll('#hand .card:not(:disabled):not(.sel)')];
        if (!cards.length || Math.random() < 0.25) break;
        click(rnd(cards));
        const aims = [...document.querySelectorAll('#gridOp .tile.aim')];
        if (aims.length && Math.random() < 0.7) click(rnd(aims));
        if (document.querySelector('.chip.incomplete')) { const a2 = [...document.querySelectorAll('#gridOp .tile.aim')]; for (let z = 0; z < 2 && document.querySelector('.chip.incomplete'); z++) click(rnd(a2)); }
      }
      const steps = [...document.querySelectorAll('#gridMe .tile.stepok')];
      if (steps.length && Math.random() < 0.6) click(rnd(steps));
      if (document.querySelector('.chip.warn')) warnSeen++;
      if (opts.pauseAt === rounds && opts.onPause) { await opts.onPause(); }
      let commit = document.getElementById('commit');
      while (commit && commit.disabled) { const x = document.querySelector('.chip .x'); if (!x) break; click(x); commit = document.getElementById('commit'); }
      if (!commit || commit.disabled) throw new Error('cannot commit');
      click(commit);
      rounds++;
    } else if (A.mode === 'play') {
      if (opts.tapThrough) click(document.getElementById('midline')); else await sleep(5);
      await sleep(5);
    } else await sleep(10);
  }
  return { rounds, mode: A.mode, winner: A.state.winner, logLines: A.log.length, errors: A.errors, warnSeen,
    lastLog: A.log.slice(-4).map((l) => l.text) };
};`;

const report = { matches: [] };
async function load(w, h, mobile) {
  await viewport(w, h, mobile);
  await send('Page.navigate', { url: pageUrl + '?fast' });
  await sleep(700);
  await evaluate(DRIVER);
}
const layout = () => evaluate(`({ sw: document.documentElement.scrollWidth, iw: innerWidth, sh: document.documentElement.scrollHeight, ih: innerHeight,
  smallestFont: Math.min(...[...document.querySelectorAll('#game *')].filter(e => e.offsetParent && e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize))) })`);

// Phone, upright
await load(390, 780, true);
await shot('phone-start.png');
await evaluate(`document.querySelector('[data-for=me][data-hero=Quick]').click(); document.querySelector('[data-for=op][data-hero=Heavy]').click(); document.getElementById('btnStart').click();`);
await sleep(300);
// a hand-built selection for the screenshot: Jab at his tile, a second attack if possible, a step
await evaluate(`(async () => {
  const click = (el) => el && el.click();
  click(document.querySelector('#hand .card[data-card=Jab]'));
  const second = [...document.querySelectorAll('#hand .card:not(:disabled):not(.sel)')].find(c => ['Slash','Bolt','Lunge','Flurry','Smash','Blast','Haymaker'].includes(c.dataset.card));
  if (second) { click(second); const aims = document.querySelectorAll('#gridOp .tile.aim'); click(aims[aims.length - 1]); }
  click(document.querySelector('#gridMe .tile.stepok'));
})()`);
await sleep(200);
report.phoneChooseLayout = await layout();
await shot('phone-choose.png');
await evaluate(`(() => { let c = document.getElementById('commit'); while (c.disabled && document.querySelector('.chip .x')) { document.querySelector('.chip .x').click(); c = document.getElementById('commit'); } c.click(); })()`);
await sleep(100);
await evaluate(`(async () => { const s = (ms) => new Promise(r => setTimeout(r, ms)); while (__duel.mode === 'play' && __duel.play && __duel.play.i < 1) await s(5); })()`);
await shot('phone-reveal.png');
// play the rest of this match through the UI
report.matches.push({ where: 'phone 390x780', ...(await evaluate(`__drive({ tapThrough: true })`)) });
report.phoneEndLayout = await layout();
await shot('phone-end.png');
await evaluate(`document.getElementById('btnEndLog').click()`);
await sleep(150);
await shot('phone-log.png');
await evaluate(`document.querySelector('[data-close=logOv]').click(); document.getElementById('btnDecks').click()`);
await sleep(150);
await shot('phone-decks.png');
await evaluate(`document.querySelector('[data-close=decksOv]').click(); document.querySelector('#tray [data-act=rematch]').click()`);
await sleep(300);
report.matches.push({ where: 'phone rematch', ...(await evaluate(`__drive({})`)) });

// Small phone
await load(360, 740, true);
await evaluate(`document.getElementById('btnStart').click()`);
await sleep(300);
report.smallPhoneLayout = await layout();
await shot('phone360-choose.png');
report.matches.push({ where: 'phone 360x740', ...(await evaluate(`__drive({ tapThrough: true })`)) });

// Phone fit: a 6-card hand, two attacks chosen; basics, Commit and every tile must be on screen without scrolling.
// Runs on index.html and on artifact.html inside a stand-in wrapper like the publisher's.
const wrapped = join(outDir, 'artifact-wrapped.html');
writeFileSync(wrapped, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body style="margin:0;height:100%">'
  + (await import('node:fs')).readFileSync(new URL('./artifact.html', import.meta.url), 'utf8') + '</body></html>');
report.fit = [];
for (const [w, h, src] of [[375, 700, pageUrl], [390, 780, pageUrl], [375, 700, 'file://' + wrapped], [390, 780, 'file://' + wrapped]]) {
  await viewport(w, h, true);
  await send('Page.navigate', { url: src + '?fast' });
  await sleep(700);
  await evaluate(`document.querySelector('[data-for=me][data-hero=Quick]').click(); document.getElementById('btnStart').click()`);
  await sleep(300);
  const fit = await evaluate(`(async () => {
    const A = __duel; while (!A.botChoice) await new Promise(r => setTimeout(r, 10));
    A.state.p[0].hand = ['Slash', 'Bolt', 'Lunge', 'Parry', 'Smash', 'Study']; A.render();
    const c = (sel) => document.querySelector(sel).click();
    c('#hand .card[data-card=Slash]'); c('#hand .card[data-card=Bolt]');
    const aims = document.querySelectorAll('#gridOp .tile.aim'); aims[aims.length - 1].click();
    c('#gridMe .tile.stepok');
    const r = (el) => el.getBoundingClientRect();
    const inView = (el) => { const b = r(el); return b.top >= 0 && b.left >= 0 && b.bottom <= innerHeight && b.right <= innerWidth; };
    const hand = document.getElementById('hand');
    const basics = [...hand.querySelectorAll('.card.basic')];
    const tiles = [...document.querySelectorAll('.grid .tile')];
    return { size: innerWidth + 'x' + innerHeight, src: location.pathname.split('/').pop(),
      basicsFirst: hand.firstElementChild === basics[0] && basics[0].nextElementSibling === basics[1],
      basicsVisible: basics.every(inView), commitVisible: inView(document.getElementById('commit')), commitEnabled: !document.getElementById('commit').disabled,
      allTilesVisible: tiles.every(inView), smallestTile: Math.min(...tiles.map(t => Math.min(r(t).width, r(t).height))),
      gutterLeft: r(document.getElementById('center')).left, gutterRight: innerWidth - r(document.getElementById('center')).right,
      pageScrolls: document.documentElement.scrollHeight > innerHeight || document.documentElement.scrollWidth > innerWidth,
      chips: [...document.querySelectorAll('#tray .chip')].map(x => x.textContent.split(String.fromCharCode(10)).map(y => y.trim()).filter(Boolean).join(' ')) };
  })()`);
  report.fit.push(fit);
  await shot(`fit-${fit.src.replace('.html', '')}-${w}x${h}.png`);
}

// Desktop
await load(1500, 800, false);
await evaluate(`document.querySelector('[data-for=op][data-hero=Heavy]').click(); document.getElementById('btnStart').click()`);
await sleep(300);
await evaluate(`(async () => { document.querySelector('#hand .card[data-card=Block]').click(); const a = [...document.querySelectorAll('#hand .card:not(:disabled):not(.sel)')].find(c => c.dataset.card !== 'Block' && c.dataset.card !== 'Jab'); if (a) a.click(); })()`);
await sleep(150);
report.desktopLayout = await layout();
await shot('desktop-choose.png');
report.matches.push({ where: 'desktop 1500x800', ...(await evaluate(`__drive({})`)) });
report.desktopEndLayout = await layout();
await shot('desktop-end.png');
// several more fast matches on desktop, mixing hero picks, to shake out errors
for (let k = 0; k < 4; k++) {
  await evaluate(`document.getElementById('btnNew').click(); document.querySelector('[data-for=me][data-hero=${k % 2 ? 'Heavy' : 'Quick'}]').click(); document.querySelector('[data-for=op][data-hero=${k < 2 ? 'Quick' : 'Heavy'}]').click(); document.getElementById('btnStart').click()`);
  await sleep(200);
  report.matches.push({ where: 'desktop extra ' + k, ...(await evaluate(`__drive({ tapThrough: ${k % 2 === 0} })`)) });
}
// new match mid-round and mid-reveal must not leave timers running into the next match
await evaluate(`document.getElementById('btnNew').click(); document.getElementById('btnStart').click()`);
await sleep(200);
await evaluate(`document.querySelector('#hand .card[data-card=Jab]')?.click(); document.getElementById('commit').click(); document.getElementById('btnNew').click(); document.getElementById('btnStart').click();`);
await sleep(1500);
report.afterRestart = await evaluate(`({ mode: __duel.mode, round: __duel.state.round, errors: __duel.errors })`);

report.problems = problems;
console.log(JSON.stringify(report, null, 1));
console.log('screenshots in', outDir);
ws.close(); chrome.kill();
process.exit(problems.length || report.fit.some((f) => !f.basicsVisible || !f.commitVisible || !f.allTilesVisible || f.smallestTile < 40 || f.pageScrolls) || report.matches.some((m) => m.errors.length || m.mode !== 'over') ? 1 : 0);
