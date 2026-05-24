from __future__ import annotations

from typing import Any, Dict, List


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


class ContradictionJudge:
    """
    Revisa contradicciones internas entre capas.

    Una señal no puede ser ENTER si varias capas críticas advierten peligro.
    """

    def evaluate(
        self,
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> Dict[str, Any]:
        contradictions: List[str] = []
        warnings: List[str] = []
        critical: List[str] = []

        suggested_market = str(market.get("suggested_market") or "NO_BET").upper()

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)

        over_score = safe_float(market.get("over_score"), 0.0)
        under_score = safe_float(market.get("under_score"), 0.0)

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        risk_score = safe_float(risk.get("risk_score"), 0.0)

        if not clock.get("clock_can_enter", False):
            contradictions.append("CLOCK_DOES_NOT_ALLOW_ENTER")

            if clock.get("clock_status") == "BLOCKED_CLOCK":
                critical.append("CLOCK_CRITICAL")

        if not data_quality.get("data_valid", False):
            contradictions.append("DATA_NOT_VALID")
            critical.append("DATA_CRITICAL")

        if suggested_market == "OVER":
            if score_hold_probability >= 75:
                contradictions.append("OVER_VS_SCORE_HOLD")

            if under_transition_score >= 75:
                contradictions.append("OVER_VS_UNDER_TRANSITION")

            if false_pressure_risk >= 75:
                contradictions.append("OVER_VS_FALSE_PRESSURE")

            if offensive_depth_score < 45:
                contradictions.append("OVER_WITHOUT_DEPTH")

        if suggested_market == "UNDER":
            if tactical_score >= 78 and over_score >= 68:
                contradictions.append("UNDER_VS_HIGH_ATTACK_ACTIVITY")

        if over_score >= 65 and under_score >= 65:
            contradictions.append("MARKET_SPLIT_OVER_UNDER")

        if risk_score >= 75:
            contradictions.append("HIGH_RISK_AGAINST_ENTER")
            warnings.append("RISK_DEMANDS_CONFIRMATION")

        if context.get("conmebol_late") and suggested_market == "OVER":
            if tactical_score < 72 or offensive_depth_score < 65:
                contradictions.append("CONMEBOL_OVER_WITHOUT_EXTRA_CONFIRMATION")

        contradiction_score = len(contradictions) * 15 + len(critical) * 25
        contradiction_score = max(0, min(100, contradiction_score))

        if critical:
            status = "CRITICAL_CONTRADICTION"
            action = "BLOCK_OR_DEGRADE"
        elif contradiction_score >= 60:
            status = "STRONG_CONTRADICTION"
            action = "WAIT_CONFIRMATION"
        elif contradiction_score >= 30:
            status = "MODERATE_CONTRADICTION"
            action = "OBSERVE"
        else:
            status = "NO_CRITICAL_CONTRADICTION"
            action = "ALLOW_EVALUATION"

        return {
            "contradiction_status": status,
            "contradiction_score": round(contradiction_score, 2),
            "contradiction_action": action,
            "contradictions": contradictions,
            "contradiction_warnings": warnings,
            "critical_contradictions": critical,
          }
