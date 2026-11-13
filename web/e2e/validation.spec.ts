// Written with AI assistance (Claude Code). See AI_USE.md.
// Test E15 in a real browser: the Validation tab opens from the keyboard, shows the site notes and
// every check, and has no WCAG 2.1 A or AA violations in light or dark mode.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const scheme of ["light", "dark"] as const) {
  test(`validation tab in ${scheme} mode`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto("./");
    const planner = page.getByRole("tab", { name: "Habitat Planner" });
    await planner.focus();
    await page.keyboard.press("End"); // the last tab
    const tab = page.getByRole("tab", { name: "Validation" });
    await expect(tab).toBeFocused();
    await expect(tab).toHaveAttribute("aria-selected", "true");
    await expect(page.getByRole("heading", { name: "Checks" })).toBeVisible();
    const panel = page.getByRole("tabpanel", { name: "Validation" });
    await expect(panel.getByText(/Slope no-go is conservative in boxwork terrain/)).toBeVisible();
    expect(await page.locator("li.check").count()).toBeGreaterThanOrEqual(12);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  });
}
