// Written with AI assistance (Claude Code). See AI_USE.md.
// Assumptions panel (PROMPT.md section 6): site-level notes, then every PLACEHOLDER setting the
// plans rest on, grouped, each with its note or source.
import LabelBadge from "./LabelBadge";
import type { Assumption, SiteNote } from "./types";

function show(v: Assumption["value"]): string {
  if (Array.isArray(v)) return v.join(" to ");
  return typeof v === "number" ? v.toLocaleString("en-US") : v;
}

export function SiteNotes({ notes }: { notes: SiteNote[] }) {
  if (notes.length === 0) return null;
  return (
    <ul className="site-notes">
      {notes.map((n) => (
        <li key={n.id} className="site-note">
          <strong>{n.title}.</strong> {n.text} <LabelBadge label={n.label} source={n.source} />
        </li>
      ))}
    </ul>
  );
}

export default function AssumptionsPanel({ items, notes }: { items: Assumption[]; notes: SiteNote[] }) {
  const groups = [...new Set(items.map((a) => a.group))];
  return (
    <section className="panel assumptions" aria-labelledby="assumptions-heading">
      <h2 id="assumptions-heading">Assumptions</h2>
      <SiteNotes notes={notes} />
      <details>
        <summary>Placeholder settings ({items.length})</summary>
        {groups.map((g) => (
          <table key={g} className="assumption-table" aria-label={g}>
            <caption>{g}</caption>
            <tbody>
              {items
                .filter((a) => a.group === g)
                .map((a) => (
                  <tr key={a.key}>
                    <th scope="row">{a.title}</th>
                    <td>
                      {show(a.value)} <LabelBadge label={a.label} source={a.note || "Team setting"} />
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        ))}
      </details>
    </section>
  );
}
