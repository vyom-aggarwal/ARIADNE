// Written with AI assistance (Claude Code). See AI_USE.md.
// The printed cuff card (PROMPT.md section 6): one page with the route map, the stations with
// bearings and distances, landmark thumbnails, abort routes to the rover and the timeline. The
// print stylesheet (styles.css, @media print) keeps it to one landscape page; it is the backup
// if electronics fail, after the paper cuff checklists Apollo crews carried.
import { bearingDeg, blocks, distanceM, type XY } from "../core/eva/sim";
import { stormAt } from "../core/plan/storm";
import { setEva, useEva } from "../core/eva/store";
import { useSite } from "../core/site";
import { clock } from "../eva/EvaControls";
import { photoFor } from "../tablet/CuffTablet";
import { type Plan, PRESET_TITLES, type Manifest } from "../planner/types";

export interface CardRow {
  n: number;
  id: string;
  role: string;
  transect: string;
  bearing: number;
  distance: number;
  arrive: number;
  leave: number;
  relay: string;
  abortMin: number | null;
}

/** One row per station: bearing and straight-line distance from the previous point (the staging
 * point for the first), times, the rover's relay, and the walk to the rover from the station. */
export function cardRows(plan: Plan): CardRow[] {
  let prev: XY = plan.legs[0]?.path_xy_m[0] ?? plan.stations[0]?.xy_m ?? [0, 0];
  return blocks(plan).map((b, i) => {
    const xy = b.station.xy_m;
    const row: CardRow = {
      n: i + 1,
      id: b.station.id,
      role: b.station.role,
      transect: b.station.transect,
      bearing: Math.round(bearingDeg(prev, xy)),
      distance: Math.round(distanceM(prev, xy)),
      arrive: b.start,
      leave: b.end,
      relay: b.station.relay ?? "STAGING",
      abortMin: stormAt(plan.storm, b.start + 0.01)?.home_walk_min ?? null,
    };
    prev = xy;
    return row;
  });
}

/** Abort routes: the line home from each station (the storm sample in force at its arrival). */
export function abortRoutes(plan: Plan): XY[][] {
  const out: XY[][] = [];
  for (const b of blocks(plan)) {
    const s = stormAt(plan.storm, b.start + 0.01);
    if (s?.home_path_xy_m && s.home_path_xy_m.length > 1) out.push([b.station.xy_m, ...s.home_path_xy_m]);
  }
  return out;
}

function RouteMap({ plan }: { plan: Plan }) {
  const legs = plan.legs.map((l) => l.path_xy_m);
  const aborts = abortRoutes(plan);
  const relays = plan.rover?.relays ?? [];
  const pts: XY[] = [...legs.flat(), ...aborts.flat(), ...relays.map((r) => r.xy_m)];
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const W = 520;
  const H = 400;
  const k = Math.min((W - 40) / (x1 - x0 || 1), (H - 40) / (y1 - y0 || 1));
  const P = (p: XY) => [20 + (p[0] - x0) * k, H - 20 - (p[1] - y0) * k];
  const line = (path: XY[]) => path.map((p) => P(p).map((v) => v.toFixed(1)).join(",")).join(" ");
  const bar = 100; // metres
  return (
    <svg className="card-map" viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`Route map: ${plan.stations.length} stations, relay sites and abort routes to the rover`}>
      <rect x={0} y={0} width={W} height={H} fill="#fff" stroke="#000" />
      {aborts.map((a, i) => (
        <polyline key={`a${i}`} points={line(a)} fill="none" stroke="#000" strokeWidth={1.2} strokeDasharray="4 3" />
      ))}
      {legs.map((l, i) => (
        <polyline key={`l${i}`} points={line(l)} fill="none" stroke="#000" strokeWidth={2.4} />
      ))}
      {relays.map((r, i) => {
        const [x, y] = P(r.xy_m);
        return (
          <g key={r.id}>
            <rect x={x - 6} y={y - 6} width={12} height={12} fill="#fff" stroke="#000" strokeWidth={2} />
            <text x={x + 9} y={y + 4} fontSize={11} fontWeight={700}>{i === 0 ? "Rover start" : `R${i}`}</text>
          </g>
        );
      })}
      {plan.stations.map((s) => {
        // a transect's three stations lie within metres of each other: label the transect once
        const [x, y] = P(s.xy_m);
        return <circle key={s.id} cx={x} cy={y} r={3} fill="#000" />;
      })}
      {[...new Map(plan.stations.map((s) => [s.transect, s])).values()].map((s, k) => {
        // fan the labels out around their dots so that neighbouring transects stay readable
        const [x, y] = P(s.xy_m);
        const a = (k * 137.5 * Math.PI) / 180;
        const [lx, ly] = [x + 20 * Math.cos(a), y + 20 * Math.sin(a)];
        return (
          <g key={s.transect}>
            <line x1={x} y1={y} x2={lx} y2={ly} stroke="#000" strokeWidth={0.8} />
            <circle cx={lx} cy={ly} r={9} fill="#fff" stroke="#000" strokeWidth={1.5} />
            <text x={lx} y={ly + 3.5} fontSize={9} textAnchor="middle" fontWeight={700}>{s.transect.replace(/^T0?/, "")}</text>
          </g>
        );
      })}
      <g transform={`translate(${W - 34}, 34)`}>
        <path d="M 0 -18 L 7 6 L 0 1 L -7 6 Z" fill="#000" />
        <text y={20} fontSize={11} textAnchor="middle">N</text>
      </g>
      <g transform={`translate(20, ${H - 10})`}>
        <line x1={0} x2={bar * k} y1={0} y2={0} stroke="#000" strokeWidth={3} />
        <text x={bar * k + 6} y={4} fontSize={10}>{bar} m</text>
      </g>
    </svg>
  );
}

function MiniTimeline({ plan }: { plan: Plan }) {
  const end = plan.totals.minutes;
  const W = 520;
  const H = 54;
  const X = (t: number) => 10 + (t / end) * (W - 20);
  const m = plan.timeline.margin;
  const top = Math.max(...m.map((x) => x.margin_min), 1);
  const Y = (v: number) => 34 - (v / top) * 26;
  return (
    <svg className="card-timeline" viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`Timeline: ${plan.stations.length} station visits over ${Math.round(end)} minutes, with the margin above the reserve`}>
      {plan.timeline.stations.map((b, i) => (
        <rect key={i} x={X(b.start_min)} y={38} width={Math.max(1, X(b.end_min) - X(b.start_min))} height={10} fill="#000" />
      ))}
      <polyline points={m.map((x) => `${X(x.t_min).toFixed(1)},${Y(x.margin_min).toFixed(1)}`).join(" ")} fill="none" stroke="#000" strokeWidth={1.5} />
      {[0, 60, 120, 180, 240, 300, 360].filter((t) => t <= end).map((t) => (
        <text key={t} x={X(t)} y={H - 1} fontSize={8} textAnchor="middle">{clock(t)}</text>
      ))}
      <text x={10} y={8} fontSize={8}>Margin above reserve (line, max {Math.round(top)} min); station visits (bars)</text>
    </svg>
  );
}

export function Card({ manifest, base, plan, preset }: { manifest: Manifest; base: string; plan: Plan; preset: string }) {
  const rows = cardRows(plan);
  const photos = [...new Map(plan.stations.map((s) => [s.transect, photoFor(manifest, s)])).values()]
    .filter((p): p is NonNullable<typeof p> => p !== null)
    .filter((p, i, a) => a.findIndex((q) => q.imageid === p.imageid) === i)
    .slice(0, 3);
  return (
    <article className="cuff-card" aria-labelledby="card-title">
      <header className="card-head">
        <h3 id="card-title">ARIADNE cuff card · {manifest.title} · {PRESET_TITLES[preset] ?? preset} route</h3>
        <p>
          {plan.stations.length} stations, {Math.round(plan.totals.minutes)} min, {Math.round(plan.totals.distance_m)} m.
          Walk limit to the rover {plan.scenario.shelter_max_min} min, reserve {plan.scenario.reserve_min} min.
          Bearings are degrees from north, straight line from the previous point. MODELED on PLACEHOLDER settings; not mission guidance.
        </p>
      </header>
      <div className="card-body">
        <div className="card-left">
          <RouteMap plan={plan} />
          <p className="card-legend">Solid: route. Dashed: abort routes to the rover from each station. Squares: rover start and relay sites (R1 to R3). Dots: stations; numbered circles: transects (T01 to T{String(new Set(plan.stations.map((s) => s.transect)).size).padStart(2, "0")}).</p>
          <MiniTimeline plan={plan} />
        </div>
        <div className="card-right">
          <table className="card-table">
            <caption>Stations</caption>
            <thead>
              <tr>
                <th scope="col">#</th><th scope="col">Station</th><th scope="col">Role</th><th scope="col">Bearing</th>
                <th scope="col">Dist. (m)</th><th scope="col">Arrive</th><th scope="col">Leave</th><th scope="col">Rover at</th><th scope="col">Abort (min)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.n}</td><td>{r.id} ({r.transect})</td><td>{r.role}</td><td>{r.distance < 1 ? "–" : `${r.bearing}°`}</td><td>{r.distance}</td>
                  <td>{clock(r.arrive)}</td><td>{clock(r.leave)}</td><td>{r.relay === "STAGING" ? "start" : r.relay.replace("RELAY", "R")}</td>
                  <td>{r.abortMin === null ? "?" : r.abortMin.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {photos.length > 0 && (
            <div className="card-photos">
              {photos.map((p) => (
                <figure key={p.imageid}>
                  <div className="card-crop" style={{ aspectRatio: `1 / ${0.75 * p.show_top_fraction}` }}>
                    <img src={base + p.file} alt={`Landmark: Navcam view, sol ${p.sol}`} />
                  </div>
                  <figcaption>Navcam, sol {p.sol}, looking toward a planned transect</figcaption>
                </figure>
              ))}
            </div>
          )}
          <p className="card-credit">Photos courtesy NASA/JPL-Caltech. Storm: go to the rover unless it is out of reach; the HUD and tablet give the lowest-dose refuge.</p>
        </div>
      </div>
    </article>
  );
}

export default function CuffCard({ site = "boxwork" }: { site?: string }) {
  const { site: data, error } = useSite(site);
  const eva = useEva();
  const plan = data?.plans[eva.preset] ?? null;
  return (
    <section className="card-wrap" aria-labelledby="card-heading">
      <h2 id="card-heading" className="planner-title">Cuff card</h2>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading the site package…</p>}
      {data && plan && (
        <>
          <div className="card-controls" role="group" aria-label="Card">
            <label>
              Route{" "}
              <select value={eva.preset} onChange={(e) => setEva({ preset: e.target.value })}>
                {Object.keys(data.plans).map((p) => (
                  <option key={p} value={p}>{PRESET_TITLES[p] ?? p}</option>
                ))}
              </select>
            </label>
            <button type="button" onClick={() => window.print()}>Print the card</button>
            <span className="note">Prints on one landscape page.</span>
          </div>
          <Card manifest={data.manifest} base={data.base} plan={plan} preset={eva.preset} />
        </>
      )}
    </section>
  );
}
