// A screenshot of the Ladder screen's Meta tab with a given report, phone and Mac widths (not a test; outside test/ so node --test ignores it):
//   cd animal_kingdom/web/shots && node shot_meta.mjs <report.json> <out-prefix>   (a report: GET /api/league/report, or league/report.py's build)
import { readFileSync } from 'node:fs';
import { startServer, openBrowser } from '../test/harness.mjs';
const [report, out] = process.argv.slice(2);
const srv = await startServer({ AK_LEAGUE_KEY: 'shot-key' });
const r = await fetch(`${srv.url}/api/league/report`, { method: 'POST', headers: { 'X-AK-League-Key': 'shot-key', 'Content-Type': 'application/json' }, body: JSON.stringify({ report: JSON.parse(readFileSync(report, 'utf8')) }) });
if (!r.ok) throw new Error('report not posted: ' + r.status);
const b = await openBrowser();
for (const [w, h, tag] of [[430, 932, 'phone'], [1512, 1400, 'mac']]) {
  const p = await b.newPage(); await p.setViewport({ width: w, height: h, deviceScaleFactor: 2 });
  await p.goto(`${srv.url}/#/ladder/meta`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('.metar section', { timeout: 15000 });
  await new Promise(res => setTimeout(res, 800));
  await p.screenshot({ path: `${out}_${tag}.png`, fullPage: true });
}
await b.close(); srv.stop();
console.log('shots written');
