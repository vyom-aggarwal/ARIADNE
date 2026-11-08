# Written with AI assistance (Claude Code). See AI_USE.md.
"""Plain HTTP helpers: whole-file downloads and JSON queries, with retries."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from ariadne.fetch.raster import USER_AGENT


def _open(url: str, timeout: float):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def download(url: str, dest: Path, timeout: float = 120, attempts: int = 4) -> dict:
    """Download to dest (via a .part file). Returns size and the server's Last-Modified."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    for attempt in range(attempts):
        try:
            with _open(url, timeout) as resp, open(part, "wb") as f:
                expected = resp.headers.get("Content-Length")
                last_modified = resp.headers.get("Last-Modified")
                while chunk := resp.read(1 << 20):
                    f.write(chunk)
            size = part.stat().st_size
            if expected is not None and int(expected) != size:
                raise OSError(f"short download: {size} of {expected} bytes")
            part.replace(dest)
            return {"bytes": size, "last_modified": last_modified}
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")


def get_json(base: str, params: dict, timeout: float = 120, attempts: int = 4) -> dict:
    url = base + "?" + urllib.parse.urlencode(params)
    for attempt in range(attempts):
        try:
            with _open(url, timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 * 2**attempt)
    raise AssertionError("unreachable")
