# Written with AI assistance (Claude Code). See AI_USE.md.
"""`ariadne ridge-sample` and `ariadne ridge-tune`: the hand-labeled ridge check on real data.

ridge-sample draws the stratified sample from the current ridge layer, fixes the tuning and test
halves, writes the sample to config/labels/ (committed, so the split is on record before any
label) and builds the local labeling page in data/labeling/<site>/.

ridge-tune reads the labels, tunes on the tuning half only, scores the test half, writes
docs/validation/ridge-map.json and the tuned settings into config/derive.yaml. The ridge layer
and transects are then regenerated with `ariadne derive --site <site> --from-stage walkability`.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy import ndimage

from ariadne import __version__ as PIPELINE_VERSION
from ariadne.config import load_derive_config, setting
from ariadne.derive import ridge_labels as rl
from ariadne.derive import terrain
from ariadne.derive.io import read_raster
from ariadne.derive.ridges import HOLLOW, OTHER, RIDGE
from ariadne.guardrails import repo_root

N_PER_CLASS = 84
SAMPLE_SEED = 20261109
SPLIT_SEED = 1109
MIN_EDGE_M = 25.0
MIN_SPACING_M = 10.0


def sample_path(root: Path, site: str) -> Path:
    return root / "config" / "labels" / f"{site}_ridge_sample.json"


def _stratum_shares(pred: np.ndarray, valid: np.ndarray) -> dict:
    n = int(valid.sum())
    return {
        name: round(float(((pred == code) & valid).sum()) / n, 6)
        for name, code in (("ridge", RIDGE), ("hollow", HOLLOW), ("other", OTHER))
    }


def ridge_sample(site: str = "boxwork", log=print) -> Path:
    root = repo_root()
    site_dir = root / "data" / "sites" / site
    pred, t, _ = read_raster(site_dir / "derived" / "ridges.tif", as_float=False)
    dem, dt, _ = read_raster(site_dir / "dem.tif")
    ortho, ot, _ = read_raster(site_dir / "ortho.tif", as_float=False)
    res = float(t.a)
    valid = np.isfinite(dem) & (pred != 255)
    pts = rl.stratified_sample(
        pred,
        N_PER_CLASS,
        int(round(MIN_EDGE_M / res)),
        MIN_SPACING_M / res,
        SAMPLE_SEED,
        valid=valid,
    )
    pts = rl.assign_halves(pts, SPLIT_SEED)
    for p in pts:
        p["x"] = round(float(t.c + (p["col"] + 0.5) * t.a), 2)
        p["y"] = round(float(t.f + (p["row"] + 0.5) * t.e), 2)
    cfg = load_derive_config()
    body = {
        "site": site,
        "points": sorted(pts, key=lambda p: p["id"]),
        "stratum_share_of_site": _stratum_shares(pred, valid),
        "predicted_with": {
            k: setting(cfg, "ridges", k) for k in ("tpi_ridge_m", "tpi_hollow_m", "ridge_relief_m")
        },
        "seeds": {"sample": SAMPLE_SEED, "split": SPLIT_SEED},
        "rules": f"{N_PER_CLASS} points per predicted class, at least {MIN_EDGE_M:.0f} m from "
        f"the crop edge and {MIN_SPACING_M:.0f} m apart; halves balanced by class and fixed here, "
        "before any label.",
    }
    sample_id = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]
    out = {
        "sample_id": sample_id,
        "pipeline_version": PIPELINE_VERSION,
        "created_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        **body,
    }
    path = sample_path(root, site)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    page_dir = root / "data" / "labeling" / site
    (page_dir / "chips").mkdir(parents=True, exist_ok=True)
    for p in pts:
        for kind, img in rl.chips(ortho, ot, dem, dt, p["x"], p["y"]).items():
            rl.write_png(page_dir / "chips" / f"{p['id']}_{kind}.png", img)
    (page_dir / "index.html").write_text(
        rl.page_html(site, pts, sample_id), encoding="utf-8", newline="\n"
    )
    log(f"sample {sample_id}: {len(pts)} points written to {path.relative_to(root)}")
    log(f"labeling page: {(page_dir / 'index.html')}")
    return path


def point_features(site_dir: Path, points: list[dict], cfg) -> tuple[dict, np.ndarray, np.ndarray]:
    """TPI for every smoothing and radius in the search, local relief and image-texture rank at
    each point, computed on the whole site exactly as the ridge stage computes them."""
    from ariadne.derive import stages

    dem, t, crs = read_raster(site_dir / "dem.tif")
    res = float(t.a)
    rows = np.array([p["row"] for p in points])
    cols = np.array([p["col"] for p in points])
    feats = {}
    for s in rl.SMOOTH_SIGMAS_M:
        z = smoothed(dem, res, s)
        for r in rl.TPI_RADII_M:
            feats[(s, r)] = terrain.tpi(z, res, r)[rows, cols].astype(np.float64)
    relief = terrain.local_relief(dem, res, float(setting(cfg, "terrain", "relief_radius_m")))
    texture = stages.texture_rank(site_dir, dem.shape, t, crs, cfg)
    return feats, relief[rows, cols].astype(np.float64), texture[rows, cols].astype(np.float64)


def smoothed(dem: np.ndarray, res: float, sigma_m: float) -> np.ndarray:
    if sigma_m <= 0:
        return dem
    z = np.asarray(dem, dtype=np.float64)
    fill = np.where(np.isnan(z), np.nanmean(z), z)
    out = ndimage.gaussian_filter(fill, sigma_m / res, mode="nearest")
    return np.where(np.isnan(z), np.nan, out)


def _apply_to_config(root: Path, best: dict, n_labels: int, sample_id: str) -> None:
    path = root / "config" / "derive.yaml"
    text = path.read_text(encoding="utf-8")
    note = f"Tuned on {n_labels} hand labels (sample {sample_id}, tuning half only)."
    for key in (
        "smooth_sigma_m",
        "tpi_radius_m",
        "tpi_ridge_m",
        "tpi_hollow_m",
        "ridge_relief_m",
        "texture_min_rank",
    ):
        value = best[key]
        if key == "tpi_hollow_m":
            value = -value  # stored as the signed threshold
        v = "null" if value is None else repr(float(value))
        new = f"  {key}: {{value: {v}, label: MODELED, note: '{note}'}}"
        text, n = re.subn(rf"^  {key}: \{{.*\}}$", new, text, flags=re.MULTILINE)
        if n != 1:
            raise RuntimeError(f"config/derive.yaml has no single ridges.{key} line")
    path.write_text(text, encoding="utf-8", newline="\n")


def ridge_tune(
    site: str, labels_path: Path, apply: bool = True, log=print, out_path: Path | None = None
) -> dict:
    root = repo_root()
    sample = json.loads(sample_path(root, site).read_text(encoding="utf-8"))
    pts = sample["points"]
    labels = rl.read_labels(labels_path, pts, sample["sample_id"])
    keep = [p for p in pts if p["id"] in labels]
    lab = np.array([labels[p["id"]] for p in keep], dtype=object)
    half = np.array([p["half"] for p in keep])
    strata = np.array([p["predicted"] for p in keep])
    cfg = load_derive_config()
    feats, relief, texture = point_features(root / "data" / "sites" / site, keep, cfg)
    best = rl.tune(lab, half, feats, relief, texture)
    test = (half == "test") & (lab != "unsure")
    shares = sample["stratum_share_of_site"]
    n_test = {c: int(np.sum(test & (strata == c))) for c in shares}
    w = np.array([shares[c] / (n_test[c] / test.sum()) if n_test[c] else 0.0 for c in strata])

    def evaluate(params):
        f = feats[(params["smooth_sigma_m"], params["tpi_radius_m"])]
        pred = rl.classify(f, relief, texture, params)
        return {
            "sample": rl.scores(lab[test], pred[test]),
            "site_wide_estimate": rl.scores(
                lab[test], pred[test], weights=w[test], strata=strata[test]
            ),
        }

    baseline = {
        "smooth_sigma_m": 0.0,
        "tpi_radius_m": 10.0,
        "tpi_ridge_m": float(sample["predicted_with"]["tpi_ridge_m"]),
        "tpi_hollow_m": -float(sample["predicted_with"]["tpi_hollow_m"]),
        "ridge_relief_m": float(sample["predicted_with"]["ridge_relief_m"]),
        "texture_min_rank": None,
    }
    result = {
        "site": site,
        "sample_id": sample["sample_id"],
        "labels_file": str(Path(labels_path).name),
        "label_counts": {k: int(np.sum(lab == k)) for k in rl.LABELS},
        "tuning_points": best["tuning_points"],
        "test_points": int(test.sum()),
        "tuned": best,
        "test": evaluate(best),
        "test_with_placeholder_thresholds": evaluate(baseline),
        "method": "Grid search on the tuning half (mean F1 of ridge and hollow); precision and "
        "recall on the test half. 'Site-wide estimate' weights each test point by its predicted "
        "class's share of the site over its share of the test half; intervals are bootstrap 95% "
        "(resampled within classes). 'Sample' is unweighted, with Wilson 95% intervals.",
        "pipeline_version": PIPELINE_VERSION,
        "computed_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    out = out_path or root / "docs" / "validation" / "ridge-map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    if apply:
        _apply_to_config(root, best, best["tuning_points"], sample["sample_id"])
    log(f"ridge map tuned on {best['tuning_points']} labels; test report: {out}")
    log(f"now run: ariadne derive --site {site} --from-stage walkability")
    return result
