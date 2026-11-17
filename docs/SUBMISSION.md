# ARIADNE: submission text

Draft text for each field of the NASA Space Apps 2026 project form, following the 2026 Project Submission Guide (dated November 13, 2026). Copy each block into the form; fill in the bracketed team details first. Every number below comes from [PROGRESS.md](PROGRESS.md), [validation.json](../validation.json) or the plans in [plan/](plan/).

**Before you press "Submit for Judging" (by Sunday, November 15, 11:59 p.m. local time of your Local Event):**

- [ ] Every team member is confirmed at the same Local Event and appears on the Members tab (at most six).
- [ ] The demo is a video of 30 seconds or less with English subtitles, or a deck of at most seven slides, at a public link that needs no login (test it in a private window).
- [ ] All text is in English; no images, video or audio of anyone under 18.
- [ ] Every external resource is listed in the references field (the second checkbox says so).
- [ ] Both checkboxes: the Terms and Conditions, and "Confirm All Work is Original". The 2026 guide also says SI should not be used to come up with the idea, and ARIADNE's idea was SI-generated (before that rule was published). How to answer is the team's call; if unsure, ask your Local Lead or Space Apps before submitting.

---

## Project Name

ARIADNE: a thread home on Mars

## Challenge

Interplanetary Survival Guide: Martian Map

## Team

[Team name] · [member names]

## High-Level Project Summary

ARIADNE plans, rehearses and guards a two-astronaut walk on Mars, using the boxwork ridges of Mount Sharp, where Curiosity is exploring now, as the test site. From NASA and USGS terrain models, orbital images and Curiosity's own positions, it maps where a suited walker can go, how much open sky each spot sees (a guide to radiation shielding), and which ridge, wall and hollow stops would teach the most. It then plans three walks, Safest, Balanced and Most science, that never break the "thread": at every point the crew keeps enough air to walk back to the rover with a reserve. The crew can rehearse the walk in 3D past real Curiosity photos, then follow it on a visor display that never shows more than four things at once, a glove-sized cuff tablet that works offline, and a one-page printed cuff card. A replay of the May 20, 2024 solar storm shows why it matters: Earth was 15.8 light-minutes away and the particles reached Mars in tens of minutes, so the crew must act on their own alarm, and ARIADNE sends both walkers to the lowest-dose refuge. Every number is labeled measured, derived, modeled or placeholder, and a Validation tab shows every check, including the one that failed.

## Link to Project Demo

[Public link to the 30-second video (YouTube or Google Drive, no login), or to the seven-slide deck.] The storyboard and English subtitles are in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md); the backup deck outline is in [SLIDES.md](SLIDES.md).

## Link to Final Project

- Live app: https://vyom-aggarwal.github.io/ARIADNE/
- Source code, data pipeline and documentation: https://github.com/vyom-aggarwal/ARIADNE

## Detailed Project Description

**What it does.** ARIADNE is a planning, rehearsal and guidance system for a Mars EVA (a walk outside), built for the boxwork ridges on Mount Sharp in Gale crater. It answers the questions a crew and its planners would ask before and during a walk: where can we safely go, what is worth sampling, what route keeps us safe, and what do we do if a solar storm hits while we are out?

**How it works.** A Python pipeline runs at build time and a static web app shows the results; there is no server and no secret key.

1. *Data.* The pipeline crops the USGS 1 m elevation model and 25 cm image mosaic of Gale crater (built from HiRISE, CTX and HRSC), the MOLA global elevation model, Curiosity's 2,893 positions in the boxwork from PLACES, ChemCam targets, the four boxwork drill holes and THEMIS night-infrared images, and records where each file came from.
2. *Layers.* From those it builds slope at each traveller's footprint, walkability for a suited walker and for the rover, terrain horizons in 72 directions out to 100 km, a sky-shielding index calibrated on Curiosity's radiation measurement beside the Murray Buttes in 2016 (the model reproduces the measured 3.8% dose drop with one parameter and gets the blocked sky to 18.5% against the paper's 19%), line of sight from the rover's antenna, sunlight, boxwork ridges and fractures, a science score for ridge, wall and hollow transects, and a confidence map.
3. *Routes.* A 16-neighbour route graph prices every step by time, effort, caution, radiation and uncertainty, using a published walking-cost model with placeholder suit settings. OR-Tools picks whole transects within a 6-hour walk. The rover acts as a mobile radio relay and as the shelter: every point of every plan stays within a set walking time of the rover, wherever it is parked or driving. Every plan is checked at least every 5 m for the thread (air to get back with a reserve), the buddy rule, the walk to the rover, and radio shadows; the thread holds in 1,000 of 1,000 random scenarios.
4. *The app.* The Habitat Planner shows the map with each layer's source, the three plans side by side with a "price of safety" line (Safest gives up 43% of the science value and gains 76 minutes of margin against Most science), a timeline, an assumptions panel, and a 3D rehearsal with Curiosity Navcam photos placed where they were taken. The Visor HUD overlays the first-person view with at most four elements in white and cyan, each with its own shape, checked against simulated colour blindness. The Cuff Tablet has 64-pixel controls, a "what you'll see" photo for each station, the four station steps, and a sample log that works offline. The printed cuff card fits one page with abort routes to the rover.
5. *Storm replay.* The May 20, 2024 event (a far-side eruption DONKI logs at 05:22 UTC; JPL reports that an astronaut beside Curiosity would have received 8,100 micrograys) starts in the middle of the walk. The alert comes on cue, storm mode takes over, and both walkers head for the rover; the panel sets RAD's figure beside modeled doses with and without the rover.

**Benefits.** It turns ten kinds of open NASA data (terrain, elevation, rover positions, rover images, ChemCam, THEMIS, RAD, DONKI, Horizons and Mars time) into one meter-scale plan a crew can rehearse and follow, with the safety rules enforced by the planner rather than left to memory. It is honest about uncertainty: the rover-walkability check failed in the boxwork (79.8% of Curiosity's positions classed passable against a 95% target) because the ridges sit at the elevation model's resolution limit, so the planner stays conservative and the surfaces mark ground where the map may be over-cautious. The same pipeline built the Murray Buttes site, where that check passes (99.8%).

**What we hope to achieve.** A planning concept that future crews, mission planners and students can pick up and test: any HiRISE terrain model could become a site, and the suit and walking settings, now placeholders, could be replaced by measured values for a real Mars suit.

**Tools.** Python (NumPy, SciPy, scikit-image, rasterio, pyproj, numba, OR-Tools), TypeScript with React, deck.gl and three.js, Vitest, Playwright and axe-core for tests, GitHub Actions and GitHub Pages. Code licensed Apache-2.0. SI tools: Claude (claude.ai), which generated the concept and plan, and Claude Code, which wrote the code (see Use of SI).

## Use of Super Intelligence (SI)

Yes. The project idea was generated by SI. At our request, Claude (Anthropic's assistant, on claude.ai) generated the ARIADNE concept, the project plan (docs/PLAN.md) and the build brief (PROMPT.md) from the challenge statement on November 8, 2026 (UTC). This happened before the 2026 Project Submission Guide was published on November 13, 2026, which says SI should not be used to come up with the idea; we state both facts plainly. Claude also researched sources, reviewed each phase report, and proposed most of the decisions we then approved or rejected. Claude Code (Anthropic's AI coding assistant) wrote the pipeline and web app code, ran the data processing, tests and checks, and drafted the documents, including this text. Our team chose the challenge, directed the work, approved or rejected each decision, got clearance from our Local Lead, and is responsible for the submission. Every source file carries the line "Written with AI assistance (Claude Code)", every commit from the kickoff on carries an "AI-assisted: Claude Code" trailer, the packaged data records it in its metadata, and the app's footer and the video's end card say so. No images, video or audio were generated by AI, with one exception: the ARIADNE mark (the small symbol beside the name and the browser-tab icon), which Claude Code drew at our request as SVG code from two straight strokes and a dot, with no image generator. All other imagery is real NASA mission imagery with its credit. Full account, decision by decision: https://github.com/vyom-aggarwal/ARIADNE/blob/main/AI_USE.md

## NASA Data

- **USGS MSL Gale merged 1 m elevation model and 25 cm orthophoto mosaic**, built from HiRISE (NASA/JPL-Caltech/University of Arizona) and CTX (NASA/JPL-Caltech/MSSS) images: terrain, slopes, horizons, the 3D view. https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m and https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm
- **MGS MOLA 463 m elevation model** (NASA/GSFC): distant horizons such as Mount Sharp. https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m
- **MSL PLACES localizations** (NASA/JPL-Caltech, PDS): Curiosity's positions, site boxes, the georeferencing and walkability checks. https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/
- **Curiosity raw images** (NASA's raw-image API; Courtesy NASA/JPL-Caltech): Navcam photos placed in the 3D view and the tablet. https://mars.nasa.gov/api/v1/raw_image_items/
- **MSL ChemCam LIBS tables** (NASA/JPL-Caltech/LANL/IRAP, PDS) and **NASA's Curiosity blog**: prior targets and the four boxwork drill holes. https://pds-geosciences.wustl.edu/msl/msl-m-chemcam-libs-4_5-rdr-v1/ and https://science.nasa.gov/blog/
- **HiRISE footprints** (PDS Orbital Data Explorer) and **THEMIS night infrared** (NASA/JPL-Caltech/ASU, through NASA Mars Trek). https://oderest.rsl.wustl.edu/ and https://trek.nasa.gov/
- **RAD radiation results:** the Murray Buttes measurement (Ehresmann et al. 2021, doi:10.1029/2021JE006851) and JPL's report of the May 20, 2024 storm. https://www.jpl.nasa.gov/news/nasa-watches-mars-light-up-during-epic-solar-storm/
- **CCMC DONKI** space-weather database: the May 2024 CMEs. https://api.nasa.gov/ (DONKI)
- **JPL Horizons**: Earth-Mars light time. https://ssd.jpl.nasa.gov/horizons/
- **NASA GISS Mars24** algorithm and **NAIF** MSL clock: Mars time and sun position. https://www.giss.nasa.gov/tools/mars24/
- **NASA technical reports:** NASA/TP-2010-216125 (suited walking: tested ranges), Ross and Eppler 2015 (NASA JSC: field geology), the NSSDCA Mars Fact Sheet. https://ntrs.nasa.gov/citations/20110003409 and https://ntrs.nasa.gov/citations/20150003504

## Space Agency Partner Data and Other References

**Space agency partner data:**

- **ESA (European Space Agency):** HRSC images from Mars Express (ESA/DLR/FU Berlin) are among the stereo images behind the USGS Gale elevation model; the X12 estimate for the May 20, 2024 flare came from the ESA/NASA Solar Orbiter mission (as JPL reports); DONKI's record of that eruption uses the ESA/NASA SOHO LASCO coronagraph.

**Other references:**

- Ehresmann, B. et al. (2021), Natural radiation shielding on Mars measured with the MSL/RAD instrument, JGR Planets, doi:10.1029/2021JE006851.
- Guo, J. et al. (2021), Radiation environment for future human exploration on the surface of Mars, Astron. Astrophys. Rev., doi:10.1007/s00159-021-00136-5.
- Minetti, A. E. et al. (2002), Energy cost of walking and running at extreme uphill and downhill slopes, J. Appl. Physiol. 93:1039.
- Kirk, R. L. et al. (2008, 2021) on HiRISE elevation models and their resolution.
- Machado, G. M., Oliveira, M. M. and Fernandes, L. A. F. (2009), colour vision deficiency simulation, IEEE TVCG 15(6).
- Allison, M. and McEwen, M. (2000), Mars time, Planet. Space Sci. 48 (Mars24).
- IERS leap-second table; W3C WCAG 2.1.
- SI tools: Claude (claude.ai) and Claude Code, both by Anthropic; how they were used is in the Use of SI field and AI_USE.md.
- Software: React, deck.gl, three.js, Vite, Vitest, Playwright, axe-core, NumPy, SciPy, scikit-image, rasterio and GDAL, pyproj, shapely, numba, Google OR-Tools, pandas, astroquery, jsonschema. Every package and its license is listed in CREDITS.md.
- Every dataset, image, value and library, with its URL and license: https://github.com/vyom-aggarwal/ARIADNE/blob/main/CREDITS.md
