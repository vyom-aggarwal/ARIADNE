// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D10: the TypeScript walker model reproduces the shared fixture written from the Python model.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  costOfTransport,
  extrapolationFlags,
  rateRatio,
  speed,
  suitFromConfig,
} from "../src/core/models/metabolic";

const root = resolve(__dirname, "..", "..");
const fixture = JSON.parse(readFileSync(resolve(root, "config/models/metabolic_fixture.json"), "utf8"));
const suits = JSON.parse(readFileSync(resolve(root, "config/suits.json"), "utf8"));
const suit = suitFromConfig(suits[fixture.suit]);

describe("walker model twin", () => {
  it("matches every row of the shared fixture", () => {
    expect(fixture.rows.length).toBeGreaterThan(20);
    for (const row of fixture.rows) {
      expect(costOfTransport(row.gradient)).toBeCloseTo(row.cw_j_kg_m, 9);
      expect(speed(row.gradient, suit)).toBeCloseTo(row.speed_m_s, 9);
      expect(rateRatio(row.gradient, suit)).toBeCloseTo(row.rate_ratio, 9);
    }
  });

  it("flags every Mars walk as extrapolated", () => {
    const flags = extrapolationFlags(0.1, 0.8, suit);
    expect(flags).toHaveLength(1);
    expect(flags[0]).toContain("gravity 0.38 g");
    expect(extrapolationFlags(-0.1, 0.8, suit).some((f) => f.includes("grade -10%"))).toBe(true);
  });
});
