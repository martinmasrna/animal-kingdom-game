// node build.mjs: inlines src/ into one self-contained index.html (imports and exports stripped, files concatenated).
import { readFileSync, writeFileSync } from 'node:fs';
const dir = new URL('./src/', import.meta.url);
const read = (f) => readFileSync(new URL(f, dir), 'utf8');
const strip = (code) => code
  .replace(/^import[\s\S]*?from\s+['"][^'"]+['"];\s*$/gm, '')
    .replace(/^export\s+(?=(const|let|function|class)\b)/gm, '');
const js0 = ['engine.js', 'bot.js', 'ui.js'].map((f) => `// ---- ${f}\n` + strip(read(f))).join('\n');
if (/^export\s/m.test(js0) || /^import\s/m.test(js0)) throw new Error('an import or export the build cannot strip');
const js = js0;
const html = read('page.html').replace('/*STYLE*/', () => read('style.css')).replace('/*SCRIPT*/', () => '"use strict";\n(() => {\n' + js + '\n})();');
writeFileSync(new URL('./index.html', import.meta.url), html);
console.log('index.html', html.length, 'bytes');

// artifact.html: the same page without the document wrapper, for a publisher that supplies its own.
const styleBlock = html.match(/<style>[\s\S]*?<\/style>/)[0];
const bodyInner = html.match(/<body>([\s\S]*)<\/body>/)[1].trim();
const artifact = `<title>Grid Duel</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n${styleBlock}\n${bodyInner}\n`;
if (/<\/?(html|head|body)\b|<!doctype/i.test(artifact.replace(/<script>[\s\S]*<\/script>/, ''))) throw new Error('artifact.html still has a document tag');
if (/100d?vh/.test(styleBlock)) throw new Error('viewport-height units in the CSS');
writeFileSync(new URL('./artifact.html', import.meta.url), artifact);
console.log('artifact.html', artifact.length, 'bytes');
