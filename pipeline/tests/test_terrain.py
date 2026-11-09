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
