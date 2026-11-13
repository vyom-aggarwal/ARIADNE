# Written with AI assistance (Claude Code). See AI_USE.md.
"""The sun's track across the sky at a site, from the Mars24 functions (pure Python and NumPy).

Kept apart from ariadne.derive.light, which compiles its raster passes with numba, so that steps
needing only the sun's position (the package step's timeline) do not load numba.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from ariadne.models import mars24

# NASA NSSDCA Mars Fact Sheet: flattening 0.00589 (docs/SOURCES_LOG.md, nasa-mars-factsheet).
MARS_FLATTENING = 0.00589


def planetographic_latitude(lat_centric_deg: float) -> float:
    """Mars24 takes planetographic latitude; the analysis grid is planetocentric."""
    t = math.tan(math.radians(lat_centric_deg)) / (1.0 - MARS_FLATTENING) ** 2
    return math.degrees(math.atan(t))


@dataclass
class SunTrack:
    times: list[datetime]
    azimuth: np.ndarray  # degrees clockwise from north
    elevation: np.ndarray  # degrees
    ltst: np.ndarray  # local true solar time, hours
    seconds: np.ndarray | None = None  # seconds from the first time
    _lookup: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.seconds is None:
            self.seconds = np.array([(x - self.times[0]).total_seconds() for x in self.times])

    def lookup(self, n_az: int):
        if n_az not in self._lookup:
            self._lookup[n_az] = band_lookup(self.azimuth, n_az)
        return self._lookup[n_az]


def sun_track(start: datetime, hours: float, step_s: float, lon_east: float, lat_centric: float):
    lat = planetographic_latitude(lat_centric)
    n = int(round(hours * 3600 / step_s)) + 1
    times = [start + timedelta(seconds=i * step_s) for i in range(n)]
    states = [mars24.solar_state(t, lon_east, lat) for t in times]
    return SunTrack(
        times=times,
        azimuth=np.array([s.azimuth for s in states]),
        elevation=np.array([s.elevation for s in states]),
        ltst=np.array([s.ltst_hours for s in states]),
    )


def local_noon_track(day_utc: datetime, lon_east: float, lat_centric: float, step_s: float):
    """A track covering one full sol centred on local true noon nearest to `day_utc` + 12 h."""
    lat = planetographic_latitude(lat_centric)
    guess = day_utc + timedelta(hours=12)
    for _ in range(4):  # Newton steps on LTST
        s = mars24.solar_state(guess, lon_east, lat)
        delta_h = ((s.ltst_hours - 12.0 + 12.0) % 24.0) - 12.0
        guess -= timedelta(hours=delta_h * 1.0274912517)
    sol_hours = 24.0 * 1.0274912517
    return sun_track(
        guess - timedelta(hours=sol_hours / 2), sol_hours, step_s, lon_east, lat_centric
    )


def band_lookup(azimuth: np.ndarray, n_az: int):
    """For each sun azimuth: the two horizon bands around it and the weight of the second."""
    pos = (np.asarray(azimuth, dtype=np.float64) % 360.0) / (360.0 / n_az)
    i0 = np.floor(pos).astype(np.int64) % n_az
    return i0, (i0 + 1) % n_az, pos - np.floor(pos)
