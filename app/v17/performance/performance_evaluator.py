from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable

from app.v17.performance.performance_constants import (
    CONFIDENCE_BUCKETS,
    DATA_QUALITY_UNKNOWN,
    PERFORMANCE_CAN_PUBLISH,
    PERFORMANCE_IS_OFFICIAL_DECISION,
    PERFORMANCE_ROLE,
    RESULT_CANCELLED,
    RESULT_EXPIRED,
    RESULT_LOST,
    RESULT_PENDING,
    RESULT_UNKNOWN,
    RESULT_VOID,
    RESULT_WON,
)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


class PerformanceMetrics:
    """
    Métricas puras de rendimiento.

    No decide.
    No publica.
    No modifica official_*.
    """

    @staticmethod
    def evaluation_header() -> Dict[str, Any]:
        return {
            "performance_role": PERFORMANCE_ROLE,
            "performance_is_official_decision": PERFORMANCE_IS_OFFICIAL_DECISION,
            "performance_can_publish": PERFORMANCE_CAN_PUBLISH,
        }

    @staticmethod
    def normalize_result(value: Any) -> str:
        status = safe_str(value, RESULT_UNKNOWN).upper()
        if status in {RESULT_WON, "WIN", "ACERTADA"}:
            return RESULT_WON
        if status in {RESULT_LOST, "LOSS", "FALLIDA"}:
            return RESULT_LOST
        if status in {RESULT_VOID, "PUSH", "ANULADA"}:
            return RESULT_VOID
        if status in {RESULT_PENDING, "OPEN", "PENDIENTE"}:
            return RESULT_PENDING
        if status in {RESULT_EXPIRED, "EXPIRE", "EXPIRADA"}:
            return RESULT_EXPIRED
        if status in {RESULT_CANCELLED, "CANCELED", "CANCELADA"}:
            return RESULT_CANCELLED
        return RESULT_UNKNOWN

    @staticmethod
    def normalize_market(value: Any) -> str:
        market = safe_str(value, "UNKNOWN").upper()
        if "OVER" in market:
            return "OVER"
        if "UNDER" in market:
            return "UNDER"
        if market in {"NO_BET", "WAIT", "OBSERVE", "BLOCKED"}:
            return market
        return market or "UNKNOWN"

    @staticmethod
    def minute_bucket(minute: Any) -> str:
        minute = safe_int(minute, -1)
        if minute < 0:
            return "UNKNOWN"
        if minute <= 15:
            return "M00_15"
        if minute <= 30:
            return "M16_30"
        if minute <= 45:
            return "M31_45"
        if minute <= 60:
            return "M46_60"
        if minute <= 75:
            return "M61_75"
        if minute <= 90:
            return "M76_90"
        return "M90_PLUS"

    @staticmethod
    def confidence_bucket(confidence: Any) -> str:
        value = safe_float(confidence, -1.0)
        if value < 0:
            return "UNKNOWN"
        if value <= 1.0:
            value *= 100.0
        if value < 40:
            return "C00_39"
        if value < 50:
            return "C40_49"
        if value < 60:
            return "C50_59"
        if value < 70:
            return "C60_69"
        if value < 80:
            return "C70_79"
        if value < 90:
            return "C80_89"
        return "C90_100"

    @staticmethod
    def empty_counter() -> Dict[str, Any]:
        return {
            "sample_count": 0,
            "decided": 0,
            "won": 0,
            "lost": 0,
            "void": 0,
            "pending": 0,
            "expired": 0,
            "cancelled": 0,
            "unknown": 0,
            "precision": 0.0,
        }

    @classmethod
    def calculate_precision(cls, won: int, lost: int) -> float:
        decided = won + lost
        if decided <= 0:
            return 0.0
        return round((won / decided) * 100.0, 2)

    @classmethod
    def global_metrics(cls, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        counter = cls.empty_counter()
        for record in records:
            cls._add_record(counter, record)
        cls._finalize_counter(counter)
        return {**cls.evaluation_header(), "metric_type": "GLOBAL", **counter}

    @classmethod
    def group_metrics(
        cls,
        records: Iterable[Dict[str, Any]],
        field: str,
        default_key: str = "UNKNOWN",
    ) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = defaultdict(cls.empty_counter)
        for record in records:
            key = safe_str(record.get(field), default_key).upper() or default_key
            cls._add_record(grouped[key], record)
        result = {}
        for key, counter in grouped.items():
            cls._finalize_counter(counter)
            result[key] = {**cls.evaluation_header(), "metric_type": field.upper(), "group_key": key, **counter}
        return dict(sorted(result.items(), key=lambda item: item[0]))

    @classmethod
    def confidence_calibration(cls, records: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                **cls.empty_counter(),
                "confidence_sum": 0.0,
                "confidence_count": 0,
                "avg_official_confidence": 0.0,
                "calibration_gap": 0.0,
            }
        )
        for record in records:
            bucket = safe_str(record.get("official_confidence_bucket"), "UNKNOWN")
            if bucket not in CONFIDENCE_BUCKETS:
                bucket = "UNKNOWN"
            counter = grouped[bucket]
            cls._add_record(counter, record)
            confidence = safe_float(record.get("official_confidence"), -1.0)
            if confidence >= 0:
                if confidence <= 1.0:
                    confidence *= 100.0
                counter["confidence_sum"] += confidence
                counter["confidence_count"] += 1
        result = {}
        for bucket, counter in grouped.items():
            cls._finalize_counter(counter)
            if counter["confidence_count"] > 0:
                counter["avg_official_confidence"] = round(counter["confidence_sum"] / counter["confidence_count"], 2)
            counter["calibration_gap"] = round(counter["precision"] - counter["avg_official_confidence"], 2)
            counter.pop("confidence_sum", None)
            counter.pop("confidence_count", None)
            result[bucket] = {**cls.evaluation_header(), "metric_type": "OFFICIAL_CONFIDENCE", "group_key": bucket, **counter}
        return {bucket: result.get(bucket, {**cls.evaluation_header(), "metric_type": "OFFICIAL_CONFIDENCE", "group_key": bucket, **cls.empty_counter(), "avg_official_confidence": 0.0, "calibration_gap": 0.0}) for bucket in CONFIDENCE_BUCKETS}

    @classmethod
    def _add_record(cls, counter: Dict[str, Any], record: Dict[str, Any]) -> None:
        status = cls.normalize_result(record.get("result_status"))
        counter["sample_count"] += 1
        if status == RESULT_WON:
            counter["won"] += 1
        elif status == RESULT_LOST:
            counter["lost"] += 1
        elif status == RESULT_VOID:
            counter["void"] += 1
        elif status == RESULT_PENDING:
            counter["pending"] += 1
        elif status == RESULT_EXPIRED:
            counter["expired"] += 1
        elif status == RESULT_CANCELLED:
            counter["cancelled"] += 1
        else:
            counter["unknown"] += 1

    @classmethod
    def _finalize_counter(cls, counter: Dict[str, Any]) -> None:
        counter["decided"] = counter["won"] + counter["lost"]
        counter["precision"] = cls.calculate_precision(counter["won"], counter["lost"])

    @classmethod
    def normalize_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(record or {})
        normalized["market"] = cls.normalize_market(normalized.get("official_market") or normalized.get("market"))
        normalized["league"] = safe_str(normalized.get("league"), "UNKNOWN")
        normalized["minute_bucket"] = safe_str(normalized.get("minute_bucket") or cls.minute_bucket(normalized.get("entry_minute")), "UNKNOWN")
        normalized["data_source_quality"] = safe_str(normalized.get("data_source_quality"), DATA_QUALITY_UNKNOWN).upper() or DATA_QUALITY_UNKNOWN
        normalized["official_confidence_bucket"] = safe_str(normalized.get("official_confidence_bucket") or cls.confidence_bucket(normalized.get("official_confidence")), "UNKNOWN")
        normalized["result_status"] = cls.normalize_result(normalized.get("result_status"))
        return normalized
