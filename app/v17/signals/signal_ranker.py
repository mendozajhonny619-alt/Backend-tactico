from __future__ import annotations

from typing import Any, Dict, List

from app.v17.core.constants import MAX_PUBLISHED_SIGNALS, RANK_WEIGHTS


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


class SignalRanker:
    """
    Ranking élite máximo 6 señales.

    Regla central:
    - No fuerza 6 señales.
    - Si hay 1 buena, muestra 1.
    - Si hay 6 buenas, muestra máximo 6.
    - Si una cumple mayoría pero falla filtros secundarios, puede pasar como OPERABLE o BUENA.
    - Si tiene bloqueo crítico, no pasa.
    """

    def rank(self, analyzed_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        publishable: List[Dict[str, Any]] = []
        observe: List[Dict[str, Any]] = []
        no_bet: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for item in analyzed_matches or []:
            final_item = self._score_item(item)
            status = str(final_item.get("master_status") or "").upper()

            if final_item.get("can_publish") and status in {"ENTER", "OPERABLE"}:
                publishable.append(final_item)
            elif status in {"OBSERVE", "WAIT_CONFIRMATION"} or final_item.get("should_observe"):
                observe.append(final_item)
            elif status in {"BLOCKED"}:
                blocked.append(final_item)
            else:
                no_bet.append(final_item)

        publishable = sorted(publishable, key=self._sort_key, reverse=True)
        observe = sorted(observe, key=self._sort_key, reverse=True)
        no_bet = sorted(no_bet, key=self._sort_key, reverse=True)
        blocked = sorted(blocked, key=self._sort_key, reverse=True)

        top_signals = publishable[:MAX_PUBLISHED_SIGNALS]

        for index, item in enumerate(top_signals, start=1):
            item["elite_position"] = index
            item["published"] = True
            item["panel_section"] = "TOP_SIGNAL"

        for item in observe:
            item["published"] = False
            item["panel_section"] = "OBSERVE"

        for item in no_bet:
            item["published"] = False
            item["panel_section"] = "NO_BET"

        for item in blocked:
            item["published"] = False
            item["panel_section"] = "BLOCKED"

        return {
            "top_signals": top_signals,
            "observe": observe,
            "no_bet": no_bet,
            "blocked": blocked,
            "all_analyzed": top_signals + observe + no_bet + blocked,
            "summary": {
                "published_count": len(top_signals),
                "observe_count": len(observe),
                "no_bet_count": len(no_bet),
                "blocked_count": len(blocked),
                "max_allowed": MAX_PUBLISHED_SIGNALS,
            },
        }

    def _score_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        signal = dict(item)

        master_confidence = safe_float(signal.get("master_confidence"), 0.0)
        market_confidence = safe_float(signal.get("market_confidence"), 0.0)
        tactical_score = safe_float(signal.get("tactical_score"), 0.0)
        pressure_score = safe_float(signal.get("pressure_score"), 0.0)
        rhythm_score = safe_float(signal.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(signal.get("goal_need_score"), 0.0)
        risk_score = safe_float(signal.get("risk_score"), 0.0)
        contradiction_score = safe_float(signal.get("contradiction_score"), 0.0)
        signal_life_penalty = safe_float(signal.get("signal_life_penalty"), 0.0)

        score_hold_probability = safe_float(signal.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(signal.get("under_transition_score"), 0.0)
        false_pressure_risk = safe_float(signal.get("false_pressure_risk"), 0.0)

        clock_bonus = 8 if signal.get("clock_can_enter") else -18
        data_bonus = 6 if signal.get("data_valid") else -25

        rank_name = str(signal.get("master_rank") or "NO_BET").upper()
        rank_bonus = RANK_WEIGHTS.get(rank_name, 0) * 4

        suggested_market = str(signal.get("master_market") or signal.get("suggested_market") or "").upper()

        if suggested_market == "OVER":
            market_specific = (
                goal_need_score * 0.10
                + pressure_score * 0.10
                + rhythm_score * 0.08
                - score_hold_probability * 0.08
                - under_transition_score * 0.08
                - false_pressure_risk * 0.10
            )
        elif suggested_market == "UNDER":
            market_specific = (
                score_hold_probability * 0.12
                + under_transition_score * 0.10
                - tactical_score * 0.05
                - pressure_score * 0.04
            )
        else:
            market_specific = 0

        elite_score = (
            master_confidence * 0.30
            + market_confidence * 0.18
            + tactical_score * 0.17
            + pressure_score * 0.10
            + rhythm_score * 0.08
            + goal_need_score * 0.07
            + max(0, 100 - risk_score) * 0.07
            + max(0, 100 - contradiction_score) * 0.03
            + market_specific
            + clock_bonus
            + data_bonus
            + rank_bonus
            - signal_life_penalty
        )

        elite_score = max(0, min(100, elite_score))

        signal["elite_score"] = round(elite_score, 2)

        if elite_score >= 86 and signal.get("can_publish"):
            signal["elite_rank"] = "PREMIUM"
        elif elite_score >= 78 and signal.get("can_publish"):
            signal["elite_rank"] = "FUERTE"
        elif elite_score >= 68 and signal.get("can_publish"):
            signal["elite_rank"] = "BUENA"
        elif elite_score >= 58:
            signal["elite_rank"] = "OPERABLE" if signal.get("can_publish") else "OBSERVE"
        elif signal.get("should_observe"):
            signal["elite_rank"] = "OBSERVE"
        elif signal.get("should_block"):
            signal["elite_rank"] = "BLOCKED"
        else:
            signal["elite_rank"] = "NO_BET"

        return signal

    def _sort_key(self, item: Dict[str, Any]) -> Any:
        rank = str(item.get("elite_rank") or item.get("master_rank") or "NO_BET").upper()
        rank_weight = RANK_WEIGHTS.get(rank, 0)

        return (
            rank_weight,
            safe_float(item.get("elite_score"), 0.0),
            safe_float(item.get("master_confidence"), 0.0),
            safe_float(item.get("market_confidence"), 0.0),
            safe_int(item.get("api_minute"), 0),
            -safe_float(item.get("risk_score"), 0.0),
          )
