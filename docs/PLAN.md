# ARIADNE: A Thread Home on Mars — Space Apps 2026 Project Plan

Nov 7, 2026 · @Vyom

Updated Nov 8, 2026 with the kickoff source checks; the evidence is in docs/SOURCES_LOG.md.

## The pitch

ARIADNE is a meter-scale Marswalk navigator: it fuses eight kinds of NASA data into one living map, then plans, rehearses and guards a two-person EVA while always showing the way home. Tagline: *every Marswalk has a thread home.*

In February 1971, Apollo 14's Alan Shepard and Edgar Mitchell turned back short of Cone Crater's rim. They were [not certain where they were](https://webarchive.library.unt.edu/eot2008/20090109112403/http:/www.hq.nasa.gov/office/pao/History/SP-4214/ch12-3.html); Lunar Reconnaissance Orbiter images later showed they had come [within about 30 m](https://www.space.com/7166-moon-photo-reveals-tracks-tough-apollo-moonwalk.html) of it. On Mars, Earth is 3 to 22 light-minutes away, so the crew must navigate, judge risk and re-plan on their own.

ARIADNE stacks orbital imagery, 1 m topography, thermal inertia, mineral spectra, rover chemistry, neutron-derived hydrogen, weather and radiation for one EVA site. It turns that stack into three answers: where the best science is, how to reach it safely in a suit, and how to get home if anything changes.

The flagship site is the boxwork terrain on Mount Sharp that Curiosity explored from mid-2025 to early 2026, a maze of ridges when seen from orbit. In the myth, Ariadne's thread led Theseus out of the labyrinth; here, the thread is a return path recomputed continuously against oxygen, daylight and radiation margins.

One data core drives three screens: a Habitat Planner to plan and rehearse in first person, a Cuff Tablet for the walk, and a Visor HUD showing only what matters next. A site generator rebuilds the whole stack for any HiRISE terrain model, proven on a second site.

## Why this wins

ARIADNE is built to score on all five judging criteria and to compete for three Global Awards: Best Mission Concept, Best Use of Data and Best Use of Science. The 2025 guide names the criteria Impact, Creativity, Validity, Relevance and Presentation ([submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide)); the definitions below come from the [judging guide](https://spaceappschallenge.org/resources/judging-awards-guide). The 2026 versions publish on November 13, so recheck then.

| Criterion | What judges ask | ARIADNE's answer |
| --- | --- | --- |
| Impact | How big is the problem; will it help many? | First Marswalks happen with Earth minutes away. ARIADNE is a reusable site generator, also usable for rover ops and Earth analog field tests. |
| Creativity | Novel, or incremental? | Terrain-shielded radiation routing, two-astronaut buddy routing with rover pickup, rehearsal with real rover photos placed where they were taken, a printed cuff-card fallback. |
| Validity | Scientifically valid; works in the real world? | Every layer cites its product. Models are checked against Curiosity measurements: the Murray Buttes dose drop, boxwork drill results and the rover's own path. |
| Relevance | Complete, feasible, user-friendly? | Covers every objective and every listed consideration. Ships as a live static site with a guided judge tour. |
| Presentation | Is the story told well? | Apollo 14 hook, labyrinth metaphor, 30-second subtitled video and a 7-slide backup. |

The competition is already visible. I found a dozen public GitHub repos for this challenge before the event, and most that name a site use Jezero crater. Slope maps, A\* routes, oxygen budgets, rover photo viewers and toggled solar-storm models appear repeatedly (examples: [Protikriti](https://github.com/AhsanulHoque22/Nasa-Space-Apps-Challenge-2026-Team-Protikriti), [MARSWAY](https://github.com/ahsanur-official/Interplanetary-Survival-Guide-Martian-Map), [Code Huzzlers](https://github.com/RISHI-1453/NASA_Space-Apps_Challenge_Martian_Map)).

Treat those features as table stakes. ARIADNE's edge is what none of those READMEs list: the boxwork site the challenge itself names, radiation shielding validated against a real RAD measurement, buddy-pair routing, a hypothesis-driven science plan built on Curiosity's drill results, and an explicit uncertainty layer.

## Mission scenario and site

The demo mission is one two-astronaut Marswalk through the Mount Sharp boxwork, staged from a pressurized rover. A second, data-poor site then proves ARIADNE is a generator rather than a one-off map.

| Element | Scenario choice | Why |
| --- | --- | --- |
| Site | Boxwork region on Mount Sharp (Aeolis Mons), Gale crater | Ridges 1 to 2 m tall with sandy hollows, crisscrossing for miles, inside the sulfate-bearing layer ([NASA, Feb 2026](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/)) |
| Crew | Two EVA crew as a buddy pair, one crew member inside as local capcom | Covers the challenge's suggestion of working in pairs |
| Mobility | Pressurized rover drives to a staging point, then can relocate to a pickup point | Covers the rover suggestion and lets the safe haven move |
| EVA budget | Configurable suit profile; default 6 h plus reserve | Planning placeholder, shown as an editable assumption |
| Conditions | Real Curiosity weather and radiation records from the boxwork campaign, plus a replay of the May 20, 2024 solar storm | Real data for "current conditions" and a real stress test |
| Earth link | One-way light time computed for the scenario date | Shows why the crew must decide alone |

The boxwork is the right flagship for three reasons. The challenge names it; orbital and ground data overlap there; and the terrain is genuinely hard. Curiosity's drivers described ridges barely wider than the rover and sandy hollows where wheels can slip, which is exactly where a walking geologist outperforms wheels.

The second site exercises "frontier mode": no rover ground truth, so the uncertainty layer carries the story. Pick a HiRISE terrain model inside a high-confidence zone of NASA's [Subsurface Water Ice Mapping](https://swim.psi.edu/) (SWIM) products, where the science objective becomes accessible water ice. If no suitable terrain model exists there, use Jezero crater instead.

## Science objectives

The EVA tests the leading explanation for the boxwork with dense, paired sampling that a rover cannot match in one day. NASA reports the working idea: groundwater moved through large fractures and left minerals that hardened the ridges, and wind later hollowed out the unhardened rock ([NASA, Feb 2026](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/)).

| Open question (from Curiosity's results) | What the crew does | Layers that drive target choice |
| --- | --- | --- |
| Did cement spread outward from the central fractures? Curiosity confirmed the dark orbital lines are fractures. | Three-station transects on several ridges: fracture, ridge wall, hollow floor | Ridge and fracture map from the 1 m terrain model and 25 cm imagery |
| Why do nodules sit on ridge walls and in hollows, not near fractures? | Photograph and count nodules at each station; map them against fracture distance | Station geometry from the transect planner |
| Does the clay-in-ridge, carbonate-in-hollow contrast hold beyond one pair? | Collect paired samples on many ridges, not one | Distance from Curiosity's boxwork drill holes (three samples from 2025 and a fourth from January 2026), so new ridges score higher |
| How high did the water table reach? | Log the elevation of every boxwork ridge visited | Boxwork extent and elevation range mapped from orbit |
| Where does the sulfate-bearing layer change character? | Spot-check the transition at the loop's far end | Mineral summary parameters from orbital spectra, as regional context |

The human advantage is speed and reach. Curiosity spent months in this terrain and drilled three samples there in 2025, plus a fourth in January 2026 beside the earlier "Nevado Sajama" hole for a wet-chemistry run; a crew can visit a dozen stations in one EVA, walk ridge crests the rover could barely fit on, and step down into sandy hollows without wheel-slip risk. ARIADNE quantifies this as "rover sols equivalent" by comparing the plan with Curiosity's actual pace through the same ground.

Each candidate station gets a science value from hypothesis role, novelty against prior samples and spectral context. The route engine then trades that value against time, risk and the walk home. Orbital spectra run about 12 to 36 m per pixel depending on the observation ([Fraeman et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5101845)), coarser than a ridge, so they set context and never pick individual stations.

## Data layer stack

ARIADNE fuses eight of the challenge's data types from five NASA Mars missions plus NASA's space-weather service, every layer carrying its product ID, resolution and credit line in the app.

| Data type | Mission and instrument | Product and source | Resolution | Used for |
| --- | --- | --- | --- | --- |
| Optical | MRO HiRISE | [MSL Gale Merged Orthophoto Mosaic](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm), USGS | 0.25 m | Basemap, ridge and fracture tracing, boulder detection |
| Optical context | MRO CTX | [Mars Trek tile API](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars) | about 6 m | Approach views and context |
| Topographic | MRO HiRISE and CTX, Mars Express HRSC, MGS MOLA | [MSL Gale Merged DEM](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), USGS | 1 m grid | Slope, roughness, ridge index, sky view, line of sight, shadows |
| Topographic gap-fill | MRO HiRISE | [HiRISE DTM catalog](https://www.uahirise.org/dtm/), or a new DTM built with NASA's Ames Stereo Pipeline | 1 to 2 m | Areas where the merged DEM falls back to coarser sources; probably none on Curiosity's boxwork path, which two public HiRISE DTMs fully cover |
| Topographic, global | MGS MOLA | Mars Trek tiles | 463 m | Planet-to-site zoom |
| Thermal | Mars Odyssey THEMIS | Day and night infrared mosaics via Mars Trek | 100 m | Relative sand proxy (Trek serves 8-bit display mosaics, not calibrated thermal inertia) |
| Spectral | MRO CRISM | Map-projected targeted products with summary parameters, PDS Geosciences Node | 12 to 36 m | Sulfate and clay context |
| Chemical | MSL ChemCam, APXS, CheMin | [MSL Analyst's Notebook](https://an.rsl.wustl.edu/msl), PDS Geosciences Node | Per target | Ground truth at Curiosity's targets and drill sites |
| Geophysical | MSL DAN | PDS Geosciences Node | Along the rover path | Subsurface hydrogen beside the route |
| Atmospheric | MSL REMS | PDS Atmospheres Node (PDS4 bundle to sol 4843); the daily public feed is for outreach only, so it feeds only the labeled Now display | Point time series | Temperature, pressure, UV and wind at the site |
| Radiation | MSL RAD, MAVEN SEP | PDS Planetary Plasma Interactions Node and published NASA values | Point time series | Baseline dose, storm replay, shielding validation |
| Space weather | CCMC DONKI, fed by NASA's Moon to Mars Space Weather Analysis Office | [DONKI](https://kauai.ccmc.gsfc.nasa.gov/DONKI/) and its API (timed out at kickoff; recheck in Phase 6) | Event lists | Predicted CME shock arrival at Mars, flare and particle alerts |
| Rover position and point of view | MSL localization, Navcam, Mastcam, MAHLI | [PLACES localization table](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv), PDS Imaging Node, [Photojournal boxwork set](https://photojournal.jpl.nasa.gov/feature/boxwork) (now redirects to a generic page; replace in Phase 4) | Per drive | Rover path, photo placement, "what you'll see here" |
| Geologic context | USGS-NASA Planetary Geologic Mapping Program | [Geologic Map of Mars, SIM 3292](https://doi.org/10.3133/sim3292) | 1:20,000,000 | Regional unit context |
| Ice, site 2 only | MRO, Mars Odyssey and MGS data via SWIM | [SWIM products](https://swim.psi.edu/) | Regional | Choosing the frontier site |

Check one thing before building: per its USGS metadata, the merged DEM uses HiRISE stereo only where it exists and falls back to CTX, HRSC or MOLA elsewhere. Confirm true HiRISE coverage over the boxwork footprint first, and gap-fill if needed. Kickoff result: public HiRISE DTMs DTEEC_019698_1750_019988_1750 and DTEEC_009149_1750_009294_1750 each cover all of Curiosity's boxwork path, and the first covers 96% of the site box. Keep every credit line, such as NASA/JPL-Caltech/MSSS, and credit ESA/DLR/FU Berlin for HRSC.

## Derived safety and science layers

Eight derived layers turn raw data into decisions; each is computed in the build pipeline and each states how it is checked.

| Derived layer | Built from | Method | How it is checked |
| --- | --- | --- | --- |
| Walkability | DEM, 25 cm imagery, THEMIS | Slope (Horn method), roughness of detrended elevation in a 5 m window, boulders of about 1 m and up from shadow detection, sand from the night-infrared proxy plus image texture, ridge-edge drop-offs from curvature | Classes compared with Curiosity's Navcam and Mastcam views at known positions |
| Boxwork ridges and fractures | DEM, 25 cm imagery | Topographic position index at 5 to 20 m scales separates ridges from hollows; line detection traces the dark central fractures | Matched against ridges and hollows on Curiosity's route |
| Radiation shielding index | DEM horizons, elevation | Open-sky fraction from horizon angles in 72 azimuths, weighted toward the zenith because low-angle particles cross more atmosphere, then scaled for air column | Must reproduce RAD's 4% drop beside the Murray Buttes cliff in September 2016 |
| Shelters and time-to-shelter | Shielding index, rover position, walking cost | High-shielding cells plus the rover become shelters; a cost-distance pass gives minutes-to-shelter everywhere | Route stays inside a chosen limit, because May 2024's particles reached Mars within tens of minutes |
| Line of sight | DEM | Viewsheds from the rover antenna and between crew helmets | Flags comm shadows behind ridges; enforces the buddy rule |
| Light and ground temperature | DEM, Mars24 sun position, REMS, THEMIS night IR | Sun angle from the [Mars24 algorithm](https://www.giss.nasa.gov/tools/mars24/help/algorithm.html), cast shadows from horizons, relative temperature from REMS daily curves scaled by insolation and thermal inertia | Compared with REMS ground temperature at Curiosity's position |
| Science value | Ridge map, drill sites, CRISM, objectives | Score per station: hypothesis role, novelty, spectral context | Weights visible and editable |
| Uncertainty | DEM source mask, image coverage, model flags | Per-cell confidence from DEM source, distance to ground imagery and model assumptions | Drawn as hatching; adds a route penalty; HUD says "unverified ground" |

The shielding index is the layer judges will probe, so state it as a formula. S is the open-sky fraction weighted by zenith angle θ; D is the predicted dose relative to RAD's open-terrain baseline, with f a small correction for air column at local pressure p.

```latex
S(x) = \frac{\int_{\text{open sky}} \cos^{n}\theta \, d\Omega}{\int_{\text{hemisphere}} \cos^{n}\theta \, d\Omega}, \qquad D(x) \approx D_{\text{RAD}} \cdot S(x) \cdot f\big(p(x)\big)
```

Be honest about the exponent n. If it is fitted to Murray Buttes, label the model "calibrated on one RAD measurement" rather than validated, and show it as a relative dose, never a measured one. The [NASA write-up](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/how-nasas-curiosity-rover-is-making-mars-safer-for-astronauts/) also reports a 7.5% drop in neutral particles there, a second number to compare against.

The DEM source mask comes from the footprints of the HiRISE stereo pairs listed in the USGS metadata. Walkability shading borrows the idea of "runnability" colors from orienteering maps, which are designed for people navigating on foot.

## Route engine

The engine plans in two layers: a terrain path search prices every step for a suited walker, and an orienteering solver picks and orders the science stations under hard safety constraints. It follows the lineage of NASA analog EVA planners such as SEXTANT, now part of NASA's BASALT field research ([Kluis et al. 2022](https://bhp.engr.tamu.edu/wp-content/uploads/sites/212/2022/02/Kluis-et-al.-2022-A-METHODOLOGY-FOR-ANALYZING-AND-IMPROVING-EVA-PERFORMANCE.pdf)).

Each grid step e costs time Δt multiplied by weighted terms: metabolic rate M for gravity g, slope s and suit; hazard R; relative radiation dose D; and uncertainty U. Slope cost is directional, so uphill and downhill differ. Speed and metabolic terms come from the predictive models in [NASA/TP-2010-216125](https://ntrs.nasa.gov/api/citations/20110003409/downloads/Norcross%20et%20al%202010%2C%20Metabolic%20costs%20%26%20biomech%20of%20inclined%20ambulation%20%26%20exploration%20tasks%20in%20a%20planet%20suit.pdf), suited walking on inclines in simulated reduced gravity; anything outside that study's tested range is flagged as extrapolated.

```latex
c(e) = \Delta t_e \left[ w_t + w_m\,\dot{M}(g, s_e, \text{suit}) + w_r\,R(e) + w_d\,\hat{D}(e) + w_u\,U(e) \right]
```

Path search runs A\* on a 16-neighbor grid with line-of-sight smoothing, in a Web Worker so the interface never freezes. Station selection is a prize-collecting routing problem: each station carries its science value, skipping it costs that value, and the solver maximizes value within the EVA budget. Three weightings ship as presets (Safest, Balanced, Most science), shown side by side like Apollo's planned and contingency traverses.

Ariadne's Thread is the hard constraint behind the name. A reverse cost-distance pass from every safe haven (rover or habitat) gives the cost of getting home from anywhere. At every point x on the route, consumables left C\_left must cover that return cost C\_home plus a reserve, or the plan is rejected.

```latex
C_{\text{left}}(x) - C_{\text{home}}(x) \geq C_{\text{reserve}} \quad \text{for every point } x \text{ on the route}
```

Three more constraints ride along. The buddy rule keeps both crew within a set distance and in mutual line of sight, and plans the moments one waits while the other samples. The shelter rule keeps every point within a set time-to-shelter. The rover rule lets the rover relocate to a pickup point on its own cost surface, which moves the end of the thread and shortens the walk home.

| Planner setting | Default | Status |
| --- | --- | --- |
| EVA budget | 6 h plus reserve | Placeholder, editable per suit profile |
| Return reserve | 30 min at nominal metabolic rate | Placeholder, editable |
| Buddy separation | 50 m with line of sight | Placeholder, editable |
| Time-to-shelter limit | 20 min | Placeholder, motivated by May 2024's tens-of-minutes particle arrival |
| Rover profile | Wheel slope limit and sand avoidance | Tuned to Curiosity's boxwork experience |

During the walk, ARIADNE re-plans whenever actual pace drifts from the plan, a margin crosses a threshold, or an alert arrives. It drops the lowest-value stations first and shows exactly what changed. On a solar-particle alert it switches to storm mode: fastest path to the best reachable shelter, with the estimated dose avoided.

&#91;embedded content: EVA re-planning loop · 5 steps, 1 decision\]

The loop has one rule: no change reaches the visor without passing the same thread, buddy, shelter and comms checks as the original plan.

## Interfaces

One data core drives five surfaces, and the two main ones mirror NASA's own Mars EVA concept. NASA's [2023 to 2024 SUITS mission description](https://nasa.gov/wp-content/uploads/2023/09/fy24-suits-mission-description.pdf) pairs an in-suit display with a Local Mission Control Console because a Mars crew faces delays of up to 20 minutes each way.

| Surface | Who and when | What it shows | NASA SUITS requirement it meets |
| --- | --- | --- | --- |
| Habitat Planner | Inside crew member and both EV crew, before and during the EVA | Layer stack with provenance, three route options, first-person rehearsal at helmet height with real Curiosity photos placed where they were taken, live map of EV1, EV2 and rover, mission and per-station timers, caution and warning | Console live 2D map, timers, caution and warning, pins synced as GeoJSON |
| Cuff Tablet | EV crew during the walk | Glove-sized controls, next-station card with a "what you'll see" photo, station steps using "Look, Observe, Describe, Document", sample log with photo, works offline | Procedures and science data reporting |
| Visor HUD | EV crew, eyes up | Heading and distance to the next station, the glowing thread home with margin in minutes, buddy position and suit status, shelter arrow during alerts, dropped pins | Mini-map, breadcrumbs, best-path return, companion telemetry, caution and warning |
| Printed cuff card | Backup if electronics fail | One-page map per EVA: route, stations, bearings, landmark photos, abort routes | Covers the challenge's "static snapshot" option |
| Earth backroom | Science team on Earth | The same view delayed by the current light time, with suggestions queued for the next re-plan | Delay-tolerant operations |

The HUD follows a few strict rules. Show at most four elements at once, keep them in the periphery, and never use red or orange symbology against Mars' ochre ground; use white and cyan with dark outlines instead. Pair every color with a shape so colorblind users lose nothing, and accept voice commands such as "distance home".

The printed card is a deliberate nod to the paper cuff checklists and traverse maps Apollo crews carried. It shows judges that the system degrades gracefully, and it doubles as the challenge's static-map deliverable.

## Live conditions and Time Machine

A single scenario clock drives every condition, so the same EVA can run on today's real Mars data, on a future date, or on a replayed historical day. This covers all three time frames the challenge suggests.

| Condition | Now | Future date | Replay |
| --- | --- | --- | --- |
| Local time, season, sun | Mars24 local true solar time and season; terrain-aware sunrise from DEM horizons | Same, computed ahead | Same, for the replay date |
| Weather | Latest REMS sols at Gale | REMS values from the same season in past Mars years | Archived REMS for that sol |
| Radiation baseline | Recent RAD values | RAD from a comparable phase of the solar cycle, since high solar activity cuts cosmic rays by 30 to 50% ([NASA](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/how-nasas-curiosity-rover-is-making-mars-safer-for-astronauts/)) | Archived RAD for that date |
| Space weather | DONKI events with predicted Mars arrival | Not forecastable; shown as "unknown" | Archived DONKI records |
| Earth link | One-way light time from JPL ephemerides | Same, computed ahead | Same, for the replay date |

The headline demo is the May 20, 2024 replay. That day an X12-class flare's particles reached Mars within tens of minutes, and RAD recorded 8,100 micrograys, the biggest surge since landing, about 30 chest X-rays for an astronaut beside the rover ([JPL](https://www.jpl.nasa.gov/news/nasa-watches-mars-light-up-during-epic-solar-storm/)). RAD's PI added that cliffsides would provide additional shielding.

In the replay, the crew is mid-EVA in the boxwork when the event begins. ARIADNE flips to storm mode, routes both crew to the best reachable shelter, and shows modeled dose with and without shelter. Every number is labeled measured or modeled, and the measured one comes from Curiosity in Gediz Vallis channel on Mount Sharp, a months-long drive from the boxwork it reached in 2025.

DONKI's model runs already list predicted CME shock arrival times at Mars, for example a [May 2024 run](https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/WSA-ENLIL/30925/1) predicting arrival on May 17. ARIADNE turns those lines into a plain banner: storm expected in N hours, keep EVAs inside the shelter limit.

## Scientific validity

Every model in ARIADNE is checked against a real measurement or reference, and every number on screen carries one of four labels: measured, derived, modeled or placeholder. Pass targets below are team targets, not published standards.

| Model | Checked against | Pass target | Shown in the app as |
| --- | --- | --- | --- |
| Radiation shielding index | RAD beside the Murray Buttes cliff, Sept 9 to 21, 2016: 4% lower total dose, 7.5% lower neutral particles | Reproduces the 4% drop with one fitted exponent; neutral drop reported as an independent comparison | "Calibrated on one RAD measurement" |
| Rover walkability | Curiosity's actual drive path through the boxwork, from the PLACES table | At least 95% of the driven path classed go or caution; every no-go cell on it reviewed as a false alarm | Map of disagreements |
| Suited walker model | Tested ranges in NASA/TP-2010-216125 | Any speed, grade or gravity outside the tested range is flagged | "Extrapolated" badge |
| Ridge and fracture map | Ridges, hollows and fractures visible in Curiosity images at known positions | Precision and recall reported on a hand-labeled sample | Scores in the Validation tab |
| Sun position | Worked examples on the GISS Mars24 algorithm page | Matches to rounding | Pass or fail |
| Ground temperature | REMS ground temperature at Curiosity's position | Daily shape and timing match; absolute values not claimed | "Relative" |
| Light-time | JPL Horizons distance for the scenario date | Within 1 second | Pass or fail |
| Browser station picker | OR-Tools reference plans on the same scenarios | Within a few percent of reference science value | Benchmark table |

What ARIADNE does not claim is just as visible. It is a planning concept, not flight software; radiation outputs are relative estimates; suit parameters are placeholders until a Mars suit exists. Rocks smaller than about a meter are not reliably visible from orbit, so the HUD reminds the crew that the last meter is theirs to judge.

All results live in a Validation tab and in a validation.json file in the repo. Judges can rerun them with one command, which turns "trust us" into "check us".

## Architecture and tech stack

ARIADNE ships as a static website: all heavy processing runs in a Python pipeline at build time, and the browser only loads files and runs the planner. With no server to fail, the link stays up through global judging, which runs into January 2027.

&#91;embedded content: ARIADNE architecture · 3 stages, 13 components\]

The pipeline turns NASA products into tiles, GeoJSON and dated event records, each tagged with its source; the browser adds the clock, the planner and the views, with live feeds as an optional extra that falls back to cached snapshots.

| Part | Choice | Why |
| --- | --- | --- |
| Pipeline | Python 3.12 with GDAL, rasterio, NumPy, SciPy and scikit-image | Standard open tools for planetary rasters |
| Coordinates | Local equirectangular grid in meters on the 3,396,190 m Mars sphere used by the USGS products | Distances stay exact, with no Earth-projection errors |
| Station selection | Google OR-Tools in the pipeline for reference plans; a TypeScript heuristic in the browser for live re-plans, benchmarked against it | OR-Tools has no official browser build |
| Ephemerides | JPL Horizons via astroquery, baked into a light-time table | Exact Earth-Mars distance for any scenario date |
| Front end | TypeScript, Vite, React, three.js for 3D, deck.gl orthographic view for the 2D map | Well documented and fast on ordinary laptops |
| Path search | Web Worker, with optional Rust compiled to WebAssembly | Target: re-plans in under a second without freezing the interface |
| Tests | pytest, Vitest, Playwright and axe-core | The judge tour runs as an automated test |
| Hosting | Public GitHub repo plus GitHub Pages, deployed by GitHub Actions | No server and no keys; published Pages sites may be no larger than [1 GB](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), so tile only the site box |

## Claude Code build plan

Give Claude Code this doc as docs/PLAN.md and build in ten gated phases; a judge-ready demo exists after phase 4, and every later phase is upside.

The ready-to-use Claude Code prompt lives in its own tab: Claude Code prompt.

Put the non-negotiables in a CLAUDE.md file at the repo root, which Claude Code reads at the start of every session. Never invent a data value: fetch it or mark it a placeholder. Label every number as measured, derived, modeled or placeholder; add each source to CREDITS.md the moment it is first used; keep the site static; write tests before features; never use NASA logos or mission insignia.

1. Phase 0, repo and guardrails. Monorepo with pipeline/, web/ and docs/; Apache-2.0 LICENSE; AI\_USE.md disclosure; CREDITS.md; a GitHub Actions workflow that builds and deploys to Pages.
   - Done when CI is green and the Pages URL loads.
2. Phase 1, site and data. Pull Curiosity's boxwork-campaign drives from the PLACES table (sols 4527 to 4852, mid-2025 to early 2026; sol 4636 was Aug 21, 2025) to set the site box. Read windows of the USGS DEM and orthomosaic, build the HiRISE coverage mask from the stereo pairs in the USGS metadata, and gap-fill from the HiRISE DTM catalog or Ames Stereo Pipeline where needed.
   - Done when the crops are correctly georeferenced, the rover path overlays the right terrain, and a coverage report exists.
3. Phase 2, derived layers. Implement the eight layers as pure functions, tested on synthetic terrain where answers are known (a tilted plane's slope, a pit's open-sky fraction). Add a second small crop at Curiosity's Murray Buttes parking spot from September 2016.
   - Done when synthetic tests pass and the Murray Buttes check is written to validation.json.
4. Phase 3, route engine. Directional A\*, cost-to-home field, station selection, and the thread, buddy, shelter and rover constraints.
   - Done when the thread holds in 1,000 random scenarios and the browser heuristic is within a few percent of OR-Tools.
5. Phase 4, Habitat Planner. Layer map with provenance pop-ups, three route options, a timeline with margins, 3D terrain and first-person rehearsal with Curiosity photos at their capture points.
   - Done when a Playwright test completes the judge tour end to end on a mid-range laptop.
6. Phase 5, Visor HUD, Cuff Tablet and printed cuff card.
   - Done when the HUD never shows more than four elements, passes a colorblind simulation, and the card prints on one page.
7. Phase 6, Time Machine. Scenario clock, Mars24, light-time table, REMS, RAD and DONKI snapshots, the May 20, 2024 replay and storm mode.
   - Done when Mars24 output matches the GISS worked examples and the replay triggers storm mode on cue.
8. Phase 7, Validation tab with every check from the validity section.
   - Done when a test confirms that every number on screen carries a label.
9. Phase 8, second site through a generator command, for example ariadne build-site with a DTM ID and an objective.
   - Done when site 2 builds with no code changes and its uncertainty layer is visibly dominant.
10. Phase 9, polish and submission: judge tour, video capture, slides, README, credits, AI disclosure, accessibility and performance passes.
    - Done when every link works in a private browser window without a login.

Must have: phases 0 to 4, the HUD, the May 2024 replay, the Validation tab and submission. Should have: Cuff Tablet, printed card and the second site. Could have: voice commands, WebAssembly path search and live Earth-backroom sync.

## Demo, video and slides

Submit a 30-second video as the demo, with English subtitles burned in, and keep a 7-slide deck as the backup and for the local pitch. Over either limit, the project is ineligible for Global Judging. The storyboard follows the beats the [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide) recommends.

| Time | Picture | Subtitle and voice-over |
| --- | --- | --- |
| 0:00 to 0:02 | Team name over a slowly turning Mars globe | "Team \[name\] presents ARIADNE." |
| 0:02 to 0:05 | Apollo 14 traverse photo, then the boxwork from orbit | "1971: two moonwalkers turned back 30 meters short of their goal. They couldn't tell where they were." |
| 0:05 to 0:10 | Globe dives to Mount Sharp; title and tagline appear | "On Mars, Earth is up to 22 light-minutes away. ARIADNE: every Marswalk has a thread home." |
| 0:10 to 0:20 | Layers stack up, three routes draw, first-person rehearsal past a real Curiosity photo, then the visor with the glowing thread | "Eight kinds of NASA data become one meter-scale plan, rehearsed in 3D, then guided from the visor." |
| 0:20 to 0:27 | May 2024 storm replay: alert, storm mode, both crew rerouted to a cliff shelter | "When the real May 2024 solar storm hits, ARIADNE routes both astronauts to shelter." |
| 0:27 to 0:30 | Tagline, live link, QR code | "Any site on Mars. Every step home." |

Record screen captures of the real app and real NASA imagery with credit lines. Use your own voices, and either no music or music you made yourselves; that avoids AI-watermark and copyright issues entirely.

The backup deck, seven slides including the title:

1. Title: ARIADNE, tagline, team members, challenge name.
2. The problem: Apollo 14's missed rim, Mars light delay, what the challenge asks.
3. The product: screenshots of planner, rehearsal and HUD.
4. The data: eight data types and five Mars missions as a plain grid, with no logos.
5. Safety you can check: the thread home, storm replay and the Murray Buttes validation.
6. The science: boxwork transects and the rover-sols comparison.
7. What's next: any-site generator, alignment with NASA's SUITS concept, live link.

For a live local pitch, follow the same arc inside the app's judge tour: hook, plan, rehearse, visor, storm, Validation tab, second site. Keep the recorded video ready as a fallback if the venue network or a laptop fails.

## Rules and submission checklist

Tick every box before pressing "Submit for Judging"; each one comes from the 2025 [submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide), [judging guide](https://spaceappschallenge.org/resources/judging-awards-guide) or [terms and conditions](https://spaceappschallenge.org/legal), pending the 2026 versions.

- [ ] Every member registered and confirmed, not waitlisted, at the same Local Event; six members at most.
- [ ] Submitted to "Interplanetary Survival Guide: Martian Map" before 11:59 p.m. local time on November 15; submission is final.
- [ ] Demo is a video of 30 seconds or less with English subtitles, or 7 slides or fewer including the title.
- [ ] Demo and final-project links are public with no login, tested in a private browser window.
- [ ] All project-page content is in English.
- [ ] NASA Data field names each NASA product and how it was used; Global Awards require NASA data.
- [ ] Partner and other data listed, including ESA's HRSC inside the merged DEM and the SWIM products.
- [ ] References cite every resource, including code libraries, images and text, with licenses for non-NASA material.
- [ ] Use of AI field explains how Claude Code was used; AI-generated code and data acknowledged in descriptive text and metadata; any AI image or video carries a visible watermark.
- [ ] Nothing generated uses NASA logos, flags or mission identifiers; mission names appear only as plain-text data citations.
- [ ] No copyrighted music, images or text without permission, and no names, voices or likenesses of anyone under 18.
- [ ] Repo carries an OSI license; NASA applies Apache 2.0 if none is given.
- [ ] No commercial promotion and no export-controlled information.
- [ ] Local Lead asked whether code written before November 14 is acceptable under the "all work is original" confirmation; safest is to plan now and generate code during the event.
- [ ] 2026 submission and judging guides reread when they publish on November 13.

## Risks and fallbacks

The two risks most likely to sink the project are missing high-resolution terrain over the boxwork and overclaiming the science; both have a fallback decided in advance.

| Risk | Mitigation | Fallback |
| --- | --- | --- |
| Boxwork lacks HiRISE-grade elevation data (unlikely: two public HiRISE DTMs cover the rover path) | Coverage report in phase 1; gap-fill from the HiRISE DTM catalog or Ames Stereo Pipeline | Move the site box to the nearest HiRISE-covered boxwork and say so on screen |
| Science overclaimed | Four-label system, uncertainty layer, "calibrated on one measurement" wording | Remove any number that cannot be labeled |
| Huge source files (the 25 cm mosaic is about 50 GB and not cloud-optimized) | Windowed remote reads; crop to the site box early | Download once, crop locally, cache the crops |
| Live feeds down or blocked by browser cross-origin rules | Build-time snapshots ship in the bundle | Live fetch switches off automatically, with a visible "snapshot" badge |
| Site too heavy for GitHub Pages or judges' laptops | Tile pyramids, level of detail, published site under 1 GB, deploys under GitHub's 10-minute limit | 2D mode switches on when WebGL is weak |
| Scope creep | Phase gates; demo-ready after phase 4 | Cut voice, WebAssembly, live backroom sync, then site 2, in that order |
| Live demo fails at the local event | Offline build on a laptop | Play the recorded video |
| Look-alike projects | Lead with the boxwork, the thread home and the storm replay in the first 10 seconds | Point judges to the Validation tab |
| Pre-event code ruled out | Ask the Local Lead now; plan-only before November 14 | Run the full build during the event from this plan |

## Sources

Pages marked "opened" were read in full; "search" means the fact came from a search result and should be reopened before it appears in the submission.

| Source | Supports | Access |
| --- | --- | --- |
| [Space Apps Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/) | 2026 dates and timeline | Opened |
| [Space Apps Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide) | Demo limits, AI rules, data fields, criteria names | Opened |
| [Space Apps Judging & Awards Guide](https://spaceappschallenge.org/resources/judging-awards-guide), 2024 edition | Criteria definitions, ten Global Awards | Opened |
| [2025 Participant Terms and Conditions](https://spaceappschallenge.org/legal) | Licensing, citation, minors, video rights | Opened |
| [NASA's Curiosity Rover Sees Martian 'Spiderwebs' Up Close](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/), NASA, Feb 23, 2026 | Boxwork facts, drill results, rover-driving difficulty | Opened |
| [Curiosity Blog, Sols 4798-4803: Back for More Science](https://science.nasa.gov/blog/curiosity-blog-sols-4798-4803-back-for-more-science/), NASA, 2026 | Fourth boxwork drill sample (Nevado Sajama2, sol 4795) | Opened |
| [NASA Watches Mars Light Up During Epic Solar Storm](https://www.jpl.nasa.gov/news/nasa-watches-mars-light-up-during-epic-solar-storm/), JPL, June 10, 2024 | May 20, 2024 event and RAD dose | Opened |
| [How NASA's Curiosity Rover Is Making Mars Safer for Astronauts](https://www.nasa.gov/missions/mars-science-laboratory/curiosity-rover/how-nasas-curiosity-rover-is-making-mars-safer-for-astronauts/), NASA, Nov 15, 2021 | Murray Buttes shielding, solar-cycle effect | Opened |
| [Mars MSL Gale Merged DEM 1m](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m), USGS | DEM coverage, fallback sources, Mars sphere radius | Opened |
| [NASA SUITS 2023-2024 Mission Description](https://nasa.gov/wp-content/uploads/2023/09/fy24-suits-mission-description.pdf) | In-suit display plus local console, 20-minute delay | Opened |
| [Mars MSL Gale Merged Orthophoto Mosaic 25cm](https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm), USGS | 25 cm mosaic and file size (about 50 GB) | Opened |
| [Fraeman et al. 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5101845) | CRISM and THEMIS resolutions over Mount Sharp | Search |
| [Norcross et al. 2010, NASA/TP-2010-216125](https://ntrs.nasa.gov/api/citations/20110003409/downloads/Norcross%20et%20al%202010%2C%20Metabolic%20costs%20%26%20biomech%20of%20inclined%20ambulation%20%26%20exploration%20tasks%20in%20a%20planet%20suit.pdf) | Suited walking on inclines | Search |
| [Kluis et al. 2022](https://bhp.engr.tamu.edu/wp-content/uploads/sites/212/2022/02/Kluis-et-al.-2022-A-METHODOLOGY-FOR-ANALYZING-AND-IMPROVING-EVA-PERFORMANCE.pdf) | SEXTANT and BASALT planner lineage | Search |
| [DONKI WSA-ENLIL run, May 2024](https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/WSA-ENLIL/30925/1) | Predicted CME arrival at Mars | Timed out at kickoff; recheck in Phase 6 |
| [Mars24 algorithm](https://www.giss.nasa.gov/tools/mars24/help/algorithm.html), NASA GISS | Mars solar time and worked examples | Opened |
| [MSL PLACES localization table](https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv) | Rover positions | Opened |
| [MSL Analyst's Notebook](https://an.rsl.wustl.edu/msl) | ChemCam, APXS, CheMin access | Search |
| [Photojournal boxwork set](https://photojournal.jpl.nasa.gov/feature/boxwork) | Point-of-view images | Redirects to a generic page; replace in Phase 4 |
| [Geologic Map of Mars, SIM 3292](https://doi.org/10.3133/sim3292), USGS | Regional geologic context | Search |
| [SWIM project](https://swim.psi.edu/) | Ice maps for the frontier site | Search |
| [Mars Trek tile API](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars) | Global and context tiles | Opened |
| [HiRISE DTM catalog](https://www.uahirise.org/dtm/) | Terrain gap-fill | Opened |
| [NASA History SP-4214, Apollo 14 chapter](https://webarchive.library.unt.edu/eot2008/20090109112403/http:/www.hq.nasa.gov/office/pao/History/SP-4214/ch12-3.html) | Crew uncertain of position | Search |
| [Space.com on LRO's view of Apollo 14 tracks](https://www.space.com/7166-moon-photo-reveals-tracks-tough-apollo-moonwalk.html) | About 30 m from Cone Crater's rim | Search |
| [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | 1 GB site, 10-minute deploys | Search |
| Rival repos: [Protikriti](https://github.com/AhsanulHoque22/Nasa-Space-Apps-Challenge-2026-Team-Protikriti), [MARSWAY](https://github.com/ahsanur-official/Interplanetary-Survival-Guide-Martian-Map), [Code Huzzlers](https://github.com/RISHI-1453/NASA_Space-Apps_Challenge_Martian_Map) | Competitive landscape | Search |
