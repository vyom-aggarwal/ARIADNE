// Written with AI assistance (Claude Code). See AI_USE.md.
// The page: a short introduction and project links, then the app in tabs: the Habitat Planner
// (Phase 4) and the Validation tab (PROMPT.md section 7).
import { type KeyboardEvent, useRef, useState } from "react";
import { AI_USE_URL, CREDITS_URL, REPO_URL } from "./links";
import Planner from "./planner/Planner";
import ValidationView from "./validation/ValidationView";

const TABS = [
  { id: "planner", title: "Habitat Planner" },
  { id: "validation", title: "Validation" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function Tabs() {
  const [active, setActive] = useState<TabId>("planner");
  const [seen, setSeen] = useState<Set<TabId>>(new Set(["planner"]));
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const open = (id: TabId) => {
    setActive(id);
    setSeen((s) => new Set(s).add(id));
  };
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = TABS.findIndex((t) => t.id === active);
    const next =
      e.key === "ArrowRight" ? (i + 1) % TABS.length
      : e.key === "ArrowLeft" ? (i - 1 + TABS.length) % TABS.length
      : e.key === "Home" ? 0
      : e.key === "End" ? TABS.length - 1
      : -1;
    if (next < 0) return;
    e.preventDefault();
    open(TABS[next].id);
    refs.current[TABS[next].id]?.focus();
  };
  return (
    <>
      <div className="tabs" role="tablist" aria-label="ARIADNE views" onKeyDown={onKey}>
        {TABS.map((t) => (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[t.id] = el;
            }}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={active === t.id}
            aria-controls={`panel-${t.id}`}
            tabIndex={active === t.id ? 0 : -1}
            onClick={() => open(t.id)}
          >
            {t.title}
          </button>
        ))}
      </div>
      {TABS.map((t) => (
        <div
          key={t.id}
          role="tabpanel"
          id={`panel-${t.id}`}
          aria-labelledby={`tab-${t.id}`}
          hidden={active !== t.id}
        >
          {seen.has(t.id) && (t.id === "planner" ? <Planner /> : <ValidationView />)}
        </div>
      ))}
    </>
  );
}

export default function App() {
  return (
    <>
      <header className="masthead">
        <p className="eyebrow">NASA Space Apps Challenge 2026 · Interplanetary Survival Guide: Martian Map</p>
        <h1>ARIADNE</h1>
        <p className="tagline">A thread home on Mars.</p>
        <p>
          ARIADNE plans, rehearses and guards a two-astronaut Marswalk through the boxwork ridges of
          Mount Sharp in Gale crater, keeping a safe way back to shelter at every step. It is built
          from openly published NASA and USGS data, and every number it shows is labeled as
          measured, derived, modeled or placeholder.
        </p>
        <nav aria-label="Project links">
          <h2 className="visually-hidden">Project links</h2>
          <ul className="links">
            <li>
              <a href={REPO_URL}>Source code on GitHub</a>
            </li>
            <li>
              <a href={AI_USE_URL}>How we use AI</a>
            </li>
            <li>
              <a href={CREDITS_URL}>Credits and data sources</a>
            </li>
          </ul>
        </nav>
      </header>
      <main>
        <Tabs />
      </main>
      <footer className="footer">
        <p>
          Code licensed under Apache-2.0. Written with AI assistance (Claude Code). Curiosity
          photos courtesy NASA/JPL-Caltech. No NASA logos or AI-generated images are used. All
          plans are modeled on placeholder settings and are not mission guidance.
        </p>
      </footer>
    </>
  );
}
