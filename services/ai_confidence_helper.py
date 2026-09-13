from __future__ import annotations

from typing import Any, Dict, List


class AIConfidenceHelper:
    """
    Ayudante para ajustar confianza de la IA.

    No crea señales.
    No bloquea.
    Solo corrige probabilidades cuando el contexto no justifica tanta confianza.
    """

    def adjust(self, ai: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        ai = dict(ai or {})
        context = context or {}

        warnings: List[str] = []
        positives: List[str] = []
        penalty = 0.0
        protection = 0.0

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        minute = self._safe_int(context.get("minute"))

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        red_alert = bool(context.get("red_alert", False))
        cooling_detected = bool(context.get("cooling_detected", False))

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        field_vision_score = self._safe_float(context.get("field_vision_score"))
        is_late_game = bool(context.get("is_late_game") or context.get("field_vision_is_late_game") or minute >= 75)
        is_added_time = bool(context.get("is_added_time") or context.get("field_vision_is_added_time") or minute >= 90)

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        field_read = self._field_confidence_read(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            red_alert=red_alert,
            cooling_detected=cooling_detected,
            field_vision_status=field_vision_status,
            field_vision_score=field_vision_score,
            is_late_game=is_late_game,
            is_added_time=is_added_time,
        )

        field_status = field_read["status"]
        field_advice = field_read["advice"]
        protection += self._safe_float(field_read.get("protection"))
        penalty += self._safe_float(field_read.get("penalty"))

        if field_read.get("warning"):
            warnings.append(str(field_read.get("warning")))

        if field_read.get("positive"):
            positives.append(str(field_read.get("positive")))

        if data_quality == "LOW":
            penalty += 8.0
            warnings.append("AI_LOW_DATA_PENALTY")

        if game_quality == "LOW":
            penalty += 5.0
            warnings.append("AI_LOW_GAME_QUALITY")

        if context_state in {"MUERTO", "FRIO"} and goal_probability >= 55:
            if not late_reactivation and not chaos_mode and not red_alert:
                penalty += 8.0
                warnings.append("AI_GOAL_PROB_OVER_CONTEXT")
            else:
                protection += 4.0
                positives.append("AI_COLD_CONTEXT_WITH_REACTIVATION")

        if pressure < 8 and rhythm < 6 and over_probability >= 60:
            penalty += 9.0
            warnings.append("AI_OVER_WITHOUT_PRESSURE")

        if minute < 12:
            penalty += 5.0
            warnings.append("AI_TOO_EARLY_READING")

        # Antes se castigaba automáticamente desde el 78.
        # Ahora solo castiga si no hay reactivación, caos ni presión viva.
        if minute >= 78 and over_probability >= 65:
            if late_reactivation or chaos_mode or red_alert or field_vision_status in {"REACTIVATION", "CHAOS", "OVER_PRESSURE"}:
                protection += 5.0
                positives.append("AI_LATE_OVER_PROTECTED_BY_LIVE_PRESSURE")
            elif pressure >= 22 and rhythm >= 14 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
                protection += 3.0
                positives.append("AI_LATE_OVER_SUPPORTED_BY_CONTEXT")
            else:
                penalty += 6.0
                warnings.append("AI_LATE_OVER_CAUTION")

        if fake_pressure_detected:
            penalty += 8.0
            warnings.append("AI_FAKE_PRESSURE_DETECTED")

        if pressure_without_depth:
            penalty += 6.0
            warnings.append("AI_PRESSURE_WITHOUT_DEPTH")

        if retention_shape:
            penalty += 6.0
            warnings.append("AI_RETENTION_SHAPE_DETECTED")

        if cooling_detected and not late_reactivation and not chaos_mode:
            penalty += 5.0
            warnings.append("AI_COOLING_DETECTED")

        if is_added_time:
            if late_reactivation or chaos_mode or red_alert:
                protection += 3.0
                positives.append("AI_ADDED_TIME_DANGER_PROTECTED")
            else:
                penalty += 4.0
                warnings.append("AI_ADDED_TIME_WITHOUT_PRESSURE")

        effective_penalty = max(0.0, penalty - protection)
        confidence_score = max(0.0, min(100.0, 100.0 - effective_penalty))

        ai["ai_score"] = round(max(0.0, ai_score - effective_penalty), 2)
        ai["goal_probability"] = round(max(0.0, goal_probability - effective_penalty), 2)
        ai["over_probability"] = round(max(0.0, over_probability - effective_penalty), 2)
        ai["under_probability"] = round(
            min(95.0, max(0.0, under_probability + (effective_penalty * 0.45))),
            2,
        )

        if field_status in {"REACTIVATION_CONFIRMED", "CHAOS_CONFIRMED"}:
            ai["goal_probability"] = round(min(96.0, ai["goal_probability"] + 3.0), 2)
            ai["over_probability"] = round(min(95.0, ai["over_probability"] + 3.0), 2)
            ai["under_probability"] = round(max(0.0, ai["under_probability"] - 2.0), 2)

        if field_status in {"RETENTION_CONFIRMED", "FAKE_PRESSURE_CONFIRMED"}:
            ai["under_probability"] = round(min(95.0, ai["under_probability"] + 3.0), 2)

        ai["confidence_helper_status"] = self._status(confidence_score)
        ai["confidence_helper_score"] = round(confidence_score, 2)
        ai["confidence_helper_penalty"] = round(effective_penalty, 2)
        ai["confidence_helper_raw_penalty"] = round(penalty, 2)
        ai["confidence_helper_protection"] = round(protection, 2)
        ai["confidence_helper_warnings"] = warnings
        ai["confidence_helper_positive_factors"] = positives
        ai["confidence_field_status"] = field_status
        ai["confidence_field_advice"] = field_advice

        return ai

    def _field_confidence_read(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        context_state: str,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        red_alert: bool,
        cooling_detected: bool,
        field_vision_status: str,
        field_vision_score: float,
        is_late_game: bool,
        is_added_time: bool,
    ) -> Dict[str, Any]:
        status = "NORMAL"
        advice = "Confianza IA estable según contexto."
        penalty = 0.0
        protection = 0.0
        warning = ""
        positive = ""

        if chaos_mode or field_vision_status == "CHAOS":
            status = "CHAOS_CONFIRMED"
            advice = "Partido volátil; no reducir agresivamente la probabilidad de gol."
            protection += 6.0
            positive = "FIELD_CHAOS_CONFIRMED"

        elif late_reactivation or field_vision_status == "REACTIVATION":
            status = "REACTIVATION_CONFIRMED"
            advice = "Reactivación detectada; proteger lectura ofensiva en tramo final."
            protection += 5.0
            positive = "FIELD_REACTIVATION_CONFIRMED"

        elif fake_pressure_detected or field_vision_status == "FAKE_PRESSURE":
            status = "FAKE_PRESSURE_CONFIRMED"
            advice = "Presión aparente sin precisión; reducir confianza en OVER."
            penalty += 6.0
            warning = "FIELD_FAKE_PRESSURE_CONFIRMED"

        elif pressure_without_depth or field_vision_status == "PRESSURE_WITHOUT_DEPTH":
            status = "NO_DEPTH_CONFIRMED"
            advice = "Hay acercamientos, pero sin profundidad suficiente."
            penalty += 4.0
            warning = "FIELD_PRESSURE_WITHOUT_DEPTH"

        elif retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            status = "RETENTION_CONFIRMED"
            advice = "Lectura de retención; subir prudencia para señales OVER."
            penalty += 5.0
            warning = "FIELD_RETENTION_CONFIRMED"

        if is_late_game and minute >= 80:
            if status in {"CHAOS_CONFIRMED", "REACTIVATION_CONFIRMED"}:
                protection += 2.0
            elif pressure < 18 and rhythm < 13:
                penalty += 4.0
                warning = warning or "FIELD_LATE_LOW_ACTIVITY"

        if is_added_time:
            if status in {"CHAOS_CONFIRMED", "REACTIVATION_CONFIRMED"} or red_alert:
                protection += 2.0
            else:
                penalty += 3.0
                warning = warning or "FIELD_ADDED_TIME_LOW_ACTIVITY"

        if cooling_detected and status not in {"CHAOS_CONFIRMED", "REACTIVATION_CONFIRMED"}:
            penalty += 3.0
            warning = warning or "FIELD_COOLING_CONFIRMED"

        if field_vision_score >= 75 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
            protection += 2.0
            positive = positive or "FIELD_VISION_STRONG"

        if 0 < field_vision_score <= 35:
            penalty += 2.0
            warning = warning or "FIELD_VISION_WEAK"

        return {
            "status": status,
            "advice": advice,
            "penalty": penalty,
            "protection": protection,
            "warning": warning,
            "positive": positive,
        }

    def _status(self, score: float) -> str:
        if score >= 85:
            return "CLEAR"
        if score >= 70:
            return "STABLE"
        if score >= 50:
            return "CAUTION"
        return "LOW_CONFIDENCE"

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
