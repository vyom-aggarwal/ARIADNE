# Written with AI assistance (Claude Code). See AI_USE.md.
"""Site boxes from a site config and Curiosity's localizations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from ariadne.config import SiteConfig
from ariadne.fetch import places
from ariadne.models.msl_time import sols_for_utc_dates


@dataclass(frozen=True)
class SiteBox:
    site: str
    method: str
    first_sol: int
    last_sol: int
    rover_count: int
    rover_extent: tuple[float, float, float, float]  # easting/northing of the localizations
    anchor: dict | None  # the parking position, for parking_position sites
    buffer_m: float
    buffer_label: str
    bounds: tuple[float, float, float, float]  # (left, bottom, right, top), meters, unsnapped

    def to_dict(self) -> dict:
        return asdict(self)


def site_box(cfg: SiteConfig, rover: pd.DataFrame) -> SiteBox:
    first, last = sols_for_utc_dates(cfg.selection.utc_start, cfg.selection.utc_end)
    sub = places.in_sols(rover, first, last)
    if sub.empty:
        raise ValueError(f"no rover localizations for {cfg.name} in sols {first} to {last}")
    extent = (
        float(sub["easting"].min()),
        float(sub["northing"].min()),
        float(sub["easting"].max()),
        float(sub["northing"].max()),
    )
    b = cfg.buffer_m
    anchor = None
    if cfg.selection.method == "rover_extent":
        bounds = (extent[0] - b, extent[1] - b, extent[2] + b, extent[3] + b)
    else:
        anchor = places.parking_position(rover, first, last)
        e, n = anchor["easting"], anchor["northing"]
        bounds = (e - b, n - b, e + b, n + b)
    return SiteBox(
        site=cfg.name,
        method=cfg.selection.method,
        first_sol=first,
        last_sol=last,
        rover_count=int(len(sub)),
        rover_extent=extent,
        anchor=anchor,
        buffer_m=b,
        buffer_label=str(cfg.buffer_label),
        bounds=bounds,
    )
