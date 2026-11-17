// Written with AI assistance (Claude Code). See AI_USE.md.
// The ARIADNE mark. "tile" is the app icon (the glyph cut out of an accent gradient, as in the
// favicon); "glyph" is the peak and dot alone, for beside the wordmark. Decorative: the h1
// carries the name.
import { useId } from "react";
import { MARK } from "./geometry";

export default function Mark({
  size = 28,
  variant = "tile",
  className,
}: {
  size?: number;
  variant?: "tile" | "glyph";
  className?: string;
}) {
  const grad = `mark-grad-${useId().replace(/:/g, "")}`;
  const c = MARK.colors;
  const tile = variant === "tile";
  return (
    <svg
      className={className}
      viewBox={tile ? MARK.viewBox : MARK.glyphViewBox}
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={grad} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={c.from} />
          <stop offset="1" stopColor={c.to} />
        </linearGradient>
      </defs>
      {tile && <rect width="64" height="64" rx={MARK.tileRadius} fill={`url(#${grad})`} />}
      <path
        d={MARK.peak}
        fill="none"
        stroke={tile ? c.ink : `url(#${grad})`}
        strokeWidth={MARK.stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={MARK.dot.cx} cy={MARK.dot.cy} r={MARK.dot.r} fill={tile ? c.ink : c.from} />
    </svg>
  );
}
