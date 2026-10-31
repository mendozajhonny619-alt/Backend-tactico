"""Offline chronological calibration lab for binary soccer markets (V3.5).

No API calls, odds requests, or production activation. A candidate calibration
is an analytical artifact requiring independent review. Only predictions
recorded before their verified outcome are admitted. Scores / confidence /
heuristic candidate ranks are not interchangeable with event probabilities.

Usage:
  python -m app.v17.ai.calibration_lab resolved_predictions.jsonl --out calibration_report.json
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ACCEPTED_MARKETS = {"OVER_MATCH_DYNAMIC", "UNDER_MATCH_DYNAMIC", "OVER_NEXT_15_DYNAMIC", "OVER", "UNDER"}
ACCEPTED_LABEL_SOURCES = {"FINAL_SCORE", "OFFICIAL_SETTLEMENT", "PROVIDER_EVENTS", "MANUALLY_VERIFIED"}


def _time(value: Any) -> datetime:
    if not value:
        raise ValueError("MISSING_TIMESTAMP")
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc
    if dt.tzinfo is None:
        raise ValueError("NAIVE_TIMESTAMP")
    return dt.astimezone(timezone.utc)


def _probability(value: Any) -> float:
    if value is None or value == "":
        raise ValueError("MISSING_EVENT_PROBABILITY")
    try:
        p = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("INVALID_EVENT_PROBABILITY") from exc
    if not math.isfinite(p) or not 0 <= p <= 100:
        raise ValueError("INVALID_EVENT_PROBABILITY")
    if p > 1:
        p /= 100.0
    return p


@dataclass(frozen=True)
class LabeledForecast:
    fixture_id: str
    episode_id: str
    market: str
    period: str
    line: float
    model_version: str
    predicted_at: datetime
    resolved_at: datetime
    p: float
    actual: int

    @property
    def group_key(self) -> Tuple[str, str, str]:
        return self.model_version, self.market, self.period


def parse_record(item: Dict[str, Any]) -> LabeledForecast:
    """Reject unknown events, unsupported lines and result-time leakage."""
    if not isinstance(item, dict):
        raise ValueError("NOT_AN_OBJECT")
    fixture = str(item.get("fixture_id") or "").strip()
    if not fixture:
        raise ValueError("MISSING_FIXTURE_ID")
    market = str(item.get("market") or "").upper().strip()
    if market not in ACCEPTED_MARKETS:
        raise ValueError("UNSUPPORTED_MARKET")
    period = str(item.get("period") or ("NEXT_15" if "NEXT_15" in market else "FT")).upper().strip()
    if period not in {"FT", "NEXT_15"}:
        raise ValueError("UNSUPPORTED_PERIOD")
    if ("NEXT_15" in market) != (period == "NEXT_15"):
        raise ValueError("MARKET_PERIOD_MISMATCH")
    model_version = str(item.get("model_version") or "").strip()
    if not model_version:
        raise ValueError("MISSING_MODEL_VERSION")
    try:
        line = float(item.get("line"))
    except (ValueError, TypeError) as exc:
        raise ValueError("MISSING_MARKET_LINE") from exc
    if not math.isfinite(line) or line <= 0 or not math.isclose(line % 1, 0.5, abs_tol=1e-6):
        raise ValueError("UNSUPPORTED_MARKET_LINE")
    source = str(item.get("label_source") or "").upper().strip()
    if source not in ACCEPTED_LABEL_SOURCES:
        raise ValueError("UNVERIFIED_OUTCOME_SOURCE")
    status = str(item.get("result_status") or "").upper().strip()
    if status not in {"WON", "LOST"}:
        raise ValueError("UNSETTLED_OUTCOME")
    p = _probability(item.get("model_probability"))
    predicted = _time(item.get("predicted_at"))
    resolved = _time(item.get("resolved_at"))
    if predicted >= resolved:
        raise ValueError("FUTURE_DATA_LEAKAGE")
    # Independent label verification against the contractual half-goal line.
    # A row claiming WON cannot contradict the final score it carries.
    if period == "FT" and source == "FINAL_SCORE":
        try:
            final_home = int(item["final_home_score"])
            final_away = int(item["final_away_score"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("MISSING_FINAL_SCORE") from exc
        if min(final_home, final_away) < 0:
            raise ValueError("INVALID_FINAL_SCORE")
        total = final_home + final_away
        won = total > line if market.startswith("OVER") else total < line
        if (status == "WON") != won:
            raise ValueError("SETTLEMENT_MISMATCH")
    if period == "NEXT_15":
        # This is a different settlement contract than full-time totals.
        # We accept it only with explicitly labeled, independently verified
        # window goals; FT scores cannot prove a NEXT_15 outcome.
        if source != "OFFICIAL_SETTLEMENT" or not item.get("settlement_rule_id"):
            raise ValueError("WINDOW_SETTLEMENT_UNVERIFIED")
        try:
            goals = int(item["verified_window_goals"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("MISSING_WINDOW_GOALS") from exc
        if goals < 0 or (status == "WON") != (goals > line if market.startswith("OVER") else goals < line):
            raise ValueError("WINDOW_SETTLEMENT_MISMATCH")
    return LabeledForecast(
        fixture_id=fixture,
        episode_id=str(item.get("episode_id") or "0"),
        market=market,
        period=period,
        line=line,
        model_version=model_version,
        predicted_at=predicted,
        resolved_at=resolved,
        p=p,
        actual=1 if status == "WON" else 0,
    )


def _metrics(rows: Sequence[LabeledForecast], predicted: Sequence[float]) -> Dict[str, Any]:
    if not rows:
        return {"samples": 0, "brier_score": None, "log_loss": None, "ece_10_bins": None}
    labels = [r.actual for r in rows]
    pairs = [(max(1e-6, min(1 - 1e-6, p)), y) for p, y in zip(predicted, labels)]
    brier = sum((p - y) ** 2 for p, y in pairs) / len(pairs)
    logloss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for p, y in pairs) / len(pairs)
    buckets: Dict[int, List[Tuple[float, int]]] = defaultdict(list)
    for p, y in pairs:
        buckets[min(9, int(p * 10))].append((p, y))
    ece = sum(
        (len(batch) / len(pairs)) * abs(sum(p for p, _ in batch) / len(batch) - sum(y for _, y in batch) / len(batch))
        for batch in buckets.values()
    )
    return {"samples": len(rows), "brier_score": round(brier, 6),
            "log_loss": round(logloss, 6), "ece_10_bins": round(ece, 6)}


def _fit_isotonic(rows: Sequence[LabeledForecast]) -> Dict[str, Any]:
    # Pool Adjacent Violators: fit ONLY on past matches. The stepwise mapping
    # is stored as a candidate and may not enter production automatically.
    sorted_rows = sorted(rows, key=lambda row: row.p)
    blocks: List[Dict[str, Any]] = []
    for r in sorted_rows:
        if blocks and blocks[-1]["upper"] == r.p:
            blocks[-1]["positive"] += r.actual
            blocks[-1]["count"] += 1
        else:
            blocks.append({"upper": r.p, "positive": r.actual, "count": 1})
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            if left["positive"] / left["count"] <= right["positive"] / right["count"]:
                break
            blocks[-2:] = [{"upper": right["upper"],
                            "positive": left["positive"] + right["positive"],
                            "count": left["count"] + right["count"]}]
    return {"method": "ISOTONIC_PAV", "steps": [
        {"upper": round(b["upper"], 8),
         "calibrated": round(max(0.001, min(0.999, b["positive"] / b["count"])), 8),
         "samples": b["count"]} for b in blocks
    ]}


def _apply_calibration(p: float, fit: Dict[str, Any]) -> float:
    steps = fit["steps"]
    i = min(len(steps) - 1, bisect_left([s["upper"] for s in steps], p))
    return float(steps[i]["calibrated"])


def _assess_group(
    rows: Sequence[LabeledForecast], *, min_train: int, min_test: int, holdout: float,
) -> Dict[str, Any]:
    # All snapshots belonging to one fixture stay in the SAME split. A
    # training outcome must already be available before the first test input.
    first_by_fixture: Dict[str, datetime] = {}
    for r in rows:
        first_by_fixture[r.fixture_id] = min(first_by_fixture.get(r.fixture_id, r.predicted_at), r.predicted_at)
    fixtures = sorted(first_by_fixture, key=lambda x: (first_by_fixture[x], x))
    if len(fixtures) < 2:
        return {"status": "INSUFFICIENT_DATA", "reason": "NOT_ENOUGH_INDEPENDENT_FIXTURES",
                "total_records": len(rows), "unique_fixtures": len(fixtures), "approved_for_production": False}
    split = max(1, min(len(fixtures) - 1, int(len(fixtures) * (1 - holdout))))
    cutoff = first_by_fixture[fixtures[split]]
    train_ids = set(fixtures[:split]); test_ids = set(fixtures[split:])
    train = [r for r in rows if r.fixture_id in train_ids and r.resolved_at < cutoff]
    test = [r for r in rows if r.fixture_id in test_ids and r.predicted_at >= cutoff]
    report: Dict[str, Any] = {
        "total_records": len(rows), "unique_fixtures": len(fixtures),
        "train_records": len(train), "test_records": len(test),
        "train_fixtures": len({r.fixture_id for r in train}),
        "test_fixtures": len({r.fixture_id for r in test}),
        "test_start_utc": cutoff.isoformat(),
        "records_excluded_by_time_embargo": len(rows) - len(train) - len(test),
        "approved_for_production": False,
    }
    if (len(train) < min_train or len(test) < min_test
            or report["train_fixtures"] < min_train
            or report["test_fixtures"] < min_test):
        return {**report, "status": "INSUFFICIENT_DATA", "reason": "NOT_ENOUGH_CHRONOLOGICAL_LABELED_FIXTURES"}
    fit = _fit_isotonic(train)
    base_rate = sum(x.actual for x in train) / len(train)
    raw = _metrics(test, [r.p for r in test])
    calibrated = _metrics(test, [_apply_calibration(r.p, fit) for r in test])
    trivial_baseline = _metrics(test, [base_rate] * len(test))
    fit_improves = bool(
        calibrated["brier_score"] < raw["brier_score"]
        and calibrated["brier_score"] < trivial_baseline["brier_score"]
        and calibrated["log_loss"] <= raw["log_loss"]
    )
    status = "CANDIDATE_FOR_REVIEW" if fit_improves else "REJECTED_OUT_OF_SAMPLE"
    return {**report, "status": status,
            "reason": "OFFLINE_REVIEW_REQUIRED" if fit_improves else "NO_HOLDOUT_IMPROVEMENT",
            "raw_holdout": raw, "candidate_holdout": calibrated,
            "constant_rate_baseline_holdout": trivial_baseline,
            "train_event_rate": round(base_rate, 6),
            "candidate_mapping": fit if fit_improves else None,
            "review_required": True}


def evaluate_dataset(
    records: Iterable[Dict[str, Any]], *, min_train: int = 200,
    min_test: int = 100, holdout: float = 0.25,
) -> Dict[str, Any]:
    if min_train < 2 or min_test < 2 or not 0.1 <= holdout <= 0.5:
        raise ValueError("INVALID_MINIMUMS_OR_HOLDOUT")
    accepted: List[LabeledForecast] = []
    rejected: Dict[str, int] = defaultdict(int)
    seen: set[Tuple[Any, ...]] = set()
    total = 0
    for raw in records:
        total += 1
        try:
            row = parse_record(raw)
        except ValueError as exc:
            rejected[str(exc)] += 1
            continue
        key = (row.fixture_id, row.episode_id, row.market, row.period, row.line,
               row.model_version, row.predicted_at)
        if key in seen:
            rejected["DUPLICATE_EVENT"] += 1
            continue
        seen.add(key)
        accepted.append(row)
    groups: Dict[Tuple[str, str, str], List[LabeledForecast]] = defaultdict(list)
    for row in accepted:
        groups[row.group_key].append(row)
    return {
        "lab_version": "JE_CALIBRATION_LAB_V3_5",
        "production_calibration_status": "NOT_VALIDATED_OUT_OF_SAMPLE",
        "auto_activation": False,
        "input_records": total,
        "accepted_records": len(accepted),
        "rejected_records_by_reason": dict(sorted(rejected.items())),
        "group_reports": [
            {"model_version": key[0], "market": key[1], "period": key[2],
             **_assess_group(rows, min_train=min_train, min_test=min_test, holdout=holdout)}
            for key, rows in sorted(groups.items())
        ],
        "limitations": [
            "Results require actual outcomes and exact market settlement rules.",
            "Model and calibration are not approved for live use automatically.",
            "Overlapping forecasts from one fixture are correlated; independent fixtures are counted separately.",
            "A model/line/horizon subgroup may remain underpowered even when a general group passes.",
        ],
    }


def read_jsonl(path: Path, *, max_lines: int = 200_000) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= max_lines:
                raise ValueError("INPUT_FILE_TOO_LARGE_FOR_LOCAL_EVALUATION")
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                value = {"invalid_json": True}
            rows.append(value)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate historical soccer forecasts offline (never activates production).")
    parser.add_argument("input", type=Path, help="JSONL with verified outcomes and timestamps")
    parser.add_argument("--out", type=Path, help="Optional path for the JSON review report")
    parser.add_argument("--min-train", type=int, default=200)
    parser.add_argument("--min-test", type=int, default=100)
    args = parser.parse_args()
    result = evaluate_dataset(read_jsonl(args.input), min_train=args.min_train, min_test=args.min_test)
    formatted = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(formatted + "\n", encoding="utf-8")
    print(formatted)


if __name__ == "__main__":
    main()
