from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_bool_int(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0

    text = str(value or "").strip().upper()
    if text in {"1", "TRUE", "YES", "SI", "SÍ", "ON"}:
        return 1

    return 0


def first_present(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


class PredictionFeatureStore:
    """
    Almacén SQLite de features predictivas V17.

    Mejora V17:
    - Mantiene la estructura original basada en JSON.
    - Agrega columnas ligeras para contexto competitivo:
        competition_tier
        competition_weight
        world_cup_flag
        national_team_flag
        major_tournament_flag
        league_filter_status
    - Es compatible con bases antiguas: si las columnas no existen, las crea con ALTER TABLE.
    - No rompe payloads anteriores porque todos los campos nuevos tienen fallback seguro.
    """

    STORAGE_DIR = Path("app/v17/storage")
    STORAGE_FILE = STORAGE_DIR / "prediction_features.db"

    COMPETITION_COLUMNS = {
        "competition_tier": "TEXT",
        "competition_weight": "REAL DEFAULT 0",
        "world_cup_flag": "INTEGER DEFAULT 0",
        "national_team_flag": "INTEGER DEFAULT 0",
        "major_tournament_flag": "INTEGER DEFAULT 0",
        "league_filter_status": "TEXT",
    }

    def __init__(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(
            str(self.STORAGE_FILE),
            check_same_thread=False,
            isolation_level=None,
        )
        self.connection.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id TEXT NOT NULL,
                api_minute INTEGER NOT NULL,
                signal_key TEXT,
                event_time TEXT,
                feature_vector_json TEXT,
                match_snapshot_json TEXT,
                pre_match_snapshot_json TEXT,
                context_snapshot_json TEXT,
                tactical_snapshot_json TEXT,
                market_snapshot_json TEXT,
                risk_snapshot_json TEXT,
                prediction_snapshot_json TEXT,
                metadata_json TEXT,
                competition_tier TEXT,
                competition_weight REAL DEFAULT 0,
                world_cup_flag INTEGER DEFAULT 0,
                national_team_flag INTEGER DEFAULT 0,
                major_tournament_flag INTEGER DEFAULT 0,
                league_filter_status TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(fixture_id, api_minute)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS training_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id TEXT NOT NULL,
                signal_key TEXT,
                entry_minute INTEGER,
                result_status TEXT,
                label TEXT,
                feature_vector_json TEXT,
                prediction_snapshot_json TEXT,
                resolution_snapshot_json TEXT,
                match_snapshot_json TEXT,
                pre_match_snapshot_json TEXT,
                competition_tier TEXT,
                competition_weight REAL DEFAULT 0,
                world_cup_flag INTEGER DEFAULT 0,
                national_team_flag INTEGER DEFAULT 0,
                major_tournament_flag INTEGER DEFAULT 0,
                league_filter_status TEXT,
                created_at TEXT
            )
            """
        )

        self._ensure_competition_columns("prediction_features")
        self._ensure_competition_columns("training_examples")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_features_fixture ON prediction_features(fixture_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_features_fixture_minute ON prediction_features(fixture_id, api_minute)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_features_competition_tier ON prediction_features(competition_tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prediction_features_world_cup ON prediction_features(world_cup_flag)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_training_examples_fixture ON training_examples(fixture_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_training_examples_competition_tier ON training_examples(competition_tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_training_examples_world_cup ON training_examples(world_cup_flag)")

    def _ensure_competition_columns(self, table_name: str) -> None:
        for column_name, column_type in self.COMPETITION_COLUMNS.items():
            if not self._column_exists(table_name, column_name):
                self.connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()
        return any(str(row[1]) == column_name for row in rows)

    def _dump(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def _load(self, value: Optional[str]) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    def _competition_context_from_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}

        feature_vector = payload.get("feature_vector") if isinstance(payload.get("feature_vector"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        match_snapshot = payload.get("match_snapshot") if isinstance(payload.get("match_snapshot"), dict) else {}
        pre_match_snapshot = payload.get("pre_match_snapshot") if isinstance(payload.get("pre_match_snapshot"), dict) else {}

        competition_tier = str(first_present(
            metadata.get("competition_tier"),
            match_snapshot.get("competition_tier"),
            pre_match_snapshot.get("competition_tier"),
            default="",
        ) or "").upper()

        competition_weight = safe_float(first_present(
            metadata.get("competition_weight"),
            feature_vector.get("competition_weight"),
            match_snapshot.get("competition_weight"),
            pre_match_snapshot.get("competition_weight"),
            default=0,
        ), 0.0)

        world_cup_flag = safe_bool_int(first_present(
            metadata.get("world_cup_flag"),
            feature_vector.get("world_cup_flag"),
            match_snapshot.get("world_cup_flag"),
            pre_match_snapshot.get("world_cup_flag"),
            default=False,
        ))

        national_team_flag = safe_bool_int(first_present(
            metadata.get("national_team_flag"),
            feature_vector.get("national_team_flag"),
            match_snapshot.get("national_team_flag"),
            pre_match_snapshot.get("national_team_flag"),
            default=False,
        ))

        major_tournament_flag = safe_bool_int(first_present(
            metadata.get("major_tournament_flag"),
            feature_vector.get("major_tournament_flag"),
            match_snapshot.get("major_tournament_flag"),
            pre_match_snapshot.get("major_tournament_flag"),
            default=False,
        ))

        league_filter_status = str(first_present(
            metadata.get("league_filter_status"),
            match_snapshot.get("league_filter_status"),
            pre_match_snapshot.get("league_filter_status"),
            default="",
        ) or "")

        return {
            "competition_tier": competition_tier,
            "competition_weight": competition_weight,
            "world_cup_flag": world_cup_flag,
            "national_team_flag": national_team_flag,
            "major_tournament_flag": major_tournament_flag,
            "league_filter_status": league_filter_status,
        }

    def _competition_context_from_signal_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}

        feature_vector = payload.get("feature_vector") if isinstance(payload.get("feature_vector"), dict) else {}
        match_snapshot = payload.get("match_snapshot") if isinstance(payload.get("match_snapshot"), dict) else {}
        pre_match_snapshot = payload.get("pre_match_snapshot") if isinstance(payload.get("pre_match_snapshot"), dict) else {}
        resolution_snapshot = payload.get("resolution_snapshot") if isinstance(payload.get("resolution_snapshot"), dict) else {}

        competition_tier = str(first_present(
            payload.get("competition_tier"),
            match_snapshot.get("competition_tier"),
            pre_match_snapshot.get("competition_tier"),
            resolution_snapshot.get("competition_tier"),
            default="",
        ) or "").upper()

        competition_weight = safe_float(first_present(
            payload.get("competition_weight"),
            feature_vector.get("competition_weight"),
            match_snapshot.get("competition_weight"),
            pre_match_snapshot.get("competition_weight"),
            resolution_snapshot.get("competition_weight"),
            default=0,
        ), 0.0)

        return {
            "competition_tier": competition_tier,
            "competition_weight": competition_weight,
            "world_cup_flag": safe_bool_int(first_present(
                payload.get("world_cup_flag"),
                feature_vector.get("world_cup_flag"),
                match_snapshot.get("world_cup_flag"),
                pre_match_snapshot.get("world_cup_flag"),
                resolution_snapshot.get("world_cup_flag"),
                default=False,
            )),
            "national_team_flag": safe_bool_int(first_present(
                payload.get("national_team_flag"),
                feature_vector.get("national_team_flag"),
                match_snapshot.get("national_team_flag"),
                pre_match_snapshot.get("national_team_flag"),
                resolution_snapshot.get("national_team_flag"),
                default=False,
            )),
            "major_tournament_flag": safe_bool_int(first_present(
                payload.get("major_tournament_flag"),
                feature_vector.get("major_tournament_flag"),
                match_snapshot.get("major_tournament_flag"),
                pre_match_snapshot.get("major_tournament_flag"),
                resolution_snapshot.get("major_tournament_flag"),
                default=False,
            )),
            "league_filter_status": str(first_present(
                payload.get("league_filter_status"),
                match_snapshot.get("league_filter_status"),
                pre_match_snapshot.get("league_filter_status"),
                resolution_snapshot.get("league_filter_status"),
                default="",
            ) or ""),
        }

    def save_feature_vector(self, payload: Dict[str, Any]) -> None:
        fixture_id = str(payload.get("fixture_id") or "").strip()
        api_minute = safe_int(payload.get("api_minute"), 0)
        if not fixture_id:
            return

        competition_context = self._competition_context_from_payload(payload)
        now = utc_now_iso()
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO prediction_features (
                fixture_id,
                api_minute,
                signal_key,
                event_time,
                feature_vector_json,
                match_snapshot_json,
                pre_match_snapshot_json,
                context_snapshot_json,
                tactical_snapshot_json,
                market_snapshot_json,
                risk_snapshot_json,
                prediction_snapshot_json,
                metadata_json,
                competition_tier,
                competition_weight,
                world_cup_flag,
                national_team_flag,
                major_tournament_flag,
                league_filter_status,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(fixture_id, api_minute) DO UPDATE SET
                signal_key=COALESCE(excluded.signal_key, prediction_features.signal_key),
                event_time=excluded.event_time,
                feature_vector_json=excluded.feature_vector_json,
                match_snapshot_json=excluded.match_snapshot_json,
                pre_match_snapshot_json=excluded.pre_match_snapshot_json,
                context_snapshot_json=excluded.context_snapshot_json,
                tactical_snapshot_json=excluded.tactical_snapshot_json,
                market_snapshot_json=excluded.market_snapshot_json,
                risk_snapshot_json=excluded.risk_snapshot_json,
                prediction_snapshot_json=COALESCE(excluded.prediction_snapshot_json, prediction_features.prediction_snapshot_json),
                metadata_json=excluded.metadata_json,
                competition_tier=COALESCE(excluded.competition_tier, prediction_features.competition_tier),
                competition_weight=CASE WHEN excluded.competition_weight > 0 THEN excluded.competition_weight ELSE prediction_features.competition_weight END,
                world_cup_flag=MAX(excluded.world_cup_flag, prediction_features.world_cup_flag),
                national_team_flag=MAX(excluded.national_team_flag, prediction_features.national_team_flag),
                major_tournament_flag=MAX(excluded.major_tournament_flag, prediction_features.major_tournament_flag),
                league_filter_status=COALESCE(excluded.league_filter_status, prediction_features.league_filter_status),
                updated_at=excluded.updated_at
            """,
            (
                fixture_id,
                api_minute,
                str(payload.get("signal_key") or ""),
                str(payload.get("event_time") or now),
                self._dump(payload.get("feature_vector")),
                self._dump(payload.get("match_snapshot")),
                self._dump(payload.get("pre_match_snapshot")),
                self._dump(payload.get("context_snapshot")),
                self._dump(payload.get("tactical_snapshot")),
                self._dump(payload.get("market_snapshot")),
                self._dump(payload.get("risk_snapshot")),
                self._dump(payload.get("prediction_snapshot")),
                self._dump(payload.get("metadata")),
                competition_context["competition_tier"],
                competition_context["competition_weight"],
                competition_context["world_cup_flag"],
                competition_context["national_team_flag"],
                competition_context["major_tournament_flag"],
                competition_context["league_filter_status"],
                now,
                now,
            ),
        )

    def update_prediction_snapshot(
        self,
        fixture_id: str,
        api_minute: int,
        prediction_snapshot: Dict[str, Any],
        signal_key: Optional[str] = None,
    ) -> None:
        fixture_id = str(fixture_id or "").strip()
        if not fixture_id:
            return

        now = utc_now_iso()
        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE prediction_features SET
                prediction_snapshot_json = ?,
                signal_key = COALESCE(?, signal_key),
                updated_at = ?
            WHERE fixture_id = ? AND api_minute = ?
            """,
            (
                self._dump(prediction_snapshot),
                str(signal_key) if signal_key is not None else None,
                now,
                fixture_id,
                safe_int(api_minute, 0),
            ),
        )

    def get_features(self, fixture_id: str, api_minute: int) -> Optional[Dict[str, Any]]:
        fixture_id = str(fixture_id or "").strip()
        if not fixture_id:
            return None

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM prediction_features WHERE fixture_id = ? AND api_minute = ?",
            (fixture_id, safe_int(api_minute, 0)),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_dict(row)

    def get_history(
        self,
        fixture_id: str,
        since_minute: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        fixture_id = str(fixture_id or "").strip()
        if not fixture_id:
            return []

        cursor = self.connection.cursor()
        if since_minute is not None:
            cursor.execute(
                "SELECT * FROM prediction_features WHERE fixture_id = ? AND api_minute >= ? ORDER BY api_minute ASC LIMIT ?",
                (fixture_id, safe_int(since_minute, 0), safe_int(limit, 100)),
            )
        else:
            cursor.execute(
                "SELECT * FROM prediction_features WHERE fixture_id = ? ORDER BY api_minute ASC LIMIT ?",
                (fixture_id, safe_int(limit, 100)),
            )
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_fixture_features(self, fixture_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self.get_history(fixture_id, since_minute=None, limit=limit)

    def save_training_example(self, payload: Dict[str, Any]) -> None:
        competition_context = self._competition_context_from_signal_payload(payload)
        now = utc_now_iso()
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO training_examples (
                fixture_id,
                signal_key,
                entry_minute,
                result_status,
                label,
                feature_vector_json,
                prediction_snapshot_json,
                resolution_snapshot_json,
                match_snapshot_json,
                pre_match_snapshot_json,
                competition_tier,
                competition_weight,
                world_cup_flag,
                national_team_flag,
                major_tournament_flag,
                league_filter_status,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(payload.get("fixture_id") or ""),
                str(payload.get("signal_key") or ""),
                safe_int(payload.get("entry_minute"), 0),
                str(payload.get("result_status") or ""),
                str(payload.get("label") or ""),
                self._dump(payload.get("feature_vector")),
                self._dump(payload.get("prediction_snapshot")),
                self._dump(payload.get("resolution_snapshot")),
                self._dump(payload.get("match_snapshot")),
                self._dump(payload.get("pre_match_snapshot")),
                competition_context["competition_tier"],
                competition_context["competition_weight"],
                competition_context["world_cup_flag"],
                competition_context["national_team_flag"],
                competition_context["major_tournament_flag"],
                competition_context["league_filter_status"],
                now,
            ),
        )

    def get_training_examples(self, fixture_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        fixture_id = str(fixture_id or "").strip()
        if not fixture_id:
            return []

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM training_examples WHERE fixture_id = ? ORDER BY created_at DESC LIMIT ?",
            (fixture_id, safe_int(limit, 100)),
        )
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_training_examples_by_competition(
        self,
        competition_tier: Optional[str] = None,
        world_cup_only: bool = False,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Consulta auxiliar para analizar o entrenar por tipo de competición.
        No reemplaza el flujo existente; solo agrega capacidad de auditoría/ML.
        """
        cursor = self.connection.cursor()

        if world_cup_only:
            cursor.execute(
                "SELECT * FROM training_examples WHERE world_cup_flag = 1 ORDER BY created_at DESC LIMIT ?",
                (safe_int(limit, 500),),
            )
        elif competition_tier:
            cursor.execute(
                "SELECT * FROM training_examples WHERE competition_tier = ? ORDER BY created_at DESC LIMIT ?",
                (str(competition_tier).upper(), safe_int(limit, 500)),
            )
        else:
            cursor.execute(
                "SELECT * FROM training_examples ORDER BY created_at DESC LIMIT ?",
                (safe_int(limit, 500),),
            )

        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_competition_summary(self) -> Dict[str, Any]:
        """
        Resumen rápido para validar que los nuevos campos estén llegando al storage.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                COALESCE(competition_tier, 'UNKNOWN') AS tier,
                COUNT(*) AS total,
                SUM(CASE WHEN world_cup_flag = 1 THEN 1 ELSE 0 END) AS world_cup,
                SUM(CASE WHEN national_team_flag = 1 THEN 1 ELSE 0 END) AS national_team,
                AVG(COALESCE(competition_weight, 0)) AS avg_weight
            FROM prediction_features
            GROUP BY COALESCE(competition_tier, 'UNKNOWN')
            ORDER BY total DESC
            """
        )
        feature_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                COALESCE(competition_tier, 'UNKNOWN') AS tier,
                COUNT(*) AS total,
                SUM(CASE WHEN world_cup_flag = 1 THEN 1 ELSE 0 END) AS world_cup,
                SUM(CASE WHEN national_team_flag = 1 THEN 1 ELSE 0 END) AS national_team,
                AVG(COALESCE(competition_weight, 0)) AS avg_weight
            FROM training_examples
            GROUP BY COALESCE(competition_tier, 'UNKNOWN')
            ORDER BY total DESC
            """
        )
        training_rows = cursor.fetchall()

        return {
            "features_by_competition": [dict(row) for row in feature_rows],
            "training_by_competition": [dict(row) for row in training_rows],
        }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        for key in [
            "feature_vector_json",
            "match_snapshot_json",
            "pre_match_snapshot_json",
            "context_snapshot_json",
            "tactical_snapshot_json",
            "market_snapshot_json",
            "risk_snapshot_json",
            "prediction_snapshot_json",
            "metadata_json",
            "resolution_snapshot_json",
        ]:
            if key in data:
                data[key.replace("_json", "")] = self._load(data.get(key))
                data.pop(key, None)
        return data