# New posts (after the move off WordPress)

One JSON file per post, named `<slug>.json`:

```json
{
  "slug": "my-post",
  "title": "My Post",
  "date": "2026-10-19T09:00:00",          // Eastern time; the post stays hidden until then
  "categories": ["Consciousness", "Growth"],
  "excerpt": "The call-to-action blurb, no hashtags.",
  "featured": "/wp-content/uploads/2026/10/my-post.jpg",   // file lives under media/
  "body": "<p><em>Call-to-action blurb</em></p><p>…</p>"
}
```

Images go in `media/wp-content/uploads/YYYY/MM/`, resized to at most 1600px wide.
Pushing to main rebuilds the site; a Monday-morning schedule publishes posts whose time has come.
