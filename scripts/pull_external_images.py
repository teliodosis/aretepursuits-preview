"""Copy images that posts hotlink from other servers (old GoDaddy site builder) into media/, as JPEGs <=1600px."""
import json, os, io, urllib.request
from PIL import Image, ImageOps
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'}
mp = json.load(open('content/media-map.json'))
for it in json.load(open('content/external-images.json')):
    data = urllib.request.urlopen(urllib.request.Request(it['url'], headers=UA), timeout=60).read()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255)); im = im.convert('RGBA'); bg.paste(im, mask=im.split()[-1]); im = bg
    im = im.convert('RGB')
    if im.width > 1600: im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(it['dest']), exist_ok=True)
    im.save(it['dest'], 'JPEG', quality=84, optimize=True, progressive=True)
    mp[it['url']] = {'path': '/' + it['dest'][len('media/'):], 'w': im.width, 'h': im.height}
    print('ok', it['dest'], im.size)
json.dump(mp, open('content/media-map.json', 'w'), indent=1)
