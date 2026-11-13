# ARIADNE build prompt for Claude Code

For the operator: save this tab as PROMPT.md in an empty Git repository, by downloading it as Markdown or copying the text. Optionally save Tab 1 as docs/PLAN.md for background.

Updated November 8, 2026 with the kickoff source checks, and again the same day with the team's Phase 2 changes (far-field horizons, the RAD baseline, the dose-pressure coefficient, the drill sites and the Mars24 wording). The evidence for every change is in docs/SOURCES_LOG.md; [VERIFIED] marks a checked source and [OPEN] one that still needs work.

Start Claude Code in that folder and say: "Read PROMPT.md and follow it, starting with the kickoff steps." In later sessions, say: "Continue with the next unfinished phase in docs/PROGRESS.md." Check with your Local Lead before generating code ahead of November 14.

Everything below is addressed to Claude Code.

## 1. Role, goal and rules

You are the lead engineer for ARIADNE, an entry in the NASA Space Apps Challenge 2026 (November 14 to 15, 2026) for the challenge "Interplanetary Survival Guide: Martian Map". Build a deployed, tested and scientifically honest web app that plans, rehearses and guards a two-astronaut Marswalk through the boxwork terrain on Mount Sharp in Gale crater, plus a generator that rebuilds it for a second site.

Judges score Impact, Creativity, Validity, Relevance and Presentation; the target Global Awards are Best Mission Concept, Best Use of Data and Best Use of Science. A verified, polished core beats a long feature list, so finish each phase completely before starting the next.

Create CLAUDE.md at the repo root with the rules below, the commands from section 8, and the line @docs/PROGRESS.md. Claude Code loads CLAUDE.md at launch and expands @-imports (docs), so every session starts with the rules and current progress.

1. Never invent data. Every value comes from a fetched source, a computation on fetched data, a documented model, or a labeled placeholder.
2. Label every number the app shows as MEASURED, DERIVED, MODELED or PLACEHOLDER, with its source on hover.
3. Verify before you depend. Fetch every URL tagged [VERIFY] and confirm format and content before coding against it, logging results in docs/SOURCES_LOG.md. If it fails, find the current official location; if there is none, or you lack web access, stop and ask.
4. Credit everything. Add each dataset, library, image and text to CREDITS.md when first used, with its URL and license or credit line.
5. Use no NASA logos, flags, insignia, mission patches or mission identifiers as graphics; mission and instrument names appear only as plain-text citations. Create no AI-generated images, video or audio.
6. Ship a static site: no server, no secrets, no API keys in client code. Live fetches are optional and fall back to bundled snapshots.
7. Write tests first. A phase is done only when its acceptance tests pass in CI.
8. Keep science honest: show uncertainty, label models as models, and claim nothing the checks in section 7 do not support.
9. Meet WCAG 2.1 AA: sufficient contrast, full keyboard access, and color never the only cue.
10. Disclose AI use. README and AI_USE.md describe your role; every source file starts with a one-line AI-assistance header; generated data files record the pipeline version; every commit message ends with the trailer "AI-assisted: Claude Code".
11. Keep docs/PROGRESS.md current: phase status, decisions, evidence, open issues and the next step.
12. Write all user-facing text in plain English.
13. License our code Apache-2.0; use only openly licensed or public-domain third-party material, and record each license.
14. Ask the human before adding paid services or non-OSI-licensed dependencies, deleting cached data, or changing the site.

## 2. Product, scenario and science

ARIADNE is a meter-scale Marswalk navigator with the tagline "Every Marswalk has a thread home." It fuses at least eight NASA data types into one map, then plans, rehearses and guards the walk while always showing a safe way back.

Who uses it:

- EV1 and EV2, the walking pair, through the Visor HUD and the Cuff Tablet.
- IV, the crew member inside, through the Habitat Planner, which plays the Local Mission Control Console role from NASA's SUITS Mars EVA concept.
- The Earth science team, through a view delayed by the current one-way light time.

Scenario: a pressurized rover drives the crew to a staging point near the boxwork. The pair walks a loop of science stations within an EVA budget (PLACEHOLDER: 6 h plus a 30 min reserve), and the rover may relocate to a pickup point.

Core concepts:

- The thread: a continuously recomputed return path to the nearest safe haven, with a consumables margin.
- Buddy rule: the pair stays within a set distance and in mutual line of sight.
- Shelter rule: every point on the route stays within a set walking time of the rover, wherever it is on its relay schedule. Terrain blocks only a few percent of the radiation (3.8% at Murray Buttes), so terrain is not counted as shelter.
- Storm mode: on a solar-particle alert, both crew are routed to the destination with the lowest modeled dose over the event, counting the exposed walk there.
- Rover rendezvous: the rover's position moves the end of the thread.

Science facts to build around, cited in the app:

- Boxwork ridges stand about 1 to 2 m tall with sandy hollows between them and crisscross for miles. The leading idea is that groundwater moving through fractures left minerals that hardened the ridges (NASA, Feb 23, 2026).
- Curiosity confirmed that dark lines seen from orbit are fractures. Nodules occur on ridge walls and in hollows rather than near fractures. Three drill samples collected in 2025 (a ridgetop, bedrock in a hollow, and a transitional area before the ridges) found clay minerals in the ridge and carbonate minerals in the hollow (same source). A fourth sample, a second hole beside the earlier "Nevado Sajama" drill hole, was drilled by sol 4795 (January 31, 2026) for a wet-chemistry run in SAM (same source; Curiosity blog, sols 4798 to 4803).
- The four boxwork drill holes, with sols from NASA's Curiosity blog [VERIFIED] and rover positions from PLACES: "Altadena" (the transitional area at the edge of the boxwork, drilled sol 4564, June 8, 2025); "Valle de la Luna" (bedrock in the "Monte Grande" hollow, drilled on the first sol of the October 17, 2025 weekend plan, hole imaged sol 4693); "Nevado Sajama" (a ridgetop about 10 m away, drill completed sol 4718, November 13, 2025); and "Nevado Sajama2" (beside it, imaged sol 4795). PLACES gives the rover's position while drilling; each hole is within the arm's reach of it.
- On May 20, 2024, particles from an X12-class flare reached Mars within tens of minutes. RAD recorded 8,100 micrograys, about 30 chest X-rays and the largest surge since landing (JPL).
- Parked against a cliff at Murray Buttes from September 9 to 21, 2016, RAD measured 4% less total radiation and 7.5% fewer neutral particles. High solar activity cuts cosmic rays by 30 to 50% (NASA). The paper behind this (Ehresmann et al. 2021, JGR Planets, doi:10.1029/2021JE006851) [VERIFIED] reports 3.8% ± 0.4% less dose on sols 1456 to 1467 than "expected", where the expected dose is a zenith-looking RAD counter (field of view within 30° of the zenith, so the butte cannot block it) scaled to the dose by a fit over sols 1440 to 1455 and 1468 to 1480. The butte and its surroundings blocked about 19% of the sky (0.37π sr, average blocking angle 11°). A later review (Guo et al. 2021, below) estimates 5% ± 1% with a different baseline, the same phase of the four previous solar rotations.
- For the About page: Apollo 14's crew turned back from Cone Crater unsure of their position, and orbital images later showed them about 30 m from the rim (Space.com).

The science objective the planner serves: three-station transects (central fracture, ridge wall, hollow floor) across many ridges, plus an elevation log of every ridge visited.

## 3. Sites, data and conventions

Sites:

- boxwork, the flagship: a bounding box around Curiosity's localization points during the boxwork campaign (initial UTC window 2025-05-01 to 2026-03-31, refined from imagery), buffered by 1.5 km (PLACEHOLDER).
- murray-buttes, for validation only: Curiosity's parking position from September 9 to 21, 2016, buffered by 2 km so horizons are complete.
- frontier, site 2: a HiRISE DTM inside a high-consistency zone of NASA's SWIM ice maps, with Jezero crater as the fallback.

Sol-to-date test fixtures from NASA image captions, UTC, with a tolerance of one day: sol 4190 = 2024-05-20, sol 4220 = 2024-06-19, sol 4636 = 2025-08-21, sol 4650 = 2025-09-05, sol 4677 = 2025-10-02. MSL sol 0 is the landing sol, and the mission clock is local mean solar time at 137.42° E (Mars24 notes); all five fixtures match the REMS daily reports to within one day [VERIFIED].

### Data

| Data | Product and URL | Notes |
| --- | --- | --- |
| Elevation | USGS MSL Gale Merged DEM 1 m: https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif (product page) | 3.6 GB, equirectangular, sphere radius 3,396,190 m, latitude −5.0987 to −4.1296, longitude 137.1242 to 137.6806 E. HiRISE stereo only for the 12 pairs listed on the product page; elsewhere CTX, HRSC or MOLA. The file is not cloud-optimized (one row per strip, no overviews), so read each site crop once and cache it. [VERIFIED: both site boxes fall inside] |
| Imagery | USGS MSL Gale Merged Orthophoto Mosaic 25 cm: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/MSL_Gale_Orthophoto_Mosaic_25cm_v3.tif | About 50 GB (50,404,480,837 bytes; the earlier 23 GB figure was wrong), uncompressed with one row per strip, so windowed reads through GDAL /vsicurl/ work but are slow (about 15 s per 100 m square); crop each site once and cache it [VERIFIED]. Color alternative: https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/MSL/MSL_Gale_HiRISE-LRGB_78quads_sharp_cog.tif, a true cloud-optimized GeoTIFF of 1.03 GB that covers the boxwork but not Murray Buttes [VERIFIED] |
| Elevation gap-fill | HiRISE DTMs: https://www.uahirise.org/dtm/, found through the ODE REST API (https://oderest.rsl.wustl.edu/live2/) [VERIFIED], or build one with Ames Stereo Pipeline: https://github.com/NeoGeographyToolkit/StereoPipeline | Only where HiRISE stereo is missing over the site. Public DTM DTEEC_019698_1750_019988_1750 (the USGS "T3" pair) covers 100% of Curiosity's boxwork path and 96% of the site box, so gap-fill is probably unnecessary there; the Phase 1 coverage report confirms |
| Regional elevation | USGS MGS MOLA DEM 463 m (MEGDR): https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif (product page https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m) [VERIFIED: 2 GB, int16, the same equirectangular projection and 3,396,190 m sphere as the analysis grid, uncompressed with one row per strip, CC0] | Far-field horizons from 2 km to about 100 km, where Mount Sharp's upper slopes rise kilometers above both sites. Elevations are above the MOLA areoid. Co-register it to the 1 m DEM over each site (a horizontal shift plus a height offset, found by matching the 1 m DEM smoothed to MOLA's pixel size): a height offset alone leaves errors of tens of meters on Mount Sharp's slopes, because the two mosaics are offset horizontally by about a MOLA pixel. The sharper HRSC and MOLA blend (200 m) was checked and not used, because its HRSC part is CC BY-SA 3.0 IGO and would put a share-alike condition on every derived layer |
| Global context | Mars Trek WMTS, for example https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg; API docs https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars | Globe intro and context. [VERIFIED: layer endpoints come from the Trek layer index; tiles allow cross-origin reads; CTX layers Gale_CTX_BlockAdj_dd and curiosity_ctx_mosaic] |
| Thermal | THEMIS day and night infrared controlled mosaics, 100 m, through Trek: THEMIS_DayIR_ControlledMosaics_100m_v2_oct2018 and THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018 [VERIFIED] | These are 8-bit display images, not calibrated thermal inertia, so night infrared is only a relative sand proxy (percentile within the site) |
| Spectral | CRISM map-projected targeted products and summary parameters, PDS Geosciences Node: https://pds-geosciences.wustl.edu/ [VERIFIED: ODE finds MTRDR products FRT000058A3 and FRT0000B6F1 (about 18 m) and HRL0000BABA (about 36 m), each covering the whole boxwork box] | 12 to 36 m per pixel; context only |
| Rover positions | MSL PLACES localizations: https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv (moved from the MSLPLC_1XXX path, which now returns 404) [VERIFIED: 49,315 rows to sol 4868; easting and northing in the same projection as the USGS mosaics]. Optional cross-check: https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json [VERIFIED: 1,386 waypoints to sol 5045] | Site box, driven path, photo placement |
| Rover science | MSL Analyst's Notebook: https://an.rsl.wustl.edu/msl, plus PDS Geosciences archives for ChemCam, APXS, CheMin and DAN. Prior targets come from the ChemCam LIBS oxide tables (https://pds-geosciences.wustl.edu/msl/msl-m-chemcam-libs-4_5-rdr-v1/mslccm_1xxx/data/moc/), joined to PLACES by spacecraft clock [VERIFIED]. Drill-sample sols from NASA's Curiosity blog, positions from PLACES (section 2) [VERIFIED] | Prior targets, drill sites, hydrogen along the path |
| Weather | REMS archive, PDS Atmospheres Node: PDS4 bundle at https://atmos.nmsu.edu/PDS/data/PDS4/msl_rems_bundle/, calibrated data to sol 4843 [VERIFIED]; latest public daily report for Now: https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json, which its provider marks for outreach only, so it feeds only the labeled Now display [VERIFIED] | Replay, Now and climatology |
| Radiation | RAD archive, PDS Planetary Plasma Interactions Node: https://pds-ppi.igpp.ucla.edu/ [VERIFY]; plus the published NASA values in section 2. Murray Buttes: Ehresmann et al. 2021, "Natural Radiation Shielding on Mars Measured With the MSL/RAD Instrument", JGR Planets 126, e2021JE006851 (free to read on Wiley) [VERIFIED]. Dose and pressure: Guo et al. 2021, "Radiation environment for future human exploration on the surface of Mars", Astron. Astrophys. Rev. 29:8, doi:10.1007/s00159-021-00136-5 (CC BY 4.0) [VERIFIED] | Baseline and replay; if the archive lacks the needed detail, show only published values. Guo et al. section 3.2 gives the dose-pressure coefficient κ: \|κ\| is 0.1 to 0.2 µGy/day per Pa for most of the mission, with an upper limit of about 0.21 µGy/day per Pa in deep solar minimum, when the mean dose was about 300 µGy/day |
| Space weather | CCMC DONKI: https://kauai.ccmc.gsfc.nasa.gov/DONKI/ and its web services or api.nasa.gov [OPEN: the host timed out on November 8, 2026; retry in Phase 6, then try api.nasa.gov, and check browser CORS]. Example run with a Mars arrival: https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/WSA-ENLIL/30925/1 | Snapshots taken at build time |
| Ground imagery | Photojournal boxwork set: https://photojournal.jpl.nasa.gov/feature/boxwork [OPEN: now redirects to a generic page; find the current location in Phase 4]; PDS Imaging Node: https://pds-imaging.jpl.nasa.gov/ for Navcam and Mastcam with labels [OPEN, Phase 4: the PLACES view_metadata.csv table is a candidate for image positions] | "What you'll see" photos; credit NASA/JPL-Caltech/MSSS |
| Geologic context | USGS SIM 3292, Geologic Map of Mars: https://doi.org/10.3133/sim3292 | Regional units |
| Ice, site 2 | SWIM: https://swim.psi.edu/ [VERIFY download format] | Frontier site choice |
| Ephemerides | JPL Horizons through astroquery.jplhorizons | Earth-Mars distance and light time |
| Mars time | Mars24 algorithm: https://www.giss.nasa.gov/tools/mars24/help/algorithm.html | Implement and test against its worked examples |
| Suited walking | NASA/TP-2010-216125: NTRS PDF [VERIFY by reading] | Transcribe the predictive metabolic model and tested ranges exactly, with page numbers |

Credit lines: NASA/JPL-Caltech/MSSS for Curiosity cameras, NASA/JPL-Caltech/University of Arizona for HiRISE, ESA/DLR/FU Berlin for HRSC inside the merged DEM, and USGS Astrogeology for the mosaics.

Conventions:

- Analysis grid: equirectangular meters on the 3,396,190 m sphere, aligned to the DEM; planetocentric latitude, east-positive longitude.
- Time: UTC internally; display UTC, MSL sol, local true solar time at the site, and season as solar longitude (Ls).
- Dose: absorbed dose in micrograys; never mix it with sieverts.
- Rasters: float32 with explicit nodata; Cloud Optimized GeoTIFF for intermediates; 256 px web tiles.
- Vectors: GeoJSON, the format NASA SUITS specifies for its console map.
- Every product carries a provenance record: source ID, URL, product ID, resolution in meters, acquisition date, processing date, pipeline version and label.

## 4. Derived layers

Implement each layer as a pure function in pipeline/ariadne/derive/, unit-tested on synthetic terrain where the answer is known. Every threshold marked PLACEHOLDER lives in config/ and appears in the app's assumptions panel.

1. Terrain basics: slope by the Horn method, aspect, roughness as the standard deviation of detrended elevation in a 5 m window, and topographic position index (TPI) at 5, 10 and 20 m. Tests: a tilted plane returns its exact slope; a flat plane returns zero roughness.
2. Horizons: horizon elevation angle h in 72 azimuths, in two parts. Near field: out to 2 km (PLACEHOLDER) on the 1 m DEM, sampling more coarsely with distance. Far field: from 2 km (or the edge of the 1 m crop, if nearer) to about 100 km (PLACEHOLDER) on the MOLA 463 m regional DEM, computed on a coarse grid and interpolated, because Mount Sharp's upper slopes rise kilometers above both sites and likely set the horizon uphill. Both parts subtract the planet's curvature (d²/2R); the horizon is the larger of the two. Store as quantized arrays. Report how much the far field shifts sunrise and sunset at each site. Tests: a cell at the bottom of a synthetic cylindrical pit returns the analytic horizon angle; a synthetic distant mountain returns its analytic angle after the curvature drop.
3. Walkability for the suited walker and the rover: go, caution or no-go, plus a continuous cost. Inputs are slope, roughness, dark-object density in the 25 cm imagery, a sand proxy (THEMIS night-infrared percentile plus smooth texture and ripple directionality) and ridge-edge drop-offs (curvature with local relief of 1 m or more). Walker slope classes (PLACEHOLDER): go up to 15°, caution 15 to 25°, no-go above 25°. Label the layer MODELED, and report boulder sizes only if per-image sun geometry is available.
4. Boxwork ridges and fractures: ridges where TPI at 10 m exceeds +0.3 m with local relief of at least 0.8 m, hollows below −0.3 m (PLACEHOLDER thresholds, tuned on a hand-labeled sample). Trace dark central fractures with a multi-scale line filter on the imagery inside the ridge mask; skeletonize and keep lines 10 m or longer. If the DEM over the site is CTX-derived, map ridges from imagery texture only and say so.
5. Radiation shielding index: with zenith weighting cos^n θ, the zenith-weighted open-sky fraction S has the closed form below, averaged over azimuths φ with horizon angle h. Relative dose is D(x) ≈ D_RAD · S(x) · f(p(x)), where f(p) = 1 + κ (p − p_ref) / D_ref uses the published dose-pressure coefficient κ and its matching mean dose D_ref (Guo et al. 2021, section 3.2), and p follows elevation with the 11.0 km scale height from NASA's Mars fact sheet. Calibrate n so that S(parking spot) / S(baseline) = 0.96, where the baseline is the positions the RAD study used as its reference: Curiosity's positions on sols 1440 to 1455 and 1468 to 1480 (Ehresmann et al. 2021), averaged over sols. Use far-field horizons at both. Search n from 0 to 10, report the n range that matches the paper's 3.8% ± 0.4%, and label the result "calibrated on one RAD measurement", or report the mismatch if no n fits. Check the horizons against the paper's 19% blocked sky (n = 0). Tests: flat open terrain gives S = 1; a cell enclosed by vertical walls gives S = 0.
6. Terrain shielding zones and time to the rover: cells with S of 0.95 or less (PLACEHOLDER), walkable and grouped into zones of at least 4 m², are mapped as information only; terrain blocks a few percent of the dose at most, so they are not shelter. The rover (and habitat) is the shelter, with PLACEHOLDER shielding. A reverse Dijkstra on walking time gives minutes to the rover everywhere, for each place the rover parks.
7. Line of sight: viewsheds from the rover antenna at 3 m and between helmets at 1.8 m (both PLACEHOLDER). This is line of sight only; radio propagation is not modeled, and the app says so.
8. Light and ground temperature: sun azimuth and elevation from Mars24; shadow wherever sun elevation is below the horizon angle at the sun's azimuth; insolation from incidence on the local slope. Relative ground temperature comes from the REMS daily curve scaled by insolation ratio and a thermal-inertia class. Label it MODELED and RELATIVE.
9. Science value: generate transect triples along mapped ridge segments 20 m or longer: a fracture point on the crest, a wall point 1 to 2 m down the flank, and a hollow point 3 to 10 m away, each walkable. Score each station as a weighted sum of hypothesis role, novelty (distance to Curiosity's prior targets), spectral context and access, with weights in config/science.json.
10. Uncertainty: per-cell confidence from DEM source class (HiRISE, CTX, HRSC or MOLA, mapped from the stereo-pair footprints listed on the USGS product page), distance to the nearest ground image, and model flags. Render it as hatching and use it as a route penalty.

```latex
S(x) = \frac{1}{N_\phi} \sum_{\phi} \left( 1 - \sin^{\,n+1}\!\big( \max(h_\phi(x),\, 0) \big) \right)
```

Why this form: integrating cos^n θ · sin θ over the open zenith angles, from 0 to 90° − h, gives (1 − sin^(n+1) h)/(n + 1) per azimuth. Dividing by the open-hemisphere value 1/(n + 1) leaves the term inside the sum.

## 5. Route engine

1. Graph: the DEM grid at 1 m, with a 2 m level for long legs; 16-neighbor moves; cost depends on the signed grade along each move, so uphill and downhill differ.
2. Walker model: read NASA/TP-2010-216125 and transcribe its predictive metabolic and speed relationships exactly, with page numbers, into pipeline/ariadne/models/metabolic.py and web/src/core/models/metabolic.ts. Unit-test both against at least three values reported in the paper. Flag any speed, grade, gravity (Mars is 0.38 g) or suit setting outside the tested range as EXTRAPOLATED; if a clean transcription is impossible, use a clearly labeled PLACEHOLDER curve and say so in the app.
3. Edge cost, with presets Safest, Balanced and Most science in config/presets.json that differ by safety settings, not just weights (all PLACEHOLDER): Safest has a 45 min reserve, a 10 min shelter limit and caution (hazard) and uncertainty penalties three times Balanced's; Balanced holds the defaults; Most science keeps Balanced's hard limits, drops the caution penalty and maximises complete transects. Edge cost terms: time Δt, metabolic rate Ṁ for gravity g, grade s and suit, hazard R, relative dose D, and uncertainty U, as in the first formula below.
4. Consumables: track C_left in minutes at the nominal metabolic rate, consumed at the rate Ṁ(t) divided by the nominal rate. C_home(x) is the consumables cost of walking from x to the nearest safe haven at planned pace.
5. Path search: A* with an admissible heuristic (straight-line distance times the minimum cost per meter), then line-of-sight smoothing that never crosses a no-go cell.
6. Cost-to-home field: multi-source Dijkstra from every safe haven on the reversed graph.
7. Leg matrix: in the pipeline, run Dijkstra from each candidate station to build an asymmetric station-to-station cost matrix, and ship it with the site.
8. Station selection as prize-collecting routing over whole transects: each fracture (or crest), wall and hollow transect is one node, visited in that order, with its three station visits and its internal walk as its service time, because the science value is in the comparison. Reference solver: Google OR-Tools routing in Python with a time dimension, service times (PLACEHOLDER: 15 min per station), and an optional-visit disjunction per station penalized by its science value. Browser solver: greedy value-per-minute insertion, then 2-opt, Or-opt and simulated annealing in a Web Worker; benchmark on at least 50 generated scenarios with a target of 95% of the OR-Tools value.
9. Hard constraints, checked at least every 5 m along the route:
   - Thread: the second formula below, with C_reserve = 30 min (PLACEHOLDER).
   - Buddy: the pair moves together; during station work the partner holds an overwatch point within 50 m (PLACEHOLDER) with mutual line of sight, or the station is invalid.
   - Shelter: walking minutes to the rover, wherever it is on its relay schedule, of 20 or less (PLACEHOLDER; Safest 10).
   - Comms: no comm shadow longer than 10 continuous minutes (PLACEHOLDER).
   - Rover: the rover follows its own cost surface (PLACEHOLDER slope limit, sand avoidance) to any pickup point, and the thread ends at the rover. The rover also serves as a mobile comms relay: it moves between a few overwatch points it can reach during the EVA, so more stations stay in line of sight, and the thread ends wherever the rover is.
   - Any violation triggers a re-solve with the offending station removed or the budget tightened.
10. Re-planning during the walk: triggers are pace drifting more than 15% from plan (PLACEHOLDER), a margin crossing its threshold, or an alert. Drop the lowest value-per-minute stations first, re-check every constraint, and show a diff of what changed.
11. Storm mode: for each destination (the rover where it is parked, the most shielded reachable terrain, or staying put), the fastest path from the current position and the modeled dose over the event: the exposed walk (S along the path) plus the rest of the event at the destination's S. Take the destination with the lowest dose; the rover's S stays a labeled PLACEHOLDER. Show the MODELED dose avoided over the event duration, taken from replay data or marked PLACEHOLDER.
12. Output: plan.json plus GeoJSON layers, following the schema below.

```latex
c(e) = \Delta t_e \left[ w_t + w_m\,\dot{M}(g, s_e, \text{suit}) + w_r\,R(e) + w_d\,\hat{D}(e) + w_u\,U(e) \right]
```

```latex
C_{\text{left}}(x) - C_{\text{home}}(x) \geq C_{\text{reserve}} \quad \text{for every sampled point } x \text{ on the route}
```

```json
{
  "site": "boxwork",
  "scenario": { "start_utc": "<ISO 8601 UTC>", "preset": "balanced", "suit_profile": "default", "rover_profile": "default" },
  "stations": [ { "id": "S01", "role": "fracture", "xy_m": [0.0, 0.0], "value": 0.0, "service_min": 15, "label": "MODELED" } ],
  "legs": [ { "from": "STAGING", "to": "S01", "path_xy_m": [[0.0, 0.0]], "minutes": 0.0, "consumables_min": 0.0, "relative_dose": 0.0 } ],
  "margins": [ { "t_min": 0.0, "c_left": 0.0, "c_home": 0.0, "c_reserve": 30.0 } ],
  "checks": { "thread": "pass", "buddy": "pass", "shelter": "pass", "comms": "pass", "rover": "pass" },
  "provenance": { "pipeline_version": "<semver>", "inputs": ["<source IDs>"] }
}
```

## 6. Interfaces

Five surfaces share one state store. The Habitat Planner and Visor HUD mirror the console and head-mounted display in NASA's SUITS 2023 to 2024 Mars EVA concept, which cites communication delays of up to 20 minutes each way (mission description).

Habitat Planner, desktop:

- 2D map with deck.gl OrthographicView in site meters; a layer panel showing source, resolution, date and label for each layer; legends and opacity.
- Three route options side by side: duration, distance, consumables used, minimum margin, worst time to the rover, relative dose, stations and science value, plus a price-of-safety line: the science value Safest gives up and the margin it gains against Most science.
- An assumptions panel listing every PLACEHOLDER setting and site-level notes, including that slope no-go classes in boxwork terrain are conservative (the rover check found about 20% false alarms on Curiosity's path).
- Timeline: margin curve, station blocks, sun elevation and comm-shadow segments.
- 3D view in three.js: chunked terrain with level of detail and the imagery as texture. First-person rehearsal at eye height (PLACEHOLDER: 1.7 m) with a speed control, Curiosity photos as billboards at their capture points facing their view direction, and an orbit-versus-ground toggle.
- EVA mode: live map of EV1, EV2 and the rover (simulated from the plan in the demo), pins, caution and warning, mission elapsed time and time at each station, mirroring the SUITS console requirements.
- Earth backroom: the same state delayed by the current light time, with a queue for suggestions.

Visor HUD, an overlay on the first-person view at 1920×1080:

- At most four elements at once, kept in the periphery; white and cyan with dark outlines, never red or orange; every color paired with a shape.
- Slope no-go cells in a DEM seam zone or a low-confidence zone are marked "map may be over-cautious here, check by eye"; the planner still avoids them.
- Heading and distance to the next station; the thread drawn as a line home with the margin in minutes; buddy bearing, distance and suit status; caution and warning, with an arrow to the lowest-dose refuge in storm mode; breadcrumbs and dropped pins.
- Voice commands through the Web Speech API where the browser supports it: "distance home", "next station", "drop pin".

Cuff Tablet, 1024×768:

- Touch targets of at least 64 CSS px (PLACEHOLDER for gloved use).
- The same "map may be over-cautious here, check by eye" marking as the HUD.
- Next-station card with a "what you'll see" photo, and station steps following "Look, Observe, Describe, Document" from SUITS.
- Sample log with a photo field stored locally; works offline through a service worker.

Other surfaces:

- Printed cuff card: a print stylesheet producing one page with the route map, stations, bearings and distances, landmark thumbnails, abort routes to the rover and the timeline.
- Judge tour: a three-minute guided overlay covering story, layers, plan, rehearsal, HUD, storm replay, Validation tab and site 2.
- About and Data pages: provenance table, credits, AI disclosure, limitations, and the Apollo 14 story.

## 7. Time Machine and validation

One scenario clock drives every condition, in three modes: Now, Future date and Replay.

- Mars24: pure functions for Mars sol date, local true solar time, solar longitude (Ls) and the subsolar point, with tests that reproduce the GISS worked examples.
- MSL sols: verify the MSL mission-time definition, then pass the sol fixtures in section 3.
- Light time: a table built from JPL Horizons through astroquery for every date the app needs, interpolated; test three dates against Horizons to within 1 s.
- Weather: archived REMS for replay sols; the latest public report for Now, fetched at build time; same-season values from earlier Mars years for Future dates, labeled as climatology.
- Radiation: archived RAD dose rates near the scenario date, otherwise PLACEHOLDER with an explanation.
- Space weather: a DONKI snapshot around each scenario date, showing CMEs with predicted Mars arrival, flares and solar energetic particle events.
- Storm replay preset: align the EVA so the May 20, 2024 event begins mid-walk, raise the alert at the event time, and enter storm mode. Show the measured 8,100 micrograys (MEASURED, JPL) beside modeled doses with and without shelter (MODELED).

make validate writes validation.json, and the app's Validation tab renders it, with site-level notes such as the conservative slope no-go classes in boxwork terrain. Targets are team targets, not published standards.

| Check | Reference | Target |
| --- | --- | --- |
| Shielding index | RAD at Murray Buttes: 3.8% ± 0.4% less dose than expected from the sols 1440 to 1455 and 1468 to 1480 baseline, 7.5% fewer neutral particles, 19% of the sky blocked (Ehresmann et al. 2021) | Calibrated n reproduces S(parking) / S(baseline) = 0.96 within the paper's uncertainty; the blocked-sky fraction and the neutral drop are reported separately |
| Rover walkability | Curiosity's driven boxwork path from PLACES, and the Murray Buttes traverse held out | At least 95% of it classed go or caution; every no-go cell listed as a possible false alarm. The check can only measure false alarms (the cautious direction), not missed hazards |
| Walker model | NASA/TP-2010-216125 values and tested ranges | Matches transcribed values; extrapolation flagged |
| Ridge map | Hand-labeled sample from Curiosity images at known positions | Precision and recall reported |
| Mars24 | GISS worked examples | Every printed value matched to 0.001° or better, most to all five printed decimals |
| Sol conversion | Fixtures in section 3 | Within one day |
| Light time | JPL Horizons | Within 1 s |
| Ground temperature | REMS at Curiosity's position | Daily shape and timing match; absolute values not claimed |
| Browser station solver | OR-Tools reference plans | At least 95% of reference science value |
| Labels | Every number rendered in the app | 100% labeled, checked by an automated UI test |

## 8. Architecture, repo and commands

All heavy processing runs in a Python pipeline at build time; the browser only loads static files and runs the clock, planner and views.

- Pipeline: Python 3.12 or 3.13 (both tested in CI; OR-Tools and numba confirmed on 3.13 on November 8, 2026) with GDAL, rasterio, NumPy, SciPy, scikit-image, pyproj, shapely, numba, OR-Tools, astroquery, pandas and pytest.
- Web app: TypeScript with Vite, React, three.js, deck.gl, Vitest, Playwright and axe-core.
- Hosting: GitHub Actions deploying to GitHub Pages; optional Rust compiled to WebAssembly for path search.

```text
ariadne/
├── CLAUDE.md                 # rules, commands, @docs/PROGRESS.md
├── PROMPT.md                 # this file
├── README.md                 # mirrors the Space Apps project form
├── AI_USE.md
├── CREDITS.md
├── LICENSE                   # Apache-2.0
├── Makefile
├── config/                   # sites/*.yaml, presets.json, suits.json, rovers.json, science.json
├── docs/                     # PROGRESS.md, SOURCES_LOG.md, VALIDATION.md, SUBMISSION.md,
│                             # VIDEO_SCRIPT.md, SLIDES.md, PLAN.md (optional)
├── pipeline/
│   ├── pyproject.toml
│   ├── ariadne/              # fetch/, derive/, models/, plan/, validate/, package/, cli.py
│   └── tests/
├── web/
│   ├── package.json
│   ├── src/                  # core/ (pure logic), workers/, map/, three/, surfaces/, tour/, ui/
│   ├── public/sites/<site>/  # tiles, GeoJSON, snapshots, manifest.json
│   ├── tests/                # Vitest
│   └── e2e/                  # Playwright: judge tour and video capture
├── data/                     # raw cache, gitignored; small manifests committed
└── .github/workflows/        # ci.yml, deploy.yml
```

Makefile targets:

- make setup: create the Python environment and install web dependencies.
- make fetch SITE=boxwork: download or window-read sources and log them in SOURCES_LOG.md.
- make derive SITE=boxwork: build the derived layers.
- make plan SITE=boxwork: build the leg matrix and OR-Tools reference plans.
- make validate: run every check and write validation.json.
- make package SITE=boxwork: write tiles, GeoJSON, snapshots and the manifest into web/public/sites/.
- make site SITE=boxwork: run all of the above in order.
- make test, make e2e and make web-dev.
- New sites through the CLI: ariadne build-site --config config/sites/<name>.yaml, or ariadne build-site --dtm <HiRISE DTM ID or path> --objective ice --name frontier.

Budgets, as team targets: the published site stays under GitHub Pages' 1 GB limit and deploys within its 10-minute limit (GitHub docs). First map in under 3 s on broadband, route re-plan in under 1 s, and a Lighthouse desktop performance score of 80 or more.

## 9. Phases and working method

Work every phase the same way:

1. Write the phase plan and its acceptance tests into docs/PROGRESS.md.
2. Write the tests, then the code.
3. Run the tests and fix until they pass in CI.
4. Self-review for science honesty, labels, credits, licenses and accessibility.
5. Commit with a message starting "phase N:" and ending with the AI trailer.
6. Update PROGRESS.md with status, decisions, evidence and the next step.

Move on to the next phase without waiting. Stop and ask only if a [VERIFY] source fails with no official replacement, a gate cannot pass after a serious attempt, or rule 14 applies.

1. Phase 0, repo and guardrails: CLAUDE.md, PROGRESS.md, SOURCES_LOG.md, CREDITS.md, AI_USE.md, LICENSE, a Makefile skeleton, CI and the Pages deploy.
   - Done when CI is green and the Pages URL serves a placeholder page.
2. Phase 1, sites and data: verification pass for any [VERIFY] source still unchecked (the kickoff verified the Phase 1 and 2 sources); site boxes; windowed reads; HiRISE coverage report; gap-fill if needed (probably not over the boxwork); the Murray Buttes crop.
   - Done when crops are correctly georeferenced, the PLACES path overlays the right terrain, the coverage report exists and the sol fixtures pass.
3. Phase 2, derived layers: all ten layers with synthetic tests, plus the shielding calibration at Murray Buttes.
   - Done when the tests pass, validation.json holds the calibration result, and the far-field effect on sunrise and sunset is reported for both sites.
4. Phase 3, route engine: A*, fields, leg matrix, OR-Tools reference, browser solver, constraints, re-planning and storm mode.
   - Done when the thread holds in 1,000 random scenarios, the browser solver meets its benchmark and plan.json validates against its schema.
5. Phase 4, Habitat Planner: map, layers with provenance, three route options, timeline, and 3D rehearsal with photo billboards. This is the minimum demoable product.
   - Done when the Playwright judge tour passes on a mid-range laptop profile.
6. Phase 5, Visor HUD, Cuff Tablet and printed card.
   - Done when the HUD shows four or fewer elements in every state, a colorblind simulation passes, axe finds no serious issues and the card prints on one page.
7. Phase 6, Time Machine: clock, light time, weather, radiation, DONKI snapshots and the storm replay.
   - Done when the Mars24, sol and light-time tests pass and the replay triggers storm mode on cue.
8. Phase 7, Validation tab: render validation.json and run the label audit.
   - Done when the label test finds no unlabeled number.
9. Phase 8, site 2: the generator builds the frontier site from config with no code changes.
   - Done when it loads and its uncertainty layer is visibly dominant.
10. Phase 9, polish and submission: judge tour, Playwright-recorded footage for the video, README, SUBMISSION.md, VIDEO_SCRIPT.md, SLIDES.md, final credits and AI disclosure.
    - Done when the definition of done in section 10 is met.

If anything slips, phases 0 to 4, the HUD, the storm replay and validation are must-haves. The tablet, the printed card and site 2 are should-haves; voice commands, WebAssembly and live backroom sync are could-haves.

## 10. Deliverables, definition of done and kickoff

Deliverables:

- README.md mirroring the Space Apps project form: project name, high-level summary, demo link, final project link, detailed description (what it does, how it works, benefits, goals, tools and languages), NASA data, Space Agency Partner and other data, use of AI, and references.
- docs/SUBMISSION.md with draft text for each form field.
- docs/VIDEO_SCRIPT.md: a 30-second storyboard with English subtitles, built only from screen captures and real NASA imagery. Beats: 0 to 2 s team and name; 2 to 5 s Apollo 14 hook; 5 to 10 s title and tagline; 10 to 20 s plan, rehearsal and visor; 20 to 27 s storm replay; 27 to 30 s tagline and link.
- A Playwright script that drives the judge tour and records video for that footage.
- docs/SLIDES.md: a backup deck outline of seven slides, including the title slide.
- AI_USE.md, CREDITS.md, LICENSE and validation.json.

Definition of done:

- The GitHub Pages URL works in a private browser window with no login, and the judge tour completes.
- All tests pass in CI; validation.json exists, and the Validation tab shows every check.
- Every number on screen carries a label; CREDITS.md and AI_USE.md are complete; there are no NASA logos and no AI-generated media anywhere.
- Site 2 builds through the CLI.
- README, SUBMISSION.md, VIDEO_SCRIPT.md and SLIDES.md are ready for the team.

Kickoff, do this now:

1. Read this file completely, plus docs/PLAN.md if it exists.
2. Summarize your understanding in at most ten bullets and list any open questions.
3. Create CLAUDE.md and docs/PROGRESS.md, then run the source verification pass for everything Phases 1 and 2 need, logging results in docs/SOURCES_LOG.md.
4. Ask the human to confirm they are cleared to start building. Space Apps asks teams to confirm their work is original, and some Local Leads expect code to be written during the November 14 to 15 event.
5. Once cleared, start Phase 0 and continue phase by phase.
