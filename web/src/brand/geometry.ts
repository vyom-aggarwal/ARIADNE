// Written with AI assistance (Claude Code). See AI_USE.md.
// The ARIADNE mark, as geometry: Mars ground seen from above with boxwork ridges, and the thread
// from a ring (you) to a square (the rover), the same symbols as the line home on the HUD and
// tablet. Drawn by hand as SVG code from lines and simple shapes; public/favicon.svg repeats it.
export const MARK = {
  viewBox: "0 0 64 64",
  tileRadius: 14,
  /** boxwork ridges: a polygon network of straight segments */
  ridges: "M0 24 L17 21 L23 0 M17 21 L20 39 L0 44 M20 39 L39 35 L44 14 L64 10 M44 14 L36 0 M39 35 L45 52 L64 55 M45 52 L27 57 L24 64 M27 57 L20 39 M39 35 L64 33",
  /** the thread, from the ring to the square */
  route: "M14 15 H33 Q41 15 37 22 L30 30 Q26 36 34 36 H43 Q50 36 48 43 L46.5 47",
  ring: { cx: 14, cy: 15, r: 5.5 },
  rover: { x: 40.5, y: 45, size: 12 },
  colors: {
    groundLight: "#b5532a",
    groundDark: "#5c200d",
    ridge: "#f0b58a",
    thread: "#3de0ff",
    outline: "#05070d",
  },
} as const;
