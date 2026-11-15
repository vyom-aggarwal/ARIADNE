# How ARIADNE uses AI

NASA Space Apps 2026 calls AI tools "Super Intelligence (SI)" and asks teams to show clearly where and how they were used, in descriptive text and metadata, because judges weigh originality, intent and execution in SI-assisted work. This file is that disclosure. It separates what the team decided from what the AI built.

## The short version

- **The idea, the design and every judgement call are the team's.** The team wrote the project plan before any AI work, chose the challenge, the site, the safety rules and the trade-offs, and reviewed each phase.
- **Claude Code (Anthropic's AI coding assistant) built it under that direction:** the pipeline, the web app, the tests, the data processing runs, the source checks and the first drafts of the documents.
- **No AI-generated images, video or audio.** Every picture is real mission imagery with its credit, or a chart or map drawn from data.

## What the team decided

The project plan, [docs/PLAN.md](docs/PLAN.md), was written and committed by the team on 2026-11-07, before any AI-assisted work (commit `92cbcca`). It sets the concept: a "thread home" that every route must keep, rehearsal in 3D past real Curiosity photos, a visor that shows at most four things, a cuff tablet, a printed cuff card, and the May 2024 storm replay. The build brief and rules ([PROMPT.md](PROMPT.md), [CLAUDE.md](CLAUDE.md)) set how the work is done: no invented data, every number labeled, tests first, credit everything, WCAG 2.1 AA.

As the build went on, the team made each of these decisions after reviewing results (all recorded, dated, in [docs/PROGRESS.md](docs/PROGRESS.md) under "Human decisions"):

- **Site and calibration.** The Mount Sharp boxwork as the flagship site; the Murray Buttes RAD measurement (Ehresmann et al. 2021) to calibrate the shielding layer; the four boxwork drill holes as science anchors.
- **Honesty about a failed check.** When the rover-walkability check failed (79.8% against a 95% target), the team required slope at each traveller's footprint scale on physical grounds, one re-run only, the failed result kept beside the new one, a held-out test at Murray Buttes (99.8%, pass), and no further re-runs. The failure is reported openly, and the planner stays conservative.
- **What a plan must be.** A 6-hour EVA with a 30-minute reserve; whole fracture, wall and hollow transects, not scattered stations; presets that differ by safety settings (Safest: 45-minute reserve, rover within 10 minutes on foot).
- **The rover's role.** The rover as a mobile radio relay, and then as the only shelter (terrain blocks a few percent at most), with storm mode choosing the lowest modeled dose rather than the nearest refuge.
- **What to show and what to label.** The price-of-safety line, the site note that slope no-go is conservative in boxwork terrain, and the station steps (Look, Observe, Describe, Document), which the team took from NASA's 2023-24 SUITS mission description.
- **Final sprint.** The storm replay first, then these submission documents; the second site stays Murray Buttes (built by the same pipeline), and a site generator for a new site is future work; the ridge map stays "not validated" because no hand labels were made in time.

The team also cleared the build with its Local Lead, decided to publish the repository and site, and owns the final submission.

## What Claude Code built

Under that direction, Claude Code:

- wrote the Python pipeline (fetching and cropping NASA and USGS data, the derived layers, the route engine with OR-Tools, the Time Machine) and the static web app (React, deck.gl and three.js);
- wrote the tests first, for each phase's acceptance tests, and ran them (343 pipeline tests, 100 unit tests and 15 browser tests at submission);
- checked every data source before the code depended on it, fetching it and recording what it found in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md), and flagged sources that had moved or could not be confirmed;
- ran the data processing and reported results, including the ones that missed their targets, and diagnosed problems for the team to decide on (for example the DEM seams behind the rover-check false alarms, and a timeline that showed the wrong comm shadows after the relay change);
- drafted the documents: README, this file, PROGRESS, CREDITS, the submission text, the video script and the slide outline.

## Where to see it in the project

- **Source code:** every source file starts with `Written with AI assistance (Claude Code). See AI_USE.md.` A test fails if any file lacks it.
- **Commits:** every commit from the kickoff on ends with `AI-assisted: Claude Code`, checked in CI. The two earlier commits (the initial commit and the project plan) are the team's own.
- **Data:** the packaged site's manifest carries an `ai_assistance` field, and every generated file records the pipeline version that made it.
- **The app:** the footer says it was written with AI assistance.
- **The video:** its end card says the software was written with AI assistance (Claude Code). The video itself is screen recordings of the app and real NASA imagery; nothing in it is AI-generated.

## Rules the AI worked under

From [CLAUDE.md](CLAUDE.md), read at the start of every session:

- **No invented data.** Every value comes from a cited source, a calculation on it, a documented model or a labeled placeholder.
- **Every number is labeled** measured, derived, modeled or placeholder, with its source on hover.
- **Verify before depending** on a source, and ask the team when a source fails.
- **No NASA logos, flags, insignia or mission identifiers** as graphics, and no AI-generated media.
- **Ask the team** before paid services, unusual licenses, deleting cached data, or changing the site.
