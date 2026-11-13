# ARIADNE: a thread home on Mars

[![CI](https://github.com/vyom-aggarwal/ARIADNE/actions/workflows/ci.yml/badge.svg)](https://github.com/vyom-aggarwal/ARIADNE/actions/workflows/ci.yml)

ARIADNE plans, rehearses and guards a two-astronaut Marswalk through the boxwork ridges of Mount Sharp in Gale crater. It keeps a safe way back to shelter at every step: if a route would leave the crew without enough oxygen and supplies to get home with a reserve, ARIADNE rejects it.

**Status: under construction.** The repository and its guardrails are being set up (Phase 0). See [docs/PROGRESS.md](docs/PROGRESS.md) for where things stand.

This README follows the NASA Space Apps project form and is filled in as the project is built.

## Project details

| Field | Entry |
| --- | --- |
| Project name | ARIADNE |
| Team | To be added |
| Challenge | Interplanetary Survival Guide: Martian Map (NASA Space Apps Challenge 2026) |
| Live site | https://vyom-aggarwal.github.io/ARIADNE/ (placeholder page for now) |
| Source code | https://github.com/vyom-aggarwal/ARIADNE |
| Demo video | To be added in Phase 9 |

## Summary

ARIADNE plans, rehearses and guards a two-astronaut walk through the boxwork ridges of Mount Sharp, where Curiosity has been exploring since 2025. From NASA and USGS terrain models, orbital images and Curiosity's own positions, a pipeline maps where a suited walker can go, how much sky each spot sees (a guide to radiation shielding), and which ridge, wall and hollow stops would teach the most. It then plans three walks (Safest, Balanced and Most science) that always keep enough air to get back to the rover, with the rover as both radio relay and shelter.

The web app shows those plans on a map with every layer's source, lets you rehearse the walk in 3D past real Curiosity photos, and drives three surfaces for the walkers: a visor display that never shows more than four things at once, a glove-friendly cuff tablet that works offline, and a one-page printed cuff card as the backup. A Validation tab shows every check, including the ones that failed. Every number is labeled measured, derived, modeled or placeholder; the suit and walking settings are placeholders, so the plans are a concept, not mission guidance.

The plan is in [docs/PLAN.md](docs/PLAN.md), progress in [docs/PROGRESS.md](docs/PROGRESS.md), and the full build brief in [PROMPT.md](PROMPT.md).

## How it works

ARIADNE has two parts:

- a **Python pipeline** (`pipeline/`) that runs at build time: it downloads terrain, imagery and rover data, builds the safety and science layers, and plans reference routes;
- a **static web app** (`web/`) that only loads the files the pipeline made. There is no server and no secret key.

## NASA data

Used so far (Phases 1 and 2), each credited in [CREDITS.md](CREDITS.md) with the checks in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md):

- Terrain: the USGS MSL Gale merged 1 m elevation model and 25 cm orthophoto (built from HiRISE, CTX and HRSC), the HiRISE color mosaic, and the MOLA global elevation model for distant horizons such as Mount Sharp.
- Rover: Curiosity's localizations (PLACES), ChemCam target tables, and the sols of the four boxwork drill holes from NASA's Curiosity blog.
- Orbital context: HiRISE footprints from the PDS Orbital Data Explorer and THEMIS night-infrared mosaics through NASA Mars Trek.
- Radiation: RAD's measurement beside the Murray Buttes in 2016 (Ehresmann et al. 2021), which calibrates the shielding layer, and the dose-pressure relation in Guo et al. 2021.
- Time: the NASA GISS Mars24 algorithm and NAIF's MSL clock.

## Use of AI

ARIADNE is built with Claude Code, an AI coding assistant, under the team's direction. [AI_USE.md](AI_USE.md) explains what the AI does, what people do, and how to tell which work is AI-assisted. No AI-generated images, video or audio are used.

## Running it

You need Python 3.12 or 3.13, Node 24 and GNU make (on Windows, run make from Git Bash, for example after `choco install make`).

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

`make package` and `make site` are defined but not built yet; each one says which phase builds it. Raw and derived rasters go to `data/` (not committed); the reports in `docs/coverage/`, `docs/derived/` and `docs/plan/` (with one plan.json per preset) and `validation.json` are committed.

## License and credits

ARIADNE's code is licensed under [Apache-2.0](LICENSE). Data, software and text by others are listed in [CREDITS.md](CREDITS.md).
