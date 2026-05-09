from __future__ import annotations

from typing import Any, Dict


class TacticalEngine:
    """
    Motor táctico del partido.

    Clasifica:
    - EXPLOSIVO
    - CALIENTE
    - CONTROLADO
    - FRIO
    - MUERTO

    Devuelve:
    - tactical_state
    - tempo_label
    - tactical_bias
    - market_alignment
    """

    def evaluate(
        self,
        context: Dict[str, Any],
        window: Dict[str, Any],
    ) -> Dict[str, Any]:

        context = context or {}
        window = window or {}

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_prob = self._safe_float(
            context.get("goal_probability")
            or context.get("goal_window_score")
        )
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        minute = self._safe_float(context.get("minute"))

        dominance = str(context.get("dominance") or "BALANCED").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        window_bias = str(window.get("bias") or "NONE").upper()

        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

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
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        if chaos_mode or red_alert:
            tactical_state = "EXPLOSIVO"
        elif live_reactivation:
            tactical_state = "CALIENTE"
        elif pressure >= 25 and rhythm >= 18:
            tactical_state = "EXPLOSIVO"
        elif pressure >= 18 and rhythm >= 14:
            tactical_state = "CALIENTE"
        elif pressure >= 12 and rhythm >= 10:
            tactical_state = "CONTROLADO"
        elif pressure >= 7 and rhythm >= 7:
            tactical_state = "FRIO"
        else:
            tactical_state = "MUERTO"

        if fake_pressure_detected or pressure_without_depth:
            tactical_state = "CONTROLADO" if pressure >= 12 else "FRIO"

        if retention_shape or score_hold_probability >= 70 or retention_risk >= 70:
            tactical_state = "CONTROLADO"

        if cooling_detected or live_decay_factor <= 0.70:
            if not live_reactivation:
                tactical_state = "FRIO"

        if under_transition_score >= 70:
            if not live_reactivation:
                tactical_state = "CONTROLADO"

        if rhythm >= 18:
            tempo_label = "ALTISIMO"
        elif rhythm >= 14:
            tempo_label = "ALTO"
        elif rhythm >= 10:
            tempo_label = "MEDIO"
        elif rhythm >= 7:
            tempo_label = "BAJO"
        else:
            tempo_label = "MUY_BAJO"

        if live_reactivation and rhythm >= 12:
            tempo_label = "ALTO"

        if fake_pressure_detected or pressure_without_depth:
            tempo_label = "FALSO_ALTO" if pressure >= 16 else tempo_label

        if retention_shape or score_hold_probability >= 70:
            tempo_label = "RETENCION"

        tactical_bias = self._calculate_bias(
            tactical_state=tactical_state,
            goal_prob=goal_prob,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            window_bias=window_bias,
            live_reactivation=live_reactivation,
            chaos_mode=chaos_mode,
            red_alert=red_alert,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            score_hold_probability=score_hold_probability,
            retention_risk=retention_risk,
        )

        market_alignment = self._calculate_alignment(
            tactical_state=tactical_state,
            tactical_bias=tactical_bias,
            context_state=context_state,
            live_reactivation=live_reactivation,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            under_transition_score=under_transition_score,
        )

        return {
            "tactical_state": tactical_state,
            "tempo_label": tempo_label,
            "tactical_bias": tactical_bias,
            "market_alignment": market_alignment,
            "tactical_live_reactivation": live_reactivation,
            "tactical_profile": self._profile(
                tactical_state=tactical_state,
                tactical_bias=tactical_bias,
                live_reactivation=live_reactivation,
                fake_pressure_detected=fake_pressure_detected,
                pressure_without_depth=pressure_without_depth,
                retention_shape=retention_shape,
                under_transition_score=under_transition_score,
                cooling_detected=cooling_detected,
            ),
        }

    def _calculate_bias(
        self,
        tactical_state: str,
        goal_prob: float,
        pressure: float,
        rhythm: float,
        context_state: str,
        window_bias: str,
        live_reactivation: bool,
        chaos_mode: bool,
        red_alert: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        cooling_detected: bool,
        under_transition_score: float,
        score_hold_probability: float,
        retention_risk: float,
    ) -> str:
        if retention_shape or score_hold_probability >= 70 or retention_risk >= 70:
            return "UNDER"

        if fake_pressure_detected or pressure_without_depth:
            return "UNDER" if goal_prob <= 58 else "NEUTRAL"

        if under_transition_score >= 70 and not live_reactivation:
            return "UNDER"

        if cooling_detected and not live_reactivation:
            return "UNDER" if context_state in {"CONTROLADO", "FRIO", "MUERTO"} else "NEUTRAL"

        if live_reactivation or chaos_mode or red_alert:
            if goal_prob >= 56 or pressure >= 20 or rhythm >= 12:
                return "OVER"

        if tactical_state in {"EXPLOSIVO", "CALIENTE"} and goal_prob >= 58:
            return "OVER"

        if tactical_state in {"CONTROLADO", "FRIO", "MUERTO"} and goal_prob <= 54:
            return "UNDER"

        if window_bias == "UNDER" and goal_prob <= 58:
            return "UNDER"

        if window_bias == "OVER" and goal_prob >= 58:
            return "OVER"

        return "NEUTRAL"

    def _calculate_alignment(
        self,
        tactical_state: str,
        tactical_bias: str,
        context_state: str,
        live_reactivation: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        under_transition_score: float,
    ) -> str:

        if tactical_bias == "OVER":
            if fake_pressure_detected or pressure_without_depth or retention_shape:
                return "BAJA"

            if live_reactivation:
                return "ALTA"

            if tactical_state in {"EXPLOSIVO", "CALIENTE"} and context_state in {
                "CALIENTE",
                "MUY_CALIENTE",
                "TIBIO",
            }:
                return "ALTA"

            return "MEDIA"

        if tactical_bias == "UNDER":
            if retention_shape or under_transition_score >= 70:
                return "ALTA"

            if tactical_state in {"CONTROLADO", "FRIO", "MUERTO"} and context_state in {
                "FRIO",
                "MUERTO",
                "CONTROLADO",
                "TIBIO",
            }:
                return "ALTA"

            return "MEDIA"

        return "BAJA"

    def _profile(
        self,
        tactical_state: str,
        tactical_bias: str,
        live_reactivation: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        under_transition_score: float,
        cooling_detected: bool,
    ) -> str:
        if live_reactivation:
            return "LIVE_REACTIVATION"

        if fake_pressure_detected or pressure_without_depth:
            return "FAKE_PRESSURE"

        if retention_shape:
            return "RETENTION_SHAPE"

        if under_transition_score >= 70:
            return "UNDER_TRANSITION"

        if cooling_detected:
            return "COOLING"

        if tactical_state in {"EXPLOSIVO", "CALIENTE"} and tactical_bias == "OVER":
            return "OVER_PRESSURE"

        if tactical_bias == "UNDER":
            return "UNDER_CONTROL"

        return "NEUTRAL"

    def _has_live_reactivation(
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

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
