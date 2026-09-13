from __future__ import annotations

from typing import Any, Dict


class UnderSignalGate:
    """
    Filtro final para señales UNDER.

    Debe ser más estricto que OVER.

    Solo deja pasar señales con:
    - contexto realmente cerrado o frío
    - probabilidad under suficiente
    - riesgo bajo/controlado
    - mercado válido
    - value real
    - baja amenaza de gol
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
        under_probability = self._safe_float(ai.get("under_probability"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))

        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))
        over_window_score = self._safe_float(context.get("over_window_score"))
        goal_window_score = self._safe_float(context.get("goal_window_score"))

        gate_min = self._safe_float(window.get("gate_min_score")) or 999
        minute = self._safe_float(window.get("minute") or context.get("minute"))

        market_valid = bool(market.get("is_valid"))
        odds = self._safe_float(market.get("odds"))

        is_value = bool(value.get("is_value"))
        edge = self._safe_float(value.get("edge"))

        # 🔹 DATA QUALITY
        if data_quality not in {"HIGH", "MEDIUM"}:
            return self._reject("GATE_DATA_QUALITY_LOW")

        # 🔹 MINUTO
        if minute and minute < 60:
            return self._reject("GATE_UNDER_TOO_EARLY")

        # 🔹 AI SCORE
        if ai_score < max(gate_min - 4, 68):
            return self._reject("GATE_AI_SCORE_TOO_LOW")

        # 🔹 UNDER PROBABILITY
        if under_probability < 64:
            return self._reject("GATE_UNDER_PROB_TOO_LOW")

        # 🔹 GOAL PROBABILITY debe ser moderada/baja
        if goal_probability > 52:
            return self._reject("GATE_GOAL_PROB_TOO_HIGH")

        # 🔹 RISK
        if risk_score > 6.3:
            return self._reject("GATE_RISK_SCORE_TOO_HIGH")

        # 🔹 CONTEXT STATE
        if context_state not in {"CONTROLADO", "TIBIO", "FRIO", "MUERTO"}:
            return self._reject("GATE_CONTEXT_NOT_ALIGNED")

        # 🔹 PRESSURE / RHYTHM deben ser moderados/bajos
        if pressure_index > 20:
            return self._reject("GATE_PRESSURE_TOO_HIGH")

        if rhythm_index > 15:
            return self._reject("GATE_RHYTHM_TOO_HIGH")

        # 🔹 GOAL THREAT WINDOW
        if over_window_score > 20:
            return self._reject("GATE_OVER_WINDOW_TOO_HIGH")

        if goal_window_score > 20:
            return self._reject("GATE_GOAL_WINDOW_TOO_HIGH")

        # 🔹 MARKET
        if not market_valid:
            return self._reject("GATE_MARKET_INVALID")

        if not odds or odds < 1.50 or odds > 2.10:
            return self._reject("GATE_ODDS_OUT_OF_RANGE")

        # 🔹 VALUE
        if not is_value:
            return self._reject("GATE_NO_VALUE")

        if edge < 0.04:
            return self._reject("GATE_EDGE_TOO_LOW")

        # 🔹 FINAL CONSENSUS
        if not self._consensus_check(context, ai, value):
            return self._reject("GATE_NO_CONSENSUS")

        return {
            "approved": True,
            "reason": "GATE_APPROVED",
        }

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------

    def _consensus_check(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        value: Dict[str, Any],
    ) -> bool:
        """
        UNDER sigue más duro que OVER.
        Exige al menos 4/5 condiciones alineadas.
        """
        checks = 0

        if self._safe_float(ai.get("under_probability")) >= 66:
            checks += 1

        if self._safe_float(ai.get("goal_probability")) <= 48:
            checks += 1

        if self._safe_float(context.get("pressure_index")) <= 18:
            checks += 1

        if str(context.get("context_state") or "").upper() in {"FRIO", "MUERTO", "CONTROLADO"}:
            checks += 1

        if self._safe_float(value.get("edge")) >= 0.05:
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
