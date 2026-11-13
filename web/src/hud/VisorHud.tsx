// Written with AI assistance (Claude Code). See AI_USE.md.
// The Visor HUD (PROMPT.md section 6): an overlay on the first-person view in a 1920 x 1080
// frame, driven by the simulated EVA. Voice commands where the browser supports them, and
// buttons for the same commands.
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { bearingDeg, distanceM, relativeBearing, snapshot } from "../core/eva/sim";
import { getEva, setEva, useEva } from "../core/eva/store";
import { type Command, listen, speak, speechSupported } from "../core/eva/voice";
import { refugeName } from "../core/plan/storm";
import { useSite } from "../core/site";
import EvaControls, { clock } from "../eva/EvaControls";
import LabelBadge from "../planner/LabelBadge";
import type { Plan } from "../planner/types";
import HudOverlay from "./HudOverlay";
import { hudElements } from "./model";

const Rehearsal = lazy(() => import("../rehearsal/Rehearsal"));

/** The spoken and shown answer to a command at plan time t (and the pin it drops). */
export function respond(plan: Plan, t: number, cmd: Command, pins: number): { text: string; pin?: [number, number] } {
  const s = snapshot(plan, t);
  if (cmd === "distance-home") {
    const d = Math.round(distanceM(s.ev1, s.rover.xy));
    const walk = s.minutesToRover !== null ? `${s.minutesToRover.toFixed(0)} minutes on foot, ` : "";
    return { text: `Rover ${walk}${d} metres. Thread margin ${s.marginMin.toFixed(0)} minutes.` };
  }
  if (cmd === "next-station") {
    if (!s.next) return { text: "All stations done. Head home to the rover." };
    const st = s.next.block.station;
    if (s.next.atStation) return { text: `At ${st.id}, the ${st.role} station, ${Math.max(0, s.next.block.end - t).toFixed(0)} minutes left.` };
    const rel = relativeBearing(bearingDeg(s.ev1, st.xy_m), s.heading);
    const side = Math.abs(rel) < 15 ? "ahead" : rel > 0 ? `${Math.round(rel)} degrees right` : `${Math.round(-rel)} degrees left`;
    return { text: `Next: ${st.id}, the ${st.role} station, ${Math.round(distanceM(s.ev1, st.xy_m))} metres, ${side}.` };
  }
  return { text: `Pin ${pins + 1} dropped at mission time ${clock(t)}.`, pin: s.ev1 };
}

export default function VisorHud({ site = "boxwork" }: { site?: string }) {
  const { site: data, error } = useSite(site);
  const eva = useEva();
  const plan = data?.plans[eva.preset] ?? null;
  const [listening, setListening] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.5);

  const snap = useMemo(() => (plan ? snapshot(plan, eva.t) : null), [plan, eva.t]);
  const elements = plan && snap ? hudElements(plan, snap, eva) : [];

  useEffect(() => {
    const el = frameRef.current;
    if (!el) return;
    const fit = () => setScale((el.clientWidth || 960) / 1920);
    fit();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(fit) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  }, [data]);

  useEffect(() => () => stopRef.current?.(), []);

  const run = (cmd: Command) => {
    const s = getEva();
    const p = data?.plans[s.preset];
    if (!p) return;
    const r = respond(p, s.t, cmd, s.pins.length);
    setEva((st) => ({
      said: r.text,
      pins: r.pin ? [...st.pins, { xy: r.pin, t: st.t, label: `Pin ${st.pins.length + 1}` }] : st.pins,
    }));
    speak(r.text);
  };

  const toggleVoice = () => {
    if (listening) {
      stopRef.current?.();
      stopRef.current = null;
      setListening(false);
      return;
    }
    const stop = listen(run, (heard) => setEva({ said: `Heard "${heard}": not a command.` }));
    if (stop) {
      stopRef.current = stop;
      setListening(true);
    }
  };

  const follow = () => (snap ? { xy: snap.ev1, heading: snap.heading } : null);
  const latest = useRef(follow);
  latest.current = follow;

  return (
    <section className="visor" aria-labelledby="visor-heading">
      <h2 id="visor-heading" className="planner-title">Visor HUD</h2>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading the site package…</p>}
      {data && plan && snap && (
        <>
          <EvaControls plans={data.plans} idPrefix="hud" />
          <div className="voice-controls" role="group" aria-label="Voice commands">
            <button type="button" onClick={() => run("distance-home")}>Distance home</button>
            <button type="button" onClick={() => run("next-station")}>Next station</button>
            <button type="button" onClick={() => run("drop-pin")}>Drop pin</button>
            {speechSupported() ? (
              <button type="button" aria-pressed={listening} onClick={toggleVoice}>
                {listening ? "Stop listening" : "Listen for voice commands"}
              </button>
            ) : (
              <span className="note">Voice commands need a browser with speech recognition; these buttons do the same.</span>
            )}
          </div>
          <div ref={frameRef} className="visor-frame" data-hud-count={elements.length}>
            <Suspense fallback={<div className="rehearsal-canvas embedded" aria-hidden="true" />}>
              <Rehearsal manifest={data.manifest} base={data.base} plan={plan} follow={() => latest.current()} embedded />
            </Suspense>
            <div className="hud-scaler" style={{ transform: `scale(${scale})` }}>
              <HudOverlay elements={elements} />
            </div>
          </div>
          <p className="note" role="status" aria-live="polite">
            {eva.said || `Mission time ${clock(eva.t)}.`}
          </p>
          <p className="note">
            The visor shows at most four elements, in white and cyan with dark outlines; each has its
            own shape. Values are MODELED from the plan and simulated <LabelBadge label="PLACEHOLDER" source="Simulated EVA; suit status is consumables left on the walker model." />.
            {eva.storm && snap.storm && ` Storm mode: ${refugeName(snap.storm.choice)}, dose ${snap.storm.dose.toFixed(0)} against ${snap.storm.dose_staying.toFixed(0)} open-sky minutes staying put over a ${plan.storm?.event_duration_min ?? 120}-minute event.`}{" "}
            {eva.storm && <LabelBadge label="MODELED" source="Storm mode by lowest modeled dose; event length and rover shielding are PLACEHOLDER." />}
          </p>
        </>
      )}
    </section>
  );
}
