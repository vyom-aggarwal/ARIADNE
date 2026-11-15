// Written with AI assistance (Claude Code). See AI_USE.md.
// Habitat Planner: the map or the 3D rehearsal fills the canvas; Layers float on the left, the
// three route options on the right, and the timeline docks at the bottom. Each panel collapses.
import { Activity, ChevronDown, ChevronUp, Layers as LayersIcon, Route } from "lucide-react";
import { lazy, type ReactNode, Suspense, useEffect, useState } from "react";
import { useSite } from "../core/site";
import AssumptionsPanel from "./AssumptionsPanel";
import LayerPanel, { type LayerState } from "./LayerPanel";
import RouteOptions from "./RouteOptions";
import Timeline from "./Timeline";

// start fetching the map code at once, in parallel with the site package
const mapModule = typeof window !== "undefined" && "WebGL2RenderingContext" in window
  ? import("./MapView")
  : null;
const MapView = lazy(() => mapModule ?? import("./MapView"));
const Rehearsal = lazy(() => import("../rehearsal/Rehearsal"));

function FloatPanel({ id, title, icon, side, children, startOpen = true }: {
  id: string;
  title: string;
  icon: ReactNode;
  side: "left" | "right" | "bottom";
  children: ReactNode;
  startOpen?: boolean;
}) {
  const [open, setOpen] = useState(startOpen);
  return (
    <section className={`float-panel ${side}${open ? "" : " collapsed"}`} aria-labelledby={`${id}-title`}>
      <div className="panel-head">
        {icon}
        <h2 id={`${id}-title`}>{title}</h2>
        <button type="button" className="ghost collapse" aria-expanded={open} aria-controls={`${id}-body`}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`} onClick={() => setOpen((o) => !o)}>
          {open ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
        </button>
      </div>
      <div className="panel-body" id={`${id}-body`} hidden={!open}>
        {children}
      </div>
    </section>
  );
}

export default function Planner({ site = "boxwork" }: { site?: string }) {
  const { site: data, error } = useSite(site);
  const [layerState, setLayerState] = useState<Record<string, LayerState>>({});
  const [preset, setPreset] = useState("balanced");
  const [view, setView] = useState<"map" | "3d">("map");
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    const on = (e: Event) => setView((e as CustomEvent<"map" | "3d">).detail);
    window.addEventListener("ariadne:planner-view", on);
    return () => window.removeEventListener("ariadne:planner-view", on);
  }, []);

  const manifest = data?.manifest ?? null;
  const plans = data?.plans ?? {};
  const plan = plans[preset] ?? null;
  return (
    <section className="planner" aria-labelledby="planner-heading" data-map-ready={mapReady}>
      <h2 id="planner-heading" className="planner-title">
        Habitat Planner{manifest ? `: ${manifest.title}` : ""}
      </h2>
      {error && <p role="alert">{error}</p>}
      {!manifest && !error && <p role="status" className="page">Loading the site package…</p>}
      {manifest && data && (
        <>
          <div className="planner-stage">
            <div className="view-switch" role="group" aria-label="View">
              <button type="button" aria-pressed={view === "map"} onClick={() => setView("map")}>
                Map
              </button>
              <button type="button" aria-pressed={view === "3d"} onClick={() => setView("3d")}>
                3D rehearsal
              </button>
            </div>
            <Suspense fallback={<p role="status" className="page">Loading the view…</p>}>
              {view === "map" ? (
                <MapView manifest={manifest} base={data.base} layerState={layerState} plan={plan}
                  onReady={() => setMapReady(true)} />
              ) : (
                <Rehearsal manifest={manifest} base={data.base} plan={plan} />
              )}
            </Suspense>
          </div>
          <FloatPanel id="layers" title="Layers" side="left" icon={<LayersIcon size={15} aria-hidden="true" />}>
            <LayerPanel
              layers={manifest.layers}
              state={layerState}
              onChange={(id, change) => setLayerState((s) => ({ ...s, [id]: { ...s[id], ...change } }))}
            />
          </FloatPanel>
          <FloatPanel id="routes" title="Routes" side="right" icon={<Route size={15} aria-hidden="true" />}>
            {Object.keys(plans).length > 0 && <RouteOptions plans={plans} selected={preset} onSelect={setPreset} />}
            <AssumptionsPanel items={manifest.assumptions ?? []} notes={manifest.site_notes ?? []} />
          </FloatPanel>
          {plan && (
            <FloatPanel id="timeline" title="Timeline" side="bottom" icon={<Activity size={15} aria-hidden="true" />}>
              <Timeline plan={plan} />
            </FloatPanel>
          )}
        </>
      )}
    </section>
  );
}
