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


class MarketAI:
    """
    Decide la orientación de mercado:
    - OVER
    - UNDER
    - OBSERVE
    - NO_BET

    No decide ENTER por sí sola.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
    ) -> Dict[str, Any]:
        minute = safe_int(match.get("api_minute"), 0)

        over_context_score = safe_float(context.get("over_context_score"), 0.0)
        under_context_score = safe_float(context.get("under_context_score"), 0.0)
        score_hold_probability = safe_float(context.get("score_hold_probability"), 0.0)
        under_transition_score = safe_float(context.get("under_transition_score"), 0.0)

        tactical_score = safe_float(tactical.get("tactical_score"), 0.0)
        offensive_depth_score = safe_float(tactical.get("offensive_depth_score"), 0.0)
        false_pressure_risk = safe_float(tactical.get("false_pressure_risk"), 0.0)
        recent_attack_proxy = safe_float(tactical.get("recent_attack_proxy"), 0.0)

        market_warnings: List[str] = []
        market_strengths: List[str] = []

        over_score = (
            over_context_score * 0.35
            + tactical_score * 0.25
            + offensive_depth_score * 0.20
            + recent_attack_proxy * 0.10
            + max(0, 100 - false_pressure_risk) * 0.10
        )

        under_score = (
            under_context_score * 0.35
            + score_hold_probability * 0.25
            + under_transition_score * 0.25
            + max(0, 100 - tactical_score) * 0.15
        )

        if false_pressure_risk >= 70:
            over_score -= 18
            market_warnings.append("OVER_FALSE_PRESSURE")

        if score_hold_probability >= 75:
            over_score -= 12
            market_warnings.append("SCORE_HOLD_AGAINST_OVER")

        if under_transition_score >= 75:
            over_score -= 10
            market_warnings.append("UNDER_TRANSITION_AGAINST_OVER")

        if minute >= 80 and recent_attack_proxy < 50:
            over_score -= 10
            market_warnings.append("LATE_WITHOUT_REACTIVATION")

        if offensive_depth_score >= 70:
            market_strengths.append("DEPTH_SUPPORTS_OVER")

        if tactical_score >= 70:
            market_strengths.append("TACTICAL_SUPPORTS_OVER")

        if score_hold_probability >= 70:
            market_strengths.append("SCORE_HOLD_SUPPORTS_UNDER")

        if under_transition_score >= 70:
            market_strengths.append("UNDER_TRANSITION_SUPPORTS_UNDER")

        over_score = max(0, min(100, over_score))
        under_score = max(0, min(100, under_score))

        if over_score >= 70 and over_score >= under_score + 8:
            market = "OVER"
            category = "OVER_CANDIDATE"
            market_status = "OVER_EDGE"
        elif under_score >= 67 and under_score >= over_score + 5:
            market = "UNDER"
            category = "UNDER_CANDIDATE"
            market_status = "UNDER_EDGE"
        elif max(over_score, under_score) >= 55:
            market = "OBSERVE"
            category = "OBSERVE"
            market_status = "MIXED_MARKET"
        else:
            market = "NO_BET"
            category = "NO_BET"
            market_status = "NO_MARKET_EDGE"

        market_confidence = max(over_score, under_score)

        return {
            "market_status": market_status,
            "suggested_market": market,
            "market_category": category,
            "over_score": round(over_score, 2),
            "under_score": round(under_score, 2),
            "market_confidence": round(market_confidence, 2),
            "market_strengths": market_strengths,
            "market_warnings": market_warnings,
      }
