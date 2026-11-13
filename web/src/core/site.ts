// Written with AI assistance (Claude Code). See AI_USE.md.
// Loads a packaged site once (manifest and the three plans) for every surface that needs it.
import { useEffect, useState } from "react";
import type { Manifest, Plan } from "../planner/types";

export interface Site {
  base: string;
  manifest: Manifest;
  plans: Record<string, Plan>;
}

const cache = new Map<string, Promise<Site>>();

export function siteBase(site: string): string {
  return `${import.meta.env.BASE_URL}sites/${site}/`;
}

export function loadSite(site: string): Promise<Site> {
  const hit = cache.get(site);
  if (hit) return hit;
  const base = siteBase(site);
  const p = (async () => {
    const manifest: Manifest = await (await fetch(`${base}manifest.json`)).json();
    const loaded = await Promise.all(
      manifest.plans.map(async (x) => [x.preset, await (await fetch(base + x.file)).json()] as const),
    );
    return { base, manifest, plans: Object.fromEntries(loaded) };
  })();
  p.catch(() => cache.delete(site));
  cache.set(site, p);
  return p;
}

export function useSite(site = "boxwork"): { site: Site | null; error: string | null } {
  const [s, setS] = useState<Site | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    loadSite(site)
      .then((x) => alive && setS(x))
      .catch(() => alive && setError("The site package could not be loaded."));
    return () => {
      alive = false;
    };
  }, [site]);
  return { site: s, error };
}
