// The game's deck list, made self-contained: every CSS rule that styles the deck body (urls inlined), the ancestor chain
// its selectors expect, each card's strip art as rendered (2x, unmasked), the chalk digits and the deck-list font.
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { startServer, openBrowser } from '../../animal_kingdom/web/test/harness.mjs';
const OUT = process.argv[2] || 'results/ladder_page/strips.json';   // run from the game repo
const srv = await startServer();
const b = await openBrowser();
const p = await b.newPage(); await p.setViewport({ width: 1512, height: 820, deviceScaleFactor: 2 });
await p.goto(`${srv.url}/#/collection`, { waitUntil: 'networkidle0' });
await p.waitForSelector('.dtile', { timeout: 15000 });
await p.evaluate(() => document.querySelector('.dtile').click()); await p.waitForSelector('.dbody', { timeout: 15000 });
await new Promise(r => setTimeout(r, 800));
const out = await p.evaluate(async () => {
  const { deckBody } = await import('/static/collection.js');
  const pool = await fetch('/api/pool').then(r => r.json());
  const cards = Object.fromEntries(pool.cards.map(c => [c.id, c]));
  const ids = pool.cards.filter(c => c.status !== 'planned').map(c => c.id);   // every card a league list may hold, a reserve legendary too
  const el = document.querySelector('.dbody');
  el.outerHTML = deckBody([...ids, ids.find(i => cards[i].rarity === 'common'), ids.find(i => cards[i].rarity === 'common')], cards);
  const body = document.querySelector('.dbody');
  let q = body; while (q && q !== document.body) { q.style.maxHeight = 'none'; q.style.overflow = 'visible'; q.style.height = 'auto'; q = q.parentElement; }
  const chain = []; for (let a = body.parentElement; a && a !== document.documentElement; a = a.parentElement) chain.unshift({ tag: a.tagName.toLowerCase(), cls: a.className });
  const subtree = [body, ...body.querySelectorAll('*')];
  const strip = sel => sel.replace(/::?(before|after|hover|focus-visible|focus|active)\b/g, '');
  const matches = sel => { try { const s = strip(sel); return subtree.some(e => e.matches(s)); } catch { return false; } };
  const css = [], fonts = [];
  const walk = rules => { for (const r of rules) {
    if (r instanceof CSSStyleRule) { if (matches(r.selectorText)) css.push(r.cssText); }
    else if (r instanceof CSSMediaRule) { if (matchMedia(r.media.mediaText).matches) walk(r.cssRules); }
    else if (r instanceof CSSFontFaceRule) fonts.push(r.cssText);
    else if (r instanceof CSSImportRule) { try { walk(r.styleSheet.cssRules); } catch {} }
    else if (r.cssRules) walk(r.cssRules);
  } };
  for (const s of document.styleSheets) { try { walk(s.cssRules); } catch {} }
  const text = css.join('\n');
  const vars = [...new Set(text.match(/var\(--[\w-]+/g) || [])].map(v => v.slice(4));
  const cs = getComputedStyle(body);
  const root = vars.map(v => [v, cs.getPropertyValue(v).trim()]).filter(([, v]) => v);
  const inherit = { color: cs.color, 'font-family': cs.fontFamily, 'font-size': cs.fontSize, 'line-height': cs.lineHeight };
  const usedFonts = new Set((text + cs.fontFamily).match(/'[^']+'|"[^"]+"/g)?.map(f => f.slice(1, -1)) || []);
  const fontText = fonts.filter(f => [...usedFonts].some(u => f.includes(u))).join('\n');
  const all = text + '\n' + fontText;
  const urls = [...new Set([...all.matchAll(/url\(["']?([^"')]+)["']?\)/g)].map(m => m[1]).filter(u => !u.startsWith('data:')))];
  const toData = async u => { const blob = await fetch(u).then(r => r.blob()); return await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(blob); }); };
  const map = {}; for (const u of urls) map[u] = await toData(u);
  const chalk = {}; for (const d of '0123456789') chalk[d] = await toData(`/static/kit2/chalk/${d}.webp`);
  // the art: unmask so the screenshot is the painting alone; the page applies the same mask
  document.querySelectorAll('.dbody .st .art').forEach(a => { a.style.maskImage = 'none'; a.style.webkitMaskImage = 'none'; a.style.opacity = '1'; });
  const meta = Object.fromEntries(ids.map(i => [i, { name: cards[i].name, rarity: cards[i].rarity, str: cards[i].str }]));
  return { css: text, fontText, map, chalk, root, inherit, chain, meta, ids };
});
let { css, fontText, map } = out;
for (const [u, d] of Object.entries(map)) { css = css.split(u).join(d); fontText = fontText.split(u).join(d); }
const art = {};
for (const id of out.ids) {
  const h = await p.$(`.dbody .st[data-card="${id}"] .art`);
  if (!h) continue;
  const box = await h.boundingBox(); if (!box || box.width < 2) continue;
  const buf = await h.screenshot({ type: 'webp', quality: 80 });
  art[id] = 'data:image/webp;base64,' + Buffer.from(buf).toString('base64');
}
mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ css, fontText, chalk: out.chalk, root: out.root, inherit: out.inherit, chain: out.chain, meta: out.meta, art }));
await b.close(); srv.stop();
console.log('cards', out.ids.length, 'art', Object.keys(art).length, 'css', css.length, 'fonts', fontText.length, 'chain', JSON.stringify(out.chain));
