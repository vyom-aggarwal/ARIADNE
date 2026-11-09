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

To be written when the first demo works (Phase 4). The plan is in [docs/PLAN.md](docs/PLAN.md), and the full build brief is in [PROMPT.md](PROMPT.md).

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
make validate                   # writes validation.json
```

`make plan`, `make package` and `make site` are defined but not built yet; each one says which phase builds it. Raw and derived rasters go to `data/` (not committed); the reports in `docs/coverage/` and `docs/derived/` and `validation.json` are committed.

## License and credits

ARIADNE's code is licensed under [Apache-2.0](LICENSE). Data, software and text by others are listed in [CREDITS.md](CREDITS.md).
