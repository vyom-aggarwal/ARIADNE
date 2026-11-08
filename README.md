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

None used yet. The sources checked so far are listed in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md), and each one is credited in [CREDITS.md](CREDITS.md) when the pipeline first uses it.

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

The data commands (`make fetch`, `make derive`, `make plan`, `make validate`, `make package`, `make site`) are defined but not built yet; each one says which phase builds it.

## License and credits

ARIADNE's code is licensed under [Apache-2.0](LICENSE). Data, software and text by others are listed in [CREDITS.md](CREDITS.md).
