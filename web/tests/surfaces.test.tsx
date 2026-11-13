// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests G2, G6 and G8 on rendered components: the HUD overlay draws at most four elements; the
// tablet shows the next-station card, its photo with credit, the four steps and a working sample
// log; the card lists every station with bearings, distances and abort walks.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { abortRoutes, Card, cardRows } from "../src/card/CuffCard";
import { bearingDeg, blocks, distanceM, endTime, snapshot } from "../src/core/eva/sim";
import { resetEva, setEva } from "../src/core/eva/store";
import HudOverlay from "../src/hud/HudOverlay";
import { alertsFor, hudElements } from "../src/hud/model";
import type { Manifest, Plan } from "../src/planner/types";
import CuffTablet, { photoFor, STEPS, TabletAlerts } from "../src/tablet/CuffTablet";
import { sampleLog } from "../src/tablet/sampleLog";

const site = resolve(__dirname, "..", "public", "sites", "boxwork");
const manifest: Manifest = JSON.parse(readFileSync(resolve(site, "manifest.json"), "utf8"));
const plans: Record<string, Plan> = Object.fromEntries(
  manifest.plans.map((p) => [p.preset, JSON.parse(readFileSync(resolve(site, p.file), "utf8"))]),
);

beforeEach(() => {
  resetEva();
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const rel = String(url).split("sites/boxwork/")[1];
    return { json: async () => JSON.parse(readFileSync(resolve(site, rel), "utf8")) };
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("HUD overlay (G2)", () => {
  it("draws the elements it is given, never more than four, each with its shape", () => {
    const plan = plans.balanced;
    for (const t of [0, 40, 200, endTime(plan)]) {
      const els = hudElements(plan, snapshot(plan, t), { storm: true, pins: [{ xy: plan.margins[3].xy_m }] });
      const { container, unmount } = render(<HudOverlay elements={els} />);
      const drawn = container.querySelectorAll("[data-hud-element]");
      expect(drawn.length).toBe(els.length);
      expect(drawn.length).toBeLessThanOrEqual(4);
      drawn.forEach((d, i) => expect(d.getAttribute("data-shape")).toBe(els[i].shape));
      unmount();
    }
  });
});

describe("Cuff Tablet (G6)", () => {
  it("shows the next-station card with its photo, credit and the four steps", async () => {
    const plan = plans.balanced;
    const withPhoto = blocks(plan).find((b) => photoFor(manifest, b.station)) ?? blocks(plan)[0];
    act(() => setEva({ preset: "balanced", t: withPhoto.start + 1 }));
    render(<CuffTablet />);
    const card = await screen.findByRole("region", { name: `At ${withPhoto.station.id}` }, { timeout: 5000 });
    for (const s of STEPS) expect(within(card).getByRole("button", { name: new RegExp(s) })).toBeTruthy();
    const ph = photoFor(manifest, withPhoto.station);
    if (ph) {
      expect(within(card).getByRole("img", { name: /Navcam view toward transect/ })).toBeTruthy();
      expect(card.textContent).toContain("Courtesy NASA/JPL-Caltech");
    } else {
      expect(card.textContent).toContain("No Curiosity photo looks toward this transect");
    }
    const step = within(card).getByRole("button", { name: /Look/ });
    fireEvent.click(step);
    expect(step.getAttribute("aria-pressed")).toBe("true");
  });

  it("saves a sample with a photo to the local log and lists it", async () => {
    const plan = plans.safest;
    act(() => setEva({ preset: "safest", t: blocks(plan)[0].start + 2 }));
    render(<CuffTablet />);
    const log = await screen.findByRole("region", { name: "Sample log" }, { timeout: 5000 });
    fireEvent.change(within(log).getByLabelText("Note"), { target: { value: "Light-toned vein, 2 cm" } });
    const file = new File([new Uint8Array([1, 2, 3])], "vein.jpg", { type: "image/jpeg" });
    fireEvent.change(within(log).getByLabelText(/Add a photo/), { target: { files: [file] } });
    fireEvent.click(within(log).getByRole("button", { name: "Save sample" }));
    await waitFor(() => expect(within(log).getByRole("list", { name: "Saved samples" }).textContent).toContain("Light-toned vein"));
    const saved = await sampleLog().all();
    const mine = saved.find((e) => e.note === "Light-toned vein, 2 cm")!;
    expect(mine.station).toBe(plan.stations[0].id);
    expect(mine.photo).toBeInstanceOf(Blob);
  });

  it("shows the over-cautious marking exactly where the plan lists it (G5)", () => {
    const base = plans.most_science;
    const m = base.margins[25];
    const marked: Plan = { ...base, overcautious: { radius_m: 25, label: "MODELED", note: "",
      samples: [{ t_min: m.t_min, xy_m: m.xy_m, nearest_xy_m: m.xy_m, distance_m: 9 }] } };
    const at = (t: number) => {
      const { container, unmount } = render(<TabletAlerts alerts={alertsFor(marked, snapshot(marked, t), false)} />);
      const text = container.textContent ?? "";
      unmount();
      return text;
    };
    expect(at(m.t_min)).toContain("Note: Map may be over-cautious here, check by eye");
    expect(at(base.margins[24].t_min)).not.toMatch(/over-cautious/);
    // storm first, as a warning with its own shape
    const { container } = render(<TabletAlerts alerts={alertsFor(marked, snapshot(marked, m.t_min), true)} />);
    const items = container.querySelectorAll("[data-alert]");
    expect(items[0].getAttribute("data-alert")).toBe("storm");
    expect(items[0].textContent).toMatch(/^.Warning: Solar storm/);
  });
});

describe("Cuff card (G8)", () => {
  it.each(Object.keys(plans))("lists every %s station with bearing, distance and abort walk", (preset) => {
    const plan = plans[preset];
    const rows = cardRows(plan);
    expect(rows).toHaveLength(plan.stations.length);
    let prev = plan.legs[0].path_xy_m[0];
    rows.forEach((r, i) => {
      const xy = plan.stations[i].xy_m;
      expect(r.bearing).toBe(Math.round(bearingDeg(prev, xy)));
      expect(r.distance).toBe(Math.round(distanceM(prev, xy)));
      expect(r.abortMin).not.toBeNull();
      expect(r.abortMin!).toBeLessThanOrEqual(plan.scenario.shelter_max_min + 1e-6);
      prev = xy;
    });
    expect(abortRoutes(plan)).toHaveLength(plan.stations.length);
    render(<Card manifest={manifest} base="./" plan={plan} preset={preset} />);
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(plan.stations.length + 1);
    expect(screen.getByRole("img", { name: /Route map/ })).toBeTruthy();
    expect(screen.getByRole("img", { name: /Timeline/ })).toBeTruthy();
    expect(document.body.textContent).toContain("courtesy NASA/JPL-Caltech");
  });
});
