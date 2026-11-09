# Written with AI assistance (Claude Code). See AI_USE.md.
"""Windowed crops of large remote GeoTIFFs, written as Cloud Optimized GeoTIFFs.

Two readers:
- GDAL band reads: the window is split into row bands read in parallel threads, each with its
  own dataset handle. Works for any GeoTIFF (used for the LZW DEM and the color COG).
- Range requests: for uncompressed single-band files stored one row per strip (the 25 cm
  orthophoto), each needed row segment is fetched with one HTTP range request. GDAL reads the
  whole 180 KB strip per row there; this reads only the bytes inside the window, which
  benchmarked about 7 times faster with byte-identical output (docs/PROGRESS.md).
"""

from __future__ import annotations

import http.client
import math
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import rasterio
import rasterio.shutil
from affine import Affine
from rasterio.io import MemoryFile
from rasterio.windows import Window

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "2",
}
USER_AGENT = "ARIADNE-pipeline (+https://github.com/vyom-aggarwal/ARIADNE)"

RangeReader = Callable[[int, int], bytes]


@dataclass
class Crop:
    data: np.ndarray  # (rows, cols) or (bands, rows, cols)
    transform: Affine
    crs: rasterio.crs.CRS
    nodata: float | None
    bounds: tuple[float, float, float, float]
    window: Window  # in the source's pixel grid
    method: str


def gdal_path(url_or_path: str) -> str:
    return (
        "/vsicurl/" + url_or_path
        if url_or_path.startswith(("http://", "https://"))
        else url_or_path
    )


def snap_bounds(bounds, transform: Affine) -> tuple[tuple[float, float, float, float], Window]:
    """Grow (left, bottom, right, top) outward to the pixel edges of a north-up grid."""
    left, bottom, right, top = bounds
    if transform.b != 0 or transform.d != 0 or transform.e >= 0:
        raise ValueError("only north-up grids are supported")
    eps = 1e-6  # tolerate float noise on requests that already sit on an edge
    col0 = math.floor((left - transform.c) / transform.a + eps)
    col1 = math.ceil((right - transform.c) / transform.a - eps)
    row0 = math.floor((top - transform.f) / transform.e + eps)
    row1 = math.ceil((bottom - transform.f) / transform.e - eps)
    win = Window(col0, row0, col1 - col0, row1 - row0)
    snapped = (
        transform.c + col0 * transform.a,
        transform.f + row1 * transform.e,
        transform.c + col1 * transform.a,
        transform.f + row0 * transform.e,
    )
    return snapped, win


def is_uncompressed_strip_tiff(url_or_path: str) -> bool:
    with rasterio.Env(**GDAL_ENV), rasterio.open(gdal_path(url_or_path)) as ds:
        return (
            ds.driver == "GTiff"
            and ds.count == 1
            and ds.compression is None
            and ds.block_shapes[0] == (1, ds.width)
        )


def resolve_redirects(url: str, max_hops: int = 5) -> str:
    """Follow HTTP redirects with HEAD requests and return the final URL."""
    for _ in range(max_hops):
        parts = urlsplit(url)
        conn_cls = (
            http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        )
        conn = conn_cls(parts.netloc, timeout=60)
        try:
            conn.request("HEAD", parts.path, headers={"User-Agent": USER_AGENT})
            resp = conn.getresponse()
            resp.read()
            if resp.status in (301, 302, 303, 307, 308) and resp.getheader("Location"):
                url = resp.getheader("Location")
                continue
            return url
        finally:
            conn.close()
    raise OSError(f"too many redirects from {url}")


def _http_range_reader(url: str) -> RangeReader:
    parts = urlsplit(resolve_redirects(url))
    local = threading.local()

    def read(start: int, length: int) -> bytes:
        for attempt in range(6):
            try:
                conn = getattr(local, "conn", None)
                if conn is None:
                    conn = http.client.HTTPSConnection(parts.netloc, timeout=60)
                    local.conn = conn
                headers = {"Range": f"bytes={start}-{start + length - 1}", "User-Agent": USER_AGENT}
                conn.request("GET", parts.path, headers=headers)
                resp = conn.getresponse()
                body = resp.read()
                if resp.status == 206 and len(body) == length:
                    return body
                raise OSError(f"HTTP {resp.status}, {len(body)} of {length} bytes")
            except (OSError, http.client.HTTPException):
                local.conn = None
                time.sleep(min(30.0, 0.5 * 2**attempt))
        raise OSError(f"range request failed after retries: bytes {start}+{length}")

    return read


def _check_inside(win: Window, ds) -> None:
    if (
        win.col_off < 0
        or win.row_off < 0
        or win.col_off + win.width > ds.width
        or (win.row_off + win.height > ds.height)
    ):
        raise ValueError(f"requested window {win} is outside the source ({ds.width} x {ds.height})")


def _read_band_rows(path: str, win: Window, indexes) -> np.ndarray:
    with rasterio.Env(**GDAL_ENV), rasterio.open(path) as ds:
        return ds.read(indexes, window=win)


def read_crop(
    url_or_path: str,
    bounds,
    workers: int = 16,
    range_reader: RangeReader | None = None,
    use_ranges: bool | None = None,
) -> Crop:
    """Read the source pixels covering `bounds` (snapped outward to the source grid)."""
    path = gdal_path(url_or_path)
    with rasterio.Env(**GDAL_ENV), rasterio.open(path) as ds:
        snapped, win = snap_bounds(bounds, ds.transform)
        _check_inside(win, ds)
        transform = ds.window_transform(win)
        crs, nodata, count, dtype = ds.crs, ds.nodata, ds.count, ds.dtypes[0]
        if use_ranges is None:
            use_ranges = (
                count == 1 and ds.compression is None and ds.block_shapes[0] == (1, ds.width)
            )
        offsets = None
        if use_ranges:
            offsets = [
                int(ds.get_tag_item(f"BLOCK_OFFSET_0_{r}", "TIFF", bidx=1))
                for r in range(win.row_off, win.row_off + win.height)
            ]
    rows, cols = int(win.height), int(win.width)

    if use_ranges:
        reader = range_reader or _http_range_reader(url_or_path)
        itemsize = np.dtype(dtype).itemsize
        start_col = int(win.col_off) * itemsize
        with ThreadPoolExecutor(max(1, workers)) as ex:
            parts = list(ex.map(lambda o: reader(o + start_col, cols * itemsize), offsets))
        data = np.frombuffer(b"".join(parts), dtype=dtype).reshape(rows, cols).copy()
        method = "range-requests"
    else:
        indexes = 1 if count == 1 else list(range(1, count + 1))
        step = max(1, math.ceil(rows / max(1, workers)))
        bands = [
            Window(win.col_off, win.row_off + r, cols, min(step, rows - r))
            for r in range(0, rows, step)
        ]
        with ThreadPoolExecutor(max(1, min(workers, len(bands)))) as ex:
            parts = list(ex.map(lambda w: _read_band_rows(path, w, indexes), bands))
        data = np.concatenate(parts, axis=-2)
        method = "gdal-bands"
    return Crop(data, transform, crs, nodata, snapped, win, method)


def write_cog(
    path: Path, crop: Crop, tags: dict[str, str] | None = None, compress: str | None = None
) -> Path:
    """Write a crop as a Cloud Optimized GeoTIFF (pixel-corner georeferencing, explicit nodata)."""
    data = crop.data if crop.data.ndim == 3 else crop.data[np.newaxis, ...]
    count, height, width = data.shape
    dtype = data.dtype
    if compress is None:
        compress = "JPEG" if (count == 3 and dtype == np.uint8) else "DEFLATE"
    profile = dict(
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype=dtype,
        crs=crop.crs,
        transform=crop.transform,
        nodata=crop.nodata,
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with MemoryFile() as mem:
        with mem.open(**profile) as tmp:
            tmp.write(data)
            tmp.update_tags(AREA_OR_POINT="Area", **(tags or {}))
        with mem.open() as tmp:
            opts = dict(
                driver="COG", compress=compress, blocksize=512, overviews="AUTO", bigtiff="IF_SAFER"
            )
            if compress == "DEFLATE":
                opts["predictor"] = 3 if np.issubdtype(dtype, np.floating) else 2
            if compress == "JPEG":
                opts["quality"] = 90
            rasterio.shutil.copy(tmp, path, **opts)
    return path
