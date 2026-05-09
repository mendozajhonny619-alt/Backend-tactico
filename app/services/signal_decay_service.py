from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict


class SignalDecayService:
    """
    Controla fatiga / vida útil de señales activas.

    No bloquea.
    No cierra señales.
    Solo agrega lectura:
    - signal_trend
    - signal_decay_status
    - signal_decay_advice

    Ajuste:
    - No mata señales tardías si hay reactivación real.
    - Distingue enfriamiento real vs pausa temporal.
    - Protege contra presión falsa, retención y transición UNDER.
    """

    FRESH_MINUTES = 3
    CONFIRM_MINUTES = 7
    WARNING_MINUTES = 12

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(signal or {})

        active_minutes = self._active_minutes(data)
        current_score = self._score(data)
        entry_score = self._safe_float(
            data.get("entry_signal_score")
            or data.get("entry_decision_score")
            or data.get("signal_score")
            or data.get("decision_score")
        )

        minute = self._safe_int(
            data.get("minute")
            or data.get("current_minute")
            or data.get("match_minute")
            or data.get("entry_minute")
        )

        market = str(data.get("market") or "").upper()
        final_decision = str(data.get("final_decision") or "").upper()

        pressure = self._safe_float(data.get("pressure_index"))
        rhythm = self._safe_float(data.get("rhythm_index"))
        goal_window = self._safe_float(data.get("goal_window_score"))
        over_window = self._safe_float(data.get("over_window_score"))
        context_state = str(data.get("context_state") or "").upper()

        cooling_detected = bool(data.get("cooling_detected", False))
        under_transition_score = self._safe_float(data.get("under_transition_score"))
        retention_risk = self._safe_float(data.get("retention_risk"))
        score_hold_probability = self._safe_float(data.get("score_hold_probability"))
        live_decay_factor = self._safe_float(data.get("live_decay_factor") or 1.0)

        late_reactivation = bool(data.get("late_reactivation", False))
        chaos_mode = bool(data.get("chaos_mode", False))
        red_alert = bool(data.get("red_alert", False))
        fake_pressure_detected = bool(data.get("fake_pressure_detected", False))
        pressure_without_depth = bool(data.get("pressure_without_depth", False))
        retention_shape = bool(data.get("retention_shape", False))

        field_vision_status = str(data.get("field_vision_status") or "").upper()
        is_added_time = bool(
            data.get("is_added_time")
            or data.get("field_vision_is_added_time")
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

        trend = "STABLE"
        if current_score >= entry_score + 8:
            trend = "UP"
        elif current_score <= entry_score - 8:
            trend = "DOWN"

        status = "FRESH"
        advice = "Señal fresca. Todavía está dentro de ventana útil."

        if active_minutes <= self.FRESH_MINUTES:
            status = "FRESH"
            advice = "Señal fresca. Ventana ideal de entrada."

        elif active_minutes <= self.CONFIRM_MINUTES:
            status = "CONFIRM"
            advice = "Confirmar que la presión siga viva antes de entrar."

        elif active_minutes <= self.WARNING_MINUTES:
            status = "AGING"
            advice = "Señal envejeciendo. Precaución si no hubo gol ni presión nueva."

        else:
            status = "NO_REENTRY"
            advice = "Señal envejecida sin gol. No reentrar salvo nueva presión fuerte."

        if live_reactivation:
            status = "REACTIVATED"
            advice = "Señal reactivada por presión/caos live. Revalidar antes de descartar."

        elif trend == "DOWN" and active_minutes >= 5:
            status = "COOLING"
            advice = "La señal está bajando respecto a su entrada. Riesgo de enfriamiento."

        if cooling_detected or live_decay_factor <= 0.70:
            if live_reactivation:
                status = "REACTIVATED_AFTER_COOLING"
                advice = "Había enfriamiento, pero apareció reactivación live. Esperar confirmación."
            else:
                status = "COOLING"
                advice = "La señal muestra enfriamiento live. No reentrar sin nueva confirmación fuerte."

        if fake_pressure_detected or pressure_without_depth:
            status = "WEAK_PRESSURE"
            advice = "Presión con poca profundidad. Evitar reentrada agresiva."

        if retention_shape:
            status = "RETENTION"
            advice = "El partido muestra forma de retención. Priorizar protección o UNDER."

        if under_transition_score >= 70:
            if live_reactivation and "OVER" in market:
                status = "REVALIDATE_OVER"
                advice = "Transición UNDER activa, pero hay reactivación. OVER solo con confirmación extrema."
            else:
                status = "NO_REENTRY"
                advice = "Transición UNDER activa. No reentrar en señales OVER sin reactivación real."

        if retention_risk >= 70 or score_hold_probability >= 70:
            if live_reactivation and "OVER" in market:
                status = "REVALIDATE_OVER"
                advice = "Alta retención, pero existe reactivación. No entrar sin nueva confirmación clara."
            else:
                status = "NO_REENTRY"
                advice = "Alta probabilidad de retención del marcador. No reentrar."

        if is_added_time and not live_reactivation:
            status = "ADDED_TIME_CAUTION"
            advice = "Tiempo añadido sin presión clara. Evitar reentrada."

        if final_decision == "WAIT":
            status = "WAIT_CONFIRMATION"
            advice = "La decisión maestra exige esperar confirmación."

        if final_decision == "NO_REENTRY":
            if live_reactivation:
                status = "REVALIDATE_OVER"
                advice = "La decisión maestra marcó no reentrar, pero hay reactivación. Solo observar confirmación."
            else:
                status = "NO_REENTRY"
                advice = "La decisión maestra indica no reentrar."

        if final_decision == "AVOID":
            status = "AVOID"
            advice = "La decisión maestra indica evitar la señal."

        return {
            "active_minutes": active_minutes,
            "signal_trend": trend,
            "signal_decay_status": status,
            "signal_decay_advice": advice,
            "signal_decay_score": max(0.0, min(100.0, current_score)),
            "signal_decay_reactivation": live_reactivation,
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

    def _score(self, item: Dict[str, Any]) -> float:
        return self._safe_float(
            item.get("decision_score")
            or item.get("revalidation_score")
            or item.get("signal_score")
            or item.get("ai_score")
        )

    def _active_minutes(self, item: Dict[str, Any]) -> int:
        activated_at = item.get("activated_at")
        if not activated_at:
            return 0

        try:
            start = datetime.fromisoformat(str(activated_at))
            now = datetime.now()
            return max(0, int((now - start).total_seconds() // 60))
        except Exception:
            return 0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
