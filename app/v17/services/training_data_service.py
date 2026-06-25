from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().upper()
    return text in {"1", "TRUE", "YES", "Y", "SI", "SÍ"}


class TrainingDataService:
    """
    Servicio mínimo y seguro para recolectar datos de entrenamiento V17.

    Mantiene la estructura original:
    - record_publication(signal)
    - record_resolution(resolved)

    Mejora V17:
    - Añade metadata competitiva para Mundial, selecciones y torneos elite.
    - Añade snapshots compactos para consultas rápidas sin romper el snapshot completo.
    - Mantiene compatibilidad con datos antiguos.
    - Nunca rompe runtime si falla escritura/lectura.
    """

    STORAGE_DIR = Path("app/v17/storage")
    STORAGE_FILE = STORAGE_DIR / "training_data.jsonl"

    def __init__(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _append(self, payload: Dict[str, Any]) -> None:
        try:
            with self.STORAGE_FILE.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception:
            # Best-effort only: training data must never break the live engine.
            pass

    def record_publication(self, signal: Dict[str, Any]) -> None:
        signal = signal or {}
        event = {
            "event": "published",
            "at": utc_now_iso(),
            "match_id": str(signal.get("match_id") or signal.get("fixture_id") or ""),
            "signal_key": signal.get("signal_key") or signal.get("signal_id") or None,
            "market": self._market(signal),
            "competition": self._competition_metadata(signal),
            "prediction": self._prediction_metadata(signal),
            "model": self._model_metadata(signal),
            "compact": self._compact_snapshot(signal),
            "snapshot": signal,
        }
        self._append(event)

    def record_resolution(self, resolved: Dict[str, Any]) -> None:
        resolved = resolved or {}
        event = {
            "event": "resolved",
            "at": utc_now_iso(),
            "match_id": str(resolved.get("match_id") or resolved.get("fixture_id") or ""),
            "signal_key": resolved.get("signal_key") or resolved.get("signal_id") or None,
            "market": self._market(resolved),
            "result_status": resolved.get("result_status") or resolved.get("tracking_status"),
            "result_label": resolved.get("result_label"),
            "result_reason": resolved.get("result_reason"),
            "competition": self._competition_metadata(resolved),
            "prediction": self._prediction_metadata(resolved),
            "model": self._model_metadata(resolved),
            "compact": self._compact_snapshot(resolved),
            "snapshot": resolved,
        }
        self._append(event)

    def get_recent_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Devuelve eventos recientes para auditoría/diagnóstico.
        No es obligatorio para el motor, pero ayuda al panel y al debug.
        """
        try:
            if not self.STORAGE_FILE.exists():
                return []

            lines = self.STORAGE_FILE.read_text(encoding="utf-8").splitlines()
            selected = lines[-max(1, int(limit)):]
            events: List[Dict[str, Any]] = []

            for line in selected:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        events.append(item)
                except Exception:
                    continue

            return events
        except Exception:
            return []

    def get_summary(self, limit: int = 2000) -> Dict[str, Any]:
        """
        Resumen seguro para revisar si el entrenamiento recibe datos útiles.
        Compatible con registros antiguos que no tengan metadata competitiva.
        """
        events = self.get_recent_events(limit=limit)

        by_event = Counter(str(x.get("event") or "UNKNOWN") for x in events)
        by_market = Counter(str(x.get("market") or "UNKNOWN") for x in events)
        by_competition = Counter(
            str((x.get("competition") or {}).get("competition_tier") or "UNKNOWN")
            for x in events
        )

        world_cup_events = 0
        national_team_events = 0
        major_tournament_events = 0

        for item in events:
            competition = item.get("competition") or {}
            if safe_bool(competition.get("world_cup_flag")):
                world_cup_events += 1
            if safe_bool(competition.get("national_team_flag")):
                national_team_events += 1
            if safe_bool(competition.get("major_tournament_flag")):
                major_tournament_events += 1

        return {
            "total_events": len(events),
            "by_event": dict(by_event),
            "by_market": dict(by_market),
            "by_competition_tier": dict(by_competition),
            "world_cup_events": world_cup_events,
            "national_team_events": national_team_events,
            "major_tournament_events": major_tournament_events,
            "storage_file": str(self.STORAGE_FILE),
        }

    def _competition_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "competition_tier": str(payload.get("competition_tier") or "UNKNOWN"),
            "competition_weight": safe_float(payload.get("competition_weight"), 0.0),
            "world_cup_flag": safe_bool(payload.get("world_cup_flag")),
            "national_team_flag": safe_bool(payload.get("national_team_flag")),
            "major_tournament_flag": safe_bool(payload.get("major_tournament_flag")),
            "league_filter_status": str(payload.get("league_filter_status") or ""),
            "league_filter_reason": str(payload.get("league_filter_reason") or ""),
            "league": str(payload.get("league") or ""),
            "country": str(payload.get("country") or ""),
        }

    def _prediction_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "prediction_mode": payload.get("prediction_mode"),
            "prediction_scenario": payload.get("prediction_scenario"),
            "prediction_market": payload.get("prediction_market"),
            "prediction_score": payload.get("prediction_score"),
            "prediction_alternative_score": payload.get("prediction_alternative_score"),
            "prediction_halftime_score": payload.get("prediction_halftime_score"),
            "prediction_final_score": payload.get("prediction_final_score"),
            "prediction_confidence": payload.get("prediction_confidence"),
            "prediction_market_alignment": payload.get("prediction_market_alignment"),
        }

    def _model_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "model_id": payload.get("model_id"),
            "predicted_class": payload.get("predicted_class"),
            "predicted_probability": payload.get("predicted_probability"),
            "has_prediction": payload.get("has_prediction"),
        }

    def _compact_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "home_team": payload.get("home_team"),
            "away_team": payload.get("away_team"),
            "league": payload.get("league"),
            "country": payload.get("country"),
            "api_minute": payload.get("api_minute"),
            "display_minute": payload.get("display_minute"),
            "estimated_minute": payload.get("estimated_minute"),
            "scoreline": payload.get("scoreline") or payload.get("current_score"),
            "market": self._market(payload),
            "master_status": payload.get("master_status"),
            "master_rank": payload.get("master_rank"),
            "master_confidence": payload.get("master_confidence"),
            "elite_score": payload.get("elite_score"),
            "elite_rank": payload.get("elite_rank"),
            "risk_status": payload.get("risk_status"),
            "risk_score": payload.get("risk_score"),
            "clock_status": payload.get("clock_status"),
            "data_quality": payload.get("data_quality"),
            "result_status": payload.get("result_status"),
            "result_label": payload.get("result_label"),
        }

    def _market(self, payload: Dict[str, Any]) -> str:
        for key in [
            "market_direction",
            "market",
            "master_market",
            "suggested_market",
            "promotion_market",
            "activation_market",
            "prediction_market",
        ]:
            value = str(payload.get(key) or "").upper()
            if "OVER" in value:
                return "OVER"
            if "UNDER" in value or "BAJO" in value:
                return "UNDER"
        return "OTHER"