# Written with AI assistance (Claude Code). See AI_USE.md.
"""Ridge-map labeling sample and tuning (acceptance tests C19 and C20)."""

import json
import zlib

import numpy as np
import pytest

from ariadne.derive import ridge_labels as rl
from ariadne.derive.ridges import HOLLOW, OTHER, RIDGE


def predicted_map(n=300):
    rng = np.random.default_rng(1)
    pred = np.full((n, n), OTHER, dtype=np.uint8)
    pred[rng.random((n, n)) < 0.15] = RIDGE
    pred[rng.random((n, n)) < 0.15] = HOLLOW
    return pred


# --- C19: the sample ---


def test_sample_is_stratified_reproducible_spaced_and_off_the_edge():
    pred = predicted_map()
    a = rl.stratified_sample(pred, n_per_class=30, min_edge_px=25, min_spacing_px=10, seed=4)
    b = rl.stratified_sample(pred, n_per_class=30, min_edge_px=25, min_spacing_px=10, seed=4)
    assert a == b
    counts = {c: sum(p["predicted"] == c for p in a) for c in ("ridge", "hollow", "other")}
    assert counts == {"ridge": 30, "hollow": 30, "other": 30}
    rc = np.array([[p["row"], p["col"]] for p in a])
    assert rc.min() >= 25 and rc.max() < 300 - 25
    d = np.hypot(*(rc[:, None, :] - rc[None, :, :]).transpose(2, 0, 1))
    assert d[~np.eye(len(a), dtype=bool)].min() >= 10
    for p in a:
        assert {"ridge": RIDGE, "hollow": HOLLOW, "other": OTHER}[p["predicted"]] == pred[
            p["row"], p["col"]
        ]


def test_halves_are_fixed_at_sampling_and_balanced_by_class():
    pts = rl.stratified_sample(predicted_map(), 30, 25, 10, seed=4)
    halves = rl.assign_halves(pts, seed=9)
    assert halves == rl.assign_halves(pts, seed=9)
    for c in ("ridge", "hollow", "other"):
        hs = [h["half"] for h in halves if h["predicted"] == c]
        assert hs.count("tune") == hs.count("test") == 15
    assert len({h["id"] for h in halves}) == len(halves)


def test_page_lists_every_point_and_hides_class_and_half(tmp_path):
    pts = rl.assign_halves(rl.stratified_sample(predicted_map(), 6, 25, 10, seed=4), seed=9)
    html = rl.page_html("boxwork", pts, "sample-v1")
    for p in pts:
        assert p["id"] in html
    assert '"predicted"' not in html and '"half"' not in html
    for word in ("Ridge", "Hollow", "Neither", "Unsure", "Download"):
        assert word in html
    assert 'lang="en"' in html and "<title>" in html


def test_png_writer_round_trips_through_zlib(tmp_path):
    rgb = np.zeros((3, 4, 3), dtype=np.uint8)
    rgb[1, 2] = (10, 200, 30)
    path = tmp_path / "x.png"
    rl.write_png(path, rgb)
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    idat = data[data.index(b"IDAT") + 4 : data.index(b"IEND") - 8]
    raw = zlib.decompress(idat)
    assert len(raw) == 3 * (1 + 4 * 3)
    row1 = raw[1 * 13 + 1 : 2 * 13]
    assert tuple(row1[6:9]) == (10, 200, 30)


# --- C20: tuning on one half, testing on the other ---


def synthetic_features(n=240, seed=3):
    """Points whose true class follows TPI at sigma 1, radius 10, with a little noise."""
    rng = np.random.default_rng(seed)
    truth = rng.choice(["ridge", "hollow", "neither"], size=n)
    base = {"ridge": 0.6, "hollow": -0.6, "neither": 0.0}
    feats = {}
    for s in rl.SMOOTH_SIGMAS_M:
        for r in rl.TPI_RADII_M:
            noise = 0.1 if (s, r) == (1.0, 10.0) else 0.5
            feats[(s, r)] = np.array([base[t] for t in truth]) + rng.normal(0, noise, n)
    relief = np.where(truth == "ridge", 1.5, 0.5) + rng.normal(0, 0.1, n)
    texture = rng.random(n)
    return truth, feats, relief, texture


def test_tuning_uses_only_the_tuning_half():
    truth, feats, relief, texture = synthetic_features()
    half = np.array(["tune", "test"] * (len(truth) // 2))
    labels = truth.copy()
    best = rl.tune(labels, half, feats, relief, texture)
    assert (best["smooth_sigma_m"], best["tpi_radius_m"]) == (1.0, 10.0)
    shuffled = labels.copy()
    test_idx = np.where(half == "test")[0]
    shuffled[test_idx] = np.random.default_rng(0).permutation(shuffled[test_idx])
    assert rl.tune(shuffled, half, feats, relief, texture) == best


def test_unsure_labels_are_dropped_from_tuning_and_scores():
    truth, feats, relief, texture = synthetic_features()
    half = np.array(["tune", "test"] * (len(truth) // 2))
    labels = truth.copy().astype(object)
    labels[::7] = "unsure"
    best = rl.tune(labels, half, feats, relief, texture)
    assert best["tuning_points"] == int(np.sum((half == "tune") & (labels != "unsure")))


def test_precision_recall_and_intervals_on_a_known_table():
    truth = np.array(["ridge"] * 10 + ["neither"] * 10)
    pred = np.array(["ridge"] * 8 + ["neither"] * 2 + ["ridge"] * 1 + ["neither"] * 9)
    m = rl.scores(truth, pred, weights=None, n_boot=0)
    assert m["ridge"]["precision"] == pytest.approx(8 / 9, abs=1e-4)
    assert m["ridge"]["recall"] == pytest.approx(0.8)
    lo, hi = rl.wilson(8, 9)
    assert lo < 8 / 9 < hi
    assert lo == pytest.approx(0.5650, abs=1e-3) and hi == pytest.approx(0.9801, abs=1e-3)
    # weights: each point counts by its stratum's share of the site
    w = np.array([2.0] * 10 + [1.0] * 10)
    mw = rl.scores(truth, pred, weights=w, n_boot=0)
    assert mw["ridge"]["precision"] == pytest.approx(16 / 17, abs=1e-4)


def test_labels_file_round_trip(tmp_path):
    pts = rl.assign_halves(rl.stratified_sample(predicted_map(), 6, 25, 10, seed=4), seed=9)
    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps({"site": "boxwork", "sample": "sample-v1", "labels": {pts[0]["id"]: "ridge"}})
    )
    got = rl.read_labels(path, pts, "sample-v1")
    assert got[pts[0]["id"]] == "ridge" and len(got) == 1
    with pytest.raises(ValueError):
        rl.read_labels(path, pts, "another-sample")
