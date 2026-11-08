# Written with AI assistance (Claude Code). See AI_USE.md.
"""MSL mission sols (acceptance test B3).

Sources: Mars24 notes (sol 0 = touchdown sol; mission clock = LMST at 137.42 E), NAIF kernel
msl_lmst_ops120808_v1.tsc (touchdown 2012-08-06T05:17:57 UTC; sol 0 midnight at the actual
landing site 2012-08-05T13:49:59 UTC = 397446666.183 ET seconds past J2000; 88775.244 s per
sol), NASA image captions (PROMPT.md section 3) and the REMS daily feed (outreach only; used
here as a cross-check, never as data).
"""

import csv
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from ariadne.models import leapseconds, msl_time

FIXTURES = Path(__file__).parent / "fixtures"

NAIF_SOL0_ET = 397446666.183
NAIF_SECONDS_PER_SOL = 88775.244
ACTUAL_LANDING_LON_EAST = 137.442
NAIF_TOLERANCE_S = 10.0  # see docs/PROGRESS.md, "B3 tolerance change"


def naif_sol_start_utc(sol: int) -> datetime:
    """Midnight LMST at the actual landing site per the NAIF linear clock (ET ~ TT here)."""
    tt = datetime(2000, 1, 1, 12, tzinfo=UTC) + timedelta(
        seconds=NAIF_SOL0_ET + sol * NAIF_SECONDS_PER_SOL
    )
    return tt - timedelta(seconds=leapseconds.tt_minus_utc(tt))


def test_touchdown_is_sol_0():
    assert msl_time.msl_sol(msl_time.MSL_TOUCHDOWN_UTC) == 0


def test_touchdown_was_mid_afternoon_on_the_mission_clock():
    # Sanity: Curiosity landed in the local afternoon.
    assert 14.0 < msl_time.msl_lmst_hours(msl_time.MSL_TOUCHDOWN_UTC) < 16.0


@pytest.mark.parametrize("sol", [0, 1000, 3000, 5000])
def test_sol_starts_agree_with_the_naif_clock(sol):
    ours = msl_time.sol_start_utc(sol, lon_east=ACTUAL_LANDING_LON_EAST)
    naif = naif_sol_start_utc(sol)
    gap = abs((ours - naif).total_seconds())
    assert gap < NAIF_TOLERANCE_S, f"sol {sol}: Mars24 {ours}, NAIF {naif}, gap {gap:.1f} s"


def test_naif_sol_0_midnight_is_as_documented():
    # Guards the conversion in this test file against the kernel's own comment.
    assert naif_sol_start_utc(0).replace(microsecond=0) in {
        datetime(2012, 8, 5, 13, 49, 58, tzinfo=UTC),
        datetime(2012, 8, 5, 13, 49, 59, tzinfo=UTC),
    }


@pytest.mark.parametrize("sol", [0, 1, 1455, 4636, 5000])
def test_sol_start_round_trips(sol):
    start = msl_time.sol_start_utc(sol)
    assert msl_time.msl_sol(start + timedelta(seconds=1)) == sol
    assert msl_time.msl_sol(start - timedelta(seconds=1)) == sol - 1


def test_a_sol_lasts_88775_seconds():
    span = msl_time.sol_start_utc(4637) - msl_time.sol_start_utc(4636)
    assert span.total_seconds() == pytest.approx(88775.244, abs=0.01)


def _within_one_day(sol: int, day: date) -> bool:
    start = msl_time.sol_start_utc(sol)
    end = msl_time.sol_start_utc(sol + 1)
    return start.date() - timedelta(days=1) <= day <= end.date() + timedelta(days=1)


@pytest.mark.parametrize(
    ("sol", "day"),
    [
        (4190, date(2024, 5, 20)),
        (4220, date(2024, 6, 19)),
        (4636, date(2025, 8, 21)),
        (4650, date(2025, 9, 5)),
        (4677, date(2025, 10, 2)),
    ],
)
def test_caption_fixtures_within_one_day(sol, day):
    assert _within_one_day(sol, day)


def _rems_sample():
    with open(FIXTURES / "rems_feed_sample.csv", encoding="utf-8") as f:
        return [
            (int(r["sol"]), date.fromisoformat(r["terrestrial_date"]), float(r["ls"]))
            for r in csv.DictReader(f)
        ]


def test_rems_sample_is_broad():
    rows = _rems_sample()
    assert len(rows) >= 90
    assert rows[0][0] <= 100 and rows[-1][0] >= 4900


def test_rems_feed_dates_within_one_day():
    bad = [(s, d) for s, d, _ in _rems_sample() if not _within_one_day(s, d)]
    assert bad == []


def test_rems_feed_solar_longitude_within_1_5_degrees():
    bad = []
    for sol, _, ls_feed in _rems_sample():
        mid = msl_time.sol_start_utc(sol) + timedelta(seconds=88775.244 / 2)
        ls = msl_time.solar_longitude(mid)
        diff = (ls - ls_feed + 180.0) % 360.0 - 180.0
        if abs(diff) > 1.5:
            bad.append((sol, ls_feed, round(ls, 2)))
    assert bad == []


def test_sol_window_for_dates_covers_both_ends():
    first, last = msl_time.sols_for_utc_dates(date(2016, 9, 9), date(2016, 9, 21))
    assert msl_time.sol_start_utc(first) <= datetime(2016, 9, 9, tzinfo=UTC)
    assert msl_time.sol_start_utc(last + 1) >= datetime(2016, 9, 22, tzinfo=UTC)
