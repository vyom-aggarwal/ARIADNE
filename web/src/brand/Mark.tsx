// Written with AI assistance (Claude Code). See AI_USE.md.
// The ARIADNE mark beside the typographic wordmark. Decorative: the h1 carries the name.
import { useId } from "react";
import { MARK } from "./geometry";

export default function Mark({ size = 28, className }: { size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  const ground = `mark-ground-${id}`;
  const tile = `mark-tile-${id}`;
  const c = MARK.colors;
  return (
    <svg
      className={className}
      viewBox={MARK.viewBox}
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={ground} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={c.groundLight} />
          <stop offset="1" stopColor={c.groundDark} />
        </linearGradient>
        <clipPath id={tile}>
          <rect width="64" height="64" rx={MARK.tileRadius} />
        </clipPath>
      </defs>
      <rect width="64" height="64" rx={MARK.tileRadius} fill={`url(#${ground})`} />
      <g clipPath={`url(#${tile})`} fill="none" stroke={c.ridge} strokeOpacity={0.38} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round">
        <path d={MARK.ridges} />
      </g>
      <path d={MARK.route} fill="none" stroke={c.outline} strokeWidth={9.5} strokeLinecap="round" strokeLinejoin="round" />
      <path d={MARK.route} fill="none" stroke={c.thread} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={MARK.ring.cx} cy={MARK.ring.cy} r={MARK.ring.r} fill={c.outline} stroke={c.thread} strokeWidth={3.2} />
      <rect x={MARK.rover.x} y={MARK.rover.y} width={MARK.rover.size} height={MARK.rover.size} rx={1.5} fill={c.thread} stroke={c.outline} strokeWidth={2.6} />
    </svg>
  );
}
