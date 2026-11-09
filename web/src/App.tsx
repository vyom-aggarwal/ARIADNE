// Written with AI assistance (Claude Code). See AI_USE.md.
// The page: a short introduction and project links, then the Habitat Planner (Phase 4).
import { AI_USE_URL, CREDITS_URL, REPO_URL } from "./links";
import Planner from "./planner/Planner";

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
        <Planner />
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
