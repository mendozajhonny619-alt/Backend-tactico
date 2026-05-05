from __future__ import annotations

from typing import Any, Dict, List


class AIConfidenceHelper:
    """
    Ayudante para ajustar confianza de la IA.

    No crea señales.
    No bloquea.
    Solo corrige probabilidades cuando el contexto no justifica tanta confianza.
    """

    def adjust(self, ai: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ai = dict(ai or {})
        context = context or {}

        warnings: List[str] = []
        penalty = 0.0

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        minute = self._safe_int(context.get("minute"))

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        if data_quality == "LOW":
            penalty += 8.0
            warnings.append("AI_LOW_DATA_PENALTY")

        if game_quality == "LOW":
            penalty += 5.0
            warnings.append("AI_LOW_GAME_QUALITY")

        if context_state in {"MUERTO", "FRIO"} and goal_probability >= 55:
            penalty += 8.0
            warnings.append("AI_GOAL_PROB_OVER_CONTEXT")

        if pressure < 8 and rhythm < 6 and over_probability >= 60:
            penalty += 9.0
            warnings.append("AI_OVER_WITHOUT_PRESSURE")

        if minute < 12:
            penalty += 5.0
            warnings.append("AI_TOO_EARLY_READING")

        if minute >= 78 and over_probability >= 65:
            penalty += 6.0
            warnings.append("AI_LATE_OVER_CAUTION")

        confidence_score = max(0.0, min(100.0, 100.0 - penalty))

        ai["ai_score"] = round(max(0.0, ai_score - penalty), 2)
        ai["goal_probability"] = round(max(0.0, goal_probability - penalty), 2)
        ai["over_probability"] = round(max(0.0, over_probability - penalty), 2)
        ai["under_probability"] = round(min(95.0, max(0.0, under_probability + (penalty * 0.45))), 2)

        ai["confidence_helper_status"] = self._status(confidence_score)
        ai["confidence_helper_score"] = round(confidence_score, 2)
        ai["confidence_helper_penalty"] = round(penalty, 2)
        ai["confidence_helper_warnings"] = warnings

        return ai

    def _status(self, score: float) -> str:
        if score >= 85:
            return "CLEAR"
        if score >= 70:
            return "STABLE"
        if score >= 50:
            return "CAUTION"
        return "LOW_CONFIDENCE"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
