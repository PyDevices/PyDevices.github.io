// SPDX-License-Identifier: MIT
// PyDevices Simulator PWA Service Worker with Cross-Origin Isolation (COI) support.

const CACHE_NAME = "pydevices-simulator-v1";

const PRECACHE_ASSETS = [
  "./",
  "./index.html",
  "./simulator.css",
  "./simulator.js",
  "./templates.js",
  "./micropython.json",
  "./pyodide.json",
  "./manifest.json",
  "/assets/img/logo.svg",
  "/assets/img/logo-512.png",
  "/assets/chrome/site.css",
  "/vendor/micropython/micropython.mjs",
  "/vendor/micropython/micropython.wasm",
  "https://cdnjs.cloudflare.com/ajax/libs/lz-string/1.5.0/lz-string.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.js",
  "https://pyscript.net/releases/2024.11.1/core.css",
  "https://pyscript.net/releases/2024.11.1/core.js",
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
