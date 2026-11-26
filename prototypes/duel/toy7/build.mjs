// node build.mjs: writes index.html and artifact.html from src/.
import { readFileSync, writeFileSync } from 'node:fs';
const dir = new URL('./', import.meta.url);
const read = (p) => readFileSync(new URL(p, dir), 'utf8');
const strip = (src) => src.replace(/^import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm, '').replace(/^export\s+(?=(const|function|let|class)\b)/gm, '');
const js = ['src/minimal.js', 'src/bots.js', 'src/ui.js'].map(f => `// ---- ${f}\n` + strip(read(f))).join('\n');
if (/^\s*(import|export)\b/m.test(js)) throw new Error('build: a module line was left in');
const html = read('src/page.html').replace('/*STYLE*/', () => read('src/style.css')).replace('/*SCRIPT*/', () => '(function () {\n"use strict";\n' + js + '\n})();');
writeFileSync(new URL('index.html', dir), html);
const head = html.slice(html.indexOf('<title>'), html.indexOf('</head>'));
const body = html.slice(html.indexOf('>', html.indexOf('<body')) + 1, html.indexOf('</body>'));
writeFileSync(new URL('artifact.html', dir), head + body);
console.log('index.html written, ' + html.length + ' bytes');
