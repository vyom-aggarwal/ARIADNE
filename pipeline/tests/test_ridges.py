# Written with AI assistance (Claude Code). See AI_USE.md.
"""Ridges, hollows and fractures on a synthetic boxwork (acceptance test C6)."""

import numpy as np
from affine import Affine

from ariadne.derive import ridges, terrain


def boxwork(n=120, period=30, wall=4, height=1.5):
    """A grid of 1.5 m ridges, 4 m wide, every 30 m, around flat hollows."""
    z = np.zeros((n, n))
    on = (np.arange(n) % period) < wall
    z[on, :] = height
    z[:, on] = height
    return z


def test_ridges_on_the_walls_and_hollows_between():
    z = boxwork()
    tpi10 = terrain.tpi(z, 1.0, 10.0)
    relief = terrain.local_relief(z, 1.0, 2.0)
    cls = ridges.ridge_hollow(tpi10, relief, 0.3, -0.3, 0.8)
    assert cls[31, 45] == ridges.RIDGE  # on a wall
    assert cls[45, 45] in (ridges.OTHER, ridges.HOLLOW)  # mid-hollow: TPI near zero or below
    assert cls[36, 45] == ridges.HOLLOW  # foot of the wall, inside the hollow


def test_a_dark_line_on_a_ridge_is_traced_and_short_ones_dropped():
    img = np.full((240, 240), 160, dtype=np.uint8)
    img[118:121, 20:220] = 60  # a dark line 200 px (50 m at 25 cm) long
    img[40:43, 40:60] = 60  # a short one, 20 px (5 m)
    ridge = np.ones_like(img, dtype=bool)
    mask = ridges.fracture_mask(img, ridge, [1, 2], 0.05, tile=128, pad=16)
    assert mask[119, 120]
    t = Affine(0.25, 0, 0, 0, -0.25, 60)
    feats, _ = ridges.skeleton_lines(mask, t, 10.0)
    lengths = sorted(f["properties"]["length_m"] for f in feats)
    assert len(feats) == 1
    assert 45 < lengths[0] < 52
    assert feats[0]["geometry"]["type"] == "LineString"


def test_no_fractures_outside_the_ridge_mask():
    img = np.full((100, 100), 160, dtype=np.uint8)
    img[49:52, 10:90] = 60
    mask = ridges.fracture_mask(img, np.zeros_like(img, dtype=bool), [1, 2], 0.05)
    assert not mask.any()
