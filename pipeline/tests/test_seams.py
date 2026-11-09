# Written with AI assistance (Claude Code). See AI_USE.md.
"""DEM mosaic seams from stereo-pair footprints (acceptance test C18)."""

import numpy as np
import pytest
from affine import Affine
from scipy import stats
from shapely.geometry import box

from ariadne.derive import seams

T = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 100.0)  # 100 x 100 m grid, origin at the top-left


def test_footprint_edges_inside_the_dem_become_seams_and_the_crop_edge_does_not():
    extent = box(0, 0, 100, 100)
    a = box(-50, -50, 60, 150)  # spills over three crop edges: only x = 60 is inside
    b = box(40, 20, 80, 70)  # wholly inside: its four edges are seams
    lines = seams.seam_lines([a, b], extent)
    assert lines.length == pytest.approx(100 + 2 * 40 + 2 * 50)
    assert extent.exterior.intersection(lines).length == pytest.approx(0.0)


def test_seam_distance_on_a_grid():
    lines = seams.seam_lines([box(-10, -10, 50, 110)], box(0, 0, 100, 100))  # the line x = 50
    d = seams.seam_distance((100, 100), T, lines)
    cols = np.arange(100) + 0.5  # cell centres
    expected = np.abs(cols - 50.0)
    assert np.all(np.abs(d[50, :] - expected) <= 0.71)
    assert d.dtype == np.float32
    empty = seams.seam_lines([], box(0, 0, 100, 100))
    assert np.all(seams.seam_distance((10, 10), T, empty) == np.inf)


def test_model_flags_count_each_reason():
    src = np.array([[1, 2], [1, 1]], dtype=np.uint8)
    edge = np.array([[5000.0, 5000.0], [500.0, 5000.0]])
    seam = np.array([[False, True], [True, False]])
    flags = seams.model_flags(src, edge, 1000.0, seam)
    assert flags.tolist() == [[0, 2], [2, 0]]


def test_zone_statistics_and_fisher_test():
    in_zone = np.array([True] * 30 + [False] * 70)
    nogo = np.array([True] * 12 + [False] * 18 + [True] * 7 + [False] * 63)
    s = seams.zone_statistics(in_zone, nogo)
    assert s["points"] == 100 and s["points_in_zone"] == 30
    assert s["share_of_points_in_zone"] == pytest.approx(0.30)
    assert s["no_go_in_zone"] == 12 and s["no_go_total"] == 19
    assert s["share_of_no_go_in_zone"] == pytest.approx(12 / 19, abs=1e-4)
    assert s["no_go_rate_in_zone"] == pytest.approx(0.40)
    assert s["no_go_rate_outside"] == pytest.approx(0.10)
    odds, p = stats.fisher_exact([[12, 18], [7, 63]])
    assert s["odds_ratio"] == pytest.approx(odds, rel=1e-3)
    assert s["fisher_p"] == pytest.approx(p, rel=1e-3)
