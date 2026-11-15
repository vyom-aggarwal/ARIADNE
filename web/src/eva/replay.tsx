// Written with AI assistance (Claude Code). See AI_USE.md.
// The May 20, 2024 storm replay (PROMPT.md section 7): the alert comes on cue where the event
// starts in the walk, storm mode takes over, and the panel sets the dose JPL reports from
// Curiosity's RAD beside the modeled doses with and without the refuge.
import { type EvaSnapshot, microgray, replaySnapshot, snapshot } from "../core/eva/sim";
import { type EvaState, setEva } from "../core/eva/store";
import { refugeName } from "../core/plan/storm";
import LabelBadge from "../planner/LabelBadge";
import type { Plan, Replay } from "../planner/types";
import { clock } from "./EvaControls";

export interface EvaView {
  snap: EvaSnapshot;
  stormOn: boolean;
  alertMin: number | null;
}

/** What every surface shows at the store's time: the plan, or the replay once it is running. */
export function evaView(plan: Plan, eva: EvaState, replay: Replay | null): EvaView {
  if (eva.replay && replay) {
    const alertMin = replay.alignment.start_min[eva.preset] ?? plan.totals.minutes / 2;
    return { snap: replaySnapshot(plan, eva.t, alertMin), stormOn: eva.storm || eva.t >= alertMin, alertMin };
  }
  return { snap: snapshot(plan, eva.t), stormOn: eva.storm, alertMin: null };
}

export function startReplay(replay: Replay, preset: string) {
  const start = replay.alignment.start_min[preset] ?? 0;
  setEva({ replay: true, storm: false, t: Math.max(0, start - 3), playing: true, speed: 0.5, said: "" });
}

export function ReplayButton({ replay, eva }: { replay: Replay | null; eva: EvaState }) {
  if (!replay) return null;
  return eva.replay ? (
    <button type="button" aria-pressed="true" onClick={() => setEva({ replay: false, playing: false })}>
      End the storm replay
    </button>
  ) : (
    <button type="button" aria-pressed="false" onClick={() => startReplay(replay, eva.preset)}>
      Replay the May 20, 2024 storm
    </button>
  );
}

/** Modeled doses at the alert, in micrograys: staying put in the open, the chosen refuge, and the
 * difference (MODELED, scaled to RAD's figure; see Replay.dose_scaling). */
export function replayDoses(plan: Plan, replay: Replay, alertMin: number) {
  const s = snapshot(plan, alertMin).storm;
  const D = plan.storm?.event_duration_min ?? 120;
  if (!s) return null;
  const ref = replay.rad_dose_uGy.value;
  return {
    choice: s.choice,
    walkMin: s.walk_min,
    staying: microgray(s.dose_staying, D, ref),
    refuge: microgray(s.dose, D, ref),
    avoided: microgray(s.dose_avoided, D, ref),
    eventMin: D,
  };
}

export function ReplayPanel({ plan, replay, eva, view }: { plan: Plan; replay: Replay; eva: EvaState; view: EvaView }) {
  if (!eva.replay || view.alertMin === null) return null;
  const doses = replayDoses(plan, replay, view.alertMin);
  const before = eva.t < view.alertMin;
  const fmt = (v: number) => Math.round(v).toLocaleString("en-US");
  return (
    <section className="replay-panel" aria-labelledby="replay-heading" data-replay-phase={before ? "before" : "after"}>
      <h3 id="replay-heading">Storm replay: {replay.title}</h3>
      <p>
        A far-side eruption: DONKI logs an EUV wave at 05:22 UTC and a halo CME at{" "}
        {replay.event.cme.speed_km_s?.toLocaleString("en-US")} km/s{" "}
        <LabelBadge label={replay.event.label} source={replay.event.source} />; the flare was later estimated at{" "}
        {replay.flare.value} <LabelBadge label={replay.flare.label} source={replay.flare.source} />.{" "}
        {replay.arrival.text} <LabelBadge label={replay.arrival.label} source={replay.arrival.source} /> Earth was{" "}
        {replay.light_time_min.value.toFixed(1)} light-minutes away{" "}
        <LabelBadge label={replay.light_time_min.label} source={replay.light_time_min.source} />, so a warning from
        Earth would come after the particles: the crew acts on the alarm where they are.
      </p>
      <p>
        {before
          ? `The event begins at mission time ${clock(view.alertMin)} (in ${Math.max(0, view.alertMin - eva.t).toFixed(1)} min).`
          : `Alert at ${clock(view.alertMin)}: storm mode. ${doses && doses.choice !== "stay" ? `Both crew head for ${refugeName(doses.choice)} (${doses.walkMin.toFixed(0)} min on foot).` : ""}`}{" "}
        <LabelBadge label={replay.alignment.label} source={`Replay alignment: ${replay.alignment.rule}`} />
      </p>
      <dl className="replay-doses">
        <div>
          <dt>Curiosity's RAD, the whole event</dt>
          <dd>
            {fmt(replay.rad_dose_uGy.value)} µGy{" "}
            <LabelBadge label={replay.rad_dose_uGy.label} source={`${replay.rad_dose_uGy.meaning}. ${replay.rad_dose_uGy.source}`} />
          </dd>
        </div>
        {doses && (
          <>
            <div>
              <dt>EV1 staying put in the open</dt>
              <dd>{fmt(doses.staying)} µGy <LabelBadge label="MODELED" source={replay.dose_scaling.text} /></dd>
            </div>
            <div>
              <dt>EV1 going to {refugeName(doses.choice)}</dt>
              <dd>{fmt(doses.refuge)} µGy <LabelBadge label="MODELED" source={replay.dose_scaling.text} /></dd>
            </div>
            <div>
              <dt>Avoided</dt>
              <dd>{fmt(doses.avoided)} µGy <LabelBadge label="MODELED" source={`${replay.dose_scaling.text} Rover shielding S is a PLACEHOLDER.`} /></dd>
            </div>
          </>
        )}
      </dl>
      <p className="note">
        {replay.dose_scaling.text} Event length {doses?.eventMin ?? 120} min <LabelBadge label="PLACEHOLDER" source="JPL gives no duration; the event length is a team placeholder." />.{" "}
        {replay.donki.disclaimer}
      </p>
    </section>
  );
}
