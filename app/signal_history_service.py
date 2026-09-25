from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def normalize_text(value: Any) -> str:
    return str(value or "").strip().upper()


class SignalHistoryService:
    """
    Servicio persistente de historial de señales V17.

    Objetivo:
    - Guardar señales detectadas.
    - Guardar candidatos fuertes aunque no sean señal principal.
    - Guardar EARLY_OVER_CANDIDATE como candidato temprano rastreable.
    - Guardar observaciones altas importantes.
    - Guardar bloqueos importantes para revisar si el bloqueo fue correcto.
    - Mantener señales principales y top signals.
    - Evitar que las señales desaparezcan del panel de resultados.
    - Actualizar una misma señal cuando evoluciona de observación a candidato fuerte o señal principal.
    - Dejar base para evaluar aciertos y fallos cuando el partido termine.

    Este servicio no decide señales.
    Solo registra, actualiza y devuelve historial.
    """

    VERSION = "V17_SIGNAL_HISTORY_SERVICE_3"

    STORAGE_DIR = Path("app/v17/storage")
    STORAGE_FILE = STORAGE_DIR / "signal_history.json"

    LEVEL_PRIORITY = {
        "BLOCKED": 5,
        "OBSERVE_ONLY": 10,
        "WAIT_REVALIDATION": 20,
        "OBSERVATION": 25,
        "HIGH_OBSERVATION": 35,
        "OVER_HIGH_OBSERVATION": 40,
        "EARLY_OVER_CANDIDATE": 45,
        "STRONG_CANDIDATE": 60,
        "MAIN_SIGNAL": 80,
        "TOP_SIGNAL": 100,
    }

    TRACKING_TYPE_BY_LEVEL = {
        "TOP_SIGNAL": "OPERATIVE_SIGNAL",
        "MAIN_SIGNAL": "OPERATIVE_SIGNAL",
        "STRONG_CANDIDATE": "CANDIDATE_SIGNAL",
        "EARLY_OVER_CANDIDATE": "EARLY_CANDIDATE_SIGNAL",
        "OVER_HIGH_OBSERVATION": "HIGH_OBSERVATION_SIGNAL",
        "HIGH_OBSERVATION": "HIGH_OBSERVATION_SIGNAL",
        "WAIT_REVALIDATION": "REVALIDATION_SIGNAL",
        "OBSERVATION": "OBSERVATION_SIGNAL",
        "OBSERVE_ONLY": "OBSERVATION_SIGNAL",
        "BLOCKED": "BLOCKED_SIGNAL",
    }

    RESULT_PENDING = "PENDING"
    RESULT_WON = "WON"
    RESULT_LOST = "LOST"
    RESULT_EXPIRED = "EXPIRED"
    RESULT_CANCELLED = "CANCELLED"
    RESULT_UNKNOWN = "UNKNOWN"

    def __init__(self) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self._ensure_storage()

    def register_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra o actualiza una señal.

        La señal ya no necesita llegar a MAIN_SIGNAL o TOP_SIGNAL para entrar al historial.
        Si llega a STRONG_CANDIDATE, EARLY_OVER_CANDIDATE, OVER_HIGH_OBSERVATION
        o BLOCKED con lectura relevante, queda registrada y visible para seguimiento.
        """

        if not isinstance(signal, dict):
            return {
                "history_ok": False,
                "history_error": "INVALID_SIGNAL",
            }

        if not self._should_store(signal):
            return {
                "history_ok": True,
                "history_action": "IGNORED_NOT_RELEVANT",
                "history_signal_id": None,
            }

        data = self._load()
        records = data.get("records", [])

        signal_id = self._build_history_id(signal)
        now = utc_now_iso()

        existing = self._find_record(records, signal_id)

        if existing is None:
            record = self._create_record(signal=signal, signal_id=signal_id, now=now)
            records.append(record)

            data["records"] = records
            data["updated_at"] = now
            self._save(data)

            return {
                "history_ok": True,
                "history_action": "CREATED",
                "history_signal_id": signal_id,
                "history_record": record,
            }

        updated = self._update_record(existing=existing, signal=signal, now=now)

        data["records"] = records
        data["updated_at"] = now
        self._save(data)

        return {
            "history_ok": True,
            "history_action": "UPDATED",
            "history_signal_id": signal_id,
            "history_record": updated,
        }

    def get_results(
        self,
        limit: int = 100,
        include_observation: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve resultados visibles para el panel.

        Por defecto muestra:
        - Señales principales.
        - Top signals.
        - Candidatos fuertes.
        - Candidatos tempranos OVER.
        - Bloqueadas importantes.

        Las observaciones simples solo se muestran si include_observation=True.
        """

        data = self._load()
        records = data.get("records", [])

        visible: List[Dict[str, Any]] = []

        for record in records:
            best_level = normalize_text(record.get("best_promotion_level"))
            tracking_type = normalize_text(record.get("tracking_type"))

            if include_observation:
                visible.append(record)
                continue

            if best_level in {
                "EARLY_OVER_CANDIDATE",
                "STRONG_CANDIDATE",
                "MAIN_SIGNAL",
                "TOP_SIGNAL",
                "BLOCKED",
            }:
                visible.append(record)
                continue

            if tracking_type in {
                "EARLY_CANDIDATE_SIGNAL",
                "CANDIDATE_SIGNAL",
                "OPERATIVE_SIGNAL",
                "BLOCKED_SIGNAL",
            }:
                visible.append(record)

        visible.sort(
            key=lambda item: (
                self.LEVEL_PRIORITY.get(normalize_text(item.get("best_promotion_level")), 0),
                str(item.get("last_seen_at") or ""),
            ),
            reverse=True,
        )

        return visible[:limit]

    def get_full_history(self, limit: int = 200) -> List[Dict[str, Any]]:
        data = self._load()
        records = data.get("records", [])

        records.sort(
            key=lambda item: str(item.get("last_seen_at") or ""),
            reverse=True,
        )

        return records[:limit]

    def get_summary(self) -> Dict[str, Any]:
        data = self._load()
        records = data.get("records", [])

        summary = {
            "total_records": len(records),
            "pending": 0,
            "won": 0,
            "lost": 0,
            "expired": 0,
            "cancelled": 0,
            "unknown": 0,
            "top_signals": 0,
            "main_signals": 0,
            "strong_candidates": 0,
            "early_over_candidates": 0,
            "high_observations": 0,
            "blocked_signals": 0,
            "observations": 0,
            "by_market": {},
            "by_competition_tier": {},
        }

        for record in records:
            result_status = normalize_text(record.get("result_status"))
            best_level = normalize_text(record.get("best_promotion_level"))
            market = normalize_text(record.get("market")) or "UNKNOWN"
            competition_tier = normalize_text(record.get("competition_tier")) or "UNKNOWN"

            self._increment_group_summary(summary["by_market"], market, result_status)
            self._increment_group_summary(summary["by_competition_tier"], competition_tier, result_status)

            if result_status == self.RESULT_PENDING:
                summary["pending"] += 1
            elif result_status == self.RESULT_WON:
                summary["won"] += 1
            elif result_status == self.RESULT_LOST:
                summary["lost"] += 1
            elif result_status == self.RESULT_EXPIRED:
                summary["expired"] += 1
            elif result_status == self.RESULT_CANCELLED:
                summary["cancelled"] += 1
            else:
                summary["unknown"] += 1

            if best_level == "TOP_SIGNAL":
                summary["top_signals"] += 1
            elif best_level == "MAIN_SIGNAL":
                summary["main_signals"] += 1
            elif best_level == "STRONG_CANDIDATE":
                summary["strong_candidates"] += 1
            elif best_level == "EARLY_OVER_CANDIDATE":
                summary["early_over_candidates"] += 1
            elif best_level in {"OVER_HIGH_OBSERVATION", "HIGH_OBSERVATION"}:
                summary["high_observations"] += 1
            elif best_level == "BLOCKED":
                summary["blocked_signals"] += 1
            else:
                summary["observations"] += 1

        return summary

    def _should_store(self, signal: Dict[str, Any]) -> bool:
        market = self._detect_market(signal)

        if market not in {"OVER", "UNDER"}:
            return False

        current_level = self._current_level(signal)

        activation_level = normalize_text(signal.get("activation_level"))
        promotion_level = normalize_text(signal.get("promotion_level"))
        master_status = normalize_text(signal.get("master_status"))
        candidate_level = normalize_text(signal.get("candidate_level"))
        over_candidate_level = normalize_text(signal.get("over_candidate_level"))
        panel_section = normalize_text(signal.get("panel_section"))
        panel_signal_type = normalize_text(signal.get("panel_signal_type"))

        can_publish = bool(signal.get("can_publish"))
        should_observe = bool(signal.get("should_observe"))

        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_support_score = safe_float(signal.get("over_support_score"), 0)
        over_support_ratio = safe_float(signal.get("over_support_ratio"), 0)

        if current_level in {
            "BLOCKED",
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
            "OVER_HIGH_OBSERVATION",
            "HIGH_OBSERVATION",
            "WAIT_REVALIDATION",
        }:
            return True

        if activation_level in {
            "BLOCKED",
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            return True

        if promotion_level in {
            "BLOCKED",
            "OBSERVE_ONLY",
            "WAIT_REVALIDATION",
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
        }:
            return True

        if master_status in {
            "OBSERVE",
            "WAIT_REVALIDATION",
            "EARLY_OVER_CANDIDATE",
            "STRONG_CANDIDATE",
            "MAIN_SIGNAL",
            "TOP_SIGNAL",
            "BLOCKED_BY_PROMOTION",
        }:
            return True

        if over_candidate_level in {
            "OVER_HIGH_OBSERVATION",
            "OVER_STRONG_CANDIDATE",
            "EARLY_OVER_CANDIDATE",
        }:
            return True

        if panel_section in {
            "OVER_HIGH_OBSERVATION",
            "HIGH_OBSERVATION",
            "STRONG_CANDIDATE",
            "BLOCKED",
        }:
            return True

        if over_candidate_active and (over_support_score >= 15 or over_support_ratio >= 0.75):
            return True

        if candidate_level or panel_signal_type:
            return True

        if can_publish or should_observe:
            return True

        return False

    def _create_record(
        self,
        signal: Dict[str, Any],
        signal_id: str,
        now: str,
    ) -> Dict[str, Any]:
        promotion_level = self._current_level(signal)
        market = self._detect_market(signal)
        tracking_type = self._tracking_type(promotion_level)

        record = {
            "history_version": self.VERSION,
            "history_signal_id": signal_id,
            "created_at": now,
            "last_seen_at": now,
            "updated_at": now,

            "match_id": str(signal.get("match_id") or signal.get("fixture_id") or ""),
            "fixture_id": str(signal.get("fixture_id") or signal.get("match_id") or ""),

            "home_team": signal.get("home_team") or "",
            "away_team": signal.get("away_team") or "",
            "league": signal.get("league") or "",
            "country": signal.get("country") or "",

            "league_filter_status": signal.get("league_filter_status") or "",
            "league_filter_reason": signal.get("league_filter_reason") or "",
            "competition_tier": self._competition_tier(signal),
            "competition_weight": self._competition_weight(signal),
            "world_cup_flag": self._bool_int(signal.get("world_cup_flag")),
            "national_team_flag": self._bool_int(signal.get("national_team_flag")),
            "major_tournament_flag": self._bool_int(signal.get("major_tournament_flag")),

            "market": market,
            "tracking_type": tracking_type,
            "initial_promotion_level": promotion_level,
            "current_promotion_level": promotion_level,
            "best_promotion_level": promotion_level,

            "initial_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "current_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "best_minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),

            "initial_scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "current_scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "final_scoreline": None,

            "home_score": safe_int(signal.get("home_score"), 0),
            "away_score": safe_int(signal.get("away_score"), 0),

            "promotion_score": safe_float(signal.get("promotion_score"), 0),
            "best_promotion_score": safe_float(signal.get("promotion_score"), 0),

            "activation_score": safe_float(signal.get("activation_score"), 0),
            "best_activation_score": safe_float(signal.get("activation_score"), 0),

            "prediction_market": signal.get("prediction_market") or "",
            "prediction_score": signal.get("prediction_score") or "",
            "prediction_next_goal_probability": signal.get("prediction_next_goal_probability") or "",
            "prediction_confidence": safe_float(signal.get("prediction_confidence"), 0),
            "prediction_scenario": signal.get("prediction_scenario") or "",
            "prediction_alternative_score": signal.get("prediction_alternative_score") or "",
            "prediction_halftime_score": signal.get("prediction_halftime_score") or "",
            "prediction_final_score": signal.get("prediction_final_score") or "",
            "prediction_market_alignment": signal.get("prediction_market_alignment") or "",
            "prediction_score_scenarios": signal.get("prediction_score_scenarios") or {},

            "model_id": signal.get("model_id") or signal.get("prediction_model_id") or "",
            "model_predicted_class": signal.get("predicted_class") or signal.get("model_predicted_class") or "",
            "model_predicted_probability": safe_float(
                signal.get("predicted_probability") or signal.get("model_predicted_probability"),
                0,
            ),

            "confidence": self._confidence(signal),
            "best_confidence": self._confidence(signal),

            "panel_label": self._panel_label(signal),

            "reason": self._reason(signal),

            "action": signal.get("activation_action")
            or signal.get("promotion_action")
            or signal.get("master_action")
            or "",

            "result_status": self.RESULT_PENDING,
            "result_reason": "Señal registrada. Resultado pendiente.",
            "evaluated_at": None,

            "evolution": [
                self._build_evolution_item(signal=signal, now=now, event="CREATED")
            ],
        }

        return record

    def _update_record(
        self,
        existing: Dict[str, Any],
        signal: Dict[str, Any],
        now: str,
    ) -> Dict[str, Any]:
        current_level = self._current_level(signal)
        current_priority = self.LEVEL_PRIORITY.get(current_level, 0)

        best_level = normalize_text(existing.get("best_promotion_level"))
        best_priority = self.LEVEL_PRIORITY.get(best_level, 0)

        current_score = safe_float(signal.get("promotion_score"), 0)
        best_score = safe_float(existing.get("best_promotion_score"), 0)

        current_activation_score = safe_float(signal.get("activation_score"), 0)
        best_activation_score = safe_float(existing.get("best_activation_score"), 0)

        current_confidence = self._confidence(signal)
        best_confidence = safe_float(existing.get("best_confidence"), 0)

        existing["last_seen_at"] = now
        existing["updated_at"] = now
        existing["current_promotion_level"] = current_level
        existing["tracking_type"] = self._tracking_type(
            self._best_level_after_update(
                current_level=current_level,
                current_priority=current_priority,
                best_level=best_level,
                best_priority=best_priority,
            )
        )

        existing["current_minute"] = safe_int(signal.get("api_minute") or signal.get("display_minute"), 0)
        existing["current_scoreline"] = (
            signal.get("scoreline")
            or signal.get("current_score")
            or existing.get("current_scoreline")
        )

        existing["home_score"] = safe_int(signal.get("home_score"), existing.get("home_score", 0))
        existing["away_score"] = safe_int(signal.get("away_score"), existing.get("away_score", 0))

        existing["league_filter_status"] = signal.get("league_filter_status") or existing.get("league_filter_status") or ""
        existing["league_filter_reason"] = signal.get("league_filter_reason") or existing.get("league_filter_reason") or ""
        existing["competition_tier"] = self._competition_tier(signal) or existing.get("competition_tier") or "UNKNOWN"
        existing["competition_weight"] = self._competition_weight(signal) or safe_float(existing.get("competition_weight"), 0)
        existing["world_cup_flag"] = max(self._bool_int(signal.get("world_cup_flag")), safe_int(existing.get("world_cup_flag"), 0))
        existing["national_team_flag"] = max(self._bool_int(signal.get("national_team_flag")), safe_int(existing.get("national_team_flag"), 0))
        existing["major_tournament_flag"] = max(self._bool_int(signal.get("major_tournament_flag")), safe_int(existing.get("major_tournament_flag"), 0))

        existing["promotion_score"] = current_score
        existing["activation_score"] = current_activation_score
        existing["confidence"] = current_confidence

        existing["prediction_market"] = signal.get("prediction_market") or existing.get("prediction_market") or ""
        existing["prediction_score"] = signal.get("prediction_score") or existing.get("prediction_score") or ""
        existing["prediction_next_goal_probability"] = (
            signal.get("prediction_next_goal_probability")
            or existing.get("prediction_next_goal_probability")
            or ""
        )
        existing["prediction_confidence"] = safe_float(
            signal.get("prediction_confidence"),
            existing.get("prediction_confidence", 0),
        )
        existing["prediction_scenario"] = signal.get("prediction_scenario") or existing.get("prediction_scenario") or ""
        existing["prediction_alternative_score"] = (
            signal.get("prediction_alternative_score")
            or existing.get("prediction_alternative_score")
            or ""
        )
        existing["prediction_halftime_score"] = (
            signal.get("prediction_halftime_score")
            or existing.get("prediction_halftime_score")
            or ""
        )
        existing["prediction_final_score"] = (
            signal.get("prediction_final_score")
            or existing.get("prediction_final_score")
            or ""
        )
        existing["prediction_market_alignment"] = (
            signal.get("prediction_market_alignment")
            or existing.get("prediction_market_alignment")
            or ""
        )
        if signal.get("prediction_score_scenarios"):
            existing["prediction_score_scenarios"] = signal.get("prediction_score_scenarios")

        existing["model_id"] = signal.get("model_id") or signal.get("prediction_model_id") or existing.get("model_id") or ""
        existing["model_predicted_class"] = (
            signal.get("predicted_class")
            or signal.get("model_predicted_class")
            or existing.get("model_predicted_class")
            or ""
        )
        existing["model_predicted_probability"] = max(
            safe_float(existing.get("model_predicted_probability"), 0),
            safe_float(signal.get("predicted_probability") or signal.get("model_predicted_probability"), 0),
        )

        existing["panel_label"] = self._panel_label(signal) or existing.get("panel_label") or ""
        existing["reason"] = self._reason(signal) or existing.get("reason") or ""

        existing["action"] = (
            signal.get("activation_action")
            or signal.get("promotion_action")
            or signal.get("master_action")
            or existing.get("action")
            or ""
        )

        if current_priority > best_priority:
            existing["best_promotion_level"] = current_level
            existing["best_minute"] = existing["current_minute"]
            existing["best_promotion_score"] = current_score
            existing["best_activation_score"] = current_activation_score
            existing["best_confidence"] = current_confidence
            existing["tracking_type"] = self._tracking_type(current_level)

            existing.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="PROMOTED")
            )

        elif (
            current_score > best_score
            or current_activation_score > best_activation_score
            or current_confidence > best_confidence
        ):
            existing["best_promotion_score"] = max(best_score, current_score)
            existing["best_activation_score"] = max(best_activation_score, current_activation_score)
            existing["best_confidence"] = max(best_confidence, current_confidence)

            existing.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="UPDATED")
            )

        else:
            evolution = existing.setdefault("evolution", [])
            if not evolution or evolution[-1].get("minute") != existing["current_minute"]:
                evolution.append(
                    self._build_evolution_item(signal=signal, now=now, event="SEEN_AGAIN")
                )

        self._apply_expiration_if_needed(existing, signal, now)

        return existing

    def _apply_expiration_if_needed(
        self,
        record: Dict[str, Any],
        signal: Dict[str, Any],
        now: str,
    ) -> None:
        if record.get("result_status") != self.RESULT_PENDING:
            return

        if bool(signal.get("no_reentry")):
            record["result_status"] = self.RESULT_EXPIRED
            record["result_reason"] = "La señal expiró por vida útil."
            record["evaluated_at"] = now
            record.setdefault("evolution", []).append(
                self._build_evolution_item(signal=signal, now=now, event="EXPIRED")
            )

    def _build_evolution_item(
        self,
        signal: Dict[str, Any],
        now: str,
        event: str,
    ) -> Dict[str, Any]:
        return {
            "event": event,
            "at": now,
            "minute": safe_int(signal.get("api_minute") or signal.get("display_minute"), 0),
            "scoreline": signal.get("scoreline") or signal.get("current_score") or "",
            "promotion_level": self._current_level(signal),
            "tracking_type": self._tracking_type(self._current_level(signal)),
            "market": self._detect_market(signal),
            "promotion_score": safe_float(signal.get("promotion_score"), 0),
            "activation_score": safe_float(signal.get("activation_score"), 0),
            "confidence": self._confidence(signal),
            "prediction_market": signal.get("prediction_market") or "",
            "prediction_score": signal.get("prediction_score") or "",
            "prediction_alternative_score": signal.get("prediction_alternative_score") or "",
            "prediction_next_goal_probability": signal.get("prediction_next_goal_probability") or "",
            "prediction_market_alignment": signal.get("prediction_market_alignment") or "",
            "competition_tier": self._competition_tier(signal),
            "competition_weight": self._competition_weight(signal),
            "world_cup_flag": self._bool_int(signal.get("world_cup_flag")),
            "national_team_flag": self._bool_int(signal.get("national_team_flag")),
            "major_tournament_flag": self._bool_int(signal.get("major_tournament_flag")),
            "panel_label": self._panel_label(signal),
            "reason": self._reason(signal),
        }

    def _increment_group_summary(
        self,
        bucket: Dict[str, Any],
        key: str,
        result_status: str,
    ) -> None:
        key = normalize_text(key) or "UNKNOWN"
        result_status = normalize_text(result_status) or self.RESULT_UNKNOWN

        group = bucket.setdefault(
            key,
            {
                "total": 0,
                "pending": 0,
                "won": 0,
                "lost": 0,
                "expired": 0,
                "cancelled": 0,
                "unknown": 0,
                "accuracy": 0.0,
            },
        )

        group["total"] += 1

        if result_status == self.RESULT_PENDING:
            group["pending"] += 1
        elif result_status == self.RESULT_WON:
            group["won"] += 1
        elif result_status == self.RESULT_LOST:
            group["lost"] += 1
        elif result_status == self.RESULT_EXPIRED:
            group["expired"] += 1
        elif result_status == self.RESULT_CANCELLED:
            group["cancelled"] += 1
        else:
            group["unknown"] += 1

        closed = group["won"] + group["lost"]
        group["accuracy"] = round((group["won"] / closed) * 100, 2) if closed else 0.0

    def _competition_tier(self, signal: Dict[str, Any]) -> str:
        tier = normalize_text(signal.get("competition_tier"))
        if tier:
            return tier

        league = normalize_text(signal.get("league"))
        country = normalize_text(signal.get("country"))
        text = f"{league} {country}"

        if any(token in text for token in ["WORLD CUP", "MUNDIAL", "COPA MUNDIAL"]):
            return "WORLD_CUP_ELITE"

        if any(token in text for token in ["CHAMPIONS LEAGUE", "EUROPA LEAGUE", "LIBERTADORES", "SUDAMERICANA"]):
            return "INTERNATIONAL_CLUB_ELITE"

        if any(token in text for token in ["COPA AMERICA", "EURO", "AFRICA CUP", "ASIAN CUP", "GOLD CUP", "NATIONS LEAGUE"]):
            return "NATIONAL_TEAM_ELITE"

        if bool(signal.get("major_tournament_flag")):
            return "MAJOR_TOURNAMENT"

        return "UNKNOWN"

    def _competition_weight(self, signal: Dict[str, Any]) -> float:
        explicit = safe_float(signal.get("competition_weight"), 0)
        if explicit > 0:
            return explicit

        tier = self._competition_tier(signal)
        weights = {
            "WORLD_CUP_ELITE": 100.0,
            "INTERNATIONAL_CLUB_ELITE": 90.0,
            "NATIONAL_TEAM_ELITE": 88.0,
            "MAJOR_TOURNAMENT": 82.0,
            "PRIORITY_LEAGUE": 75.0,
            "COUNTRY_REVIEW": 45.0,
        }
        return weights.get(tier, 0.0)

    def _bool_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return 1 if value else 0

        text = normalize_text(value)
        if text in {"1", "TRUE", "YES", "SI", "SÍ"}:
            return 1

        return 0

    def _current_level(self, signal: Dict[str, Any]) -> str:
        activation_level = normalize_text(signal.get("activation_level"))

        if activation_level in {
            "BLOCKED",
            "TOP_SIGNAL",
            "MAIN_SIGNAL",
            "STRONG_CANDIDATE",
            "EARLY_OVER_CANDIDATE",
            "WAIT_REVALIDATION",
            "HIGH_OBSERVATION",
            "OBSERVATION",
        }:
            return activation_level

        promotion_level = normalize_text(signal.get("promotion_level"))

        if promotion_level in {
            "BLOCKED",
            "TOP_SIGNAL",
            "MAIN_SIGNAL",
            "STRONG_CANDIDATE",
            "EARLY_OVER_CANDIDATE",
            "WAIT_REVALIDATION",
            "HIGH_OBSERVATION",
            "OVER_HIGH_OBSERVATION",
            "OBSERVATION",
            "OBSERVE_ONLY",
        }:
            return promotion_level

        over_candidate_level = normalize_text(signal.get("over_candidate_level"))
        panel_section = normalize_text(signal.get("panel_section"))
        master_status = normalize_text(signal.get("master_status"))

        if over_candidate_level == "EARLY_OVER_CANDIDATE":
            return "EARLY_OVER_CANDIDATE"

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            return "STRONG_CANDIDATE"

        if over_candidate_level == "OVER_HIGH_OBSERVATION":
            return "OVER_HIGH_OBSERVATION"

        if panel_section == "OVER_HIGH_OBSERVATION":
            return "OVER_HIGH_OBSERVATION"

        if panel_section == "HIGH_OBSERVATION":
            return "HIGH_OBSERVATION"

        if master_status in {
            "TOP_SIGNAL",
            "MAIN_SIGNAL",
            "STRONG_CANDIDATE",
            "EARLY_OVER_CANDIDATE",
            "WAIT_REVALIDATION",
            "BLOCKED_BY_PROMOTION",
        }:
            if master_status == "BLOCKED_BY_PROMOTION":
                return "BLOCKED"
            return master_status

        if bool(signal.get("can_publish")):
            return "MAIN_SIGNAL"

        if bool(signal.get("should_observe")):
            return "OBSERVE_ONLY"

        return "OBSERVE_ONLY"

    def _detect_market(self, signal: Dict[str, Any]) -> str:
        candidates = [
            signal.get("prediction_market"),
            signal.get("activation_market"),
            signal.get("promotion_market"),
            signal.get("narrative_reading_name"),
            signal.get("football_dominant_reading"),
            signal.get("panel_market"),
            signal.get("master_market"),
            signal.get("market"),
            signal.get("suggested_market"),
        ]

        for item in candidates:
            value = normalize_text(item)
            if "OVER" in value:
                return "OVER"
            if "UNDER" in value or "BAJO" in value:
                return "UNDER"

        over = safe_float(signal.get("over_score"), 0)
        under = safe_float(signal.get("under_score"), 0)

        if over > under + 5:
            return "OVER"

        if under > over + 5:
            return "UNDER"

        return "NO_BET"

    def _confidence(self, signal: Dict[str, Any]) -> float:
        values = [
            safe_float(signal.get("activation_score"), 0),
            safe_float(signal.get("promotion_score"), 0),
            safe_float(signal.get("prediction_confidence"), 0),
            safe_float(signal.get("master_confidence"), 0),
            safe_float(signal.get("football_confidence"), 0),
            safe_float(signal.get("elite_score"), 0),
        ]

        return max(values)

    def _panel_label(self, signal: Dict[str, Any]) -> str:
        return (
            signal.get("panel_activation_label")
            or signal.get("activation_label")
            or signal.get("panel_promotion_label")
            or signal.get("promotion_panel_label")
            or signal.get("panel_signal_type")
            or signal.get("panel_label")
            or ""
        )

    def _reason(self, signal: Dict[str, Any]) -> str:
        return (
            signal.get("panel_activation_reason")
            or signal.get("activation_reason")
            or signal.get("panel_promotion_reason")
            or signal.get("promotion_reason")
            or signal.get("prediction_panel_message")
            or signal.get("panel_narrative_reason")
            or signal.get("narrative_main_reason")
            or signal.get("master_reason")
            or ""
        )

    def _tracking_type(self, level: str) -> str:
        normalized = normalize_text(level)
        return self.TRACKING_TYPE_BY_LEVEL.get(normalized, "OBSERVATION_SIGNAL")

    def _best_level_after_update(
        self,
        current_level: str,
        current_priority: int,
        best_level: str,
        best_priority: int,
    ) -> str:
        if current_priority > best_priority:
            return current_level
        return best_level or current_level

    def _build_history_id(self, signal: Dict[str, Any]) -> str:
        match_id = str(signal.get("match_id") or signal.get("fixture_id") or "").strip()
        market = self._detect_market(signal)

        if not match_id:
            home = str(signal.get("home_team") or "").strip().lower().replace(" ", "_")
            away = str(signal.get("away_team") or "").strip().lower().replace(" ", "_")
            match_id = f"{home}_vs_{away}"

        return f"V17_HISTORY:{match_id}:{market}"

    def _find_record(
        self,
        records: List[Dict[str, Any]],
        signal_id: str,
    ) -> Optional[Dict[str, Any]]:
        for record in records:
            if record.get("history_signal_id") == signal_id:
                return record
        return None

    def _ensure_storage(self) -> None:
        if self.STORAGE_FILE.exists():
            return

        self._save(
            {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "records": [],
            }
        )

    def _load(self) -> Dict[str, Any]:
        self._ensure_storage()

        try:
            with self.STORAGE_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid history storage")

            data.setdefault("records", [])
            return data

        except Exception:
            return {
                "version": self.VERSION,
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
                "records": [],
            }

    def _save(self, data: Dict[str, Any]) -> None:
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        temp_file = self.STORAGE_FILE.with_suffix(".tmp")

        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        temp_file.replace(self.STORAGE_FILE)
