# Written with AI assistance (Claude Code). See AI_USE.md.
"""Windowed crops (acceptance test B5), on synthetic GeoTIFFs laid out like the USGS mosaics."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

from ariadne.fetch import raster

# A grid whose origin is not on whole meters, like the USGS DEM (x0 = 8,127,993.49).
X0, Y0 = 1000.49, 5000.0


def strip_tiff(path, dtype="uint8", compress=None, res=0.25, shape=(400, 300), nodata=0):
    rng = np.random.default_rng(1)
    if dtype == "uint8":
        data = rng.integers(1, 255, size=shape, dtype="uint8")
    else:
        data = rng.normal(-3600, 20, size=shape).astype(dtype)
    prof = dict(
        driver="GTiff",
        width=shape[1],
        height=shape[0],
        count=1,
        dtype=dtype,
        transform=from_origin(X0, Y0, res, res),
        nodata=nodata,
        blockysize=1,
        tiled=False,
    )
    if compress:
        prof["compress"] = compress
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(data, 1)
    return data


def test_snap_bounds_goes_outward_onto_the_grid():
    t = from_origin(X0, Y0, 1.0, 1.0)
    req = (X0 + 10.3, Y0 - 50.7, X0 + 20.2, Y0 - 40.1)
    (left, bottom, right, top), win = raster.snap_bounds(req, t)
    assert left <= req[0] and bottom <= req[1] and right >= req[2] and top >= req[3]
    for edge in (left - X0, right - X0, Y0 - top, Y0 - bottom):
        assert edge == pytest.approx(round(edge), abs=1e-9)
    assert (win.col_off, win.row_off, win.width, win.height) == (10, 40, 11, 11)


def test_snap_bounds_keeps_an_exact_request():
    t = from_origin(X0, Y0, 0.25, 0.25)
    req = (X0 + 1.0, Y0 - 2.0, X0 + 3.0, Y0 - 1.0)
    snapped, win = raster.snap_bounds(req, t)
    assert snapped == pytest.approx(req)
    assert (win.width, win.height) == (8, 4)


@pytest.mark.parametrize("workers", [1, 4])
def test_parallel_gdal_bands_equal_a_direct_read(tmp_path, workers):
    path = tmp_path / "dem.tif"
    strip_tiff(path, dtype="float32", compress="lzw", res=1.0, nodata=-32767)
    req = (X0 + 20.2, Y0 - 300.7, X0 + 250.0, Y0 - 33.3)
    crop = raster.read_crop(str(path), req, workers=workers)
    with rasterio.open(path) as src:
        _, win = raster.snap_bounds(req, src.transform)
        direct = src.read(1, window=win)
        assert crop.transform == src.window_transform(win)
    np.testing.assert_array_equal(crop.data, direct)
    assert crop.nodata == -32767


def test_uncompressed_strip_reader_equals_a_direct_read(tmp_path):
    path = tmp_path / "ortho.tif"
    strip_tiff(path)
    req = (X0 + 3.1, Y0 - 90.0, X0 + 60.0, Y0 - 7.7)

    def local_range(start, length):
        with open(path, "rb") as f:
            f.seek(start)
            return f.read(length)

    assert raster.is_uncompressed_strip_tiff(str(path))
    crop = raster.read_crop(str(path), req, workers=8, range_reader=local_range)
    with rasterio.open(path) as src:
        _, win = raster.snap_bounds(req, src.transform)
        np.testing.assert_array_equal(crop.data, src.read(1, window=win))
    assert crop.method == "range-requests"


def test_compressed_files_are_not_sent_to_the_strip_reader(tmp_path):
    path = tmp_path / "dem.tif"
    strip_tiff(path, dtype="float32", compress="lzw", res=1.0, nodata=-32767)
    assert not raster.is_uncompressed_strip_tiff(str(path))


def test_request_outside_the_source_is_an_error(tmp_path):
    path = tmp_path / "dem.tif"
    strip_tiff(path, dtype="float32", res=1.0, nodata=-32767)
    with pytest.raises(ValueError, match="outside"):
        raster.read_crop(str(path), (X0 - 500, Y0 - 10, X0 + 5, Y0), workers=1)


def test_write_cog_keeps_georeferencing_nodata_and_tags(tmp_path):
    src_path = tmp_path / "dem.tif"
    strip_tiff(src_path, dtype="float32", compress="lzw", res=1.0, nodata=-32767)
    crop = raster.read_crop(str(src_path), (X0 + 10, Y0 - 300, X0 + 290, Y0 - 10), workers=2)
    out = tmp_path / "crop.tif"
    raster.write_cog(out, crop, tags={"ARIADNE_TEST": "1"})
    with rasterio.open(out) as dst:
        assert dst.transform == crop.transform
        assert dst.nodata == -32767
        assert dst.tags()["ARIADNE_TEST"] == "1"
        assert dst.profile.get("tiled") is True
        np.testing.assert_array_equal(dst.read(1), crop.data)
        win = from_bounds(*dst.bounds, transform=dst.transform)
        assert int(round(win.width)) == crop.data.shape[1]
