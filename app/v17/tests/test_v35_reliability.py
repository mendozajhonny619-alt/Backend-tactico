"""V3.5 guardrails: real timed windows and fail-closed Master publication."""
from __future__ import annotations

from datetime import datetime, timezone

from app.jhonny_elite.master_protocol import TemporalMatchMemory, MasterDecisionAI20, CalibrationMetrics
from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine


def snapshot(minute, timestamp, **overrides):
    row = {
        "fixture_id": "fixture-42", "api_minute": minute, "fetched_at": timestamp,
        "home_score": 0, "away_score": 0,
        "home_shots": 3, "away_shots": 2, "home_shots_on_target": 1,
        "away_shots_on_target": 0, "home_xg": 0.5, "away_xg": 0.1,
        "shots": 5, "shots_on_target": 1, "xg": 0.6,
    }
    row.update(overrides)
    return row


def test_twenty_minute_old_snapshot_does_not_fake_5_10_15():
    memory = TemporalMatchMemory()
    memory.enrich(snapshot(60, 1000))
    out = memory.enrich(snapshot(80, 2200, shots=16, xg=2.1))
    assert out["temporal_memory_ready"] is False
    assert all(out[f"window_{w}"]["available"] is False for w in (5, 10, 15))
    assert AdvancedProbabilityEngine()._recent_hazard(out) == (None, None)


def test_multiple_snapshots_create_only_real_measured_windows():
    memory = TemporalMatchMemory()
    for minute in (60, 65, 70):
        out = memory.enrich(snapshot(minute, 1000 + (minute - 60) * 60,
                                     shots=minute - 55, xg=(minute - 55) / 20))
    assert out["window_5"]["available"]
    assert out["window_10"]["available"]
    assert out["window_15"]["available"] is False
    out = memory.enrich(snapshot(75, 1900, shots=20, xg=1.0))
    assert all(out[f"window_{w}"]["available"] for w in (5, 10, 15))
    assert out["window_5"]["observed_minutes"] == 5
    assert out["window_10"]["observed_minutes"] == 10
    assert out["window_15"]["observed_minutes"] == 15


def test_half_time_time_gap_invalidates_momentum_even_if_minutes_increase():
    memory = TemporalMatchMemory()
    memory.enrich(snapshot(45, 1000))
    out = memory.enrich(snapshot(50, 2300, shots=10))  # 5 game min but 21+ wall-clock minutes
    assert out["window_5"]["available"] is False
    assert not out["temporal_memory_ready"]


def test_backwards_scores_and_stat_corrections_reset_baseline():
    memory = TemporalMatchMemory()
    memory.enrich(snapshot(60, 1000, home_score=1, xg=1.5, shots=8))
    score_revised = memory.enrich(snapshot(65, 1300, home_score=0, xg=1.5, shots=8))
    assert score_revised["temporal_memory_reset_reason"] == "SCORE_REVISION"
    assert score_revised["window_5"]["available"] is False
    stats_revised = memory.enrich(snapshot(70, 1600, home_score=0, xg=0.8, shots=7))
    assert stats_revised["temporal_memory_reset_reason"] == "STAT_REVISION"
    assert not stats_revised["temporal_memory_ready"]


def test_per_team_deltas_remain_distinct_and_zero_is_valid():
    memory = TemporalMatchMemory()
    memory.enrich(snapshot(60, 1000, home_shots=0, away_shots=0,
                           home_shots_on_target=0, away_shots_on_target=0,
                           home_xg=0, away_xg=0, shots=0, shots_on_target=0, xg=0))
    out = memory.enrich(snapshot(65, 1300, home_shots=2, away_shots=4,
                                 home_shots_on_target=1, away_shots_on_target=0,
                                 home_xg=0.35, away_xg=0.4, shots=6,
                                 shots_on_target=1, xg=0.75))
    window = out["window_5"]
    assert window["available"] is True
    assert window["home_delta_shots"] == 2
    assert window["away_delta_shots"] == 4
    assert window["home_delta_sot"] == 1
    assert window["away_delta_sot"] == 0
    assert window["home_delta_xg"] == 0.35
    assert window["away_delta_xg"] == 0.4


def test_missing_stats_never_become_false_zero_momentum():
    memory = TemporalMatchMemory()
    memory.enrich({"fixture_id": "55", "minute": 30, "fetched_at": 1000})
    out = memory.enrich({"fixture_id": "55", "minute": 35, "fetched_at": 1300})
    assert out["window_5"]["available"] is False
    assert out["window_5"]["reason"] == "MISSING_FINISHING_STATISTICS"


def master_inputs():
    return dict(
        match={"api_minute": 70, "home_score": 1, "away_score": 0, "recent_threat_score": 75},
        direction="OVER", candidate_score=99, candidate=True, blockers=[],
        clock={"clock_status": "CLOCK_OK"},
        data_truth={"data_truth_status": "EXCELLENT", "data_truth_score": 98},
        context={"over_context_score": 95, "rhythm_score": 90},
        tactical={"tactical_score": 94}, risk={"risk_score": 5, "risk_status": "LOW"},
        pre_match={"pre_match_available": True, "over_pre_match_score": 99},
        math_evidence={"math_support_over": 99, "calibration_status": "VALIDATED_OUT_OF_SAMPLE"},
        odds={"odds_available": True, "line": 2.5, "odds": 1.85, "has_positive_value": True,
              "value_edge": 20, "expected_value": 0.19},
        contradiction={"critical_contradictions": []},
    )


def test_legacy_quote_cannot_publish_without_explicit_verification():
    kwargs = master_inputs()
    out = MasterDecisionAI20().decide(**kwargs)
    assert out["official_can_publish"] is False
    assert "LIVE_GOALS_MARKET_NOT_VERIFIED" in out["official_warnings"]


def test_model_uncalibrated_cannot_publish_despite_verified_quote():
    kwargs = master_inputs()
    kwargs["odds"].update({
        "verification_required": True, "valuation_status": "VERIFIED_FRESH_CALIBRATED",
        "odds_source": "API_FOOTBALL_LIVE_ODDS", "quote_is_live": True,
        "market_verified": True, "fixture_verified": True,
        "market_type": "MATCH_GOALS_TOTAL", "market_period": "FT",
        "odds_age_seconds": 3, "odds_timestamp": datetime.now(timezone.utc).isoformat(),
    })
    kwargs["math_evidence"]["calibration_status"] = "NOT_VALIDATED_OUT_OF_SAMPLE"
    out = MasterDecisionAI20().decide(**kwargs)
    assert out["official_can_publish"] is False


def test_calibration_never_uses_heuristic_confidence_as_event_probability():
    value = CalibrationMetrics.evaluate([
        {"result_status": "WON", "official_confidence": 98},
        {"result_status": "LOST", "official_confidence": 80},
    ])
    assert value["samples"] == 0
    assert value["brier_score"] is None
    assert value["calibration_status"] == "INSUFFICIENT_DATA"


def test_dashboard_never_displays_candidate_index_as_goal_probability():
    from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter
    adapter = V17DashboardAdapter.__new__(V17DashboardAdapter)
    pack = adapter._prediction_probability_pack({"over_score": 96, "under_score": 4})
    assert pack["raw_over_score"] == 96
    assert pack["visual_over_probability"] is None
    assert pack["visual_under_probability"] is None
