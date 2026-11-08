# Written with AI assistance (Claude Code). See AI_USE.md.
"""Provenance records for every product (PROMPT.md section 3, "Conventions").

Each product gets a JSON sidecar `<file>.prov.json`; GeoTIFFs also carry the same JSON in an
`ARIADNE_PROVENANCE` tag, so the record travels with the file.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ariadne import PIPELINE_VERSION
from ariadne.labels import Label

REQUIRED_FIELDS = (
    "source_id",
    "url",
    "product_id",
    "resolution_m",
    "acquisition_date",
    "processing_date",
    "pipeline_version",
    "label",
)
TAG = "ARIADNE_PROVENANCE"


@dataclass(frozen=True)
class Provenance:
    source_id: str
    url: str
    product_id: str
    resolution_m: float | None
    acquisition_date: str | None  # ISO date or range; None for mosaics, explained in notes
    processing_date: str  # ISO 8601 UTC, ending in Z
    pipeline_version: str
    label: Label
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", Label(self.label))  # raises ValueError if unknown
        if not self.source_id or not self.url or not self.product_id:
            raise ValueError("source_id, url and product_id are required")
        if self.acquisition_date is None and not self.notes.strip():
            raise ValueError("explain a missing acquisition_date in notes")
        if not self.pipeline_version:
            raise ValueError("pipeline_version is required")

    @classmethod
    def new(cls, **kwargs: Any) -> Provenance:
        """A record stamped with the current UTC time and this pipeline version."""
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        kwargs.setdefault("processing_date", now)
        kwargs.setdefault("pipeline_version", PIPELINE_VERSION)
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["label"] = str(self.label)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Provenance:
        return cls(**d)


def sidecar_path(target: Path) -> Path:
    target = Path(target)
    return target.with_name(target.name + ".prov.json")


def write_provenance(target: Path, prov: Provenance, embed: bool = False) -> Path:
    """Write the sidecar; with embed=True also store the record in the GeoTIFF's tags."""
    text = json.dumps(prov.to_dict(), indent=2, sort_keys=True)
    out = sidecar_path(target)
    out.write_text(text + "\n", encoding="utf-8")
    if embed:
        import rasterio

        with rasterio.open(target, "r+") as ds:
            ds.update_tags(**{TAG: json.dumps(prov.to_dict(), sort_keys=True)})
    return out


def read_provenance(target: Path) -> Provenance:
    return Provenance.from_dict(json.loads(sidecar_path(target).read_text(encoding="utf-8")))
