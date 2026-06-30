from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
from app.v17.performance.performance_history import PerformanceHistory
from app.v17.performance.performance_metrics import PerformanceMetrics, safe_float, safe_int, safe_str


VALID_RESULTS = {RESULT_WON, RESULT_LOST, RESULT_VOID, RESULT_PENDING}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


class PerformanceImporter:
    """
    PerformanceImporter V17.

    Rol:
    - IMPORT_ONLY / EVALUATION_ONLY.
    - No decide.
    - No publica.
    - No modifica official_*.
    - No toca MasterDecisionAI ni LiveSignalEngine.

    Importa historial existente hacia performance.db.
    """

    VERSION = "V17_PERFORMANCE_IMPORTER_1_OFFLINE_PASSIVE"
    IMPORT_ROLE = "IMPORT_ONLY"

    def __init__(
        self,
        base_dir: Optional[str | Path] = None,
        performance_db_path: Optional[str | Path] = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else self._default_app_dir()
        self.storage_dir = self.base_dir / "v17" / "storage"

        self.signal_history_path = self.storage_dir / "signal_history.json"
        self.training_data_path = self.storage_dir / "training_data.jsonl"
        self.prediction_features_db_path = self.storage_dir / "prediction_features.db"
        self.football_memory_db_path = self.storage_dir / "football_intelligence_memory.db"

        self.history = PerformanceHistory(db_path=str(performance_db_path or DEFAULT_DB_PATH))
        self.performance_db_path = Path(self.history.db_path)
        self._ensure_import_log()

    def import_all(self) -> Dict[str, Any]:
        summary = self._header()
        summary.update({"sources": {}, "started_at": utc_now_iso()})

        summary["sources"]["signal_history"] = self.import_signal_history()
        summary["sources"]["training_data"] = self.import_training_data()
        summary["sources"]["prediction_features"] = self.import_prediction_features()
        summary["sources"]["football_memory"] = self.import_football_memory()

        summary["finished_at"] = utc_now_iso()
        return summary

    def import_signal_history(self) -> Dict[str, Any]:
        source = "signal_history"
        stats = self._empty_stats(source, self.signal_history_path)

        data = self._safe_json_load(self.signal_history_path)
        if data is None:
            stats["skipped_reason"] = "file_missing_or_invalid"
            return stats

        for obj in self._walk_json_objects(data):
            self._import_object(obj=obj, source=source, object_type="object", stats=stats)

        return stats

    def import_training_data(self) -> Dict[str, Any]:
        source = "training_data"
        stats = self._empty_stats(source, self.training_data_path)

        if not self.training_data_path.exists():
            stats["skipped_reason"] = "file_missing"
            return stats

        for idx, obj in enumerate(self._safe_jsonl_iter(self.training_data_path), start=1):
            self._import_object(obj=obj, source=source, object_type="jsonl", stats=stats, fallback=f"line_{idx}")

        return stats

    def import_prediction_features(self) -> Dict[str, Any]:
        source = "prediction_features"
        stats = self._empty_stats(source, self.prediction_features_db_path)

        if not self.prediction_features_db_path.exists():
            stats["skipped_reason"] = "file_missing"
            return stats

        try:
            with sqlite3.connect(str(self.prediction_features_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                for table in ("prediction_features", "training_examples"):
                    if not self._table_exists(conn, table):
                        continue
                    rows = conn.execute(f"SELECT rowid AS __rowid__, * FROM {table}").fetchall()
                    for row in rows:
                        obj = dict(row)
                        self._import_object(
                            obj=obj,
                            source=source,
                            object_type=table,
                            stats=stats,
                            fallback=f"{table}_{obj.get('__rowid__', '')}",
                            force_event_type=f"IMPORT_PREDICTION_FEATURES_{table.upper()}",
                        )
        except Exception as exc:
            stats["errors"] += 1
            stats["error_samples"].append(str(exc)[:300])

        return stats

    def import_football_memory(self) -> Dict[str, Any]:
        source = "football_memory"
        stats = self._empty_stats(source, self.football_memory_db_path)

        if not self.football_memory_db_path.exists():
            stats["skipped_reason"] = "file_missing"
            return stats

        memory_tables = (
            "memory_events",
            "team_memory",
            "league_memory",
            "matchup_memory",
            "live_pattern_memory",
            "memory_snapshot_dedup",
        )

        try:
            with sqlite3.connect(str(self.football_memory_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                for table in memory_tables:
                    if not self._table_exists(conn, table):
                        continue
                    rows = conn.execute(f"SELECT rowid AS __rowid__, * FROM {table}").fetchall()
                    for row in rows:
                        obj = dict(row)
                        stable_id = self._stable_id(obj, fallback=f"{table}_{obj.get('__rowid__', '')}")
                        import_key = self._make_import_key(source, table, stable_id)
                        if self._already_imported(import_key):
                            stats["duplicates"] += 1
                            continue

                        self.history.record_event(
                            event_type=f"IMPORT_FOOTBALL_MEMORY_{table.upper()}",
                            signal_key=safe_str(obj.get("signal_key")),
                            fixture_id=safe_str(obj.get("fixture_id")),
                            payload={
                                "source": source,
                                "table": table,
                                "memory_role": "EVIDENCE_ONLY",
                                "memory_is_official_decision": False,
                                "memory_can_publish": False,
                                "data": obj,
                            },
                        )
                        self._mark_imported(import_key, source, stable_id)
                        stats["events_imported"] += 1
                        stats["processed"] += 1
        except Exception as exc:
            stats["errors"] += 1
            stats["error_samples"].append(str(exc)[:300])

        return stats

    def _import_object(
        self,
        *,
        obj: Dict[str, Any],
        source: str,
        object_type: str,
        stats: Dict[str, Any],
        fallback: str = "",
        force_event_type: Optional[str] = None,
    ) -> None:
        if not isinstance(obj, dict):
            return
        try:
            signal_payload = self._extract_signal_payload(obj, source=source)
            result_payload = self._extract_result_payload(obj, source=source)
            stable_id = self._stable_id(signal_payload or result_payload or obj, fallback=fallback)
            import_key = self._make_import_key(source, object_type, stable_id)

            if self._already_imported(import_key):
                stats["duplicates"] += 1
                return

            imported_anything = False
            if signal_payload:
                self.history.upsert_signal(signal_payload)
                stats["signals_imported"] += 1
                imported_anything = True

            if result_payload:
                self.history.record_result(result_payload)
                stats["results_imported"] += 1
                imported_anything = True

            if force_event_type or not imported_anything:
                self.history.record_event(
                    event_type=force_event_type or f"IMPORT_{source.upper()}_OBJECT",
                    signal_key=safe_str((signal_payload or result_payload or {}).get("signal_key")),
                    fixture_id=safe_str((signal_payload or result_payload or obj).get("fixture_id")),
                    payload={
                        "source": source,
                        "object_type": object_type,
                        "imported_as_signal_or_result": imported_anything,
                        "data": obj,
                    },
                )
                stats["events_imported"] += 1

            self._mark_imported(import_key, source, stable_id)
            stats["processed"] += 1
        except Exception as exc:
            stats["errors"] += 1
            stats["error_samples"].append(str(exc)[:300])

    def _extract_signal_payload(self, obj: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        market = self._first(obj, "official_market", "market", "signal_market", "prediction_market", "suggested_market")
        fixture_id = self._first(obj, "fixture_id", "match_id", "api_fixture_id")
        signal_key = self._first(obj, "signal_key", "signal_id", "id", "candidate_id")

        if not market and not fixture_id and not signal_key:
            return None

        reality = obj.get("pre_match_live_reality") if isinstance(obj.get("pre_match_live_reality"), dict) else {}
        memory = obj.get("football_memory_context") if isinstance(obj.get("football_memory_context"), dict) else {}
        minute = self._safe_int(self._first(obj, "entry_minute", "api_minute", "display_minute", "minute", "elapsed", "match_minute")) or 0
        confidence = self._safe_float(self._first(obj, "official_confidence", "master_confidence", "confidence", "signal_confidence")) or 0.0

        payload = {
            "signal_key": safe_str(signal_key or self._synthetic_signal_key(obj)),
            "fixture_id": safe_str(fixture_id),
            "home_team": safe_str(self._first(obj, "home_team", "home", "home_name")),
            "away_team": safe_str(self._first(obj, "away_team", "away", "away_name")),
            "league": safe_str(self._first(obj, "league", "league_name"), "UNKNOWN"),
            "country": safe_str(self._first(obj, "country"), "UNKNOWN"),
            "market": PerformanceMetrics.normalize_market(market),
            "official_market": safe_str(self._first(obj, "official_market") or market),
            "official_status": safe_str(self._first(obj, "official_status", "status")),
            "official_can_publish": bool(self._safe_bool(self._first(obj, "official_can_publish")) or False),
            "official_confidence": confidence,
            "entry_minute": minute,
            "minute_bucket": PerformanceMetrics.minute_bucket(minute),
            "entry_scoreline": safe_str(self._score_text(obj)),
            "final_scoreline": safe_str(self._first(obj, "final_scoreline", "final_score", "current_scoreline")),
            "result_status": PerformanceMetrics.normalize_result(self._first(obj, "result_status", "tracking_status")),
            "result_reason": safe_str(self._first(obj, "result_reason", "resolution_reason")),
            "data_source_quality": safe_str(self._first(obj, "data_source_quality", "data_quality"), "UNKNOWN").upper(),
            "stats_completeness_score": self._safe_float(self._first(obj, "stats_completeness_score")) or 0.0,
            "pre_match_live_reality": reality,
            "football_memory_context": memory,
            "source": source,
            "raw_payload": obj,
        }
        return payload

    def _extract_result_payload(self, obj: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        raw_result = self._first(obj, "result_status", "tracking_status", "final_result", "resolution", "outcome", "signal_result")
        result_status = PerformanceMetrics.normalize_result(raw_result)
        if result_status not in VALID_RESULTS:
            return None

        signal_key = safe_str(self._first(obj, "signal_key", "signal_id", "id", "candidate_id") or self._synthetic_signal_key(obj))
        return {
            "signal_key": signal_key,
            "fixture_id": safe_str(self._first(obj, "fixture_id", "match_id", "api_fixture_id")),
            "result_status": result_status,
            "result_reason": safe_str(self._first(obj, "result_reason", "resolution_reason")),
            "resolved_at": safe_str(self._first(obj, "resolved_at", "finished_at", "updated_at") or utc_now_iso()),
            "final_scoreline": safe_str(self._first(obj, "final_scoreline", "final_score") or self._score_text(obj)),
            "source": source,
            "raw_payload": obj,
        }

    def _ensure_import_log(self) -> None:
        self.performance_db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.performance_db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_import_log (
                    import_key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_id TEXT,
                    imported_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _already_imported(self, import_key: str) -> bool:
        with sqlite3.connect(str(self.performance_db_path)) as conn:
            row = conn.execute("SELECT import_key FROM performance_import_log WHERE import_key = ?", (import_key,)).fetchone()
        return row is not None

    def _mark_imported(self, import_key: str, source: str, source_id: str) -> None:
        with sqlite3.connect(str(self.performance_db_path)) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO performance_import_log (
                    import_key, source, source_id, imported_at
                ) VALUES (?, ?, ?, ?)
                """,
                (import_key, source, source_id, utc_now_iso()),
            )
            conn.commit()

    def _make_import_key(self, source: str, object_type: str, stable_id: str) -> str:
        return f"{source}:{object_type}:{stable_id}"

    def _stable_id(self, obj: Dict[str, Any], fallback: str = "") -> str:
        direct = self._first(obj, "signal_key", "signal_id", "event_id", "memory_id", "id", "row_id", "uuid", "__rowid__")
        if direct:
            return safe_str(direct)
        fixture_id = self._first(obj, "fixture_id", "match_id", "api_fixture_id") or "no_fixture"
        market = self._first(obj, "official_market", "market", "signal_market", "suggested_market") or "no_market"
        minute = self._first(obj, "entry_minute", "api_minute", "display_minute", "minute", "elapsed", "match_minute") or "no_minute"
        score = self._score_text(obj) or "no_score"
        created_at = self._first(obj, "created_at", "updated_at", "timestamp", "ts") or fallback or "no_time"
        return f"{fixture_id}:{market}:{minute}:{score}:{created_at}"

    def _synthetic_signal_key(self, obj: Dict[str, Any]) -> str:
        return f"PERF_IMPORT:{self._stable_id(obj)}"

    def _safe_json_load(self, path: Path) -> Optional[Any]:
        if not path.exists():
            return None
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return json.loads(path.read_text(encoding=encoding))
            except Exception:
                continue
        return None

    def _safe_jsonl_iter(self, path: Path) -> Iterable[Dict[str, Any]]:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with path.open("r", encoding=encoding) as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if isinstance(obj, dict):
                                yield obj
                        except Exception:
                            continue
                return
            except Exception:
                continue

    def _walk_json_objects(self, data: Any) -> Iterable[Dict[str, Any]]:
        if isinstance(data, dict):
            yield data
            for value in data.values():
                yield from self._walk_json_objects(value)
        elif isinstance(data, list):
            for item in data:
                yield from self._walk_json_objects(item)

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _first(self, obj: Dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in obj and obj.get(key) not in (None, ""):
                return obj.get(key)
        return None

    def _score_text(self, obj: Dict[str, Any]) -> Optional[str]:
        direct = self._first(obj, "score", "scoreline", "current_score", "final_score", "entry_scoreline")
        if direct:
            return safe_str(direct)
        home_score = self._first(obj, "home_score", "home_goals")
        away_score = self._first(obj, "away_score", "away_goals")
        if home_score is not None and away_score is not None:
            return f"{home_score}-{away_score}"
        return None

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except Exception:
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def _safe_bool(self, value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        text = safe_str(value).lower()
        if text in {"true", "1", "yes", "y", "si", "sí"}:
            return True
        if text in {"false", "0", "no", "n"}:
            return False
        return None

    def _empty_stats(self, source: str, path: Path) -> Dict[str, Any]:
        return {
            "source": source,
            "path": str(path),
            "exists": path.exists(),
            "processed": 0,
            "signals_imported": 0,
            "results_imported": 0,
            "events_imported": 0,
            "duplicates": 0,
            "errors": 0,
            "error_samples": [],
            "skipped_reason": None,
        }

    def _header(self) -> Dict[str, Any]:
        return {
            "role": self.IMPORT_ROLE,
            "performance_role": PERFORMANCE_ROLE,
            "performance_is_official_decision": PERFORMANCE_IS_OFFICIAL_DECISION,
            "performance_can_publish": PERFORMANCE_CAN_PUBLISH,
            "evaluation_only": True,
            "official_decision_modified": False,
            "version": self.VERSION,
        }
