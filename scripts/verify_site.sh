#!/bin/bash
# Check a deployed build: every page/post returns 200, and legacy links redirect where they should.
BASE=${1:-https://site.aretepursuits-preview.pages.dev}
mkdir -p reports; out=reports/verify.txt; : > $out
python3 - "$BASE" > /tmp/urls.txt <<'PY'
import json,sys,re
P=json.load(open('content/posts.json'))
for u in ['/','/services/executive-coaching/','/services/organizations/','/services/consciousness-coaching/','/services/life-coaching/','/meditation/','/blog/','/about/','/resources/','/contact/','/privacy-policy/','/terms-and-conditions/','/feed.xml','/sitemap.xml','/robots.txt','/og/default.jpg']: print(u)
for p in P: print('/'+p['slug']+'/')
for c in json.load(open('content/categories.json')):
    if c['count']: print('/category/'+{'walkabout':'wanderment'}.get(c['slug'],c['slug'])+'/')
PY
fail=0
while read u; do c=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$u"); [ "$c" != "200" ] && { echo "PAGE $c $u" >> $out; fail=$((fail+1)); }; done < /tmp/urls.txt
echo "pages checked $(wc -l < /tmp/urls.txt), failures $fail" >> $out
for u in /schedule/25 /schedule/website /schedule/consciousness /schedule/session /services/leadership-workshops/ /services/disc-facilitation/ /services/360-feedback/ /everything-disc /five-behaviors /feed/ /blog/feed/ /blog/f/gentleness /blog/gentleness /blog/page/3/ /executive-coaching /blog/f/clearing-the-fog /blog/f/the-heros-journey /blog/f/it%E2%80%99s-called-breakfast-for-a-reason /blog/f/the-hero-ignored /wp-sitemap.xml /category/walkabout/ /productivity-mastery /gentleness/feed/ /nonexistent-page-xyz/; do
  echo "REDIR $u -> $(curl -s -o /dev/null -w "%{http_code} %{redirect_url}" "$BASE$u")" >> $out
done
echo "HEADERS / $(curl -sI "$BASE/" | grep -i -E 'x-robots|content-type' | tr '\r\n' '  ')" >> $out
