// Written with AI assistance (Claude Code). See AI_USE.md.
// Offline support (PROMPT.md section 6: the Cuff Tablet works offline through a service worker).
// On install it caches the app shell (the page, its scripts and styles, and the chunks they load)
// and the small files of the site package the tablet and card need (manifest, plans, photos,
// validation). Pages and data are fetched network-first, so a new deploy reaches users who are
// online; hashed assets are served from the cache first. Nothing is sent anywhere.
const CACHE = "ariadne-v1";
const SITE = "sites/boxwork/";

async function put(cache, url) {
  try {
    const res = await fetch(url, { cache: "no-cache" });
    if (res.ok) await cache.put(url, res.clone());
    return res;
  } catch {
    return null;
  }
}

async function precache() {
  const cache = await caches.open(CACHE);
  const shell = new Set(["./"]);
  const page = await put(cache, "./");
  if (page) {
    const html = await page.text();
    for (const m of html.matchAll(/(?:src|href)="\.\/(assets\/[^"]+)"/g)) shell.add(`./${m[1]}`);
  }
  // the chunks the entry scripts load later (the map, the 3D view, the surfaces)
  for (const url of [...shell].filter((u) => u.endsWith(".js"))) {
    const res = await put(cache, url);
    if (!res) continue;
    const js = await res.text();
    for (const m of js.matchAll(/["'`](?:\.\/|assets\/)([\w.-]+\.(?:js|css))["'`]/g)) {
      shell.add(`./assets/${m[1]}`);
    }
  }
  await Promise.all([...shell].map((u) => put(cache, u)));
  const manifest = await put(cache, `./${SITE}manifest.json`);
  if (manifest) {
    const m = await manifest.json();
    const files = [
      "validation.json",
      ...m.plans.map((p) => p.file),
      ...m.photos.map((p) => p.file),
    ];
    await Promise.all(files.map((f) => put(cache, `./${SITE}${f}`)));
  }
}

self.addEventListener("install", (event) => {
  event.waitUntil(precache().then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key);
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  const hashed = url.pathname.includes("/assets/");
  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);
      if (hashed) {
        const hit = await cache.match(req);
        if (hit) return hit;
      }
      try {
        const res = await fetch(req);
        if (res.ok) cache.put(req, res.clone());
        return res;
      } catch {
        const hit = await cache.match(req, { ignoreSearch: true });
        if (hit) return hit;
        if (req.mode === "navigate") {
          const page = await cache.match("./");
          if (page) return page;
        }
        return new Response("Offline and not cached", { status: 503, statusText: "Offline" });
      }
    })(),
  );
});
