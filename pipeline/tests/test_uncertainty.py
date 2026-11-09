# Written with AI assistance (Claude Code). See AI_USE.md.
"""Per-cell confidence (acceptance test C11)."""

import numpy as np
import pytest
from affine import Affine

from ariadne.derive import uncertainty as un
from ariadne.fetch.coverage import HIRISE, NODATA, OTHER

SCORE = {"hirise": 1.0, "other": 0.3, "nodata": 0.0}
W = {"source": 0.5, "imagery": 0.3, "flags": 0.2}


def test_confidence_ordering_and_range():
    src = np.array([HIRISE, HIRISE, HIRISE, OTHER, NODATA])
    dist = np.array([0.0, 300.0, 0.0, 0.0, 0.0])
    flags = np.array([0, 0, 2, 0, 0])
    c = un.confidence(src, dist, flags, SCORE, 100.0, W)
    assert c[0] == pytest.approx(1.0)
    assert c[0] > c[1] and c[0] > c[2] and c[0] > c[3]
    assert c[4] == 0.0
    assert np.all((c >= 0) & (c <= 1))


def test_distance_to_points():
    t = Affine(1, 0, 0, 0, -1, 10)
    d = un.distance_to_points((10, 10), t, [0.5], [9.5])
    assert d[0, 0] == 0 and d[0, 3] == pytest.approx(3.0) and d[4, 3] == pytest.approx(5.0)
