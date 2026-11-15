// Written with AI assistance (Claude Code). See AI_USE.md.
// Test H5: in Chromium, the May 20, 2024 storm replay raises the alert on cue and enters storm
// mode in the Visor HUD, with RAD's measured dose beside the modeled doses.
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 } });

test("storm replay triggers storm mode on cue", async ({ page }) => {
  test.setTimeout(120_000);
  const replay = await (await page.request.get("./sites/boxwork/replay.json")).json();
  const start: number = replay.alignment.start_min.balanced;
  await page.goto("./");
  await page.getByRole("tab", { name: "Visor HUD" }).click();
  const panel = page.getByRole("tabpanel", { name: "Visor HUD" });
  await panel.getByRole("button", { name: "Replay the May 20, 2024 storm" }).click();
  await panel.getByRole("button", { name: "Pause" }).click();
  const time = panel.getByLabel(/Mission time/);
  await time.fill(String(Math.floor(start - 1)));
  await expect(panel.locator(".replay-panel")).toHaveAttribute("data-replay-phase", "before");
  await expect(panel.locator("[data-hud-element='storm']")).toHaveCount(0);
  await time.fill(String(Math.ceil(start + 1)));
  await expect(panel.locator(".replay-panel")).toHaveAttribute("data-replay-phase", "after");
  await expect(panel.locator("[data-hud-element='storm']")).toBeVisible();
  await expect(panel.locator("[data-hud-element='alert'][data-shape='octagon']")).toContainText("Solar storm");
  const doses = panel.locator(".replay-doses");
  await expect(doses).toContainText("8,100 µGy");
  await expect(doses.locator(".label-badge", { hasText: "MEASURED" })).toHaveCount(1);
  await expect(doses.locator(".label-badge", { hasText: "MODELED" })).toHaveCount(3);
  expect(Number(await page.locator(".visor-frame").getAttribute("data-hud-count"))).toBeLessThanOrEqual(4);
  await panel.getByRole("button", { name: "End the storm replay" }).click();
});
