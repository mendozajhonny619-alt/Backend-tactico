from __future__ import annotations

from typing import Any, Dict, List


class SignalRevalidatorService:
    """
    Revalida señales activas.

    Objetivo:
    - No bloquea señales.
    - No elimina señales.
    - No cambia mercado ni rank.
    - Solo indica si la señal sigue fuerte, se debilita o se enfría.

    Ajuste:
    - No castiga automáticamente minuto 80+ si hay reactivación real.
    - Distingue presión real, presión falsa, retención y caos.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        signal = signal or {}

        market = str(signal.get("market") or "").upper()

        current_minute = self._safe_int(
            signal.get("current_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        entry_minute = self._safe_int(
            signal.get("entry_minute")
            or signal.get("minute")
            or signal.get("minuto")
        )

        active_minutes = max(0, current_minute - entry_minute)

        signal_score = self._safe_float(signal.get("signal_score"))
        ai_score = self._safe_float(signal.get("ai_score"))
        goal_probability = self._safe_float(signal.get("goal_probability"))
        over_probability = self._safe_float(signal.get("over_probability"))
        under_probability = self._safe_float(signal.get("under_probability"))
        risk_score = self._safe_float(signal.get("risk_score"))

        shots = self._safe_float(signal.get("shots"))
        shots_on_target = self._safe_float(signal.get("shots_on_target"))
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
        cooling_detected = bool(signal.get("cooling_detected", False))
        under_transition_score = self._safe_float(signal.get("under_transition_score"))
        retention_risk = self._safe_float(signal.get("retention_risk"))
        score_hold_probability = self._safe_float(signal.get("score_hold_probability"))
        live_decay_factor = self._safe_float(signal.get("live_decay_factor") or 1.0)
        field_vision_status = str(signal.get("field_vision_status") or "").upper()
        is_added_time = bool(
            signal.get("is_added_time")
            or signal.get("field_vision_is_added_time")
            or current_minute >= 90
        )

        live_reactivation = self._has_live_reactivation(
            minute=current_minute,
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

        score = 50.0
        reasons: List[str] = []
        warnings: List[str] = []

        if signal_score >= 75:
            score += 12
            reasons.append("Signal Score alto")
        elif signal_score >= 65:
            score += 7
            reasons.append("Signal Score aceptable")
        elif signal_score > 0 and signal_score < 55:
            score -= 8
            warnings.append("Signal Score bajo")

        if ai_score >= 70:
            score += 10
            reasons.append("IA favorable")
        elif ai_score >= 60:
            score += 5
            reasons.append("IA operable")
        elif ai_score > 0 and ai_score < 55:
            score -= 8
            warnings.append("IA débil")

        if market == "OVER":
            if goal_probability >= 75:
                score += 10
                reasons.append("Probabilidad de gol alta")
            elif goal_probability >= 65:
                score += 6
                reasons.append("Probabilidad de gol favorable")
            elif goal_probability > 0 and goal_probability < 58:
                score -= 10
                warnings.append("Probabilidad de gol insuficiente")

            if over_probability >= 75:
                score += 9
                reasons.append("OVER muy alineado")
            elif over_probability >= 65:
                score += 5
                reasons.append("OVER alineado")
            elif over_probability > 0 and over_probability < 58:
                score -= 9
                warnings.append("OVER perdiendo fuerza")

        elif market == "UNDER":
            if under_probability >= 72:
                score += 10
                reasons.append("UNDER muy alineado")
            elif under_probability >= 64:
                score += 5
                reasons.append("UNDER alineado")
            elif under_probability > 0 and under_probability < 58:
                score -= 9
                warnings.append("UNDER perdiendo fuerza")

            if goal_probability >= 60 and not (retention_shape or fake_pressure_detected or pressure_without_depth):
                score -= 12
                warnings.append("Amenaza de gol elevada contra UNDER")

        if shots_on_target >= 3:
            score += 8
            reasons.append("Buen volumen de tiros al arco")
        elif market == "OVER" and current_minute >= 65 and shots_on_target <= 1 and not live_reactivation:
            score -= 10
            warnings.append("Pocos tiros al arco para sostener OVER")

        if shots >= 8:
            score += 4
            reasons.append("Volumen de tiros aceptable")

        if corners >= 4:
            score += 4
            reasons.append("Corners favorables")

        if dangerous_attacks >= 25:
            score += 7
            reasons.append("Ataques peligrosos altos")
        elif market == "OVER" and current_minute >= 65 and dangerous_attacks < 12 and not live_reactivation:
            score -= 8
            warnings.append("Ataques peligrosos bajos para OVER")

        if xg >= 1.3:
            score += 8
            reasons.append("xG competitivo")
        elif market == "OVER" and current_minute >= 65 and xg < 0.7 and not live_reactivation:
            score -= 10
            warnings.append("xG bajo para sostener alta probabilidad")

        if live_reactivation:
            score += 12
            reasons.append("Reactivación live confirmada")

        if chaos_mode or red_alert:
            score += 8
            reasons.append("Contexto caótico / alerta roja")

        if fake_pressure_detected:
            score -= 12
            warnings.append("Presión falsa detectada")

        if pressure_without_depth:
            score -= 9
            warnings.append("Presión sin profundidad")

        if retention_shape:
            if market == "UNDER":
                score += 8
                reasons.append("Retención favorece UNDER")
            else:
                score -= 10
                warnings.append("Retención contra OVER")

        if cooling_detected or live_decay_factor <= 0.70:
            if live_reactivation:
                score -= 2
                warnings.append("Enfriamiento previo, pero con reactivación")
            else:
                score -= 10
                warnings.append("Enfriamiento live")

        if under_transition_score >= 70:
            if market == "UNDER":
                score += 8
                reasons.append("Transición UNDER confirmada")
            elif live_reactivation:
                score -= 4
                warnings.append("Transición UNDER, pero hay reactivación")
            else:
                score -= 14
                warnings.append("Transición UNDER contra OVER")

        if retention_risk >= 70 or score_hold_probability >= 70:
            if market == "UNDER":
                score += 6
                reasons.append("Alta retención favorece UNDER")
            elif live_reactivation:
                score -= 4
                warnings.append("Alta retención, pero reactivación presente")
            else:
                score -= 14
                warnings.append("Alta probabilidad de retención")

        if active_minutes <= 8:
            age_label = "FRESCA"
            score += 6
            reasons.append("Señal fresca")
        elif active_minutes <= 15:
            age_label = "VIGENTE"
            score += 1
            reasons.append("Señal todavía vigente")
        elif active_minutes <= 22:
            age_label = "ENFRIANDO"
            if live_reactivation:
                score -= 2
                reasons.append("Señal vieja pero reactivada")
            else:
                score -= 10
                warnings.append("Señal activa por varios minutos sin cumplirse")
        else:
            age_label = "ENFRIADA"
            if live_reactivation:
                score -= 5
                reasons.append("Señal envejecida pero con reactivación")
            else:
                score -= 18
                warnings.append("Señal envejecida sin confirmación")

        if market == "OVER":
            if current_minute >= 85:
                if live_reactivation:
                    score -= 2
                    warnings.append("Minuto muy avanzado, pero con reactivación")
                else:
                    score -= 16
                    warnings.append("Minuto muy avanzado para OVER")
            elif current_minute >= 80:
                if live_reactivation:
                    score += 2
                    reasons.append("Minuto avanzado con presión viva")
                else:
                    score -= 10
                    warnings.append("Minuto avanzado para OVER")
            elif current_minute >= 75:
                if live_reactivation:
                    score += 2
                    reasons.append("Tramo final con reactivación")
                else:
                    score -= 4
                    warnings.append("Tramo final: vigilar timing")

        if is_added_time and not live_reactivation:
            score -= 6
            warnings.append("Tiempo añadido sin presión clara")

        if risk_score >= 7.5:
            score -= 15
            warnings.append("Riesgo alto")
        elif risk_score >= 6.5:
            score -= 8
            warnings.append("Riesgo medio-alto")

        score = round(max(0.0, min(score, 100.0)), 2)

        status = "STRONG"
        advice = "SEÑAL TODAVÍA FUERTE"

        if score < 75:
            status = "WEAKENING"
            advice = "SEÑAL VÁLIDA, PERO PERDIENDO FUERZA"

        if score < 60 or (age_label in {"ENFRIANDO", "ENFRIADA"} and not live_reactivation):
            status = "COOLING"
            advice = "SEÑAL ENFRIADA: NO REENTRAR SIN NUEVA CONFIRMACIÓN"

        if live_reactivation and score >= 55:
            status = "REACTIVATED"
            advice = "SEÑAL REACTIVADA: ESPERAR CONFIRMACIÓN FINAL"

        if fake_pressure_detected or pressure_without_depth:
            status = "WEAK_PRESSURE"
            advice = "PRESIÓN DÉBIL O SIN PROFUNDIDAD: NO REENTRAR AGRESIVO"

        if retention_shape and market == "OVER":
            status = "RETENTION_RISK"
            advice = "RIESGO DE RETENCIÓN CONTRA OVER"

        if score < 45 or (market == "OVER" and current_minute >= 85 and active_minutes >= 12 and not live_reactivation):
            status = "HIGH_RISK"
            advice = "ALTO RIESGO: EVITAR ENTRADA TARDÍA"

        reason = self._build_reason(status, reasons, warnings)

        return {
            "revalidation_status": status,
            "revalidation_score": score,
            "revalidation_reason": reason,
            "revalidation_advice": advice,
            "signal_age_label": age_label,
            "revalidation_warnings": warnings,
            "revalidation_positive_factors": reasons,
            "last_revalidated_minute": current_minute,
            "active_minutes": active_minutes,
            "revalidation_live_reactivation": live_reactivation,
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
        reasons: List[str],
        warnings: List[str],
    ) -> str:
        if status in {"STRONG", "REACTIVATED"}:
            return "Señal fuerte: " + ", ".join(reasons[:4]) if reasons else "Señal todavía fuerte"

        if warnings:
            return "Revalidación: " + ", ".join(warnings[:4])

        return "Revalidación activa"

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
