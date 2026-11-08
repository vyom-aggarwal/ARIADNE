# Written with AI assistance (Claude Code). See AI_USE.md.
"""MSL (Curiosity) mission time: sols and the mission clock.

Definitions (docs/SOURCES_LOG.md):
- Sol 0 is the sol of touchdown, and the mission clock is local mean solar time (LMST) for a
  planned site at 137.42 E (Mars24 notes, `mars24-notes`).
- Touchdown was 2012-08-06T05:17:57 UTC (NAIF kernel msl_lmst_ops120808_v1.tsc, `naif-msl-lmst`).

Sol N therefore begins at mean midnight at 137.42 E. Mean solar time comes from Mars24.
Label: MODELED.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta

from ariadne.models import mars24
from ariadne.models.leapseconds import tt_minus_utc

MSL_CLOCK_LON_EAST = 137.42
MSL_TOUCHDOWN_UTC = datetime(2012, 8, 6, 5, 17, 57, tzinfo=UTC)
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _mean_solar_days(utc: datetime, lon_east: float) -> float:
    """Count of local mean solar days at an east longitude: MSD + longitude / 360."""
    _, _, jd_tt = mars24.julian_dates(utc)
    return mars24.mars_sol_date(jd_tt) + lon_east / 360.0


def _sol0_count(lon_east: float) -> int:
    return math.floor(_mean_solar_days(MSL_TOUCHDOWN_UTC, lon_east))


def msl_sol(utc: datetime, lon_east: float = MSL_CLOCK_LON_EAST) -> int:
    """MSL sol number at a UTC instant (negative before the landing sol)."""
    return math.floor(_mean_solar_days(utc, lon_east)) - _sol0_count(lon_east)


def msl_lmst_hours(utc: datetime) -> float:
    """Mission-clock time of day, in hours (LMST at 137.42 E)."""
    return (_mean_solar_days(utc, MSL_CLOCK_LON_EAST) % 1.0) * 24.0


def sol_start_utc(sol: int, lon_east: float = MSL_CLOCK_LON_EAST) -> datetime:
    """UTC instant when the given sol begins (mean midnight at lon_east)."""
    msd = _sol0_count(lon_east) + sol - lon_east / 360.0
    jd_tt = (msd - 44796.0 + 0.0009626) * mars24.SOL_IN_DAYS + 2451549.5
    tt_as_utc = _UNIX_EPOCH + timedelta(days=jd_tt - 2440587.5)
    utc = tt_as_utc - timedelta(seconds=tt_minus_utc(tt_as_utc))
    # One refinement in case the subtraction crossed a leap-second boundary.
    return tt_as_utc - timedelta(seconds=tt_minus_utc(utc))


def solar_longitude(utc: datetime) -> float:
    """Areocentric solar longitude Ls in degrees (season)."""
    return mars24.solar_state(utc, lon_east=MSL_CLOCK_LON_EAST, lat=0.0).ls


def sols_for_utc_dates(first_day: date, last_day: date) -> tuple[int, int]:
    """The sols that overlap the UTC days first_day to last_day, inclusive."""
    start = datetime(first_day.year, first_day.month, first_day.day, tzinfo=UTC)
    end = datetime(last_day.year, last_day.month, last_day.day, tzinfo=UTC) + timedelta(days=1)
    return msl_sol(start), msl_sol(end - timedelta(microseconds=1))
