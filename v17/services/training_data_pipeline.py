from __future__ import annotations

from typing import Any, Dict, Optional

from app.v17.services.prediction_feature_store import PredictionFeatureStore


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


def safe_str(value: Any) -> str:
    return str(value or "")


def bool_to_int(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0

    text = str(value or "").strip().upper()
    if text in {"1", "TRUE", "YES", "SI", "SÍ", "Y"}:
        return 1

    return 0


class TrainingDataPipeline:
    """
    Pipeline de entrenamiento V17.

    Recibe señales resueltas y genera ejemplos de entrenamiento duraderos.

    Mejora V17:
    - Conserva contexto competitivo dentro del ejemplo de entrenamiento.
    - Evita que Mundial, selecciones o torneos elite queden mezclados con ligas comunes.
    - Mantiene compatibilidad con bases/feature stores antiguos porque los campos nuevos
      también viajan dentro de feature_vector, prediction_snapshot y resolution_snapshot.
    """

    def __init__(self, feature_store: PredictionFeatureStore) -> None:
        self.feature_store = feature_store

    def record_resolution(self, resolved_signal: Dict[str, Any]) -> None:
        if not isinstance(resolved_signal, dict):
            return

        fixture_id = str(
            resolved_signal.get("fixture_id")
            or resolved_signal.get("match_id")
            or ""
        ).strip()
        if not fixture_id:
            return

        entry_minute = safe_int(resolved_signal.get("entry_minute") or resolved_signal.get("api_minute"), 0)
        if entry_minute < 0:
            entry_minute = 0

        feature_row = self.feature_store.get_features(fixture_id, entry_minute)
        if feature_row is None:
            history = self.feature_store.get_history(fixture_id, since_minute=entry_minute, limit=1)
            feature_row = history[0] if history else None

        competition_snapshot = self._build_competition_snapshot(
            signal=resolved_signal,
            feature_row=feature_row,
        )

        feature_vector = self._merge_competition_into_feature_vector(
            feature_vector=feature_row.get("feature_vector") if feature_row else {},
            competition_snapshot=competition_snapshot,
        )

        prediction_snapshot = self._build_prediction_snapshot(resolved_signal, competition_snapshot)
        resolution_snapshot = self._build_resolution_snapshot(resolved_signal, competition_snapshot)

        example_payload = {
            "fixture_id": fixture_id,
            "signal_key": safe_str(resolved_signal.get("signal_key") or resolved_signal.get("signal_id")),
            "entry_minute": entry_minute,
            "result_status": safe_str(resolved_signal.get("result_status") or "PENDING").upper(),
            "label": safe_str(resolved_signal.get("result_status") or "PENDING").upper(),
            "feature_vector": feature_vector,
            "prediction_snapshot": prediction_snapshot,
            "resolution_snapshot": resolution_snapshot,
            "match_snapshot": feature_row.get("match_snapshot") if feature_row else {},
            "pre_match_snapshot": feature_row.get("pre_match_snapshot") if feature_row else {},
            "competition_snapshot": competition_snapshot,
            "metadata": {
                **competition_snapshot,
                "source": "TRAINING_DATA_PIPELINE_V17",
            },
        }

        self.feature_store.save_training_example(example_payload)

    def _build_competition_snapshot(
        self,
        signal: Dict[str, Any],
        feature_row: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        feature_row = feature_row or {}
        metadata = feature_row.get("metadata") if isinstance(feature_row.get("metadata"), dict) else {}
        match_snapshot = feature_row.get("match_snapshot") if isinstance(feature_row.get("match_snapshot"), dict) else {}

        competition_tier = safe_str(
            signal.get("competition_tier")
            or metadata.get("competition_tier")
            or match_snapshot.get("competition_tier")
            or "UNKNOWN"
        ).upper()

        competition_weight = safe_float(
            signal.get("competition_weight")
            or metadata.get("competition_weight")
            or match_snapshot.get("competition_weight"),
            0.0,
        )

        world_cup_flag = bool_to_int(
            signal.get("world_cup_flag")
            or metadata.get("world_cup_flag")
            or match_snapshot.get("world_cup_flag")
        )

        national_team_flag = bool_to_int(
            signal.get("national_team_flag")
            or metadata.get("national_team_flag")
            or match_snapshot.get("national_team_flag")
        )

        major_tournament_flag = bool_to_int(
            signal.get("major_tournament_flag")
            or metadata.get("major_tournament_flag")
            or match_snapshot.get("major_tournament_flag")
        )

        return {
            "competition_tier": competition_tier,
            "competition_weight": competition_weight,
            "world_cup_flag": world_cup_flag,
            "national_team_flag": national_team_flag,
            "major_tournament_flag": major_tournament_flag,
            "league_filter_status": safe_str(
                signal.get("league_filter_status")
                or metadata.get("league_filter_status")
                or match_snapshot.get("league_filter_status")
            ),
            "league_filter_reason": safe_str(
                signal.get("league_filter_reason")
                or metadata.get("league_filter_reason")
                or match_snapshot.get("league_filter_reason")
            ),
            "league": safe_str(
                signal.get("league")
                or metadata.get("league")
                or match_snapshot.get("league")
            ),
            "country": safe_str(
                signal.get("country")
                or metadata.get("country")
                or match_snapshot.get("country")
            ),
        }

    def _merge_competition_into_feature_vector(
        self,
        feature_vector: Any,
        competition_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        vector = dict(feature_vector) if isinstance(feature_vector, dict) else {}

        tier = safe_str(competition_snapshot.get("competition_tier")).upper()

        vector.setdefault("competition_weight", safe_float(competition_snapshot.get("competition_weight"), 0.0))
        vector.setdefault("world_cup_flag", bool_to_int(competition_snapshot.get("world_cup_flag")))
        vector.setdefault("national_team_flag", bool_to_int(competition_snapshot.get("national_team_flag")))
        vector.setdefault("major_tournament_flag", bool_to_int(competition_snapshot.get("major_tournament_flag")))

        vector.setdefault("competition_tier_world_cup", 1 if "WORLD_CUP" in tier else 0)
        vector.setdefault("competition_tier_international_elite", 1 if "INTERNATIONAL" in tier or "NATIONAL_TEAM" in tier else 0)
        vector.setdefault("competition_tier_priority_league", 1 if "PRIORITY" in tier else 0)
        vector.setdefault("competition_tier_country_review", 1 if "COUNTRY_REVIEW" in tier else 0)

        return vector

    def _build_prediction_snapshot(
        self,
        signal: Dict[str, Any],
        competition_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        competition_snapshot = competition_snapshot or {}

        return {
            "prediction_market": safe_str(signal.get("prediction_market")),
            "prediction_confidence": safe_float(signal.get("prediction_confidence"), 0.0),
            "prediction_scenario": safe_str(signal.get("prediction_scenario")),
            "prediction_mode": safe_str(signal.get("prediction_mode")),
            "prediction_next_goal_probability": safe_str(signal.get("prediction_next_goal_probability")),
            "prediction_score": safe_str(signal.get("prediction_score")),
            "prediction_alternative_score": safe_str(signal.get("prediction_alternative_score")),
            "prediction_halftime_score": safe_str(signal.get("prediction_halftime_score")),
            "prediction_final_score": safe_str(signal.get("prediction_final_score")),
            "prediction_market_alignment": safe_str(signal.get("prediction_market_alignment")),
            "prediction_panel_message": safe_str(signal.get("prediction_panel_message")),
            "competition_tier": safe_str(competition_snapshot.get("competition_tier")),
            "competition_weight": safe_float(competition_snapshot.get("competition_weight"), 0.0),
            "world_cup_flag": bool_to_int(competition_snapshot.get("world_cup_flag")),
            "national_team_flag": bool_to_int(competition_snapshot.get("national_team_flag")),
            "major_tournament_flag": bool_to_int(competition_snapshot.get("major_tournament_flag")),
        }

    def _build_resolution_snapshot(
        self,
        signal: Dict[str, Any],
        competition_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        competition_snapshot = competition_snapshot or {}

        return {
            "result_status": safe_str(signal.get("result_status")),
            "result_reason": safe_str(signal.get("result_reason")),
            "result_label": safe_str(signal.get("result_label")),
            "resolved": bool(signal.get("resolved")),
            "resolved_at": safe_str(signal.get("resolved_at")),
            "current_score": safe_str(signal.get("current_score") or signal.get("current_scoreline") or ""),
            "current_total_goals": safe_int(signal.get("current_total_goals"), 0),
            "tracking_status": safe_str(signal.get("tracking_status")),
            "market": safe_str(signal.get("market") or signal.get("market_direction") or signal.get("master_market")),
            "master_status": safe_str(signal.get("master_status")),
            "elite_rank": safe_str(signal.get("elite_rank")),
            "elite_score": safe_float(signal.get("elite_score"), 0.0),
            "competition_tier": safe_str(competition_snapshot.get("competition_tier")),
            "competition_weight": safe_float(competition_snapshot.get("competition_weight"), 0.0),
            "world_cup_flag": bool_to_int(competition_snapshot.get("world_cup_flag")),
            "national_team_flag": bool_to_int(competition_snapshot.get("national_team_flag")),
            "major_tournament_flag": bool_to_int(competition_snapshot.get("major_tournament_flag")),
            "league_filter_status": safe_str(competition_snapshot.get("league_filter_status")),
        }