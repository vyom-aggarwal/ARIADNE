# Written with AI assistance (Claude Code). See AI_USE.md.
"""Repository guardrails for the project rules in CLAUDE.md.

Checks that every source file carries the AI-assistance header (rule 10), that no file holds
an API key or token (rule 6), and that every commit message ends with the AI trailer (rule 10).
Run as `python -m ariadne.guardrails {headers,secrets,trailers}`; the pytest suite calls the
same functions.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

HEADER_TEXT = "Written with AI assistance (Claude Code). See AI_USE.md."
TRAILER = "AI-assisted: Claude Code"

# The two commits made before the project rules existed; trailers are checked after this one.
PRE_RULE_BASE = "92cbcca"

# Comment syntax per file type. Types not listed here (JSON, Markdown, data) need no header.
COMMENT_BY_SUFFIX = {
    ".py": "#",
    ".toml": "#",
    ".yml": "#",
    ".yaml": "#",
    ".sh": "#",
    ".ts": "//",
    ".tsx": "//",
    ".js": "//",
    ".mjs": "//",
    ".cjs": "//",
    ".css": "/*",
    ".html": "<!--",
}
COMMENT_BY_NAME = {"Makefile": "#"}

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "data",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
}

SECRET_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),  # GitHub tokens
    re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key ID
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"sk-(?:ant-)?[A-Za-z0-9_\-]{20,}"),  # Anthropic and OpenAI style keys
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),  # Slack
    re.compile(r"api_key=(?!DEMO_KEY\b)[A-Za-z0-9]{20,}"),  # api.nasa.gov style query keys
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"
    ),
]

MAX_SCAN_BYTES = 5_000_000


def repo_root(start: Path | None = None) -> Path:
    """Find the repository root: the nearest folder holding CLAUDE.md and pipeline/."""
    candidates = [start] if start else [Path.cwd(), Path(__file__).resolve()]
    for c in candidates:
        for p in [c, *c.parents]:
            if (p / "CLAUDE.md").is_file() and (p / "pipeline").is_dir():
                return p
    raise FileNotFoundError("could not find the ARIADNE repository root")


def repo_files(root: Path) -> list[Path]:
    """Files tracked or addable by git (respecting .gitignore); a directory walk without git."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        files = [root / f for f in out.split("\0") if f]
        return sorted(p for p in files if p.is_file())
    except (OSError, subprocess.CalledProcessError):
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            found += [Path(dirpath) / f for f in filenames]
        return sorted(found)


def comment_prefix(path: Path) -> str | None:
    """The comment opener a header must use for this file, or None if it needs no header."""
    return COMMENT_BY_NAME.get(path.name) or COMMENT_BY_SUFFIX.get(path.suffix)


def has_header(path: Path) -> bool:
    """True if the first line (or the line after a shebang) is the AI-assistance header."""
    prefix = comment_prefix(path)
    if prefix is None:
        return True
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return False
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    if not lines:
        return False
    first = lines[0].strip()
    return first.startswith(prefix) and HEADER_TEXT in first


def files_missing_header(root: Path) -> list[str]:
    return [
        p.relative_to(root).as_posix()
        for p in repo_files(root)
        if comment_prefix(p) is not None and not has_header(p)
    ]


def scan_file_for_secrets(path: Path) -> list[str]:
    """Return 'line N' markers for lines that look like secrets (never the secret itself)."""
    try:
        if path.stat().st_size > MAX_SCAN_BYTES:
            return []
        raw = path.read_bytes()
    except OSError:
        return []
    if b"\0" in raw[:4096]:
        return []  # binary
    text = raw.decode("utf-8", errors="replace")
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if any(p.search(line) for p in SECRET_PATTERNS):
            hits.append(f"line {n}")
    return hits


def find_secrets(root: Path) -> list[str]:
    hits = []
    for p in repo_files(root):
        for h in scan_file_for_secrets(p):
            hits.append(f"{p.relative_to(root).as_posix()} {h}")
    return hits


def commits_missing_trailer(commits: Iterable[tuple[str, str]]) -> list[str]:
    """Return the SHAs whose message does not end with the exact AI trailer line."""
    bad = []
    for sha, message in commits:
        lines = [ln.strip() for ln in message.strip().splitlines() if ln.strip()]
        if not lines or lines[-1] != TRAILER:
            bad.append(sha)
    return bad


def git_commits(root: Path, since: str) -> list[tuple[str, str]]:
    """Non-merge commits reachable from HEAD but not from `since`, as (sha, message)."""
    out = subprocess.run(
        ["git", "log", "--no-merges", "--format=%H%x00%B%x1e", f"{since}..HEAD"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if record:
            sha, _, msg = record.partition("\x00")
            commits.append((sha, msg))
    return commits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ariadne.guardrails", description=__doc__)
    sub = parser.add_subparsers(dest="check", required=True)
    sub.add_parser("headers", help="every source file starts with the AI-assistance header")
    sub.add_parser("secrets", help="no API keys or tokens in repository files")
    t = sub.add_parser("trailers", help="every commit message ends with the AI trailer")
    t.add_argument("--since", default=PRE_RULE_BASE, help="check commits after this ref")
    args = parser.parse_args(argv)
    root = repo_root()

    if args.check == "headers":
        bad = files_missing_header(root)
        what = "files missing the AI-assistance header"
    elif args.check == "secrets":
        bad = find_secrets(root)
        what = "possible secrets"
    else:
        commits = git_commits(root, args.since)
        bad = commits_missing_trailer(commits)
        what = f'commits not ending with "{TRAILER}" (of {len(commits)} checked)'

    if bad:
        print(f"{len(bad)} {what}:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        return 1
    print(f"OK: no {what}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
