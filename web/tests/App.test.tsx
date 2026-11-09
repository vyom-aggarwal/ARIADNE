// Written with AI assistance (Claude Code). See AI_USE.md.
// The page around the Habitat Planner (acceptance test A7, updated in Phase 4).
import { cleanup, render, screen, within } from "@testing-library/react";
import axe from "axe-core";
import { afterEach, describe, expect, it } from "vitest";
import App from "../src/App";
import { REPO_URL } from "../src/links";

afterEach(cleanup);

describe("page", () => {
  it("shows ARIADNE as the only level-one heading", () => {
    render(<App />);
    const h1s = screen.getAllByRole("heading", { level: 1 });
    expect(h1s).toHaveLength(1);
    expect(h1s[0].textContent).toBe("ARIADNE");
  });

  it("explains the project in plain English", () => {
    render(<App />);
    expect(screen.getByText(/two-astronaut Marswalk/i)).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: /Habitat Planner/ })).toBeTruthy();
  });

  it("links to the source code, AI use and credits", () => {
    render(<App />);
    const nav = screen.getByRole("navigation", { name: /project links/i });
    const links = within(nav).getAllByRole("link");
    const byName = (re: RegExp) => links.find((a) => re.test(a.textContent ?? ""));
    expect(byName(/source code/i)?.getAttribute("href")).toBe(REPO_URL);
    expect(byName(/AI/)?.getAttribute("href")).toBe(`${REPO_URL}/blob/main/AI_USE.md`);
    expect(byName(/credits/i)?.getAttribute("href")).toBe(`${REPO_URL}/blob/main/CREDITS.md`);
  });

  it("has exactly one main landmark", () => {
    render(<App />);
    expect(screen.getAllByRole("main")).toHaveLength(1);
  });

  it("has no WCAG 2.1 A or AA violations that jsdom can check", async () => {
    const { container } = render(<App />);
    const results = await axe.run(container, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
      // jsdom has no layout engine, so contrast is checked in the Playwright test instead.
      rules: { "color-contrast": { enabled: false } },
    });
    expect(results.violations.map((v) => v.id)).toEqual([]);
  });
});
