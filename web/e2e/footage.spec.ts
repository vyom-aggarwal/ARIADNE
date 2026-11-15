// Written with AI assistance (Claude Code). See AI_USE.md.
// Screen footage for the demo video and slides (docs/VIDEO_SCRIPT.md): Playwright records the
// live app at 1280 x 720 and saves one clip and one still per beat in footage/ at the repo root.
// Skipped unless ARIADNE_FOOTAGE=1 (`make footage`), so normal test runs stay fast.
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";

const OUT = resolve(process.cwd(), "..", "footage"); // Playwright runs from web/
const ON = !!process.env.ARIADNE_FOOTAGE;

test.skip(!ON, "footage is recorded only with ARIADNE_FOOTAGE=1");
test.use({
  viewport: { width: 1280, height: 720 },
  video: { mode: "on", size: { width: 1280, height: 720 } },
  launchOptions: { args: ["--use-gl=angle", "--use-angle=swiftshader"] },
});

async function save(page: Page, name: string) {
  mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: `${OUT}/${name}.png` });
  const video = page.video();
  await page.close();
  await video?.saveAs(`${OUT}/${name}.webm`);
}

async function tab(page: Page, name: string) {
  await page.getByRole("tab", { name }).click();
}

test("planner: map, layers and the three routes", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("./");
  await expect(page.locator("[data-map-ready='true']")).toBeAttached({ timeout: 60_000 });
  await page.locator(".map").scrollIntoViewIfNeeded();
  await page.waitForTimeout(1500);
  await page.getByRole("checkbox", { name: /Walkability, rover/ }).click();
  await page.waitForTimeout(1500);
  for (const p of ["Safest", "Most science", "Balanced"]) {
    await page.getByRole("button", { name: `Show ${p} on the map` }).click();
    await page.waitForTimeout(1200);
  }
  await page.getByTestId("price-of-safety").scrollIntoViewIfNeeded();
  await page.waitForTimeout(1500);
  await save(page, "planner");
});

test("rehearsal: walking height past Curiosity photos", async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto("./");
  await page.getByRole("button", { name: "3D rehearsal" }).click();
  await expect(page.locator(".rehearsal-canvas[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
  await page.locator(".rehearsal-canvas").scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Ground" }).click();
  await page.getByRole("slider", { name: "Walking speed multiplier" }).fill("12");
  await page.waitForTimeout(8000);
  await save(page, "rehearsal");
});

test("hud: the visor during the walk", async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto("./");
  await tab(page, "Visor HUD");
  await expect(page.locator(".rehearsal-canvas.embedded[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
  const panel = page.getByRole("tabpanel", { name: "Visor HUD" });
  await panel.getByLabel(/Mission time/).fill("100");
  await page.locator(".visor-frame").scrollIntoViewIfNeeded();
  await panel.getByRole("button", { name: "Play", exact: true }).click();
  await page.waitForTimeout(6000);
  await save(page, "hud");
});

test("replay: the May 20, 2024 storm", async ({ page }) => {
  test.setTimeout(150_000);
  await page.goto("./");
  await tab(page, "Visor HUD");
  await expect(page.locator(".rehearsal-canvas.embedded[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
  const panel = page.getByRole("tabpanel", { name: "Visor HUD" });
  await page.locator(".visor-frame").scrollIntoViewIfNeeded();
  await panel.getByRole("button", { name: "Replay the May 20, 2024 storm" }).click();
  await expect(panel.locator(".replay-panel")).toHaveAttribute("data-replay-phase", "after", { timeout: 30_000 });
  await page.waitForTimeout(4000);
  await page.locator(".replay-panel").scrollIntoViewIfNeeded();
  await page.waitForTimeout(3000);
  await save(page, "replay");
});

test("tablet and card", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto("./");
  await tab(page, "Cuff Tablet");
  await page.getByRole("tabpanel", { name: "Cuff Tablet" }).getByLabel(/Mission time/).fill("40");
  await page.getByTestId("tablet").scrollIntoViewIfNeeded();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${OUT}/tablet.png` });
  await tab(page, "Cuff card");
  await page.locator(".cuff-card").scrollIntoViewIfNeeded();
  await page.waitForTimeout(3000);
  await save(page, "tablet-card");
});
