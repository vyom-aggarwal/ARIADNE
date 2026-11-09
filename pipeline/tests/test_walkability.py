# Written with AI assistance (Claude Code). See AI_USE.md.
"""Walkability on synthetic inputs (acceptance test C5)."""

import numpy as np
import pytest
from affine import Affine
from rasterio.crs import CRS

from ariadne.derive import terrain
from ariadne.derive import walkability as wk

W = {"slope": 1.0, "roughness": 1.0, "dark": 1.0, "sand": 0.5, "dropoff": 1.0}


def test_classes_switch_at_the_thresholds():
    slope = np.array([0.0, 15.0, 15.01, 25.0, 25.01, np.nan])
    assert list(wk.classify(slope, (15, 25))) == [0, 0, 1, 1, 2, 2]


def test_no_go_wins_and_cost_is_nan_there():
    slope = np.array([5.0, 5.0, 30.0])
    rough = np.array([0.05, 0.2, 0.05])
    zeros = np.zeros(3)
    cls, cost = wk.walkability(
        slope,
        rough,
        zeros,
        zeros,
        np.zeros(3, bool),
        (15, 25),
        (0.15, 0.35),
        0.1,
        None,
        wk.CAUTION,
        W,
    )
    assert list(cls) == [0, 1, 2]
    assert np.isfinite(cost[:2]).all() and np.isnan(cost[2])


def test_cost_rises_with_slope():
    slope = np.array([0.0, 5.0, 10.0, 14.0])
    z = np.zeros(4)
    _, cost = wk.walkability(
        slope, z, z, z, np.zeros(4, bool), (15, 25), (0.15, 0.35), 0.1, None, 1, W
    )
    assert np.all(np.diff(cost) > 0)
    assert cost[0] == pytest.approx(1.0)


def test_dark_fraction_counts_dark_spots_relative_to_surroundings():
    img = np.full((64, 64), 150, dtype=np.uint8)
    img[8:12, 8:12] = 40  # one 1 m block fully dark
    img[:, 32:] = 90  # a darker half (a mosaic seam), not rocks
    frac = wk.dark_fraction(img, 4, 5, 0.6)
    assert frac[2, 2] == pytest.approx(1.0)
    assert frac[2, 12] == pytest.approx(0.0)  # the darker half is not counted as dark
    assert frac[10, 4] == pytest.approx(0.0)


def test_coherence_is_high_for_ripples_and_low_for_noise():
    rows, cols = np.mgrid[0:128, 0:128]
    ripples = (128 + 60 * np.sin(cols * 2 * np.pi / 8)).astype(np.uint8)
    rng = np.random.default_rng(0)
    noise = rng.integers(60, 200, (128, 128)).astype(np.uint8)
    assert wk.orientation_coherence(ripples, 4, 5).mean() > 0.8
    assert wk.orientation_coherence(noise, 4, 5).mean() < 0.4


def test_sand_proxy_prefers_smooth_rippled_cool_ground():
    smooth = np.array([0.9, 0.1])
    rippled = np.array([0.9, 0.1])
    night = np.array([0.1, 0.9])  # low night-IR brightness = cool = sandy
    s = wk.sand_proxy(smooth, rippled, night)
    assert s[0] > 0.8 > 0.2 > s[1]
    assert wk.sand_proxy(smooth, rippled, None)[0] == pytest.approx(0.9)


def test_a_one_metre_step_is_a_dropoff():
    z = np.zeros((21, 21))
    z[:, :10] = 1.2  # a ledge 1.2 m high
    conv = terrain.convexity(z, 1.0)
    rel = terrain.local_relief(z, 1.0, 2.0)
    d = wk.dropoffs(conv, rel, 0.3, 1.0)
    assert d[10, 9]  # the top edge of the ledge
    assert not d[10, 2] and not d[10, 18]


def test_percentile_rank_and_regridding():
    r = wk.percentile_rank(np.array([3.0, 1.0, 2.0, np.nan]))
    assert list(r[:3]) == pytest.approx([1.0, 1 / 3, 2 / 3])
    assert np.isnan(r[3])
    src = np.arange(16, dtype=np.float32).reshape(4, 4)
    out = wk.to_grid(
        src,
        Affine(2, 0, 0, 0, -2, 8),
        (8, 8),
        Affine(1, 0, 0, 0, -1, 8),
        CRS.from_string("+proj=eqc +R=3396190 +units=m"),
        wk.Resampling.nearest,
    )
    assert out[0, 0] == 0 and out[7, 7] == 15


# --- C17: footprint scales come from config, each with a source ---


def test_slope_scales_from_the_real_config():
    from ariadne.config import load_derive_config

    cfg = load_derive_config()
    s = wk.slope_scales(cfg)
    assert s["r_eff_m"] == pytest.approx(2.5)
    assert s["rover_m"] == pytest.approx(3.05)
    assert s["walker_m"] == pytest.approx(2.5)
    assert s["r_eff_coarse_m"] == pytest.approx(5.0)
    assert s["rover_coarse_m"] == pytest.approx(5.0)
    assert s["walker_coarse_m"] == pytest.approx(5.0)
    for key in ("dem_image_pixel_m", "dem_resolution_pixels", "rover_footprint_m"):
        entry = cfg["walkability"][key]
        assert entry["label"] in ("MEASURED", "MODELED") and entry.get("source")


def test_slope_scales_take_the_larger_of_footprint_and_resolution():
    def e(v):
        return {"value": v, "label": "PLACEHOLDER"}

    cfg = {
        "walkability": {
            "dem_image_pixel_m": e(0.5),
            "dem_resolution_pixels": e(10),
            "dem_resolution_pixels_coarse": e(20),
            "rover_footprint_m": e(3.0),
            "walker_footprint_m": e(1.0),
        }
    }
    s = wk.slope_scales(cfg)
    assert s["r_eff_m"] == pytest.approx(5.0)
    assert s["rover_m"] == pytest.approx(5.0)  # the DEM, not the rover, limits the scale
    assert s["walker_m"] == pytest.approx(5.0)
    assert s["rover_coarse_m"] == pytest.approx(10.0)
