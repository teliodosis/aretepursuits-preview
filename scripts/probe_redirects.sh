#!/bin/bash
# Record where each legacy URL on the live site redirects today.
out=content/legacy-redirects.txt; : > $out
paths="/schedule/25 /schedule/50 /schedule/80 /schedule/blog /schedule/website /schedule/doctums /schedule/discovery /schedule/session /schedule/session100 /schedule/session200 /schedule/individual /schedule/disc /schedule/consciousness /schedule/coaching-friends-family /five-behaviors /everything-disc /productivity-boot-camp /productivity-mastery /corporate-coaching /412-2/teliodosis /465-2/ /root /blog/f.rss /services/ /executive-coaching /disc-facilitation /leadership-workshops /life-coaching /360-feedback /?page_id=57 /?page_id=62 /?page_id=80 /?page_id=86 /?page_id=87 /?page_id=88 /?page_id=89 /?page_id=90 /?page_id=91 /blog/feed/ /feed/"
if [ -n "$PROBE_PATHS" ]; then paths="$PROBE_PATHS"; out=content/probe-extra.txt; : > $out; else
for s in $(python3 -c "import json;print(' '.join(p['slug'] for p in json.load(open('content/posts.json'))))"); do paths="$paths /blog/f/$s /blog/$s"; done
fi
for p in $paths; do
  r=$(curl -s -o /dev/null -w "%{http_code} %{redirect_url}" "https://aretepursuits.com$p"); [ -n "$PROBE_PATHS" ] && r="$r FINAL $(curl -sL -o /dev/null -w "%{http_code} %{url_effective}" "https://aretepursuits.com$p")"
  echo "$p $r" >> $out
done
wc -l $out
