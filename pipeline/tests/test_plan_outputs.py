# Written with AI assistance (Claude Code). See AI_USE.md.
"""Committed Phase 3 outputs (tests D9 and D13): plan.json files, the report and validation.json.

The plans and the report are committed, so they are checked in CI; the fields and leg bundles
live in data/ (not committed).
"""

import json

import jsonschema
import pytest

from ariadne.guardrails import repo_root

ROOT = repo_root()
PLANS = sorted((ROOT / "docs" / "plan").glob("*.json"))
SCHEMA = json.loads((ROOT / "config" / "schemas" / "plan.schema.json").read_text(encoding="utf-8"))


def test_there_is_a_plan_for_each_preset():
    names = {p.stem.split("-", 1)[1] for p in PLANS}
    assert {"safest", "balanced", "most_science"} <= names


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_plan_validates_against_the_schema(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(plan, SCHEMA)
    # margins are at most 5 m apart and the thread holds at each
    assert all(m["step_m"] <= 5.0 + 1e-6 for m in plan["margins"])
    assert plan["checks"]["thread"] == "pass"
    assert all(m["c_left"] - (m["c_home"] or 0) >= m["c_reserve"] - 1e-6 for m in plan["margins"])
    # legs chain from the staging point back to it through the stations, in order
    ids = ["STAGING"] + [s["id"] for s in plan["stations"]] + ["STAGING"]
    if plan["legs"]:
        assert [leg["from"] for leg in plan["legs"]] + [plan["legs"][-1]["to"]] == ids
    assert plan["walker_model"]["extrapolated"] is True


def test_a_broken_plan_fails_the_schema():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"site": "boxwork"}, SCHEMA)


def test_report_and_validation_carry_the_phase_3_results():
    report = (ROOT / "docs" / "plan" / "boxwork.md").read_text(encoding="utf-8")
    assert "Thread over random scenarios" in report and "Reference plans" in report
    v = json.loads((ROOT / "validation.json").read_text(encoding="utf-8"))
    checks = {c["id"]: c for c in v["checks"]}
    assert checks["thread"]["status"] == "pass"
    assert checks["thread"]["result"]["scenarios"] >= 1000
    assert checks["walker-model"]["status"] == "reported"
    assert checks["walker-model"]["result"]["minetti_within_one_sd"] == "12 of 13"
    assert checks["station-solver"]["status"] in {"pass", "fail"}
    assert checks["station-solver"]["result"]["scenarios"] >= 50
