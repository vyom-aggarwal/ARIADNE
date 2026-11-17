// Written with AI assistance (Claude Code). See AI_USE.md.
// The ARIADNE mark, as geometry: a peak that is both the A of the name and Mount Sharp, with a
// dot for the walker on it. Drawn by hand as SVG code from two straight strokes and a circle, in
// the app's accent colors; public/favicon.svg repeats the tile version.
export const MARK = {
  viewBox: "0 0 64 64",
  /** the glyph alone, cropped to its strokes, for use beside the wordmark */
  glyphViewBox: "13 12 38 39",
  tileRadius: 16,
  peak: "M17 47 L32 16 L47 47",
  stroke: 7,
  dot: { cx: 32, cy: 38, r: 4.6 },
  colors: {
    from: "#3de0ff",
    to: "#9b8cff",
    ink: "#0a0e1a",
  },
} as const;
