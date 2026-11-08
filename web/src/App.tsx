// Written with AI assistance (Claude Code). See AI_USE.md.
// Phase 0 placeholder page. It states only what is true today: the app is not built yet.
import { AI_USE_URL, CREDITS_URL, REPO_URL } from "./links";

export default function App() {
  return (
    <>
      <main className="page">
        <p className="eyebrow">NASA Space Apps Challenge 2026 · Interplanetary Survival Guide: Martian Map</p>
        <h1>ARIADNE</h1>
        <p className="tagline">A thread home on Mars.</p>
        <p>
          ARIADNE will plan, rehearse and guard a two-astronaut Marswalk through the boxwork ridges
          of Mount Sharp in Gale crater, keeping a safe way back to shelter at every step. It is
          being built from openly published NASA and USGS data, and every number it shows will be
          labeled as measured, derived, modeled or placeholder.
        </p>

        <section aria-labelledby="status-heading">
          <h2 id="status-heading">Status</h2>
          <p>
            Under construction. This page is a placeholder while the data pipeline and the map are
            built. Progress is tracked in the project repository.
          </p>
        </section>

        <nav aria-label="Project links">
          <h2>Project links</h2>
          <ul>
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
      </main>
      <footer className="page footer">
        <p>
          Code licensed under Apache-2.0. Written with AI assistance (Claude Code). No NASA logos or
          AI-generated images are used.
        </p>
      </footer>
    </>
  );
}
