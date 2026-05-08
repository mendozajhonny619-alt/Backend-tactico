from __future__ import annotations

from typing import Any, Dict


class FinalDecisionEngine:
    """
    Capa maestra de decisión final.

    No reemplaza motores existentes.
    No calcula contexto.
    No calcula probabilidades.
    No valida cuotas directamente.

    Solo decide si una oportunidad realmente merece:
    - ENTER
    - OBSERVE
    - WAIT
    - NO_REENTRY
    - AVOID
    """

    DECISION_ENTER = "ENTER"
    DECISION_OBSERVE = "OBSERVE"
    DECISION_WAIT = "WAIT"
    DECISION_NO_REENTRY = "NO_REENTRY"
    DECISION_AVOID = "AVOID"

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        risk: Dict[str, Any],
        tactical: Dict[str, Any],
        opportunity: Dict[str, Any],
        market: Dict[str, Any] | None = None,
        value: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}
        window = window or {}
        risk = risk or {}
        tactical = tactical or {}
        opportunity = opportunity or {}
        market = market or {}
        value = value or {}

        minute = self._safe_int(match.get("minute") or context.get("minute"))
        market_type = str(opportunity.get("market") or "").upper()
        opportunity_type = str(opportunity.get("type") or "").upper()
        rank = str(opportunity.get("rank") or "").upper()

        context_state = str(context.get("context_state") or "MUERTO").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        fake_pressure_detected = bool(
            context.get("fake_pressure_detected")
            or match.get("fake_pressure_detected")
            or match.get("deep_fake_pressure_detected")
        )
        pressure_without_depth = bool(
            context.get("pressure_without_depth")
            or match.get("pressure_without_depth")
            or match.get("deep_pressure_without_depth")
        )

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        risk_score = self._safe_float(risk.get("risk_score") or ai.get("risk_score"))
        risk_level = str(risk.get("risk_level") or ai.get("risk_level") or "ALTO").upper()

        window_allowed = bool(window.get("allowed", False))
        allow_over = bool(window.get("allow_over", False))
        allow_under = bool(window.get("allow_under", False))

        market_status = str(market.get("market_status") or "").upper()
        market_valid = bool(market.get("is_valid", False))
        is_value = bool(value.get("is_value", False))
        value_edge = self._safe_float(value.get("edge"))

        score_hold_probability = self._safe_float(match.get("score_hold_probability"))
        retention_risk = self._safe_float(match.get("retention_risk"))
        retention_risk_label = str(match.get("retention_risk_label") or "").upper()

        next_goal_confidence = self._safe_float(match.get("next_goal_confidence"))
        next_goal_bias = str(match.get("next_goal_bias") or "").upper()
        next_goal_support = str(match.get("next_goal_support") or "").upper()

        deep_projection_bias = str(match.get("deep_projection_bias") or "").upper()
        risk_reducer_status = str(match.get("risk_reducer_status") or "").upper()
        revalidation_status = str(match.get("revalidation_status") or "").upper()
        signal_decay_status = str(match.get("signal_decay_status") or "").upper()

        signal_life_status = str(
            match.get("signal_life_status")
            or match.get("deep_signal_life_status")
            or ""
        ).upper()

        decision = self.DECISION_OBSERVE
        reason = "FINAL_DECISION_OBSERVE_DEFAULT"
        confidence = 50.0

        # =========================
        # BLOQUEOS ABSOLUTOS
        # =========================
        if not window_allowed:
            return self._result(
                decision=self.DECISION_AVOID,
                reason="FINAL_AVOID_INVALID_WINDOW",
                confidence=90,
                market_type=market_type,
            )

        if opportunity_type in {"NO_BET", "REJECTED"}:
            return self._result(
                decision=self.DECISION_AVOID,
                reason="FINAL_AVOID_NO_VALID_OPPORTUNITY",
                confidence=88,
                market_type=market_type,
            )

        if risk_level == "ALTO" and risk_score >= 8.5:
            return self._result(
                decision=self.DECISION_AVOID,
                reason="FINAL_AVOID_RISK_TOO_HIGH",
                confidence=86,
                market_type=market_type,
            )

        if minute >= 86:
            return self._result(
                decision=self.DECISION_NO_REENTRY,
                reason="FINAL_NO_REENTRY_TOO_LATE",
                confidence=84,
                market_type=market_type,
            )

        if signal_life_status in {"EXPIRED", "DEAD", "NO_REENTRY"}:
            return self._result(
                decision=self.DECISION_NO_REENTRY,
                reason="FINAL_NO_REENTRY_SIGNAL_LIFE_EXPIRED",
                confidence=82,
                market_type=market_type,
            )

        if signal_decay_status in {"NO_REENTRY", "AVOID"}:
            return self._result(
                decision=self.DECISION_NO_REENTRY,
                reason="FINAL_NO_REENTRY_SIGNAL_DECAY_BLOCK",
                confidence=86,
                market_type=market_type,
            )

        if revalidation_status in {"HIGH_RISK", "NO_REENTRY", "AVOID"}:
            return self._result(
                decision=self.DECISION_NO_REENTRY,
                reason="FINAL_NO_REENTRY_REVALIDATION_BLOCK",
                confidence=84,
                market_type=market_type,
            )

        if risk_reducer_status in {"NO_REENTRY", "AVOID"}:
            return self._result(
                decision=self.DECISION_NO_REENTRY,
                reason="FINAL_NO_REENTRY_RISK_REDUCER_BLOCK",
                confidence=84,
                market_type=market_type,
            )

        # =========================
        # OVER: PROTECCIÓN PRINCIPAL
        # =========================
        if market_type == "OVER":
            if not allow_over:
                return self._result(
                    decision=self.DECISION_AVOID,
                    reason="FINAL_AVOID_OVER_NOT_ALLOWED_BY_WINDOW",
                    confidence=86,
                    market_type=market_type,
                )

            if context_state in {"MUERTO", "FRIO"}:
                return self._result(
                    decision=self.DECISION_AVOID,
                    reason="FINAL_AVOID_OVER_COLD_CONTEXT",
                    confidence=88,
                    market_type=market_type,
                )

            if fake_pressure_detected or pressure_without_depth:
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_FAKE_PRESSURE",
                    confidence=88,
                    market_type=market_type,
                )

            if cooling_detected or live_decay_factor <= 0.70:
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_LIVE_COOLING",
                    confidence=86,
                    market_type=market_type,
                )

            if under_transition_score >= 70:
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_UNDER_TRANSITION",
                    confidence=90,
                    market_type=market_type,
                )

            if retention_risk >= 70 or retention_risk_label == "ALTO":
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_RETENTION_RISK",
                    confidence=88,
                    market_type=market_type,
                )

            if score_hold_probability >= 70 and score_hold_probability > goal_probability:
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_HOLD_BEATS_GOAL",
                    confidence=88,
                    market_type=market_type,
                )

            if next_goal_support == "AGAINST_OVER":
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_NEXT_GOAL_AGAINST_OVER",
                    confidence=84,
                    market_type=market_type,
                )

            if minute >= 43 and minute <= 45 and not self._has_extreme_over_pressure(
                pressure, rhythm, goal_window, over_window, context_state
            ):
                return self._result(
                    decision=self.DECISION_WAIT,
                    reason="FINAL_WAIT_OVER_FIRST_HALF_DEAD_ZONE",
                    confidence=76,
                    market_type=market_type,
                )

            if minute >= 80 and not self._has_extreme_over_pressure(
                pressure, rhythm, goal_window, over_window, context_state
            ):
                return self._result(
                    decision=self.DECISION_NO_REENTRY,
                    reason="FINAL_NO_REENTRY_OVER_LATE_NO_EXTREME_PRESSURE",
                    confidence=84,
                    market_type=market_type,
                )

            if pressure >= 12 and rhythm < 7 and goal_probability < 62:
                return self._result(
                    decision=self.DECISION_OBSERVE,
                    reason="FINAL_OBSERVE_OVER_PRESSURE_WITHOUT_RHYTHM",
                    confidence=68,
                    market_type=market_type,
                )

            if market_valid and not is_value:
                return self._result(
                    decision=self.DECISION_WAIT,
                    reason="FINAL_WAIT_OVER_MARKET_NO_VALUE",
                    confidence=72,
                    market_type=market_type,
                )

            if (
                ai_score >= 64
                and goal_probability >= 66
                and over_probability >= 66
                and pressure >= 14
                and rhythm >= 9
                and context_state in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}
                and risk_score <= 7.2
                and rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}
            ):
                if market_valid and is_value:
                    decision = self.DECISION_ENTER
                    reason = "FINAL_ENTER_OVER_CONFIRMED_BY_CONTEXT_MARKET_VALUE"
                    confidence = 82 + min(10, value_edge * 100)
                elif market_status == "INTERNAL_ONLY" or not market_valid:
                    decision = self.DECISION_OBSERVE
                    reason = "FINAL_OBSERVE_OVER_INTERNAL_ONLY_NO_MARKET_CONFIRMATION"
                    confidence = 72
                else:
                    decision = self.DECISION_WAIT
                    reason = "FINAL_WAIT_OVER_NEEDS_MARKET_CONFIRMATION"
                    confidence = 70

        # =========================
        # UNDER: VALIDACIÓN PRINCIPAL
        # =========================
        elif market_type == "UNDER":
            if not allow_under:
                return self._result(
                    decision=self.DECISION_AVOID,
                    reason="FINAL_AVOID_UNDER_NOT_ALLOWED_BY_WINDOW",
                    confidence=84,
                    market_type=market_type,
                )

            if context_state in {"CALIENTE", "MUY_CALIENTE"} and pressure >= 22:
                return self._result(
                    decision=self.DECISION_AVOID,
                    reason="FINAL_AVOID_UNDER_HOT_CONTEXT",
                    confidence=88,
                    market_type=market_type,
                )

            if minute < 58:
                return self._result(
                    decision=self.DECISION_WAIT,
                    reason="FINAL_WAIT_UNDER_TOO_EARLY",
                    confidence=76,
                    market_type=market_type,
                )

            if goal_probability >= 60 and under_transition_score < 70:
                return self._result(
                    decision=self.DECISION_OBSERVE,
                    reason="FINAL_OBSERVE_UNDER_GOAL_PROB_STILL_HIGH",
                    confidence=70,
                    market_type=market_type,
                )

            if pressure > 28 or rhythm > 18:
                return self._result(
                    decision=self.DECISION_AVOID,
                    reason="FINAL_AVOID_UNDER_TOO_MUCH_ACTIVITY",
                    confidence=82,
                    market_type=market_type,
                )

            under_context_confirmed = (
                context_state in {"CONTROLADO", "FRIO", "MUERTO"}
                or cooling_detected
                or fake_pressure_detected
                or pressure_without_depth
                or under_transition_score >= 70
                or score_hold_probability >= 68
                or retention_risk >= 65
                or retention_risk_label == "ALTO"
                or deep_projection_bias == "UNDER"
                or next_goal_support == "SUPPORTS_UNDER"
            )

            if (
                under_probability >= 64
                and goal_probability <= 55
                and pressure <= 24
                and rhythm <= 15
                and under_context_confirmed
                and risk_score <= 7.5
                and rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}
            ):
                if market_valid and is_value:
                    decision = self.DECISION_ENTER
                    reason = "FINAL_ENTER_UNDER_CONFIRMED_BY_RETENTION_MARKET_VALUE"
                    confidence = 82 + min(10, value_edge * 100)
                elif market_status == "INTERNAL_ONLY" or not market_valid:
                    decision = self.DECISION_OBSERVE
                    reason = "FINAL_OBSERVE_UNDER_INTERNAL_ONLY_NO_MARKET_CONFIRMATION"
                    confidence = 74
                else:
                    decision = self.DECISION_WAIT
                    reason = "FINAL_WAIT_UNDER_NEEDS_MARKET_CONFIRMATION"
                    confidence = 72

        else:
            return self._result(
                decision=self.DECISION_AVOID,
                reason="FINAL_AVOID_UNKNOWN_MARKET",
                confidence=82,
                market_type=market_type,
            )

        # =========================
        # AJUSTES FINALES
        # =========================
        if decision == self.DECISION_ENTER and data_quality == "LOW":
            decision = self.DECISION_OBSERVE
            reason = "FINAL_OBSERVE_LOW_DATA_DOWNGRADE"
            confidence = min(confidence, 70)

        if decision == self.DECISION_ENTER and game_quality == "LOW" and market_type == "OVER":
            decision = self.DECISION_WAIT
            reason = "FINAL_WAIT_OVER_LOW_GAME_QUALITY"
            confidence = min(confidence, 68)

        if decision == self.DECISION_ENTER and risk_reducer_status == "HIGH_CAUTION":
            decision = self.DECISION_WAIT
            reason = "FINAL_WAIT_RISK_REDUCER_HIGH_CAUTION"
            confidence = min(confidence, 70)

        if decision == self.DECISION_ENTER and revalidation_status in {"COOLING", "WEAKENING"}:
            decision = self.DECISION_WAIT
            reason = "FINAL_WAIT_REVALIDATION_WEAKENING"
            confidence = min(confidence, 70)

        if decision == self.DECISION_ENTER and signal_decay_status in {"COOLING", "AGING"}:
            decision = self.DECISION_WAIT
            reason = "FINAL_WAIT_SIGNAL_DECAY_WARNING"
            confidence = min(confidence, 70)

        if decision == self.DECISION_ENTER and next_goal_confidence > 0:
            if market_type == "OVER" and next_goal_bias in {"NONE", "NO_GOAL", "HOLD"}:
                decision = self.DECISION_OBSERVE
                reason = "FINAL_OBSERVE_OVER_NEXT_GOAL_NOT_CONFIRMED"
                confidence = min(confidence, 72)

        return self._result(
            decision=decision,
            reason=reason,
            confidence=confidence,
            market_type=market_type,
        )

    def _has_extreme_over_pressure(
        self,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
    ) -> bool:
        return (
            pressure >= 28
            and rhythm >= 15
            and (goal_window >= 24 or over_window >= 24)
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        )

    def _result(
        self,
        decision: str,
        reason: str,
        confidence: float,
        market_type: str,
    ) -> Dict[str, Any]:
        return {
            "final_decision": decision,
            "final_decision_reason": reason,
            "final_decision_confidence": round(self._clamp(confidence, 0.0, 100.0), 2),
            "final_decision_market": market_type,
            "should_enter": decision == self.DECISION_ENTER,
            "should_observe": decision == self.DECISION_OBSERVE,
            "should_wait": decision == self.DECISION_WAIT,
            "should_no_reentry": decision == self.DECISION_NO_REENTRY,
            "should_avoid": decision == self.DECISION_AVOID,
        }

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

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(value, max_value))
