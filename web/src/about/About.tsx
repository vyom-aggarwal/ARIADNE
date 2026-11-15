// Written with AI assistance (Claude Code). See AI_USE.md.
// About: the Apollo 14 story behind the "thread home", the second site, the data sources as
// text (no logos), and the disclosure of how SI was used.
import { ExternalLink } from "lucide-react";
import { AI_USE_URL, CREDITS_URL, REPO_URL } from "../links";

export default function About() {
  return (
    <section className="page" aria-labelledby="about-heading">
      <h2 id="about-heading" className="page-title">About ARIADNE</h2>
      <div className="about-grid">
        <article className="panel" aria-labelledby="apollo-heading">
          <h2 id="apollo-heading">Why a thread home</h2>
          <p>
            On February 6, 1971, Apollo 14's moonwalkers Alan Shepard and Edgar Mitchell set out for the rim of
            Cone Crater. NASA estimates they were within 50 to 75 metres of it when mission control told them to
            collect samples there and head back.
          </p>
          <p className="note">
            Source: NASA, Apollo 14 Mission Details,{" "}
            <a href="https://www.nasa.gov/missions/apollo/apollo-14-mission-details/">nasa.gov</a>.
          </p>
          <p>
            On Mars, Earth is many light-minutes away, so the crew must carry the plan with them. ARIADNE keeps a
            thread home: at every point of a walk the crew has enough air to get back to the rover with a reserve.
          </p>
        </article>
        <article className="panel" aria-labelledby="sites-heading">
          <h2 id="sites-heading">Two sites, one pipeline</h2>
          <p>
            <strong>Mount Sharp boxwork</strong>, where Curiosity has been exploring since 2025: the flagship site
            with the plans, the rehearsal, the visor and the storm replay.
          </p>
          <p>
            <strong>Murray Buttes</strong>, where Curiosity measured how much a butte shields radiation in 2016:
            the same pipeline built this site to calibrate the shielding layer and to test walkability on ground it
            had not seen. A generator for any new HiRISE terrain is future work.
          </p>
        </article>
        <article className="panel" aria-labelledby="data-heading">
          <h2 id="data-heading">Data</h2>
          <ul>
            <li>USGS Gale 1 m elevation model and 25 cm image mosaic (from HiRISE, CTX and ESA's HRSC)</li>
            <li>MOLA global elevation model</li>
            <li>Curiosity's positions (PLACES), Navcam photos, ChemCam targets and drill holes</li>
            <li>THEMIS night infrared, HiRISE footprints</li>
            <li>RAD radiation results, CCMC DONKI space weather, JPL Horizons light time</li>
            <li>NASA GISS Mars24 and NAIF time</li>
          </ul>
          <p>
            <a href={CREDITS_URL}>Every source with its credit and license <ExternalLink size={12} aria-hidden="true" /></a>
          </p>
        </article>
        <article className="panel" aria-labelledby="si-heading">
          <h2 id="si-heading">How SI was used</h2>
          <p>
            Claude (claude.ai) generated the project concept and plan at the team's request and proposed most
            decisions; Claude Code wrote the software; the team chose the challenge, directed the work and approved
            or rejected each decision. The idea was SI-generated before the 2026 rule against that was published.
          </p>
          <p>
            <a href={AI_USE_URL}>The full account <ExternalLink size={12} aria-hidden="true" /></a> ·{" "}
            <a href={REPO_URL}>Source code <ExternalLink size={12} aria-hidden="true" /></a>
          </p>
        </article>
      </div>
    </section>
  );
}
