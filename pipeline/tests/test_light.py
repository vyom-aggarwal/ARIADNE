# Written with AI assistance (Claude Code). See AI_USE.md.
"""Light: shadows, incidence, sunrise and relative temperature (acceptance test C9)."""

import math
from datetime import UTC, datetime

import numpy as np
import pytest

from ariadne.derive import horizons as hz
from ariadne.derive import light


def test_shadow_exactly_when_the_sun_is_below_the_interpolated_horizon():
    bands = np.zeros(72)
    bands[18], bands[19] = 10.0, 20.0  # east: 90 and 95 degrees
    assert light.in_shadow(bands, 92.5, 14.9)
    assert not light.in_shadow(bands, 92.5, 15.1)
    assert not light.in_shadow(bands, 270.0, 0.1)


@pytest.mark.parametrize(
    ("slope", "aspect", "az", "el", "expected"),
    [
        (0.0, np.nan, 123.0, 90.0, 1.0),  # sun overhead on flat ground
        (20.0, 180.0, 0.0, 90.0, math.cos(math.radians(20))),  # overhead on a slope
        (30.0, 90.0, 90.0, 60.0, 1.0),  # sun square-on to an east-facing 30 degree slope
        (30.0, 270.0, 90.0, 30.0, 0.0),  # sun grazing the back of a west-facing slope
    ],
)
def test_incidence_on_sloped_planes(slope, aspect, az, el, expected):
    assert float(light.incidence_cos(slope, aspect, az, el)) == pytest.approx(expected, abs=1e-9)


def _track():
    return light.local_noon_track(datetime(2025, 11, 13, tzinfo=UTC), 137.39, -4.82, 60)


def test_sunrise_is_when_the_sun_reaches_a_constant_horizon():
    tr = _track()
    t = np.array([(x - tr.times[0]).total_seconds() for x in tr.times])
    rise0, set0 = light.sunrise_sunset_point(np.zeros(72), tr)
    rise5, set5 = light.sunrise_sunset_point(np.full(72, 5.0), tr)
    assert np.interp(rise0, t, tr.elevation) == pytest.approx(0.0, abs=0.02)
    assert np.interp(rise5, t, tr.elevation) == pytest.approx(5.0, abs=0.02)
    assert rise5 > rise0 and set5 < set0
    # morning sun is in the east
    assert 45 < np.interp(rise0, t, tr.azimuth) < 135


def test_grid_sunrise_matches_the_point_version():
    tr = _track()
    h = np.zeros((72, 3, 3))
    h[:, 1, 1] = 8.0
    codes = hz.quantize(h, -12.0, 0.4)
    rise, sset, insol = light.sun_grid(
        codes, -12.0, 0.4, hz.NODATA_CODE, tr, np.zeros((3, 3)), np.full((3, 3), np.nan)
    )
    r_pt, s_pt = light.sunrise_sunset_point(np.full(72, 8.0), tr)
    assert rise[1, 1] == pytest.approx(r_pt, abs=1.0)
    assert sset[1, 1] == pytest.approx(s_pt, abs=1.0)
    assert insol[0, 0] == pytest.approx(1.0, abs=1e-6)  # flat open ground
    assert insol[1, 1] < 1.0


def test_relative_temperature_keeps_the_rems_timing():
    t = np.linspace(0, 24, 97)
    rems = 230 + 40 * np.sin((t - 7) / 24 * 2 * np.pi)
    warm = light.relative_ground_temperature(rems, 1.2, 1.0)
    cool = light.relative_ground_temperature(rems, 0.6, 1.0)
    assert int(np.argmax(warm)) == int(np.argmax(rems)) == int(np.argmax(cool))
    assert warm.max() > rems.max() > cool.max()
    assert light.relative_ground_temperature(rems, 1.0, 1.0) == pytest.approx(rems)


def test_planetographic_latitude_is_slightly_larger():
    assert light.planetographic_latitude(-4.8) < -4.8
    assert light.planetographic_latitude(-4.8) == pytest.approx(-4.856, abs=0.002)


@pytest.mark.parametrize(
    "after", [datetime(2014, 12, 24, tzinfo=UTC), datetime(2023, 12, 23, tzinfo=UTC)]
)
def test_all_four_seasons_are_found_for_any_start(after):
    from ariadne.derive.run import mars_year_dates
    from ariadne.models import msl_time

    dates = mars_year_dates(after)
    assert [label for label, _ in dates] == ["Ls 0", "Ls 90", "Ls 180", "Ls 270"]
    for (label, day), target in zip(dates, (0, 90, 180, 270), strict=True):
        ls = msl_time.solar_longitude(day)
        assert abs((ls - target + 180) % 360 - 180) < 1.0, (label, ls)
    assert dates[0][1] > after


def test_sun_statistics_skip_cells_near_the_crop_edge():
    from ariadne.derive.run import edge_filter

    samples = {
        "rows": np.array([5, 1500, 1500, 3990]),
        "cols": np.array([1500, 1500, 10, 1500]),
        "near": np.zeros((4, 72)),
        "comb": np.zeros((4, 72)),
    }
    kept = edge_filter(samples, (4000, 4000), 1.0, 1000.0)
    assert list(kept["rows"]) == [1500] and list(kept["cols"]) == [1500]
    assert kept["near"].shape == (1, 72)
