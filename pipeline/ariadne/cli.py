# Written with AI assistance (Claude Code). See AI_USE.md.
"""Command-line entry point for the ARIADNE build pipeline.

Phase 0 defines every command so the Makefile and CI can call them. Commands that are not
built yet stop with exit code 2 and name the phase that builds them, so a run never looks
like it succeeded when nothing was made.
"""

from __future__ import annotations

import argparse
import sys

from ariadne import __version__

NOT_BUILT = 2
BUILT = {"fetch", "derive", "validate", "ridge-sample", "ridge-tune"}  # the rest name their phase

# Command -> (phase that builds it, one-line description).
COMMANDS = {
    "fetch": (1, "Download or window-read the sources for a site and log them."),
    "derive": (2, "Build the derived terrain, light, radiation and science layers."),
    "plan": (3, "Build the leg matrix and the OR-Tools reference plans."),
    "validate": (2, "Run every check against measurements and write validation.json."),
    "ridge-sample": (2, "Draw the ridge-labeling sample and build the local labeling page."),
    "ridge-tune": (2, "Tune the ridge map on the tuning half of the labels; test on the rest."),
    "package": (4, "Write tiles, GeoJSON, snapshots and the manifest for the web app."),
    "build-site": (8, "Build a whole new site from a config file or a HiRISE DTM."),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ariadne",
        description="ARIADNE build pipeline: plan, rehearse and guard a Marswalk.",
    )
    parser.add_argument("--version", action="version", version=f"ariadne {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    for name, (_phase, help_text) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text, description=help_text)
        if name == "build-site":
            src = p.add_mutually_exclusive_group(required=True)
            src.add_argument("--config", help="path to config/sites/<name>.yaml")
            src.add_argument("--dtm", help="HiRISE DTM product ID or local path")
            p.add_argument("--objective", default=None, help="mission objective, such as ice")
            p.add_argument("--name", default=None, help="short name for the new site")
        else:
            p.add_argument("--site", default="boxwork", help="site name (default: boxwork)")
        if name == "ridge-tune":
            p.add_argument("--labels", required=True, help="labels JSON from the labeling page")
            p.add_argument(
                "--no-apply", action="store_true", help="report only; leave config unchanged"
            )
        if name == "fetch":
            p.add_argument("--force", action="store_true", help="re-read sources even if cached")
        if name == "derive":
            p.add_argument("--force", action="store_true", help="recompute horizons even if cached")
            p.add_argument(
                "--report-only",
                action="store_true",
                help="rebuild the report from the saved layers",
            )
            p.add_argument(
                "--from-stage",
                choices=["walkability"],
                default=None,
                help="reuse the saved horizons, light and sunrise results; re-run this stage "
                "and every stage after it",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return NOT_BUILT
    if args.command == "fetch":
        from ariadne.fetch.run import fetch_site, fetch_summary_ok

        summary = fetch_site(args.site, force=args.force)
        return 0 if fetch_summary_ok(summary) else 1
    if args.command == "derive":
        from ariadne.derive.run import derive_site, refresh_report

        if args.report_only:
            refresh_report(args.site)
        else:
            derive_site(args.site, force=args.force, from_stage=args.from_stage)
        return 0
    if args.command == "ridge-sample":
        from ariadne.derive.ridge_run import ridge_sample

        ridge_sample(args.site)
        return 0
    if args.command == "ridge-tune":
        from pathlib import Path

        from ariadne.derive.ridge_run import ridge_tune

        ridge_tune(args.site, Path(args.labels), apply=not args.no_apply)
        return 0
    if args.command == "validate":
        from ariadne.validate.run import write_validation

        v = write_validation()
        failed = [c["id"] for c in v["checks"] if c["status"] == "fail"]
        if failed:
            # A failed check is a result to show in the Validation tab, not a crash.
            print("validation.json written; checks that missed their target: " + ", ".join(failed))
        return 0
    phase, _ = COMMANDS[args.command]
    print(
        f"ariadne {args.command}: not built yet. Phase {phase} builds this command "
        "(see docs/PROGRESS.md).",
        file=sys.stderr,
    )
    return NOT_BUILT


if __name__ == "__main__":
    sys.exit(main())
