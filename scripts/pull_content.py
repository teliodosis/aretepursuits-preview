"""Pull all public content from the WordPress site into content/*.json (runs on GitHub Actions)."""
import json, os, time, urllib.request, urllib.parse
BASE = 'https://aretepursuits.com/wp-json/wp/v2/'
UA = {'User-Agent': 'Mozilla/5.0 (aretepursuits migration)'}
def get(path, params):
    url = BASE + path + '?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r), int(r.headers.get('X-WP-TotalPages', '1'))
        except Exception as e:
            print('retry', url, e); time.sleep(3 * (attempt + 1))
    raise SystemExit('failed ' + url)
def all_of(path, extra=None):
    out, page = [], 1
    while True:
        data, pages = get(path, {'per_page': 100, 'page': page, **(extra or {})})
        out += data
        if page >= pages: return out
        page += 1
os.makedirs('content', exist_ok=True)
posts = all_of('posts', {'status': 'publish', '_embed': 'wp:featuredmedia'})
for p in posts:
    emb = p.pop('_embedded', {}) or {}
    fm = (emb.get('wp:featuredmedia') or [{}])[0] or {}
    p['featured'] = {'url': fm.get('source_url'), 'alt': fm.get('alt_text'), 'sizes': {k: v.get('source_url') for k, v in ((fm.get('media_details') or {}).get('sizes') or {}).items()}} if fm.get('source_url') else None
    p.pop('_links', None)
pages = all_of('pages', {'status': 'publish'})
for p in pages: p.pop('_links', None)
cats = all_of('categories')
for c in cats: c.pop('_links', None)
media = all_of('media')
media = [{'id': m['id'], 'date': m['date'], 'mime': m.get('mime_type'), 'url': m.get('source_url'), 'alt': m.get('alt_text'),
          'w': (m.get('media_details') or {}).get('width'), 'h': (m.get('media_details') or {}).get('height'),
          'bytes': (m.get('media_details') or {}).get('filesize'), 'post': m.get('post')} for m in media]
for name, data in [('posts', posts), ('pages', pages), ('categories', cats), ('media', media)]:
    json.dump(data, open(f'content/{name}.json', 'w'), ensure_ascii=False, indent=1)
    print(name, len(data))
