from __future__ import annotations

from typing import Any, Dict, List


class OpportunityContextValidator:
    """
    Validador auxiliar para MatchOpportunityService.

    No crea señales.
    No bloquea por sí solo.
    Solo detecta si una oportunidad tiene contexto peligroso.
    """

    def validate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        market: str,
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        penalty = 0.0

        minute = self._safe_int(match.get("minute") or context.get("minute"))
        home_score = self._safe_int(match.get("home_score"))
        away_score = self._safe_int(match.get("away_score"))
        total_goals = home_score + away_score
        goal_diff = abs(home_score - away_score)

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "").upper()

        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))

        market = str(market or "").upper()

        if data_quality == "LOW":
            penalty += 8
            warnings.append("OPP_LOW_DATA")

        if game_quality == "LOW":
            penalty += 5
            warnings.append("OPP_LOW_GAME_QUALITY")

        if risk_level == "ALTO" or risk_score >= 7.4:
            penalty += 10
            warnings.append("OPP_HIGH_RISK")

        if minute < 12:
            penalty += 8
            warnings.append("OPP_TOO_EARLY")

        if "OVER" in market:
            if minute >= 78:
                penalty += 14
                warnings.append("OPP_OVER_TOO_LATE")

            if goal_diff >= 3 and minute >= 60:
                penalty += 18
                warnings.append("OPP_OVER_MATCH_RESOLVED")

            if total_goals >= 4 and minute >= 65:
                penalty += 14
                warnings.append("OPP_OVER_SCORE_OVEREXTENDED")

            if context_state in {"MUERTO", "FRIO"}:
                penalty += 12
                warnings.append("OPP_OVER_COLD_CONTEXT")

            if context_state == "CONTROLADO" and minute >= 65:
                penalty += 10
                warnings.append("OPP_OVER_CONTROLLED_CONTEXT")

            if cooling_detected:
                penalty += 14
                warnings.append("OPP_OVER_COOLING_DETECTED")

            if under_transition_score >= 70:
                penalty += 18
                warnings.append("OPP_OVER_UNDER_TRANSITION_ACTIVE")
            elif under_transition_score >= 55:
                penalty += 10
                warnings.append("OPP_OVER_UNDER_TRANSITION_WARNING")

            if over_probability >= 62 and pressure < 9 and rhythm < 6:
                penalty += 10
                warnings.append("OPP_OVER_PROB_WITHOUT_PRESSURE")

        if "UNDER" in market:
            if minute < 55:
                penalty += 10
                warnings.append("OPP_UNDER_TOO_EARLY")

            if context_state in {"CALIENTE", "MUY_CALIENTE"}:
                penalty += 16
                warnings.append("OPP_UNDER_HOT_CONTEXT")

            if goal_probability >= 60:
                penalty += 12
                warnings.append("OPP_UNDER_GOAL_PROB_HIGH")

            if pressure >= 24 or rhythm >= 16:
                penalty += 10
                warnings.append("OPP_UNDER_TOO_MUCH_ACTIVITY")

            if under_transition_score >= 70 and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
                penalty = max(0.0, penalty - 8.0)
                warnings.append("OPP_UNDER_TRANSITION_CONFIRMED")

            if cooling_detected and minute >= 60:
                penalty = max(0.0, penalty - 5.0)
                warnings.append("OPP_UNDER_COOLING_CONFIRMED")

        score = max(0.0, min(100.0, 100.0 - penalty))

        if score >= 80:
            status = "CLEAR"
        elif score >= 60:
            status = "CAUTION"
        elif score >= 40:
            status = "WARNING"
        else:
            status = "DANGER"

        return {
            "opportunity_context_status": status,
            "opportunity_context_score": round(score, 2),
            "opportunity_context_penalty": round(penalty, 2),
            "opportunity_context_warnings": warnings,
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
