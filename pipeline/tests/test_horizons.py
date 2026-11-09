# Written with AI assistance (Claude Code). See AI_USE.md.
"""Near- and far-field horizons on synthetic terrain (acceptance tests C2 and C3)."""

import math

import numpy as np
import pytest
from affine import Affine

from ariadne.derive import horizons as hz

AZ = hz.azimuths(72)


def grid_transform(res, left=0.0, top=0.0):
    return Affine(res, 0.0, left, 0.0, -res, top)


# C2: near field


def test_pit_centre_sees_the_analytic_angle_in_every_azimuth():
    res, radius, depth = 0.1, 20.0, 10.0
    n = int(2 * (radius + 5) / res)
    rows, cols = np.mgrid[0:n, 0:n]
    cx = cy = n / 2 * res
    d = np.hypot((cols + 0.5) * res - cx, (rows + 0.5) * res - cy)
    z = np.where(d < radius, -depth, 0.0)
    t = grid_transform(res, 0.0, n * res)
    dist = hz.near_distances(radius + 4, res, 32.0, 1.03)
    h = hz.horizons_at_points(z, t, np.array([cx]), np.array([n * res - cy]), AZ, dist, 0.0)
    expected = math.degrees(math.atan(depth / radius))
    assert np.all(np.abs(h[0] - expected) < 0.3), (h.min(), h.max(), expected)


def test_flat_plane_horizon_is_only_the_curvature_dip():
    z = np.full((200, 200), -3600.0)  # big enough that 60 m rays stay inside
    dist = hz.near_distances(60, 1.0, 32.0, 1.03)
    band = hz.near_field_band(z, 1.0, 45.0, dist, 1.0)
    # 1 m up, the lowest-looking sample is the farthest (60 m): atan(-(1 + d^2/2R) / d)
    expected = -math.degrees(math.atan((1.0 + 60.0**2 / (2 * hz.R_MARS)) / 60.0))
    assert band[100, 100] == pytest.approx(expected, abs=1e-4)
    # with the observer on the ground, the dip is under a microradian
    band0 = hz.near_field_band(z, 1.0, 45.0, dist, 0.0)
    assert -1e-4 < band0[100, 100] <= 0.0


def test_azimuth_90_looks_east():
    z = np.zeros((41, 41))
    z[:, 30:] = 10.0  # a wall to the east
    dist = hz.near_distances(20, 1.0, 32.0, 1.03)
    east = hz.near_field_band(z, 1.0, 90.0, dist, 0.0)[20, 20]
    west = hz.near_field_band(z, 1.0, 270.0, dist, 0.0)[20, 20]
    north = hz.near_field_band(z, 1.0, 0.0, dist, 0.0)[20, 20]
    assert east == pytest.approx(math.degrees(math.atan(10 / 10)), abs=0.01)
    assert west < 0.01 and north < 0.01


def test_band_and_point_versions_agree():
    rng = np.random.default_rng(3)
    z = rng.normal(0, 2, (50, 50)).cumsum(axis=0) * 0.2
    t = grid_transform(1.0, 0.0, 50.0)
    dist = hz.near_distances(30, 1.0, 32.0, 1.03)
    pts = [(25, 25), (10, 40), (40, 12)]
    xs = np.array([c + 0.5 for _, c in pts])
    ys = np.array([50.0 - (r + 0.5) for r, _ in pts])
    hp = hz.horizons_at_points(z, t, xs, ys, AZ[::9], dist, 1.0)
    for ai, a in enumerate(AZ[::9]):
        band = hz.near_field_band(z, 1.0, a, dist, 1.0)
        for pi, (r, c) in enumerate(pts):
            assert band[r, c] == pytest.approx(hp[pi, ai], abs=1e-4)


def test_quantization_round_trip():
    h = np.array([-12.0, -3.3, 0.0, 0.19, 26.57, 61.0, 89.6, np.nan])
    back = hz.dequantize(hz.quantize(h, -12.0, 0.4), -12.0, 0.4)
    assert np.all(np.abs(back[:-1] - h[:-1]) <= 0.2 + 1e-6)
    assert np.isnan(back[-1])


def test_near_distances_are_fine_then_growing():
    d = hz.near_distances(2000, 1.0, 32.0, 1.03)
    assert d[0] == 1.0 and np.all(np.diff(d[:32]) == 1.0)
    assert d[-1] == pytest.approx(2000)
    assert np.all(np.diff(d) > 0)
    assert len(d) < 200


def test_horizon_at_azimuth_interpolates_and_wraps():
    bands = np.zeros(72)
    bands[0], bands[1], bands[71] = 10.0, 20.0, 30.0
    assert hz.horizon_at_azimuth(bands, 2.5) == pytest.approx(15.0)
    assert hz.horizon_at_azimuth(bands, 357.5) == pytest.approx(20.0)


# C3: far field


def test_far_profile_max_finds_a_distant_plateau_after_curvature():
    res = 200.0
    n = 200  # 40 km square
    z = np.zeros((n, n))
    row = 100
    c0 = 100  # observer column (pixel centre)
    z[:, c0 + 50 : c0 + 70] = 4000.0  # plateau from 10 km to 14 km east
    t = grid_transform(res)
    x0, y0 = (c0 + 0.5) * res, -(row + 0.5) * res
    dist = hz.far_distances(0.0, 19_000.0, res, 1.01)
    tmax, dstar = hz.profile_max_at_points(
        z, t, np.array([x0]), np.array([y0]), np.array([1.0]), np.array([90.0]), dist
    )
    d = 10_000.0
    expected = math.degrees(math.atan((4000.0 - d * d / (2 * hz.R_MARS) - 1.0) / d))
    assert math.degrees(math.atan(tmax[0, 0])) == pytest.approx(expected, abs=0.01)
    assert dstar[0, 0] == pytest.approx(d)


def test_tie_offset_is_recovered():
    fine = np.full((100, 100), -4000.0) + np.linspace(0, 20, 100)[None, :]
    ft = grid_transform(1.0, 1000.0, -1000.0)
    coarse = np.full((40, 40), -4005.0) + np.linspace(-200, 200, 40)[None, :] * 0
    ct = grid_transform(100.0, 0.0, 0.0)
    off = hz.tie_offset(fine, ft, coarse, ct, step=5)
    assert off == pytest.approx(float(np.median(fine[::5, ::5])) + 4005.0, abs=1e-6)


def test_far_field_on_a_grid_and_combined_horizon():
    # fine crop 400 m square inside a 60 km regional grid with a plateau 10 km to the east
    fine = np.zeros((400, 400))
    ft = grid_transform(1.0, 30_000.0, -30_000.0)
    reg = np.zeros((300, 300)) - 2.0  # regional DEM sits 2 m low; the tie fixes it
    rt = grid_transform(200.0)
    reg[:, int(40_400 / 200) : int(44_000 / 200)] = 3000.0
    az = np.array([0.0, 90.0, 180.0, 270.0])
    ff = hz.far_field(fine, ft, reg, rt, az, 2000.0, 25_000.0, 100.0, 200.0, 1.01, 1.0)
    assert ff.tie_offset_m == pytest.approx(2.0)
    east = hz.far_field_band(ff, 1, fine, ft, 1.0)
    north = hz.far_field_band(ff, 0, fine, ft, 1.0)
    # The crop centre is at x = 30,200 m. The first plateau pixel centre is at 40,500 m, so with
    # bilinear sampling every 200 m the first full-height sample is at 40,600 m (d = 10,400 m).
    d = 10_400.0
    expected = math.degrees(math.atan((3000.0 - d * d / (2 * hz.R_MARS) - 1.0) / d))
    assert east[200, 200] == pytest.approx(expected, abs=0.05)
    assert north[200, 200] < 0.0
    near = np.full_like(east, 5.0)
    combined = np.maximum(near, east)
    assert combined[200, 200] == pytest.approx(max(5.0, expected), abs=0.05)


def test_distance_to_box_edge():
    d = hz.distance_to_box_edge(
        np.array([5.0]), np.array([5.0]), np.array([0.0, 90.0, 45.0]), (0, 0, 10, 10)
    )
    assert d[0, 0] == pytest.approx(5.0)
    assert d[0, 1] == pytest.approx(5.0)
    assert d[0, 2] == pytest.approx(5.0 * math.sqrt(2))


def test_coregistration_recovers_a_known_shift_and_offset():
    def g(x, y):  # smooth terrain: a slope plus broad hills
        return 0.05 * x + 0.03 * y + 60 * np.sin(x / 700.0) * np.cos(y / 900.0)

    fine_t = grid_transform(10.0, 7000.0, -7000.0)
    rr, cc = np.mgrid[0:600, 0:600]
    fx, fy = hz.apply_transform(fine_t, cc + 0.5, rr + 0.5)
    fine = g(fx, fy)
    dx, dy, dz = 300.0, -200.0, 20.0
    coarse_t = grid_transform(400.0, 0.0, 0.0)
    cr, ccol = np.mgrid[0:50, 0:50]
    ux, uy = hz.apply_transform(coarse_t, ccol + 0.5, cr + 0.5)
    coarse = g(ux - dx, uy - dy) - dz  # so coarse(x + dx, y + dy) + dz = g(x, y)
    co = hz.coregister(fine, fine_t, coarse, coarse_t, search_m=600.0, step=5)
    assert co.dx == pytest.approx(dx, abs=20)
    assert co.dy == pytest.approx(dy, abs=20)
    assert co.dz == pytest.approx(dz, abs=3)
    assert co.mad < co.mad_vertical_only
    # sampling through the shifted transform applies the shift
    st = hz.shifted(coarse_t, co.dx, co.dy)
    v = hz.sample_bilinear(coarse, st, [10_000.0], [-10_000.0])[0]
    w = hz.sample_bilinear(coarse, coarse_t, [10_000.0 + co.dx], [-10_000.0 + co.dy])[0]
    assert v == pytest.approx(w)
