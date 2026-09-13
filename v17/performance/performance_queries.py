from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from app.v17.performance.performance_constants import (
        DEFAULT_DB_PATH,
        PERFORMANCE_CAN_PUBLISH,
        PERFORMANCE_IS_OFFICIAL_DECISION,
        PERFORMANCE_ROLE,
        RESULT_LOST,
        RESULT_PENDING,
        RESULT_VOID,
        RESULT_WON,
    )
except Exception:
    DEFAULT_DB_PATH = "app/v17/storage/performance.db"
    PERFORMANCE_ROLE = "EVALUATION_ONLY"
    PERFORMANCE_IS_OFFICIAL_DECISION = False
    PERFORMANCE_CAN_PUBLISH = False
    RESULT_WON = "WON"
    RESULT_LOST = "LOST"
    RESULT_VOID = "VOID"
    RESULT_PENDING = "PENDING"


RESULT_EXPIRED = "EXPIRED"
RESULT_CANCELLED = "CANCELLED"
RESULT_UNKNOWN = "UNKNOWN"
DECIDED_RESULTS = {RESULT_WON, RESULT_LOST}


class PerformanceQueries:
    """
    Read-only reporting query layer for performance.db.

    This module is intentionally tolerant of schema differences between:
    - Fase 5.1 PerformanceHistory
    - Fase 5.2 PerformanceImporter
    - future passive/offline performance schemas

    It never imports MasterDecisionAI, never calls LiveSignalEngine,
    never publishes, and never mutates official_* fields.
    """

    ROLE = PERFORMANCE_ROLE

    SIGNAL_TABLE_CANDIDATES = (
        "performance_signals",
        "signals",
        "signal_performance",
        "performance_signal_history",
    )
    EVENT_TABLE_CANDIDATES = (
        "performance_events",
        "events",
        "performance_import_log",
    )

    FIELD_ALIASES = {
        "signal_key": (
            "signal_key",
            "signal_id",
            "id",
            "candidate_id",
            "source_id",
        ),
        "fixture_id": (
            "fixture_id",
            "match_id",
            "api_fixture_id",
            "game_id",
        ),
        "home_team": (
            "home_team",
            "home",
            "home_name",
            "homeTeam",
        ),
        "away_team": (
            "away_team",
            "away",
            "away_name",
            "awayTeam",
        ),
        "league": (
            "league",
            "league_name",
            "competition",
            "competition_name",
            "tournament",
        ),
        "country": (
            "country",
            "country_name",
        ),
        "market": (
            "market",
            "official_market",
            "signal_market",
            "suggested_market",
            "prediction_market",
        ),
        "official_market": (
            "official_market",
            "market",
            "signal_market",
            "suggested_market",
            "prediction_market",
        ),
        "official_status": (
            "official_status",
            "status",
            "signal_status",
            "decision_status",
        ),
        "official_can_publish": (
            "official_can_publish",
            "can_publish",
            "publishable",
        ),
        "official_confidence": (
            "official_confidence",
            "confidence",
            "master_confidence",
            "signal_confidence",
        ),
        "official_confidence_bucket": (
            "official_confidence_bucket",
            "confidence_bucket",
        ),
        "entry_minute": (
            "entry_minute",
            "minute",
            "api_minute",
            "display_minute",
            "match_minute",
            "elapsed",
        ),
        "minute_bucket": (
            "minute_bucket",
            "entry_minute_bucket",
            "match_minute_bucket",
        ),
        "entry_scoreline": (
            "entry_scoreline",
            "scoreline",
            "score",
            "current_score",
        ),
        "final_scoreline": (
            "final_scoreline",
            "final_score",
            "fulltime_score",
        ),
        "result_status": (
            "result_status",
            "tracking_status",
            "final_result",
            "resolution",
            "outcome",
            "signal_result",
        ),
        "result_reason": (
            "result_reason",
            "resolution_reason",
            "reason",
        ),
        "data_source_quality": (
            "data_source_quality",
            "data_quality",
            "source_quality",
            "stats_quality",
        ),
        "stats_completeness_score": (
            "stats_completeness_score",
            "completeness_score",
            "stats_completeness",
        ),
        "pre_match_expectation": (
            "pre_match_expectation",
            "prematch_expectation",
        ),
        "live_reality": (
            "live_reality",
            "reality_status",
        ),
        "reality_confidence": (
            "reality_confidence",
            "live_reality_confidence",
        ),
        "football_memory_available": (
            "football_memory_available",
            "memory_available",
        ),
        "football_memory_confidence": (
            "football_memory_confidence",
            "memory_confidence",
        ),
        "payload_json": (
            "payload_json",
            "raw_payload",
            "payload",
            "data",
        ),
    }

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)

    def evaluation_header(self) -> Dict[str, Any]:
        return {
            "performance_role": PERFORMANCE_ROLE,
            "performance_is_official_decision": PERFORMANCE_IS_OFFICIAL_DECISION,
            "performance_can_publish": PERFORMANCE_CAN_PUBLISH,
            "evaluation_only": True,
        }

    def database_exists(self) -> bool:
        return self.db_path.exists()

    def list_tables(self) -> List[str]:
        if not self.database_exists():
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            return [str(row["name"]) for row in rows]
        except Exception:
            return []

    def table_exists(self, table_name: str) -> bool:
        return table_name in set(self.list_tables())

    def get_columns(self, table_name: str) -> List[str]:
        if not self.table_exists(table_name):
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"PRAGMA table_info({self._quote_identifier(table_name)})"
                ).fetchall()
            return [str(row["name"]) for row in rows]
        except Exception:
            return []

    def detect_signal_table(self) -> Optional[str]:
        tables = set(self.list_tables())
        for table in self.SIGNAL_TABLE_CANDIDATES:
            if table in tables:
                return table
        return None

    def detect_event_tables(self) -> List[str]:
        tables = set(self.list_tables())
        return [table for table in self.EVENT_TABLE_CANDIDATES if table in tables]

    def fetch_signals(self, limit: int = 100000) -> List[Dict[str, Any]]:
        table = self.detect_signal_table()
        if not table:
            return []

        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"SELECT * FROM {self._quote_identifier(table)} LIMIT ?",
                    (limit,),
                ).fetchall()
        except Exception:
            return []

        return [self.normalize_signal(self._row_to_dict(row)) for row in rows]

    def fetch_events(self, limit: int = 100000) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for table in self.detect_event_tables():
            try:
                with self._connect() as conn:
                    rows = conn.execute(
                        f"SELECT * FROM {self._quote_identifier(table)} LIMIT ?",
                        (limit,),
                    ).fetchall()
                for row in rows:
                    item = self._row_to_dict(row)
                    item["_source_table"] = table
                    events.append(item)
            except Exception:
                continue
        return events

    def full_metrics(self) -> Dict[str, Any]:
        signals = self.fetch_signals()
        evaluable = [
            row for row in signals if row.get("result_status") in DECIDED_RESULTS
        ]

        by_market = self.group_accuracy(evaluable, "market")
        by_league = self.group_accuracy(evaluable, "league")
        by_minute = self.group_accuracy(evaluable, "minute_bucket")
        by_data_quality = self.group_accuracy(evaluable, "data_source_quality")
        confidence = self.confidence_calibration(evaluable)

        return {
            **self.evaluation_header(),
            "db_path": str(self.db_path),
            "database_exists": self.database_exists(),
            "tables": self.list_tables(),
            "signal_table": self.detect_signal_table(),
            "event_tables": self.detect_event_tables(),
            "total_signals": len(signals),
            "evaluable_signals": len(evaluable),
            "pending_signals": len(
                [s for s in signals if s.get("result_status") == RESULT_PENDING]
            ),
            "void_signals": len(
                [s for s in signals if s.get("result_status") == RESULT_VOID]
            ),
            "global_accuracy": self.metrics_for_rows(evaluable, label="GLOBAL"),
            "by_market": by_market,
            "by_league": by_league,
            "by_minute": by_minute,
            "by_data_source_quality": by_data_quality,
            "confidence_calibration": confidence,
            "best_markets": self.best_groups(by_market),
            "worst_markets": self.worst_groups(by_market),
            "best_leagues": self.best_groups(by_league),
            "dangerous_leagues": self.worst_groups(by_league),
            "strong_minutes": self.best_groups(by_minute),
            "weak_minutes": self.worst_groups(by_minute),
        }

    def group_accuracy(
        self,
        rows: Iterable[Dict[str, Any]],
        field: str,
    ) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            key = self.safe_str(row.get(field), "UNKNOWN").upper() or "UNKNOWN"
            groups.setdefault(key, []).append(row)

        result = [
            self.metrics_for_rows(items, label=key)
            for key, items in groups.items()
        ]
        result.sort(
            key=lambda item: (
                -item["sample_count"],
                -item["precision"],
                item["label"],
            )
        )
        return result

    def metrics_for_rows(
        self,
        rows: Iterable[Dict[str, Any]],
        label: str,
    ) -> Dict[str, Any]:
        sample_count = 0
        won = 0
        lost = 0
        void = 0
        pending = 0
        expired = 0
        cancelled = 0
        unknown = 0

        for row in rows:
            sample_count += 1
            status = self.normalize_result(row.get("result_status"))

            if status == RESULT_WON:
                won += 1
            elif status == RESULT_LOST:
                lost += 1
            elif status == RESULT_VOID:
                void += 1
            elif status == RESULT_PENDING:
                pending += 1
            elif status == RESULT_EXPIRED:
                expired += 1
            elif status == RESULT_CANCELLED:
                cancelled += 1
            else:
                unknown += 1

        decided = won + lost
        precision = round((won / decided) * 100.0, 2) if decided else 0.0

        return {
            **self.evaluation_header(),
            "label": label,
            "group_key": label,
            "sample_count": sample_count,
            "total": sample_count,
            "decided": decided,
            "won": won,
            "lost": lost,
            "void": void,
            "pending": pending,
            "expired": expired,
            "cancelled": cancelled,
            "unknown": unknown,
            "precision": precision,
            "accuracy_pct": precision,
        }

    def confidence_calibration(
        self,
        rows: Iterable[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for row in rows:
            bucket = self.safe_str(
                row.get("official_confidence_bucket")
                or self.confidence_bucket(row.get("official_confidence")),
                "UNKNOWN",
            ).upper()
            groups.setdefault(bucket, []).append(row)

        result = []

        for bucket, items in groups.items():
            base = self.metrics_for_rows(items, label=bucket)
            confidences = []

            for item in items:
                confidence = self.safe_float(item.get("official_confidence"), None)

                if confidence is None:
                    continue

                if confidence <= 1.0:
                    confidence *= 100.0

                confidences.append(confidence)

            avg_confidence = (
                round(sum(confidences) / len(confidences), 2)
                if confidences
                else 0.0
            )
            base["avg_official_confidence"] = avg_confidence
            base["calibration_gap"] = round(base["precision"] - avg_confidence, 2)
            result.append(base)

        result.sort(key=lambda item: item["label"])
        return result

    def best_groups(
        self,
        rows: List[Dict[str, Any]],
        min_samples: int = 5,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        filtered = [
            row
            for row in rows
            if int(row.get("decided") or row.get("sample_count") or 0) >= min_samples
        ]
        filtered.sort(
            key=lambda item: (
                -float(item.get("precision", 0.0)),
                -int(item.get("decided", 0)),
                item["label"],
            )
        )
        return filtered[:limit]

    def worst_groups(
        self,
        rows: List[Dict[str, Any]],
        min_samples: int = 5,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        filtered = [
            row
            for row in rows
            if int(row.get("decided") or row.get("sample_count") or 0) >= min_samples
        ]
        filtered.sort(
            key=lambda item: (
                float(item.get("precision", 0.0)),
                -int(item.get("decided", 0)),
                item["label"],
            )
        )
        return filtered[:limit]

    def normalize_signal(self, row: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.parse_json_if_needed(self.alias_value(row, "payload_json"))
        merged: Dict[str, Any] = {}

        if isinstance(payload, dict):
            merged.update(payload)

        merged.update(row)

        reality = merged.get("pre_match_live_reality")
        if not isinstance(reality, dict):
            reality = self.parse_json_if_needed(reality)

        if isinstance(reality, dict):
            merged.setdefault(
                "pre_match_expectation",
                reality.get("pre_match_expectation"),
            )
            merged.setdefault("live_reality", reality.get("live_reality"))
            merged.setdefault(
                "reality_confidence",
                reality.get("reality_confidence"),
            )

        memory = merged.get("football_memory_context")
        if not isinstance(memory, dict):
            memory = self.parse_json_if_needed(memory)

        if isinstance(memory, dict):
            merged.setdefault(
                "football_memory_available",
                memory.get("memory_available"),
            )
            merged.setdefault(
                "football_memory_confidence",
                memory.get("memory_confidence"),
            )

        normalized = dict(merged)
        normalized["signal_key"] = self.safe_str(
            self.alias_value(merged, "signal_key")
        )
        normalized["fixture_id"] = self.safe_str(
            self.alias_value(merged, "fixture_id")
        )
        normalized["home_team"] = self.safe_str(
            self.alias_value(merged, "home_team")
        )
        normalized["away_team"] = self.safe_str(
            self.alias_value(merged, "away_team")
        )
        normalized["league"] = (
            self.safe_str(self.alias_value(merged, "league"), "UNKNOWN")
            or "UNKNOWN"
        )
        normalized["country"] = (
            self.safe_str(self.alias_value(merged, "country"), "UNKNOWN")
            or "UNKNOWN"
        )
        normalized["market"] = self.normalize_market(
            self.alias_value(merged, "market")
        )
        normalized["official_market"] = self.normalize_market(
            self.alias_value(merged, "official_market")
        )
        normalized["official_status"] = self.safe_str(
            self.alias_value(merged, "official_status")
        )
        normalized["official_can_publish"] = self.safe_bool(
            self.alias_value(merged, "official_can_publish")
        )
        normalized["official_confidence"] = self.safe_float(
            self.alias_value(merged, "official_confidence"),
            0.0,
        )
        normalized["official_confidence_bucket"] = self.safe_str(
            self.alias_value(merged, "official_confidence_bucket")
            or self.confidence_bucket(normalized["official_confidence"]),
            "UNKNOWN",
        )
        normalized["entry_minute"] = self.safe_int(
            self.alias_value(merged, "entry_minute"),
            0,
        )
        normalized["minute_bucket"] = self.safe_str(
            self.alias_value(merged, "minute_bucket")
            or self.minute_bucket(normalized["entry_minute"]),
            "UNKNOWN",
        )
        normalized["entry_scoreline"] = self.safe_str(
            self.alias_value(merged, "entry_scoreline")
        )
        normalized["final_scoreline"] = self.safe_str(
            self.alias_value(merged, "final_scoreline")
        )
        normalized["result_status"] = self.normalize_result(
            self.alias_value(merged, "result_status")
        )
        normalized["result_reason"] = self.safe_str(
            self.alias_value(merged, "result_reason")
        )
        normalized["data_source_quality"] = (
            self.safe_str(
                self.alias_value(merged, "data_source_quality"),
                "UNKNOWN",
            ).upper()
            or "UNKNOWN"
        )
        normalized["stats_completeness_score"] = self.safe_float(
            self.alias_value(merged, "stats_completeness_score"),
            0.0,
        )
        normalized["pre_match_expectation"] = self.safe_str(
            self.alias_value(merged, "pre_match_expectation")
        )
        normalized["live_reality"] = self.safe_str(
            self.alias_value(merged, "live_reality")
        )
        normalized["reality_confidence"] = self.safe_float(
            self.alias_value(merged, "reality_confidence"),
            0.0,
        )
        normalized["football_memory_available"] = self.safe_bool(
            self.alias_value(merged, "football_memory_available")
        )
        normalized["football_memory_confidence"] = self.safe_str(
            self.alias_value(merged, "football_memory_confidence")
        )

        return normalized

    def alias_value(
        self,
        row: Dict[str, Any],
        canonical: str,
        default: Any = None,
    ) -> Any:
        for key in self.FIELD_ALIASES.get(canonical, (canonical,)):
            if key in row and row.get(key) not in (None, ""):
                return row.get(key)
        return default

    def normalize_result(self, value: Any) -> str:
        text = self.safe_str(value, RESULT_UNKNOWN).upper()

        aliases = {
            "WIN": RESULT_WON,
            "WON": RESULT_WON,
            "SUCCESS": RESULT_WON,
            "HIT": RESULT_WON,
            "GREEN": RESULT_WON,
            "ACERTADA": RESULT_WON,
            "LOSS": RESULT_LOST,
            "LOST": RESULT_LOST,
            "FAIL": RESULT_LOST,
            "FAILED": RESULT_LOST,
            "RED": RESULT_LOST,
            "FALLIDA": RESULT_LOST,
            "VOID": RESULT_VOID,
            "PUSH": RESULT_VOID,
            "ANULADA": RESULT_VOID,
            "PENDING": RESULT_PENDING,
            "OPEN": RESULT_PENDING,
            "PENDIENTE": RESULT_PENDING,
            "EXPIRED": RESULT_EXPIRED,
            "EXPIRADA": RESULT_EXPIRED,
            "CANCELLED": RESULT_CANCELLED,
            "CANCELED": RESULT_CANCELLED,
            "CANCELADA": RESULT_CANCELLED,
        }

        return aliases.get(text, RESULT_UNKNOWN)

    def normalize_market(self, value: Any) -> str:
        market = self.safe_str(value, "UNKNOWN").upper()

        if "OVER" in market:
            return "OVER"

        if "UNDER" in market:
            return "UNDER"

        return market or "UNKNOWN"

    def minute_bucket(self, minute: Any) -> str:
        value = self.safe_int(minute, -1)

        if value < 0:
            return "UNKNOWN"

        if value <= 15:
            return "M00_15"

        if value <= 30:
            return "M16_30"

        if value <= 45:
            return "M31_45"

        if value <= 60:
            return "M46_60"

        if value <= 75:
            return "M61_75"

        if value <= 90:
            return "M76_90"

        return "M90_PLUS"

    def confidence_bucket(self, confidence: Any) -> str:
        value = self.safe_float(confidence, -1.0)

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

    def parse_json_if_needed(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        try:
            return json.loads(value)
        except Exception:
            return value

    def safe_str(self, value: Any, default: str = "") -> str:
        if value is None:
            return default
        return str(value).strip()

    def safe_int(self, value: Any, default: int = 0) -> int:
        try:
            if value is None or value == "":
                return default
            return int(float(value))
        except Exception:
            return default

    def safe_float(
        self,
        value: Any,
        default: Optional[float] = 0.0,
    ) -> Optional[float]:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except Exception:
            return default

    def safe_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return value != 0

        text = self.safe_str(value).lower()
        return text in {"true", "1", "yes", "y", "si", "sí"}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {key: row[key] for key in row.keys()}

    def _quote_identifier(self, value: str) -> str:
        return '"' + value.replace('"', '""') + '"'
