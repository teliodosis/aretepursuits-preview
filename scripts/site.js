/* Arete Pursuits — small runtime for the static site */
(function () {
  var path = location.pathname;
  /* current-page highlighting */
  var GROUP = { '/services/executive-coaching/': 'lead', '/services/organizations/': 'lead', '/services/consciousness-coaching/': 'being', '/services/life-coaching/': 'being', '/meditation/': 'being' };
  document.querySelectorAll('.menu > a').forEach(function (a) {
    var h = a.getAttribute('href');
    if (h === path || (h === '/blog/' && (document.body.dataset.kind === 'post' || path.indexOf('/category/') === 0))) a.setAttribute('aria-current', 'page');
  });
  document.querySelectorAll('.dd > button').forEach(function (b) { b.classList.toggle('on', GROUP[path] === b.dataset.group); });

  /* menus with forgiving hover */
  var dds = [].slice.call(document.querySelectorAll('.dd'));
  function closeAll(except) { dds.forEach(function (d) { if (d !== except) { d.querySelector('.dd-panel').hidden = true; d.querySelector('button').setAttribute('aria-expanded', 'false'); } }); }
  dds.forEach(function (d) {
    var b = d.querySelector('button'), p = d.querySelector('.dd-panel'), t = null;
    function open() { clearTimeout(t); closeAll(d); p.hidden = false; b.setAttribute('aria-expanded', 'true'); }
    b.addEventListener('click', function (e) { e.stopPropagation(); if (p.hidden) open(); else { p.hidden = true; b.setAttribute('aria-expanded', 'false'); } });
    d.addEventListener('mouseenter', function () { if (matchMedia('(hover:hover)').matches) open(); });
    d.addEventListener('mouseleave', function () { if (matchMedia('(hover:hover)').matches) { clearTimeout(t); t = setTimeout(function () { p.hidden = true; b.setAttribute('aria-expanded', 'false'); }, 400); } });
  });
  document.addEventListener('click', function (e) { if (!e.target.closest('.dd')) closeAll(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeAll(); });
  var burger = document.getElementById('burger'), mobile = document.getElementById('mobileNav');
  if (burger) burger.addEventListener('click', function () { var o = mobile.hidden; mobile.hidden = !o; burger.setAttribute('aria-expanded', String(o)); burger.textContent = o ? 'Close' : 'Menu'; });

  /* in-page jumps */
  document.addEventListener('click', function (e) {
    var j = e.target.closest('[data-jump]'); if (!j) return;
    var t = document.getElementById(j.dataset.jump); if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); }
  });

  /* copy buttons on the contact page */
  document.querySelectorAll('.copy').forEach(function (cp) {
    cp.addEventListener('click', function () {
      var v = cp.dataset.copy;
      try { navigator.clipboard.writeText(v).then(function () { cp.textContent = 'Copied'; setTimeout(function () { cp.textContent = v.indexOf('@') > -1 ? 'Copy address' : 'Copy number'; }, 1600); }, function () { cp.textContent = 'Select the text above to copy'; }); } catch (_) {}
    });
  });

  /* hover definition for "fortnightly" */
  var main = document.getElementById('app');
  if (main) {
    var w = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { return /fortnightly/i.test(n.nodeValue) && !n.parentElement.closest('a,.fn,script,style,textarea,input,h1') ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; } });
    var nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
    nodes.forEach(function (n) {
      var f = document.createDocumentFragment();
      n.nodeValue.split(/(fortnightly)/i).forEach(function (part, i) {
        if (i % 2) { var s = document.createElement('span'); s.className = 'fn'; s.tabIndex = 0; s.textContent = part; s.setAttribute('aria-label', part + ' (every two weeks)'); f.appendChild(s); }
        else if (part) f.appendChild(document.createTextNode(part));
      });
      n.replaceWith(f);
    });
  }

  /* search the writing archive */
  var q = document.getElementById('q'), arch = document.getElementById('archive');
  if (q && arch) {
    var empty = document.createElement('p'); empty.className = 'empty'; empty.hidden = true; arch.appendChild(empty);
    q.addEventListener('input', function () {
      var v = q.value.trim().toLowerCase(), shown = 0;
      arch.querySelectorAll('.row').forEach(function (r) { var hit = !v || r.textContent.toLowerCase().indexOf(v) > -1; r.hidden = !hit; if (hit) shown++; });
      arch.querySelectorAll('.year').forEach(function (y) { y.hidden = !y.querySelector('.row:not([hidden])'); });
      empty.hidden = shown > 0; empty.textContent = 'No posts match “' + q.value + '”. Try another word.';
      var top = document.getElementById('toptier'); if (top) top.hidden = !!v;
    });
  }
})();
