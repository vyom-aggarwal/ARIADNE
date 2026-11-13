// Written with AI assistance (Claude Code). See AI_USE.md.
// Draws the HUD elements (hud/model.ts) on a 1920 x 1080 frame: white and cyan with dark
// outlines, each element with its own shape, at most four, in the periphery.
import type { XY } from "../core/eva/sim";
import { HUD } from "./colors";
import type { HudElement, Shape } from "./model";

function Glyph({ shape, color, rotate = 0 }: { shape: Shape; color: string; rotate?: number }) {
  const s = { fill: "none", stroke: color, strokeWidth: 6, strokeLinejoin: "round" as const, paintOrder: "stroke" };
  const halo = { fill: "none", stroke: HUD.outline, strokeWidth: 14, strokeLinejoin: "round" as const };
  const path = (() => {
    switch (shape) {
      case "chevron":
        return "M -28 18 L 0 -22 L 28 18";
      case "double-chevron":
        return "M -28 26 L 0 -6 L 28 26 M -28 4 L 0 -28 L 28 4";
      case "ring":
        return "M 26 0 A 26 26 0 1 1 -26 0 A 26 26 0 1 1 26 0";
      case "diamond":
        return "M 0 -28 L 26 0 L 0 28 L -26 0 Z";
      case "octagon":
        return "M -12 -28 L 12 -28 L 28 -12 L 28 12 L 12 28 L -12 28 L -28 12 L -28 -12 Z M 0 -14 L 0 6 M 0 14 L 0 16";
      case "triangle":
        return "M 0 -28 L 28 24 L -28 24 Z M 0 -8 L 0 8 M 0 15 L 0 17";
      case "circle":
        return "M 22 0 A 22 22 0 1 1 -22 0 A 22 22 0 1 1 22 0 M 0 -10 L 0 6";
      case "hatched-square":
        return "M -24 -24 L 24 -24 L 24 24 L -24 24 Z M -24 0 L 0 -24 M -24 24 L 24 -24 M 0 24 L 24 0";
      default:
        return "M -26 0 L 26 0";
    }
  })();
  return (
    <svg className="hud-glyph" viewBox="-36 -36 72 72" width="72" height="72" aria-hidden="true">
      <g transform={`rotate(${rotate})`}>
        <path d={path} {...halo} />
        <path d={path} {...s} />
      </g>
    </svg>
  );
}

function MiniMap({ el }: { el: HudElement }) {
  const pts: XY[] = [...(el.homePath ?? []), ...(el.crumbs ?? []), ...(el.pins ?? [])];
  if (pts.length === 0) return null;
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const span = Math.max(x1 - x0, y1 - y0, 50);
  const W = 300;
  const H = 220;
  const k = Math.min((W - 30) / span, (H - 30) / span);
  const cx = (x0 + x1) / 2;
  const cy = (y0 + y1) / 2;
  const P = (p: XY) => `${(W / 2 + (p[0] - cx) * k).toFixed(1)},${(H / 2 - (p[1] - cy) * k).toFixed(1)}`;
  const home = (el.homePath ?? []).map(P).join(" ");
  return (
    <svg className="hud-minimap" viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true">
      {(el.crumbs ?? []).map((c, i) => (
        <circle key={i} cx={P(c).split(",")[0]} cy={P(c).split(",")[1]} r={3} fill={HUD.white} stroke={HUD.outline} strokeWidth={2} />
      ))}
      <polyline points={home} fill="none" stroke={HUD.outline} strokeWidth={10} strokeLinejoin="round" />
      <polyline points={home} fill="none" stroke={HUD.cyan} strokeWidth={5} strokeLinejoin="round" />
      {(el.pins ?? []).map((p, i) => {
        const [x, y] = P(p).split(",").map(Number);
        return (
          <path key={i} d={`M ${x} ${y - 12} L ${x + 7} ${y} L ${x} ${y + 12} L ${x - 7} ${y} Z`}
            fill={HUD.white} stroke={HUD.outline} strokeWidth={3} />
        );
      })}
      {el.ev1 && (() => {
        const [x, y] = P(el.ev1).split(",").map(Number);
        return <rect x={x - 7} y={y - 7} width={14} height={14} fill={HUD.cyan} stroke={HUD.outline} strokeWidth={3} />;
      })()}
    </svg>
  );
}

export default function HudOverlay({ elements }: { elements: HudElement[] }) {
  return (
    <div className="hud-overlay" data-hud-count={elements.length}>
      {elements.map((el) => {
        const color = el.color === "cyan" ? HUD.cyan : HUD.white;
        return (
          <div key={el.slot} className={`hud-el hud-${el.slot}`} data-hud-element={el.kind}
            data-shape={el.shape} style={{ color }}>
            <Glyph shape={el.shape} color={color} rotate={el.shape === "chevron" || el.shape === "double-chevron" ? (el.arrowDeg ?? 0) : 0} />
            <div className="hud-text">
              {el.kind === "thread" && <MiniMap el={el} />}
              <span>{el.text}</span>
              {el.more ? <span className="hud-more"> (+{el.more} more)</span> : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
