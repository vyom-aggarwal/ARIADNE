// Written with AI assistance (Claude Code). See AI_USE.md.
// Phase 0 accessibility check on the built page in a real browser (acceptance test A9).
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.describe("placeholder page", () => {
  for (const scheme of ["light", "dark"] as const) {
    test(`has no WCAG 2.1 A or AA violations in ${scheme} mode`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto("./");
      await expect(page.getByRole("heading", { level: 1, name: "ARIADNE" })).toBeVisible();
      // The AI header comment sits before the doctype; the page must still render in standards mode.
      expect(await page.evaluate(() => document.compatMode)).toBe("CSS1Compat");
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
    });
  }

  test("every link can be reached with the Tab key", async ({ page }) => {
    await page.goto("./");
    const hrefs = await page
      .getByRole("link")
      .evaluateAll((els) => [...new Set(els.map((a) => (a as HTMLAnchorElement).href))]);
    expect(hrefs.length).toBeGreaterThan(0);
    const reached = new Set<string>();
    for (let i = 0; i < hrefs.length + 3; i++) {
      await page.keyboard.press("Tab");
      const href = await page.evaluate(() => {
        const el = document.activeElement;
        return el instanceof HTMLAnchorElement ? el.href : null;
      });
      if (href) reached.add(href);
    }
    expect([...reached].sort()).toEqual([...hrefs].sort());
  });

  test("focused links show a visible outline", async ({ page }) => {
    await page.goto("./");
    await page.keyboard.press("Tab");
    const outline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      const s = getComputedStyle(el);
      return { style: s.outlineStyle, width: parseFloat(s.outlineWidth) };
    });
    expect(outline.style).not.toBe("none");
    expect(outline.width).toBeGreaterThanOrEqual(2);
  });
});
