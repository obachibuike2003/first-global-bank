// Kill-switch service worker.
//
// The previous worker cached pages, which made the installed app go stale and
// occasionally hang on old content while the website stayed correct. This
// version does the opposite: it takes over, deletes every cache, unregisters
// itself, and reloads open windows so they load live from the network from now
// on. After this runs once on a device, no service worker controls the app and
// it behaves exactly like the website.

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map(k => caches.delete(k)));
    } catch (e) {}
    try {
      await self.registration.unregister();
    } catch (e) {}
    const clients = await self.clients.matchAll({ type: 'window' });
    clients.forEach(c => { try { c.navigate(c.url); } catch (e) {} });
  })());
});

// Never intercept requests — let everything hit the network directly.
