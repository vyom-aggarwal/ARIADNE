# Written with AI assistance (Claude Code). See AI_USE.md.
"""Mars24 and leap seconds (acceptance tests B1 and B2).

Expected values are the two worked examples on the GISS Mars24 algorithm page
(https://www.giss.nasa.gov/tools/mars24/help/algorithm.html), printed to 5 decimals.
"""

import warnings
from datetime import UTC, datetime

import pytest

from ariadne.models import leapseconds, mars24

TOL = 1e-5  # the page prints 5 decimals

# The page's printed declination, sun angles and Spirit LTST cannot be reproduced to 5 decimals
# from its own printed inputs (see test_page_is_not_self_consistent_at_5_decimals), so those
# keys use a looser, stated tolerance. Steps A-1 to C-5 must match to the printed precision.
LOOSE_TOL = {"declination": 1e-3, "zenith": 1e-3, "azimuth": 1e-3, "ltst_hours": 1e-4}

EXAMPLE_1 = {
    "utc": datetime(2000, 1, 6, 0, 0, 0, tzinfo=UTC),
    "lon_east": 0.0,
    "lat": 0.0,
    "expect": {
        "jd_ut": 2451549.5,
        "tt_minus_utc": 64.184,
        "jd_tt": 2451549.50074,
        "dt_j2000": 4.50074,
        "mean_anomaly": 21.74558,
        "alpha_fms": 272.74566,
        "pbs": 0.00142,
        "equation_of_center": 4.44193,
        "ls": 277.18758,
        "eot_deg": -5.18774,
        "mst_hours": 23.99425,
        "lmst_hours": 23.99425,
        "ltst_hours": 23.64840,
        "subsolar_lon_west": 174.72600,
        "declination": -25.22825,
        "helio_distance_au": 1.39358,
        "helio_longitude": 2.26352,
        "helio_latitude": -1.35957,
        "zenith": 154.26182,
        "azimuth": 191.03905,
    },
}

EXAMPLE_2 = {
    # Spirit: local true midnight before touchdown, at 184.702 W, 14.640 S (planetographic).
    "utc": datetime(2004, 1, 3, 13, 46, 31, tzinfo=UTC),
    "lon_east": 360.0 - 184.702,
    "lat": -14.640,
    "expect": {
        "jd_ut": 2453008.07397,
        "tt_minus_utc": 64.184,
        "jd_tt": 2453008.07471,
        "dt_j2000": 1463.07471,
        "mean_anomaly": 66.06858,
        "alpha_fms": 317.09457,
        "pbs": 0.01614,
        "equation_of_center": 10.22959,
        "ls": 327.32416,
        "eot_deg": -12.77553,
        "mst_hours": 13.16537,
        "lmst_hours": 0.85190,
        "ltst_hours": 0.00025,
        "subsolar_lon_west": 4.70500,
        "declination": -13.42065,
        "helio_distance_au": 1.47767,
        "helio_longitude": 52.37564,
        "helio_latitude": 0.08965,
        "zenith": 151.93895,
        "azimuth": 179.99383,
    },
}


@pytest.mark.parametrize("example", [EXAMPLE_1, EXAMPLE_2], ids=["coincident", "spirit"])
def test_worked_example_matches_every_printed_value(example):
    r = mars24.solar_state(example["utc"], lon_east=example["lon_east"], lat=example["lat"])
    for key, want in example["expect"].items():
        got = getattr(r, key)
        tol = LOOSE_TOL.get(key, TOL)
        assert got == pytest.approx(want, abs=tol), f"{key}: got {got}, want {want}"


def test_page_is_not_self_consistent_at_5_decimals():
    """Why LOOSE_TOL exists: the page's own printed values disagree at the 5th decimal."""
    import math

    e = EXAMPLE_2["expect"]
    # C-4: LTST = LMST + EOT / 15 from the printed LMST and EOT gives 0.00020 h, not 0.00025 h.
    ltst_from_printed = e["lmst_hours"] + e["eot_deg"] / 15.0
    assert abs(ltst_from_printed - e["ltst_hours"]) > 4e-5
    # D-1: the printed formula applied to the printed Ls gives -13.42040, not -13.42065.
    ls = math.radians(e["ls"])
    decl_from_printed = math.degrees(math.asin(0.42565 * math.sin(ls))) + 0.25 * math.sin(ls)
    assert abs(decl_from_printed - e["declination"]) > 2e-4
    # Our results still sit within LOOSE_TOL of the printed values.
    assert abs(decl_from_printed - e["declination"]) < LOOSE_TOL["declination"]


def test_lmst_wraps_into_0_to_24_hours():
    r = mars24.solar_state(datetime(2025, 8, 21, 12, tzinfo=UTC), lon_east=137.42, lat=-4.8)
    for h in (r.mst_hours, r.lmst_hours, r.ltst_hours):
        assert 0.0 <= h < 24.0


def test_east_longitude_moves_local_time_later():
    t = datetime(2025, 8, 21, 12, tzinfo=UTC)
    a = mars24.solar_state(t, lon_east=137.0, lat=0.0).lmst_hours
    b = mars24.solar_state(t, lon_east=152.0, lat=0.0).lmst_hours
    assert (b - a) % 24 == pytest.approx(1.0, abs=1e-9)  # 15 degrees east = 1 hour later


# B2: leap seconds


@pytest.mark.parametrize(
    ("utc", "expected"),
    [
        (datetime(2000, 1, 6, tzinfo=UTC), 64.184),
        (datetime(2004, 1, 3, tzinfo=UTC), 64.184),
        (datetime(2012, 8, 6, 5, 17, 57, tzinfo=UTC), 67.184),
        (datetime(2016, 9, 15, tzinfo=UTC), 68.184),
        (datetime(2017, 1, 1, tzinfo=UTC), 69.184),
        (datetime(2025, 8, 21, tzinfo=UTC), 69.184),
    ],
)
def test_tt_minus_utc_from_the_iers_table(utc, expected):
    assert leapseconds.tt_minus_utc(utc) == pytest.approx(expected, abs=1e-9)


def test_leap_second_table_records_its_expiry():
    assert leapseconds.table_expiry() == datetime(2027, 6, 28, tzinfo=UTC).date()


def test_dates_past_the_table_expiry_warn():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = leapseconds.tt_minus_utc(datetime(2030, 1, 1, tzinfo=UTC))
    assert value == pytest.approx(69.184)
    assert any(issubclass(w.category, leapseconds.LeapSecondTableExpired) for w in caught)


def test_naive_datetimes_are_rejected():
    with pytest.raises(ValueError):
        leapseconds.tt_minus_utc(datetime(2020, 1, 1))
