"""Offline calibration: no future outcome, no duplicate/leaked fixture, no auto approval."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.v17.ai.calibration_lab import evaluate_dataset, parse_record, _fit_isotonic, _apply_calibration

START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def row(n: int, *, predicted=None, resolved=None, fixture=None, **changes):
    predicted = predicted or START + timedelta(days=n)
    result = {
        "fixture_id": fixture or str(1000 + n),
        "episode_id": "initial", "market": "OVER_MATCH_DYNAMIC", "period": "FT",
        "line": 2.5, "model_version": "MODEL_TEST_V1",
        "predicted_at": predicted.isoformat(),
        "resolved_at": (resolved or predicted + timedelta(hours=3)).isoformat(),
        "model_probability": 65 if n % 2 else 35,
        "label_source": "FINAL_SCORE",
        "result_status": "WON" if n % 2 else "LOST",
        "final_home_score": 2 if n % 2 else 1,
        "final_away_score": 1,
    }
    result.update(changes)
    return result


def test_reject_future_data_and_missing_labels():
    records = [
        row(0, resolved=START - timedelta(minutes=1)),
        row(1, label_source="UNVERIFIED"),
        row(2, result_status="PENDING"),
        row(3, model_probability=None),
        row(4, line=2.0),
        row(5),
    ]
    result = evaluate_dataset(records, min_train=2, min_test=2)
    assert result["accepted_records"] == 1
    assert result["rejected_records_by_reason"]["FUTURE_DATA_LEAKAGE"] == 1
    assert result["rejected_records_by_reason"]["UNVERIFIED_OUTCOME_SOURCE"] == 1
    assert result["rejected_records_by_reason"]["UNSETTLED_OUTCOME"] == 1
    assert result["rejected_records_by_reason"]["MISSING_EVENT_PROBABILITY"] == 1
    assert result["rejected_records_by_reason"]["UNSUPPORTED_MARKET_LINE"] == 1
    assert result["production_calibration_status"] == "NOT_VALIDATED_OUT_OF_SAMPLE"
    assert result["auto_activation"] is False


def test_default_minimums_cannot_be_bypassed_by_small_samples():
    result = evaluate_dataset([row(i) for i in range(18)])
    assert result["group_reports"][0]["status"] == "INSUFFICIENT_DATA"
    assert not result["group_reports"][0]["approved_for_production"]


def test_chronological_holdout_and_metrics_exist_without_auto_activation():
    result = evaluate_dataset([row(i) for i in range(30)], min_train=8, min_test=6)
    g = result["group_reports"][0]
    assert g["train_fixtures"] >= 8
    assert g["test_fixtures"] >= 6
    assert g["raw_holdout"]["samples"] >= 6
    assert g["candidate_holdout"]["samples"] >= 6
    assert g["approved_for_production"] is False
    assert result["production_calibration_status"] == "NOT_VALIDATED_OUT_OF_SAMPLE"


def test_future_overlap_is_embargoed_and_not_used_as_train():
    records = [row(i, resolved=START + timedelta(days=25)) if i == 3 else row(i) for i in range(20)]
    result = evaluate_dataset(records, min_train=2, min_test=2)
    g = result["group_reports"][0]
    assert g["records_excluded_by_time_embargo"] >= 1


def test_same_fixture_snapshots_cannot_cross_train_test_split():
    records = [row(i) for i in range(28)]
    records.append(row(25, fixture="1000", predicted=START + timedelta(days=26),
                       resolved=START + timedelta(days=26, hours=3)))
    result = evaluate_dataset(records, min_train=3, min_test=3)
    g = result["group_reports"][0]
    assert g["unique_fixtures"] == 28
    assert g["approved_for_production"] is False


def test_isotonic_calibration_is_monotone():
    training = [parse_record(row(i)) for i in range(20)]
    fit = _fit_isotonic(training)
    predictions = [_apply_calibration(x / 100.0, fit) for x in range(1, 100)]
    assert predictions == sorted(predictions)


def test_score_settlement_is_checked_against_market():
    bad = row(3, final_home_score=0, final_away_score=0)
    result = evaluate_dataset([bad, row(3, final_home_score=None)], min_train=2, min_test=2)
    assert result["rejected_records_by_reason"]["SETTLEMENT_MISMATCH"] == 1
    assert result["rejected_records_by_reason"]["MISSING_FINAL_SCORE"] == 1


def test_next_15_market_does_not_confuse_final_score_with_window_goals():
    invalid = row(2, market="OVER_NEXT_15_DYNAMIC", period="NEXT_15")
    valid = row(3, market="OVER_NEXT_15_DYNAMIC", period="NEXT_15",
                label_source="OFFICIAL_SETTLEMENT", settlement_rule_id="provider:next15_v1",
                line=0.5, verified_window_goals=1)
    result = evaluate_dataset([invalid, valid], min_train=2, min_test=2)
    assert result["accepted_records"] == 1
    assert result["rejected_records_by_reason"]["WINDOW_SETTLEMENT_UNVERIFIED"] == 1
