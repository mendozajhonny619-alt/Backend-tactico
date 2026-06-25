from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.v17.signals.learning_memory import LearningMemory
from app.v17.signals.result_resolver import ResultResolver
from app.v17.services.training_data_service import TrainingDataService
from app.v17.services.prediction_feature_store import PredictionFeatureStore
from app.v17.services.training_data_pipeline import TrainingDataPipeline
from app.v17.services.model_prediction_service import ModelPredictionService
from app.v17.ml.model_registry import ModelRegistry


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



def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().upper()
    return text in {"1", "TRUE", "YES", "SI", "SÍ", "ON"}

def normalize_market(value: Any) -> str:
    """
    Normaliza el mercado para tracking.

    El historial no debe guardar solo ENTER, OPERABLE u OBSERVE.
    Debe guardar si la señal real fue OVER o UNDER.
    """

    text = str(value or "").upper()

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    if "SOBRE" in text:
        return "OVER"

    if "BAJO" in text:
        return "UNDER"

    return "OTHER"


class SignalTracker:
    """
    Tracking de señales V17.

    Funciones:
    - registra señales publicadas
    - evita duplicados por partido y mercado
    - mantiene pendientes
    - resuelve resultados
    - guarda aprendizaje
    - separa rendimiento por OVER y UNDER
    """

    def __init__(self, max_pending: int = 100) -> None:
        self.max_pending = max_pending
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._closed: List[Dict[str, Any]] = []

        self.resolver = ResultResolver()
        self.learning_memory = LearningMemory()
        self.training_service = TrainingDataService()
        self.prediction_feature_store = PredictionFeatureStore()
        self.training_pipeline = TrainingDataPipeline(self.prediction_feature_store)
        
        # Phase 3: Model feedback recording
        from pathlib import Path
        storage_dir = str(Path(__file__).parent.parent.parent / "v17" / "storage")
        self.model_registry = ModelRegistry(storage_dir)
        self.model_prediction_service = ModelPredictionService(
            self.model_registry,
            feedback_storage_dir=storage_dir
        )

    def register_published_signals(self, top_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        registered: List[Dict[str, Any]] = []

        for signal in top_signals or []:
            if not isinstance(signal, dict):
                continue

            if not signal.get("can_publish"):
                continue

            market_direction = self._extract_market_direction(signal)

            if market_direction not in {"OVER", "UNDER"}:
                continue

            signal_key = self._stable_signal_key(signal, market_direction)

            if not signal_key:
                continue

            signal = deepcopy(signal)
            signal["signal_key"] = signal_key
            signal["market"] = market_direction
            signal["market_direction"] = market_direction

            if signal_key in self._pending:
                existing = self._pending[signal_key]
                existing.update(self._refresh_tracking_view(existing, signal))
                registered.append(deepcopy(existing))
                continue

            tracked = self._create_tracking_record(signal)
            self._pending[signal_key] = tracked
            registered.append(deepcopy(tracked))

            try:
                self.training_service.record_publication(tracked)
            except Exception:
                # best-effort, do not break tracking
                pass

        self._trim_pending()
        return registered

    def update_with_live_matches(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        match_index = self._build_match_index(live_matches)

        still_pending: Dict[str, Dict[str, Any]] = {}
        newly_closed: List[Dict[str, Any]] = []

        for signal_key, tracked in list(self._pending.items()):
            match_id = str(tracked.get("match_id") or tracked.get("fixture_id") or "")

            current_match = match_index.get(match_id)

            if not current_match:
                tracked["tracking_status"] = "PENDING"
                tracked["pending_reason"] = "MATCH_NOT_FOUND_IN_LIVE_SNAPSHOT"
                still_pending[signal_key] = tracked
                continue

            resolved = self.resolver.resolve(tracked, current_match)

            resolved["market"] = tracked.get("market") or tracked.get("market_direction") or "OTHER"
            resolved["market_direction"] = normalize_market(resolved.get("market"))
            resolved["signal_key"] = signal_key

            if resolved.get("resolved"):
                resolved["tracking_status"] = "CLOSED"
                newly_closed.append(deepcopy(resolved))
                self._closed.insert(0, deepcopy(resolved))
                self.learning_memory.add_result(resolved)
                try:
                    self.training_service.record_resolution(resolved)
                except Exception:
                    pass
                try:
                    self.training_pipeline.record_resolution(resolved)
                except Exception:
                    pass
                
                # Phase 3: Record model feedback for performance tracking
                try:
                    signal_key_str = str(resolved.get("signal_key") or "")
                    fixture_id = str(resolved.get("match_id") or resolved.get("fixture_id") or "")
                    league = str(resolved.get("league") or "UNKNOWN")
                    market = normalize_market(resolved.get("market"))
                    market_category = str(resolved.get("market_category") or "GENERAL")
                    actual_result = str(resolved.get("result_status") or "UNRESOLVED").upper()

                    # V17 Competition Intelligence:
                    # se conserva en el registro resuelto para análisis y aprendizaje posterior.
                    # No se pasa como argumento extra para no romper ModelPredictionService
                    # si su firma todavía no lo soporta.
                    resolved["competition_tier"] = str(resolved.get("competition_tier") or "UNKNOWN")
                    resolved["competition_weight"] = safe_float(resolved.get("competition_weight"), 0.0)
                    resolved["world_cup_flag"] = safe_bool(resolved.get("world_cup_flag"))
                    resolved["national_team_flag"] = safe_bool(resolved.get("national_team_flag"))
                    resolved["major_tournament_flag"] = safe_bool(resolved.get("major_tournament_flag"))

                    self.model_prediction_service.record_feedback(
                        signal_key=signal_key_str,
                        fixture_id=fixture_id,
                        league=league,
                        market=market,
                        market_category=market_category,
                        actual_result=actual_result,
                        current_score=resolved.get("current_score"),
                        current_total_goals=resolved.get("current_total_goals")
                    )
                except Exception:
                    pass  # Don't break resolution if feedback recording fails
            else:
                resolved["tracking_status"] = "PENDING"
                still_pending[signal_key] = resolved

        self._pending = still_pending
        self._closed = self._closed[:500]

        return {
            "pending": self.pending(),
            "closed": self.closed(),
            "newly_closed": newly_closed,
            "summary": self.summary(),
            "learning": self.learning_memory.summary(),
            "performance_analysis": self.learning_memory.performance_analysis(),
        }

    def pending(self) -> List[Dict[str, Any]]:
        return sorted(
            [deepcopy(x) for x in self._pending.values()],
            key=lambda x: safe_int(x.get("entry_minute"), 0),
            reverse=True,
        )

    def closed(self, limit: int = 100) -> List[Dict[str, Any]]:
        return deepcopy(self._closed[:limit])

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        items = self.closed(limit=limit) + self.pending()
        return items[:limit]

    def summary(self) -> Dict[str, Any]:
        pending = len(self._pending)
        closed = len(self._closed)

        wins = sum(1 for x in self._closed if x.get("result_status") == "WON")
        losses = sum(1 for x in self._closed if x.get("result_status") == "LOST")
        voids = sum(1 for x in self._closed if x.get("result_status") == "VOID")

        precision = round((wins / max(1, wins + losses)) * 100, 2)

        by_market = self._summary_by_market()
        by_competition_tier = self._summary_by_competition_tier()

        return {
            "pending": pending,
            "closed": closed,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "precision": precision,
            "total_tracked": pending + closed,
            "by_market": by_market,
            "by_competition_tier": by_competition_tier,
            "over": by_market.get("OVER", {}),
            "under": by_market.get("UNDER", {}),
        }

    def get_tracking_summary(self) -> Dict[str, Any]:
        return self.summary()

    def get_tracking_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history(limit=limit)

    def get_performance_analysis(self) -> Dict[str, Any]:
        return self.learning_memory.performance_analysis()

    def _create_tracking_record(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        entry_minute = safe_int(
            signal.get("api_minute")
            or signal.get("display_minute")
            or signal.get("minute")
            or signal.get("current_minute"),
            0,
        )

        entry_home_score = safe_int(
            signal.get("home_score")
            or signal.get("current_home_score")
            or signal.get("entry_home_score"),
            0,
        )

        entry_away_score = safe_int(
            signal.get("away_score")
            or signal.get("current_away_score")
            or signal.get("entry_away_score"),
            0,
        )

        market_direction = self._extract_market_direction(signal)

        max_follow_minutes = 20

        if market_direction == "UNDER":
            max_follow_minutes = 18

        if entry_minute >= 80:
            max_follow_minutes = 12

        if entry_minute >= 88:
            max_follow_minutes = 8

        signal_key = self._stable_signal_key(signal, market_direction)

        return {
            **deepcopy(signal),
            "signal_key": signal_key,
            "tracking_status": "PENDING",
            "result_status": "PENDING",
            "result_label": "PENDIENTE",
            "registered_at": utc_now_iso(),
            "last_seen_at": utc_now_iso(),
            "entry_minute": entry_minute,
            "entry_home_score": entry_home_score,
            "entry_away_score": entry_away_score,
            "entry_score": f"{entry_home_score}-{entry_away_score}",
            "entry_total_goals": entry_home_score + entry_away_score,
            "market": market_direction,
            "market_direction": market_direction,
            "max_follow_minutes": max_follow_minutes,

            # V17 Competition Intelligence para aprendizaje y estadísticas.
            "competition_tier": str(signal.get("competition_tier") or "UNKNOWN"),
            "competition_weight": safe_float(signal.get("competition_weight"), 0.0),
            "world_cup_flag": safe_bool(signal.get("world_cup_flag")),
            "national_team_flag": safe_bool(signal.get("national_team_flag")),
            "major_tournament_flag": safe_bool(signal.get("major_tournament_flag")),
            "league_filter_status": signal.get("league_filter_status"),
            "league_filter_reason": signal.get("league_filter_reason"),

            # Predicción y ML conservados para análisis posterior.
            "prediction_market_alignment": signal.get("prediction_market_alignment"),
            "prediction_score": signal.get("prediction_score"),
            "prediction_alternative_score": signal.get("prediction_alternative_score"),
            "prediction_final_score": signal.get("prediction_final_score"),
            "prediction_confidence": signal.get("prediction_confidence"),
            "model_id": signal.get("model_id"),
            "predicted_class": signal.get("predicted_class"),
            "predicted_probability": signal.get("predicted_probability"),

            "resolved": False,
            "resolved_at": None,
            "result_reason": "TRACKING_STARTED",
            "result_explanation": (
                f"La señal {market_direction} fue publicada y se encuentra en seguimiento."
            ),
        }

    def _refresh_tracking_view(
        self,
        existing: Dict[str, Any],
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Actualiza lectura visual de una señal pendiente sin borrar su entrada original.

        Importante:
        No se modifica entry_minute ni entry_score, porque son el punto real
        donde la señal empezó a seguirse.
        """

        keep_fields = {
            "registered_at",
            "entry_minute",
            "entry_home_score",
            "entry_away_score",
            "entry_score",
            "entry_total_goals",
            "max_follow_minutes",
            "result_status",
            "result_label",
            "tracking_status",
            "resolved",
            "resolved_at",
            "market",
            "market_direction",
            "signal_key",
            "competition_tier",
            "competition_weight",
            "world_cup_flag",
            "national_team_flag",
            "major_tournament_flag",
            "league_filter_status",
            "league_filter_reason",
        }

        refreshed = deepcopy(existing)

        for key, value in signal.items():
            if key not in keep_fields:
                refreshed[key] = value

        refreshed["last_seen_at"] = utc_now_iso()
        refreshed["tracking_status"] = "PENDING"
        refreshed["result_status"] = "PENDING"
        refreshed["market"] = existing.get("market") or existing.get("market_direction") or self._extract_market_direction(signal)
        refreshed["market_direction"] = normalize_market(refreshed.get("market"))

        return refreshed

    def _build_match_index(self, live_matches: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        index: Dict[str, Dict[str, Any]] = {}

        for match in live_matches or []:
            if not isinstance(match, dict):
                continue

            match_id = str(match.get("match_id") or match.get("fixture_id") or "")
            if match_id:
                index[match_id] = match

        return index

    def _summary_by_market(self) -> Dict[str, Dict[str, Any]]:
        markets = {
            "OVER": self._empty_market_summary("OVER"),
            "UNDER": self._empty_market_summary("UNDER"),
            "OTHER": self._empty_market_summary("OTHER"),
        }

        for item in self._pending.values():
            market = normalize_market(item.get("market") or item.get("market_direction"))
            markets.setdefault(market, self._empty_market_summary(market))
            markets[market]["pending"] += 1
            markets[market]["total"] += 1

        for item in self._closed:
            market = normalize_market(item.get("market") or item.get("market_direction"))
            markets.setdefault(market, self._empty_market_summary(market))

            markets[market]["closed"] += 1
            markets[market]["total"] += 1

            result_status = str(item.get("result_status") or "").upper()

            if result_status == "WON":
                markets[market]["wins"] += 1
            elif result_status == "LOST":
                markets[market]["losses"] += 1
            elif result_status == "VOID":
                markets[market]["voids"] += 1

        for market, data in markets.items():
            wins = data["wins"]
            losses = data["losses"]
            data["precision"] = round((wins / max(1, wins + losses)) * 100, 2)
            data["open_precision"] = round((wins / max(1, data["closed"])) * 100, 2)

        return markets

    def _summary_by_competition_tier(self) -> Dict[str, Dict[str, Any]]:
        tiers: Dict[str, Dict[str, Any]] = {}

        for item in self._pending.values():
            tier = str(item.get("competition_tier") or "UNKNOWN").upper()
            tiers.setdefault(tier, self._empty_competition_summary(tier))
            tiers[tier]["pending"] += 1
            tiers[tier]["total"] += 1

        for item in self._closed:
            tier = str(item.get("competition_tier") or "UNKNOWN").upper()
            tiers.setdefault(tier, self._empty_competition_summary(tier))

            tiers[tier]["closed"] += 1
            tiers[tier]["total"] += 1

            result_status = str(item.get("result_status") or "").upper()

            if result_status == "WON":
                tiers[tier]["wins"] += 1
            elif result_status == "LOST":
                tiers[tier]["losses"] += 1
            elif result_status == "VOID":
                tiers[tier]["voids"] += 1

        for tier, data in tiers.items():
            wins = data["wins"]
            losses = data["losses"]
            data["precision"] = round((wins / max(1, wins + losses)) * 100, 2)
            data["open_precision"] = round((wins / max(1, data["closed"])) * 100, 2)

        return tiers

    def _empty_competition_summary(self, tier: str) -> Dict[str, Any]:
        return {
            "competition_tier": tier,
            "total": 0,
            "pending": 0,
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "voids": 0,
            "precision": 0.0,
            "open_precision": 0.0,
        }

    def _empty_market_summary(self, market: str) -> Dict[str, Any]:
        return {
            "market": market,
            "total": 0,
            "pending": 0,
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "voids": 0,
            "precision": 0.0,
            "open_precision": 0.0,
        }

    def _extract_market_direction(self, signal: Dict[str, Any]) -> str:
        raw_market = (
            signal.get("market_direction")
            or signal.get("market")
            or signal.get("master_market")
            or signal.get("suggested_market")
            or signal.get("market_category")
            or signal.get("context_category")
            or ""
        )

        return normalize_market(raw_market)

    def _stable_signal_key(self, signal: Dict[str, Any], market_direction: str) -> str:
        """
        Crea una clave estable por partido y mercado.

        Antes el sistema podía duplicar señales porque la key cambiaba con el minuto.
        Ahora una señal OVER o UNDER del mismo partido se actualiza, no se duplica.
        """

        match_id = str(
            signal.get("match_id")
            or signal.get("fixture_id")
            or signal.get("id")
            or ""
        ).strip()

        if not match_id:
            return str(signal.get("signal_key") or signal.get("signal_id") or "").strip()

        return f"V17:{match_id}:{market_direction}"

    def _trim_pending(self) -> None:
        if len(self._pending) <= self.max_pending:
            return

        items = sorted(
            self._pending.items(),
            key=lambda kv: safe_int(kv[1].get("entry_minute"), 0),
            reverse=True,
        )

        self._pending = dict(items[: self.max_pending])
