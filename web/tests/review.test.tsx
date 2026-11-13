// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests E13 to E15 (team decisions of 2026-11-10): the price of safety in the route options, the
// assumptions panel with the conservative-slope site note, and the Validation tab.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AssumptionsPanel from "../src/planner/AssumptionsPanel";
import RouteOptions, { priceOfSafety } from "../src/planner/RouteOptions";
import type { Manifest, Plan, Validation } from "../src/planner/types";
import ValidationView, { resultFacts } from "../src/validation/ValidationView";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);
const validation: Validation = JSON.parse(readFileSync(resolve(site, "validation.json"), "utf8"));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("price of safety (E13)", () => {
  it("is Most science's value minus Safest's, and Safest's margin minus Most science's", () => {
    const p = priceOfSafety(plans)!;
    const a = plans.safest.totals;
    const b = plans.most_science.totals;
    expect(p.valueGivenUp).toBeCloseTo(b.science_value - a.science_value, 9);
    expect(p.marginGained).toBeCloseTo(a.min_thread_margin_min - b.min_thread_margin_min, 9);
    expect(p.transectsGivenUp).toBe(b.transects - a.transects);
  });

  it("is shown under the route options with its label", () => {
    render(<RouteOptions plans={plans} selected="balanced" onSelect={() => {}} />);
    const line = screen.getByTestId("price-of-safety");
    const p = priceOfSafety(plans)!;
    expect(line.textContent).toContain(p.valueGivenUp.toFixed(2));
    expect(line.textContent).toContain(p.marginGained.toFixed(1));
    expect(line.querySelector(".label-badge")?.textContent).toBe("MODELED");
  });

  it("says when Safest and Most science visit the same transects", () => {
    const same = { ...plans, safest: { ...plans.most_science, totals: { ...plans.most_science.totals } } };
    expect(priceOfSafety(same)!.sameTransects).toBe(true);
    render(<RouteOptions plans={same} selected="balanced" onSelect={() => {}} />);
    expect(screen.getByTestId("price-of-safety").textContent).toMatch(/same transects/);
  });
});

describe("assumptions panel (E14)", () => {
  it("lists every PLACEHOLDER setting and the conservative-slope note", () => {
    const items = manifest.assumptions ?? [];
    expect(items.length).toBeGreaterThan(20);
    expect(items.every((a) => a.label === "PLACEHOLDER")).toBe(true);
    const keys = items.map((a) => a.key);
    for (const k of ["shelter_max_min", "safest.shelter_max_min", "shelter_s", "storm_event_duration_min"]) {
      expect(keys).toContain(k);
    }
    render(<AssumptionsPanel items={items} notes={manifest.site_notes ?? []} />);
    const panel = screen.getByRole("region", { name: "Assumptions" });
    expect(panel.textContent).toMatch(/Slope no-go is conservative in boxwork terrain/);
    expect(panel.textContent).toMatch(/false alarms/);
    expect(within(panel).getAllByRole("table").length).toBeGreaterThan(3);
  });
});

describe("validation tab (E15)", () => {
  it("renders every check with its status in words and the site notes", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ json: async () => validation })));
    render(<ValidationView />);
    await waitFor(() => screen.getByText("Checks"));
    const items = screen.getAllByRole("listitem").filter((li) => li.classList.contains("check"));
    expect(items).toHaveLength(validation.checks.length);
    expect(screen.getAllByText("Fail").length).toBe(validation.checks.filter((c) => c.status === "fail").length);
    expect(document.body.textContent).toMatch(/Slope no-go is conservative in boxwork terrain/);
  });

  it("pulls only short plain facts out of a result", () => {
    expect(resultFacts({ points: 2893, share: { go: 0.3 }, go_or_caution: 0.7981, long: "x".repeat(200) }))
      .toEqual([["points", "2,893"], ["go or caution", "0.7981"]]);
  });
});
