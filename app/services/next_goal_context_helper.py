from __future__ import annotations

from typing import Any, Dict


class NextGoalContextHelper:
    """
    Interpreta la lectura del NextGoalSideEngine.

    No bloquea.
    No cambia rank.
    Solo agrega lectura para panel y análisis.
    """

    def interpret(
        self,
        next_goal: Dict[str, Any],
        opportunity: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        next_goal = next_goal or {}
        opportunity = opportunity or {}

        market = str(opportunity.get("market") or "").upper()
        bias = str(next_goal.get("next_goal_bias") or "NEUTRAL").upper()
        status = str(next_goal.get("next_goal_status") or "UNCLEAR").upper()
        confidence = self._safe_float(next_goal.get("next_goal_confidence"))
        hold_prob = self._safe_float(next_goal.get("score_hold_probability"))

        retention_risk = self._safe_float(next_goal.get("retention_risk"))
        retention_label = str(next_goal.get("retention_risk_label") or "").upper()
        final_decision = str(next_goal.get("final_decision") or "").upper()
        deep_projection_bias = str(next_goal.get("deep_projection_bias") or "").upper()
        fake_pressure_detected = bool(
            next_goal.get("fake_pressure_detected")
            or next_goal.get("deep_fake_pressure_detected")
        )

        warning = str(next_goal.get("next_goal_warning") or "")

        support = "NEUTRAL"
        advice = "Lectura auxiliar sin confirmación fuerte."

        if "OVER" in market:
            if hold_prob >= 70:
                support = "AGAINST_OVER"
                advice = "Cuidado: alta probabilidad de que el marcador se mantenga."
            elif status == "CONFIRMATION" and confidence >= 65:
                support = "SUPPORTS_OVER"
                advice = "La presión lateral apoya una posible continuación de gol."
            elif bias != "NEUTRAL" and confidence >= 50:
                support = "WEAK_SUPPORT_OVER"
                advice = "Hay sesgo hacia un lado, pero falta confirmación fuerte."

        elif "UNDER" in market:
            if hold_prob >= 68:
                support = "SUPPORTS_UNDER"
                advice = "La lectura apoya que el marcador pueda mantenerse."
            elif status == "CONFIRMATION" and confidence >= 70:
                support = "AGAINST_UNDER"
                advice = "Cuidado: hay presión clara de un lado para próximo gol."
            else:
                support = "NEUTRAL_UNDER"
                advice = "Lectura lateral no contradice fuerte el UNDER."

        else:
            if hold_prob >= 70:
                support = "SCORE_HOLD_INFO"
                advice = "El partido muestra tendencia a mantener marcador."
            elif status == "CONFIRMATION":
                support = "NEXT_GOAL_SIDE_INFO"
                advice = "Hay sesgo claro hacia un lado para próximo gol."

        if "OVER" in market:
            if retention_risk >= 70 or retention_label == "ALTO":
                support = "AGAINST_OVER"
                advice = "Cuidado: retención alta. No reforzar OVER sin reactivación real."

            if fake_pressure_detected:
                support = "AGAINST_OVER"
                advice = "Cuidado: presión sin profundidad real. Evitar sobrevalorar OVER."

            if final_decision in {"NO_REENTRY", "AVOID"}:
                support = "AGAINST_OVER"
                advice = "La decisión maestra no permite reentrada segura para OVER."

        if "UNDER" in market:
            if retention_risk >= 70 or retention_label == "ALTO" or deep_projection_bias == "UNDER":
                support = "SUPPORTS_UNDER"
                advice = "La lectura de retención/proyección apoya UNDER."

            if final_decision == "AVOID":
                support = "AGAINST_UNDER"
                advice = "La decisión maestra bloquea esta entrada UNDER."

        if not market:
            if retention_risk >= 70 or retention_label == "ALTO":
                support = "SCORE_HOLD_INFO"
                advice = "El partido muestra alta tendencia a mantener marcador."

        return {
            "next_goal_support": support,
            "next_goal_helper_advice": advice,
            "next_goal_helper_warning": warning,
        }

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
