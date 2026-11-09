# Written with AI assistance (Claude Code). See AI_USE.md.
"""Walker model (acceptance test D1): Minetti et al. 2002 values, the tested ranges of
NASA/TP-2010-216125, and the shared fixture the TypeScript twin is checked against."""

import json

import numpy as np
import pytest

from ariadne.guardrails import repo_root
from ariadne.models import metabolic as mb

# Minetti et al. 2002, Table 2 (p. 1042): gradient, mean minimum Cw, SD (J/kg/m), n = 10.
MINETTI_TABLE_2 = [
    (-0.45, 3.46, 0.95),
    (-0.40, 3.23, 0.59),
    (-0.35, 2.65, 0.68),
    (-0.30, 2.18, 0.67),
    (-0.20, 1.30, 0.48),
    (-0.10, 0.81, 0.37),
    (0.00, 1.64, 0.50),
    (0.10, 4.68, 0.34),
    (0.20, 8.07, 0.57),
    (0.30, 11.29, 1.14),
    (0.35, 12.72, 0.76),
    (0.40, 14.75, 0.61),
    (0.45, 17.33, 1.11),
]
FIXTURE = repo_root() / "config" / "models" / "metabolic_fixture.json"


@pytest.fixture(scope="module")
def suit():
    return mb.load_suit()


@pytest.mark.parametrize(("i", "mean", "sd"), [r for r in MINETTI_TABLE_2 if r[0] != 0.0])
def test_polynomial_matches_the_measured_means_within_one_sd(i, mean, sd):
    assert abs(float(mb.cost_of_transport(i)) - mean) <= sd


def test_the_level_value_is_the_one_known_mismatch():
    # The fitted polynomial gives 2.5 on the level; the measured minimum was 1.64 +/- 0.50
    # (1.7 SD). The fit also used Margaria's data (Fig. 1 legend), so the gap is recorded here.
    assert float(mb.cost_of_transport(0.0)) == pytest.approx(2.5)
    assert 1.0 < (2.5 - 1.64) / 0.50 < 2.0


def test_uphill_costs_more_than_downhill_and_the_range_is_clamped():
    assert mb.cost_of_transport(0.2) > mb.cost_of_transport(-0.2)
    assert mb.cost_of_transport(0.9) == pytest.approx(mb.cost_of_transport(0.45))


def test_pace_follows_the_power_ceiling_uphill(suit):
    assert float(mb.speed(0.0, suit)) == pytest.approx(suit.max_speed_m_s)
    v = float(mb.speed(0.3, suit))
    assert v == pytest.approx(
        suit.power_ceiling_w_kg / (suit.suit_gravity_factor * 11.184), rel=1e-3
    )
    assert mb.speed(0.4, suit) < mb.speed(0.2, suit) < mb.speed(0.0, suit)
    assert float(mb.rate_ratio(0.0, suit)) == pytest.approx(1.0)


def test_every_mars_walk_is_flagged_extrapolated(suit):
    flags = mb.extrapolation_flags(0.1, 0.8, suit)
    assert len(flags) == 1 and "gravity 0.38 g" in flags[0]
    assert any("grade -10%" in f for f in mb.extrapolation_flags(-0.1, 0.8, suit))
    assert any("speed 0.30" in f for f in mb.extrapolation_flags(0.1, 0.3, suit))
    assert any("Minetti" in f for f in mb.extrapolation_flags(0.6, 0.8, suit))


def test_shared_fixture_matches_this_implementation(suit):
    """config/models/metabolic_fixture.json is the contract both implementations meet."""
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fx["suit"] == "default"
    for row in fx["rows"]:
        i = row["gradient"]
        assert float(mb.cost_of_transport(i)) == pytest.approx(row["cw_j_kg_m"], abs=1e-9)
        assert float(mb.speed(i, suit)) == pytest.approx(row["speed_m_s"], abs=1e-9)
        assert float(mb.rate_ratio(i, suit)) == pytest.approx(row["rate_ratio"], abs=1e-9)
    grid = np.array([r["gradient"] for r in fx["rows"]])
    assert grid.min() <= -0.45 and grid.max() >= 0.45
