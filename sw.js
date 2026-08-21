const CACHE = 'fgsb-v18';
const STATIC = [
  '/',
  '/index.html',
  '/login.html',
  '/Signup.html',
  '/dashboard.html',
  '/transfers.html',
  '/cards.html',
  '/bills.html',
  '/loan.html',
  '/support.html',
  '/branches.html',
  '/forgot-password.html',
  '/reset-password.html',
  '/manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  const url = new URL(req.url);

  // Only ever intercept GETs; let POSTs etc. hit the network untouched.
  if (req.method !== 'GET') return;

  // Admin pages: always fresh, never cached.
  if (url.origin === self.location.origin && url.pathname.startsWith('/admin')) {
    e.respondWith(fetch(req));
    return;
  }

  // API calls (the backend lives on another origin): network only, with an
  // offline JSON fallback so callers get a clean error instead of hanging.
  if (url.pathname.startsWith('/api/') || url.hostname === 'dhiobank.13-48-31-7.sslip.io') {
    e.respondWith(
      fetch(req).catch(() => new Response(
        JSON.stringify({ error: 'Offline' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // Page navigations: network-first, so the installed app always loads the
  // latest deployed page when online and only falls back to cache offline.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(res => {
        if (res.ok && url.origin === self.location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() =>
        caches.match(req).then(c => c || caches.match('/index.html'))
      )
    );
    return;
  }

  // Everything else (icons, fonts, css, images): cache-first for speed,
  // refreshing the cached copy in the background when reachable.
  e.respondWith(
    caches.match(req).then(cached =>
      cached || fetch(req).then(res => {
        if (res.ok && url.origin === self.location.origin) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(req, clone));
        }
        return res;
      }).catch(() => cached)
    )
  );
});
