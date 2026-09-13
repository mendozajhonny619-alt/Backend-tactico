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
    - lectura live avanzada

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

        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))
        goal_window_score = self._safe_float(context.get("goal_window_score"))
        over_window_score = self._safe_float(context.get("over_window_score"))

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        window_phase = str(window.get("phase") or "BLOCKED").upper()
        window_bias = str(window.get("bias") or "").upper()
        gate_min_score = self._safe_float(window.get("gate_min_score"))
        minute = self._safe_int(window.get("minute") or context.get("minute"))

        market_valid = bool(market.get("is_valid")) if market else False
        odds = self._safe_float(market.get("odds")) if market else 0.0
        market_type = str(market.get("market_type") or market.get("market") or "").upper()
        market_status = str(market.get("market_status") or "").upper()

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        red_alert = bool(context.get("red_alert", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        score_hold_probability = self._safe_float(context.get("score_hold_probability"))
        retention_risk = self._safe_float(context.get("retention_risk"))

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        is_added_time = bool(
            context.get("is_added_time")
            or context.get("field_vision_is_added_time")
            or minute >= 90
        )

        live_reactivation = self._has_live_reactivation(
            minute=minute,
            pressure=pressure_index,
            rhythm=rhythm_index,
            goal_window=goal_window_score,
            over_window=over_window_score,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        # ---------------------------------------------------
        # DATA QUALITY
        # ---------------------------------------------------
        if data_quality == "LOW":
            if live_reactivation:
                risk_score += 1.2
                risk_flags.append("DATA_QUALITY_LOW_BUT_REACTIVATION")
            else:
                risk_score += 2.3
                risk_flags.append("DATA_QUALITY_LOW")

        elif data_quality == "MEDIUM":
            risk_score += 0.9
            risk_flags.append("DATA_QUALITY_MEDIUM")

        # ---------------------------------------------------
        # GAME QUALITY
        # ---------------------------------------------------
        if game_quality == "LOW":
            if live_reactivation:
                risk_score += 0.8
                risk_flags.append("GAME_QUALITY_LOW_BUT_LIVE_PRESSURE")
            else:
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

        if live_reactivation:
            risk_score -= 1.0
            risk_flags.append("LIVE_REACTIVATION_REDUCES_RISK")

        if chaos_mode:
            risk_score -= 0.4
            risk_flags.append("CHAOS_MODE_OPERABLE")

        if red_alert:
            risk_score += 0.3
            risk_flags.append("RED_ALERT_VOLATILITY")

        # ---------------------------------------------------
        # FAKE PRESSURE / RETENTION
        # ---------------------------------------------------
        if fake_pressure_detected:
            risk_score += 1.8
            risk_flags.append("FAKE_PRESSURE_DETECTED")

        if pressure_without_depth:
            risk_score += 1.3
            risk_flags.append("PRESSURE_WITHOUT_DEPTH")

        if retention_shape:
            risk_score += 1.4
            risk_flags.append("RETENTION_SHAPE")

        if score_hold_probability >= 70:
            risk_score += 1.2
            risk_flags.append("SCORE_HOLD_PROBABILITY_HIGH")

        if retention_risk >= 70:
            risk_score += 1.2
            risk_flags.append("RETENTION_RISK_HIGH")

        # ---------------------------------------------------
        # LIVE COOLING / UNDER TRANSITION
        # ---------------------------------------------------
        if cooling_detected:
            if live_reactivation:
                risk_score += 0.3
                risk_flags.append("COOLING_BUT_REACTIVATED")
            else:
                risk_score += 1.2
                risk_flags.append("LIVE_COOLING_DETECTED")

        if under_transition_score >= 70:
            if market_type == "UNDER" or window_bias == "UNDER":
                risk_score -= 0.2
                risk_flags.append("UNDER_TRANSITION_SUPPORTS_UNDER")
            elif live_reactivation:
                risk_score += 0.5
                risk_flags.append("UNDER_TRANSITION_BUT_REACTIVATION")
            else:
                risk_score += 1.4
                risk_flags.append("UNDER_TRANSITION_ACTIVE")

        elif under_transition_score >= 55:
            risk_score += 0.7
            risk_flags.append("UNDER_TRANSITION_WARNING")

        if live_decay_factor <= 0.70:
            if live_reactivation:
                risk_score += 0.2
                risk_flags.append("LIVE_DECAY_LOW_BUT_REACTIVATED")
            else:
                risk_score += 0.8
                risk_flags.append("LIVE_DECAY_LOW")

        # ---------------------------------------------------
        # PRESSURE / RHYTHM
        # ---------------------------------------------------
        if pressure_index < 10:
            risk_score += 1.8
            risk_flags.append("PRESSURE_TOO_LOW")
        elif pressure_index < 16:
            risk_score += 0.8
        elif pressure_index >= 26:
            risk_score -= 0.3
            risk_flags.append("PRESSURE_STRONG")

        if rhythm_index < 7:
            risk_score += 1.4
            risk_flags.append("RHYTHM_TOO_LOW")
        elif rhythm_index < 11:
            risk_score += 0.6
        elif rhythm_index >= 15:
            risk_score -= 0.3
            risk_flags.append("RHYTHM_STRONG")

        if fake_pressure_detected or pressure_without_depth:
            risk_score += 0.8

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
            if live_reactivation:
                risk_score += 0.7
                risk_flags.append("WINDOW_RESTRICTED_BUT_REACTIVATION")
            else:
                risk_score += 1.5
                risk_flags.append("WINDOW_RESTRICTED")
        elif window_phase == "OPERABLE":
            risk_score += 0.4
        elif window_phase == "PREMIUM":
            risk_score -= 0.3

        if gate_min_score > 0 and ai_score > 0 and ai_score < gate_min_score:
            if live_reactivation:
                risk_score += 0.3
                risk_flags.append("WINDOW_GATE_NOT_MET_BUT_REACTIVATION")
            else:
                risk_score += 0.9
                risk_flags.append("WINDOW_GATE_NOT_MET")

        # ---------------------------------------------------
        # LATE GAME
        # ---------------------------------------------------
        if minute >= 80:
            if live_reactivation:
                risk_score += 0.4
                risk_flags.append("LATE_GAME_WITH_REACTIVATION")
            else:
                risk_score += 1.0
                risk_flags.append("LATE_GAME_RISK")

        if is_added_time:
            if live_reactivation:
                risk_score += 0.5
                risk_flags.append("ADDED_TIME_WITH_PRESSURE")
            else:
                risk_score += 1.2
                risk_flags.append("ADDED_TIME_NO_REACTIVATION")

        # ---------------------------------------------------
        # MARKET
        # ---------------------------------------------------
        if market:
            if not market_valid:
                if market_status in {"PENDING", "INTERNAL_ONLY"}:
                    risk_score += 0.5
                    risk_flags.append("MARKET_INTERNAL_OR_PENDING")
                else:
                    risk_score += 1.0
                    risk_flags.append("MARKET_INVALID")
            else:
                if odds > 0:
                    if odds < 1.55:
                        risk_score += 0.6
                        risk_flags.append("ODDS_TOO_LOW")
                    elif odds > 2.05:
                        if live_reactivation:
                            risk_score += 0.3
                            risk_flags.append("ODDS_HIGH_BUT_LIVE_REACTIVATION")
                        else:
                            risk_score += 0.8
                            risk_flags.append("ODDS_TOO_HIGH")
                    else:
                        risk_score -= 0.1

        # ---------------------------------------------------
        # Ajustes de coherencia
        # ---------------------------------------------------
        if market_type == "OVER":
            if retention_shape or fake_pressure_detected or pressure_without_depth:
                risk_score += 0.8
                risk_flags.append("OVER_CONTEXT_RISK")

            if under_transition_score >= 70 and not live_reactivation:
                risk_score += 0.8
                risk_flags.append("OVER_AGAINST_UNDER_TRANSITION")

        if market_type == "UNDER":
            if retention_shape or score_hold_probability >= 70 or under_transition_score >= 70:
                risk_score -= 0.5
                risk_flags.append("UNDER_CONTEXT_SUPPORT")

            if context_state in {"CALIENTE", "MUY_CALIENTE"} and pressure_index >= 22:
                risk_score += 1.0
                risk_flags.append("UNDER_HOT_CONTEXT_RISK")

        # ---------------------------------------------------
        # Clamp / label / accept
        # ---------------------------------------------------
        risk_score = max(0.0, min(risk_score, 10.0))
        risk_level = self._risk_label(risk_score)

        is_risk_acceptable = risk_score <= 6.8

        return {
            "is_risk_acceptable": is_risk_acceptable,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "risk_live_reactivation": live_reactivation,
        }

    def _has_live_reactivation(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
        late_reactivation: bool,
        chaos_mode: bool,
        red_alert: bool,
        field_vision_status: str,
        is_added_time: bool,
    ) -> bool:
        if minute < 70:
            return False

        if late_reactivation or chaos_mode or red_alert:
            return True

        if field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
            return True

        if (
            pressure >= 26
            and rhythm >= 15
            and (goal_window >= 22 or over_window >= 22)
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if is_added_time and pressure >= 30 and rhythm >= 16:
            return True

        return False

    def _risk_label(self, risk_score: float) -> str:
        if risk_score <= 3.0:
            return "BAJO"
        if risk_score <= 6.8:
            return "MEDIO"
        return "ALTO"

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
