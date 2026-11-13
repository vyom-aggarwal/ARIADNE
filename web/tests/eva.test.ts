// Written with AI assistance (Claude Code). See AI_USE.md.
// Test G1: the EVA simulated from the committed plans.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  BUDDY_LAG_MIN,
  bearingDeg,
  blocks,
  buddyAt,
  distanceM,
  endTime,
  nextStation,
  positionAt,
  relativeBearing,
  roverAt,
  snapshot,
} from "../src/core/eva/sim";
import type { Manifest, Plan } from "../src/planner/types";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);

describe("bearing and distance", () => {
  it("are exact on synthetic points (x east, y north)", () => {
    expect(bearingDeg([0, 0], [0, 10])).toBeCloseTo(0);
    expect(bearingDeg([0, 0], [10, 0])).toBeCloseTo(90);
    expect(bearingDeg([0, 0], [0, -10])).toBeCloseTo(180);
    expect(bearingDeg([0, 0], [-10, 0])).toBeCloseTo(270);
    expect(bearingDeg([5, 5], [6, 6])).toBeCloseTo(45);
    expect(distanceM([1, 2], [4, 6])).toBeCloseTo(5);
    expect(relativeBearing(10, 350)).toBeCloseTo(20);
    expect(relativeBearing(350, 10)).toBeCloseTo(-20);
  });
});

describe.each(Object.keys(plans))("simulation of %s", (preset) => {
  const plan = plans[preset];

  it("follows the plan's walking samples", () => {
    for (const m of plan.margins) {
      if (m.station !== null && m.station !== undefined) continue;
      const p = positionAt(plan, m.t_min);
      expect(distanceM(p, m.xy_m)).toBeLessThan(5.01); // samples are at most 5 m apart
    }
    expect(positionAt(plan, 0)).toEqual(plan.margins[0].xy_m);
    expect(endTime(plan)).toBeCloseTo(plan.margins[plan.margins.length - 1].t_min);
  });

  it("holds EV1 at each station for its visit, with EV2 at the overwatch point", () => {
    for (const b of blocks(plan)) {
      for (const t of [b.start + 0.01, (b.start + b.end) / 2, b.end - 0.01]) {
        expect(distanceM(positionAt(plan, t), b.station.xy_m)).toBeLessThan(1e-6);
        expect(nextStation(plan, t)?.atStation).toBe(true);
        expect(buddyAt(plan, t)).toEqual(b.station.overwatch_xy_m);
      }
    }
  });

  it("walks EV2 just behind EV1 on legs", () => {
    const b = blocks(plan);
    const t = b.length ? b[0].start / 2 : 1;
    expect(buddyAt(plan, t)).toEqual(positionAt(plan, t - BUDDY_LAG_MIN));
  });

  it("moves the rover on its relay schedule and ends where the plan ends", () => {
    const rover = plan.rover!;
    const xy = (id: string) => rover.relays.find((r) => r.id === id)!.xy_m;
    expect(roverAt(plan, endTime(plan) + 1).xy).toEqual(xy(rover.ends_at));
    const bl = blocks(plan);
    for (const mv of rover.moves) {
      const start = mv.before_transect === 1 ? 0 : bl[3 * (mv.before_transect - 1) - 1].start;
      const mid = roverAt(plan, start + mv.drive_min / 2);
      expect(mid.moving).toBe(true);
      const after = roverAt(plan, start + mv.drive_min + 0.01);
      expect(after.xy).toEqual(rover.relays[mv.to_relay].xy_m);
      expect(after.moving).toBe(false);
    }
    if (rover.moves.length === 0) expect(roverAt(plan, 1).xy).toEqual(xy("STAGING"));
  });

  it("gives a full snapshot at any time", () => {
    for (let t = 0; t <= endTime(plan); t += 7) {
      const s = snapshot(plan, t);
      expect(Number.isFinite(s.marginMin)).toBe(true);
      expect(s.storm).not.toBeNull();
      if (s.minutesToRover !== null) expect(s.minutesToRover).toBeLessThanOrEqual(plan.scenario.shelter_max_min + 1e-6);
    }
  });
});
