// Written with AI assistance (Claude Code). See AI_USE.md.
// Controls for the simulated EVA shared by the HUD and the tablet: route, play, mission time,
// speed and the manual storm alert. They drive the one state store, so every surface agrees.
import { endTime } from "../core/eva/sim";
import { setEva, useEva } from "../core/eva/store";
import LabelBadge from "../planner/LabelBadge";
import { type Plan, PRESET_TITLES } from "../planner/types";

export function clock(min: number): string {
  const m = Math.max(0, Math.floor(min));
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}`;
}

const SPEEDS: [number, string][] = [
  [1 / 60, "real time"],
  [0.5, "30×"],
  [2, "120×"],
  [6, "360×"],
];

export default function EvaControls({ plans, idPrefix }: { plans: Record<string, Plan>; idPrefix: string }) {
  const eva = useEva();
  const plan = plans[eva.preset];
  const end = plan ? endTime(plan) : 0;
  return (
    <div className="eva-controls" role="group" aria-label="Simulated EVA">
      <label>
        Route{" "}
        <select value={eva.preset} onChange={(e) => setEva({ preset: e.target.value, t: Math.min(eva.t, endTime(plans[e.target.value])) })}>
          {Object.keys(plans).map((p) => (
            <option key={p} value={p}>
              {PRESET_TITLES[p] ?? p}
            </option>
          ))}
        </select>
      </label>
      <button type="button" aria-pressed={eva.playing} onClick={() => setEva((s) => ({ playing: !s.playing, t: s.t >= end ? 0 : s.t }))}>
        {eva.playing ? "Pause" : "Play"}
      </button>
      <label htmlFor={`${idPrefix}-time`}>
        Mission time {clock(eva.t)} of {clock(end)}
      </label>
      <input
        id={`${idPrefix}-time`}
        type="range"
        min={0}
        max={Math.ceil(end)}
        step={0.5}
        value={eva.t}
        onChange={(e) => setEva({ t: Number(e.target.value) })}
      />
      <label>
        Speed{" "}
        <select value={eva.speed} onChange={(e) => setEva({ speed: Number(e.target.value) })}>
          {SPEEDS.map(([v, name]) => (
            <option key={name} value={v}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <button type="button" aria-pressed={eva.storm} onClick={() => setEva((s) => ({ storm: !s.storm }))}>
        {eva.storm ? "End storm alert" : "Simulate a storm alert"}
      </button>
      <span className="note">
        Simulated from the plan <LabelBadge label="PLACEHOLDER" source="EVA simulated from the MODELED plan: walker positions, buddy lag and rover drives are not telemetry; the storm alert is manual until Phase 6 replays May 2024." />
      </span>
    </div>
  );
}
