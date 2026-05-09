from __future__ import annotations

from typing import Any, Dict, List


class SignalRiskReducer:
    """
    Analiza señales activas y agrega avisos de riesgo.

    IMPORTANTE:
    - No bloquea señales.
    - No elimina señales.
    - No cambia el mercado.
    - Solo agrega lectura preventiva para ayudar a decidir mejor.

    Ajuste:
    - No sobrecastiga minuto 80+ si hay reactivación real.
    - Distingue presión falsa, retención, cooling y caos.
    - Permite lectura de riesgo más inteligente en tramo final.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        market = str(signal.get("market") or "").upper()
        rank = str(signal.get("rank") or "").upper()
        risk_level = str(signal.get("risk_level") or "").upper()

        minute = self._safe_int(
            signal.get("current_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        entry_minute = self._safe_int(
            signal.get("entry_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        active_minutes = max(0, minute - entry_minute)

        signal_score = self._safe_float(signal.get("signal_score"))
        ai_score = self._safe_float(signal.get("ai_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))

        final_decision = str(signal.get("final_decision") or "").upper()
        signal_decay_status = str(signal.get("signal_decay_status") or "").upper()
        revalidation_status = str(signal.get("revalidation_status") or "").upper()

        cooling_detected = bool(signal.get("cooling_detected", False))
        under_transition_score = self._safe_float(signal.get("under_transition_score"))
        score_hold_probability = self._safe_float(signal.get("score_hold_probability"))
        retention_risk = self._safe_float(signal.get("retention_risk"))
        live_decay_factor = self._safe_float(signal.get("live_decay_factor") or 1.0)

        shots_on_target = self._safe_float(signal.get("shots_on_target"))
        shots = self._safe_float(signal.get("shots"))
        corners = self._safe_float(signal.get("corners"))
        dangerous_attacks = self._safe_float(signal.get("dangerous_attacks"))
        xg = self._safe_float(signal.get("xg") or signal.get("xG"))

        pressure = self._safe_float(signal.get("pressure_index"))
        rhythm = self._safe_float(signal.get("rhythm_index"))
        goal_window = self._safe_float(signal.get("goal_window_score"))
        over_window = self._safe_float(signal.get("over_window_score"))
        context_state = str(signal.get("context_state") or "").upper()

        late_reactivation = bool(signal.get("late_reactivation", False))
        chaos_mode = bool(signal.get("chaos_mode", False))
        red_alert = bool(signal.get("red_alert", False))
        fake_pressure_detected = bool(signal.get("fake_pressure_detected", False))
        pressure_without_depth = bool(signal.get("pressure_without_depth", False))
        retention_shape = bool(signal.get("retention_shape", False))
        field_vision_status = str(signal.get("field_vision_status") or "").upper()
        is_added_time = bool(
            signal.get("is_added_time")
            or signal.get("field_vision_is_added_time")
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

        warnings: List[str] = []
        positives: List[str] = []

        # -----------------------------
        # Lecturas positivas
        # -----------------------------
        if rank in {"PREMIUM", "FUERTE", "BUENA"}:
            positives.append("Rango fuerte del sistema")

        if signal_score >= 70:
            positives.append("Signal Score alto")

        if ai_score >= 65:
            positives.append("IA con lectura favorable")

        if goal_probability >= 68:
            positives.append("Probabilidad de gol elevada")

        if market == "OVER" and over_probability >= 68:
            positives.append("Probabilidad OVER favorable")

        if market == "UNDER" and under_probability >= 68:
            positives.append("Probabilidad UNDER favorable")

        if shots_on_target >= 3:
            positives.append("Buen volumen de tiros al arco")

        if dangerous_attacks >= 20:
            positives.append("Ataques peligrosos relevantes")

        if xg >= 1.0:
            positives.append("xG competitivo")

        if live_reactivation:
            positives.append("Reactivación live detectada")

        if chaos_mode or red_alert:
            positives.append("Partido en modo caos / alerta roja")

        # -----------------------------
        # Alertas de riesgo
        # -----------------------------
        if risk_level == "ALTO" or risk_score >= 7.0:
            warnings.append("Riesgo alto detectado")

        if market == "OVER":
            if minute >= 80:
                if live_reactivation:
                    warnings.append("OVER en minuto avanzado, pero con reactivación")
                else:
                    warnings.append("OVER en minuto avanzado")

            if active_minutes >= 15:
                if live_reactivation:
                    warnings.append("Señal antigua, pero reactivada")
                else:
                    warnings.append("La señal lleva varios minutos activa sin cumplirse")

            if active_minutes >= 22:
                if live_reactivation:
                    warnings.append("Señal muy antigua, requiere confirmación extrema")
                else:
                    warnings.append("Señal enfriada por tiempo activo prolongado")

            if shots_on_target <= 1 and minute >= 65 and not live_reactivation:
                warnings.append("Pocos tiros al arco para una señal OVER")

            if xg < 0.7 and minute >= 65 and not live_reactivation:
                warnings.append("xG bajo para sostener alta probabilidad de gol")

            if dangerous_attacks < 12 and minute >= 65 and not live_reactivation:
                warnings.append("Ataques peligrosos bajos para OVER")

            if fake_pressure_detected:
                warnings.append("Presión falsa contra OVER")

            if pressure_without_depth:
                warnings.append("Presión sin profundidad contra OVER")

            if retention_shape:
                warnings.append("Forma de retención contra OVER")

        if market == "UNDER":
            if goal_probability >= 60 and not (
                retention_shape or fake_pressure_detected or pressure_without_depth
            ):
                warnings.append("Amenaza de gol elevada para una señal UNDER")

            if shots_on_target >= 4 and not fake_pressure_detected:
                warnings.append("Demasiados tiros al arco para UNDER")

            if dangerous_attacks >= 28 and not pressure_without_depth:
                warnings.append("Partido con presión alta contra UNDER")

            if retention_shape:
                positives.append("Retención favorece UNDER")

            if fake_pressure_detected or pressure_without_depth:
                positives.append("Presión débil favorece UNDER")

        if cooling_detected or live_decay_factor <= 0.70:
            if live_reactivation:
                warnings.append("Enfriamiento previo, pero con reactivación")
            else:
                warnings.append("Enfriamiento live detectado")

        if under_transition_score >= 70:
            if market == "UNDER":
                positives.append("Transición UNDER activa a favor")
            elif live_reactivation:
                warnings.append("Transición UNDER activa, pero hay reactivación")
            else:
                warnings.append("Transición UNDER activa")

        if score_hold_probability >= 70 or retention_risk >= 70:
            if market == "UNDER":
                positives.append("Alta retención favorece UNDER")
            elif live_reactivation:
                warnings.append("Alta retención, pero con reactivación")
            else:
                warnings.append("Alta retención del marcador")

        if signal_decay_status in {"COOLING", "NO_REENTRY", "AVOID"}:
            if live_reactivation:
                warnings.append("Vida de señal degradada, pero reactivada")
            else:
                warnings.append("Vida de señal degradada")

        if revalidation_status in {"COOLING", "HIGH_RISK", "NO_REENTRY", "AVOID"}:
            if live_reactivation:
                warnings.append("Revalidación débil, pero con reactivación")
            else:
                warnings.append("Revalidación debilitada")

        if is_added_time and not live_reactivation:
            warnings.append("Tiempo añadido sin reactivación clara")

        if final_decision == "WAIT":
            warnings.append("Decisión maestra exige esperar")

        if final_decision == "NO_REENTRY":
            if live_reactivation:
                warnings.append("Decisión maestra indica no reentrar, pero hay reactivación")
            else:
                warnings.append("Decisión maestra indica no reentrar")

        if final_decision == "AVOID":
            warnings.append("Decisión maestra indica evitar")

        # -----------------------------
        # Estado final del avisador
        # -----------------------------
        status = "OK"
        live_advice = "SEÑAL LIMPIA SEGÚN LECTURA ACTUAL"

        if warnings:
            status = "CAUTION"
            live_advice = "SEÑAL VÁLIDA, PERO CON PRECAUCIÓN"

        if len(warnings) >= 3 or risk_score >= 7.5:
            status = "HIGH_CAUTION"
            live_advice = "RIESGO ELEVADO: NO REFORZAR SIN NUEVA CONFIRMACIÓN"

        if live_reactivation and status in {"CAUTION", "HIGH_CAUTION"}:
            status = "REVALIDATE"
            live_advice = "HAY REACTIVACIÓN LIVE: esperar confirmación antes de descartar o reforzar."

        if market == "OVER" and active_minutes >= 22:
            if live_reactivation:
                status = "REVALIDATE"
                live_advice = "SEÑAL ANTIGUA PERO REACTIVADA: solo observar confirmación extrema."
            else:
                status = "COOLING"
                live_advice = "SEÑAL ENFRIADA: OBSERVAR Y EVITAR REENTRADA"

        if market == "OVER" and minute >= 85 and active_minutes >= 15:
            if live_reactivation:
                status = "REVALIDATE"
                live_advice = "MINUTO MUY AVANZADO, PERO HAY REACTIVACIÓN: no entrar sin presión extrema."
            else:
                status = "HIGH_CAUTION"
                live_advice = "MINUTO MUY AVANZADO: SOLO CON PRESIÓN EXTREMA"

        if fake_pressure_detected or pressure_without_depth:
            status = "HIGH_CAUTION"
            live_advice = "PRESIÓN FALSA O SIN PROFUNDIDAD: evitar reentrada agresiva."

        if retention_shape and market == "OVER":
            status = "HIGH_CAUTION"
            live_advice = "RETENCIÓN CONTRA OVER: mejor observar o esperar nueva ruptura."

        if final_decision == "WAIT":
            status = "WAIT_CONFIRMATION"
            live_advice = "ESPERAR CONFIRMACIÓN: no reforzar sin nueva validación."

        if final_decision == "NO_REENTRY":
            if live_reactivation:
                status = "REVALIDATE"
                live_advice = "NO REENTRY previo, pero hay reactivación. Solo observar confirmación fuerte."
            else:
                status = "NO_REENTRY"
                live_advice = "NO REENTRAR: la decisión maestra degradó la señal."

        if final_decision == "AVOID":
            status = "AVOID"
            live_advice = "EVITAR: la decisión maestra bloqueó esta señal."

        if signal_decay_status in {"NO_REENTRY", "AVOID"} and final_decision != "ENTER":
            if live_reactivation:
                status = "REVALIDATE"
                live_advice = "Vida útil degradada, pero existe reactivación live. Solo observar."
            else:
                status = signal_decay_status
                live_advice = "La vida útil de la señal ya no permite reentrada segura."

        reason = self._build_reason(
            status=status,
            positives=positives,
            warnings=warnings,
        )

        return {
            "risk_reducer_status": status,
            "risk_reducer_reason": reason,
            "live_advice": live_advice,
            "risk_warnings": warnings,
            "positive_factors": positives,
            "active_minutes": active_minutes,
            "risk_reducer_live_reactivation": live_reactivation,
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

    def _build_reason(
        self,
        status: str,
        positives: List[str],
        warnings: List[str],
    ) -> str:
        if status in {"OK", "REVALIDATE"}:
            if positives:
                return "Señal con soporte: " + ", ".join(positives[:4])
            return "Señal sin alertas críticas"

        if warnings:
            return "Aviso PRO: " + ", ".join(warnings[:4])

        return "Lectura preventiva activa"

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
