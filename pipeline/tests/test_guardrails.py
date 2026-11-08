# Written with AI assistance (Claude Code). See AI_USE.md.
"""Phase 0 guardrails: required files, AI headers, no secrets, commit trailers (A1 to A4)."""

from pathlib import Path

import pytest

from ariadne import guardrails as g

ROOT = g.repo_root()

REQUIRED_FILES = [
    "LICENSE",
    "README.md",
    "AI_USE.md",
    "CREDITS.md",
    "CLAUDE.md",
    "PROMPT.md",
    "docs/PROGRESS.md",
    "docs/SOURCES_LOG.md",
    "docs/PLAN.md",
]


# A1: required files and license


@pytest.mark.parametrize("rel", REQUIRED_FILES)
def test_required_file_exists(rel):
    assert (ROOT / rel).is_file(), f"missing {rel}"


def test_license_is_apache_2():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "END OF TERMS AND CONDITIONS" in text


# A2: AI-assistance header on every source file


def test_every_source_file_has_the_ai_header():
    missing = g.files_missing_header(ROOT)
    assert missing == [], "add the AI-assistance header to: " + ", ".join(missing)


def test_header_check_finds_some_source_files():
    # Guards against the check passing because it looked at nothing.
    files = [p for p in g.repo_files(ROOT) if g.comment_prefix(p) is not None]
    names = {p.name for p in files}
    assert "cli.py" in names
    assert "App.tsx" in names
    assert "ci.yml" in names
    assert "Makefile" in names


@pytest.mark.parametrize(
    ("name", "first_line", "ok"),
    [
        ("a.py", "# " + g.HEADER_TEXT, True),
        ("a.py", "# some other comment", False),
        ("a.ts", "// " + g.HEADER_TEXT, True),
        ("a.ts", "# " + g.HEADER_TEXT, False),
        ("a.css", "/* " + g.HEADER_TEXT + " */", True),
        ("a.html", "<!-- " + g.HEADER_TEXT + " -->", True),
        ("Makefile", "# " + g.HEADER_TEXT, True),
        ("a.yml", "", False),
    ],
)
def test_header_check_on_single_files(tmp_path, name, first_line, ok):
    p = tmp_path / name
    p.write_text(first_line + "\nbody\n", encoding="utf-8")
    assert g.has_header(p) is ok


def test_header_may_follow_a_shebang(tmp_path):
    p = tmp_path / "run.py"
    p.write_text("#!/usr/bin/env python\n# " + g.HEADER_TEXT + "\n", encoding="utf-8")
    assert g.has_header(p)


def test_files_without_comment_syntax_are_exempt(tmp_path):
    p = tmp_path / "package.json"
    p.write_text("{}\n", encoding="utf-8")
    assert g.comment_prefix(p) is None


# A3: no secrets


def test_no_secrets_in_repo_files():
    hits = g.find_secrets(ROOT)
    assert hits == [], "possible secrets: " + ", ".join(hits)


@pytest.mark.parametrize(
    "line",
    [
        # Built by concatenation so this file never contains a real-looking token.
        "token = '" + "gh" + "p_" + "a" * 36 + "'",
        "AWS " + "AKIA" + "ABCDEFGHIJKLMNOP",
        "url = 'https://api.nasa.gov/DONKI/CME?api_key=" + "x" * 40 + "'",
        "API_KEY = '" + "k" * 24 + "'",
        "-----BEGIN " + "PRIVATE KEY-----",
        "key: " + "sk-" + "ant-" + "z" * 30,
    ],
)
def test_secret_scanner_catches_common_tokens(tmp_path, line):
    (tmp_path / "leak.txt").write_text(line + "\n", encoding="utf-8")
    assert g.scan_file_for_secrets(tmp_path / "leak.txt")


def test_secret_scanner_allows_ordinary_text(tmp_path):
    p = tmp_path / "ok.md"
    p.write_text("Use api.nasa.gov with DEMO_KEY only in local experiments.\n", encoding="utf-8")
    assert not g.scan_file_for_secrets(p)


# A4: commit trailers (the CI step runs the same function on real history)


def test_trailer_check_accepts_a_message_ending_with_the_trailer():
    msg = "phase 0: repo and guardrails\n\nDetails.\n\nAI-assisted: Claude Code\n"
    assert g.commits_missing_trailer([("abc123", msg)]) == []


@pytest.mark.parametrize(
    "msg",
    [
        "phase 0: repo and guardrails\n",
        "AI-assisted: Claude Code\n\nphase 0: trailer not at the end\n",
        "phase 0: x\n\nAI-assisted: claude code\n",
    ],
)
def test_trailer_check_rejects_other_messages(msg):
    assert g.commits_missing_trailer([("abc123", msg)]) == ["abc123"]


def test_repo_root_holds_the_project_rules():
    assert (ROOT / "CLAUDE.md").is_file()
    assert isinstance(ROOT, Path)
