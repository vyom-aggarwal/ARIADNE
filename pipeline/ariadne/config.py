# Written with AI assistance (Claude Code). See AI_USE.md.
"""Load site and source configuration from config/."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from ariadne.guardrails import repo_root
from ariadne.labels import Label


def config_dir() -> Path:
    return repo_root() / "config"


@dataclass(frozen=True)
class Selection:
    method: str  # "rover_extent" or "parking_position"
    utc_start: date
    utc_end: date  # inclusive


@dataclass(frozen=True)
class SiteConfig:
    name: str
    title: str
    role: str
    selection: Selection
    buffer_m: float
    buffer_label: Label
    buffer_reason: str
    sources: list[str]
    optional_sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    product_id: str
    product_page: str
    resolution_m: float | None
    label: Label
    credit: str
    license: str
    acquisition_date: str | None = None
    notes: str = ""
    output: str | None = None
    nodata: float | None = None


def load_site_config(name: str) -> SiteConfig:
    raw = yaml.safe_load((config_dir() / "sites" / f"{name}.yaml").read_text(encoding="utf-8"))
    sel = raw["selection"]
    if sel["method"] not in {"rover_extent", "parking_position"}:
        raise ValueError(f"unknown selection method {sel['method']!r}")
    return SiteConfig(
        name=raw["name"],
        title=raw["title"],
        role=raw["role"],
        selection=Selection(sel["method"], sel["utc_start"], sel["utc_end"]),
        buffer_m=float(raw["buffer_m"]),
        buffer_label=Label(raw["buffer_label"]),
        buffer_reason=raw["buffer_reason"],
        sources=list(raw["sources"]),
        optional_sources=list(raw.get("optional_sources", [])),
    )


def load_sources() -> dict[str, Source]:
    raw: dict[str, dict[str, Any]] = yaml.safe_load(
        (config_dir() / "sources.yaml").read_text(encoding="utf-8")
    )
    return {k: Source(id=k, **v) for k, v in raw.items()}
