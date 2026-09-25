from __future__ import annotations

from typing import Any, Dict


class EliteSignalGate:
    """
    Filtro final para señales OVER.

    Ajuste:
    - No bloquea automáticamente OVER después del minuto 75.
    - Permite OVER tardío solo con reactivación real, caos, red alert o presión extrema.
    - Mantiene protección contra presión falsa, retención, cooling y baja calidad.
    """

    def validate(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        window: Dict[str, Any],
        market: Dict[str, Any],
        value: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = context or {}
        ai = ai or {}
        window = window or {}
        market = market or {}
        value = value or {}

        data_quality = str(context.get("data_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))

        pressure_index = self._safe_float(context.get("pressure_index"))
        rhythm_index = self._safe_float(context.get("rhythm_index"))
        over_window_score = self._safe_float(context.get("over_window_score"))
        goal_window_score = self._safe_float(context.get("goal_window_score"))

        gate_min = self._safe_float(window.get("gate_min_score")) or 60
        minute = self._safe_float(window.get("minute") or context.get("minute"))

        market_valid = bool(market.get("is_valid"))
        odds = self._safe_float(market.get("odds"))
        market_status = str(market.get("market_status") or "").upper()

        is_value = bool(value.get("is_value"))
        edge = self._safe_float(value.get("edge"))
        value_category = str(value.get("value_category") or "").upper()

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        red_alert = bool(context.get("red_alert", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        is_added_time = bool(
            context.get("is_added_time")
            or context.get("field_vision_is_added_time")
            or minute >= 90
        )

        late_over_allowed = self._has_late_over_permission(
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

        if data_quality not in {"MEDIUM", "HIGH"}:
            if not late_over_allowed:
                return self._reject("GATE_DATA_QUALITY_NOT_ENOUGH")

        if minute and minute < 15:
            return self._reject("GATE_OVER_TOO_EARLY")

        if minute and minute > 75 and not late_over_allowed:
            return self._reject("GATE_OVER_TOO_LATE_WITHOUT_REACTIVATION")

        if fake_pressure_detected:
            return self._reject("GATE_OVER_FAKE_PRESSURE")

        if pressure_without_depth:
            return self._reject("GATE_OVER_PRESSURE_WITHOUT_DEPTH")

        if retention_shape:
            return self._reject("GATE_OVER_RETENTION_SHAPE")

        if cooling_detected or live_decay_factor <= 0.70:
            if not late_over_allowed:
                return self._reject("GATE_OVER_LIVE_COOLING")

        if under_transition_score >= 70:
            if not late_over_allowed:
                return self._reject("GATE_OVER_UNDER_TRANSITION_ACTIVE")

        if ai_score < max(gate_min - 10, 52):
            return self._reject("GATE_AI_SCORE_TOO_LOW")

        if goal_probability < 58:
            return self._reject("GATE_GOAL_PROB_TOO_LOW")

        if over_probability < 58:
            return self._reject("GATE_OVER_PROB_TOO_LOW")

        if risk_score > 7.5:
            if not late_over_allowed:
                return self._reject("GATE_RISK_SCORE_TOO_HIGH")

        if context_state not in {"TIBIO", "CALIENTE", "MUY_CALIENTE", "CONTROLADO"}:
            if not late_over_allowed:
                return self._reject("GATE_CONTEXT_NOT_ALIGNED")

        if context_state == "CONTROLADO":
            if not late_over_allowed and (
                goal_probability < 68
                or over_probability < 68
                or pressure_index < 14
            ):
                return self._reject("GATE_CONTROLLED_CONTEXT_NOT_STRONG_ENOUGH")

        if pressure_index < 8:
            return self._reject("GATE_PRESSURE_TOO_LOW")

        if rhythm_index < 5:
            return self._reject("GATE_RHYTHM_TOO_LOW")

        if over_window_score < 8:
            if not late_over_allowed:
                return self._reject("GATE_OVER_WINDOW_TOO_LOW")

        if goal_window_score < 8:
            if not late_over_allowed:
                return self._reject("GATE_GOAL_WINDOW_TOO_LOW")

        if late_over_allowed and minute >= 80:
            if not self._late_consensus_check(context, ai):
                return self._reject("GATE_LATE_OVER_NO_EXTREME_CONSENSUS")

        if not market_valid:
            return self._reject("GATE_MARKET_INVALID")

        if market_status != "INTERNAL_ONLY":
            if not odds or odds < 1.50 or odds > 2.10:
                return self._reject("GATE_ODDS_OUT_OF_RANGE")

        if value_category != "INTERNAL":
            if not is_value:
                return self._reject("GATE_NO_VALUE")

            if edge < 0.02:
                return self._reject("GATE_EDGE_TOO_LOW")

        if not self._consensus_check(context, ai, value, late_over_allowed=late_over_allowed):
            return self._reject("GATE_NO_CONSENSUS")

        return {
            "approved": True,
            "reason": "GATE_APPROVED_LATE_REACTIVATION" if late_over_allowed and minute >= 76 else "GATE_APPROVED",
            "late_over_allowed": late_over_allowed,
        }

    def _has_late_over_permission(
        self,
        minute: float,
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
        if minute < 76:
            return True

        if late_reactivation or chaos_mode or red_alert:
            return True

        if field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
            return True

        if (
            pressure >= 28
            and rhythm >= 15
            and (goal_window >= 22 or over_window >= 22)
            and context_state in {"CALIENTE", "MUY_CALIENTE"}
        ):
            return True

        if is_added_time and pressure >= 30 and rhythm >= 16:
            return True

        return False

    def _late_consensus_check(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> bool:
        checks = 0

        if self._safe_float(ai.get("goal_probability")) >= 64:
            checks += 1

        if self._safe_float(ai.get("over_probability")) >= 64:
            checks += 1

        if self._safe_float(ai.get("ai_score")) >= 60:
            checks += 1

        if self._safe_float(context.get("pressure_index")) >= 18:
            checks += 1

        if self._safe_float(context.get("rhythm_index")) >= 11:
            checks += 1

        if self._safe_float(context.get("goal_window_score")) >= 14:
            checks += 1

        if self._safe_float(context.get("over_window_score")) >= 14:
            checks += 1

        if str(context.get("context_state") or "").upper() in {"CALIENTE", "MUY_CALIENTE"}:
            checks += 1

        if bool(context.get("late_reactivation")) or bool(context.get("chaos_mode")) or bool(context.get("red_alert")):
            checks += 1

        return checks >= 5

    def _consensus_check(
        self,
        context: Dict[str, Any],
        ai: Dict[str, Any],
        value: Dict[str, Any],
        late_over_allowed: bool = False,
    ) -> bool:
        checks = 0

        if self._safe_float(ai.get("goal_probability")) >= 62:
            checks += 1

        if self._safe_float(ai.get("over_probability")) >= 62:
            checks += 1

        if self._safe_float(ai.get("ai_score")) >= 55:
            checks += 1

        if self._safe_float(context.get("pressure_index")) >= 10:
            checks += 1

        if self._safe_float(context.get("rhythm_index")) >= 6:
            checks += 1

        if str(context.get("context_state") or "").upper() in {"TIBIO", "CALIENTE", "MUY_CALIENTE"}:
            checks += 1

        value_category = str(value.get("value_category") or "").upper()
        if value_category == "INTERNAL" or self._safe_float(value.get("edge")) >= 0.02:
            checks += 1

        if late_over_allowed:
            if bool(context.get("late_reactivation")) or bool(context.get("chaos_mode")) or bool(context.get("red_alert")):
                checks += 1

            return checks >= 5

        return checks >= 4

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "approved": False,
            "reason": reason,
        }
