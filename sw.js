// ── Inventur Scanner – Service Worker ────────────────────────────────────────
// WICHTIG: CACHE_NAME hochzählen (v2, v3, …) bei jedem Deployment.
// Das löst die Update-Erkennung im Browser aus.
const CACHE_NAME = 'inventur-v61';

// App-Shell (müssen alle erfolgreich geladen werden)
const CORE_URLS = [
  './',
  './index.html',
  './manifest.json',
  './data/masterlist.json',
];

// CDN-Bibliotheken (best-effort; kein Abbruch wenn offline)
const CDN_URLS = [
  'https://unpkg.com/@zxing/library@0.18.6/umd/index.min.js',
  'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
];

// ── INSTALL: Cache befüllen + sofort aktivieren ──────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE_URLS);
    await Promise.allSettled(CDN_URLS.map(u => cache.add(u)));
    await self.skipWaiting(); // nicht auf Tab-Schliessung warten
  })());
});

// ── ACTIVATE: Alte Caches löschen ───────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── SHARE TARGET: Eingehende Datei cachen + weiterleiten ─────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (event.request.method === 'POST' && url.searchParams.has('share-target')) {
    event.respondWith((async () => {
      const formData = await event.request.formData();
      const file = formData.get('file');
      if (file && file.size > 0) {
        const cache = await caches.open('inventur-share');
        await cache.put('incoming-file', new Response(await file.arrayBuffer(), {
          headers: {
            'Content-Type': file.type || 'application/octet-stream',
            'X-Filename': file.name || 'shared.xlsx',
          }
        }));
      }
      const appUrl = new URL('./', self.location.href);
      appUrl.searchParams.set('share-incoming', '1');
      return Response.redirect(appUrl.toString(), 303);
    })());
    return;
  }
});

// ── FETCH: Cache-Strategie ───────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Analytics: nativ durchlassen, nicht cachen
  if (url.hostname === 'script.google.com' || url.hostname === 'script.googleusercontent.com') return;

  // masterlist.json: Network-first → immer aktuellste Daten
  if (url.pathname.endsWith('masterlist.json')) {
    event.respondWith(
      fetch(event.request)
        .then(res => {
          if (res.ok) {
            caches.open(CACHE_NAME).then(c => c.put(event.request, res.clone()));
          }
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Alles andere: Cache-first, Netzwerk als Fallback
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(res => {
        if (res.ok) {
          caches.open(CACHE_NAME).then(c => c.put(event.request, res.clone()));
        }
        return res;
      });
    })
  );
});

