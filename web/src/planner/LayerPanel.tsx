// Written with AI assistance (Claude Code). See AI_USE.md.
// Layer panel: each layer's toggle, opacity, legend and provenance (source, resolution, date,
// label), with the source IDs on hover and focus.
import LabelBadge from "./LabelBadge";
import type { Layer } from "./types";

export interface LayerState {
  visible?: boolean;
  opacity?: number;
}

interface Props {
  layers: Layer[];
  state: Record<string, LayerState>;
  onChange: (id: string, change: LayerState) => void;
}

const GROUPS: [string, string][] = [
  ["base", "Base maps"],
  ["safety", "Safety"],
  ["science", "Science"],
  ["uncertainty", "Uncertainty"],
  ["context", "Context"],
];

function swatch(color: number[], pattern?: string) {
  const [r, g, b, a = 255] = color;
  const rgba = `rgba(${r}, ${g}, ${b}, ${Math.max(a, 120) / 255})`;
  const background =
    pattern === "hatch"
      ? `repeating-linear-gradient(45deg, ${rgba} 0 3px, transparent 3px 6px)`
      : rgba;
  return <span className="swatch" aria-hidden="true" style={{ background }} />;
}

export default function LayerPanel({ layers, state, onChange }: Props) {
  return (
    <section className="panel layer-panel" aria-labelledby="layers-heading">
      <h2 id="layers-heading">Layers</h2>
      {GROUPS.map(([group, title]) => {
        const items = layers.filter((l) => l.group === group);
        if (items.length === 0) return null;
        return (
          <fieldset key={group}>
            <legend>{title}</legend>
            {items.map((lay) => {
              const s = state[lay.id] ?? {};
              const visible = s.visible ?? lay.default_visible;
              const opacity = s.opacity ?? lay.opacity;
              const id = `layer-toggle-${lay.id}`;
              return (
                <div className="layer" key={lay.id} data-testid={`layer-${lay.id}`}>
                  <div className="layer-head">
                    <input
                      type="checkbox"
                      id={id}
                      checked={visible}
                      onChange={(e) => onChange(lay.id, { visible: e.target.checked })}
                    />
                    <label htmlFor={id}>{lay.title}</label>
                    <LabelBadge label={lay.label} source={`Sources: ${lay.sources.join(", ")}`} />
                  </div>
                  <p className="layer-meta">
                    {lay.resolution_m ? `${lay.resolution_m} m · ` : ""}
                    {lay.date}
                  </p>
                  <p className="layer-desc">{lay.description}</p>
                  {lay.legend && (
                    <ul className="legend">
                      {lay.legend.map((e) => (
                        <li key={e.label}>
                          {swatch(e.color, lay.pattern)}
                          {e.label}
                        </li>
                      ))}
                    </ul>
                  )}
                  {lay.kind === "raster" && (
                    <label className="opacity">
                      <span className="visually-hidden">Opacity of {lay.title}</span>
                      <span aria-hidden="true">Opacity</span>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        step={5}
                        value={Math.round(opacity * 100)}
                        aria-label={`Opacity of ${lay.title}`}
                        onChange={(e) => onChange(lay.id, { opacity: Number(e.target.value) / 100 })}
                      />
                    </label>
                  )}
                </div>
              );
            })}
          </fieldset>
        );
      })}
    </section>
  );
}
