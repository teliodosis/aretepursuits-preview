"""Download every upload referenced by posts/pages, resize for the web, write media/ + content/media-map.json."""
import json, os, re, subprocess, time, urllib.request, urllib.parse, io
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
UA = {'User-Agent': 'Mozilla/5.0 (aretepursuits migration)'}
P = json.load(open('content/posts.json')); G = json.load(open('content/pages.json'))
RX = re.compile(r'https?://(?:www\.)?aretepursuits\.com/wp-content/uploads/[^"\'\s)>]+')
refs = set()
for p in P + G:
    for u in RX.findall(p['content']['rendered']): refs.add(u.split('?')[0])
    if p.get('featured'): refs.add(p['featured']['url'])
def original(u):
    return re.sub(r'-(\d+)x(\d+)(\.[A-Za-z]+)$', r'\3', u)
def fetch(u):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u, safe=':/%?=&'), headers=UA), timeout=120) as r: return r.read()
        except Exception as e:
            if getattr(e, 'code', None) == 404: return None
            time.sleep(2 * (a + 1))
    return None
mp = {}
def rel(u): return u.split('/wp-content/uploads/', 1)[1]
def handle(orig):
    path0 = 'media/wp-content/uploads/' + rel(orig)
    for cand in (path0, path0.rsplit('.', 1)[0] + '.jpg' if path0.lower().endswith('.png') else None, path0[:-4] + '.mp4' if path0.endswith('.mov') else None):
        if cand and os.path.exists(cand):
            try:
                im = Image.open(cand); return orig, {'path': '/' + cand[len('media/'):], 'w': im.width, 'h': im.height}
            except Exception:
                return orig, {'path': '/' + cand[len('media/'):]}
    data = fetch(orig); src = orig
    if data is None:
        cands = [r for r in refs if original(r) == orig]
        for c in cands:
            data = fetch(c)
            if data: src = c; break
    if data is None: return orig, None
    path = 'media/wp-content/uploads/' + rel(orig)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = orig.rsplit('.', 1)[-1].lower()
    if ext in ('jpg', 'jpeg', 'jpe', 'png', 'webp', 'gif'):
        try:
            im = Image.open(io.BytesIO(data)); im = ImageOps.exif_transpose(im)
            if ext != 'gif' and im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
            if ext in ('jpg', 'jpeg', 'jpe'):
                im.convert('RGB').save(path, 'JPEG', quality=82, optimize=True, progressive=True)
            elif ext == 'png':
                if len(data) > 600_000 and im.mode in ('RGB', 'P', 'L') :
                    path = path[:-4] + '.jpg'; im.convert('RGB').save(path, 'JPEG', quality=84, optimize=True, progressive=True)
                else:
                    im.save(path, 'PNG', optimize=True)
            elif ext == 'webp':
                im.save(path, 'WEBP', quality=82)
            else:
                open(path, 'wb').write(data)
            return orig, {'path': '/' + path[len('media/'):], 'w': im.width, 'h': im.height}
        except Exception as e:
            print('image fail', orig, e); open(path, 'wb').write(data)
            return orig, {'path': '/' + path[len('media/'):]}
    if ext == 'mov':
        tmp = '/tmp/' + os.path.basename(orig); open(tmp, 'wb').write(data)
        path = path[:-4] + '.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-vf', 'scale=-2:min(720\\,ih)', '-c:v', 'libx264', '-crf', '28', '-preset', 'slow', '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', path], check=True)
        return orig, {'path': '/' + path[len('media/'):], 'bytes': os.path.getsize(path)}
    open(path, 'wb').write(data)
    return orig, {'path': '/' + path[len('media/'):]}
origs = sorted({original(r) for r in refs})
print('unique originals', len(origs))
with ThreadPoolExecutor(8) as ex:
    for o, res in ex.map(handle, origs):
        if res: mp[o] = res
        else: print('MISSING', o)
refmap = {r: mp.get(original(r)) for r in refs}
# social card (1200x630) and thumbnail (720w) per post from featured image
os.makedirs('media/og', exist_ok=True); os.makedirs('media/thumbs', exist_ok=True)
for p in P:
    f = p.get('featured'); m = f and refmap.get(f['url'])
    if not m or 'w' not in m: continue
    try:
        im = Image.open('media' + m['path']).convert('RGB')
        ImageOps.fit(im, (1200, 630), Image.LANCZOS).save(f"media/og/{p['slug']}.jpg", 'JPEG', quality=82, optimize=True)
        t = im.copy(); t.thumbnail((720, 720)); t.save(f"media/thumbs/{p['slug']}.jpg", 'JPEG', quality=80, optimize=True, progressive=True)
    except Exception as e: print('og fail', p['slug'], e)
json.dump(refmap, open('content/media-map.json', 'w'), indent=1)
print('mapped', sum(1 for v in refmap.values() if v), 'of', len(refmap))
