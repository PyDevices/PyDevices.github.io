// Every file this worker serves comes from the cache once it has been
// fetched, so a browser that has already visited keeps the old copies. Change
// VERSION whenever you change a file: the next visit installs a worker with a
// new cache and the old one is deleted. While you are editing, a hard reload
// skips the worker instead (see docs/pwa-guide.md, "Edits that don't show").
const VERSION = '2';
const CACHE_NAME = 'pyscript-template-' + VERSION;
const SHELL = [
  './',
  './index.html',
  './main.py',
  './pyscript.json',
  './manifest.json',
  './style.css',
  './pwa.js',
  './icon-192.png',
  './icon-512.png',
  './vendor/pyscript/core.css',
  './vendor/pyscript/core.js',
];

self.addEventListener('install', function (event) {
  event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {
    return cache.addAll(SHELL);
  }).then(function () {
    return self.skipWaiting();
  }));
});

self.addEventListener('activate', function (event) {
  event.waitUntil(caches.keys().then(function (names) {
    return Promise.all(names.filter(function (name) {
      return name !== CACHE_NAME;
    }).map(function (name) {
      return caches.delete(name);
    }));
  }).then(function () {
    return self.clients.claim();
  }));
});

// On the first visit the page starts loading before this worker controls it,
// so whatever it fetched in that window (PyScript's hashed chunks, the
// interpreter) never passed through the fetch handler below. pwa.js posts
// the URLs the page loaded once the worker is ready; cache the missing ones
// so the first visit alone is enough to launch offline.
self.addEventListener('message', function (event) {
  var data = event.data || {};
  if (data.type !== 'cache-urls' || !Array.isArray(data.urls)) return;
  event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {
    return Promise.all(data.urls.map(function (url) {
      return cache.match(url).then(function (hit) {
        if (hit) return;
        return fetch(url).then(function (response) {
          if (response && response.status === 200) return cache.put(url, response);
        }).catch(function () {});
      });
    }));
  }));
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(function (cached) {
    if (cached) return cached;
    return fetch(event.request).then(function (response) {
      if (!response || response.status !== 200) return response;
      var copy = response.clone();
      caches.open(CACHE_NAME).then(function (cache) {
        cache.put(event.request, copy);
      });
      return response;
    });
  }));
});
