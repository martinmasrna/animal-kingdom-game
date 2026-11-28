// node build.mjs: writes index.html, one self-contained file, from src/ and RULES.md.
// The three modules are concatenated in dependency order with their import lines and export
// keywords removed, inside one function scope; RULES.md becomes the rules panel.
import { readFileSync, writeFileSync } from 'node:fs';
const dir = new URL('./', import.meta.url);
const read = (p) => readFileSync(new URL(p, dir), 'utf8');

function strip(src) {
  return src
    .replace(/^import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm, '')
    .replace(/^export\s+(?=(const|function|let|class|async)\b)/gm, '');
}
// the little markdown RULES.md uses: headings, bullets, tables, bold, paragraphs
function md(src) {
  const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  const out = []; let list = false, table = null;
  const close = () => { if (list) { out.push('</ul>'); list = false; } if (table) { out.push('<table>' + table.join('') + '</table>'); table = null; } };
  for (const line of src.split('\n')) {
    if (/^\|/.test(line)) {
      if (/^\|[\s|:-]+\|$/.test(line)) continue;
      const cells = line.split('|').slice(1, -1).map(c => esc(c.trim()));
      if (!table) { close(); table = ['<tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr>']; } else table.push('<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>');
      continue;
    }
    const h = line.match(/^(#+)\s+(.*)/);
    if (h) { close(); out.push(`<h${h[1].length + 1}>${esc(h[2])}</h${h[1].length + 1}>`); continue; }
    const b = line.match(/^\s*-\s+(.*)/);
    if (b) { if (table) close(); if (!list) { out.push('<ul>'); list = true; } out.push(`<li>${esc(b[1])}</li>`); continue; }
    if (!line.trim()) { close(); continue; }
    close(); out.push(`<p>${esc(line)}</p>`);
  }
  close();
  return out.join('\n');
}
const js = ['src/engine.js', 'src/bot.js', 'src/ui.js'].map(f => `// ---- ${f}\n` + strip(read(f))).join('\n');
if (/^\s*(import|export)\b/m.test(js)) throw new Error('build: a module line was left in');
const html = read('src/page.html')
  .replace('/*STYLE*/', () => read('src/style.css'))
  .replace('<!--RULES-->', () => md(read('RULES.md').replace(/ ?All numbers are placeholders\./, '')))
  .replace('/*SCRIPT*/', () => '(function () {\n"use strict";\n' + js + '\n})();');
writeFileSync(new URL('index.html', dir), html);
// artifact.html: the same page without the document wrapper, for publishing as an Artifact
const head = html.slice(html.indexOf('<title>'), html.indexOf('</head>'));
const body = html.slice(html.indexOf('>', html.indexOf('<body')) + 1, html.indexOf('</body>'));
writeFileSync(new URL('artifact.html', dir), head + body);
console.log('index.html written, ' + html.length + ' bytes');
