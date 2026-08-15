const PUBLIC_CACHE = "mingli-public-v1";

const PRIVATE_PATH_PREFIXES = [
  "/app/",
  "/account",
  "/auth/",
  "/workbench/",
  "/checkout/",
  "/share/",
  "/invite/",
];

const PUBLIC_DOCUMENT_PATHS = new Set([
  "/",
  "/arts",
  "/daily",
  "/tools",
  "/library",
  "/about",
  "/pricing",
  "/methodology",
  "/support",
  "/privacy",
  "/terms",
]);

function isPrivatePath(pathname) {
  return PRIVATE_PATH_PREFIXES.some(
    (prefix) => {
      const base = prefix.replace(/\/$/, "");
      return pathname === base || pathname.startsWith(`${base}/`);
    },
  );
}

function isCacheablePublicRequest(request, url) {
  if (request.method !== "GET" || url.origin !== self.location.origin) return false;
  if (request.cache === "no-store") return false;
  if (isPrivatePath(url.pathname)) return false;
  if (url.pathname.startsWith("/api/")) return false;

  if (url.pathname.startsWith("/_next/static/")) return true;
  return request.mode === "navigate" && PUBLIC_DOCUMENT_PATHS.has(url.pathname);
}

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (isPrivatePath(url.pathname)) {
    event.respondWith(fetch(event.request, { cache: "no-store" }));
    return;
  }

  if (!isCacheablePublicRequest(event.request, url)) return;

  event.respondWith(
    caches.open(PUBLIC_CACHE).then(async (cache) => {
      const cached = await cache.match(event.request);
      if (cached) return cached;

      const response = await fetch(event.request);
      if (response.ok && response.type !== "opaque") {
        await cache.put(event.request, response.clone());
      }
      return response;
    }),
  );
});
