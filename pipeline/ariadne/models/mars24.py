# Written with AI assistance (Claude Code). See AI_USE.md.
"""Mars solar time and sun position, following the NASA GISS Mars24 algorithm step by step.

Source: https://www.giss.nasa.gov/tools/mars24/help/algorithm.html (Allison and McEwen 2000,
with the 2015 revisions). Step names (A-1 ... D-6) match that page. Label: MODELED.

Conventions: Mars24 uses west longitude; this module takes east longitude (the project
convention) and converts. Latitude for the sun's position is planetographic, as on the page.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from ariadne.models.leapseconds import tt_minus_utc

SOL_IN_DAYS = 1.0274912517  # Earth days per mean solar day on Mars (step C-2)

# Step B-3 perturbers: amplitude A (deg), period tau (Julian years), phase phi (deg).
_PBS_TERMS = (
    (0.0071, 2.2353, 49.409),
    (0.0057, 2.7543, 168.173),
    (0.0039, 1.1177, 191.837),
    (0.0037, 15.7866, 21.736),
    (0.0021, 2.1354, 15.704),
    (0.0020, 2.4694, 95.528),
    (0.0018, 32.8493, 49.095),
)


def _sin(deg: float) -> float:
    return math.sin(math.radians(deg))


def _cos(deg: float) -> float:
    return math.cos(math.radians(deg))


@dataclass(frozen=True)
class SolarState:
    """Every intermediate value of the Mars24 algorithm for one instant and place."""

    jd_ut: float
    tt_minus_utc: float
    jd_tt: float
    dt_j2000: float
    mean_anomaly: float  # deg, 0-360
    alpha_fms: float  # deg, 0-360
    pbs: float  # deg
    equation_of_center: float  # deg (nu - M)
    ls: float  # areocentric solar longitude, deg, 0-360
    eot_deg: float
    mst_hours: float  # mean solar time at the prime meridian
    lmst_hours: float
    ltst_hours: float
    subsolar_lon_west: float  # deg west, 0-360
    declination: float  # deg, planetographic
    helio_distance_au: float
    helio_longitude: float  # deg, 0-360
    helio_latitude: float  # deg
    zenith: float  # deg
    azimuth: float  # deg clockwise from north, 0-360

    @property
    def elevation(self) -> float:
        return 90.0 - self.zenith

    @property
    def subsolar_lon_east(self) -> float:
        return (360.0 - self.subsolar_lon_west) % 360.0


def julian_dates(utc: datetime) -> tuple[float, float, float]:
    """Steps A-2, A-4 and A-5: (JD_UT, TT - UTC in seconds, JD_TT)."""
    jd_ut = 2440587.5 + utc.timestamp() / 86400.0
    dt = tt_minus_utc(utc)
    return jd_ut, dt, jd_ut + dt / 86400.0


def mars_sol_date(jd_tt: float) -> float:
    """Mars Sol Date: mean solar days, so that MST = 24 h * frac(MSD) (step C-2)."""
    return (jd_tt - 2451549.5) / SOL_IN_DAYS + 44796.0 - 0.0009626


def solar_state(utc: datetime, lon_east: float, lat: float) -> SolarState:
    """Run Mars24 steps A to D for a UTC instant, east longitude and planetographic latitude."""
    jd_ut, dt_tt, jd_tt = julian_dates(utc)
    d = jd_tt - 2451545.0  # A-6

    m = 19.3871 + 0.52402073 * d  # B-1
    alpha = 270.3871 + 0.524038496 * d  # B-2
    pbs = sum(a * _cos(0.985626 * d / tau + phi) for a, tau, phi in _PBS_TERMS)  # B-3
    eoc = (  # B-4
        (10.691 + 3.0e-7 * d) * _sin(m)
        + 0.623 * _sin(2 * m)
        + 0.050 * _sin(3 * m)
        + 0.005 * _sin(4 * m)
        + 0.0005 * _sin(5 * m)
        + pbs
    )
    ls = (alpha + eoc) % 360.0  # B-5

    eot = 2.861 * _sin(2 * ls) - 0.071 * _sin(4 * ls) + 0.002 * _sin(6 * ls) - eoc  # C-1
    mst = (24.0 * mars_sol_date(jd_tt)) % 24.0  # C-2
    lon_west = (-lon_east) % 360.0
    lmst = (mst - lon_west / 15.0) % 24.0  # C-3
    ltst = (lmst + eot / 15.0) % 24.0  # C-4
    subsolar_w = (mst * 15.0 + eot + 180.0) % 360.0  # C-5

    decl = math.degrees(math.asin(0.42565 * _sin(ls))) + 0.25 * _sin(ls)  # D-1
    r = 1.52367934 * (  # D-2
        1.00436
        - 0.09309 * _cos(m)
        - 0.004336 * _cos(2 * m)
        - 0.00031 * _cos(3 * m)
        - 0.00003 * _cos(4 * m)
    )
    helio_lon = (ls + 85.061 - 0.015 * _sin(71.0 + 2 * ls) - 5.5e-6 * d) % 360.0  # D-3
    helio_lat = -(1.8497 - 2.23e-5 * d) * _sin(ls - 144.50 + 2.57e-6 * d)  # D-4

    h = lon_west - subsolar_w  # hour angle, D-5
    cos_z = _sin(decl) * _sin(lat) + _cos(decl) * _cos(lat) * _cos(h)
    zenith = math.degrees(math.acos(max(-1.0, min(1.0, cos_z))))
    azimuth = (  # D-6
        math.degrees(
            math.atan2(_sin(h), _cos(lat) * math.tan(math.radians(decl)) - _sin(lat) * _cos(h))
        )
        % 360.0
    )

    return SolarState(
        jd_ut=jd_ut,
        tt_minus_utc=dt_tt,
        jd_tt=jd_tt,
        dt_j2000=d,
        mean_anomaly=m % 360.0,
        alpha_fms=alpha % 360.0,
        pbs=pbs,
        equation_of_center=eoc,
        ls=ls,
        eot_deg=eot,
        mst_hours=mst,
        lmst_hours=lmst,
        ltst_hours=ltst,
        subsolar_lon_west=subsolar_w,
        declination=decl,
        helio_distance_au=r,
        helio_longitude=helio_lon,
        helio_latitude=helio_lat,
        zenith=zenith,
        azimuth=azimuth,
    )
