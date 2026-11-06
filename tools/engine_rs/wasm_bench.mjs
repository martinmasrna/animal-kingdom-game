// The browser numbers in knowledge/wasm/STATUS.md: the wasm's size, its load time in a fresh browser (fetch, compile,
// the engine built from /api/local/engine), and the bots' time per move in a Web Worker on the positions wasm_bench.py
// timed on the server's engine, each by a fresh bot of the level, as there. Headless Chromium on this machine.
//
//     .venv/bin/python tools/engine_rs/wasm_bench.py --out /tmp/pos.json && node tools/engine_rs/wasm_bench.mjs /tmp/pos.json
//
// Needs the web tests' npm install (puppeteer-core) and CHROME set as for those tests.
import { readFileSync, statSync } from 'node:fs';
import { gzipSync, brotliCompressSync } from 'node:zlib';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, openBrowser } from '../../animal_kingdom/web/test/harness.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const WASM = join(ROOT, 'animal_kingdom/web/static/wasm/ak_engine_bg.wasm');
const data = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const bytes = readFileSync(WASM);
const kb = n => (n / 1024).toFixed(0) + ' KB';
console.log(`wasm: ${kb(statSync(WASM).size)} raw, ${kb(gzipSync(bytes, { level: 9 }).length)} gzip, ${kb(brotliCompressSync(bytes).length)} brotli`);

const server = await startServer();
const browser = await openBrowser();
const stats = ms => { const s = [...ms].sort((a, b) => a - b); return { median: s[Math.floor(s.length / 2)], mean: s.reduce((a, b) => a + b, 0) / s.length, max: s[s.length - 1] }; };
try {
  // load: three fresh contexts (no cache), the median
  const loads = [];
  for (let i = 0; i < 3; i++) {
    const ctx = await browser.createBrowserContext();
    const page = await ctx.newPage();
    await page.goto(`${server.url}/privacy`);
    loads.push(await page.evaluate(async () => {
      const t0 = performance.now();
      const [mod, doc] = await Promise.all([fetch('/static/wasm/ak_engine_bg.wasm').then(r => r.arrayBuffer()).then(b => WebAssembly.compile(b)),
        fetch('/api/local/engine').then(r => r.json())]);
      const t1 = performance.now();
      const ak = await import('/static/wasm/ak_engine.js');
      await ak.default({ module_or_path: mod });
      new ak.Engine(JSON.stringify(doc.cards), JSON.stringify(doc.maps), JSON.stringify(doc.config), doc.map_id);
      return { fetchCompile: t1 - t0, total: performance.now() - t0 };
    }));
    await ctx.close();
  }
  loads.sort((a, b) => a.total - b.total);
  console.log(`load (fresh browser, localhost): fetch + compile ${loads[1].fetchCompile.toFixed(0)} ms, ready ${loads[1].total.toFixed(0)} ms`);

  const page = await browser.newPage();
  await page.goto(`${server.url}/privacy`);
  for (const [level, native] of Object.entries(data.native.levels)) {
    const out = await page.evaluate(async (states, setup) => {
      const doc = await (await fetch('/api/local/engine')).json();
      const src = `import init, { Engine, Bot } from '${location.origin}/static/wasm/ak_engine.js';
        onmessage = async ({ data: { doc, setup, states } }) => {
          await init();
          const eng = new Engine(JSON.stringify(doc.cards), JSON.stringify(doc.maps), JSON.stringify(doc.config), doc.map_id);
          const ms = [], moves = [];
          for (let i = 0; i < states.length; i++) {
            const bot = new Bot(setup.spec, 1000 + i, setup.evaluator || ''), st = eng.fromJson(JSON.stringify(states[i]));
            const t0 = performance.now(); moves.push(JSON.parse(bot.choose(st))); ms.push(performance.now() - t0);
            bot.free(); st.free();
          }
          postMessage({ ms, moves });
        };`;
      const w = new Worker(URL.createObjectURL(new Blob([src], { type: 'text/javascript' })), { type: 'module' });
      return await new Promise(res => { w.onmessage = e => res(e.data); w.postMessage({ doc, setup, states }); });
    }, data.states, { spec: native.spec, evaluator: native.evaluator });
    const same = out.moves.filter((m, i) => JSON.stringify(m) === JSON.stringify(native.moves[i])).length;
    const b = stats(out.ms), n = stats(native.ms);
    const ratio = out.ms.reduce((a, x) => a + x, 0) / native.ms.reduce((a, x) => a + x, 0);
    console.log(`${level}: ${out.ms.length} moves; browser median ${b.median.toFixed(0)} ms, mean ${b.mean.toFixed(0)}, max ${b.max.toFixed(0)}; ` +
      `server median ${n.median.toFixed(0)} ms, mean ${n.mean.toFixed(0)}, max ${n.max.toFixed(0)}; browser/server ${ratio.toFixed(2)}x; same move ${same}/${out.ms.length}`);
  }
} finally {
  await browser.close(); server.stop();
}
