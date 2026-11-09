# Written with AI assistance (Claude Code). See AI_USE.md.
"""Shielding index, pressure factor and calibration (acceptance test C4)."""

import math

import numpy as np
import pytest
from scipy import integrate

from ariadne.derive import shielding as sh


def test_flat_open_ground_gives_one_and_walls_give_zero():
    assert sh.open_sky_fraction(np.zeros(72), 2.0) == pytest.approx(1.0)
    assert sh.open_sky_fraction(np.full(72, -5.0), 2.0) == pytest.approx(1.0)
    assert sh.open_sky_fraction(np.full(72, 90.0), 2.0) == pytest.approx(0.0)


@pytest.mark.parametrize("n", [0.0, 1.0, 3.7])
def test_closed_form_equals_numerical_integration(n):
    rng = np.random.default_rng(int(n * 10))
    h = rng.uniform(-5, 60, 72)

    def open_part(hdeg):
        top = math.radians(90.0 - max(hdeg, 0.0))
        val, _ = integrate.quad(lambda th: math.cos(th) ** n * math.sin(th), 0.0, top)
        return val

    hemi, _ = integrate.quad(lambda th: math.cos(th) ** n * math.sin(th), 0.0, math.pi / 2)
    numeric = np.mean([open_part(x) for x in h]) / hemi
    assert sh.open_sky_fraction(h, n) == pytest.approx(numeric, abs=1e-9)


def test_blocked_fraction_is_mean_sine_and_matches_the_paper_example():
    h = np.full(72, 11.0)
    assert sh.blocked_fraction(h) == pytest.approx(math.sin(math.radians(11.0)))
    # Ehresmann et al. 2021: an average blocking angle of 11 degrees ~ 0.37 pi of 2 pi sr ~ 19%
    assert sh.blocked_fraction(h) == pytest.approx(0.19, abs=0.005)


def test_s_rises_with_n_for_any_partial_horizon():
    h = np.r_[np.full(36, 16.0), np.full(36, 6.0)]
    values = [float(sh.open_sky_fraction(h, n)) for n in (0, 1, 2, 5, 10)]
    assert values == sorted(values)


def test_pressure_factor():
    kw = dict(z_ref=-4379.0, p_ref=849.0, kappa=-0.21, dose_ref=300.0, scale_height=11000.0)
    assert sh.pressure_factor(-4379.0, **kw) == pytest.approx(1.0)
    # 110 m lower: p = 849 exp(0.01) = 857.53 Pa, so f = 1 - 0.21 * 8.53 / 300
    p = 849.0 * math.exp(110.0 / 11000.0)
    expected = 1.0 - 0.21 * (p - 849.0) / 300.0
    assert sh.pressure_factor(-4489.0, **kw) == pytest.approx(expected)
    assert sh.pressure_factor(-4489.0, **kw) < 1.0 < sh.pressure_factor(-4200.0, **kw)


def test_column_to_pressure():
    assert sh.column_to_pressure(23.0, 3.69) == pytest.approx(848.7)


def _synthetic_case():
    park = np.r_[np.full(36, 16.0), np.full(36, 6.0)]
    base = [np.full((2, 72), 3.0), np.full((1, 72), 4.0), np.full((2, 72), 2.0)]
    f_base = [np.ones(len(b)) for b in base]
    return park, base, f_base


def test_calibration_recovers_a_known_n():
    park, base, f_base = _synthetic_case()
    true_n = 1.7
    target = sh.dose_ratio(true_n, park, 1.0, base, f_base)
    cal = sh.calibrate_n(
        park, 1.0, base, f_base, target, ratio_bounds=(target - 0.004, target + 0.004)
    )
    assert cal.n == pytest.approx(true_n, abs=0.002)
    assert cal.crossings == 1
    assert cal.n_low < cal.n < cal.n_high


def test_calibration_reports_no_fit():
    park, base, f_base = _synthetic_case()
    cal = sh.calibrate_n(park, 1.0, base, f_base, target_ratio=0.5)
    assert cal.n is None
    assert "No n" in cal.note


def test_shielding_map_matches_point_formula():
    rng = np.random.default_rng(5)
    bands = rng.uniform(-5, 40, (72, 3, 4)).astype(np.float32)
    s_map = sh.shielding_map(iter(bands), 1.5, 72)
    s_pt = sh.open_sky_fraction(np.moveaxis(bands, 0, -1), 1.5)
    assert np.allclose(s_map, s_pt, atol=1e-6)
