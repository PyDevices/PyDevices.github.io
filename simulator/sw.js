// SPDX-License-Identifier: MIT
// PyDevices Simulator PWA Service Worker with Cross-Origin Isolation (COI) support.

const CACHE_NAME = "pydevices-simulator-v7";

const PRECACHE_ASSETS = [
  "./",
  "./index.html",
  "./simulator.css",
  "./simulator.js",
  "./templates.js",
  "./manifest.json",
  "/assets/img/logo.svg",
  "/assets/img/logo-512.png",
  "/assets/chrome/site.css",
  "/vendor/micropython/micropython.mjs",
  "/vendor/micropython/micropython.wasm",
  "/vendor/xterm/xterm.css",
  "/vendor/xterm/xterm-DrSYbXEP.js",
  "/vendor/xterm/xterm_addon-fit-DxKdSnof.js",
  // Monaco is vendored so a cold offline install still gets an editor. The AMD
  // loader fetches these lazily, which the cache-on-fetch handler below would
  // only pick up after one online session.
  "/vendor/monaco/vs/loader.js",
  "/vendor/monaco/vs/editor/editor.main.js",
  "/vendor/monaco/vs/editor/editor.main.css",
  "/vendor/monaco/vs/basic-languages/python/python.js",
  "/vendor/monaco/vs/base/worker/workerMain.js",
  "/vendor/monaco/vs/base/browser/ui/codicons/codicon/codicon.ttf",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS).catch((err) => {
        console.warn("[Simulator SW] Precache warning:", err);
      });
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

function withCoiHeaders(response) {
  if (!response || response.status === 0) return response;
  const newHeaders = new Headers(response.headers);
  newHeaders.set("Cross-Origin-Embedder-Policy", "credentialless");
  newHeaders.set("Cross-Origin-Opener-Policy", "same-origin");
  newHeaders.set("Cross-Origin-Resource-Policy", "cross-origin");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const mutableSimulatorAsset = request.mode === "navigate" ||
    (url.origin === self.location.origin && url.pathname.startsWith("/simulator/"));

  if (mutableSimulatorAsset) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return withCoiHeaders(response);
        })
        .catch(() => caches.match(request).then((cached) => {
          if (cached) return withCoiHeaders(cached);
          if (request.mode === "navigate") {
            return caches.match("./index.html").then(withCoiHeaders);
          }
          throw new Error("Network unavailable");
        }))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return withCoiHeaders(cached);
      }

      return fetch(request)
        .then((response) => {
          // Cache successful responses for same-origin or known CDNs
          if (response && response.status === 200) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return withCoiHeaders(response);
        })
        .catch(() => {
          // If offline and request is for page, fallback to cached index.html
          if (request.mode === "navigate") {
            return caches.match("./index.html").then(withCoiHeaders);
          }
          throw new Error("Network unavailable");
        });
    })
  );
});
