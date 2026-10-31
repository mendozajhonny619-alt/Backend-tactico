"""V3.6 regression tests. Everything is offline; no API credits consumed."""
import tempfile
from pathlib import Path

import pytest

from app.v17.services.shadow_outcome_tracker import ShadowOutcomeTracker


def candidate(fid="123", minute=67, score=(1, 0), direction="OVER", primary="2-0", p=66.5):
    return {
        "match_id": fid, "fixture_id": fid, "home_team": "Local", "away_team": "Visita",
        "country": "Test", "league": "Primera", "home_score": score[0], "away_score": score[1],
        "api_minute": minute, "effective_minute": minute, "status_short": "2H",
        "prediction_status": "EXPERIMENTAL", "decision_status": "STRONG_CANDIDATE",
        "data_truth_status": "EXCELLENT", "data_age_seconds": 5,
        "suggested_market": direction, "probability_next_goal": p,
        "probability_no_more_goals": 100-p, "primary_final_score": primary,
        "primary_score_probability": 34.3, "candidate_score": 84.2,
        "math_engine_version": "test_poisson", "official_can_publish": False,
        "can_publish": False, "prediction_evidence_gaps": [],
    }


def fixture(fid="123", score=(2, 0), status="FT"):
    return {"match_id": fid, "fixture_id": fid, "status_short": status,
            "home_score": score[0], "away_score": score[1]}


@pytest.fixture
def tracker(tmp_path):
    return ShadowOutcomeTracker(tmp_path / "data" / "research.sqlite3")


def rows(tracker):
    return {x["event_type"]: x for x in tracker.recent()}


def test_freezes_first_candidate_and_survives_restart(tracker):
    first = candidate()
    assert tracker.register([first]) == 2
    assert tracker.register([dict(first, candidate_score=99.9, probability_next_goal=99.9)]) == 0
    data = rows(tracker)
    assert data["GOAL_REMAINING_FT"]["model_probability"] == 66.5
    assert data["EXACT_SCORE_FT"]["predicted_score"] == "2-0"
    after_restart = ShadowOutcomeTracker(tracker.path)
    assert len(after_restart.recent()) == 2
    assert after_restart.pending_fixture_ids() == ["123"]
    assert all(x["shadow_only"] == 1 for x in after_restart.recent())


def test_verified_ft_settles_event_and_exact_score(tracker):
    tracker.register([candidate()])
    assert tracker.resolve([fixture(status="2H")]) == 0
    assert tracker.resolve([fixture(status="FT")]) == 2
    assert all(r["result_status"] == "WON" for r in tracker.recent())
    assert tracker.resolve([fixture(status="FT")]) == 0  # idempotent
    assert tracker.pending_fixture_ids() == []
    assert all(x["label_source"] == "PROVIDER_FINAL_SCORE" for x in tracker.recent())
    assert tracker.snapshot()["grouped"]["EXACT_SCORE_FT"]["hit_rate_percent"] == 100.0


def test_no_goal_research_is_not_a_contractual_under(tracker):
    c = candidate(fid="230", minute=80, score=(2, 0), direction="UNDER", primary="2-0", p=16.0)
    tracker.register([c])
    assert rows(tracker)["NO_GOAL_REMAINING_FT"]["model_probability"] == 84.0
    tracker.resolve([fixture("230", score=(2, 1))])
    assert all(x["result_status"] == "LOST" for x in tracker.recent())
    assert all(x["market_direction"] == "UNDER" for x in tracker.recent())


def test_no_goal_ft_correct_prediction(tracker):
    tracker.register([candidate(fid="231",minute=78,score=(2,0),direction="UNDER",primary="2-0",p=14)])
    tracker.resolve([fixture("231",score=(2,0))])
    assert all(x["result_status"] == "WON" for x in tracker.recent())


def test_bad_source_cannot_be_tracked(tracker):
    invalid = [
        dict(candidate(fid="1"), prediction_status="N/A"),
        dict(candidate(fid="2"), data_truth_status="INSUFFICIENT"),
        dict(candidate(fid="3"), clock_stale=True),
        dict(candidate(fid="4"), prediction_evidence_gaps=["SCORE_CONFLICT"]),
        dict(candidate(fid="5"), data_age_seconds=10000),
        dict(candidate(fid="6"), status_short="FT"),
        dict(candidate(fid="7"), primary_final_score="0-0"),
        dict(candidate(fid="8"), probability_next_goal=None),
        dict(candidate(fid="9"), decision_status="OBSERVATION"),
        dict(candidate(fid="10"), tracking_only_terminal=True),
        dict(candidate(fid="11",minute=55,direction="UNDER")),
        dict(candidate(fid="12",minute=97)),
    ]
    assert tracker.register(invalid) == 0
    assert tracker.recent() == []


def test_new_episode_requires_a_new_score_and_cooldown(tracker):
    assert tracker.register([candidate(score=(1,0),minute=60)]) == 2
    assert tracker.register([candidate(score=(1,1),minute=62,primary="2-1")]) == 0
    assert tracker.register([candidate(score=(1,1),minute=67,primary="2-1")]) == 2
    assert tracker.register([candidate(score=(1,1),minute=72,primary="3-1")]) == 0
    assert tracker.register([candidate(score=(2,1),minute=73,primary="3-1")]) == 2
    assert tracker.register([candidate(score=(3,1),minute=80,primary="4-1")]) == 0  # max episodes
    assert len(tracker.recent()) == 6


def test_never_fabricate_results_without_verified_final(tracker):
    tracker.register([candidate()])
    assert tracker.resolve([]) == 0
    assert tracker.resolve([fixture(status="2H",score=(2,0))]) == 0
    assert all(x["result_status"] == "PENDING" for x in tracker.recent())
    assert tracker.snapshot()["grouped"]["GOAL_REMAINING_FT"]["hit_rate_percent"] is None
    assert tracker.resolve([fixture(status="AET",score=(3,1))]) == 2
    assert all(x["result_status"] == "VOID" for x in tracker.recent())


def test_score_correction_marked_unresolved(tracker):
    tracker.register([candidate(score=(1,1),primary="2-1")])
    tracker.resolve([fixture(score=(1,0))])
    assert all(x["result_status"] == "UNRESOLVED" for x in tracker.recent())
    assert tracker.snapshot()["grouped"]["GOAL_REMAINING_FT"]["hit_rate_percent"] is None


def test_export_only_verified_research_not_market_bets(tracker, tmp_path):
    tracker.register([candidate(fid="123")])
    tracker.register([candidate(fid="222",direction="UNDER",minute=85,primary="1-0",score=(1,0))])
    tracker.resolve([fixture("123",score=(2,0))])
    path=tmp_path / "analysis" / "shadow_labeled.jsonl"
    assert tracker.export_research_jsonl(path) == 2
    content=path.read_text(encoding="utf-8")
    assert '"research_only": true' in content
    assert '"event_type": "EXACT_SCORE_FT"' in content
    assert "222" not in content


def test_only_top_six_new_forecasts_are_recorded_each_cycle(tracker):
    entries=[candidate(fid=str(i),minute=60,score=(1,0),direction="OVER",primary="2-0") for i in range(1,16)]
    assert tracker.register(entries) == 12  # 6 x (event + FT)
    assert len(tracker.pending_fixture_ids()) == 6


def test_research_does_not_require_odds_and_does_not_publish(tracker):
    data = candidate()
    data["odds_available"] = False
    data["can_publish"] = False
    data["official_can_publish"] = False
    assert tracker.register([data]) == 2
    assert all(x["shadow_only"] == 1 for x in tracker.recent())
    assert tracker.snapshot()["official_signals_created"] == 0


def test_paginated_query_reports_all_counts_and_does_not_confuse_markets(tracker):
    for i in range(1, 9):
        tracker.register([candidate(fid=str(i), minute=74, direction="OVER", primary="2-0")])
    for i in range(1, 9):
        tracker.resolve([fixture(str(i),score=(2,0) if i<=5 else (1,0))])
    query = tracker.query(range_key="all", family="goals",limit=3)
    assert query["total"] == 8 and query["has_more"]
    assert len(query["rows"]) == 3 and query["summary"]["won"] == 5
    next_page = tracker.query(range_key="all",family="goals",limit=3,offset=3)
    assert len(next_page["rows"]) == 3
    assert len(tracker.query(range_key="all",family="goals",limit=3,offset=6)["rows"]) == 2
    ft = tracker.query(range_key="all",family="score")
    assert ft["total"] == 8 and all(r["event_type"] == "EXACT_SCORE_FT" for r in ft["rows"])
    assert tracker.snapshot(limit=2)["total_historical_forecasts"] == 16
    assert tracker.snapshot(limit=2)["is_complete_history"] is False


def test_date_ranges_are_based_on_la_paz_entry_date(tracker):
    from datetime import datetime, timezone, timedelta
    from zoneinfo import ZoneInfo
    tracker.register([candidate(fid="today")])
    tracker.register([candidate(fid="yesterday")])
    tracker.register([candidate(fid="last_week")])
    now = datetime.now(ZoneInfo("America/La_Paz"))
    midnight = now.replace(hour=12,minute=0,second=0,microsecond=0)
    previous = (midnight-timedelta(days=1)).astimezone(timezone.utc).isoformat()
    old = (midnight-timedelta(days=8)).astimezone(timezone.utc).isoformat()
    with tracker._lock,tracker._connect() as db:
        db.execute("UPDATE forecasts SET created_at=? WHERE fixture_id='yesterday'",(previous,))
        db.execute("UPDATE forecasts SET created_at=? WHERE fixture_id='last_week'",(old,))
    assert tracker.query(range_key="today")["total"] == 1
    assert tracker.query(range_key="yesterday")["total"] == 1
    assert tracker.query(range_key="seven")["total"] == 2
    assert tracker.query(range_key="all")["total"] == 3


def test_diagnostic_brier_score_is_not_claimed_as_calibration(tracker):
    tracker.register([candidate()])
    tracker.resolve([fixture(score=(2,0))])
    diag = tracker.research_diagnostics()
    goal = diag["groups"]["GOAL_REMAINING_FT"]
    assert goal["labeled_forecasts"] == 1
    assert goal["distinct_fixtures"] == 1
    assert goal["brier_score"] == pytest.approx((1-0.665)**2,abs=1e-6)
    assert diag["production_calibrated"] is False
    assert diag["requires_temporal_out_of_sample_validation"] is True
    assert tracker.snapshot()["research_diagnostics"] == diag


def test_extra_time_cannot_be_frozen_as_90_minute_forecast(tracker):
    assert tracker.register([dict(candidate(), status_short="ET")]) == 0


def test_invalid_query_range_and_family_are_rejected(tracker):
    with pytest.raises(ValueError,match="INVALID_DATE_RANGE"):
        tracker.query(range_key="never")
    with pytest.raises(ValueError,match="INVALID_FORECAST_FAMILY"):
        tracker.query(family="betting")
