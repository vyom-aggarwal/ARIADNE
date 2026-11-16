// Written with AI assistance (Claude Code). See AI_USE.md.
// The ARIADNE mark and favicon: a vector drawing in code (no image generator, no third-party
// artwork), the same geometry in the app and the favicon, and the page heading unchanged.
import { cleanup, render, screen } from "@testing-library/react";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import App from "../src/App";
import Mark from "../src/brand/Mark";
import { MARK } from "../src/brand/geometry";

afterEach(cleanup);

const pub = (f: string) => resolve(__dirname, "..", "public", f);
const html = readFileSync(resolve(__dirname, "..", "index.html"), "utf8");
const favicon = readFileSync(pub("favicon.svg"), "utf8");

describe("favicon", () => {
  it("is linked from the page, with a touch icon, and both files exist", () => {
    expect(html).toMatch(/<link rel="icon" href="[./]*favicon\.svg" type="image\/svg\+xml"/);
    expect(html).toMatch(/<link rel="apple-touch-icon" href="[./]*apple-touch-icon\.png"/);
    expect(html).not.toContain('href="data:,"');
    expect(existsSync(pub("apple-touch-icon.png"))).toBe(true);
  });

  it("starts with the AI-assistance header and is plain vector code", () => {
    expect(favicon.startsWith("<!-- Written with AI assistance (Claude Code). See AI_USE.md. -->")).toBe(true);
    for (const banned of ["<image", "<text", "base64", "http://", "https://", "<script", "<foreignObject"]) {
      // the xmlns declaration is the one allowed URL
      const body = favicon.replace('xmlns="http://www.w3.org/2000/svg"', "");
      expect(body).not.toContain(banned);
    }
  });

  it("draws the same mark as the app", () => {
    expect(favicon).toContain(MARK.route);
    expect(favicon).toContain(MARK.ridges);
    for (const c of Object.values(MARK.colors)) expect(favicon.toLowerCase()).toContain(c.toLowerCase());
  });
});

describe("mark", () => {
  it("is decorative: hidden from assistive technology", () => {
    const { container } = render(<Mark size={28} />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("focusable")).toBe("false");
    expect(svg.querySelector("path[d]")?.getAttribute("d")).toBeTruthy();
  });

  it("uses unique gradient ids when drawn twice", () => {
    const { container } = render(
      <>
        <Mark size={28} />
        <Mark size={48} />
      </>,
    );
    const ids = [...container.querySelectorAll("linearGradient")].map((g) => g.id);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
  });

  it("sits beside the wordmark without changing the heading", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".mission-bar .wordmark svg[aria-hidden='true']")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("ARIADNE");
  });
});
