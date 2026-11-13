// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests E6 to E8: layer panel, route options and timeline, on the packaged boxwork site.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import LayerPanel from "../src/planner/LayerPanel";
import RouteOptions from "../src/planner/RouteOptions";
import Timeline from "../src/planner/Timeline";
import type { Manifest, Plan } from "../src/planner/types";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);

afterEach(cleanup);

describe("layer panel (E6)", () => {
  it("shows each layer's source, resolution, date and label", () => {
    render(<LayerPanel layers={manifest.layers} state={{}} onChange={() => {}} />);
    for (const lay of manifest.layers) {
      const item = screen.getByTestId(`layer-${lay.id}`);
      expect(within(item).getByText(lay.title)).toBeTruthy();
      expect(item.textContent).toContain(lay.label);
      expect(item.textContent).toContain(lay.date);
      if (lay.resolution_m) expect(item.textContent).toMatch(new RegExp(`${lay.resolution_m} m`));
      expect(item.querySelector("[title]")?.getAttribute("title")).toContain(lay.sources[0]);
    }
  });

  it("toggles and fades layers with labelled controls", () => {
    const changes: [string, object][] = [];
    render(
      <LayerPanel
        layers={manifest.layers}
        state={{}}
        onChange={(id, s) => changes.push([id, s])}
      />,
    );
    const box = screen.getByRole("checkbox", { name: /Walkability, rover/ });
    fireEvent.click(box);
    expect(changes.at(-1)).toEqual(["walk_rover", { visible: true }]);
    const slider = screen.getByRole("slider", { name: /Opacity of Walkability, rover/ });
    fireEvent.change(slider, { target: { value: "40" } });
    expect(changes.at(-1)).toEqual(["walk_rover", { opacity: 0.4 }]);
  });

  it("describes the over-cautious hatching in words", () => {
    render(<LayerPanel layers={manifest.layers} state={{}} onChange={() => {}} />);
    expect(screen.getByTestId("layer-overcautious_walker").textContent).toMatch(/check by eye/);
  });
});

describe("route options (E7)", () => {
  it("shows the eight figures for each preset, each with its label", () => {
    render(<RouteOptions plans={plans} selected="balanced" onSelect={() => {}} />);
    const table = screen.getByRole("table", { name: /route options/i });
    const rows = within(table).getAllByRole("row");
    const names = rows.slice(1).map((r) => r.querySelector("th")?.textContent ?? "");
    for (const m of ["Duration", "Distance", "Consumables used", "Least margin",
      "Worst walk to the rover", "Relative dose", "Stations", "Science value"]) {
      expect(names.some((n) => n.startsWith(m))).toBe(true);
    }
    for (const row of rows.slice(1)) {
      const cells = row.querySelectorAll("td");
      expect(cells).toHaveLength(3);
      cells.forEach((td) => expect(td.querySelector(".label-badge")).toBeTruthy());
    }
    expect(table.textContent).toContain(plans.balanced.totals.minutes.toFixed(0));
  });

  it("selects a preset from the keyboard-reachable buttons", () => {
    const picked: string[] = [];
    render(<RouteOptions plans={plans} selected="balanced" onSelect={(p) => picked.push(p)} />);
    fireEvent.click(screen.getByRole("button", { name: /Show Safest/ }));
    expect(picked).toEqual(["safest"]);
    expect(screen.getByRole("button", { name: /Show Balanced/ }).getAttribute("aria-pressed")).toBe("true");
  });
});

describe("timeline (E8)", () => {
  it("draws the margin, station blocks, sun elevation and comm shadows", () => {
    const plan = plans.balanced;
    const { container } = render(<Timeline plan={plan} />);
    const svg = screen.getByRole("img", { name: /timeline/i });
    expect(svg).toBeTruthy();
    expect(container.querySelector("[data-series='margin']")).toBeTruthy();
    expect(container.querySelector("[data-series='sun']")).toBeTruthy();
    expect(container.querySelectorAll("[data-station]")).toHaveLength(plan.timeline.stations.length);
    expect(container.querySelectorAll("[data-shadow]")).toHaveLength(plan.timeline.comm_shadows.length);
    expect(container.textContent).toMatch(/MODELED/);
    // a text summary for screen readers, with the least margin
    const least = Math.min(...plan.timeline.margin.map((m) => m.margin_min));
    expect(container.textContent).toContain(least.toFixed(0));
  });
});
