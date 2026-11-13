// Written with AI assistance (Claude Code). See AI_USE.md.
// The Cuff Tablet (PROMPT.md section 6), in a 1024 x 768 frame: controls of at least 64 CSS px
// (PLACEHOLDER for gloved use), the next-station card with a "what you'll see" photo, station
// steps from the team brief (Look, Observe, Describe, Document; PROMPT.md section 6 attributes
// them to NASA SUITS, not yet confirmed in a SUITS document), alerts with the over-cautious marking,
// the line home, and a sample log kept in this browser.
import { useEffect, useMemo, useState } from "react";
import { bearingDeg, distanceM, snapshot } from "../core/eva/sim";
import { useEva } from "../core/eva/store";
import { useSite } from "../core/site";
import EvaControls, { clock } from "../eva/EvaControls";
import { type Alert, alertsFor } from "../hud/model";
import LabelBadge from "../planner/LabelBadge";
import type { Manifest, Photo, Plan, Station } from "../planner/types";
import { newId, type SampleEntry, sampleLog } from "./sampleLog";

export const STEPS = ["Look", "Observe", "Describe", "Document"] as const;
const STEP_HELP: Record<(typeof STEPS)[number], string> = {
  Look: "Find the station marker and the ridge, wall or hollow around it.",
  Observe: "Note texture, color, veins and fractures at arm's length.",
  Describe: "Say what you see for the log and the science team.",
  Document: "Take the photo and log the sample below.",
};

/** A Curiosity Navcam frame looking toward this station's transect, if one was found. */
export function photoFor(manifest: Manifest, st: Station | undefined): Photo | null {
  if (!st || st.transect_source_id === undefined) return null;
  return manifest.photos.find((p) => p.transect_source_id === st.transect_source_id) ?? null;
}

/** The line home: the fastest walk to where the rover parks next, from the plan's storm samples. */
export function LineHome({ path, ev1 }: { path: [number, number][]; ev1: [number, number] }) {
  const pts = [ev1, ...path];
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const span = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 40);
  const W = 240;
  const H = 150;
  const k = Math.min((W - 24) / span, (H - 24) / span);
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2;
  const cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  const P = (p: [number, number]) => [W / 2 + (p[0] - cx) * k, H / 2 - (p[1] - cy) * k];
  const end = P(pts[pts.length - 1]);
  const me = P(ev1);
  return (
    <svg className="line-home" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Line home to the rover">
      <polyline points={pts.map((p) => P(p).join(",")).join(" ")} fill="none" stroke="currentColor" strokeWidth={4} strokeDasharray="8 5" />
      <rect x={end[0] - 7} y={end[1] - 7} width={14} height={14} fill="currentColor" />
      <circle cx={me[0]} cy={me[1]} r={7} fill="none" stroke="currentColor" strokeWidth={3} />
    </svg>
  );
}

const ALERT_MARK: Record<string, string> = { octagon: "⯃", triangle: "▲", "hatched-square": "▨", circle: "◯" };

/** The same alerts as the HUD, each with its shape and level in words. */
export function TabletAlerts({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) return null;
  return (
    <ul className="tablet-alerts" aria-label="Alerts">
      {alerts.map((a) => (
        <li key={a.id} className={`tablet-alert alert-${a.level}`} data-alert={a.id}>
          <span className="alert-shape" aria-hidden="true">{ALERT_MARK[a.shape] ?? "◯"}</span>
          {a.level === "warning" ? "Warning: " : a.level === "caution" ? "Caution: " : "Note: "}
          {a.text}
        </li>
      ))}
    </ul>
  );
}

function Steps({ station }: { station: Station }) {
  const [done, setDone] = useState<Record<string, boolean>>({});
  useEffect(() => setDone({}), [station.id]);
  return (
    <ol className="tablet-steps">
      {STEPS.map((s) => (
        <li key={s}>
          <button type="button" aria-pressed={!!done[s]} onClick={() => setDone((d) => ({ ...d, [s]: !d[s] }))}>
            <span aria-hidden="true">{done[s] ? "✓ " : "○ "}</span>
            {s}
          </button>
          <span className="step-help">{STEP_HELP[s]}</span>
        </li>
      ))}
    </ol>
  );
}

function SampleLogPanel({ plan, station, t, preset }: { plan: Plan; station: Station | null; t: number; preset: string }) {
  const [entries, setEntries] = useState<SampleEntry[]>([]);
  const [note, setNote] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const log = sampleLog();
  const refresh = () => log.all().then(setEntries).catch(() => setEntries([]));
  useEffect(() => {
    refresh();
  }, []);
  useEffect(() => {
    const made: Record<string, string> = {};
    for (const e of entries) if (e.photo && typeof URL.createObjectURL === "function") made[e.id] = URL.createObjectURL(e.photo);
    setUrls(made);
    return () => Object.values(made).forEach((u) => URL.revokeObjectURL(u));
  }, [entries]);
  const save = async () => {
    await log.add({ id: newId(), created_utc: new Date().toISOString(), mission_min: t,
      station: station?.id ?? null, preset, note: note.trim(), photo });
    setNote("");
    setPhoto(null);
    refresh();
  };
  return (
    <section className="tablet-card" aria-labelledby="log-heading">
      <h3 id="log-heading">Sample log</h3>
      <p className="note">Stored only in this browser; it works offline. Station {station?.id ?? "none"}, mission time {clock(t)}.</p>
      <label className="tablet-field">
        Note
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
      </label>
      <label className="tablet-file">
        {photo ? `Photo: ${photo.name}` : "Add a photo"}
        <input type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
      </label>
      <button type="button" onClick={save} disabled={!note.trim() && !photo}>Save sample</button>
      <ul className="sample-list" aria-label="Saved samples">
        {entries.map((e) => (
          <li key={e.id} data-sample={e.id}>
            {urls[e.id] && <img src={urls[e.id]} alt={`Sample photo at ${e.station ?? "no station"}`} />}
            <span>{e.station ?? "No station"} · {clock(e.mission_min)} · {e.note || "(no note)"}</span>
            <button type="button" onClick={() => log.remove(e.id).then(refresh)} aria-label={`Delete sample ${e.station ?? ""} at ${clock(e.mission_min)}`}>Delete</button>
          </li>
        ))}
      </ul>
      <span className="visually-hidden">{plan.site}</span>
    </section>
  );
}

export default function CuffTablet({ site = "boxwork" }: { site?: string }) {
  const { site: data, error } = useSite(site);
  const eva = useEva();
  const plan = data?.plans[eva.preset] ?? null;
  const snap = useMemo(() => (plan ? snapshot(plan, eva.t) : null), [plan, eva.t]);
  return (
    <section className="tablet-wrap" aria-labelledby="tablet-heading">
      <h2 id="tablet-heading" className="planner-title">Cuff Tablet</h2>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading the site package…</p>}
      {data && plan && snap && (() => {
        const st = snap.next?.block.station;
        const ph = photoFor(data.manifest, st);
        const alerts = alertsFor(plan, snap, eva.storm);
        return (
          <>
            <EvaControls plans={data.plans} idPrefix="tablet" />
            <div className="tablet" data-testid="tablet">
              <header className="tablet-bar">
                <span>{clock(eva.t)} elapsed</span>
                <span>Margin {snap.marginMin.toFixed(0)} min <LabelBadge label="MODELED" source="Thread margin above the reserve, from the plan" /></span>
                <span>Rover {snap.minutesToRover?.toFixed(0) ?? "?"} min on foot <LabelBadge label="MODELED" source="Walking minutes to the rover wherever it is (walker model, PLACEHOLDER suit)" /></span>
              </header>
              <TabletAlerts alerts={alerts} />
              <div className="tablet-grid">
                <section className="tablet-card" aria-labelledby="next-heading">
                  <h3 id="next-heading">{st ? (snap.next!.atStation ? `At ${st.id}` : `Next: ${st.id}`) : "All stations done"}</h3>
                  {st ? (
                    <>
                      <p>
                        {snap.next!.atStation || distanceM(snap.ev1, st.xy_m) < 1 ? (
                          <>You are at the {st.role} station of transect {st.transect}, {Math.max(0, snap.next!.block.end - eva.t).toFixed(0)} min left here.</>
                        ) : (
                          <>
                            The {st.role} station of transect {st.transect}, {Math.round(distanceM(snap.ev1, st.xy_m))} m at{" "}
                            {Math.round(bearingDeg(snap.ev1, st.xy_m))}° from north.
                          </>
                        )}{" "}
                        <LabelBadge label="MODELED" source="Station from the plan; bearing clockwise from north" />
                      </p>
                      <figure className="see-photo">
                        {ph ? (
                          <>
                            <div className="see-crop" style={{ aspectRatio: `1 / ${0.75 * ph.show_top_fraction}` }}>
                              <img src={data.base + ph.file} alt={`Curiosity Navcam view toward transect ${st.transect}, sol ${ph.sol}`} />
                            </div>
                            <figcaption>
                              What you'll see: Navcam, sol {ph.sol}, from Curiosity's path toward this transect. Courtesy NASA/JPL-Caltech. <LabelBadge label="MEASURED" source={`Raw image ${ph.imageid}`} />
                            </figcaption>
                          </>
                        ) : (
                          <figcaption>No Curiosity photo looks toward this transect.</figcaption>
                        )}
                      </figure>
                      <Steps station={st} />
                    </>
                  ) : (
                    <p>Head home to the rover.</p>
                  )}
                </section>
                <div className="tablet-side">
                  {snap.storm?.home_path_xy_m && (
                    <section className="tablet-card" aria-labelledby="home-heading">
                      <h3 id="home-heading">Line home</h3>
                      <figure className="tablet-home">
                        <LineHome path={snap.storm.home_path_xy_m} ev1={snap.ev1} />
                        <figcaption>
                          The circle is you, the square the rover: {snap.storm.home_walk_min?.toFixed(0)} min on foot from the last check point{" "}
                          <LabelBadge label="MODELED" source="Fastest walk to where the rover parks next (walker model)" />
                        </figcaption>
                      </figure>
                    </section>
                  )}
                  <SampleLogPanel plan={plan} station={snap.next?.atStation ? st ?? null : null} t={eva.t} preset={eva.preset} />
                </div>
              </div>
            </div>
          </>
        );
      })()}
    </section>
  );
}
