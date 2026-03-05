const CACHE_NAME = 'irsanai-hub-v1';
const URLS = ['/playground/index.html', '/playground/manifest.webmanifest'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(URLS)));
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(r => r || fetch(event.request)));
});
