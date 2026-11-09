// Written with AI assistance (Claude Code). See AI_USE.md.
// Test E10: the judge tour of the Habitat Planner. With ARIADNE_PERF=1 it runs on a mid-range
// laptop profile (1366 x 768, CPU slowed four times through the Chrome DevTools Protocol) and
// holds the first map to 5 s; results are recorded in docs/PROGRESS.md. CI runs the same tour as
// a functional check, because shared runners are slower and vary from run to run.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PERF = !!process.env.ARIADNE_PERF;

test.use({ viewport: { width: 1366, height: 768 } });

test("judge tour: map, layers, routes, timeline and 3D rehearsal", async ({ page }) => {
  test.setTimeout(300_000);
  if (PERF) {
    // warm the local preview server (not the browser's cache), as a CDN would be warm
    for (const path of ["./", "./sites/boxwork/manifest.json", "./sites/boxwork/layers/imagery_2m.png"])
      await page.request.get(path);
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  }
  const t0 = Date.now();
  await page.goto("./");
  await expect(page.getByRole("heading", { level: 2, name: /Habitat Planner/ })).toBeVisible();
  // the map is ready (deck.gl drawing) within the budget
  await expect(page.locator("[data-map-ready='true']")).toBeAttached({ timeout: PERF ? 5000 : 20000 });
  const firstMapMs = Date.now() - t0;
  await expect(page.locator(".map canvas").first()).toBeVisible();
  if (PERF) expect(firstMapMs).toBeLessThan(5000);
  console.log(`first map ${firstMapMs} ms${PERF ? " (4x CPU slowdown)" : ""}`);

  // layers toggle, with provenance in text
  const rover = page.getByRole("checkbox", { name: /Walkability, rover/ });
  await rover.check();
  await expect(rover).toBeChecked();
  await expect(page.getByTestId("layer-overcautious_walker")).toContainText("check by eye");

  // routes switch
  const safest = page.getByRole("button", { name: /Show Safest on the map/ });
  await safest.click();
  await expect(safest).toHaveAttribute("aria-pressed", "true");
  // the timeline shows the selected plan
  await expect(page.getByRole("img", { name: /^Timeline:/ })).toBeVisible();

  // no serious or critical accessibility problems on the planner
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const bad = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(bad.map((v) => `${v.id}: ${v.help}`)).toEqual([]);

  // the 3D rehearsal opens in orbit mode with the billboards, then walks on the ground
  await page.getByRole("button", { name: "3D rehearsal" }).click();
  const canvas = page.locator(".rehearsal-canvas");
  await expect(canvas).toHaveAttribute("data-status", "Ready", { timeout: 150000 });
  await expect(canvas.locator("canvas")).toBeVisible();
  expect(Number(await canvas.getAttribute("data-billboards"))).toBeGreaterThan(0);
  await page.getByRole("button", { name: "Ground" }).click();
  await expect(canvas).toHaveAttribute("data-mode", "ground");
  await page.getByRole("slider", { name: "Walking speed multiplier" }).fill("20");
  await page.getByRole("button", { name: /Pause walk/ }).click();
  await expect(page.getByRole("button", { name: /Resume walk/ })).toBeVisible();
  await page.getByRole("button", { name: "Orbit" }).click();
  await expect(canvas).toHaveAttribute("data-mode", "orbit");
});
