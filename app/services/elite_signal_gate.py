from __future__ import annotations

from typing import Any, Dict


class EliteSignalGate:
    """
    Filtro final para señales OVER.
    """

    def validate(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        market: Dict[str, Any],
        value: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = context or {}
        ai = ai or {}
        window = window or {}
        market = market or {}
        value = value or {}

        data_quality = str(context.get("data_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))

        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))
        over_window_score = self._safe_float(context.get("over_window_score"))
        goal_window_score = self._safe_float(context.get("goal_window_score"))

        gate_min = self._safe_float(window.get("gate_min_score")) or 60
        minute = self._safe_float(window.get("minute") or context.get("minute"))

        market_valid = bool(market.get("is_valid"))
        odds = self._safe_float(market.get("odds"))
        market_status = str(market.get("market_status") or "").upper()

        is_value = bool(value.get("is_value"))
        edge = self._safe_float(value.get("edge"))
        value_category = str(value.get("value_category") or "").upper()

        if data_quality not in {"MEDIUM", "HIGH"}:
            return self._reject("GATE_DATA_QUALITY_NOT_ENOUGH")

        if minute and minute < 15:
            return self._reject("GATE_OVER_TOO_EARLY")

        if minute and minute > 75:
            return self._reject("GATE_OVER_TOO_LATE")

        if ai_score < max(gate_min - 10, 52):
            return self._reject("GATE_AI_SCORE_TOO_LOW")

        if goal_probability < 58:
            return self._reject("GATE_GOAL_PROB_TOO_LOW")

        if over_probability < 58:
            return self._reject("GATE_OVER_PROB_TOO_LOW")

        if risk_score > 7.5:
            return self._reject("GATE_RISK_SCORE_TOO_HIGH")

        if context_state not in {"TIBIO", "CALIENTE", "MUY_CALIENTE", "CONTROLADO"}:
            return self._reject("GATE_CONTEXT_NOT_ALIGNED")

        if context_state == "CONTROLADO":
            if goal_probability < 68 or over_probability < 68 or pressure_index < 14:
                return self._reject("GATE_CONTROLLED_CONTEXT_NOT_STRONG_ENOUGH")

        if pressure_index < 8:
            return self._reject("GATE_PRESSURE_TOO_LOW")

        if rhythm_index < 5:
            return self._reject("GATE_RHYTHM_TOO_LOW")

        if over_window_score < 8:
            return self._reject("GATE_OVER_WINDOW_TOO_LOW")

        if goal_window_score < 8:
            return self._reject("GATE_GOAL_WINDOW_TOO_LOW")

        if not market_valid:
            return self._reject("GATE_MARKET_INVALID")

        if market_status != "INTERNAL_ONLY":
            if not odds or odds < 1.50 or odds > 2.10:
                return self._reject("GATE_ODDS_OUT_OF_RANGE")

        if value_category != "INTERNAL":
            if not is_value:
                return self._reject("GATE_NO_VALUE")

            if edge < 0.02:
                return self._reject("GATE_EDGE_TOO_LOW")

        if not self._consensus_check(context, ai, value):
            return self._reject("GATE_NO_CONSENSUS")

        return {
            "approved": True,
            "reason": "GATE_APPROVED",
        }

    def _consensus_check(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        value: Dict[str, Any],
    ) -> bool:
        checks = 0

        if self._safe_float(ai.get("goal_probability")) >= 62:
            checks += 1

        if self._safe_float(ai.get("over_probability")) >= 62:
            checks += 1

        if self._safe_float(ai.get("ai_score")) >= 55:
            checks += 1

        if self._safe_float(context.get("pressure_index")) >= 10:
            checks += 1

        if self._safe_float(context.get("rhythm_index")) >= 6:
            checks += 1

        if str(context.get("context_state") or "").upper() in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}:
            checks += 1

        value_category = str(value.get("value_category") or "").upper()
        if value_category == "INTERNAL" or self._safe_float(value.get("edge")) >= 0.02:
            checks += 1

        return checks >= 4

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "approved": False,
            "reason": reason,
        }
