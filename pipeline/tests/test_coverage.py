# Written with AI assistance (Claude Code). See AI_USE.md.
"""DEM source-class mask from stereo-pair footprints (acceptance test B7), on synthetic data."""

import numpy as np
import pytest
from rasterio.transform import from_origin
from shapely.geometry import box

from ariadne.fetch import coverage
from ariadne.fetch.places import MARS_RADIUS_M


def deg(m):
    return np.degrees(m / MARS_RADIUS_M)


def ode_product(obs, kind, e0, n0, e1, n1, product="RDRV11"):
    """A minimal ODE product record with a footprint given in meters."""
    lon0, lon1, lat0, lat1 = deg(e0), deg(e1), deg(n0), deg(n1)
    wkt = f"POLYGON (({lon0} {lat0}, {lon1} {lat0}, {lon1} {lat1}, {lon0} {lat1}, {lon0} {lat0}))"
    return {
        "Observation_id": obs,
        "LabelURL": f"https://hirise.lpl.arizona.edu/PDS/RDR/X/{obs}/{obs}_{kind}.LBL",
        "Footprint_C0_geometry": wkt,
    }


def test_usgs_pair_list_has_the_12_pairs_from_the_product_page():
    pairs = coverage.USGS_STEREO_PAIRS
    assert len(pairs) == 12
    assert pairs["T3"] == ("ESP_019698", "ESP_019988")
    assert pairs["Traverse"] == ("PSP_009149", "PSP_009294")
    flat = [obs for pair in pairs.values() for obs in pair]
    assert len(set(flat)) == 24


def test_observation_footprints_prefer_red_and_ignore_the_latitude_suffix():
    prods = [
        ode_product("PSP_009149_1750", "RED", 0, 0, 100, 100),
        ode_product("PSP_009149_1750", "COLOR", 40, 0, 60, 100),
    ]
    fps = coverage.observation_footprints(prods)
    assert set(fps) == {"PSP_009149"}
    assert fps["PSP_009149"].area == pytest.approx(100 * 100, rel=1e-6)


def test_a_pair_covers_only_where_both_images_overlap():
    obs = {
        "A_000001": box(0, 0, 100, 100),
        "A_000002": box(50, 0, 150, 100),
        "B_000003": box(0, 0, 10, 10),
    }
    pairs = coverage.pair_footprints(
        obs, {"AB": ("A_000001", "A_000002"), "BC": ("B_000003", "C_000004")}
    )
    assert set(pairs) == {"AB"}  # BC lacks one image, so it gives no stereo coverage
    assert pairs["AB"].bounds == pytest.approx((50, 0, 100, 100))


def test_mask_rasterizes_exactly_on_the_grid():
    transform = from_origin(0, 100, 1, 1)  # 100 x 100 one-meter cells
    valid = np.ones((100, 100), bool)
    valid[:, 95:] = False  # pretend the DEM has no data in the last 5 columns
    mask = coverage.source_class_mask((100, 100), transform, [box(10, 20, 30, 60)], valid)
    assert mask.dtype == np.uint8
    assert int((mask == coverage.HIRISE).sum()) == 20 * 40
    assert int((mask == coverage.NODATA).sum()) == 5 * 100
    assert int((mask == coverage.OTHER).sum()) == 100 * 100 - 800 - 500


def test_shares_add_up_and_points_are_classified():
    transform = from_origin(0, 100, 1, 1)
    mask = coverage.source_class_mask(
        (100, 100), transform, [box(0, 0, 50, 100)], np.ones((100, 100), bool)
    )
    pts_e = np.array([10.5, 20.5, 70.5, 90.5])
    pts_n = np.array([50.5, 50.5, 50.5, 50.5])
    s = coverage.coverage_summary(mask, transform, pts_e, pts_n)
    assert s["box_percent"]["hirise_stereo"] == pytest.approx(50.0)
    assert sum(s["box_percent"].values()) == pytest.approx(100.0)
    assert s["path_percent"]["hirise_stereo"] == pytest.approx(50.0)
    assert s["path_points"] == 4


def test_footprints_convert_to_meters_linearly():
    prods = [ode_product("ESP_019698_1750", "RED", 8_141_000, -286_000, 8_142_000, -285_000)]
    g = coverage.observation_footprints(prods)["ESP_019698"]
    assert g.bounds == pytest.approx((8_141_000, -286_000, 8_142_000, -285_000), abs=1e-6)
