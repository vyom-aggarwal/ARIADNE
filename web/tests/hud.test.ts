// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests G2, G3 and G5: the HUD shows at most four elements in every state, in priority order,
// in white and cyan with a shape for each element, visible to colorblind viewers on any ground.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { bearingDeg, endTime, relativeBearing, snapshot } from "../src/core/eva/sim";
import {
  contrast,
  type Deficiency,
  HUD,
  hexToRgb,
  isRedOrOrange,
  luminance,
  MACHADO_2009,
  simulate,
  visibleOnGround,
} from "../src/hud/colors";
import { ALERT_SHAPES, alertsFor, hudElements, LOW_MARGIN_MIN, steerPoint } from "../src/hud/model";
import type { Manifest, Plan } from "../src/planner/types";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);

/** The same plan with every sample marked over-cautious (no committed route passes near one). */
function allOvercautious(plan: Plan): Plan {
  return {
    ...plan,
    overcautious: {
      radius_m: 25, label: "MODELED", note: "",
      samples: plan.margins.map((m) => ({ t_min: m.t_min, xy_m: m.xy_m, nearest_xy_m: m.xy_m, distance_m: 10 })),
    },
  };
}

const KIND_SHAPES: Record<string, string[]> = {
  next: ["chevron", "ring"],
  storm: ["double-chevron"],
  thread: ["polyline"],
  buddy: ["diamond"],
  alert: Object.values(ALERT_SHAPES),
};

describe("HUD elements (G2)", () => {
  it.each(Object.keys(plans))("never shows more than four, in every state of %s", (preset) => {
    const variants = [plans[preset], allOvercautious(plans[preset])];
    const pinSets = [[], [{ xy: plans[preset].margins[0].xy_m }, { xy: plans[preset].margins[9].xy_m }]];
    let states = 0;
    for (const plan of variants) {
      for (let t = 0; t <= endTime(plan) + 1; t += 1) {
        const snap = snapshot(plan, t);
        for (const storm of [false, true]) {
          for (const pins of pinSets) {
            const els = hudElements(plan, snap, { storm, pins });
            expect(els.length).toBeLessThanOrEqual(4);
            expect(new Set(els.map((e) => e.slot)).size).toBe(els.length); // one per slot
            for (const e of els) {
              expect(KIND_SHAPES[e.kind]).toContain(e.shape);
              expect(["white", "cyan"]).toContain(e.color);
            }
            states++;
          }
        }
      }
    }
    expect(states).toBeGreaterThan(1000);
  });

  it("puts alerts in priority order and counts the rest", () => {
    const plan = allOvercautious(plans.balanced);
    const snap = { ...snapshot(plan, 30), marginMin: LOW_MARGIN_MIN - 1 };
    const alerts = alertsFor(plan, snap, true);
    expect(alerts.map((a) => a.id).slice(0, 2)).toEqual(["storm", "low-margin"]);
    expect(alerts.at(-1)!.id).toBe("overcautious");
    const top = hudElements(plan, snap, { storm: true, pins: [] }).find((e) => e.kind === "alert")!;
    expect(top.shape).toBe("octagon");
    expect(top.more).toBe(alerts.length - 1);
  });

  it("shows the over-cautious marking exactly at the listed samples (G5)", () => {
    const base = plans.safest;
    const listed = base.margins[40];
    const plan: Plan = { ...base, overcautious: { radius_m: 25, label: "MODELED", note: "",
      samples: [{ t_min: listed.t_min, xy_m: listed.xy_m, nearest_xy_m: listed.xy_m, distance_m: 12 }] } };
    const text = (t: number) => hudElements(plan, snapshot(plan, t), { storm: false, pins: [] })
      .find((e) => e.kind === "alert")?.text ?? "";
    expect(text(listed.t_min)).toBe("Map may be over-cautious here, check by eye");
    expect(text(base.margins[39].t_min)).not.toMatch(/over-cautious/);
    expect(text(base.margins[41].t_min)).not.toMatch(/over-cautious/);
    // the committed plans pass no closer than 25 m to any flagged cell, so they list none
    for (const p of Object.values(plans)) expect(p.overcautious?.samples).toEqual([]);
  });

  it("points the storm arrow along the path to the lowest-dose refuge", () => {
    const plan = plans.balanced;
    let checked = 0;
    for (let t = 2; t < endTime(plan); t += 11) {
      const snap = snapshot(plan, t);
      const el = hudElements(plan, snap, { storm: true, pins: [] }).find((e) => e.kind === "storm")!;
      expect(el).toBeTruthy();
      if (snap.storm!.choice === "stay") continue;
      const target = steerPoint(snap.storm!.path_xy_m, snap.ev1)!;
      expect(el.arrowDeg).toBeCloseTo(relativeBearing(bearingDeg(snap.ev1, target), snap.heading), 6);
      expect(el.text).toMatch(/the rover|terrain shielding/i);
      checked++;
    }
    expect(checked).toBeGreaterThan(10);
  });
});

describe("HUD colors (G3)", () => {
  const colors = { white: hexToRgb(HUD.white), cyan: hexToRgb(HUD.cyan) };
  const outline = hexToRgb(HUD.outline);
  const kinds = Object.keys(MACHADO_2009) as Deficiency[];

  it("uses white and cyan only, never red or orange", () => {
    for (const c of Object.values(colors)) expect(isRedOrOrange(c)).toBe(false);
    expect(isRedOrOrange([1, 0, 0])).toBe(true); // the check itself catches red
    expect(isRedOrOrange([1, 0.55, 0])).toBe(true); // and orange
  });

  it("gives every element type its own shape", () => {
    const all = Object.values(KIND_SHAPES).flat();
    expect(new Set(all).size).toBe(all.length);
  });

  it("keeps 3:1 against the outline and on any ground, with normal and deficient color vision", () => {
    const grounds = Array.from({ length: 101 }, (_, i) => i / 100);
    const tone = manifest.ground_tone!;
    expect(tone.label).toBe("DERIVED");
    for (const g of [tone.p01, tone.p50, tone.p99]) grounds.push(g);
    for (const space of ["linear", "gamma"] as const) {
      for (const [name, c] of Object.entries(colors)) {
        const seen = [c, ...kinds.map((k) => simulate(c, k, space))];
        const ol = [outline, ...kinds.map((k) => simulate(outline, k, space))];
        seen.forEach((s, i) => {
          expect(contrast(luminance(s), luminance(ol[i])), `${name} ${space} ${i}`).toBeGreaterThanOrEqual(3);
          for (const g of grounds) expect(visibleOnGround(s, ol[i], g), `${name} on ${g}`).toBe(true);
        });
      }
    }
  });

  it("matches the published matrices (Machado et al. 2009, severity 1.0)", () => {
    expect(MACHADO_2009.protan[0]).toEqual([0.152286, 1.052583, -0.204868]);
    expect(MACHADO_2009.deutan[1]).toEqual([0.280085, 0.672501, 0.047413]);
    expect(MACHADO_2009.tritan[2]).toEqual([0.004733, 0.691367, 0.3039]);
    // white stays white: each row sums to 1
    for (const k of kinds) for (const row of MACHADO_2009[k]) expect((row as readonly number[]).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 5);
  });
});
