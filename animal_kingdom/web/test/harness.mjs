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

// Pages open as a player who has done the tutorial (home shows the full piece); `newPlayer` opens them as a first visit.
export async function openBrowser({ newPlayer = false } = {}) {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', defaultViewport: { width: 1512, height: 800 } });
  if (!newPlayer) { const open = b.newPage.bind(b);
    b.newPage = async () => { const p = await open(); await p.evaluateOnNewDocument(() => { try { localStorage.setItem('ak:learned', '1'); } catch { /* no storage */ } }); return p; }; }
  return b;
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

// Runs in the page: what the screen shows, against what the current view says it should show. Returns a list of
// mismatches (empty when the screen is right).
export function screenMismatches() {
  const { V } = window.__ak(), G = V.game, out = [];
  if (!G) return out;
  const you = V.you, them = you === 'A' ? 'B' : 'A', rel = p => (p === you ? 'A' : 'B');
  const dcr = cr => { if (you === 'A') return cr; const [c, r] = cr.split(','); return `${6 - +c},${r}`; };
  const visible = e => { const s = getComputedStyle(e), r = e.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.5 && r.width > 20; };
  const digits = e => [...e.querySelectorAll('img')].map(i => i.alt).join('');

  // the board
  const want = {};
  for (const [cr, st] of Object.entries(G.board)) want[dcr(cr)] = st;
  for (const el of document.querySelectorAll('#board .cr[data-cr]')) {
    const cr = el.dataset.cr, st = want[cr];
    if (!st) { if (el.classList.contains('unit') && !el.classList.contains('ghost')) out.push(`${cr}: a unit shown on an empty crossroad`); continue; }
    if (el.classList.contains('ghost')) continue;   // a placement preview under the pointer
    const top = st[st.length - 1];
    if (!el.classList.contains('unit')) { out.push(`${cr}: ${top.id} missing`); continue; }
    if (!visible(el)) out.push(`${cr}: ${top.id} not visible`);
    if (!el.classList.contains(rel(top.owner))) out.push(`${cr}: ${top.id} in the wrong colour`);
    const str = digits(el.querySelector('.boss'));
    if (str !== String(top.str)) out.push(`${cr}: ${top.id} shows strength ${str}, is ${top.str}`);
    const timer = el.querySelector('.timer');
    const alts = e => [...e.querySelectorAll('img')].map(i => i.alt).join('');   // painted digits: their alt text
    if (top.timer && !(timer && alts(timer) === String(top.timer))) out.push(`${cr}: ${top.id} timer ${top.timer} not shown`);
    const kw = (window.__ak.cards()[top.id].kw || []).filter(k => ['Armor', 'Stealth'].includes(k));
    const badges = [...el.querySelectorAll('.kw img')].map(i => i.alt).join(', ');   // one painted badge per keyword
    if (kw.length && badges !== kw.join(', ')) out.push(`${cr}: ${top.id} is ${kw.join(', ')} but shows ${badges || 'no badge'}`);
    const buried = el.querySelectorAll('.buried').length;
    if (buried !== Math.min(3, st.length - 1)) out.push(`${cr}: ${buried} buried discs for a stack of ${st.length}`);
    delete want[cr];
  }
  for (const cr of Object.keys(want)) out.push(`${cr}: no crossroad element for ${want[cr].slice(-1)[0].id}`);

  // the dens: the gem shows the food; pit i holds the ripe and ghost fruit of food and income, ten to a pit
  for (const side of ['A', 'B']) {
    const seat = side === 'A' ? you : them, food = G.food[seat], inc = G.income[seat], win = G.winFood;
    const gem = document.querySelector(`#board .dcount.${side}`);
    if (!gem || digits(gem) !== String(food)) out.push(`den ${side}: gem shows ${gem && digits(gem)}, food is ${food}`);
    const ripe = Math.min(food, win), green = Math.max(0, Math.min(inc, win - ripe));
    const pits = [...document.querySelectorAll('#board .pit img.now')].filter(i => i.src.includes(`/${side.toLowerCase()}pit`));
    if (pits.length !== 10) out.push(`den ${side}: ${pits.length} pits`);
    pits.forEach((img, i) => {
      const r = Math.max(0, Math.min(10, ripe - i * 10)), t = Math.max(0, Math.min(10, ripe + green - i * 10));
      if (!img.src.endsWith(`_${r}_${t - r}.webp`)) out.push(`den ${side} pit ${i}: shows ${img.src.split('/').pop()}, should hold ${r} ripe ${t - r} ghost`);
    });
  }

  // both hands
  const backs = document.querySelectorAll('#opphand .back').length;
  if (backs !== G.handCount[them]) out.push(`${backs} card backs, they hold ${G.handCount[them]}`);
  const hand = [...document.querySelectorAll('#hand .hc')].map(e => +e.dataset.iid);
  if (hand.join() !== G.hand.map(h => h.iid).join()) out.push(`hand shows ${hand}, is ${G.hand.map(h => h.iid)}`);

  // a game won by taking a den shows the unit that took it, in that den's mouth
  if (G.result && G.result.reason === 'hq_capture') { const cap = document.querySelector('#board .cr.unit.capture');
    if (!cap || !visible(cap)) out.push('the unit that took the den is not shown'); }

  // whose turn, and the end of a game
  const tb = document.getElementById('tbtn').textContent;
  if (V.phase === 'playing' && !(G.current === you ? /End turn/.test(tb) : /Their turn/.test(tb))) out.push(`turn button says "${tb}"`);
  const ended = V.phase === 'game_over' || V.phase === 'match_over';
  if (ended !== document.getElementById('endov').classList.contains('on')) out.push(`end overlay ${ended ? 'missing' : 'shown mid-game'}`);
  return out;
}
