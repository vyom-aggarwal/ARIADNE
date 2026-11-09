# Written with AI assistance (Claude Code). See AI_USE.md.
"""Terrain basics on synthetic surfaces with known answers (acceptance test C1)."""

import math

import numpy as np
import pytest

from ariadne.derive import terrain

RES = 1.0


def plane(n=41, slope_deg=10.0, facing_deg=90.0, res=RES):
    """A plane that faces (descends toward) compass direction `facing_deg`."""
    rows, cols = np.mgrid[0:n, 0:n].astype(float)
    east, north = cols * res, -rows * res
    g = math.tan(math.radians(slope_deg))
    a = math.radians(facing_deg)
    # height falls along the facing direction
    return -g * (east * math.sin(a) + north * math.cos(a))


@pytest.mark.parametrize("facing", [0.0, 90.0, 180.0, 270.0, 45.0])
def test_tilted_plane_exact_slope_and_aspect(facing):
    z = plane(slope_deg=12.5, facing_deg=facing)
    slope, aspect = terrain.slope_aspect(z, RES)
    inner = (slice(1, -1), slice(1, -1))
    assert np.allclose(slope[inner], 12.5, atol=1e-4)
    diff = (aspect[inner] - facing + 180.0) % 360.0 - 180.0
    assert np.allclose(diff, 0.0, atol=1e-3)


def test_flat_ground_has_zero_slope_and_no_aspect():
    slope, aspect = terrain.slope_aspect(np.full((9, 9), -3600.0), RES)
    assert np.all(slope == 0)
    assert np.all(np.isnan(aspect))


def test_resolution_scales_the_gradient():
    z = plane(slope_deg=20.0, res=2.0)
    slope, _ = terrain.slope_aspect(z, 2.0)
    assert np.allclose(slope[1:-1, 1:-1], 20.0, atol=1e-4)


@pytest.mark.parametrize("z", [np.full((30, 30), -3600.0), plane(n=30, slope_deg=17.0) - 3600.0])
def test_planes_have_zero_roughness(z):
    r = terrain.roughness(z, RES, 5.0)
    assert np.allclose(r[3:-3, 3:-3], 0.0, atol=1e-6)


def test_roughness_sees_bumps():
    rng = np.random.default_rng(1)
    z = plane(n=30) + rng.normal(0, 0.2, (30, 30))
    r = terrain.roughness(z, RES, 5.0)
    assert 0.1 < float(np.median(r[3:-3, 3:-3])) < 0.3


def test_tpi_is_zero_on_a_plane_and_positive_on_a_bump():
    z = plane(n=61, slope_deg=8.0)
    t = terrain.tpi(z, RES, 10.0)
    assert np.allclose(t[12:-12, 12:-12], 0.0, atol=1e-6)
    bump = np.zeros((61, 61))
    bump[28:33, 28:33] = 1.0
    t = terrain.tpi(bump, RES, 10.0)
    assert t[30, 30] > 0.9
    assert t[30, 23] < 0.0  # within 10 m of the bump, so the bump raises the mean
    assert t[30, 5] == pytest.approx(0.0, abs=1e-9)  # beyond reach


def test_local_relief_of_a_step():
    z = np.zeros((21, 21))
    z[:, 10:] = 1.5
    rel = terrain.local_relief(z, RES, 2.0)
    assert rel[10, 10] == pytest.approx(1.5)
    assert rel[10, 2] == pytest.approx(0.0)


def test_convexity_is_positive_on_a_crest():
    rows, cols = np.mgrid[0:21, 0:21].astype(float)
    z = -0.05 * (cols - 10) ** 2  # a ridge running north-south
    c = terrain.convexity(z, RES)
    assert c[10, 10] > 0


# --- C16: slope at a traveller's footprint scale (plane fit over a disc) ---


def test_disc_weights_are_area_shares():
    w = terrain.disc_weights(3.05, RES)
    assert w.shape == (3, 3)
    assert w[1, 1] == pytest.approx(1.0)
    assert np.allclose(w, w[::-1, :]) and np.allclose(w, w[:, ::-1]) and np.allclose(w, w.T)
    assert 0.0 < w[0, 0] < w[0, 1] < 1.0
    # the weights add up to the disc's area in cells
    assert w.sum() == pytest.approx(math.pi * 1.525**2, rel=0.01)
    assert terrain.disc_weights(5.0, RES).shape == (5, 5)


@pytest.mark.parametrize("diameter", [2.5, 3.05, 5.0])
@pytest.mark.parametrize("facing", [0.0, 90.0, 225.0])
def test_footprint_slope_is_exact_on_tilted_planes(diameter, facing):
    z = plane(slope_deg=17.0, facing_deg=facing)
    slope, aspect = terrain.footprint_slope(z, RES, diameter)
    inner = (slice(4, -4), slice(4, -4))
    assert np.allclose(slope[inner], 17.0, atol=1e-4)
    diff = (aspect[inner] - facing + 180.0) % 360.0 - 180.0
    assert np.allclose(diff, 0.0, atol=1e-3)


def test_wider_footprint_lowers_slope_noise_as_predicted():
    rng = np.random.default_rng(7)
    sigma = 0.2
    z = rng.normal(0.0, sigma, (400, 400))
    for d in (2.5, 5.0):
        slope, _ = terrain.footprint_slope(z, RES, d)
        g = np.tan(np.radians(slope[10:-10, 10:-10]))
        w = terrain.disc_weights(d, RES)
        k = w.shape[0] // 2
        x = np.arange(-k, k + 1)[None, :] * RES
        # each gradient component has variance sigma^2 sum(w^2 x^2) / (sum(w x^2))^2; the
        # magnitude of two independent normal components has mean sigma_g * sqrt(pi / 2)
        sig_g = sigma * math.sqrt((w**2 * x**2).sum()) / (w * x**2).sum()
        assert g.mean() == pytest.approx(sig_g * math.sqrt(math.pi / 2), rel=0.05)
    s25, _ = terrain.footprint_slope(z, RES, 2.5)
    s50, _ = terrain.footprint_slope(z, RES, 5.0)
    assert np.median(s50) < 0.5 * np.median(s25)


def test_footprint_slope_nan_inside_the_disc_only():
    z = plane(slope_deg=5.0)
    z[20, 20] = np.nan
    slope, _ = terrain.footprint_slope(z, RES, 3.05)
    assert np.isnan(slope[20, 20]) and np.isnan(slope[21, 21]) and np.isnan(slope[19, 20])
    assert np.isfinite(slope[20, 23]) and np.isfinite(slope[23, 20])
