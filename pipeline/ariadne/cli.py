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

# Command -> (phase that builds it, one-line description).
COMMANDS = {
    "fetch": (1, "Download or window-read the sources for a site and log them."),
    "derive": (2, "Build the derived terrain, light, radiation and science layers."),
    "plan": (3, "Build the leg matrix and the OR-Tools reference plans."),
    "validate": (2, "Run every check against measurements and write validation.json."),
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return NOT_BUILT
    phase, _ = COMMANDS[args.command]
    print(
        f"ariadne {args.command}: not built yet. Phase {phase} builds this command "
        "(see docs/PROGRESS.md).",
        file=sys.stderr,
    )
    return NOT_BUILT


if __name__ == "__main__":
    sys.exit(main())
