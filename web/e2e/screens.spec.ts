// Written with AI assistance (Claude Code). See AI_USE.md.
// Layout checks for the redesign. Always on: no horizontal scroll on any surface at 1280, 1366,
// 1440, 1920 and 390 px. With ARIADNE_SCREENS=1: screenshots of every surface at 1440 x 900,
// 1366 x 768 and 390 x 844, plus the storm replay mid-alert, saved in screens/ (not committed).
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";

// software WebGL, so the 3D views draw in headless screenshots
test.use({ launchOptions: { args: ["--use-gl=angle", "--use-angle=swiftshader"] } });

const TABS = ["Habitat Planner", "Visor HUD", "Cuff Tablet", "Cuff card", "Validation", "About"];
const OUT = resolve(process.cwd(), "..", "screens");

async function openTab(page: Page, name: string) {
  await page.getByRole("tab", { name }).click();
  await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
}

async function noHorizontalScroll(page: Page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    const panel = document.querySelector<HTMLElement>(".canvas > [role='tabpanel']:not([hidden])");
    return {
      page: doc.scrollWidth <= doc.clientWidth + 1,
      panel: !panel || panel.scrollWidth <= panel.clientWidth + 1,
      widths: [doc.scrollWidth, doc.clientWidth, panel?.scrollWidth, panel?.clientWidth],
    };
  });
}

for (const [w, h] of [[1280, 800], [1366, 768], [1440, 900], [1920, 1080], [390, 844]] as const) {
  test(`no horizontal scroll on any surface at ${w} px`, async ({ page }) => {
    test.setTimeout(300_000); // the visor's 3D view renders in software here
    await page.setViewportSize({ width: w, height: h });
    await page.goto("./");
    for (const tab of TABS) {
      await openTab(page, tab);
      await page.waitForTimeout(400);
      const r = await noHorizontalScroll(page);
      expect(r.page && r.panel, `${tab} at ${w}px: ${r.widths.join(", ")}`).toBe(true);
    }
  });
}

test.describe("screenshots", () => {
  test.skip(!process.env.ARIADNE_SCREENS, "screenshots are taken only with ARIADNE_SCREENS=1");
  for (const [w, h] of [[1440, 900], [1366, 768], [390, 844]] as const) {
    test(`every surface at ${w} x ${h}`, async ({ page }) => {
      test.setTimeout(300_000);
      mkdirSync(OUT, { recursive: true });
      await page.setViewportSize({ width: w, height: h });
      await page.goto("./");
      await expect(page.locator("[data-map-ready='true']")).toBeAttached({ timeout: 60_000 });
      for (const tab of TABS) {
        await openTab(page, tab);
        if (tab === "Visor HUD") {
          await expect(page.locator(".rehearsal-canvas.embedded[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
          await page.getByRole("tabpanel", { name: "Visor HUD" }).getByLabel(/Mission time/).fill("100");
        }
        if (tab === "Cuff Tablet") await page.getByRole("tabpanel", { name: "Cuff Tablet" }).getByLabel(/Mission time/).fill("40");
        await page.mouse.move(w - 2, h - 2); // no hover tooltips in the shots
        await page.waitForTimeout(1500);
        await page.screenshot({ path: `${OUT}/${w}x${h}-${tab.toLowerCase().replace(/\s+/g, "-")}.png` });
      }
    });
  }

  test("storm replay mid-alert at 1440 x 900", async ({ page }) => {
    test.setTimeout(180_000);
    mkdirSync(OUT, { recursive: true });
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("./");
    await openTab(page, "Visor HUD");
    await expect(page.locator(".rehearsal-canvas.embedded[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
    const panel = page.getByRole("tabpanel", { name: "Visor HUD" });
    const replay = await (await page.request.get("./sites/boxwork/replay.json")).json();
    await panel.getByRole("button", { name: "Replay the May 20, 2024 storm" }).click();
    await panel.getByRole("button", { name: "Pause" }).click();
    await panel.getByLabel(/Mission time/).fill(String(Math.ceil(replay.alignment.start_min.balanced + 3)));
    await expect(panel.locator("[data-hud-element='storm']")).toBeVisible();
    await page.mouse.move(1438, 898);
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${OUT}/1440x900-storm-replay.png` });
  });
});
