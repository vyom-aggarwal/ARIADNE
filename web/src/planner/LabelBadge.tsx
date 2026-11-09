// Written with AI assistance (Claude Code). See AI_USE.md.
// Every number the app shows carries its label; the source appears on hover and focus.
import type { Label } from "./types";

export default function LabelBadge({ label, source }: { label: Label | string; source?: string }) {
  return (
    <span className={`label-badge label-${String(label).toLowerCase()}`} title={source ?? label}>
      {label}
    </span>
  );
}
