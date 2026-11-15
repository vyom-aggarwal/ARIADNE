// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests H3 and H4: the May 20, 2024 storm replay raises the alert on cue, sends both crew along
// the storm path to the refuge, and scales modeled doses to RAD's measured figure.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { distanceM, microgray, positionAt, replaySnapshot, snapshot } from "../src/core/eva/sim";
import { evaView, replayDoses } from "../src/eva/replay";
import { hudElements } from "../src/hud/model";
import type { Manifest, Plan, Replay } from "../src/planner/types";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);
const replay: Replay = JSON.parse(readFileSync(resolve(site, manifest.replay!), "utf8"));
const eva = (preset: string, t: number, on = true) =>
  ({ preset, t, playing: false, speed: 1, storm: false, replay: on, pins: [], said: "" });

describe("replay data (H3)", () => {
  it("carries the event, RAD's dose with its meaning and source, and the light time", () => {
    expect(replay.event.onset_utc).toBe("2024-05-20T05:22Z");
    expect(replay.rad_dose_uGy.value).toBe(8100);
    expect(replay.rad_dose_uGy.label).toBe("MEASURED");
    expect(replay.rad_dose_uGy.meaning).toMatch(/astronaut standing next to Curiosity/);
    expect(replay.rad_dose_uGy.source).toMatch(/jpl\.nasa\.gov/);
    expect(replay.light_time_min.value).toBeGreaterThan(15);
    expect(replay.light_time_min.value).toBeLessThan(17);
    expect(replay.alignment.label).toBe("PLACEHOLDER");
  });

  it.each(Object.keys(plans))("starts the event mid-walk on a walking sample (%s)", (preset) => {
    const plan = plans[preset];
    const start = replay.alignment.start_min[preset];
    expect(Math.abs(start - plan.totals.minutes / 2)).toBeLessThan(plan.totals.minutes / 4);
    const sample = plan.margins.find((m) => Math.abs(m.t_min - start) < 0.01);
    expect(sample?.station ?? null).toBeNull();
  });
});

describe("replay simulation (H4)", () => {
  it.each(Object.keys(plans))("raises the alert exactly on cue in the HUD (%s)", (preset) => {
    const plan = plans[preset];
    const start = replay.alignment.start_min[preset];
    const before = evaView(plan, eva(preset, start - 0.1), replay);
    const after = evaView(plan, eva(preset, start + 0.1), replay);
    expect(before.stormOn).toBe(false);
    expect(after.stormOn).toBe(true);
    const kinds = (v: typeof before) => hudElements(plan, v.snap, { storm: v.stormOn, pins: [] }).map((e) => e.kind);
    expect(kinds(before)).not.toContain("storm");
    expect(kinds(after)).toContain("storm");
    expect(kinds(after).length).toBeLessThanOrEqual(4);
    // without the replay, nothing happens at that time
    expect(evaView(plan, eva(preset, start + 0.1, false), replay).stormOn).toBe(false);
  });

  it("walks both crew along the storm path to the refuge and shelters them on arrival", () => {
    const plan = plans.balanced;
    const start = replay.alignment.start_min.balanced;
    const s = snapshot(plan, start).storm!;
    expect(s.choice).toBe("rover");
    expect(replaySnapshot(plan, start - 1, start).ev1).toEqual(positionAt(plan, start - 1));
    const mid = replaySnapshot(plan, start + s.walk_min / 2, start);
    const end = replaySnapshot(plan, start + s.walk_min + 1, start);
    const refuge = s.path_xy_m[s.path_xy_m.length - 1];
    expect(distanceM(end.ev1, refuge)).toBeLessThan(0.01);
    expect(distanceM(mid.ev1, refuge)).toBeGreaterThan(0);
    expect(end.storm!.walk_min).toBe(0);
    const el = hudElements(plan, end, { storm: true, pins: [] }).find((e) => e.kind === "storm")!;
    expect(el.text).toMatch(/Sheltered/);
  });

  it("scales modeled doses so the whole open-sky event equals RAD's figure", () => {
    expect(microgray(120, 120, 8100)).toBeCloseTo(8100);
    expect(microgray(60, 120, 8100)).toBeCloseTo(4050);
    const plan = plans.safest;
    const d = replayDoses(plan, replay, replay.alignment.start_min.safest)!;
    expect(d.refuge).toBeLessThan(d.staying);
    expect(d.avoided).toBeCloseTo(d.staying - d.refuge, 0);
    expect(d.staying).toBeLessThanOrEqual(8100 + 1e-6); // S is at most 1
  });
});

describe("storm arrow along the path", () => {
  it("aims ahead of the walker along the path, never back at a passed vertex", async () => {
    const { steerPoint } = await import("../src/hud/model");
    const path: [number, number][] = [[0, 0], [0, 100], [100, 100]];
    expect(steerPoint(path, [0, 50])).toEqual([0, 65]); // 15 m further north
    expect(steerPoint(path, [1, 95])).toEqual([10, 100]); // round the corner
    expect(steerPoint(path, [99, 100])).toEqual([100, 100]); // the refuge itself when nearer
  });

  it("points the replay arrow roughly ahead while the crew walks to the rover", () => {
    const plan = plans.balanced;
    const start = replay.alignment.start_min.balanced;
    const s = snapshot(plan, start).storm!;
    for (const f of [0.2, 0.5, 0.8]) {
      const snap = replaySnapshot(plan, start + f * s.walk_min, start);
      const el = hudElements(plan, snap, { storm: true, pins: [] }).find((e) => e.kind === "storm")!;
      expect(Math.abs(el.arrowDeg!)).toBeLessThan(90);
    }
  });
});
