# Written with AI assistance (Claude Code). See AI_USE.md.
"""The georeferencing check behind B8 finds a known shift on synthetic terrain."""

import numpy as np
import pytest
from rasterio.transform import from_origin

from ariadne.fetch import checks


def terrain(n=400):
    """Smooth hills with ridges, so elevation changes in every direction (1 m cells)."""
    y, x = np.mgrid[0:n, 0:n].astype(float)
    return (
        3.0 * np.sin(x / 9.0) * np.cos(y / 13.0) + 2.0 * np.sin((x + y) / 7.0) + 0.01 * x - 3600.0
    ).astype("float32")


def path_points(transform, n=300):
    rng = np.random.default_rng(3)
    cols = rng.uniform(80, 320, n)
    rows = rng.uniform(80, 320, n)
    east, north = transform * (cols, rows)
    return np.asarray(east), np.asarray(north)


def test_sampling_hits_pixel_centers_exactly():
    dem = terrain()
    t = from_origin(1000.49, 5000.0, 1.0, 1.0)
    e, n = t * (np.array([10.5, 200.5]), np.array([20.5, 300.5]))
    vals = checks.sample_bilinear(dem, t, e, n, nodata=-32767)
    assert vals == pytest.approx([dem[20, 10], dem[300, 200]])


def test_aligned_points_pass_with_zero_shift():
    dem = terrain()
    t = from_origin(1000.49, 5000.0, 1.0, 1.0)
    e, n = path_points(t)
    z = checks.sample_bilinear(dem, t, e, n, nodata=None)
    out = checks.georeference_check(dem, t, -32767, e, n, z)
    assert out["passed"]
    assert out["median_dem_minus_places_m"] == pytest.approx(0.0, abs=1e-6)
    assert out["best_shift_east_north_m"] == (0.0, 0.0)


def test_a_misregistered_crop_is_caught():
    dem = terrain()
    t = from_origin(1000.49, 5000.0, 1.0, 1.0)
    e, n = path_points(t)
    z = checks.sample_bilinear(dem, t, e, n, nodata=None)
    # Claim the crop sits 6 m east and 4 m south of where it really is.
    shifted = from_origin(1000.49 + 6.0, 5000.0 - 4.0, 1.0, 1.0)
    out = checks.georeference_check(dem, shifted, -32767, e, n, z)
    assert not out["passed"]
    assert out["best_shift_east_north_m"] == (6.0, -4.0)


def test_nodata_points_are_counted_not_used():
    dem = terrain()
    dem[:, :200] = -32767
    t = from_origin(0.0, 400.0, 1.0, 1.0)
    e, n = path_points(t)
    z = np.full(e.shape, -3600.0)
    out = checks.georeference_check(dem, t, -32767, e, n, z, max_shift_m=2)
    assert out["points"] + out["points_outside_or_nodata"] == len(e)
    assert out["points_outside_or_nodata"] > 0
