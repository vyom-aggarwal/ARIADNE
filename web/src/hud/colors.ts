// Written with AI assistance (Claude Code). See AI_USE.md.
// HUD colors (PROMPT.md section 6): white and cyan with dark outlines, never red or orange, and
// the checks behind that rule: WCAG relative luminance and contrast, and color vision deficiency
// simulated with Machado, Oliveira and Fernandes 2009 (IEEE TVCG 15(6):1291-1298), severity 1.0
// matrices as published on the authors' page (docs/SOURCES_LOG.md, machado-2009-cvd).

export const HUD = {
  white: "#ffffff",
  cyan: "#7df9ff",
  outline: "#05080b",
} as const;

export type HudColor = "white" | "cyan";
export type RGB = [number, number, number];

export function hexToRgb(hex: string): RGB {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255) as RGB;
}

export function srgbToLinear(v: number): number {
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

export function linearToSrgb(v: number): number {
  const c = Math.min(1, Math.max(0, v));
  return c <= 0.0031308 ? c * 12.92 : 1.055 * c ** (1 / 2.4) - 0.055;
}

/** WCAG 2.1 relative luminance of an sRGB color (components 0 to 1). */
export function luminance([r, g, b]: RGB): number {
  return 0.2126 * srgbToLinear(r) + 0.7152 * srgbToLinear(g) + 0.0722 * srgbToLinear(b);
}

export function contrast(l1: number, l2: number): number {
  const [a, b] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (a + 0.05) / (b + 0.05);
}

export const MACHADO_2009 = {
  protan: [
    [0.152286, 1.052583, -0.204868],
    [0.114503, 0.786281, 0.099216],
    [-0.003882, -0.048116, 1.051998],
  ],
  deutan: [
    [0.367322, 0.860646, -0.227968],
    [0.280085, 0.672501, 0.047413],
    [-0.01182, 0.04294, 0.968881],
  ],
  tritan: [
    [1.255528, -0.076749, -0.178779],
    [-0.078411, 0.930809, 0.147602],
    [0.004733, 0.691367, 0.3039],
  ],
} as const;

export type Deficiency = keyof typeof MACHADO_2009;

/** The color as seen with a deficiency. The source does not say whether the matrices act on
 * linear or gamma-encoded RGB, so both are offered and the checks must pass both ways. */
export function simulate(rgb: RGB, kind: Deficiency, space: "linear" | "gamma"): RGB {
  const m = MACHADO_2009[kind];
  const v = space === "linear" ? rgb.map(srgbToLinear) : rgb;
  const out = m.map((row) => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]);
  const clamped = out.map((x) => Math.min(1, Math.max(0, x)));
  return (space === "linear" ? clamped.map(linearToSrgb) : clamped) as RGB;
}

/** Hue in degrees and saturation (HSL) of an sRGB color. */
export function hueSat([r, g, b]: RGB): { hue: number; sat: number } {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { hue: 0, sat: 0 };
  const sat = d / (1 - Math.abs(2 * l - 1));
  let hue = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  hue *= 60;
  return { hue: (hue + 360) % 360, sat };
}

/** Red or orange: a saturated hue from 340 through 0 to 50 degrees. */
export function isRedOrOrange(rgb: RGB): boolean {
  const { hue, sat } = hueSat(rgb);
  return sat > 0.15 && (hue >= 340 || hue <= 50);
}

/** A symbol drawn in `symbol` with a `outline` halo stays visible on ground of luminance g when
 * either the symbol or its outline contrasts at least `min` with the ground. */
export function visibleOnGround(symbol: RGB, outline: RGB, groundLum: number, min = 3): boolean {
  return Math.max(contrast(luminance(symbol), groundLum), contrast(luminance(outline), groundLum)) >= min;
}
