# Written with AI assistance (Claude Code). See AI_USE.md.
"""Hand labels for the ridge map: the sample, the labeling page, tuning and the test.

The sample is drawn at random within each predicted class (ridge, hollow, other), and every
point is assigned to the tuning half or the test half when it is drawn, before any label exists.
Tuning looks only at the tuning half; precision and recall are reported on the test half.
Because the sample is stratified, site-wide estimates weight each point by its stratum's share
of the site divided by its share of the sample.
"""

from __future__ import annotations

import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np
from scipy import ndimage

from ariadne.derive.ridges import HOLLOW, OTHER, RIDGE

CLASS_CODES = {"ridge": RIDGE, "hollow": HOLLOW, "other": OTHER}
LABELS = ("ridge", "hollow", "neither", "unsure")
SMOOTH_SIGMAS_M = (0.0, 1.0, 2.0, 3.0)
TPI_RADII_M = (5.0, 10.0, 20.0)
TPI_THRESHOLDS_M = tuple(round(0.05 * k, 2) for k in range(1, 21))
RELIEF_FLOORS_M = (0.0, 0.4, 0.8, 1.2)
TEXTURE_FLOORS = (None, 0.25, 0.5, 0.75)
CHIP_M = 32.0
CONTEXT_M = 128.0
CHIP_PX = 256


# --- the sample ---


def stratified_sample(
    pred: np.ndarray,
    n_per_class: int,
    min_edge_px: int,
    min_spacing_px: float,
    seed: int,
    valid: np.ndarray | None = None,
    max_candidates: int = 20000,
) -> list[dict]:
    """`n_per_class` random cells in each predicted class, away from the edge and spaced apart.

    Classes take turns, one accepted point each, so no class gets first pick of the space.
    """
    h, w = pred.shape
    inside = np.zeros((h, w), dtype=bool)
    inside[min_edge_px : h - min_edge_px, min_edge_px : w - min_edge_px] = True
    if valid is not None:
        inside &= valid
    rng = np.random.default_rng(seed)
    queues = {}
    for name in ("ridge", "hollow", "other"):
        idx = np.flatnonzero(inside & (pred == CLASS_CODES[name]))
        take = min(idx.size, max_candidates)
        queues[name] = list(rng.choice(idx, size=take, replace=False)) if take else []
    chosen: list[dict] = []
    rc = np.empty((0, 2))
    counts = dict.fromkeys(queues, 0)
    while any(counts[c] < n_per_class and queues[c] for c in queues):
        for name in ("ridge", "hollow", "other"):
            q = queues[name]
            while counts[name] < n_per_class and q:
                r, c = divmod(int(q.pop(0)), w)
                if rc.size and np.min(np.hypot(rc[:, 0] - r, rc[:, 1] - c)) < min_spacing_px:
                    continue
                chosen.append({"row": r, "col": c, "predicted": name})
                rc = np.vstack([rc, [r, c]])
                counts[name] += 1
                break
    return chosen


def assign_halves(points: list[dict], seed: int) -> list[dict]:
    """Give each point a half (tune or test, balanced within each class) and an id in a random
    display order. Fixed by the seed, so the split exists before any label does."""
    rng = np.random.default_rng(seed)
    half = [None] * len(points)
    for name in ("ridge", "hollow", "other"):
        idx = [i for i, p in enumerate(points) if p["predicted"] == name]
        idx = [idx[k] for k in rng.permutation(len(idx))]
        for k, i in enumerate(idx):
            half[i] = "tune" if k < len(idx) // 2 else "test"
    order = rng.permutation(len(points))
    out = []
    for n, i in enumerate(order, start=1):
        p = dict(points[i])
        p.update(id=f"P{n:03d}", half=half[i])
        out.append(p)
    return out


# --- chips and the page ---


def write_png(path: Path, img: np.ndarray) -> None:
    """Write an 8-bit grayscale (H x W) or RGB (H x W x 3) PNG with zlib, no imaging library."""
    a = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
    color = 0 if a.ndim == 2 else 2
    h, w = a.shape[:2]
    rows = a.reshape(h, -1)
    raw = b"".join(b"\x00" + rows[i].tobytes() for i in range(h))

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, color, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def _stretch(a: np.ndarray) -> np.ndarray:
    v = a[a > 0]
    if v.size == 0:
        return np.zeros(a.shape, dtype=np.uint8)
    lo, hi = np.percentile(v, [2, 98])
    hi = max(hi, lo + 1.0)
    return (np.clip((a - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def hillshade(z: np.ndarray, res: float, azimuth=315.0, altitude=45.0) -> np.ndarray:
    gy, gx = np.gradient(np.asarray(z, dtype=np.float64), res)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)  # rows grow southward
    az, alt = math.radians(360.0 - azimuth + 90.0), math.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return (np.clip(shade, 0, 1) * 255).astype(np.uint8)


def _mark(gray: np.ndarray, radius_px: float, box_px: float | None = None) -> np.ndarray:
    """RGB copy of a chip with a cyan ring (dark outline) at its centre, and an optional box."""
    rgb = np.repeat(gray[:, :, None], 3, axis=2)
    h, w = gray.shape
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(yy - (h - 1) / 2, xx - (w - 1) / 2)
    edge = np.abs(d - radius_px)
    rgb[(edge >= 1.0) & (edge < 2.2)] = (0, 0, 0)
    rgb[edge < 1.0] = (0, 225, 255)
    if box_px is not None:
        c0, c1 = (w - box_px) / 2, (w + box_px) / 2
        ring = (
            (
                (np.abs(xx - c0) < 1)
                | (np.abs(xx - c1) < 1)
                | (np.abs(yy - c0) < 1)
                | (np.abs(yy - c1) < 1)
            )
            & (xx >= c0 - 1)
            & (xx <= c1 + 1)
            & (yy >= c0 - 1)
            & (yy <= c1 + 1)
        )
        rgb[ring] = (0, 225, 255)
    return rgb


def chips(ortho, ortho_t, dem, dem_t, x: float, y: float) -> dict[str, np.ndarray]:
    """Image, hillshade and context chips (RGB, CHIP_PX square, north up) centred on (x, y)."""

    def window(arr, t, half_m):
        c = (x - t.c) / t.a
        r = (y - t.f) / t.e
        n = int(round(half_m / abs(t.a)))
        r0, c0 = int(round(r)) - n, int(round(c)) - n
        out = np.zeros((2 * n, 2 * n), dtype=np.float64)
        rs, cs = max(r0, 0), max(c0, 0)
        re_, ce = min(r0 + 2 * n, arr.shape[0]), min(c0 + 2 * n, arr.shape[1])
        if re_ > rs and ce > cs:
            out[rs - r0 : re_ - r0, cs - c0 : ce - c0] = arr[rs:re_, cs:ce]
        return out

    img = _stretch(window(ortho, ortho_t, CHIP_M / 2))
    img = ndimage.zoom(img, CHIP_PX / img.shape[0], order=0)
    z = window(dem, dem_t, CHIP_M / 2 + 1)
    hs = hillshade(z, abs(dem_t.a))[1:-1, 1:-1]
    hs = np.clip(ndimage.zoom(hs.astype(np.float64), CHIP_PX / hs.shape[0], order=1), 0, 255)
    ctx = window(ortho, ortho_t, CONTEXT_M / 2)
    k = max(1, ctx.shape[0] // CHIP_PX)
    ctx = ctx[: (ctx.shape[0] // k) * k, : (ctx.shape[1] // k) * k]
    ctx = ctx.reshape(ctx.shape[0] // k, k, ctx.shape[1] // k, k).mean(axis=(1, 3))
    ctx = _stretch(ctx)
    px_per_m = CHIP_PX / CHIP_M
    return {
        "image": _mark(img.astype(np.uint8), 2.0 * px_per_m),
        "hillshade": _mark(hs.astype(np.uint8), 2.0 * px_per_m),
        "context": _mark(ctx, 2.0 * CHIP_PX / CONTEXT_M, CHIP_PX * CHIP_M / CONTEXT_M),
    }


PAGE = """<!doctype html>
<!-- Written with AI assistance (Claude Code). See AI_USE.md. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ridge labels</title>
<style>
:root { --bg: #111418; --fg: #f2f4f7; --muted: #b7c0cc; --accent: #5fd4ff; --panel: #1c2128; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 900px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.4rem; margin: 0 0 8px; }
p, li { color: var(--muted); }
.chips { display: flex; flex-wrap: wrap; gap: 12px; margin: 12px 0; }
figure { margin: 0; background: var(--panel); padding: 8px; border-radius: 6px; }
figure img { display: block; width: 256px; height: 256px; image-rendering: pixelated; }
figcaption { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
button { font: inherit; padding: 10px 16px; border-radius: 6px; border: 2px solid var(--fg);
  background: var(--panel); color: var(--fg); cursor: pointer; min-width: 120px; }
button[aria-pressed="true"] { background: var(--accent); color: #000; border-color: var(--accent); }
button:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
.status { font-weight: 600; }
kbd { border: 1px solid var(--muted); border-radius: 3px; padding: 0 4px; }
</style>
</head>
<body>
<main>
<h1>Ridge labels: __SITE__</h1>
<p>For the point inside the cyan ring, choose what the ground there is. North is up. The first two
pictures are 32 m across (25 cm image, then shaded relief from the 1 m elevation model); the third
is 128 m across, with a box showing the first two.</p>
<ul>
<li><strong>Ridge</strong>: on or along a raised boxwork wall (its crest or upper flank).</li>
<li><strong>Hollow</strong>: in a low area between walls.</li>
<li><strong>Neither</strong>: ground that is neither, such as flat plains, sand or broad slopes.</li>
<li><strong>Unsure</strong>: you cannot tell. Unsure points are left out of tuning and testing.</li>
</ul>
<p>Keys: <kbd>1</kbd> Ridge, <kbd>2</kbd> Hollow, <kbd>3</kbd> Neither, <kbd>4</kbd> Unsure,
<kbd>&larr;</kbd> and <kbd>&rarr;</kbd> to move. Labels are kept in this browser until you download
them.</p>
<p class="status" id="status" role="status" aria-live="polite"></p>
<div class="chips">
<figure><img id="c-image" alt=""><figcaption>Image, 32 m</figcaption></figure>
<figure><img id="c-hillshade" alt=""><figcaption>Shaded relief, 32 m</figcaption></figure>
<figure><img id="c-context" alt=""><figcaption>Context, 128 m</figcaption></figure>
</div>
<div class="buttons" role="group" aria-label="Label">
<button data-label="ridge">1 Ridge</button>
<button data-label="hollow">2 Hollow</button>
<button data-label="neither">3 Neither</button>
<button data-label="unsure">4 Unsure</button>
</div>
<div class="buttons">
<button id="prev">&larr; Previous</button>
<button id="next">Next &rarr;</button>
<button id="next-open">Next unlabeled</button>
<button id="download">Download labels</button>
<label>Load labels <input type="file" id="load" accept="application/json"></label>
</div>
</main>
<script>
const SITE = "__SITE__", SAMPLE = "__SAMPLE__";
const POINTS = __POINTS__;
const KEY = "ariadne-ridge-labels-" + SAMPLE;
let labels = {};
try { labels = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { labels = {}; }
let i = 0;
function save() { try { localStorage.setItem(KEY, JSON.stringify(labels)); } catch (e) {} }
function show() {
  const p = POINTS[i];
  for (const k of ["image", "hillshade", "context"]) {
    const el = document.getElementById("c-" + k);
    el.src = "chips/" + p.id + "_" + k + ".png";
    el.alt = k + " chip for point " + p.id;
  }
  document.querySelectorAll("button[data-label]").forEach(b =>
    b.setAttribute("aria-pressed", String(labels[p.id] === b.dataset.label)));
  const done = POINTS.filter(q => labels[q.id]).length;
  document.getElementById("status").textContent =
    "Point " + p.id + " (" + (i + 1) + " of " + POINTS.length + "). Labeled: " + done +
    ". This point: " + (labels[p.id] || "not labeled yet") + ".";
}
function setLabel(l) { labels[POINTS[i].id] = l; save(); if (i < POINTS.length - 1) i++; show(); }
document.querySelectorAll("button[data-label]").forEach(b =>
  b.addEventListener("click", () => setLabel(b.dataset.label)));
document.getElementById("prev").onclick = () => { if (i > 0) i--; show(); };
document.getElementById("next").onclick = () => { if (i < POINTS.length - 1) i++; show(); };
document.getElementById("next-open").onclick = () => {
  const k = POINTS.findIndex(q => !labels[q.id]); if (k >= 0) i = k; show(); };
document.getElementById("download").onclick = () => {
  const out = { site: SITE, sample: SAMPLE, labeled_utc: new Date().toISOString(), labels };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: "application/json" }));
  a.download = SITE + "_ridge_labels.json"; a.click();
};
document.getElementById("load").onchange = ev => {
  const f = ev.target.files[0]; if (!f) return;
  f.text().then(t => { const d = JSON.parse(t);
    if (d.sample !== SAMPLE) { alert("That file is for a different sample."); return; }
    labels = Object.assign(labels, d.labels); save(); show(); });
};
document.addEventListener("keydown", ev => {
  if (ev.target.tagName === "INPUT") return;
  const m = { "1": "ridge", "2": "hollow", "3": "neither", "4": "unsure" };
  if (m[ev.key]) setLabel(m[ev.key]);
  else if (ev.key === "ArrowLeft") document.getElementById("prev").click();
  else if (ev.key === "ArrowRight") document.getElementById("next").click();
});
show();
</script>
</body>
</html>
"""


def page_html(site: str, points: list[dict], sample_id: str) -> str:
    """The labeling page. It carries only each point's id, never its predicted class or half."""
    public = [{"id": p["id"]} for p in sorted(points, key=lambda p: p["id"])]
    return (
        PAGE.replace("__SITE__", site)
        .replace("__SAMPLE__", sample_id)
        .replace("__POINTS__", json.dumps(public))
    )


def read_labels(path: Path, points: list[dict], sample_id: str) -> dict[str, str]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("sample") != sample_id:
        raise ValueError(f"labels are for sample {d.get('sample')!r}, not {sample_id!r}")
    ids = {p["id"] for p in points}
    return {k: v for k, v in d["labels"].items() if k in ids and v in LABELS}


# --- tuning and scoring ---


def classify(tpi, relief, texture, p: dict) -> np.ndarray:
    tpi, relief = np.asarray(tpi, dtype=np.float64), np.asarray(relief, dtype=np.float64)
    out = np.full(tpi.shape, "neither", dtype=object)
    ridge = (tpi > p["tpi_ridge_m"]) & (relief >= p["ridge_relief_m"])
    if p.get("texture_min_rank") is not None:
        ridge &= np.asarray(texture, dtype=np.float64) >= p["texture_min_rank"]
    out[ridge] = "ridge"
    out[tpi < -p["tpi_hollow_m"]] = "hollow"
    return out


def _f1(truth, pred, cls) -> float:
    tp = np.sum((pred == cls) & (truth == cls))
    fp = np.sum((pred == cls) & (truth != cls))
    fn = np.sum((pred != cls) & (truth == cls))
    return 2 * tp / (2 * tp + fp + fn) if tp else 0.0


def tune(labels, half, feats: dict, relief, texture) -> dict:
    """Grid search on the tuning half only: the mean F1 of ridge and hollow.

    Ridge and hollow predictions never overlap (TPI above +t or below -t), so each class's F1
    depends only on its own parameters and the two are maximised separately. Ties keep the
    first setting in the search order (least smoothing, then the listed radii and thresholds).
    """
    labels, half = np.asarray(labels, dtype=object), np.asarray(half)
    use = (half == "tune") & (labels != "unsure")
    truth = labels[use]
    rel, tex = np.asarray(relief)[use], np.asarray(texture)[use]
    best = None
    for s in SMOOTH_SIGMAS_M:
        for r in TPI_RADII_M:
            tpi = np.asarray(feats[(s, r)])[use]
            br = (-1.0, None)
            for tr in TPI_THRESHOLDS_M:
                for rf in RELIEF_FLOORS_M:
                    for tf in TEXTURE_FLOORS:
                        ridge = (tpi > tr) & (rel >= rf)
                        if tf is not None:
                            ridge &= tex >= tf
                        pred = np.where(ridge, "ridge", "neither")
                        f = _f1(truth, pred, "ridge")
                        if f > br[0]:
                            br = (f, (tr, rf, tf))
            bh = (-1.0, None)
            for th in TPI_THRESHOLDS_M:
                pred = np.where(tpi < -th, "hollow", "neither")
                f = _f1(truth, pred, "hollow")
                if f > bh[0]:
                    bh = (f, th)
            score = (br[0] + bh[0]) / 2
            if best is None or score > best["objective"] + 1e-12:
                best = {
                    "smooth_sigma_m": s,
                    "tpi_radius_m": r,
                    "tpi_ridge_m": br[1][0],
                    "ridge_relief_m": br[1][1],
                    "texture_min_rank": br[1][2],
                    "tpi_hollow_m": bh[1],
                    "objective": round(float(score), 4),
                    "f1_ridge": round(float(br[0]), 4),
                    "f1_hollow": round(float(bh[0]), 4),
                }
    best["tuning_points"] = int(use.sum())
    return best


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (centre - half, centre + half)


def _pr(truth, pred, w, cls):
    tp = np.sum(w * ((pred == cls) & (truth == cls)))
    pp = np.sum(w * (pred == cls))
    ap = np.sum(w * (truth == cls))
    return (tp / pp if pp else float("nan"), tp / ap if ap else float("nan"))


def scores(truth, pred, weights=None, n_boot: int = 2000, seed: int = 0, strata=None) -> dict:
    """Precision and recall for ridge and hollow. Unweighted: Wilson 95% intervals. Weighted
    (site-wide estimate from a stratified sample): bootstrap 95% intervals, resampling within
    strata."""
    truth, pred = np.asarray(truth, dtype=object), np.asarray(pred, dtype=object)
    w = np.ones(truth.size) if weights is None else np.asarray(weights, dtype=np.float64)
    out = {"points": int(truth.size)}
    for cls in ("ridge", "hollow"):
        prec, rec = _pr(truth, pred, w, cls)
        m = {"precision": float(prec), "recall": float(rec)}
        if weights is None:
            tp = int(np.sum((pred == cls) & (truth == cls)))
            m["precision_ci95"] = list(wilson(tp, int(np.sum(pred == cls))))
            m["recall_ci95"] = list(wilson(tp, int(np.sum(truth == cls))))
        elif n_boot:
            rng = np.random.default_rng(seed)
            groups = (
                [np.flatnonzero(np.asarray(strata) == g) for g in np.unique(strata)]
                if strata is not None
                else [np.arange(truth.size)]
            )
            ps, rs = [], []
            for _ in range(n_boot):
                idx = np.concatenate([rng.choice(g, size=g.size, replace=True) for g in groups])
                p_, r_ = _pr(truth[idx], pred[idx], w[idx], cls)
                ps.append(p_)
                rs.append(r_)
            m["precision_ci95"] = [float(x) for x in np.nanpercentile(ps, [2.5, 97.5])]
            m["recall_ci95"] = [float(x) for x in np.nanpercentile(rs, [2.5, 97.5])]
        out[cls] = {
            k: (round(v, 4) if isinstance(v, float) else [round(x, 4) for x in v])
            for k, v in m.items()
        }
    return out
