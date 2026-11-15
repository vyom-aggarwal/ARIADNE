# ARIADNE: a thread home on Mars

[![CI](https://github.com/vyom-aggarwal/ARIADNE/actions/workflows/ci.yml/badge.svg)](https://github.com/vyom-aggarwal/ARIADNE/actions/workflows/ci.yml)

ARIADNE plans, rehearses and guards a two-astronaut Marswalk through the boxwork ridges of Mount Sharp in Gale crater. It keeps a safe way back to shelter at every step: if a route would leave the crew without enough oxygen and supplies to get home with a reserve, ARIADNE rejects it.

**Status: ready for NASA Space Apps 2026 (submission closes November 15, 2026).** The planner, the visor, the cuff tablet, the printed card and the May 20, 2024 storm replay all work in the live app. See [docs/PROGRESS.md](docs/PROGRESS.md) for every phase's tests and results, and [docs/SUBMISSION.md](docs/SUBMISSION.md) for the project form text.

This README follows the NASA Space Apps project form.

## Project details

| Field | Entry |
| --- | --- |
| Project name | ARIADNE |
| Team | [team name and members, to be added by the team] |
| Challenge | Interplanetary Survival Guide: Martian Map (NASA Space Apps Challenge 2026) |
| Live site | https://vyom-aggarwal.github.io/ARIADNE/ |
| Source code | https://github.com/vyom-aggarwal/ARIADNE |
| Demo | [30-second video link, to be added by the team]; storyboard and subtitles in [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md), backup deck in [docs/SLIDES.md](docs/SLIDES.md) |

## Summary

ARIADNE plans, rehearses and guards a two-astronaut walk through the boxwork ridges of Mount Sharp, where Curiosity has been exploring since 2025. From NASA and USGS terrain models, orbital images and Curiosity's own positions, a pipeline maps where a suited walker can go, how much sky each spot sees (a guide to radiation shielding), and which ridge, wall and hollow stops would teach the most. It then plans three walks (Safest, Balanced and Most science) that always keep enough air to get back to the rover, with the rover as both radio relay and shelter.

The web app shows those plans on a map with every layer's source, lets you rehearse the walk in 3D past real Curiosity photos, and drives three surfaces for the walkers: a visor display that never shows more than four things at once, a glove-friendly cuff tablet that works offline, and a one-page printed cuff card as the backup. A Validation tab shows every check, including the ones that failed. Every number is labeled measured, derived, modeled or placeholder; the suit and walking settings are placeholders, so the plans are a concept, not mission guidance.

The plan is in [docs/PLAN.md](docs/PLAN.md), progress in [docs/PROGRESS.md](docs/PROGRESS.md), and the full build brief in [PROMPT.md](PROMPT.md).

## How it works

ARIADNE has two parts:

- a **Python pipeline** (`pipeline/`) that runs at build time: it downloads terrain, imagery and rover data, builds the safety and science layers, and plans reference routes;
- a **static web app** (`web/`) that only loads the files the pipeline made. There is no server and no secret key.

## What you can do in the app

- **Habitat Planner:** the boxwork map with every layer's source, resolution, date and label; three routes side by side with a price-of-safety line; a timeline; an assumptions panel; a 3D rehearsal at walking height past Curiosity photos placed where they were taken.
- **Visor HUD:** the walk seen through the visor, never more than four elements, white and cyan with a shape each; buttons and voice for "distance home", "next station" and "drop pin".
- **Cuff Tablet:** glove-sized controls, a "what you'll see" photo for each station, the station steps, a sample log that stays in your browser, and it works offline.
- **Cuff card:** one printed page with the route, abort routes to the rover, bearings and distances.
- **Storm replay:** "Replay the May 20, 2024 storm" starts the event in the middle of the walk; the alert comes on cue and both walkers head for the rover, with Curiosity's measured dose beside the modeled ones.
- **Validation:** every check, passed or failed, with site notes.

## NASA data

Each credited in [CREDITS.md](CREDITS.md), with the checks in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md):

- Terrain: the USGS MSL Gale merged 1 m elevation model and 25 cm orthophoto (built from HiRISE, CTX and HRSC), the HiRISE color mosaic, and the MOLA global elevation model for distant horizons such as Mount Sharp.
- Rover: Curiosity's localizations (PLACES), ChemCam target tables, and the sols of the four boxwork drill holes from NASA's Curiosity blog.
- Orbital context: HiRISE footprints from the PDS Orbital Data Explorer and THEMIS night-infrared mosaics through NASA Mars Trek.
- Radiation: RAD's measurement beside the Murray Buttes in 2016 (Ehresmann et al. 2021), which calibrates the shielding layer, and the dose-pressure relation in Guo et al. 2021.
- Time: the NASA GISS Mars24 algorithm and NAIF's MSL clock.
- Rover photos: Curiosity Navcam frames from NASA's raw-image API (Courtesy NASA/JPL-Caltech).
- Space weather and the storm replay: CCMC DONKI (through api.nasa.gov), JPL's report of the May 20, 2024 storm (RAD), and JPL Horizons for Earth-Mars light time.
- Space agency partner data: ESA's HRSC images (Mars Express) inside the USGS elevation model; ESA/NASA Solar Orbiter and SOHO behind the May 2024 storm records.

## Use of AI (Super Intelligence)

The idea and every judgement call are the team's: the project plan was written before any AI-assisted work, and the team decided the site, the safety rules, how to report a failed check, the rover's role as relay and shelter, the storm-mode rule and what to label. Claude Code, Anthropic's AI coding assistant, built the pipeline, the web app and the tests under that direction, checked the data sources and drafted the documents. Every source file and commit is marked, and the packaged data says so in its metadata. No AI-generated images, video or audio are used. [AI_USE.md](AI_USE.md) gives the full split, decision by decision.

## Running it

You need Python 3.12 or newer, Node 24 and GNU make. On Windows the team runs the Python pipeline under WSL (Ubuntu), because a Windows security policy blocks numba's and OR-Tools' libraries there; CI runs everything on Linux.

```bash
make setup     # create .venv and install the web dependencies
make test      # pipeline and web tests
make e2e       # browser tests, including accessibility checks
make web-dev   # local dev server
```

The data commands so far:

```bash
make fetch SITE=murray-buttes   # crops for the calibration site (once)
make fetch SITE=boxwork         # crops, context data and drill sites for the flagship site
make derive SITE=murray-buttes  # calibrates the shielding layer, then builds the layers
make derive SITE=boxwork
make plan SITE=boxwork          # route fields, leg matrices, OR-Tools plans, the solver benchmark
make validate                   # writes validation.json
ariadne derive --site boxwork --from-stage walkability  # re-run walkability and later layers only
ariadne ridge-sample --site boxwork  # draw the ridge-labeling sample and build the local labeling page
ariadne ridge-tune --site boxwork --labels config/labels/boxwork_ridge_labels.json  # tune on half, test on half
```

```bash
ariadne timemachine             # light-time table (JPL Horizons) and the DONKI storm snapshot
make package SITE=boxwork       # tiles, plans, photos, the storm replay and the manifest for the app
make footage                    # screen recordings for the demo video (footage/, not committed)
```

`make site` and `ariadne build-site` (a whole new site from a HiRISE terrain model) are not built yet. Raw and derived rasters go to `data/` (not committed); the reports in `docs/coverage/`, `docs/derived/` and `docs/plan/` (with one plan.json per preset), the snapshots in `config/snapshots/`, `validation.json` and the packaged site in `web/public/sites/` are committed.

## License and credits

ARIADNE's code is licensed under [Apache-2.0](LICENSE). Data, software and text by others are listed in [CREDITS.md](CREDITS.md).
