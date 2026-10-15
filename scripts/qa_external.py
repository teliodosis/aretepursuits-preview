"""External QA: (1) every URL in the live site's sitemaps resolves on the new site; (2) every external link on the new site still works."""
import json, os, re, sys, subprocess, urllib.request, urllib.error, concurrent.futures as cf
NEW = sys.argv[1].rstrip('/'); SITE_DIR = sys.argv[2]
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'}
os.makedirs('reports', exist_ok=True)
def get(url, method='GET'):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA, method=method), timeout=25)
        return r.status, r.geturl(), r.read() if method == 'GET' else b''
    except urllib.error.HTTPError as e: return e.code, url, b''
    except Exception as e: return 0, url, str(e).encode()
# 1) live sitemap URLs -> new site
live = set()
def sitemap(u):
    s, _, b = get(u); txt = b.decode('utf-8', 'ignore')
    for loc in re.findall(r'<loc>([^<]+)</loc>', txt):
        if loc.endswith('.xml'): sitemap(loc)
        else: live.add(loc)
sitemap('https://aretepursuits.com/wp-sitemap.xml')
out = [f'live sitemap URLs: {len(live)}']
def chk(u):
    path = re.sub(r'^https?://[^/]+', '', u) or '/'
    s, final, _ = get(NEW + path)
    return u, path, s, final
bad = []
with cf.ThreadPoolExecutor(8) as ex:
    for u, path, s, final in ex.map(chk, sorted(live)):
        if s != 200: bad.append(f'{s} {path} -> {final}')
out += ['LIVE URL NOT FOUND ON NEW SITE: ' + b for b in bad] or ['all live sitemap URLs resolve on the new site']
open('reports/qa-live-urls.txt', 'w').write('\n'.join(out) + '\n')
# 2) external links on the new site
links = {}
for d, _, fs in os.walk(SITE_DIR):
    for f in fs:
        if not f.endswith('.html'): continue
        p = os.path.join(d, f); rel = '/' + os.path.relpath(p, SITE_DIR).replace('index.html', '')
        for u in re.findall(r'href="(https?://[^"#]+)', open(p, encoding='utf-8', errors='ignore').read()):
            u = u.replace('&amp;', '&')
            if 'aretepursuits.com' in u and '/schedule/' not in u: continue
            links.setdefault(u, set()).add(rel)
def ext(u):
    s, final, body = get(u, 'HEAD')
    if s in (0, 403, 405, 429, 400) or s >= 500: s, final, body = get(u)
    return u, s, final
rows = []
with cf.ThreadPoolExecutor(12) as ex:
    for u, s, final in ex.map(ext, sorted(links)):
        if s == 0 or s >= 400:
            pages = sorted(links[u]); rows.append(f'{s}\t{u}\t{len(pages)} page(s): {", ".join(pages[:4])}')
open('reports/qa-external-links.txt', 'w').write(f'external links checked: {len(links)}; problems: {len(rows)}\n' + '\n'.join(sorted(rows)) + '\n')
print(out[0], len(bad), len(links), len(rows))
