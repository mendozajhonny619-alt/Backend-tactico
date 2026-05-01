from __future__ import annotations

from typing import Any, Dict, Optional


class ValueEngine:
    """
    Calcula edge real comparando:

    - prob_real del modelo
    - prob_implicita de la cuota

    Devuelve:
    - edge
    - prob_real
    - prob_implicita
    - is_value
    - status
    - value_category

    Reglas:
    - edge <= 0 => no value
    - edge débil => no value
    - edge mínimo:
        OVER  -> 0.03
        UNDER -> 0.04
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

        if not market.get("is_valid"):
            return self._reject(market.get("reason") or "VALUE_MARKET_NOT_VALID")

        odds = self._safe_float(market.get("odds"))
        resolved_market_type = self._resolve_market_type(
            market_type=market_type,
            market_market_type=market.get("market_type"),
        )

        if odds <= 1.0:
            return self._reject("VALUE_ODDS_INVALID")

        if resolved_market_type not in {"OVER", "UNDER"}:
            return self._reject("VALUE_MARKET_TYPE_UNKNOWN")

        prob_real = self._resolve_real_probability(ai=ai, market_type=resolved_market_type)
        if prob_real is None:
            return self._reject("VALUE_REAL_PROBABILITY_MISSING")

        prob_real = self._normalize_probability(prob_real)
        prob_implicita = 1.0 / odds
        edge = prob_real - prob_implicita

        min_required = (
            self.MIN_EDGE_OVER if resolved_market_type == "OVER" else self.MIN_EDGE_UNDER
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
        }

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
        """
        Acepta probabilidad en formato:
        - 0.67
        - 67
        y la devuelve en rango 0..1
        """
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
