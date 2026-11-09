# ARIADNE progress

Last updated: 2026-11-08 (Phase 2 started).

## Status

| Phase | Status |
| --- | --- |
| Kickoff | Done. Sources for Phases 1 and 2 verified (docs/SOURCES_LOG.md); findings applied to PROMPT.md and docs/PLAN.md |
| 0 Repo and guardrails | Done 2026-11-08: all ten acceptance tests pass; CI green; site live at https://vyom-aggarwal.github.io/ARIADNE/ |
| 1 Sites and data | Done 2026-11-08: B1 to B7 pass in CI; B8 to B10 pass on the real crops (docs/coverage/) |
| 2 Derived layers | In progress: spec changes applied and sources verified; plan and tests below |
| 3 to 9 | Not started |

## Human decisions (2026-11-08)

- **Clearance:** approved by the team's Local Lead to build before November 14.
- **Repo and site:** the GitHub repo is public (it already was) and GitHub Pages is to be enabled in Phase 0.
- **Setup:** pip venv with prebuilt wheels (bundled GDAL); the Makefile is the single source of commands and CI runs it on Linux; locally, GNU make through Chocolatey from Git Bash; PLAN.md moves to docs/.
- **Python version:** use 3.13 locally if OR-Tools and numba install there, otherwise pin 3.12. Result below: both work, so no pin.
- **Open items kept open:** the Photojournal boxwork set (Phase 4) and DONKI (Phase 6).
- **Phase 2 spec changes (2026-11-08):** (1) far-field horizons: 2 km on the 1 m DEM, then to about 100 km on a coarse regional DEM, reporting the sunrise and sunset shift; (2) calibrate n so that S(parking spot) / S(the RAD study's baseline positions) = 0.96, with far-field horizons at both; (3) use Ehresmann et al. 2021 (doi:10.1029/2021JE006851) for the Murray Buttes figures and Guo et al. 2021 (doi:10.1007/s00159-021-00136-5) for a dose-pressure coefficient, verified first; (4) drill sites Altadena, Valle de la Luna, Nevado Sajama and Nevado Sajama2, sols from NASA's Curiosity blog and positions from PLACES; (5) describe the Mars24 example mismatch as rounding unless it can be shown otherwise. Applied to PROMPT.md and docs/PLAN.md; evidence in docs/SOURCES_LOG.md (Phase 2 verification pass).

## Kickoff findings that change the plan

Full evidence is in docs/SOURCES_LOG.md. PROMPT.md and docs/PLAN.md now carry these corrections.

1. **PLACES moved.** Use https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/data_localizations/localized_interp.csv. The old `MSLPLC_1XXX` URL returns 404. The table uses the same equirectangular meters as the USGS mosaics.
2. **The 25 cm orthophoto is about 50 GB**, not 23 GB. It is uncompressed with one row per strip, so windowed reads work but are slow (about 15 s per 100 m square). Crop each site once and cache it. The HiRISE color COG is fast but covers only the boxwork, not Murray Buttes.
3. **The DEM is not cloud-optimized either** (one row per strip). A site crop over `/vsicurl/` should take a few minutes; cache it.
4. **HiRISE-grade elevation over the boxwork is likely.** Public HiRISE DTM DTEEC_019698_1750_019988_1750 (the USGS "T3" pair) covers 100% of the rover path and 96% of the site box, and DTEEC_009149_1750_009294_1750 ("Traverse") covers 100% of the path. Ames Stereo Pipeline gap-fill is probably unnecessary; the Phase 1 coverage report will confirm.
5. **Site boxes:** boxwork = sols 4527 to 4852, rover extent 514 × 924 m, buffered box E 8,141,606 to 8,145,119 m, N −286,731 to −282,807 m. Murray Buttes parking spot = site 57, drive 2798, about E 8,141,565, N −278,307. Both boxes fall inside the DEM and the 25 cm mosaic.
6. **THEMIS on Trek is 8-bit display imagery**, not calibrated thermal inertia, so the sand proxy is relative only.
7. **The REMS daily feed is "outreach purposes only."** Use it only for the Now display, labeled; compute from the PDS REMS bundle, which runs to sol 4843.
8. **Boxwork drill samples: three in 2025, plus a fourth in January 2026.** NASA (Feb 23, 2026) reports three samples collected in 2025 (ridgetop, hollow bedrock, transitional area) and a fourth collected recently for wet chemistry. The Curiosity blog for sols 4798 to 4803 shows that fourth hole, "Nevado Sajama2", beside the earlier "Nevado Sajama" hole on sol 4795 (January 31, 2026). The kickoff note "three, not four" was incomplete and is corrected.
9. **MSL sol definition:** sol 0 is the touchdown sol, and the mission clock is LMST at 137.42° E (Mars24 notes). The REMS feed confirms all five sol fixtures to within one day.
10. Prior science targets come from ChemCam oxide tables (target name, SCLK, distance) joined to PLACES by SCLK.

## Decisions

- **Python:** pip venv at `.venv/` with prebuilt wheels. On 2026-11-08, Python 3.13.14 on this Windows machine installed and ran OR-Tools 9.15.6755 (CP-SAT solve and routing manager), numba 0.68.1 (an `njit` function), rasterio 1.5.2, NumPy 2.5.4, SciPy 1.18.1, scikit-image 0.26.0, astroquery 0.4.11, pyproj 3.8.0, shapely 2.2.0, pandas 3.1.1 and pytest 9.2.0. So there is no 3.12 pin: `requires-python >= 3.12`, and CI tests 3.12 and 3.13 on Linux.
- **make:** the Makefile is the single source of commands; CI runs it on Linux. GNU make is not yet installed on this machine (`choco install make` from an administrator shell adds it); until then the same commands run directly.
- **Node:** Node 24 LTS locally and in CI (`.nvmrc`).
- **GitHub Actions:** current majors that run on Node 24: checkout v7, setup-python v7, setup-node v7, configure-pages v6, upload-pages-artifact v5, deploy-pages v5.
- **Deploys only after green CI:** deploy.yml runs when the CI workflow succeeds on `main` (or by manual dispatch) and builds the commit that CI tested.
- **Raw data cache:** `data/` (gitignored). Expect about 1 GB per site for crops; the full 50 GB mosaic is never downloaded.
- **Line endings:** `.gitattributes` keeps LF in the repo, since this machine has `core.autocrlf` on and CI is Linux.

## Phase 0 plan: repo and guardrails

Build the skeleton every later phase plugs into, with the project rules enforced by tests from the first commit.

1. Move PLAN.md to docs/ (done) and apply the kickoff findings to PROMPT.md and docs/PLAN.md (done).
2. Add LICENSE (Apache-2.0, official text), README.md shaped like the Space Apps project form, AI_USE.md, CREDITS.md, `.gitignore`, `.gitattributes`, `.nvmrc`.
3. Pipeline skeleton: `pipeline/pyproject.toml` (package `ariadne`), a CLI with the commands from PROMPT.md section 8 that say clearly which phase builds them, and a guardrails module for repo checks.
4. Web skeleton: Vite, React and TypeScript placeholder page with Vitest, Playwright and axe-core.
5. Makefile with every target from CLAUDE.md, plus the smaller targets CI uses.
6. `.github/workflows/ci.yml` and `deploy.yml`; enable GitHub Pages with the Actions source.

### Phase 0 acceptance tests

| ID | Test | Where |
| --- | --- | --- |
| A1 | LICENSE is the Apache-2.0 text; README.md, AI_USE.md, CREDITS.md, CLAUDE.md, PROMPT.md and docs/PROGRESS.md, SOURCES_LOG.md and PLAN.md exist | `pipeline/tests/test_guardrails.py` |
| A2 | Every source file (Python, TypeScript, JavaScript, CSS, HTML, YAML, TOML, Makefile) starts with the one-line AI-assistance header | `pipeline/tests/test_guardrails.py` |
| A3 | No API keys, tokens or secrets in any tracked file | `pipeline/tests/test_guardrails.py` |
| A4 | Every commit after the two pre-rule commits ends with "AI-assisted: Claude Code" | `python -m ariadne.guardrails trailers` in CI |
| A5 | OR-Tools (CP-SAT and routing), numba, rasterio and the rest of the stack import and run on Python 3.12 and 3.13 | `pipeline/tests/test_environment.py`, CI matrix |
| A6 | `python -m ariadne --help` lists every command; commands not built yet exit with code 2 and name the phase that builds them | `pipeline/tests/test_cli.py` |
| A7 | The placeholder page shows the ARIADNE heading, a plain-English summary, and links to the source code, AI use and credits; it has one main landmark and one h1 | `web/tests/App.test.tsx` |
| A8 | Every npm package in the lockfile has an allowed open license | `web/scripts/check-licenses.mjs` |
| A9 | The built page has no axe-core WCAG 2.1 A or AA violations in Chromium, and every link can be reached with the Tab key | `web/e2e/placeholder.spec.ts` |
| A10 | CI is green on `main`, the deploy workflow succeeds, and the Pages URL serves the placeholder heading | GitHub Actions and a fetch of the Pages URL |

### Phase 0 evidence

- **Commits:** `bd960a8` kickoff docs; `c54ec4d` license, AI disclosure, credits, README; `f878dc6` web placeholder and tests; `8eba763` pipeline skeleton, guardrails, Makefile, CI; `67f0179` Pages deploy.
- **Local run:** 52 pipeline tests pass on Python 3.13 (A1 to A6), ruff clean, all three guardrails pass; 17 Vitest tests pass (A7, A8 unit tests); `npm run licenses` passes for all 138 npm packages (A8); 4 Playwright tests pass on the production build in Chromium (A9: no axe WCAG 2.1 A/AA violations in light or dark mode, all links reachable by Tab, visible focus outline, standards mode despite the header comment before the doctype).
- **CI:** run 42533117810 on `67f0179`: Pipeline (Python 3.12) success, Pipeline (Python 3.13) success, Web success. This was the first real run of the Makefile, since GNU make is not installed on this machine.
- **Deploy:** run 42533196737 (build and deploy both succeeded), triggered by the green CI run. Pages is enabled with the GitHub Actions source and HTTPS enforced. Fetching https://vyom-aggarwal.github.io/ARIADNE/ returned HTTP 200 with title "ARIADNE"; its script (HTTP 200) renders the "ARIADNE" h1 and the summary text, and its stylesheet returns HTTP 200 (A10).
- **Self-review:** the page shows no data values, so no labels are due yet; it says plainly that it is a placeholder. Every library is credited with its license; all licenses are OSI-approved. No NASA graphics, no AI-generated media, no secrets.

## Phase 1 plan: sites and data

Turn the kickoff checks into a repeatable `make fetch SITE=<site>` that crops every source to a site box, records where each file came from, and proves the crops sit in the right place.

1. **Time.** Mars24 (GISS algorithm, steps A to D) and MSL mission time in `pipeline/ariadne/models/`. TT − UTC comes from the IERS leap-second table, bundled with its expiry date. MSL sol N starts at local mean midnight at 137.42° E, with sol 0 the touchdown sol. Touchdown is 2012-08-06 05:17:57 UTC per NAIF's MSL LMST clock kernel (`naif-msl-lmst`), which also gives sol 0's midnight at the actual landing site, an independent check.
2. **Site configs.** `config/sites/boxwork.yaml` (Curiosity's localizations between 2025-05-01 and 2026-03-31 UTC, buffered by 1.5 km, PLACEHOLDER) and `config/sites/murray-buttes.yaml` (the parking position held from 2016-09-09 to 2016-09-21, buffered by 2 km, PLACEHOLDER, so horizons are complete), plus `config/sources.yaml` listing each source with its URL, product ID, resolution, credit and license.
3. **Fetch with provenance.** Download PLACES once; derive the site box; snap it outward to each source's pixel grid; read the window in parallel row bands over `/vsicurl/`; write Cloud Optimized GeoTIFFs (DEM float32 with nodata −32767; orthophoto uint8 with nodata 0; HiRISE color where it covers the site). Every product gets a provenance record with the fields PROMPT.md section 3 lists. Re-running skips products whose record matches.
4. **Coverage.** Query ODE for the footprints of the 12 USGS HiRISE stereo pairs and the public HiRISE DTMs; a pair's stereo footprint is the overlap of its two images. Rasterize onto the DEM crop grid as a source-class mask (HiRISE stereo, or "CTX, HRSC or MOLA", which the USGS metadata does not let us separate), and report the share of the site box and of the rover path in each class.
5. **Georeferencing checks.** Sample the DEM crop at Curiosity's positions and compare with PLACES elevations; search horizontal shifts of ±10 m for the best fit; check that the crops share bounds; write a quicklook PNG (hillshade, orthophoto and rover path) for a visual check.
6. **Reports.** `docs/coverage/<site>.md` (committed, stamped with the pipeline version) holds the box, sols, coverage and check results; the fetch also rewrites a marked fetch-log block in docs/SOURCES_LOG.md. Raw crops stay in `data/` (gitignored).

### Phase 1 acceptance tests

Tests B1 to B7 run in CI on fixtures and synthetic rasters; B8 to B10 run on the real crops during `make fetch`, with results committed in `docs/coverage/`.

| ID | Test | Where |
| --- | --- | --- |
| B1 | Both GISS Mars24 worked examples reproduce every listed value from A-2 to C-5, plus the heliocentric distance, longitude and latitude, to the printed precision (1e-5). Declination, zenith, azimuth and the Spirit LTST match within 0.001° (LTST 1e-4 h): in the Spirit example the printed declination and LTST differ from what the printed formulas give from the printed inputs by 0.00025° and 0.00005 h, more than rounding of those inputs explains (a test shows the arithmetic); the page does not say why. All gaps are under one arcsecond | `pipeline/tests/test_mars24.py` |
| B2 | TT − UTC is 64.184 s in 2000 and 2004, 67.184 s in August 2012, and 69.184 s from 2017; dates past the table's expiry raise a clear warning | `pipeline/tests/test_mars24.py` |
| B3 | MSL sols: touchdown is sol 0; sol 0 midnight at 137.442° E matches NAIF's 2012-08-05 13:49:59 UTC, and NAIF's linear clock at sols 1000, 3000 and 5000, within 10 s (first planned at 2 s; the measured gap is 5.8 to 6.6 s, see the note below); the five caption fixtures match within one day; a sample of about 95 REMS daily-feed sols matches its dates within one day and its Ls within 1.5° | `pipeline/tests/test_msl_time.py` |
| B4 | Provenance records carry every required field and a valid label, and survive a round trip through a sidecar file and GeoTIFF tags | `pipeline/tests/test_provenance.py` |
| B5 | A crop read in parallel row bands equals one direct window read; its bounds cover the request and lie on the source pixel grid | `pipeline/tests/test_raster.py` |
| B6 | Site boxes from a fixture extract of real PLACES rows: the boxwork rover extent and the Murray Buttes parking position (site 57, drive 2798) match the kickoff values | `pipeline/tests/test_sites.py` |
| B7 | Footprint rasterization gives the exact mask for synthetic polygons; a stereo pair covers only where both images overlap; coverage shares add up to 100% | `pipeline/tests/test_coverage.py` |
| B8 | Crops are georeferenced: the median of (DEM − PLACES elevation) along Curiosity's path is within 2 m, and the best-fit horizontal shift is within 2 m of zero | `docs/coverage/<site>.md` |
| B9 | The coverage report exists for both sites, with box and rover-path shares by DEM source class and the gap-fill decision | `docs/coverage/<site>.md` |
| B10 | Every crop in `data/sites/<site>/` has a provenance record, and the fetch-log block in docs/SOURCES_LOG.md lists it | fetch run, `pipeline/tests/test_fetch_outputs.py` (skipped when `data/` is empty, as in CI) |

**B3 tolerance change (2026-11-08).** Before writing the test, a check showed that Mars24's mean solar time starts each MSL sol 6.6 s earlier than NAIF's LMST clock kernel at sol 0, and 5.8 s earlier at sol 5000. The two are independent models: NAIF's is a 2012 linear fit anchored at landing; Mars24's constants were revised in 2015. The gap is about 1/15,000 of the one-day tolerance PROMPT.md requires, so B3 uses 10 s for the NAIF comparison and keeps the measured values in its assertion message.

The thresholds in B8 are team targets, set before the real crops were read: 2 m allows for any offset between PLACES' rover reference point and the ground, and for localization error, while still catching a misregistration of a few pixels.

### Phase 1 evidence

- **Commits:** `239e66d` Mars24 and MSL sols; `3cbc58f` site configs, provenance and crops; `0455713` coverage mask, georeferencing check and fetch command; `3b4bf99` both sites fetched, reports and fetch log. CI passed on every one; the last is run 42538161863 (Python 3.12, Python 3.13 and web all green).
- **Tests:** 124 pipeline tests pass locally on Python 3.13; in CI the B10 data checks skip because `data/` is not committed, and the committed reports are checked instead.
- **Time (B1 to B3):** both Mars24 worked examples match; touchdown is sol 0; the five caption fixtures and 93 REMS feed sols match within one day, with Ls within 1.5°; NAIF's clock agrees within 10 s (measured 5.8 to 6.6 s).
- **Fetch results** (`docs/coverage/boxwork.md`, `docs/coverage/murray-buttes.md`):

| | Boxwork | Murray Buttes |
| --- | --- | --- |
| Box | 3,514 × 3,925 m, sols 4526 to 4853 (2,893 localizations) | 4,000 × 4,000 m around site 57, drive 2798 (held sols 1455 to 1468) |
| DEM crop | 3,514 × 3,925 px, 32 s | 4,001 × 4,001 px, 35 s |
| Orthophoto crop | 14,056 × 15,697 px, 41 s | 16,001 × 16,001 px, 40 s |
| Color crop | 14,056 × 15,697 px, 13 s | not made (the color mosaic does not cover it) |
| HiRISE stereo share (box; localizations) | 100%; 100% of 8,945 | 100%; 100% of 16,064 |
| Pairs covering the box | T3 95.7%, Traverse 79.4%, West 26.2% | West 69.0%, Traverse 48.9%, West of Center 32.7% |
| Median DEM − PLACES elevation | −0.00 m (MAD 0.10 m) | +0.01 m (MAD 0.07 m) |
| Best-fit shift | (0, 0) m | (0, 0) m |
| B8 result | PASS | PASS |

- **Visual check:** in both quicklooks Curiosity's localizations follow valley floors and pass the parking spot without crossing cliffs.

### Phase 1 decisions

- **Sol windows** use every sol that overlaps the configured UTC days, so the boxwork runs from sol 4526 to 4853 (the kickoff's linear estimate gave 4527 to 4852). The rover extent is unchanged.
- **Murray Buttes box** is the parking position ± 2 km, as PROMPT.md describes, rather than the extent of every localization in the window. PLACES has one row per drive, so "parked" means the localization with the longest gap until the next one (13 sols).
- **Orthophoto reads** use HTTP range requests for only the bytes inside the window (benchmarked about 7 times faster than GDAL with identical output); the DEM and color mosaics use parallel GDAL row bands.
- **The DEM declares pixel-center georeferencing**; GDAL converts it to corner coordinates on read, and the crops are written as pixel-corner files. The zero best-fit shift confirms there is no half-pixel error.
- **No gap-fill** at either site (team rule: at least 99% of localizations and 90% of the box on HiRISE stereo).
- **Provenance tags** are written with each Cloud Optimized GeoTIFF, because a COG cannot be re-tagged in place; a cached crop without its tag is re-read. This re-read the Murray Buttes DEM crop from the first, failed run.

## Phase 2 plan: derived layers

Turn the crops into the ten layers of PROMPT.md section 4, each a pure function in `pipeline/ariadne/derive/` tested on synthetic terrain, then run them on both sites with `make derive` and write `validation.json` with `make validate`.

1. **Inputs.** Add the MOLA 463 m regional DEM to `config/sources.yaml`, cropped to the site box plus 102 km (100 km far-field reach, PLACEHOLDER, plus a margin) by the existing range reader. Add the THEMIS night-IR tiles (Trek, level 9, about 81 m) for the sand proxy, the ChemCam oxide tables for prior targets, and the four drill sites (sols from the blog, positions from PLACES). Every threshold goes into `config/derive.yaml` and `config/science.json`, marked PLACEHOLDER.
2. **Terrain basics.** Horn slope and aspect, roughness (standard deviation of elevation after removing a best-fit plane in a 5 m window), TPI at 5, 10 and 20 m, local relief.
3. **Horizons.** 72 azimuths. Near field: rays on the 1 m DEM out to 2 km or the crop edge, 1 m steps to 32 m, then steps growing 3% per step, bilinear sampling, curvature drop d²/2R, observer 1 m above the ground (PLACEHOLDER). Far field: on a 100 m coarse grid, rays on MOLA from where the near field stops (less a 100 m overlap) to 100 km, MOLA tied to the 1 m DEM by their median difference; each fine cell takes the interpolated far-field profile maximum, corrected to first order for its own elevation. The horizon is the larger of the two. Stored as a 72-band uint8 COG (0.4° steps from −12° to +90°).
4. **Shielding.** S(n) by the closed form; f(p) = 1 + κ (p − p_ref) / D_ref with κ = −0.21 µGy/day per Pa and D_ref = 300 µGy/day (Guo et al. 2021, the published upper limit and its matching dose), p from elevation with the 11.0 km scale height, and p at Murray Buttes from the paper's 23 g/cm² (about 849 Pa). Calibration: the baseline is Curiosity's position on each of sols 1440 to 1455 and 1468 to 1480 (the mean of S at the positions held at the start and end of each sol, since PLACES gives no drive times); the parking spot is site 57, drive 2798. Find n in 0 to 10 where S(parking) f / mean(S f over baseline sols) = 0.962 (the paper's 3.8%), the n range for 3.4% to 4.2%, and the n for exactly 0.96. Also report the blocked sky (n = 0) at the parking spot against the paper's 19%, and the sensitivity to observer height (0.5 m and 2 m) and to near-field-only horizons.
5. **Walkability** (walker and rover): slope classes (walker go up to 15°, caution 15° to 25°, no-go above 25°; rover go up to 12°, caution 12° to 20°, no-go above 20°; all PLACEHOLDER), roughness, dark-object density (share of 25 cm pixels much darker than their surroundings), a sand proxy (smooth texture, ripple directionality and THEMIS night-IR percentile, all relative within the site) and ridge-edge drop-offs (convex profile curvature with at least 1 m of local relief). Output: class and a continuous cost multiplier. Label MODELED. No boulder sizes (no per-image sun geometry).
6. **Ridges and fractures.** Ridge where TPI10 > +0.3 m and local relief ≥ 0.8 m; hollow where TPI10 < −0.3 m (PLACEHOLDER). Fractures: multi-scale dark-line filter (Sato) on the 25 cm image inside the ridge mask, skeletonized, lines ≥ 10 m kept, written as GeoJSON. Both sites have HiRISE stereo everywhere, so the DEM route applies.
7. **Shelters and time-to-shelter.** Shelter cells: S ≤ 0.95 and walkable, in zones ≥ 4 m² (PLACEHOLDER); the rover counts as a shelter. Minutes-to-shelter by a multi-source least-cost pass (scikit-image MCP) at a PLACEHOLDER walking speed divided by the walkability cost; Phase 3 replaces the speed with the NASA/TP-2010-216125 model.
8. **Line of sight.** Viewshed from the rover antenna (3 m) to a helmet (1.8 m), and a pairwise helmet-to-helmet test (both PLACEHOLDER), by ray marching. The derive run uses a PLACEHOLDER staging point (Curiosity's Altadena drill position at the boxwork; the parking spot at Murray Buttes). Line of sight only; radio is not modeled.
9. **Light.** Sun track from Mars24; shadow where the sun's elevation is below the horizon at its azimuth (interpolated between azimuths); insolation from incidence on the local slope; sunrise and sunset per cell for a reference date; daily insolation relative to flat open ground. Relative ground temperature is implemented and tested as a function of a REMS daily curve, but the REMS archive itself is read in Phase 6, so no temperature map is made yet.
10. **Science value.** Transect triples along ridge crests ≥ 20 m long: a crest point (on a mapped fracture where one lies within 2 m), a wall point 1 to 2 m down the flank, a hollow point 3 to 10 m away, all walkable. Score = weighted sum of hypothesis role, novelty (distance to the nearest ChemCam target or drill hole), spectral context and access, weights in `config/science.json`. CRISM is not read yet, so the spectral term is marked missing and its weight is set aside, not faked.
11. **Uncertainty.** Confidence in 0 to 1 from the DEM source class, the distance to the nearest ground image (Curiosity's localizations stand in for camera positions; PLACES `view_metadata.csv` is the better source, still to check) and model flags (DEM not HiRISE, near-field horizon cut short by the crop edge).
12. **Outputs.** COGs and GeoJSON with provenance in `data/sites/<site>/derived/`; a committed report `docs/derived/<site>.md` (calibration, horizons, the far-field effect on sunrise and sunset, layer summaries); `validation.json` at the repo root with the shielding calibration, the rover-walkability check on Curiosity's path, and the Mars24 and sol checks.

### Phase 2 acceptance tests

C1 to C12 run in CI on synthetic data; C13 to C15 check the committed outputs of the real run, as in Phase 1.

| ID | Test | Where |
| --- | --- | --- |
| C1 | Terrain: a tilted plane gives its exact slope and aspect (four orientations); roughness is zero on flat and tilted planes; TPI is zero on a plane and positive on a bump; local relief of a step equals the step | `pipeline/tests/test_terrain.py` |
| C2 | Near-field horizons: the centre of a cylindrical pit gives atan(depth / radius) within 0.3° in every azimuth; a flat plane gives the curvature dip only; azimuth 90° looks east; quantization round-trips within 0.2° | `pipeline/tests/test_horizons.py` |
| C3 | Far-field horizons: a cone-shaped mountain on a coarse grid gives its analytic angle after the curvature drop, within 0.1°; the tie offset between two DEMs is recovered; the combined horizon is the larger of near and far | `pipeline/tests/test_horizons.py` |
| C4 | Shielding: flat open ground gives S = 1, vertical walls S = 0; the closed form equals numerical integration of cos^n θ over the open sky; the blocked fraction at n = 0 equals mean(sin h); the calibration recovers a known n from synthetic horizons and reports "no fit" when none exists; f(p) is 1 at the reference elevation and follows the hand-computed value elsewhere | `pipeline/tests/test_shielding.py` |
| C5 | Walkability: classes switch at the configured slope thresholds; no-go wins over other factors; cost rises with slope; dark-object density and the sand proxy respond to synthetic dark spots, smooth patches and ripples; a 1 m step is flagged as a drop-off | `pipeline/tests/test_walkability.py` |
| C6 | Ridges and fractures: a synthetic boxwork grid gives ridges on the walls and hollows between; a dark line on a ridge is traced; lines shorter than 10 m are dropped | `pipeline/tests/test_ridges.py` |
| C7 | Shelters: zones smaller than 4 m² and unwalkable cells are dropped; minutes-to-shelter on flat ground equals distance divided by speed (straight and diagonal); the rover point counts as a shelter; unreachable cells are marked | `pipeline/tests/test_shelters.py` |
| C8 | Line of sight: a wall hides what is behind it; flat ground is all visible; the pairwise test is symmetric and depends on height | `pipeline/tests/test_los.py` |
| C9 | Light: shadow exactly when the sun is below the interpolated horizon; insolation equals cos(incidence) for sloped planes; with a constant horizon h0, sunrise is when the sun reaches h0; the relative temperature curve keeps the REMS timing | `pipeline/tests/test_light.py` |
| C10 | Science: transects only on crests of 20 m or more; wall and hollow points at the configured distances and walkable; each score term lies in 0 to 1; novelty grows with distance to prior targets; a missing term is reported, not invented | `pipeline/tests/test_science.py` |
| C11 | Uncertainty: confidence is highest on HiRISE ground near images with no flags, falls with distance and flags, and stays in 0 to 1 | `pipeline/tests/test_uncertainty.py` |
| C12 | Inputs: drill positions are the localizations held on the blog sols; baseline sols give start and end positions; ChemCam file names yield SCLKs; Trek tile indices cover a box; `ariadne derive` and `ariadne validate` are built | `pipeline/tests/test_inputs.py`, `pipeline/tests/test_cli.py` |
| C13 | `validation.json` holds the shielding calibration: n, the ratio, the n range for 3.8% ± 0.4%, the n for 0.96, the blocked-sky check against 19%, the sensitivity runs, the label "calibrated on one RAD measurement", and the sources | `pipeline/tests/test_validation_outputs.py` |
| C14 | `docs/derived/<site>.md` exists for both sites and reports the far-field shift of sunrise and sunset | `pipeline/tests/test_validation_outputs.py` |
| C15 | Every derived product has a provenance record with a label and the pipeline version (skipped when `data/` is empty, as in CI) | `pipeline/tests/test_validation_outputs.py` |

Team targets set before the real run: the calibration passes if some n in 0 to 10 reproduces the ratio; the blocked-sky check is reported, not gated (the paper's horizon mask comes from rover images and a different elevation model); the rover-walkability check passes if at least 95% of Curiosity's boxwork localizations are classed go or caution.

## Next steps

1. Phase 2: write the C1 to C12 tests, then the derive modules; fetch the MOLA crop; run the calibration and the far-field report; then the remaining layers, `make derive` on both sites and `validation.json`.

## Open issues

- DONKI's host timed out from this machine (needed in Phase 6). Retry, then try api.nasa.gov.
- The Photojournal boxwork link now redirects to a generic page (needed in Phase 4).
- Still to find: image positions for the uncertainty layer (PLACES `view_metadata.csv` is the candidate) and a hand-labeled ridge sample for the ridge-map check. The drill sites and the Ehresmann et al. 2021 quantities are now verified.
- Team name and README credits: not given yet; README shows them as "to be added".
- The georeferencing check is not an independent test of height: PLACES records the DEM pixel of each localization, so its elevations are tied to an orbital DEM. The horizontal shift search is the real alignment test. An independent height check would need ground data, such as rover stereo; this is not planned.
- HiRISE coverage edges are uncertain by about 30 m, because ODE rounds footprint vertices. It makes no difference at these two sites, which are fully covered, but it matters for the uncertainty layer elsewhere.
- The orthophoto shows mosaic seams (one is visible in the Murray Buttes quicklook). Phase 2's dark-object density should check that seams do not register as features.
