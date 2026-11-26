// node build.mjs: writes index.html, one self-contained file, from src/.
// The three modules are concatenated in dependency order with their
// import lines and export keywords removed, inside one function scope.
import { readFileSync, writeFileSync } from 'node:fs';
// node build.mjs full: the full-hand variant, written to index-full.html and artifact-full.html
const FULL = process.argv[2] === 'full';
const dir = new URL('./', import.meta.url);
const read = (p) => readFileSync(new URL(p, dir), 'utf8');

function strip(src) {
  return src
    .replace(/^import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm, '')
    .replace(/^export\s+(?=(const|function|let|class)\b)/gm, '');
}
const js = ['src/engine.js', 'src/bot.js', 'src/ui.js'].map(f => `// ---- ${f}\n` + strip(read(f))).join('\n').replace('/*BOOT*/', FULL ? 'setFullHand(true);' : '');
if (/^\s*(import|export)\b/m.test(js)) throw new Error('build: a module line was left in');
const html = read('src/page.html')
  .replace('/*STYLE*/', () => read('src/style.css'))
  .replace('/*SCRIPT*/', () => '(function () {\n"use strict";\n' + js + '\n})();');
const title = FULL ? html.replace('<title>Board Toy 4</title>', '<title>Board Toy 4, Full Hand</title>') : html;
writeFileSync(new URL(FULL ? 'index-full.html' : 'index.html', dir), title);
// artifact.html: the same page without the document wrapper, for publishing as an Artifact
// (the publisher adds its own doctype, head and body).
const head = title.slice(title.indexOf('<title>'), title.indexOf('</head>'));
const body = title.slice(title.indexOf('>', title.indexOf('<body')) + 1, title.indexOf('</body>'));
writeFileSync(new URL(FULL ? 'artifact-full.html' : 'artifact.html', dir), head + body);
console.log('index.html written, ' + html.length + ' bytes');

