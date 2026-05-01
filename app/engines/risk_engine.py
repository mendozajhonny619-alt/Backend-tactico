from __future__ import annotations

from typing import Any, Dict


class RiskEngine:
    """
    Evalúa riesgo operativo total.

    Mezcla:
    - calidad de datos
    - contexto
    - IA
    - ventana
    - mercado

    Devuelve:
    - is_risk_acceptable
    - risk_score
    - risk_level
    - risk_flags
    """

    def evaluate(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        market: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        context = context or {}
        ai = ai or {}
        window = window or {}
        market = market or {}

        risk_score = 0.0
        risk_flags: list[str] = []

        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()

        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        window_phase = str(window.get("phase") or "BLOCKED").upper()
        gate_min_score = self._safe_float(window.get("gate_min_score"))

        market_valid = bool(market.get("is_valid")) if market else False
        odds = self._safe_float(market.get("odds")) if market else 0.0

        # ---------------------------------------------------
        # DATA QUALITY
        # ---------------------------------------------------
        if data_quality == "LOW":
            risk_score += 2.3
            risk_flags.append("DATA_QUALITY_LOW")
        elif data_quality == "MEDIUM":
            risk_score += 0.9
            risk_flags.append("DATA_QUALITY_MEDIUM")

        # ---------------------------------------------------
        # GAME QUALITY
        # ---------------------------------------------------
        if game_quality == "LOW":
            risk_score += 1.8
            risk_flags.append("GAME_QUALITY_LOW")
        elif game_quality == "MEDIUM":
            risk_score += 0.6

        # ---------------------------------------------------
        # CONTEXT STATE
        # ---------------------------------------------------
        if context_state == "MUERTO":
            risk_score += 2.6
            risk_flags.append("CONTEXT_DEAD")
        elif context_state == "FRIO":
            risk_score += 1.7
            risk_flags.append("CONTEXT_COLD")
        elif context_state == "CONTROLADO":
            risk_score += 1.0
        elif context_state == "TIBIO":
            risk_score += 0.5
        elif context_state in {"CALIENTE", "MUY_CALIENTE"}:
            risk_score -= 0.4

        # ---------------------------------------------------
        # PRESSURE / RHYTHM
        # ---------------------------------------------------
        if pressure_index < 10:
            risk_score += 1.8
            risk_flags.append("PRESSURE_TOO_LOW")
        elif pressure_index < 16:
            risk_score += 0.8

        if rhythm_index < 7:
            risk_score += 1.4
            risk_flags.append("RHYTHM_TOO_LOW")
        elif rhythm_index < 11:
            risk_score += 0.6

        # ---------------------------------------------------
        # IA / PROBABILIDADES
        # ---------------------------------------------------
        if ai_score < 45:
            risk_score += 2.5
            risk_flags.append("AI_SCORE_VERY_LOW")
        elif ai_score < 60:
            risk_score += 1.2
            risk_flags.append("AI_SCORE_LOW")
        elif ai_score >= 78:
            risk_score -= 0.5

        if goal_probability < 50:
            risk_score += 1.2
            risk_flags.append("GOAL_PROB_LOW")
        elif goal_probability >= 68:
            risk_score -= 0.3

        strongest_market_prob = max(over_probability, under_probability)
        if strongest_market_prob < 58:
            risk_score += 1.0
            risk_flags.append("MARKET_PROBABILITY_WEAK")
        elif strongest_market_prob >= 70:
            risk_score -= 0.2

        # ---------------------------------------------------
        # WINDOW
        # ---------------------------------------------------
        if window_phase == "BLOCKED":
            risk_score += 3.5
            risk_flags.append("WINDOW_BLOCKED")
        elif window_phase == "RESTRICTED":
            risk_score += 1.5
            risk_flags.append("WINDOW_RESTRICTED")
        elif window_phase == "OPERABLE":
            risk_score += 0.4
        elif window_phase == "PREMIUM":
            risk_score -= 0.3

        if gate_min_score > 0 and ai_score > 0 and ai_score < gate_min_score:
            risk_score += 0.9
            risk_flags.append("WINDOW_GATE_NOT_MET")

        # ---------------------------------------------------
        # MARKET
        # ---------------------------------------------------
        if market:
            if not market_valid:
                risk_score += 1.0
                risk_flags.append("MARKET_INVALID")
            else:
                if odds < 1.55:
                    risk_score += 0.6
                    risk_flags.append("ODDS_TOO_LOW")
                elif odds > 2.05:
                    risk_score += 0.8
                    risk_flags.append("ODDS_TOO_HIGH")
                else:
                    risk_score -= 0.1

        # ---------------------------------------------------
        # Clamp / label / accept
        # ---------------------------------------------------
        risk_score = max(0.0, min(risk_score, 10.0))
        risk_level = self._risk_label(risk_score)

        is_risk_acceptable = risk_score <= 6.5

        return {
            "is_risk_acceptable": is_risk_acceptable,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
        }

    def _risk_label(self, risk_score: float) -> str:
        if risk_score <= 3.0:
            return "BAJO"
        if risk_score <= 6.5:
            return "MEDIO"
        return "ALTO"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
