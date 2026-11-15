// Written with AI assistance (Claude Code). See AI_USE.md.
// The planner's 2D map: deck.gl OrthographicView in site metres (east, north), shifted to the
// site's south-west corner so float32 keeps centimetre precision.
import { OrthographicView } from "@deck.gl/core";
import { BitmapLayer, GeoJsonLayer, IconLayer, PathLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import DeckGL from "@deck.gl/react";
import { useEffect, useMemo, useState } from "react";
import type { LayerState } from "./LayerPanel";
import type { Manifest, Plan } from "./types";

interface Props {
  manifest: Manifest;
  base: string;
  layerState: Record<string, LayerState>;
  plan: Plan | null;
  onReady?: () => void;
}

type XY = [number, number];

const THREAD: [number, number, number] = [61, 224, 255];
// a relay site is drawn as a diamond (a vector glyph, not an image)
const DIAMOND =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><path d="M20 3 L37 20 L20 37 L3 20 Z" fill="#ffc24a" stroke="#000" stroke-width="3"/></svg>',
  );

/** A scale-bar length (metres) near 110 px at this zoom: 1, 2 or 5 times a power of ten. */
export function scaleBar(zoom: number): { metres: number; px: number } {
  const pxPerM = 2 ** zoom;
  const target = 110 / pxPerM;
  const p = 10 ** Math.floor(Math.log10(target));
  const metres = [1, 2, 5, 10].map((k) => k * p).filter((m) => m <= target).pop() ?? p;
  return { metres, px: metres * pxPerM };
}

function shiftGeo(gj: any, ox: number, oy: number): any {
  const shift = (c: any): any =>
    typeof c[0] === "number" ? [c[0] - ox, c[1] - oy] : c.map((x: any) => shift(x));
  return {
    ...gj,
    features: gj.features.map((f: any) => ({
      ...f,
      geometry: f.geometry && { ...f.geometry, coordinates: shift(f.geometry.coordinates) },
    })),
  };
}

export default function MapView({ manifest, base, layerState, plan, onReady }: Props) {
  const [ox, oy] = [manifest.bounds_m[0], manifest.bounds_m[1]];
  const [vectors, setVectors] = useState<Record<string, any>>({});
  // overlays are fetched only once shown; the 1 m imagery replaces the 2 m overview after load
  const [shown, setShown] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (!loaded) return;
    const img = manifest.layers.find((l) => l.id === "imagery");
    if (!img?.file_detail) return;
    const pre = new Image();
    pre.onload = () => setDetail(true);
    pre.src = base + img.file_detail;
  }, [loaded, manifest, base]);
  useEffect(() => {
    const now = manifest.layers
      .filter((l) => layerState[l.id]?.visible ?? l.default_visible)
      .map((l) => l.id);
    setShown((s) => (now.every((id) => s.has(id)) ? s : new Set([...s, ...now])));
  }, [manifest, layerState]);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!ready) return; // context vectors load after the first map is drawn
    let alive = true;
    for (const lay of manifest.layers.filter((l) => l.kind === "vector")) {
      fetch(base + lay.file)
        .then((r) => r.json())
        .then((gj) => alive && setVectors((v) => ({ ...v, [lay.id]: shiftGeo(gj, ox, oy) })))
        .catch(() => {});
    }
    return () => {
      alive = false;
    };
  }, [manifest, base, ox, oy, ready]);

  const local = (p: XY): XY => [p[0] - ox, p[1] - oy];
  const [zoom, setZoom] = useState(-1.2);
  const stage = local(manifest.staging_xy_m);
  const initialViewState = { target: [stage[0], stage[1], 0] as [number, number, number], zoom: -1.2,
    minZoom: -4, maxZoom: 4 };

  const layers = useMemo(() => {
    const out: any[] = [];
    for (const lay of manifest.layers) {
      const s = layerState[lay.id] ?? {};
      const visible = s.visible ?? lay.default_visible;
      const opacity = s.opacity ?? lay.opacity;
      if (lay.kind === "raster" && lay.bounds_m && shown.has(lay.id)) {
        const useDetail = detail && !!lay.file_detail;
        const [w, so, e, n] = useDetail && lay.bounds_detail_m ? lay.bounds_detail_m : lay.bounds_m;
        out.push(
          new BitmapLayer({
            id: lay.id,
            image: base + (useDetail ? lay.file_detail : lay.file),
            bounds: [w - ox, so - oy, e - ox, n - oy],
            visible,
            opacity,
            textureParameters: { minFilter: "linear", magFilter: lay.id === "imagery" ? "linear" : "nearest" },
          }),
        );
      } else if (lay.kind === "vector" && vectors[lay.id]) {
        out.push(
          new GeoJsonLayer({
            id: lay.id,
            data: vectors[lay.id],
            visible,
            opacity,
            stroked: true,
            filled: true,
            pointType: "circle",
            getLineColor: lay.id === "seams" ? [240, 228, 66, 220] : lay.id === "rover_path"
              ? [255, 255, 255, 230] : [0, 114, 178, 200],
            getFillColor: [255, 255, 255, 230],
            getPointRadius: 4,
            pointRadiusUnits: "pixels",
            lineWidthUnits: "pixels",
            getLineWidth: lay.id === "rover_path" ? 2 : 1.5,
          }),
        );
      }
    }
    if (plan) {
      // the thread: a dark edge, a wide soft glow and a bright core
      const path = (l: any) => l.path_xy_m.map((p: XY) => local(p));
      const transects = [...new Map(plan.stations.map((s) => [s.transect, s])).values()];
      out.push(
        new PathLayer({ id: "route-edge", data: plan.legs, getPath: path, getColor: [0, 0, 0, 200],
          getWidth: 9, widthUnits: "pixels", capRounded: true, jointRounded: true }),
        new PathLayer({ id: "route", data: plan.legs, getPath: path, getColor: [...THREAD, 90],
          getWidth: 12, widthUnits: "pixels", capRounded: true, jointRounded: true }),
        new PathLayer({ id: "route-core", data: plan.legs, getPath: path, getColor: [215, 250, 255, 255],
          getWidth: 2.5, widthUnits: "pixels", capRounded: true, jointRounded: true }),
        new ScatterplotLayer({
          id: "stations",
          data: plan.stations,
          getPosition: (s: any) => local(s.xy_m),
          getFillColor: [10, 14, 26, 255],
          getLineColor: THREAD,
          stroked: true,
          lineWidthMinPixels: 2,
          getRadius: 5,
          radiusUnits: "pixels",
          pickable: true,
        }),
        new ScatterplotLayer({
          id: "transect-markers",
          data: transects,
          getPosition: (s: any) => local(s.xy_m),
          getFillColor: [10, 14, 26, 255],
          getLineColor: THREAD,
          stroked: true,
          lineWidthMinPixels: 2,
          getRadius: 11,
          radiusUnits: "pixels",
          pickable: true,
        }),
        new TextLayer({
          id: "transect-numbers",
          data: transects,
          getPosition: (s: any) => local(s.xy_m),
          getText: (s: any) => s.transect.replace(/^T0?/, ""),
          getSize: 12,
          getColor: [230, 236, 247],
          fontWeight: 700,
          fontFamily: "Inter, system-ui, sans-serif",
        }),
      );
    }
    if (plan?.rover) {
      const relays = plan.rover.relays.filter((r) => r.id !== "STAGING");
      out.push(
        new IconLayer({
          id: "relays",
          data: relays,
          getPosition: (r: any) => local(r.xy_m),
          getIcon: () => ({ url: DIAMOND, width: 40, height: 40, anchorY: 20, mask: false }),
          getSize: 22,
          sizeUnits: "pixels",
          pickable: true,
        }),
        new TextLayer({
          id: "relay-labels",
          data: relays,
          getPosition: (r: any) => local(r.xy_m),
          getText: (r: any) => r.id.replace("RELAY", "R"),
          getSize: 12,
          getColor: [230, 236, 247],
          getPixelOffset: [0, -20],
          fontWeight: 700,
          fontFamily: "Inter, system-ui, sans-serif",
          outlineWidth: 2,
          outlineColor: [0, 0, 0, 255],
          fontSettings: { sdf: true },
        }),
      );
    }
    out.push(
      new ScatterplotLayer({
        id: "staging",
        data: [stage],
        getPosition: (p: XY) => p,
        getFillColor: [255, 255, 255],
        getLineColor: [0, 0, 0],
        stroked: true,
        lineWidthMinPixels: 3,
        getRadius: 9,
        radiusUnits: "pixels",
        pickable: true,
      }),
    );
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manifest, base, layerState, plan, vectors, ox, oy, shown, detail]);

  const bar = scaleBar(zoom);
  const tooltip = ({ object, layer }: any) => {
    if (!object || !layer) return null;
    const style = { background: "rgba(15,21,38,0.97)", color: "#e6ecf7", border: "1px solid rgba(140,170,255,0.28)",
      borderRadius: "6px", fontFamily: "Inter, system-ui, sans-serif", fontSize: "12px", padding: "6px 8px" };
    if (layer.id === "stations" || layer.id === "transect-markers") {
      return { text: `${object.id} · ${object.role} station · transect ${object.transect}`, style };
    }
    if (layer.id === "relays") return { text: `${object.id.replace("RELAY", "Relay site R")} (PLACEHOLDER)`, style };
    if (layer.id === "staging") return { text: "Staging point: the rover starts here (PLACEHOLDER)", style };
    return null;
  };
  return (
    <div className="map-wrap">
      <div className="map" role="region" aria-label="Map of the site in metres; drag to pan, scroll or use the keyboard to zoom" tabIndex={0}>
        <DeckGL
          views={new OrthographicView({ id: "ortho", flipY: false, controller: true })}
          initialViewState={initialViewState}
          controller={{ keyboard: true, scrollZoom: true, dragPan: true }}
          layers={layers}
          useDevicePixels={1}
          onLoad={() => {
            setLoaded(true);
            setReady(true);
            onReady?.();
          }}
          getCursor={() => "crosshair"}
          getTooltip={tooltip}
          onViewStateChange={({ viewState }: any) => setZoom(viewState.zoom)}
        />
      </div>
      <div className="map-overlay map-scale" aria-hidden="true">
        <span className="bar" style={{ width: `${bar.px.toFixed(0)}px` }} />
        <span>{bar.metres >= 1000 ? `${bar.metres / 1000} km` : `${bar.metres} m`}</span>
      </div>
      <div className="map-overlay map-north" aria-hidden="true">
        <svg width="16" height="22" viewBox="0 0 16 22"><path d="M8 1 L14 20 L8 15 L2 20 Z" fill="currentColor" /></svg>
        N
      </div>
      <div className="map-overlay map-legend">
        <ul className="map-key" aria-label="Map key">
          <li><span className="lg-route" aria-hidden="true" /> Selected route (the thread)</li>
          <li><span className="lg-station" aria-hidden="true" /> Station; numbered circle: transect</li>
          <li><span className="lg-relay" aria-hidden="true" /> Rover relay site (R1 to R3), PLACEHOLDER</li>
          <li><span className="lg-stage" aria-hidden="true" /> Staging point (rover), PLACEHOLDER</li>
        </ul>
      </div>
    </div>
  );
}
