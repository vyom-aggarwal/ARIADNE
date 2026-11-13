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
    ids = ["STAGING"] + [s["id"] for s in plan["stations"]] + [plan["rover"]["ends_at"]]
    if plan["legs"]:
        assert [leg["from"] for leg in plan["legs"]] + [plan["legs"][-1]["to"]] == ids
    assert plan["walker_model"]["extrapolated"] is True


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_plans_visit_whole_transects_in_order(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    st = plan["stations"]
    assert len(st) % 3 == 0 and plan["totals"]["stations"] == len(st)
    assert plan["totals"]["transects"] == len(st) // 3
    for k in range(0, len(st), 3):
        trio = st[k : k + 3]
        assert len({s["transect"] for s in trio}) == 1
        assert trio[0]["role"] in {"fracture", "crest"}
        assert [s["role"] for s in trio[1:]] == ["wall", "hollow"]


def test_presets_differ_by_their_safety_settings():
    presets = json.loads((ROOT / "config" / "presets.json").read_text(encoding="utf-8"))["presets"]
    safest, balanced, most = presets["safest"], presets["balanced"], presets["most_science"]
    assert safest["limits"] == {"reserve_min": 45, "shelter_max_min": 10}
    assert safest["weights"]["hazard"] == 3 * balanced["weights"]["hazard"]
    assert safest["weights"]["uncertainty"] == 3 * balanced["weights"]["uncertainty"]
    assert most["limits"] == balanced["limits"] and most["weights"]["hazard"] == 0
    assert most["objective"] == "transects"
    plans = {p.stem.split("-", 1)[1]: json.loads(p.read_text(encoding="utf-8")) for p in PLANS}
    s = plans["safest"]
    assert all(m["c_reserve"] == 45 for m in s["margins"])
    assert s["totals"]["worst_minutes_to_shelter"] <= 10.0 + 1e-6
    for name, plan in plans.items():
        lim = presets[name]["limits"]
        assert plan["scenario"]["reserve_min"] == lim["reserve_min"]
        assert plan["totals"]["worst_minutes_to_shelter"] <= lim["shelter_max_min"] + 1e-6
        assert plan["scenario"]["eva_max_min"] == 360  # the spec's 6 h
        assert plan["totals"]["minutes"] <= 360 + 1e-6


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


# --- F5: the rover as a mobile comms relay ---


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_plans_carry_the_rover_relay_schedule_and_end_at_the_rover(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    rover = plan["rover"]
    relay_ids = {r["id"] for r in rover["relays"]}
    assert "STAGING" in relay_ids and rover["ends_at"] in relay_ids
    assert all(s["relay"] in relay_ids for s in plan["stations"])
    if plan["legs"]:
        assert plan["legs"][-1]["to"] == rover["ends_at"]
    # each transect is worked from one relay; moves happen only between transects
    for k in range(0, len(plan["stations"]), 3):
        assert len({s["relay"] for s in plan["stations"][k : k + 3]}) == 1
    assert plan["totals"]["rover_moves"] == len(rover["moves"])
    for mv in rover["moves"]:
        assert mv["drive_min"] <= 15.0 + 1e-6 or mv["before_transect"] == 1
    assert plan["totals"]["longest_comm_shadow_min"] <= 10.0 + 1e-6
    assert all(v == "pass" for v in plan["checks"].values())


def test_report_compares_plans_with_and_without_the_relay():
    report = (ROOT / "docs" / "plan" / "boxwork.md").read_text(encoding="utf-8")
    assert "Rover as a mobile comms relay" in report and "staging only, with relay" in report


# --- E11 to E13: the rover is the shelter, storm mode by lowest dose, price of safety ---


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_every_sample_stays_within_the_walking_limit_to_the_rover(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    lim = plan["scenario"]["shelter_max_min"]
    mins = [m["minutes_to_rover"] for m in plan["margins"]]
    assert mins and all(x is not None and x <= lim + 1e-6 for x in mins)
    assert max(mins) <= plan["totals"]["worst_minutes_to_shelter"] + 1e-6


@pytest.mark.parametrize("path", PLANS, ids=lambda p: p.name)
def test_plans_carry_storm_responses_by_lowest_dose(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    st = plan["storm"]
    assert st["label"] == "MODELED"
    assert {"event_duration_min", "rover_s"} <= set(st["placeholders"])
    sm = st["samples"]
    assert all(b["t_min"] > a["t_min"] for a, b in zip(sm, sm[1:], strict=False))
    # a response at least every 5 minutes of walking (the crew stands still during a visit)
    mg = plan["margins"]
    service = plan["stations"][0]["service_min"] if plan["stations"] else 0.0
    for a, b in zip(sm, sm[1:], strict=False):
        walked = sum(
            q["t_min"] - p["t_min"] - (service if q["station"] is not None else 0.0)
            for p, q in zip(mg, mg[1:], strict=False)
            if a["t_min"] <= p["t_min"] and q["t_min"] <= b["t_min"] and p["xy_m"] != q["xy_m"]
        )
        assert walked <= 5.0 + 0.5, (a["t_min"], b["t_min"], walked)
    assert sm[-1]["t_min"] >= plan["totals"]["minutes"] - 5.5
    for x in sm:
        assert x["choice"] in {"rover", "terrain", "stay"}
        assert x["dose"] <= x["dose_staying"] + 1e-6  # staying put is always an option
        assert x["dose_avoided"] == pytest.approx(x["dose_staying"] - x["dose"], abs=0.011)
        assert len(x["path_xy_m"]) >= 1
        if x["choice"] == "rover":
            assert x["s_dest"] == pytest.approx(st["rover_s"])


def test_report_gives_the_price_of_safety_and_says_whether_the_presets_separate():
    report = (ROOT / "docs" / "plan" / "boxwork.md").read_text(encoding="utf-8")
    assert "## Price of safety" in report and "Do the presets separate?" in report
    assert "## Storm mode along the plans" in report
    assert "terrain shelter" not in report.lower()
