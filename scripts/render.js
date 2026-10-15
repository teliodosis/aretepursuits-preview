// Render every route of the single-page source (src/index.src.html) to static HTML fragments.
// Input: build/data.json from build_site.py. Output: build/rendered.json {key: html}.
const fs = require('fs');
const root = __dirname + '/..';
const src = fs.readFileSync(root + '/src/index.src.html', 'utf8');
let js = src.slice(src.indexOf('<script>') + 8, src.lastIndexOf('</script>'));
js = js.replace('/*__DATA__*/', fs.readFileSync(root + '/src/data.js', 'utf8'));
// Drop the browser-only tail (router, menus, listeners) — keep definitions only.
js = js.slice(0, js.indexOf('/* router */'));
const D = JSON.parse(fs.readFileSync(root + '/build/data.json', 'utf8'));
global.document = { createElement: () => ({}), getElementById: () => null, querySelectorAll: () => [] };
global.localStorage = { getItem: () => null, setItem() {} };
const out = {};
const run = new Function('D', 'out', js + `
POSTS.length = 0; D.posts.forEach(p => POSTS.push(p));
IMG.clear(); D.img.forEach(s => IMG.add(s));
Object.keys(EX).forEach(k => delete EX[k]); Object.assign(EX, D.ex);
Object.keys(BODY).forEach(k => delete BODY[k]); Object.assign(BODY, D.body);
CATS.length = 0; (() => { const m = {}; POSTS.forEach(p => p.c.forEach(c => m[c] = (m[c] || 0) + 1)); Object.entries(m).sort((a, b) => b[1] - a[1]).forEach(e => CATS.push(e)); })();
for (const k of Object.keys(pages)) { if (k === 'writing') continue; out['page:' + k] = pages[k](); }
cat = null; q = ''; out['page:writing'] = pages.writing();
for (const [c] of CATS) { cat = c; q = ''; out['cat:' + c] = pages.writing(); }
cat = null;
for (const p of POSTS) out['post:' + p.s] = post(p.s);
out['__threshold'] = threshold();
out['__phead404'] = phead('Not found', 'This page has <em>wandered</em> off.', 'The page you were looking for has moved or no longer exists.');
out['__legalhead:Privacy Policy'] = phead('Legal', 'Privacy Policy', '');
out['__legalhead:Terms and Conditions'] = phead('Legal', 'Terms and Conditions', '');
`);
run(D, out);
fs.writeFileSync(root + '/build/rendered.json', JSON.stringify(out));
console.log('rendered', Object.keys(out).length);
