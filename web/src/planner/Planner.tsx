// Written with AI assistance (Claude Code). See AI_USE.md.
// Habitat Planner: loads one packaged site and shows the layers, the map or the 3D rehearsal,
// the three route options and the timeline of the selected route.
import { lazy, Suspense, useEffect, useState } from "react";
import AssumptionsPanel from "./AssumptionsPanel";
import LayerPanel, { type LayerState } from "./LayerPanel";
import RouteOptions from "./RouteOptions";
import Timeline from "./Timeline";
import type { Manifest, Plan } from "./types";

// start fetching the map code at once, in parallel with the site package
const mapModule = typeof window !== "undefined" && "WebGL2RenderingContext" in window
  ? import("./MapView")
  : null;
const MapView = lazy(() => mapModule ?? import("./MapView"));
const Rehearsal = lazy(() => import("../rehearsal/Rehearsal"));

export default function Planner({ site = "boxwork" }: { site?: string }) {
  const base = `${import.meta.env.BASE_URL}sites/${site}/`;
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [error, setError] = useState<string | null>(null);
  const [layerState, setLayerState] = useState<Record<string, LayerState>>({});
  const [preset, setPreset] = useState("balanced");
  const [view, setView] = useState<"map" | "3d">("map");
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const m: Manifest = await (await fetch(`${base}manifest.json`)).json();
        const loaded = await Promise.all(
          m.plans.map(async (p) => [p.preset, await (await fetch(base + p.file)).json()] as const),
        );
        if (!alive) return;
        setManifest(m);
        setPlans(Object.fromEntries(loaded));
      } catch {
        if (alive) setError("The site package could not be loaded.");
      }
    })();
    return () => {
      alive = false;
    };
  }, [base]);

  const plan = plans[preset] ?? null;
  return (
    <section className="planner" aria-labelledby="planner-heading" data-map-ready={mapReady}>
      <h2 id="planner-heading" className="planner-title">
        Habitat Planner{manifest ? `: ${manifest.title}` : ""}
      </h2>
      {error && <p role="alert">{error}</p>}
      {!manifest && !error && <p role="status">Loading the site package…</p>}
      {manifest && (
        <div className="planner-grid">
          <LayerPanel
            layers={manifest.layers}
            state={layerState}
            onChange={(id, change) => setLayerState((s) => ({ ...s, [id]: { ...s[id], ...change } }))}
          />
          <div className="planner-centre">
            <div className="view-switch" role="group" aria-label="View">
              <button type="button" aria-pressed={view === "map"} onClick={() => setView("map")}>
                Map
              </button>
              <button type="button" aria-pressed={view === "3d"} onClick={() => setView("3d")}>
                3D rehearsal
              </button>
            </div>
            <Suspense fallback={<p role="status">Loading the view…</p>}>
              {view === "map" ? (
                <MapView
                  manifest={manifest}
                  base={base}
                  layerState={layerState}
                  plan={plan}
                  onReady={() => setMapReady(true)}
                />
              ) : (
                <Rehearsal manifest={manifest} base={base} plan={plan} />
              )}
            </Suspense>
            {plan && <Timeline plan={plan} />}
          </div>
          <div className="planner-side">
            {Object.keys(plans).length > 0 && (
              <RouteOptions plans={plans} selected={preset} onSelect={setPreset} />
            )}
            <AssumptionsPanel items={manifest.assumptions ?? []} notes={manifest.site_notes ?? []} />
          </div>
        </div>
      )}
    </section>
  );
}
