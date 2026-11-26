// node build.mjs: writes index.html, one self-contained file, from src/.
// The three modules are concatenated in dependency order with their
// import lines and export keywords removed, inside one function scope.
import { readFileSync, writeFileSync } from 'node:fs';
const dir = new URL('./', import.meta.url);
const read = (p) => readFileSync(new URL(p, dir), 'utf8');

function strip(src) {
  return src
    .replace(/^import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm, '')
    .replace(/^export\s+(?=(const|function|let|class)\b)/gm, '');
}
const js = ['src/engine.js', 'src/bot.js', 'src/ui.js'].map(f => `// ---- ${f}\n` + strip(read(f))).join('\n');
if (/^\s*(import|export)\b/m.test(js)) throw new Error('build: a module line was left in');
const html = read('src/page.html')
  .replace('/*STYLE*/', () => read('src/style.css'))
  .replace('/*SCRIPT*/', () => '(function () {\n"use strict";\n' + js + '\n})();');
writeFileSync(new URL('index.html', dir), html);
// artifact.html: the same page without the document wrapper, for publishing as an Artifact
// (the publisher adds its own doctype, head and body).
const head = html.slice(html.indexOf('<title>'), html.indexOf('</head>'));
const body = html.slice(html.indexOf('>', html.indexOf('<body')) + 1, html.indexOf('</body>'));
writeFileSync(new URL('artifact.html', dir), head + body);
console.log('index.html written, ' + html.length + ' bytes');
