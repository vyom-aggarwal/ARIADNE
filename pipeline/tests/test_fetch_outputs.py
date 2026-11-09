# Written with AI assistance (Claude Code). See AI_USE.md.
"""Fetched products carry provenance and are logged (acceptance test B10).

Runs against data/sites/<site>/ when a fetch has been run on this machine; skipped otherwise
(CI has no raw data). The committed reports in docs/coverage/ are checked either way.
"""

import json

import pytest

from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.provenance import REQUIRED_FIELDS, read_provenance, sidecar_path

ROOT = repo_root()
SITES = ["boxwork", "murray-buttes"]


@pytest.mark.parametrize("site", SITES)
def test_coverage_report_is_committed(site):
    md = ROOT / "docs" / "coverage" / f"{site}.md"
    assert md.is_file(), f"run `make fetch SITE={site}` to write {md}"
    text = md.read_text(encoding="utf-8")
    for heading in ("## Site box", "## Where the elevation comes from", "## Georeferencing check"):
        assert heading in text
    assert "**Gap-fill decision:**" in text
    assert "pipeline " in text


@pytest.mark.parametrize("site", SITES)
def test_every_product_has_provenance_and_is_logged(site):
    site_dir = ROOT / "data" / "sites" / site
    if not (site_dir / "fetch_summary.json").exists():
        pytest.skip(f"no local fetch for {site}")
    summary = json.loads((site_dir / "fetch_summary.json").read_text(encoding="utf-8"))
    log = (ROOT / "docs" / "SOURCES_LOG.md").read_text(encoding="utf-8")
    block = log.split(f"<!-- site:{site} -->", 1)[1].split("<!-- /site -->", 1)[0]
    files = [p["file"] for p in summary["products"] if not p.get("skipped")]
    files += ["source_class.tif"]
    for name in files + ["rover_path.geojson"]:
        path = site_dir / name
        assert path.exists(), name
        assert sidecar_path(path).exists(), f"{name} has no provenance sidecar"
        prov = read_provenance(path).to_dict()
        for f in REQUIRED_FIELDS:
            assert f in prov
        assert Label(prov["label"])
    for name in files:
        assert f"| {name} |" in block, f"{name} missing from the fetch log"
