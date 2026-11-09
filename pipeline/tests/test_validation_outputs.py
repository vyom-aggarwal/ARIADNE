# Written with AI assistance (Claude Code). See AI_USE.md.
"""Committed Phase 2 outputs (acceptance tests C13 to C15).

validation.json and docs/derived/<site>.md are committed, so they are checked in CI. The derived
rasters live in data/ (not committed); their provenance check skips when data/ is empty.
"""

import json

import pytest

from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.provenance import read_provenance, sidecar_path

ROOT = repo_root()
SITES = ["boxwork", "murray-buttes"]


@pytest.fixture(scope="module")
def validation():
    return json.loads((ROOT / "validation.json").read_text(encoding="utf-8"))


def test_validation_holds_the_shielding_calibration(validation):
    checks = {c["id"]: c for c in validation["checks"]}
    cal = checks["shielding-murray-buttes"]
    assert cal["label"] == "calibrated on one RAD measurement"
    assert cal["status"] in {"pass", "fail"}
    r = cal["result"]
    for key in ("n", "n_range_for_uncertainty", "n_for_headline_ratio", "ratio_at_n", "passed"):
        assert key in r
    if r["passed"]:
        lo, hi = r["n_range_for_uncertainty"]
        assert lo <= r["n"] <= hi
        assert r["ratio_at_n"] == pytest.approx(cal["reference"]["target_ratio"], abs=5e-4)
    ref = cal["reference"]
    assert ref["baseline_sols"] == [[1440, 1455], [1468, 1480]]
    assert "Ehresmann" in ref["source"]
    sky = cal["sky_check"]
    assert sky["blocked_fraction_paper"] == 0.19 and 0 <= sky["blocked_fraction_model"] <= 1
    assert {s["case"].split(" ")[0] for s in cal["sensitivity"]} >= {"observer", "near-field"}
    assert len(cal["baseline_positions"]) == (1455 - 1440 + 1) + (1480 - 1468 + 1)


def test_validation_lists_every_section_7_check(validation):
    ids = {c["id"] for c in validation["checks"]}
    assert {
        "shielding-murray-buttes",
        "rover-walkability",
        "mars24",
        "sols",
        "ridge-map",
        "walker-model",
        "ground-temperature",
        "light-time",
        "station-solver",
        "labels",
    } <= ids
    for c in validation["checks"]:
        assert c["status"] in {"pass", "fail", "reported", "not run"}
        if c["status"] == "not run":
            assert c["reason"]


@pytest.mark.parametrize("site", SITES)
def test_derived_report_exists_with_the_far_field_sun_table(site):
    text = (ROOT / "docs" / "derived" / f"{site}.md").read_text(encoding="utf-8")
    assert "How far-field horizons shift sunrise and sunset" in text
    assert "Far field delays sunrise" in text
    assert "Ls 90" in text and "Ls 270" in text


DERIVED = [
    "slope.tif",
    "aspect.tif",
    "roughness.tif",
    "tpi10.tif",
    "horizons.tif",
    "shielding.tif",
    "sky_blocked.tif",
    "sunrise_ltst.tif",
    "sunset_ltst.tif",
    "insolation.tif",
    "walk_class_walker.tif",
    "walk_cost_walker.tif",
    "walk_class_rover.tif",
    "sand_proxy.tif",
    "ridges.tif",
    "fractures.geojson",
    "shelters.tif",
    "minutes_to_shelter.tif",
    "viewshed_staging.tif",
    "confidence.tif",
]


@pytest.mark.parametrize("site", SITES)
def test_every_derived_product_has_provenance(site):
    out = ROOT / "data" / "sites" / site / "derived"
    if not (out / "summary.json").exists():
        pytest.skip("no local derive run (data/ is not committed)")
    names = DERIVED + (["transects.geojson"] if site == "boxwork" else [])
    for name in names:
        path = out / name
        assert path.exists(), name
        assert sidecar_path(path).exists(), name
        prov = read_provenance(path)
        assert prov.label in set(Label)
        assert prov.pipeline_version


# --- C21: the rover re-run keeps the first result, adds the held-out site and the seams ---


def test_rover_check_keeps_the_frozen_first_result_beside_the_new_one(validation):
    checks = {c["id"]: c for c in validation["checks"]}
    rov = checks["rover-walkability"]
    frozen = json.loads(
        (ROOT / "docs" / "validation" / "rover-walkability-first-run.json").read_text(
            encoding="utf-8"
        )
    )["check"]
    first = rov["first_run"]
    assert first["status"] == frozen["status"] == "fail"
    assert first["result"]["go_or_caution"] == frozen["result"]["go_or_caution"] == 0.7971
    assert first["result"]["share"] == frozen["result"]["share"]
    assert "footprint" in rov["method"]
    assert rov["status"] in {"pass", "fail"}
    assert rov["status"] == ("pass" if rov["result"]["go_or_caution"] >= 0.95 else "fail")
    # the first-run method, recomputed from today's layers, reproduces the frozen numbers
    assert rov["first_run_reproduced"]["go_or_caution"] == pytest.approx(0.7971, abs=1e-4)
    assert set(rov["sensitivity"]) >= {"coarse_resolution"}
    for block in (rov["result"], rov["first_run_reproduced"]):
        s = block["seams"]
        assert s["points"] == rov["result"]["points"]
        assert 0.0 <= s["share_of_points_in_zone"] <= 1.0 and "fisher_p" in s


def test_rover_check_has_the_murray_buttes_held_out_result(validation):
    checks = {c["id"]: c for c in validation["checks"]}
    held = checks["rover-walkability-held-out"]
    assert held["site"] == "murray-buttes"
    assert held["status"] in {"pass", "fail"}
    assert held["status"] == ("pass" if held["result"]["go_or_caution"] >= 0.95 else "fail")
    assert held["result"]["points"] > 100
    assert "seams" in held["result"] and "comparison_horn_1m" in held
