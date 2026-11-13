// Written with AI assistance (Claude Code). See AI_USE.md.
// Tests G2 and G6 to G9 in Chromium on the production build: the Visor HUD over the 3D view,
// the Cuff Tablet's glove-sized controls, its local sample log and offline reload, the printed
// card on one page, and accessibility of all three in light and dark mode.
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 } });

async function openTab(page: Page, name: string) {
  await page.getByRole("tab", { name }).click();
  await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
}

async function axe(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return results.violations.map((v) => `${v.id} (${v.impact}): ${v.help}`);
}

test("visor HUD: at most four elements over the first-person view, storm arrow and voice buttons", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("./");
  await openTab(page, "Visor HUD");
  const frame = page.locator(".visor-frame");
  await expect(frame).toBeVisible();
  await expect(page.locator(".rehearsal-canvas.embedded[data-status='Ready']")).toBeAttached({ timeout: 90_000 });
  const panel = page.getByRole("tabpanel", { name: "Visor HUD" });
  await panel.getByLabel(/Mission time/).fill("60");
  const count = async () => Number(await frame.getAttribute("data-hud-count"));
  expect(await count()).toBeLessThanOrEqual(4);
  await expect(panel.locator("[data-hud-element='next']")).toBeVisible();
  await panel.getByRole("button", { name: "Simulate a storm alert" }).click();
  await expect(panel.locator("[data-hud-element='storm']")).toBeVisible();
  await expect(panel.locator("[data-hud-element='alert'][data-shape='octagon']")).toBeVisible();
  expect(await count()).toBeLessThanOrEqual(4);
  await panel.getByRole("button", { name: "Drop pin" }).click();
  await expect(panel.getByRole("status").filter({ hasText: "Pin 1 dropped" })).toBeVisible();
  await panel.getByRole("button", { name: "Distance home" }).click();
  await expect(panel.getByRole("status").filter({ hasText: /Rover .* metres/ })).toBeVisible();
  await panel.getByRole("button", { name: "End storm alert" }).click();
});

test("cuff tablet: every control at least 64 x 64 px at 1024 x 768, and the sample log persists", async ({ page }) => {
  await page.goto("./");
  await openTab(page, "Cuff Tablet");
  const panel = page.getByRole("tabpanel", { name: "Cuff Tablet" });
  await panel.getByLabel(/Mission time/).fill("40"); // during a station visit on the Balanced route
  const tablet = page.getByTestId("tablet");
  await expect(tablet).toBeVisible();
  const box = await tablet.boundingBox();
  expect(Math.round(box!.width)).toBe(1024);
  expect(Math.round(box!.height)).toBe(768);
  const sizes = await tablet.locator("button, select, textarea, input, a[href]").evaluateAll((els) =>
    els.map((e) => {
      const r = e.getBoundingClientRect();
      return { what: `${e.tagName} ${e.textContent?.trim().slice(0, 30) ?? ""}`, w: r.width, h: r.height };
    }),
  );
  expect(sizes.length).toBeGreaterThan(5);
  for (const s of sizes) {
    expect(s.w, s.what).toBeGreaterThanOrEqual(64);
    expect(s.h, s.what).toBeGreaterThanOrEqual(64);
  }
  for (const step of ["Look", "Observe", "Describe", "Document"]) {
    await expect(tablet.getByRole("button", { name: new RegExp(step) })).toBeVisible();
  }
  const note = `Vein sample ${Date.now()}`;
  await tablet.getByLabel("Note").fill(note);
  await tablet.locator("input[type=file]").setInputFiles({ name: "vein.png", mimeType: "image/png",
    buffer: Buffer.from("89504e470d0a1a0a", "hex") });
  await tablet.getByRole("button", { name: "Save sample" }).click();
  await expect(tablet.getByRole("list", { name: "Saved samples" })).toContainText(note);
  await page.reload();
  await openTab(page, "Cuff Tablet");
  await expect(page.getByTestId("tablet").getByRole("list", { name: "Saved samples" })).toContainText(note);
});

test("cuff tablet works offline after one visit", async ({ page, context }) => {
  test.setTimeout(120_000);
  await page.goto("./");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload(); // now the service worker controls the page
  await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await openTab(page, "Cuff Tablet");
  await expect(page.getByTestId("tablet")).toBeVisible();
  await context.setOffline(true);
  await page.reload();
  await openTab(page, "Cuff Tablet");
  await expect(page.getByTestId("tablet")).toBeVisible();
  await expect(page.getByTestId("tablet").getByRole("heading", { level: 3 }).first()).toBeVisible();
  await context.setOffline(false);
});

test("cuff card prints on exactly one page with all its parts", async ({ page }) => {
  await page.goto("./");
  await openTab(page, "Cuff card");
  const card = page.locator(".cuff-card");
  await expect(card).toBeVisible();
  await expect(card.getByRole("img", { name: /Route map/ })).toBeVisible();
  await expect(card.getByRole("img", { name: /Timeline/ })).toBeVisible();
  await expect(card.getByRole("table")).toContainText("Bearing");
  await expect(card).toContainText("abort routes to the rover");
  expect(await card.locator(".card-photos img").count()).toBeGreaterThan(0);
  await page.emulateMedia({ media: "print" });
  const fits = await card.evaluate((el) => el.scrollHeight <= el.clientHeight + 1 && el.scrollWidth <= el.clientWidth + 1);
  expect(fits).toBe(true);
  const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true });
  const pages = (pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g) ?? []).length;
  expect(pages).toBe(1);
});

for (const scheme of ["light", "dark"] as const) {
  test(`HUD, tablet and card have no WCAG 2.1 A or AA violations in ${scheme} mode`, async ({ page }) => {
    test.setTimeout(180_000);
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto("./");
    for (const tab of ["Visor HUD", "Cuff Tablet", "Cuff card"]) {
      await openTab(page, tab);
      await expect(page.getByRole("tabpanel", { name: tab }).getByRole("heading", { level: 2 })).toBeVisible();
      if (tab === "Visor HUD") await expect(page.locator(".visor-frame")).toBeVisible();
      expect(await axe(page), tab).toEqual([]);
    }
  });
}

test("every tablet control can be reached with the Tab key", async ({ page }) => {
  await page.goto("./");
  await openTab(page, "Cuff Tablet");
  const tablet = page.getByTestId("tablet");
  await expect(tablet).toBeVisible();
  const n = await tablet.locator("button:not([disabled]), select, textarea, input").count();
  await tablet.locator("button").first().focus();
  const reached = new Set<string>();
  for (let i = 0; i < n + 4; i++) {
    const id = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      return el && el.closest("[data-testid='tablet']") ? `${el.tagName}:${el.textContent?.trim() ?? ""}:${(el as HTMLInputElement).type ?? ""}` : null;
    });
    if (id) reached.add(id);
    await page.keyboard.press("Tab");
  }
  expect(reached.size).toBeGreaterThanOrEqual(n);
});
