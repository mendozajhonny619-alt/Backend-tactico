from __future__ import annotations

from app.jhonny_elite.master_protocol import (
    CalibrationMetrics,
    DataTruthAI,
    MasterDecisionAI20,
    TemporalMatchMemory,
)
from app.v17.signals.signal_tracker import SignalTracker
from app.config.config import Config


def test_data_truth_blocks_empty_live_evidence():
    truth = DataTruthAI().evaluate(
        {"api_minute": 70, "shots": 0, "shots_on_target": 0, "dangerous_attacks": 0, "xg": 0, "has_live_stats": False},
        {"data_valid": True, "data_issues": []},
        {"clock_status": "CLOCK_OK", "timestamp_missing": True, "stats_confirmed": False},
    )
    assert truth["anti_empty_data_block"] is True
    assert truth["data_valid"] is False
    assert "EMPTY_LIVE_EVIDENCE" in truth["data_truth_issues"]


def test_temporal_memory_exposes_5_10_15_windows():
    memory = TemporalMatchMemory()
    a = {"fixture_id": "7", "api_minute": 60, "fetched_at": 1000, "shots": 5, "shots_on_target": 1, "dangerous_attacks": 12, "corners": 2, "xg": 0.5, "home_score": 0, "away_score": 0}
    b = {"fixture_id": "7", "api_minute": 65, "fetched_at": 1300, "shots": 9, "shots_on_target": 3, "dangerous_attacks": 20, "corners": 4, "xg": 1.0, "home_score": 0, "away_score": 0}
    memory.enrich(a)
    out = memory.enrich(b)
    assert out["temporal_memory_ready"] is True
    assert out["window_5"]["available"] is True
    assert out["window_10"]["available"] is True
    assert out["window_15"]["available"] is True
    assert out["window_5"]["delta_sot"] == 2


def test_master_requires_real_odds_line_and_value():
    master = MasterDecisionAI20()
    result = master.decide(
        match={"api_minute": 70, "recent_threat_score": 75},
        direction="OVER", candidate_score=92, candidate=True, blockers=[],
        clock={"clock_status": "CLOCK_OK"},
        data_truth={"data_truth_status": "HIGH", "data_truth_score": 90},
        context={"over_context_score": 82, "under_context_score": 20, "rhythm_score": 80},
        tactical={"tactical_score": 80, "false_pressure_risk": 10},
        risk={"risk_score": 20, "risk_status": "LOW"},
        pre_match={"pre_match_available": True, "over_pre_match_score": 80},
        math_evidence={"math_support_over": 88, "primary_final_score": "2-1", "probability_next_goal": 82},
        odds={"odds_available": False, "line": 2.5, "odds": 0, "has_positive_value": False},
        contradiction={"critical_contradictions": []},
    )
    assert result["official_can_publish"] is False
    assert "MISSING_REAL_LINE_OR_ODDS" in result["official_warnings"]


def test_master_can_confirm_with_four_of_five_layers():
    master = MasterDecisionAI20()
    result = master.decide(
        match={"api_minute": 70, "recent_threat_score": 78},
        direction="OVER", candidate_score=96, candidate=True, blockers=[],
        clock={"clock_status": "CLOCK_OK"},
        data_truth={"data_truth_status": "EXCELLENT", "data_truth_score": 98},
        context={"over_context_score": 90, "under_context_score": 12, "rhythm_score": 82},
        tactical={"tactical_score": 87, "false_pressure_risk": 8},
        risk={"risk_score": 15, "risk_status": "LOW"},
        pre_match={"pre_match_available": True, "over_pre_match_score": 86},
        math_evidence={"math_support_over": 94, "primary_final_score": "2-1", "probability_next_goal": 88},
        odds={"odds_available": True, "line": 2.5, "odds": 1.8, "has_positive_value": True, "value_edge": 14, "expected_value": 0.20, "implied_probability": 55.56},
        contradiction={"critical_contradictions": []},
    )
    assert result["official_consensus"] >= 4
    assert result["official_can_publish"] is True
    assert result["official_market"] == "OVER"
    assert result["decision_version"] == "MASTER_PROTOCOL_20.0"


def test_master_critical_contradiction_blocks():
    master = MasterDecisionAI20()
    result = master.decide(
        match={"api_minute": 72}, direction="UNDER", candidate_score=95, candidate=True, blockers=[],
        clock={"clock_status": "CLOCK_OK"},
        data_truth={"data_truth_status": "HIGH", "data_truth_score": 90},
        context={}, tactical={}, risk={"risk_score": 10}, pre_match={}, math_evidence={},
        odds={"odds_available": True, "line": 3.5, "odds": 1.7, "has_positive_value": True},
        contradiction={"critical_contradictions": ["UNDER_PLUS_ACCELERATING_RHYTHM"]},
    )
    assert result["official_status"] == "BLOCKED"
    assert result["official_can_publish"] is False


def test_tracker_key_is_match_market_line_only(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DATA_DIR", str(tmp_path))
    tracker = SignalTracker()
    a = {"match_id": "44", "market": "OVER", "home_score": 1, "away_score": 0, "line": 2.5}
    b = {"match_id": "44", "market": "OVER", "home_score": 2, "away_score": 0, "line": 2.5}
    c = {"match_id": "44", "market": "OVER", "home_score": 2, "away_score": 0, "line": 3.5}
    assert tracker._stable_signal_key(a, "OVER") == tracker._stable_signal_key(b, "OVER")
    assert tracker._stable_signal_key(a, "OVER") != tracker._stable_signal_key(c, "OVER")


def test_calibration_metrics_are_native():
    metrics = CalibrationMetrics.evaluate([
        {"official_confidence": 80, "result_status": "WON"},
        {"official_confidence": 70, "result_status": "LOST"},
    ])
    assert metrics["samples"] == 2
    assert metrics["brier_score"] > 0
    assert metrics["log_loss"] > 0
    assert metrics["calibration_error"] >= 0
