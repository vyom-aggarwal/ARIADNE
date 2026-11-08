# Written with AI assistance (Claude Code). See AI_USE.md.
"""Provenance records (acceptance test B4)."""

import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ariadne import PIPELINE_VERSION
from ariadne.labels import Label
from ariadne.provenance import REQUIRED_FIELDS, Provenance, read_provenance, write_provenance


def make(**over):
    base = dict(
        source_id="usgs-gale-dem-1m",
        url="https://example.org/dem.tif",
        product_id="MSL_Gale_DEM_Mosaic_1m_v3",
        resolution_m=1.0,
        acquisition_date=None,
        label=Label.MEASURED,
        notes="mosaic of many images",
    )
    base.update(over)
    return Provenance.new(**base)


def test_required_fields_match_prompt_section_3():
    assert set(REQUIRED_FIELDS) == {
        "source_id",
        "url",
        "product_id",
        "resolution_m",
        "acquisition_date",
        "processing_date",
        "pipeline_version",
        "label",
    }


def test_new_record_fills_processing_date_and_pipeline_version():
    p = make()
    assert p.pipeline_version == PIPELINE_VERSION
    assert p.processing_date.endswith("Z")
    d = p.to_dict()
    for f in REQUIRED_FIELDS:
        assert f in d


def test_labels_are_the_four_project_labels():
    assert {lab.value for lab in Label} == {"MEASURED", "DERIVED", "MODELED", "PLACEHOLDER"}


def test_invalid_label_is_rejected():
    with pytest.raises(ValueError):
        make(label="GUESSED")


def test_missing_acquisition_date_needs_a_note():
    with pytest.raises(ValueError):
        make(acquisition_date=None, notes="")


def test_sidecar_round_trip(tmp_path):
    target = tmp_path / "dem.tif"
    target.write_bytes(b"")
    p = make(extra={"window": [1, 2, 3, 4]})
    write_provenance(target, p)
    sidecar = tmp_path / "dem.tif.prov.json"
    assert json.loads(sidecar.read_text(encoding="utf-8"))["label"] == "MEASURED"
    assert read_provenance(target) == p


def test_geotiff_tag_round_trip(tmp_path):
    path = tmp_path / "x.tif"
    prof = dict(
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        transform=from_origin(0, 2, 1, 1),
    )
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(np.zeros((2, 2), "float32"), 1)
    p = make()
    write_provenance(path, p, embed=True)
    with rasterio.open(path) as src:
        tagged = json.loads(src.tags()["ARIADNE_PROVENANCE"])
    assert tagged["source_id"] == "usgs-gale-dem-1m"
    assert read_provenance(path) == p
