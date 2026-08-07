/* Boo's Game Box — service worker.
 *
 * ┌──────────────────────────────────────────────────────────────────┐
 * │  BUMP CACHE_VERSION ON EVERY DEPLOY.                             │
 * │                                                                  │
 * │  This worker is cache-first. If you change a .py file, a style,  │
 * │  or anything else in public/ and do not bump this number, every  │
 * │  device that has already visited will keep serving the old copy  │
 * │  forever. A stale worker shipping yesterday's game is the single │
 * │  most common way this app breaks.                                │
 * └──────────────────────────────────────────────────────────────────┘
 */
const CACHE_VERSION = "v3";

/* Must match PYODIDE_VERSION in app.js. tools/check_games.py checks that
 * these two agree, so run it before you deploy. */
const PYODIDE_VERSION = "314.0.3";

const CACHE_NAME = `boos-game-box-${CACHE_VERSION}`;
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

const FONTS_CSS =
  "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600..900&family=Plus+Jakarta+Sans:wght@400..800&display=swap";

/* The app shell. */
const SHELL = [
  "./",
  "index.html",
  "styles.css",
  "app.js",
  "manifest.json",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-maskable-512.png",
  "py/games.json",
  "py/view.py",
  "py/engine.py",
  "py/games/__init__.py",
];

/* The Python runtime itself. Big, but it is the whole point of offline. */
const PYODIDE_FILES = [
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "pyodide-lock.json",
  "python_stdlib.zip",
].map((name) => PYODIDE_URL + name);

/* Anything from these origins is worth keeping once we have seen it. */
function isCacheable(url) {
  return (
    url.origin === self.location.origin ||
    url.href.startsWith(PYODIDE_URL) ||
    url.origin === "https://fonts.googleapis.com" ||
    url.origin === "https://fonts.gstatic.com"
  );
}

/* The games are read from the registry, not listed here — that is what
 * keeps "add a game" down to one new file and one new line. */
async function gameFiles() {
  try {
    const response = await fetch("py/games.json", { cache: "no-store" });
    const ids = (await response.json()).games || [];
    return ids.map((id) => `py/games/${id.replace(/-/g, "_")}.py`);
  } catch (error) {
    console.warn("[sw] could not read the game registry:", error);
    return [];
  }
}

/* Cache each URL on its own, so one bad response cannot stop the install.
 * A half-cached box that works online beats a worker that never installs. */
async function cacheAll(cache, urls) {
  await Promise.all(
    urls.map(async (url) => {
      try {
        const response = await fetch(url, { cache: "no-store" });
        if (response.ok) await cache.put(url, response);
      } catch (error) {
        console.warn("[sw] skipped", url, error);
      }
    })
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      await cacheAll(cache, SHELL.concat(await gameFiles()));
      await cacheAll(cache, [FONTS_CSS]);
      await cacheAll(cache, PYODIDE_FILES);
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((name) => name.startsWith("boos-game-box-") && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!isCacheable(url)) return;

  event.respondWith(
    (async () => {
      const cached = await caches.match(request, { ignoreSearch: false });
      if (cached) return cached;

      try {
        const response = await fetch(request);
        // Opaque responses have status 0; keep them anyway (fonts, CDN).
        if (response && (response.ok || response.type === "opaque")) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(request, response.clone());
        }
        return response;
      } catch (error) {
        // Offline and not in the cache. A navigation still gets the shell.
        if (request.mode === "navigate") {
          const shell = await caches.match("index.html");
          if (shell) return shell;
        }
        throw error;
      }
    })()
  );
});

/* Lets a page ask the worker to step aside for a new one immediately. */
self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});
