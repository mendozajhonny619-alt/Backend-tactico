from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.v17.performance.performance_constants import (
    DEFAULT_DB_PATH,
    PERFORMANCE_CAN_PUBLISH,
    PERFORMANCE_IS_OFFICIAL_DECISION,
    PERFORMANCE_ROLE,
    PERFORMANCE_VERSION,
)
from app.v17.performance.performance_history import PerformanceHistory
from app.v17.performance.performance_metrics import PerformanceMetrics


class PerformanceEvaluator:
    """
    PerformanceEvaluator V17.

    Rol:
    - OFFLINE/PASSIVE.
    - EVALUATION_ONLY.
    - No decide.
    - No publica.
    - No modifica official_*.
    - No toca MasterDecisionAI.
    """

    VERSION = PERFORMANCE_VERSION

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.history = PerformanceHistory(db_path=db_path)

    def record_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        result = self.history.upsert_signal(signal)
        return self._wrap_result(result)

    def record_result(self, result_payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.history.record_result(result_payload)
        return self._wrap_result(result)

    def evaluate(self, records: Optional[List[Dict[str, Any]]] = None, include_pending: bool = True) -> Dict[str, Any]:
        if records is None:
            records = self.history.list_signals(include_pending=include_pending)
        normalized = [PerformanceMetrics.normalize_record(record) for record in records if isinstance(record, dict)]
        return {
            **self._header(),
            "version": self.VERSION,
            "sample_count": len(normalized),
            "global": self.calculate_global_precision(normalized),
            "by_market": self.calculate_precision_by_market(normalized),
            "by_league": self.calculate_precision_by_league(normalized),
            "by_minute": self.calculate_precision_by_minute(normalized),
            "by_data_source_quality": self.calculate_precision_by_data_source_quality(normalized),
            "official_confidence_calibration": self.calculate_official_confidence_calibration(normalized),
        }

    def calculate_global_precision(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        return PerformanceMetrics.global_metrics(self._records(records))

    def calculate_precision_by_market(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        return PerformanceMetrics.group_metrics(records=self._records(records), field="market", default_key="UNKNOWN")

    def calculate_precision_by_league(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        return PerformanceMetrics.group_metrics(records=self._records(records), field="league", default_key="UNKNOWN")

    def calculate_precision_by_minute(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        return PerformanceMetrics.group_metrics(records=self._records(records), field="minute_bucket", default_key="UNKNOWN")

    def calculate_precision_by_data_source_quality(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        return PerformanceMetrics.group_metrics(records=self._records(records), field="data_source_quality", default_key="UNKNOWN")

    def calculate_official_confidence_calibration(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
        return PerformanceMetrics.confidence_calibration(self._records(records))

    def list_records(self, include_pending: bool = True, limit: int = 5000) -> Dict[str, Any]:
        records = self.history.list_signals(include_pending=include_pending, limit=limit)
        return {**self._header(), "records": records, "count": len(records)}

    def _records(self, records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        if records is None:
            records = self.history.list_signals(include_pending=True)
        return [PerformanceMetrics.normalize_record(record) for record in records if isinstance(record, dict)]

    def _wrap_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {**self._header(), **(result or {})}

    def _header(self) -> Dict[str, Any]:
        return {
            "performance_role": PERFORMANCE_ROLE,
            "performance_is_official_decision": PERFORMANCE_IS_OFFICIAL_DECISION,
            "performance_can_publish": PERFORMANCE_CAN_PUBLISH,
        }
