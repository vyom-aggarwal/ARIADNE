# How ARIADNE uses AI

NASA Space Apps asks teams to say how they used AI. This file is that disclosure, and it is kept current as the project grows.

## What the AI does

ARIADNE is built with **Claude Code**, Anthropic's AI coding assistant, working in this repository under the team's direction. Claude Code:

- writes the pipeline code, the web app, the tests and most of the documentation;
- checks data sources before the code depends on them, fetching each one and recording what it found in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md);
- runs the tests and the build, and keeps [docs/PROGRESS.md](docs/PROGRESS.md) up to date.

## What people do

The team decides what to build and approves each step that matters: getting clearance from the Local Lead, publishing the repository and website, the choice of site, any paid service or unusual license, and the final submission. The team reviews the work and is responsible for it.

## Rules the AI works under

These are in [CLAUDE.md](CLAUDE.md), which Claude Code reads at the start of every session:

- **No invented data.** Every value comes from a cited source, a calculation on that source, a documented model, or a clearly labeled placeholder.
- **Every number is labeled** measured, derived, modeled or placeholder, with its source on hover.
- **No AI-generated images, video or audio.** Pictures in the app are real mission imagery with credit lines, or charts drawn from data.
- **No NASA logos, flags, insignia or mission patches** used as graphics.

## How to tell which work is AI-assisted

- Every source file starts with the line `Written with AI assistance (Claude Code). See AI_USE.md.` A test fails if any source file lacks it.
- Every commit message, from the kickoff on, ends with `AI-assisted: Claude Code`. CI checks this. The two earlier commits ("Initial commit" and the project plan) were made by the team before this rule existed.
- Generated data files record the pipeline version that made them.
