"""Build the static aretepursuits.com site.

Inputs:  src/index.src.html + src/data.js (design and page copy), content/*.json (WordPress export),
         media/ (resized uploads, og cards, thumbnails), baseline/img (site images and logos).
Output:  the directory given as argv[1] (default dist/), ready for Cloudflare Pages.
"""
import json, os, re, shutil, subprocess, sys, html as H
from datetime import datetime, timezone
from email.utils import format_datetime
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'dist')
SITE = 'https://aretepursuits.com'
J = lambda p: json.load(open(os.path.join(ROOT, p), encoding='utf-8'))
from zoneinfo import ZoneInfo
NOW = datetime.now(ZoneInfo('America/New_York')).replace(tzinfo=None)
legacy = J('content/posts.json')
NEW = []  # posts published after the move off WordPress: content/new-posts/<slug>.json
nd = os.path.join(ROOT, 'content/new-posts')
for f in sorted(os.listdir(nd)) if os.path.isdir(nd) else []:
    if f.endswith('.json'): NEW.append(json.load(open(os.path.join(nd, f), encoding='utf-8')))
for n in NEW:  # shape them like WordPress posts so one code path handles both
    n['_new'] = True; n.setdefault('categories', [])
posts = [p for p in legacy if p['slug'] not in {n['slug'] for n in NEW}] + NEW
posts = [p for p in posts if datetime.fromisoformat(p['date'][:19]) <= NOW]   # scheduled posts wait for their time
posts = sorted(posts, key=lambda p: p['date'], reverse=True)
pages_wp = {p['slug']: p for p in J('content/pages.json')}
cats_wp = {c['id']: (H.unescape(c['name']), c['slug']) for c in J('content/categories.json')}
mmap = J('content/media-map.json')
TITLE_OVERRIDES = {k: v for k, v in J('content/title-overrides.json').items() if not k.startswith('_')} if os.path.exists(os.path.join(ROOT, 'content/title-overrides.json')) else {}
LINK_OVERRIDES = {k: v for k, v in J('content/link-overrides.json').items() if not k.startswith('_')} if os.path.exists(os.path.join(ROOT, 'content/link-overrides.json')) else {}
AUDIO = J('content/audio.json') if os.path.exists(os.path.join(ROOT, 'content/audio.json')) else {}
SLUGS = {p['slug'] for p in posts}
slugify = lambda s: re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s.lower()))
CAT_RENAME = {'Walkabout': 'Wanderment'}  # Josh no longer uses 'walkabout'; old URL redirects
CAT_SLUG = {name: slug for name, slug in cats_wp.values()}            # display name -> WP slug
for old, new in CAT_RENAME.items(): CAT_SLUG[new] = slugify(new)
CAT_BY_JS = {slugify(name): slug for name, slug in cats_wp.values()}  # JS slugify(name) -> WP slug
for old, new in CAT_RENAME.items(): CAT_BY_JS[slugify(new)] = slugify(new)


ROUTES = {'home': '/', 'executive-coaching': '/services/executive-coaching/', 'organizations': '/services/organizations/',
          'consciousness-coaching': '/services/consciousness-coaching/', 'life-coaching': '/services/life-coaching/',
          'meditation': '/meditation/', 'writing': '/blog/', 'blog': '/blog/', 'about': '/about/', 'resources': '/resources/',
          'contact': '/contact/', 'privacy-policy': '/privacy-policy/'}

def original(u): return re.sub(r'-(\d+)x(\d+)(\.[A-Za-z]+)$', r'\3', u)
def media_for(u):
    u = u.split('?')[0].replace('://www.', '://')
    return mmap.get(u) or mmap.get(original(u))

SIG = re.compile(r"^\s*(I am an executive|I’m an executive|I'm an executive|If you would like to learn more, schedule|Want to comment\?|You can subscribe and comment)", re.I)
def clean(raw):
    soup = BeautifulSoup(raw, 'html.parser')
    for t in soup(['script', 'style', 'form', 'noscript']): t.decompose()
    # Drop the closing signature lines (they appear on every post) but keep anything after them, like footnotes.
    kids = [k for k in soup.children if getattr(k, 'name', None)]
    for i, k in enumerate(kids):
        if k.name in ('p', 'div') and SIG.match(k.get_text()):
            j = i - 1
            while j >= 0 and (kids[j].name == 'hr' or not kids[j].get_text(strip=True)) and not kids[j].find(['img', 'video', 'iframe']):
                kids[j].decompose(); j -= 1
            k.decompose()
    while True:
        kids = [k for k in soup.children if getattr(k, 'name', None)]
        if not kids: break
        last = kids[-1]
        if last.name == 'hr' or (not last.get_text(strip=True).strip('-–—_* ') and not last.find(['img', 'video', 'iframe'])): last.decompose()
        else: break
    for a in soup.find_all('a', href=True):
        h = a['href'].strip()
        if h in LINK_OVERRIDES:
            if LINK_OVERRIDES[h] is None: a.unwrap(); continue   # dead link with no replacement: keep the words
            h = LINK_OVERRIDES[h]
        a['href'] = h
        if 'practice.do' in h:  # Practice (coaching platform) shut down
            if '/josh-dietrich/book/' in h: a['href'] = '/schedule/blog'
            elif re.search(r'practice\.do/(me/)?josh-dietrich/?$', h): a['href'] = '/contact/'
            else: a.unwrap()
            continue
        m = re.match(r'^https?://(?:www\.)?aretepursuits\.com(/[^#?]*)?([?#].*)?$', h)
        if m:
            path = m.group(1) or '/'
            if '/wp-content/uploads/' in path:
                mm = media_for('https://aretepursuits.com' + path)
                a['href'] = mm['path'] if mm else path
            else:
                s = re.match(r'^/(?:blog/(?:f/)?)?([a-z0-9-]+)/?$', path)
                LEG = {'/services/leadership-workshops/': '/services/organizations/', '/services/disc-facilitation/': '/services/organizations/', '/services/360-feedback/': '/services/organizations/'}
                path = LEG.get(path if path.endswith('/') else path + '/', path)
                a['href'] = f'/{s.group(1)}/' if s and s.group(1) in SLUGS else path + (m.group(2) or '')
            for k in ('target', 'rel'): a.attrs.pop(k, None)
        elif h.startswith('http'):
            a['target'] = '_blank'; a['rel'] = 'noopener'
    for im in soup.find_all('img'):
        mm = media_for(im.get('src', ''))
        if mm:
            im['src'] = mm['path']
            if mm.get('w'): im['width'], im['height'] = str(mm['w']), str(mm['h'])
        for k in ('srcset', 'sizes', 'style', 'class', 'decoding', 'fetchpriority'): im.attrs.pop(k, None)
        im['loading'] = 'lazy'; im['alt'] = im.get('alt', '')
    for v in soup.find_all(['video', 'source']):
        if v.get('src'):
            mm = media_for(v['src'])
            if mm: v['src'] = mm['path']
    for f in soup.find_all('iframe', src=True):  # privacy-enhanced YouTube embeds (no cookies until played)
        f['src'] = f['src'].replace('://www.youtube.com/embed/', '://www.youtube-nocookie.com/embed/').replace('://youtube.com/embed/', '://www.youtube-nocookie.com/embed/')
    for v in soup.find_all('video'): v['controls'] = ''; v['playsinline'] = ''; v['preload'] = 'metadata'
    for t in soup.find_all(True):
        for k in ('style', 'class', 'id'):
            if t.name != 'iframe': t.attrs.pop(k, None)
    return str(soup)

def text(raw, n=None):
    t = re.sub(r'\s+', ' ', BeautifulSoup(raw, 'html.parser').get_text(' ')).strip()
    t = re.sub(r'\s*(\[…\]|\[&hellip;\]|…|\[\.\.\.\])\s*$', '', H.unescape(t)).strip()
    if n and len(t) > n: t = t[:t.rfind(' ', 0, n)].rstrip(',;:') + '…'
    return t

def ensure_cards(slug, featured):
    """Social card (1200x630) and thumbnail (720w) for a new post's featured image (path under media/)."""
    from PIL import Image, ImageOps
    srcp = os.path.join(ROOT, 'media', featured.lstrip('/'))
    og, th = os.path.join(ROOT, 'media/og', slug + '.jpg'), os.path.join(ROOT, 'media/thumbs', slug + '.jpg')
    if os.path.exists(og) and os.path.exists(th): return
    im = Image.open(srcp).convert('RGB')
    ImageOps.fit(im, (1200, 630), Image.LANCZOS).save(og, 'JPEG', quality=82, optimize=True)
    t = im.copy(); t.thumbnail((720, 720)); t.save(th, 'JPEG', quality=80, optimize=True, progressive=True)

# ---------- data for the renderer ----------
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
P, EX, BODY, IMG, FEAT = [], {}, {}, [], {}
for p in posts:
    s = p['slug']
    if p.get('_new'):
        P.append({'d': p['date'][:10], 's': s, 't': p['title'], 'c': p['categories']})
        EX[s] = p.get('excerpt', ''); BODY[s] = p['body']
        if p.get('featured'):
            ensure_cards(s, p['featured']); IMG.append(s); FEAT[s] = p['featured']
        continue
    names = [cats_wp[c][0] for c in p['categories'] if c in cats_wp and cats_wp[c][0] != 'Uncategorized']
    names = [CAT_RENAME.get(n, n) for n in names]
    P.append({'d': p['date'][:10], 's': s, 't': TITLE_OVERRIDES.get(s, H.unescape(p['title']['rendered'])), 'c': names})
    EX[s] = text(p['excerpt']['rendered'], 240)
    BODY[s] = clean(p['content']['rendered'])
    f = p.get('featured'); mm = f and media_for(f['url'])
    if mm and os.path.exists(os.path.join(ROOT, 'media/thumbs', s + '.jpg')):
        IMG.append(s); FEAT[s] = mm['path']
json.dump({'posts': P, 'ex': EX, 'body': BODY, 'img': IMG}, open(os.path.join(ROOT, 'build/data.json'), 'w'))
subprocess.run(['node', os.path.join(ROOT, 'scripts/render.js')], check=True)
R = json.load(open(os.path.join(ROOT, 'build/rendered.json')))

for p in P:
    for c in p['c']:
        if c not in CAT_SLUG: CAT_SLUG[c] = slugify(c); CAT_BY_JS[slugify(c)] = slugify(c)

# ---------- shell pieces from the source ----------
src = open(os.path.join(ROOT, 'src/index.src.html'), encoding='utf-8').read()
fonts = src[src.index('<link rel="preconnect"'):src.index('<style>')]
css = src[src.index('<style>') + 7:src.index('</style>')]
header = src[src.index('<header class="site">'):src.index('<main id="app">')]
footer = src[src.index('<footer class="site">'):src.index('</footer>') + 9]
BASE_IMG = set(os.listdir(os.path.join(ROOT, 'baseline/img')))

def links(h):
    def hashlink(m):
        r = H.unescape(m.group(1))
        if r.startswith('post-'): return f'href="/{r[5:]}/"'
        if r.startswith('writing~'):
            c = CAT_BY_JS.get(r.split('~', 1)[1]); return f'href="/category/{c}/"' if c else 'href="/blog/"'
        return f'href="{ROUTES.get(r, "/")}"'
    h = re.sub(r'href="#([^"]*)"', hashlink, h)
    def imgsrc(m):
        f = m.group(1)
        if f in BASE_IMG: return f'src="/img/{f}"'
        s = re.match(r'p-(.+)\.jpg$', f)
        if s: return f'src="/thumbs/{s.group(1)}.jpg"'
        return f'src="/img/{f}"'
    return re.sub(r'src="img/([^"]+)"', imgsrc, h)

def chips(h, current=None):
    def rep(m):
        name = H.unescape(m.group(1)); rest = m.group(2)
        if not name: return f'<a class="chip" href="/blog/"{" aria-current=\"page\"" if not current else ""}>{rest}</a>'
        slug = CAT_SLUG.get(name)
        cur = ' aria-current="page"' if name == current else ''
        return f'<a class="chip" href="/category/{slug}/"{cur}>{rest}</a>'
    return re.sub(r'<button class="chip" data-cat="([^"]*)" aria-pressed="[a-z]+">(.*?)</button>', rep, h, flags=re.S)

DEFAULT_OG = '/og/default.jpg'
def page(path, title, desc, body, kind='page', og=DEFAULT_OG, ogtype='website', extra_head=''):
    url = SITE + path
    head = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{H.escape(title)}</title>
<meta name="description" content="{H.escape(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:site_name" content="Arete Pursuits">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{H.escape(title)}">
<meta property="og:description" content="{H.escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}{og}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Arete Pursuits" href="/feed.xml">
{extra_head}{fonts}<style>{css}
.article iframe{{width:100%;height:auto;aspect-ratio:16/9;border:0;border-radius:var(--r)}}
.article video{{width:100%;height:auto;border-radius:var(--r)}}
[hidden]{{display:none!important}}
body{{margin:0}}img{{max-width:100%;height:auto}}
</style>
</head>
<body data-kind="{kind}">
'''
    return head + links(header) + f'<main id="app"><div class="enter">{links(body)}</div></main>\n' + links(footer) + '\n<script src="/site.js" defer></script>\n</body>\n</html>\n'

def write(path, content):
    fp = os.path.join(OUT, path.lstrip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.lstrip('/'))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf-8').write(content)

if os.path.exists(OUT):
    for n in os.listdir(OUT):
        if n == '.git': continue
        fp = os.path.join(OUT, n); shutil.rmtree(fp) if os.path.isdir(fp) else os.remove(fp)
os.makedirs(OUT, exist_ok=True)

META = {
 'home': ('Arete Pursuits | Executive, Life & Consciousness Coaching | Josh Dietrich, PCC',
          'Executive coaching for leaders who want to grow faster than the job alone will teach them, and life and consciousness coaching for anyone ready to meet themselves more fully.'),
 'executive-coaching': ('Executive Coaching | Arete Pursuits', 'A six-month executive coaching engagement with Everything DiSC and the Leadership Circle Profile 360, from a coach with thirty years in technology leadership.'),
 'organizations': ('Leadership Workshops, DiSC & 360s for Organizations | Arete Pursuits', 'Leadership workshops, Everything DiSC team sessions, and Leadership Circle 360s for HR, talent, and executive teams.'),
 'consciousness-coaching': ('Consciousness Coaching | Arete Pursuits', 'A focused kind of life coaching for people drawn to awareness, presence, and meaning, informed by nondual meditation, ontological coaching, and neuroscience.'),
 'life-coaching': ('Life Coaching | Arete Pursuits', 'A confidential thought partner for whatever life brings: purpose, transitions, productivity, health habits, and work/life balance.'),
 'meditation': ('Meditation | Arete Pursuits', 'Nondual meditation explained in plain language, free guided meditations, and an invitation to explore meditating together.'),
 'about': ('About Josh Dietrich | Arete Pursuits', 'Thirty years in technology leadership, more than 2,000 coaching hours, and training in ontological coaching, neuroscience, and nondual meditation.'),
 'resources': ('Library: Books, Programs & Meditations | Arete Pursuits', 'Books, programs, and meditations Josh recommends most often to clients, loosely sorted to help you find your way in.'),
 'contact': ('Begin a Conversation | Arete Pursuits', 'Schedule a free 25-minute conversation about executive, life, or consciousness coaching, or get in touch by email or phone.'),
 'writing': ('Writing | Arete Pursuits', 'Writing since 2021 on leadership, neuroscience, consciousness, and life on the road.'),
}
PAGE_IDS = {57: '/services/life-coaching/', 62: '/services/organizations/', 80: '/contact/', 86: '/services/executive-coaching/', 87: '/resources/', 88: '/about/', 89: '/blog/', 90: '/services/organizations/', 91: '/services/organizations/'}
LEGACY_ROUTER = ('<script>(function(){var q=new URLSearchParams(location.search),m=' + json.dumps({**{str(k): v for k, v in PAGE_IDS.items()}, **{'p' + str(p['id']): '/' + p['slug'] + '/' for p in posts if 'id' in p}}, separators=(',', ':'))
                 + ',t=q.get("page_id")?m[q.get("page_id")]:q.get("p")?m["p"+q.get("p")]:q.get("s")?"/blog/?q="+encodeURIComponent(q.get("s")):null;if(t)location.replace(t);})();</script>\n')
LD_HOME = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "ProfessionalService", "name": "Arete Pursuits", "url": SITE, "email": "josh@aretepursuits.com", "telephone": "+1-703-431-8025", "founder": {"@type": "Person", "name": "Josh Dietrich", "jobTitle": "Executive, life, and consciousness coach"}, "sameAs": ["https://www.linkedin.com/in/joshuadietrich/", "https://substack.com/@teliodosis"]}) + '</script>\n'

for key, (title, desc) in META.items():
    body = R['page:' + key]
    if key == 'writing':
        body = chips(body)
        i = body.find('<a class="feature"')
        if i > -1:
            j = body.find('</section>', i) + len('</section>')
            body = body[:i] + '<div id="toptier">' + body[i:j] + '</div>' + body[j:]
        body = body.replace(f'src="img/p-{P[0]["s"]}.jpg"', f'src="{FEAT.get(P[0]["s"], "")}"')
    write(ROUTES[key], page(ROUTES[key], title, desc, body, extra_head=(LEGACY_ROUTER + LD_HOME) if key == 'home' else ''))

# categories
for name, slug in sorted(CAT_SLUG.items()):
    k = 'cat:' + name
    if k not in R: continue
    n = sum(1 for p in P if name in p['c'])
    write(f'/category/{slug}/', page(f'/category/{slug}/', f'{name} | Writing | Arete Pursuits', f'{n} posts on {name.lower()} from Josh Dietrich’s writing on leadership, consciousness, and life on the road.', chips(R[k], name)))

# posts
for p in P:
    s = p['s']; body = R['post:' + s]
    if s in FEAT: body = body.replace(f'src="img/p-{s}.jpg"', f'src="{FEAT[s]}"', 1)
    if s in AUDIO:
        a = AUDIO[s]; mins = max(1, round(a['seconds'] / 60))
        player = (f'<div class="listen" data-listen data-src="{a["src"]}" data-dur="{a["seconds"]}" data-title="{H.escape(p["t"])}">'
                  '<button class="pp" type="button" aria-label="Play narration"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg></button>'
                  f'<div class="mid"><div class="lab">Listen · {mins} min · narrated by Josh</div><div class="row"><input type="range" min="0" max="{a["seconds"]}" value="0" step="1" aria-label="Seek"><span class="t">0:00 / {a["seconds"]//60}:{a["seconds"]%60:02d}</span></div></div>'
                  '<button class="sp" type="button" aria-label="Playback speed">1×</button></div>')
        body = body.replace('<div class="post-hero"', player + '\n <div class="post-hero"', 1)
    og = f'/og/{s}.jpg' if s in IMG else DEFAULT_OG
    ld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BlogPosting", "headline": p['t'], "datePublished": p['d'], "author": {"@type": "Person", "name": "Josh Dietrich"}, "image": SITE + og, "url": f"{SITE}/{s}/", **({"audio": {"@type": "AudioObject", "contentUrl": SITE + AUDIO[s]["src"], "encodingFormat": "audio/mpeg"}} if s in AUDIO else {})}) + '</script>\n'
    extra = ld + f'<meta property="article:published_time" content="{p["d"]}">\n'
    write(f'/{s}/', page(f'/{s}/', f'{p["t"]} | Arete Pursuits', EX[s] or p['t'], body, kind='post', og=og, ogtype='article', extra_head=extra))

# legal
for slug, name in [('privacy-policy', 'Privacy Policy')]:  # Terms page dropped Oct 15 (old PDF conflicted with the MSA)
    own = os.path.join(ROOT, f'content/{slug}.html')  # site-owned text (approved by Josh) replaces the WordPress page
    content = open(own, encoding='utf-8').read() if os.path.exists(own) else clean(pages_wp[slug]['content']['rendered'])
    if slug == 'terms-and-conditions':
        pdf = re.search(r'href="(/wp-content/uploads/[^"]+\.pdf)"', content)
        content = f'<p>The Arete Pursuits Terms and Conditions are available as a PDF.</p><p><a class="btn btn-line" href="{pdf.group(1)}">Read the Terms and Conditions (PDF)</a></p>' if pdf else content
    body = R['__legalhead:' + name] + f'<div class="wrap" style="padding-bottom:80px"><article class="article">{content}</article></div>'
    write(f'/{slug}/', page(f'/{slug}/', f'{name} | Arete Pursuits', (f'How aretepursuits.com handles your information: no cookies, cookieless analytics, and what happens when you contact Josh.' if slug == 'privacy-policy' else f'{name} for aretepursuits.com.'), body))

# 404
body404 = R['__phead404'] + '<div class="wrap" style="padding-block:40px 90px"><p>Try the <a class="tl-link" href="/">home page</a>, browse <a class="tl-link" href="/blog/">all writing</a>, or <a class="tl-link" href="/contact/">get in touch</a>.</p></div>'
open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8').write(page('/404', 'Page not found | Arete Pursuits', 'This page has moved or no longer exists.', body404))

# ---------- assets ----------
shutil.copytree(os.path.join(ROOT, 'baseline/img'), os.path.join(OUT, 'img'))
shutil.copytree(os.path.join(ROOT, 'media/wp-content'), os.path.join(OUT, 'wp-content'))
shutil.copytree(os.path.join(ROOT, 'media/og'), os.path.join(OUT, 'og'), dirs_exist_ok=True)
shutil.copytree(os.path.join(ROOT, 'media/thumbs'), os.path.join(OUT, 'thumbs'))
if os.path.isdir(os.path.join(ROOT, 'media/audio')): shutil.copytree(os.path.join(ROOT, 'media/audio'), os.path.join(OUT, 'audio'))
shutil.copy(os.path.join(ROOT, 'scripts/site.js'), os.path.join(OUT, 'site.js'))
from PIL import Image, ImageOps
ImageOps.fit(Image.open(os.path.join(ROOT, 'baseline/img/p-meditations-on-ogha-pooge.jpg')).convert('RGB'), (1200, 630), Image.LANCZOS).save(os.path.join(OUT, 'og/default.jpg'), 'JPEG', quality=84)
open(os.path.join(OUT, 'favicon.svg'), 'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0F1614"/><text x="32" y="45" font-family="Georgia,serif" font-size="40" font-style="italic" text-anchor="middle" fill="#E49A5B">A</text></svg>')

# ---------- feed, sitemap, robots, headers, redirects ----------
def rfc822(d): return format_datetime(datetime.fromisoformat(d).replace(hour=12, tzinfo=timezone.utc))
items = ''.join(f'''<item><title>{H.escape(p["t"])}</title><link>{SITE}/{p["s"]}/</link><guid isPermaLink="true">{SITE}/{p["s"]}/</guid><pubDate>{rfc822(p["d"])}</pubDate>{"".join(f"<category>{H.escape(c)}</category>" for c in p["c"])}<description>{H.escape(EX[p["s"]])}</description>{f'<enclosure url="{SITE}{AUDIO[p["s"]]["src"]}" length="{AUDIO[p["s"]]["bytes"]}" type="audio/mpeg"/>' if p["s"] in AUDIO else ""}<content:encoded><![CDATA[{BODY[p["s"]].replace("]]>", "]]&gt;").replace('src="/', f'src="{SITE}/').replace('href="/', f'href="{SITE}/')}]]></content:encoded></item>''' for p in P[:30])
open(os.path.join(OUT, 'feed.xml'), 'w', encoding='utf-8').write(f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Arete Pursuits</title><link>{SITE}/</link><atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/><description>Writing by Josh Dietrich on leadership, consciousness, and life on the road.</description><language>en-us</language><lastBuildDate>{rfc822(P[0]["d"])}</lastBuildDate>{items}</channel></rss>\n')
urls = [ROUTES[k] for k in META] + ['/privacy-policy/'] + [f'/category/{s}/' for n, s in CAT_SLUG.items() if 'cat:' + n in R]
sm = ''.join(f'<url><loc>{SITE}{u}</loc></url>' for u in dict.fromkeys(urls)) + ''.join(f'<url><loc>{SITE}/{p["s"]}/</loc><lastmod>{p["d"]}</lastmod></url>' for p in P)
open(os.path.join(OUT, 'sitemap.xml'), 'w').write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
open(os.path.join(OUT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
open(os.path.join(OUT, '_headers'), 'w').write('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/wp-content/*\n  Cache-Control: public, max-age=31536000, immutable\n/thumbs/*\n  Cache-Control: public, max-age=604800\n/og/*\n  Cache-Control: public, max-age=604800\n')
rules = []
for line in open(os.path.join(ROOT, 'src/_redirects')):
    rules.append(line.rstrip('\n'))
    parts = line.split()
    if parts and not line.startswith('#') and not parts[0].endswith('/') and '*' not in parts[0] and '.' not in parts[0].rsplit('/', 1)[-1]:
        rules.append(line.replace(parts[0], parts[0] + '/', 1).rstrip('\n'))  # same rule with a trailing slash
open(os.path.join(OUT, '_redirects'), 'w').write('\n'.join(rules) + '\n')
# The pages.dev copies (aretepursuits.pages.dev, the review project, branch previews) stay out of search engines;
# only aretepursuits.com is indexed.
with open(os.path.join(OUT, '_headers'), 'a') as f:
    f.write('\nhttps://:project.pages.dev/*\n  X-Robots-Tag: noindex\nhttps://:version.:project.pages.dev/*\n  X-Robots-Tag: noindex\n')
if os.environ.get('REVIEW'):  # review deploys stay out of search engines until cutover
    open(os.path.join(OUT, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
    with open(os.path.join(OUT, '_headers'), 'a') as f: f.write('/*\n  X-Robots-Tag: noindex, nofollow\n')
n_files = sum(len(f) for _, _, f in os.walk(OUT))
print('built', OUT, 'files', n_files, 'posts', len(P))
