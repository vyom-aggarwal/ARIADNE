# Written with AI assistance (Claude Code). See AI_USE.md.
"""The timeline of a plan: margin curve, station blocks, comm-shadow segments, sun elevation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import numpy as np


def build(plan: dict, in_sight: Callable, sun: list[float] | None) -> dict:
    margins = [
        {
            "t_min": m["t_min"],
            "margin_min": round(m["c_left"] - (m["c_home"] or 0.0) - m["c_reserve"], 3),
        }
        for m in plan["margins"]
    ]
    service = {s["id"]: float(s["service_min"]) for s in plan["stations"]}
    t, blocks = 0.0, []
    for leg in plan["legs"]:
        t += float(leg["minutes"])
        if leg["to"] in service:
            blocks.append(
                {
                    "id": leg["to"],
                    "start_min": round(t, 3),
                    "end_min": round(t + service[leg["to"]], 3),
                }
            )
            t += service[leg["to"]]
    shadows, start = [], None
    for m in plan["margins"]:
        visible = bool(in_sight(m["xy_m"]))
        if not visible and start is None:
            start = m["t_min"]
        elif visible and start is not None:
            shadows.append({"start_min": start, "end_min": m["t_min"]})
            start = None
    if start is not None:
        shadows.append({"start_min": start, "end_min": plan["margins"][-1]["t_min"]})
    out = {"margin": margins, "stations": blocks, "comm_shadows": shadows}
    if sun is not None:
        out["sun_elevation_deg"] = [
            {"t_min": m["t_min"], "deg": round(float(s), 2)}
            for m, s in zip(plan["margins"], sun, strict=True)
        ]
    return out


def sun_elevation(start: datetime, t_min, lon_east: float, lat_centric: float) -> list[float]:
    """Sun elevation (degrees) from Mars24 at start + t minutes, at a planetocentric latitude."""
    from ariadne.derive.light import planetographic_latitude
    from ariadne.models import mars24

    lat = planetographic_latitude(lat_centric)
    return [
        float(mars24.solar_state(start + timedelta(minutes=float(t)), lon_east, lat).elevation)
        for t in t_min
    ]


def ltst_start(sol_start: datetime, ltst_hours: float, lon_east: float, lat_centric: float):
    """The UTC time on a sol when local true solar time reaches `ltst_hours` (1-minute search)."""
    from ariadne.derive.light import sun_track

    track = sun_track(sol_start, 25.0, 60.0, lon_east, lat_centric)
    lt = np.asarray(track.ltst)
    k = int(np.argmax((lt[:-1] <= ltst_hours) & (lt[1:] > ltst_hours)))
    return track.times[k]
