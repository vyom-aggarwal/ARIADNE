# ARIADNE progress

Last updated: 2026-11-08.

## Status

| Phase | Status |
| --- | --- |
| Kickoff | Done. Sources for Phases 1 and 2 verified (docs/SOURCES_LOG.md); findings applied to PROMPT.md and docs/PLAN.md |
| 0 Repo and guardrails | Done 2026-11-08: all ten acceptance tests pass; CI green; site live at https://vyom-aggarwal.github.io/ARIADNE/ |
| 1 Sites and data | In progress: plan and acceptance tests below |
| 2 to 9 | Not started |

## Human decisions (2026-11-08)

- **Clearance:** approved by the team's Local Lead to build before November 14.
- **Repo and site:** the GitHub repo is public (it already was) and GitHub Pages is to be enabled in Phase 0.
- **Setup:** pip venv with prebuilt wheels (bundled GDAL); the Makefile is the single source of commands and CI runs it on Linux; locally, GNU make through Chocolatey from Git Bash; PLAN.md moves to docs/.
- **Python version:** use 3.13 locally if OR-Tools and numba install there, otherwise pin 3.12. Result below: both work, so no pin.
- **Open items kept open:** the Photojournal boxwork set (Phase 4) and DONKI (Phase 6).

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
| B1 | Both GISS Mars24 worked examples reproduce every listed value from A-2 to C-5, plus the heliocentric distance, longitude and latitude, to the printed precision (1e-5). Declination, zenith, azimuth and the Spirit LTST match within 0.001° (LTST 1e-4 h), because the page's own printed values for those are not consistent with its printed inputs at the 5th decimal; a test demonstrates this | `pipeline/tests/test_mars24.py` |
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

## Next steps

1. Finish Phase 1 as planned above, committing each working piece.

## Open issues

- DONKI's host timed out from this machine (needed in Phase 6). Retry, then try api.nasa.gov.
- The Photojournal boxwork link now redirects to a generic page (needed in Phase 4).
- Still to find in Phase 2: the sols and positions of the four boxwork drill samples, image positions for the uncertainty layer and the hand-labeled ridge sample, and the exact quantities in the Ehresmann et al. 2021 Murray Buttes paper.
- Team name and README credits: not given yet; README shows them as "to be added".
