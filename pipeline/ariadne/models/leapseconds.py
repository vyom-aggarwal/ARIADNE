# Written with AI assistance (Claude Code). See AI_USE.md.
"""TT − UTC from the IERS leap-second table (Mars24 step A-4).

The table is bundled verbatim from https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat
(fetched 2026-11-08, "Updated through IERS Bulletin 72 issued in July 2026"). TT − UTC is
TAI − UTC + 32.184 s. Before 1972 Mars24's polynomial is used. Past the table's expiry date the
last value is kept and a LeapSecondTableExpired warning is raised, since a leap second could
have been added since.
"""

from __future__ import annotations

import re
import warnings
from datetime import UTC, date, datetime
from functools import lru_cache
from importlib.resources import files

TT_MINUS_TAI = 32.184
_MONTH_NAMES = (
    "January February March April May June July August September October November December"
)
_MONTHS = {m: i + 1 for i, m in enumerate(_MONTH_NAMES.split())}


class LeapSecondTableExpired(UserWarning):
    """The requested date is after the bundled leap-second table's expiry date."""


@lru_cache(maxsize=1)
def _table() -> tuple[list[tuple[date, float]], date]:
    text = files("ariadne.models").joinpath("data/Leap_Second.dat").read_text(encoding="utf-8")
    rows = []
    expiry = None
    for line in text.splitlines():
        m = re.search(r"File expires on\s+(\d+)\s+(\w+)\s+(\d{4})", line)
        if m:
            expiry = date(int(m.group(3)), _MONTHS[m.group(2)], int(m.group(1)))
        if line.lstrip().startswith("#") or not line.strip():
            continue
        _mjd, d, mo, y, tai_utc = line.split()
        rows.append((date(int(y), int(mo), int(d)), float(tai_utc)))
    if not rows or expiry is None:
        raise RuntimeError("could not parse the bundled leap-second table")
    return rows, expiry


def table_expiry() -> date:
    return _table()[1]


def _require_aware(utc: datetime) -> None:
    if utc.tzinfo is None or utc.utcoffset() is None:
        raise ValueError("use a timezone-aware UTC datetime")


def tt_minus_utc(utc: datetime) -> float:
    """TT − UTC in seconds at the given UTC instant."""
    _require_aware(utc)
    day = utc.astimezone(UTC).date()
    rows, expiry = _table()
    if day < rows[0][0]:
        # Mars24 A-4 polynomial for dates before 1972, T in Julian centuries from J2000 (UT).
        jd_ut = utc.timestamp() / 86400.0 + 2440587.5
        t = (jd_ut - 2451545.0) / 36525.0
        return 64.184 + 59.0 * t - 51.2 * t**2 - 67.1 * t**3 - 16.4 * t**4
    if day > expiry:
        warnings.warn(
            f"{day} is after the leap-second table's expiry ({expiry}); "
            "update pipeline/ariadne/models/data/Leap_Second.dat",
            LeapSecondTableExpired,
            stacklevel=2,
        )
    tai_utc = rows[0][1]
    for start, value in rows:
        if day >= start:
            tai_utc = value
        else:
            break
    return tai_utc + TT_MINUS_TAI
