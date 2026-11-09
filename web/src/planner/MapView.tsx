// Written with AI assistance (Claude Code). See AI_USE.md.
// The planner's 2D map: deck.gl OrthographicView in site metres (east, north), shifted to the
// site's south-west corner so float32 keeps centimetre precision.
import { OrthographicView } from "@deck.gl/core";
import { BitmapLayer, GeoJsonLayer, PathLayer, ScatterplotLayer } from "@deck.gl/layers";
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

// Okabe-Ito colors for the station roles; the legend below the map names them in text.
const ROLE_COLORS: Record<string, [number, number, number]> = {
  fracture: [0, 114, 178],
  crest: [0, 114, 178],
  wall: [204, 121, 167],
  hollow: [86, 180, 233],
};

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
      out.push(
        new PathLayer({
          id: "route",
          data: plan.legs,
          getPath: (l: any) => l.path_xy_m.map((p: XY) => local(p)),
          getColor: [0, 0, 0, 255],
          getWidth: 5,
          widthUnits: "pixels",
        }),
        new PathLayer({
          id: "route-core",
          data: plan.legs,
          getPath: (l: any) => l.path_xy_m.map((p: XY) => local(p)),
          getColor: [255, 255, 255, 255],
          getWidth: 2,
          widthUnits: "pixels",
        }),
        new ScatterplotLayer({
          id: "stations",
          data: plan.stations,
          getPosition: (s: any) => local(s.xy_m),
          getFillColor: (s: any) => ROLE_COLORS[s.role] ?? [255, 255, 255],
          getLineColor: [0, 0, 0],
          stroked: true,
          lineWidthMinPixels: 1.5,
          getRadius: 6,
          radiusUnits: "pixels",
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
      }),
    );
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manifest, base, layerState, plan, vectors, ox, oy, shown, detail]);

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
        />
      </div>
      <ul className="map-key">
        <li><span className="key-dot key-staging" aria-hidden="true" /> Staging point (rover), PLACEHOLDER</li>
        <li><span className="key-dot" style={{ background: "rgb(0,114,178)" }} aria-hidden="true" /> Fracture or crest station</li>
        <li><span className="key-dot" style={{ background: "rgb(204,121,167)" }} aria-hidden="true" /> Wall station</li>
        <li><span className="key-dot" style={{ background: "rgb(86,180,233)" }} aria-hidden="true" /> Hollow station</li>
        <li><span className="key-line" aria-hidden="true" /> Selected route (white line with a black edge)</li>
      </ul>
    </div>
  );
}
