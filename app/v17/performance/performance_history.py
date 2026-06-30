from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.v17.performance.performance_constants import (
    DEFAULT_DB_PATH,
    PERFORMANCE_CAN_PUBLISH,
    PERFORMANCE_IS_OFFICIAL_DECISION,
    PERFORMANCE_ROLE,
    PERFORMANCE_VERSION,
    RESULT_PENDING,
)
from app.v17.performance.performance_metrics import (
    PerformanceMetrics,
    safe_float,
    safe_int,
    safe_str,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def load_json(value: Any) -> Any:
    try:
        if not value:
            return {}
        return json.loads(value)
    except Exception:
        return {}


class PerformanceHistory:
    """
    Storage SQLite pasivo para PerformanceEvaluator V17.

    No decide.
    No publica.
    No modifica official_*.
    """

    VERSION = PERFORMANCE_VERSION

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def upsert_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._result(False, "INVALID_SIGNAL_PAYLOAD")

        record = self._build_signal_record(signal)
        signal_key = record.get("signal_key")

        if not signal_key:
            return self._result(False, "MISSING_SIGNAL_KEY")

        existing = self.get_signal(signal_key)
        if existing:
            record = self._merge_existing(existing, record)

        now = utc_now_iso()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO performance_signals (
                    signal_key, fixture_id, home_team, away_team, league, country,
                    market, official_market, official_status, official_can_publish,
                    official_confidence, official_confidence_bucket, entry_minute,
                    minute_bucket, entry_scoreline, final_scoreline, result_status,
                    result_reason, data_source_quality, stats_completeness_score,
                    pre_match_expectation, live_reality, reality_confidence,
                    football_memory_available, football_memory_confidence,
                    payload_json, created_at, updated_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(signal_key) DO UPDATE SET
                    fixture_id=excluded.fixture_id,
                    home_team=excluded.home_team,
                    away_team=excluded.away_team,
                    league=excluded.league,
                    country=excluded.country,
                    market=excluded.market,
                    official_market=excluded.official_market,
                    official_status=excluded.official_status,
                    official_can_publish=excluded.official_can_publish,
                    official_confidence=excluded.official_confidence,
                    official_confidence_bucket=excluded.official_confidence_bucket,
                    entry_minute=excluded.entry_minute,
                    minute_bucket=excluded.minute_bucket,
                    entry_scoreline=excluded.entry_scoreline,
                    final_scoreline=excluded.final_scoreline,
                    result_status=excluded.result_status,
                    result_reason=excluded.result_reason,
                    data_source_quality=excluded.data_source_quality,
                    stats_completeness_score=excluded.stats_completeness_score,
                    pre_match_expectation=excluded.pre_match_expectation,
                    live_reality=excluded.live_reality,
                    reality_confidence=excluded.reality_confidence,
                    football_memory_available=excluded.football_memory_available,
                    football_memory_confidence=excluded.football_memory_confidence,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at,
                    resolved_at=excluded.resolved_at
                """,
                (
                    record["signal_key"], record["fixture_id"], record["home_team"], record["away_team"], record["league"], record["country"],
                    record["market"], record["official_market"], record["official_status"], record["official_can_publish"],
                    record["official_confidence"], record["official_confidence_bucket"], record["entry_minute"], record["minute_bucket"],
                    record["entry_scoreline"], record["final_scoreline"], record["result_status"], record["result_reason"],
                    record["data_source_quality"], record["stats_completeness_score"], record["pre_match_expectation"], record["live_reality"],
                    record["reality_confidence"], record["football_memory_available"], record["football_memory_confidence"], safe_json(signal),
                    existing.get("created_at") if existing else now, now, record["resolved_at"],
                ),
            )

            self._insert_event(conn=conn, event_type="SIGNAL_UPSERTED", signal_key=record["signal_key"], fixture_id=record["fixture_id"], payload=record)
            conn.commit()

        return self._result(True, "SIGNAL_RECORDED", signal_key=record["signal_key"])

    def record_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return self._result(False, "INVALID_RESULT_PAYLOAD")

        signal_key = safe_str(result.get("signal_key") or result.get("signal_id") or self._make_signal_key(result))
        if not signal_key:
            return self._result(False, "MISSING_SIGNAL_KEY")

        signal = self.get_signal(signal_key)
        merged = {**(signal or {}), **result, "signal_key": signal_key}
        merged["result_status"] = PerformanceMetrics.normalize_result(result.get("result_status") or result.get("tracking_status") or merged.get("result_status"))
        merged["result_reason"] = safe_str(result.get("result_reason") or merged.get("result_reason"))
        merged["resolved_at"] = safe_str(result.get("resolved_at") or utc_now_iso())
        return self.upsert_signal(merged)

    def get_signal(self, signal_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM performance_signals WHERE signal_key = ?", (signal_key,)).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def list_signals(self, *, include_pending: bool = True, limit: int = 5000) -> List[Dict[str, Any]]:
        query = "SELECT * FROM performance_signals"
        params: List[Any] = []
        if not include_pending:
            query += " WHERE result_status IN ('WON', 'LOST')"
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def record_event(self, event_type: str, payload: Dict[str, Any], signal_key: str = "", fixture_id: str = "") -> Dict[str, Any]:
        with self._connect() as conn:
            self._insert_event(conn=conn, event_type=event_type, signal_key=signal_key, fixture_id=fixture_id, payload=payload)
            conn.commit()
        return self._result(True, "EVENT_RECORDED")

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_signals (
                    signal_key TEXT PRIMARY KEY,
                    fixture_id TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    league TEXT,
                    country TEXT,
                    market TEXT,
                    official_market TEXT,
                    official_status TEXT,
                    official_can_publish INTEGER DEFAULT 0,
                    official_confidence REAL DEFAULT 0,
                    official_confidence_bucket TEXT,
                    entry_minute INTEGER DEFAULT 0,
                    minute_bucket TEXT,
                    entry_scoreline TEXT,
                    final_scoreline TEXT,
                    result_status TEXT,
                    result_reason TEXT,
                    data_source_quality TEXT,
                    stats_completeness_score REAL DEFAULT 0,
                    pre_match_expectation TEXT,
                    live_reality TEXT,
                    reality_confidence REAL DEFAULT 0,
                    football_memory_available INTEGER DEFAULT 0,
                    football_memory_confidence TEXT,
                    payload_json TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    resolved_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    signal_key TEXT,
                    fixture_id TEXT,
                    event_time TEXT NOT NULL,
                    payload_json TEXT
                )
                """
            )
            for stmt in [
                "CREATE INDEX IF NOT EXISTS idx_performance_signals_market ON performance_signals(market)",
                "CREATE INDEX IF NOT EXISTS idx_performance_signals_league ON performance_signals(league)",
                "CREATE INDEX IF NOT EXISTS idx_performance_signals_result ON performance_signals(result_status)",
                "CREATE INDEX IF NOT EXISTS idx_performance_signals_minute_bucket ON performance_signals(minute_bucket)",
                "CREATE INDEX IF NOT EXISTS idx_performance_signals_data_quality ON performance_signals(data_source_quality)",
                "CREATE INDEX IF NOT EXISTS idx_performance_events_signal ON performance_events(signal_key)",
            ]:
                conn.execute(stmt)
            conn.commit()

    def _build_signal_record(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        reality = signal.get("pre_match_live_reality") if isinstance(signal.get("pre_match_live_reality"), dict) else {}
        memory = signal.get("football_memory_context") if isinstance(signal.get("football_memory_context"), dict) else {}
        entry_minute = safe_int(signal.get("entry_minute") or signal.get("api_minute") or signal.get("display_minute"), 0)
        official_confidence = safe_float(signal.get("official_confidence") or signal.get("master_confidence") or signal.get("confidence"), 0.0)
        market = PerformanceMetrics.normalize_market(signal.get("official_market") or signal.get("market") or signal.get("suggested_market") or signal.get("prediction_market"))
        result_status = PerformanceMetrics.normalize_result(signal.get("result_status") or signal.get("tracking_status") or RESULT_PENDING)
        signal_key = safe_str(signal.get("signal_key") or signal.get("signal_id") or self._make_signal_key(signal))
        return {
            "signal_key": signal_key,
            "fixture_id": safe_str(signal.get("fixture_id") or signal.get("match_id")),
            "home_team": safe_str(signal.get("home_team")),
            "away_team": safe_str(signal.get("away_team")),
            "league": safe_str(signal.get("league"), "UNKNOWN"),
            "country": safe_str(signal.get("country"), "UNKNOWN"),
            "market": market,
            "official_market": safe_str(signal.get("official_market") or market),
            "official_status": safe_str(signal.get("official_status")),
            "official_can_publish": 1 if bool(signal.get("official_can_publish")) else 0,
            "official_confidence": official_confidence,
            "official_confidence_bucket": PerformanceMetrics.confidence_bucket(official_confidence),
            "entry_minute": entry_minute,
            "minute_bucket": PerformanceMetrics.minute_bucket(entry_minute),
            "entry_scoreline": safe_str(signal.get("entry_scoreline") or signal.get("scoreline") or signal.get("current_score")),
            "final_scoreline": safe_str(signal.get("final_scoreline") or signal.get("current_scoreline")),
            "result_status": result_status,
            "result_reason": safe_str(signal.get("result_reason")),
            "data_source_quality": safe_str(signal.get("data_source_quality") or signal.get("data_quality"), "UNKNOWN").upper(),
            "stats_completeness_score": safe_float(signal.get("stats_completeness_score"), 0.0),
            "pre_match_expectation": safe_str(reality.get("pre_match_expectation")),
            "live_reality": safe_str(reality.get("live_reality")),
            "reality_confidence": safe_float(reality.get("reality_confidence"), 0.0),
            "football_memory_available": 1 if bool(memory.get("memory_available")) else 0,
            "football_memory_confidence": safe_str(memory.get("memory_confidence")),
            "resolved_at": safe_str(signal.get("resolved_at")),
        }

    def _merge_existing(self, existing: Dict[str, Any], new_record: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(existing)
        merged.update(new_record)
        new_status = PerformanceMetrics.normalize_result(new_record.get("result_status"))
        old_status = PerformanceMetrics.normalize_result(existing.get("result_status"))
        if new_status == RESULT_PENDING and old_status != RESULT_PENDING:
            merged["result_status"] = old_status
            merged["result_reason"] = existing.get("result_reason")
            merged["resolved_at"] = existing.get("resolved_at")
            merged["final_scoreline"] = existing.get("final_scoreline")
        return merged

    def _insert_event(self, *, conn: sqlite3.Connection, event_type: str, signal_key: str, fixture_id: str, payload: Dict[str, Any]) -> None:
        conn.execute(
            """
            INSERT INTO performance_events (event_type, signal_key, fixture_id, event_time, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, signal_key, fixture_id, utc_now_iso(), safe_json(payload)),
        )

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        data["payload"] = load_json(data.get("payload_json"))
        return data

    def _make_signal_key(self, signal: Dict[str, Any]) -> str:
        fixture_id = safe_str(signal.get("fixture_id") or signal.get("match_id"))
        market = PerformanceMetrics.normalize_market(signal.get("official_market") or signal.get("market") or signal.get("suggested_market"))
        minute = safe_int(signal.get("entry_minute") or signal.get("api_minute") or signal.get("display_minute"), 0)
        if not fixture_id:
            return ""
        return f"PERF:{fixture_id}:{market}:{minute}"

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _result(self, ok: bool, reason: str, **extra: Any) -> Dict[str, Any]:
        return {
            "performance_role": PERFORMANCE_ROLE,
            "performance_is_official_decision": PERFORMANCE_IS_OFFICIAL_DECISION,
            "performance_can_publish": PERFORMANCE_CAN_PUBLISH,
            "performance_ok": ok,
            "performance_reason": reason,
            **extra,
        }
