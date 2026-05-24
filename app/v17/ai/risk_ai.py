from __future__ import annotations

from typing import Any, Dict, List


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


class RiskAI:
    """
    Detecta riesgos operativos:
    - reloj atrasado
    - CONMEBOL tardío sin confirmación
    - presión falsa
    - score hold
    - señal dudosa
    - falta de tiros al arco
    - datos débiles
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        clock: Dict[str, Any],
        data_quality: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        market: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = safe_int(match.get("api_minute"), 0)

        risk_reasons: List[str] = []
        risk_warnings: List[str] = []
        hard_blockers: List[str] = []

        risk_score = 0.0

        if not data_quality.get("data_valid", False):
            risk_score += 35
            hard_blockers.extend(data_quality.get("data_issues", []))

        if data_quality.get("data_weak", False):
            risk_score += 12
            risk_warnings.extend(data_quality.get("data_warnings", []))

        if not clock.get("clock_can_enter", False):
            risk_score += 30
            if clock.get("clock_status") == "BLOCKED_CLOCK":
                hard_blockers.extend(clock.get("clock_blockers", []))
            else:
                risk_warnings.extend(clock.get("clock_warnings", []))

        is_conmebol = bool(context.get("is_conmebol", False))
        conmebol_late = bool(context.get("conmebol_late", False))
        suggested_market = str(market.get("suggested_market") or "NO_BET").upper()

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)

        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        total_shots_on = safe_int(match.get("total_shots_on"), 0)

        if false_pressure_risk >= 75:
            risk_score += 22
            risk_reasons.append("FALSE_PRESSURE_RISK")

        if suggested_market == "OVER" and total_shots_on <= 1 and minute >= 55:
            risk_score += 18
            risk_reasons.append("OVER_WITH_LOW_SHOTS_ON_TARGET")

        if suggested_market == "OVER" and score_hold_probability >= 75:
            risk_score += 18
            risk_reasons.append("OVER_AGAINST_SCORE_HOLD")

        if suggested_market == "OVER" and under_transition_score >= 75:
            risk_score += 15
            risk_reasons.append("OVER_AGAINST_UNDER_TRANSITION")

        if suggested_market == "OVER" and minute >= 80 and recent_attack_proxy < 50:
            risk_score += 16
            risk_reasons.append("LATE_OVER_WITHOUT_REACTIVATION")

        if suggested_market == "OVER" and offensive_depth_score < 45:
            risk_score += 14
            risk_reasons.append("OVER_WITHOUT_DEPTH")

        if conmebol_late:
            risk_score += 14
            risk_warnings.append("CONMEBOL_EXTRA_CONFIRMATION_REQUIRED")

            if suggested_market == "OVER":
                if tactical_score < 72 or offensive_depth_score < 65 or recent_attack_proxy < 60:
                    risk_score += 20
                    risk_reasons.append("CONMEBOL_OVER_NOT_CONFIRMED")

        if suggested_market == "UNDER" and tactical_score >= 78:
            risk_score += 12
            risk_warnings.append("UNDER_AGAINST_STRONG_TACTICAL_ACTIVITY")

        if suggested_market == "NO_BET":
            risk_score += 15
            risk_warnings.append("NO_MARKET_EDGE")

        risk_score = max(0, min(100, risk_score))

        if hard_blockers:
            risk_status = "EXTREME_RISK"
            risk_action = "BLOCK"
        elif risk_score >= 75:
            risk_status = "HIGH_RISK"
            risk_action = "WAIT_CONFIRMATION"
        elif risk_score >= 55:
            risk_status = "MEDIUM_RISK"
            risk_action = "OBSERVE"
        elif risk_score >= 35:
            risk_status = "CONTROLLED_RISK"
            risk_action = "OPERABLE_WITH_CAUTION"
        else:
            risk_status = "LOW_RISK"
            risk_action = "RISK_ACCEPTABLE"

        return {
            "risk_status": risk_status,
            "risk_score": round(risk_score, 2),
            "risk_action": risk_action,
            "risk_reasons": risk_reasons,
            "risk_warnings": risk_warnings,
            "hard_blockers": hard_blockers,
          }
