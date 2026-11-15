// Written with AI assistance (Claude Code). See AI_USE.md.
// The first-visit intro: shown over the live map with its facts and two actions, accessible,
// dismissed by "Explore" and remembered; "Start the 3-minute judge tour" opens the tour.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } }); // a first visit: nothing remembered

test("intro shows on the first visit, is accessible and is remembered once dismissed", async ({ page }) => {
  await page.goto("./");
  const intro = page.getByRole("dialog", { name: "A thread home on Mars" });
  await expect(intro).toBeVisible();
  await expect(intro).toContainText("two-astronaut Marswalk");
  await expect(intro.locator(".label-badge")).toHaveCount(3); // three labeled facts
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  await intro.getByRole("button", { name: "Explore" }).click();
  await expect(intro).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "ARIADNE" })).toBeVisible();
  await expect(page.getByRole("dialog", { name: "A thread home on Mars" })).toHaveCount(0);
});

test("the judge tour starts from the intro and walks the surfaces", async ({ page }) => {
  await page.goto("./");
  await page.getByRole("button", { name: "Start the 3-minute judge tour" }).click();
  const tour = page.getByRole("region", { name: "Judge tour" });
  await expect(tour).toContainText("step 1 of 8");
  for (let i = 0; i < 4; i++) await tour.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("tab", { name: "Visor HUD" })).toHaveAttribute("aria-selected", "true");
  await tour.getByRole("button", { name: "Next" }).click(); // the storm replay
  await tour.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("tab", { name: "Validation" })).toHaveAttribute("aria-selected", "true");
  await tour.getByRole("button", { name: "End tour" }).click();
  await expect(tour).toHaveCount(0);
});
