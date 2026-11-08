# ARIADNE: rules for every session

ARIADNE is a NASA Space Apps 2026 entry ("Interplanetary Survival Guide: Martian Map"): a static web app that plans, rehearses and guards a two-astronaut Marswalk through the Mount Sharp boxwork. The full brief is PROMPT.md; background is PLAN.md.

## Rules

1. Never invent data. Every value comes from a fetched source, a computation on fetched data, a documented model, or a labeled placeholder.
2. Label every number the app shows as MEASURED, DERIVED, MODELED or PLACEHOLDER, with its source on hover.
3. Verify before you depend. Fetch every URL tagged [VERIFY] and confirm format and content before coding against it, logging results in docs/SOURCES_LOG.md. If it fails, find the current official location; if there is none, or you lack web access, stop and ask.
4. Credit everything. Add each dataset, library, image and text to CREDITS.md when first used, with its URL and license or credit line.
5. Use no NASA logos, flags, insignia, mission patches or mission identifiers as graphics; mission and instrument names appear only as plain-text citations. Create no AI-generated images, video or audio.
6. Ship a static site: no server, no secrets, no API keys in client code. Live fetches are optional and fall back to bundled snapshots.
7. Write tests first. A phase is done only when its acceptance tests pass in CI.
8. Keep science honest: show uncertainty, label models as models, and claim nothing the checks in PROMPT.md section 7 do not support.
9. Meet WCAG 2.1 AA: sufficient contrast, full keyboard access, and color never the only cue.
10. Disclose AI use. README and AI_USE.md describe Claude Code's role; every source file starts with a one-line AI-assistance header; generated data files record the pipeline version; every commit message ends with the trailer "AI-assisted: Claude Code".
11. Keep docs/PROGRESS.md current: phase status, decisions, evidence, open issues and the next step.
12. Write all user-facing text in plain English.
13. License our code Apache-2.0; use only openly licensed or public-domain third-party material, and record each license.
14. Ask the human before adding paid services or non-OSI-licensed dependencies, deleting cached data, or changing the site.

## Commands

- `make setup`: create the Python environment and install web dependencies.
- `make fetch SITE=boxwork`: download or window-read sources and log them in docs/SOURCES_LOG.md.
- `make derive SITE=boxwork`: build the derived layers.
- `make plan SITE=boxwork`: build the leg matrix and OR-Tools reference plans.
- `make validate`: run every check and write validation.json.
- `make package SITE=boxwork`: write tiles, GeoJSON, snapshots and the manifest into web/public/sites/.
- `make site SITE=boxwork`: run all of the above in order.
- `make test`, `make e2e`, `make web-dev`.
- New sites: `ariadne build-site --config config/sites/<name>.yaml`, or `ariadne build-site --dtm <HiRISE DTM ID or path> --objective ice --name frontier`.

## Working method per phase

Plan and acceptance tests into docs/PROGRESS.md, then tests, then code; pass in CI; self-review for honesty, labels, credits, licenses and accessibility; commit as "phase N: ..." with the AI trailer; update PROGRESS.md.

@docs/PROGRESS.md
