from __future__ import annotations

from typing import Any, Dict, Optional


class ValueEngine:
    """
    Calcula edge real comparando:
    - prob_real del modelo
    - prob_implicita de la cuota

    Si no hay cuota real:
    - usa value interno/simulado
    - no inventa cuota real
    - reconoce reactivación, retención, UNDER transition y mercado interno
    """

    MIN_EDGE_OVER = 0.03
    MIN_EDGE_UNDER = 0.04

    def evaluate(
        self,
        ai: Dict[str, Any],
        market: Dict[str, Any],
        market_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not isinstance(ai, dict):
            return self._reject("VALUE_AI_INVALID")

        if not isinstance(market, dict):
            return self._reject("VALUE_MARKET_INVALID")

        resolved_market_type = self._resolve_market_type(
            market_type=market_type,
            market_market_type=market.get("market_type"),
        )

        if resolved_market_type not in {"OVER", "UNDER"}:
            return self._reject("VALUE_MARKET_TYPE_UNKNOWN")

        if not market.get("is_valid"):
            return self._reject(market.get("reason") or "VALUE_MARKET_NOT_VALID")

        odds = self._safe_float(market.get("odds"))
        market_status = str(market.get("market_status") or "").upper()
        line = str(market.get("line") or "").upper()

        if (
            odds <= 1.0
            or market_status in {"PENDING", "INTERNAL_ONLY"}
            or line == "AUTO"
        ):
            return self._evaluate_internal_value(
                ai=ai,
                market=market,
                market_type=resolved_market_type,
            )

        prob_real = self._resolve_real_probability(ai=ai, market_type=resolved_market_type)
        if prob_real is None:
            return self._reject("VALUE_REAL_PROBABILITY_MISSING")

        prob_real = self._normalize_probability(prob_real)
        prob_implicita = 1.0 / odds
        edge = prob_real - prob_implicita

        min_required = self._dynamic_min_edge(
            market_type=resolved_market_type,
            market=market,
            base_edge=self.MIN_EDGE_OVER if resolved_market_type == "OVER" else self.MIN_EDGE_UNDER,
        )

        is_value = edge >= min_required
        value_category = self._categorize_edge(edge=edge, min_required=min_required)

        return {
            "is_value": is_value,
            "status": "VALUE_OK" if is_value else "VALUE_TOO_WEAK",
            "value_category": value_category,
            "market_type": resolved_market_type,
            "odds": round(odds, 3),
            "prob_real": round(prob_real, 4),
            "prob_implicita": round(prob_implicita, 4),
            "edge": round(edge, 4),
            "min_required_edge": round(min_required, 4),
            "value_mode": "REAL_MARKET",
            "value_live_bias": market.get("market_live_bias"),
            "value_recommendation": market.get("market_recommendation"),
        }

    def _evaluate_internal_value(
        self,
        ai: Dict[str, Any],
        market: Dict[str, Any],
        market_type: str,
    ) -> Dict[str, Any]:
        prob_real = self._resolve_real_probability(ai=ai, market_type=market_type)
        if prob_real is None:
            return self._reject("VALUE_REAL_PROBABILITY_MISSING")

        prob_real = self._normalize_probability(prob_real)

        ai_score = self._normalize_probability(self._safe_float(ai.get("ai_score")))
        goal_probability = self._normalize_probability(self._safe_float(ai.get("goal_probability")))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "").upper()

        market_live_bias = str(market.get("market_live_bias") or "").upper()
        market_live_status = str(market.get("market_live_status") or "").upper()
        market_late_pressure = bool(market.get("market_late_pressure", False))

        if market_type == "UNDER":
            synthetic_market_prob = self._simulate_under_market_probability(
                prob_real=prob_real,
                ai_score=ai_score,
                goal_probability=goal_probability,
                risk_score=risk_score,
                risk_level=risk_level,
                market_live_bias=market_live_bias,
            )
        else:
            synthetic_market_prob = self._simulate_over_market_probability(
                prob_real=prob_real,
                ai_score=ai_score,
                goal_probability=goal_probability,
                risk_score=risk_score,
                risk_level=risk_level,
                market_live_bias=market_live_bias,
                market_late_pressure=market_late_pressure,
            )

        edge = prob_real - synthetic_market_prob

        min_required = self._dynamic_min_edge(
            market_type=market_type,
            market=market,
            base_edge=self.MIN_EDGE_OVER if market_type == "OVER" else self.MIN_EDGE_UNDER,
        )

        is_value = edge >= min_required

        if market_live_status == "WARNING" and market_type == "OVER":
            is_value = False

        value_category = self._categorize_edge(edge=edge, min_required=min_required)

        return {
            "is_value": is_value,
            "status": "INTERNAL_VALUE_OK" if is_value else "INTERNAL_VALUE_TOO_WEAK",
            "value_category": value_category,
            "market_type": market_type,
            "odds": None,
            "prob_real": round(prob_real, 4),
            "prob_implicita": round(synthetic_market_prob, 4),
            "edge": round(edge, 4),
            "min_required_edge": round(min_required, 4),
            "value_mode": "INTERNAL_SIMULATED",
            "market_status": market.get("market_status") or "INTERNAL_ONLY",
            "reason": "VALUE_INTERNAL_SIMULATED_NO_REAL_ODDS",
            "value_live_bias": market.get("market_live_bias"),
            "value_recommendation": market.get("market_recommendation"),
        }

    def _simulate_over_market_probability(
        self,
        prob_real: float,
        ai_score: float,
        goal_probability: float,
        risk_score: float,
        risk_level: str,
        market_live_bias: str,
        market_late_pressure: bool,
    ) -> float:
        simulated = (
            prob_real * 0.55
            + goal_probability * 0.25
            + ai_score * 0.20
        )

        if risk_level == "ALTO" or risk_score >= 7.0:
            simulated += 0.08
        elif risk_level == "MEDIO" or risk_score >= 4.5:
            simulated += 0.04

        if market_live_bias == "OVER_LATE_REACTIVATION" or market_late_pressure:
            simulated -= 0.035

        if market_live_bias == "AGAINST_OVER":
            simulated += 0.08

        return max(0.05, min(simulated, 0.95))

    def _simulate_under_market_probability(
        self,
        prob_real: float,
        ai_score: float,
        goal_probability: float,
        risk_score: float,
        risk_level: str,
        market_live_bias: str,
    ) -> float:
        inverse_goal = max(0.0, 1.0 - goal_probability)

        simulated = (
            prob_real * 0.60
            + inverse_goal * 0.25
            + ai_score * 0.15
        )

        if risk_level == "ALTO" or risk_score >= 7.0:
            simulated += 0.07
        elif risk_level == "MEDIO" or risk_score >= 4.5:
            simulated += 0.03

        if market_live_bias == "UNDER_SUPPORTED":
            simulated -= 0.035

        if market_live_bias == "AGAINST_UNDER":
            simulated += 0.08

        return max(0.05, min(simulated, 0.95))

    def _dynamic_min_edge(
        self,
        market_type: str,
        market: Dict[str, Any],
        base_edge: float,
    ) -> float:
        live_bias = str(market.get("market_live_bias") or "").upper()
        live_status = str(market.get("market_live_status") or "").upper()
        late_pressure = bool(market.get("market_late_pressure", False))

        edge = base_edge

        if market_type == "OVER" and (live_bias == "OVER_LATE_REACTIVATION" or late_pressure):
            edge -= 0.01

        if market_type == "UNDER" and live_bias == "UNDER_SUPPORTED":
            edge -= 0.01

        if live_status == "WARNING":
            edge += 0.02

        if live_bias in {"AGAINST_OVER", "AGAINST_UNDER"}:
            edge += 0.03

        return max(0.015, min(edge, 0.08))

    def _resolve_real_probability(self, ai: Dict[str, Any], market_type: str) -> Optional[float]:
        if market_type == "OVER":
            primary = ai.get("over_probability")
            fallback = ai.get("goal_probability")
        else:
            primary = ai.get("under_probability")
            fallback = None

        primary_value = self._safe_float(primary)
        fallback_value = self._safe_float(fallback)

        if primary_value > 0:
            return primary_value

        if fallback_value > 0:
            return fallback_value

        return None

    def _resolve_market_type(
        self,
        market_type: Optional[str],
        market_market_type: Optional[str],
    ) -> Optional[str]:
        for raw in (market_type, market_market_type):
            if not raw:
                continue
            text = str(raw).strip().upper()
            if "OVER" in text:
                return "OVER"
            if "UNDER" in text:
                return "UNDER"
        return None

    def _normalize_probability(self, value: float) -> float:
        if value > 1:
            value = value / 100.0
        return max(0.0, min(value, 1.0))

    def _categorize_edge(self, edge: float, min_required: float) -> str:
        if edge <= 0:
            return "NEGATIVE"
        if edge < min_required:
            return "WEAK"
        if edge < min_required + 0.02:
            return "FAIR"
        if edge < min_required + 0.05:
            return "GOOD"
        return "STRONG"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "is_value": False,
            "status": "VALUE_REJECTED",
            "value_category": "NONE",
            "market_type": None,
            "odds": None,
            "prob_real": None,
            "prob_implicita": None,
            "edge": 0.0,
            "min_required_edge": None,
            "reason": reason,
            }
