from __future__ import annotations

from typing import Any, Dict

from app.services.ai_confidence_helper import AIConfidenceHelper


class AIMatchEngine:
    """
    Convierte contexto + datos del partido en lectura IA operativa.
    """

    def __init__(self) -> None:
        self._confidence_helper = AIConfidenceHelper()

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))

        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        dominance = str(context.get("dominance") or "BALANCED").upper()
        attack_side = str(context.get("attack_side") or "BALANCED").upper()
        red_alert = bool(context.get("red_alert", False))
        minute = self._safe_int(context.get("minute"))

        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))

        home_pressure = self._safe_float(context.get("home_pressure"))
        away_pressure = self._safe_float(context.get("away_pressure"))

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        field_vision_score = self._safe_float(context.get("field_vision_score"))
        is_late_game = bool(context.get("is_late_game") or context.get("field_vision_is_late_game") or minute >= 75)
        is_added_time = bool(context.get("is_added_time") or context.get("field_vision_is_added_time") or minute >= 90)

        is_dead_empty = (
            pressure <= 0
            and rhythm <= 0
            and goal_window <= 0
            and over_window <= 0
            and home_pressure <= 0
            and away_pressure <= 0
            and data_quality == "LOW"
            and game_quality == "LOW"
        )

        if is_dead_empty:
            result = {
                "ai_score": 0.0,
                "goal_probability": 0.0,
                "over_probability": 0.0,
                "under_probability": 95.0,
                "risk_score": 9.0,
                "risk_level": "ALTO",
                "momentum_label": "ESTABLE",
                "result_prediction": "NO_EDGE",
                "winner_prediction": "DRAW_LEAN",
                "ai_live_adjustment": "DEAD_EMPTY_CONTEXT",
                "ai_live_advice": "Sin datos útiles para lectura IA.",
            }
            return self._confidence_helper.adjust(result, context)

        base_activity = (
            (pressure * 0.37)
            + (rhythm * 0.27)
            + (goal_window * 0.19)
            + (over_window * 0.17)
        )

        quality_bonus = {
            "LOW": -2.0,
            "MEDIUM": 6.0,
            "HIGH": 11.0,
        }.get(data_quality, 0.0)

        game_bonus = {
            "LOW": -2.0,
            "MEDIUM": 5.0,
            "HIGH": 9.0,
        }.get(game_quality, 0.0)

        state_bonus = {
            "MUERTO": -12.0,
            "FRIO": -5.0,
            "CONTROLADO": 1.0,
            "TIBIO": 8.0,
            "CALIENTE": 17.0,
            "MUY_CALIENTE": 25.0,
        }.get(context_state, 0.0)

        minute_bonus = self._minute_bonus(minute)

        side_bonus = 0.0
        if dominance in {"HOME", "AWAY"}:
            side_bonus += 2.5
        if attack_side in {"HOME", "AWAY"}:
            side_bonus += 1.5

        max_side_pressure = max(home_pressure, away_pressure)

        pressure_side_bonus = 0.0
        if max_side_pressure >= 10:
            pressure_side_bonus += 1.5
        if max_side_pressure >= 16:
            pressure_side_bonus += 2.0
        if max_side_pressure >= 22:
            pressure_side_bonus += 2.0

        red_bonus = 6.0 if red_alert else 0.0

        ai_score = (
            base_activity
            + quality_bonus
            + game_bonus
            + state_bonus
            + minute_bonus
            + side_bonus
            + pressure_side_bonus
            + red_bonus
        )

        if data_quality in {"MEDIUM", "HIGH"} and (pressure >= 8 or rhythm >= 8):
            ai_score = max(ai_score, 42.0)

        if data_quality == "HIGH" and game_quality in {"MEDIUM", "HIGH"} and (pressure >= 12 or rhythm >= 10):
            ai_score = max(ai_score, 50.0)

        if context_state in {"CALIENTE", "MUY_CALIENTE"} and pressure >= 16:
            ai_score = max(ai_score, 60.0)

        if context_state == "MUY_CALIENTE" and pressure >= 25 and rhythm >= 13:
            ai_score = max(ai_score, 70.0)

        if data_quality == "LOW" and context_state not in {"CALIENTE", "MUY_CALIENTE"}:
            ai_score = min(ai_score, 58.0)

        ai_score = self._clamp(ai_score, 0.0, 96.0)

        goal_probability = (
            12.0
            + (pressure * 1.12)
            + (rhythm * 0.78)
            + (goal_window * 0.44)
            + (over_window * 0.28)
        )

        goal_probability += {
            "LOW": -7.0,
            "MEDIUM": 2.0,
            "HIGH": 6.0,
        }.get(data_quality, 0.0)

        goal_probability += {
            "LOW": -5.0,
            "MEDIUM": 2.0,
            "HIGH": 5.0,
        }.get(game_quality, 0.0)

        goal_probability += {
            "MUERTO": -12.0,
            "FRIO": -6.0,
            "CONTROLADO": 0.0,
            "TIBIO": 5.0,
            "CALIENTE": 12.0,
            "MUY_CALIENTE": 17.0,
        }.get(context_state, 0.0)

        if red_alert:
            goal_probability += 7.0

        if max_side_pressure >= 16:
            goal_probability += 3.0

        if max_side_pressure >= 22 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
            goal_probability += 2.0

        goal_probability += self._goal_minute_adjustment(minute)

        if data_quality in {"MEDIUM", "HIGH"} and (pressure >= 10 or rhythm >= 10):
            goal_probability = max(goal_probability, 40.0)

        if context_state in {"CALIENTE", "MUY_CALIENTE"} and pressure >= 16:
            goal_probability = max(goal_probability, 60.0)

        if context_state == "MUY_CALIENTE" and pressure >= 25 and rhythm >= 13:
            goal_probability = max(goal_probability, 72.0)

        if data_quality == "LOW" and context_state not in {"CALIENTE", "MUY_CALIENTE"}:
            goal_probability = min(goal_probability, 58.0)

        goal_probability = self._clamp(goal_probability, 0.0, 96.0)

        over_probability = (
            (ai_score * 0.53)
            + (goal_probability * 0.47)
        )

        over_probability += {
            "LOW": -7.0,
            "MEDIUM": 1.0,
            "HIGH": 6.0,
        }.get(data_quality, 0.0)

        over_probability += {
            "LOW": -5.0,
            "MEDIUM": 1.0,
            "HIGH": 5.0,
        }.get(game_quality, 0.0)

        over_probability += {
            "MUERTO": -15.0,
            "FRIO": -9.0,
            "CONTROLADO": -2.0,
            "TIBIO": 5.0,
            "CALIENTE": 12.0,
            "MUY_CALIENTE": 18.0,
        }.get(context_state, 0.0)

        if red_alert:
            over_probability += 5.0

        if pressure >= 16 and rhythm >= 10:
            over_probability += 3.0

        if pressure >= 22 and rhythm >= 14:
            over_probability += 4.0

        if max_side_pressure >= 18:
            over_probability += 2.0

        if minute >= 25:
            over_probability += 2.0
        if minute >= 60:
            over_probability += 2.0

        if context_state == "TIBIO" and data_quality in {"MEDIUM", "HIGH"} and pressure >= 12:
            over_probability = max(over_probability, 52.0)

        if context_state == "CALIENTE" and pressure >= 16:
            over_probability = max(over_probability, 64.0)

        if context_state == "MUY_CALIENTE" and pressure >= 24:
            over_probability = max(over_probability, 74.0)

        if data_quality == "LOW" and context_state not in {"CALIENTE", "MUY_CALIENTE"}:
            over_probability = min(over_probability, 58.0)

        over_probability = self._clamp(over_probability, 0.0, 95.0)

        under_probability = 100.0 - over_probability

        if context_state in {"MUERTO", "FRIO"}:
            under_probability += 4.0

        if context_state in {"CALIENTE", "MUY_CALIENTE"}:
            under_probability -= 5.0

        if minute >= 65 and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
            under_probability += 6.0

        if minute < 55 and context_state in {"MUERTO", "FRIO"}:
            under_probability += 2.0

        under_probability = self._clamp(under_probability, 0.0, 95.0)

        live_adjusted = self._apply_live_state_correction(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            context_state=context_state,
            pressure=pressure,
            rhythm=rhythm,
            minute=minute,
            live_decay_factor=live_decay_factor,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
        )

        ai_score = live_adjusted["ai_score"]
        goal_probability = live_adjusted["goal_probability"]
        over_probability = live_adjusted["over_probability"]
        under_probability = live_adjusted["under_probability"]

        field_adjusted = self._apply_field_vision_correction(
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            field_vision_status=field_vision_status,
            field_vision_score=field_vision_score,
            is_late_game=is_late_game,
            is_added_time=is_added_time,
        )

        ai_score = field_adjusted["ai_score"]
        goal_probability = field_adjusted["goal_probability"]
        over_probability = field_adjusted["over_probability"]
        under_probability = field_adjusted["under_probability"]
        ai_live_adjustment = field_adjusted["ai_live_adjustment"]
        ai_live_advice = field_adjusted["ai_live_advice"]

        risk_score = self._calculate_risk_score(
            data_quality=data_quality,
            context_state=context_state,
            pressure=pressure,
            rhythm=rhythm,
            minute=minute,
            red_alert=red_alert,
            ai_score=ai_score,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            is_added_time=is_added_time,
        )

        risk_level = self._risk_level_from_score(risk_score)

        momentum_label = self._momentum_label(
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            red_alert=red_alert,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            retention_shape=retention_shape,
        )

        result_prediction = self._result_prediction(
            over_probability=over_probability,
            under_probability=under_probability,
            goal_probability=goal_probability,
            minute=minute,
        )

        winner_prediction = self._winner_prediction(
            dominance=dominance,
            attack_side=attack_side,
            ai_score=ai_score,
            context_state=context_state,
        )

        result = {
            "ai_score": round(ai_score, 2),
            "goal_probability": round(goal_probability, 2),
            "over_probability": round(over_probability, 2),
            "under_probability": round(under_probability, 2),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "momentum_label": momentum_label,
            "result_prediction": result_prediction,
            "winner_prediction": winner_prediction,
            "ai_live_adjustment": ai_live_adjustment,
            "ai_live_advice": ai_live_advice,
        }

        return self._confidence_helper.adjust(result, context)

    def _apply_live_state_correction(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        context_state: str,
        pressure: float,
        rhythm: float,
        minute: int,
        live_decay_factor: float,
        cooling_detected: bool,
        under_transition_score: float,
    ) -> Dict[str, float]:
        if context_state == "MUERTO":
            ai_score = min(ai_score, 38.0)
            goal_probability = min(goal_probability, 34.0)
            over_probability = min(over_probability, 28.0)
            under_probability = max(under_probability, 72.0)

        elif context_state == "FRIO":
            ai_score = min(ai_score, 46.0)
            goal_probability = min(goal_probability, 42.0)
            over_probability = min(over_probability, 36.0)
            under_probability = max(under_probability, 66.0)

        elif context_state == "CONTROLADO":
            ai_score = min(ai_score, 54.0)
            goal_probability = min(goal_probability, 50.0)
            over_probability = min(over_probability, 44.0)
            under_probability = max(under_probability, 58.0)

        if cooling_detected:
            ai_score = min(ai_score, 48.0)
            goal_probability = min(goal_probability, 44.0)
            over_probability = min(over_probability, 38.0)
            under_probability = max(under_probability, 64.0)

        if pressure < 18 and rhythm < 14:
            ai_score = min(ai_score, 42.0)
            goal_probability = min(goal_probability, 38.0)
            over_probability = min(over_probability, 32.0)
            under_probability = max(under_probability, 68.0)

        if pressure < 14 and rhythm < 12:
            ai_score = min(ai_score, 34.0)
            goal_probability = min(goal_probability, 30.0)
            over_probability = min(over_probability, 25.0)
            under_probability = max(under_probability, 75.0)

        if minute >= 70 and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
            ai_score = min(ai_score, 46.0)
            goal_probability = min(goal_probability, 42.0)
            over_probability = min(over_probability, 35.0)
            under_probability = max(under_probability, 68.0)

        if live_decay_factor <= 0.70:
            ai_score = min(ai_score, 50.0)
            goal_probability = min(goal_probability, 46.0)
            over_probability = min(over_probability, 40.0)
            under_probability = max(under_probability, 62.0)

        if under_transition_score >= 70:
            ai_score = min(ai_score, 45.0)
            goal_probability = min(goal_probability, 40.0)
            over_probability = min(over_probability, 34.0)
            under_probability = max(under_probability, 70.0)

        elif under_transition_score >= 55:
            ai_score = min(ai_score, 52.0)
            goal_probability = min(goal_probability, 48.0)
            over_probability = min(over_probability, 42.0)
            under_probability = max(under_probability, 62.0)

        return {
            "ai_score": self._clamp(ai_score, 0.0, 96.0),
            "goal_probability": self._clamp(goal_probability, 0.0, 96.0),
            "over_probability": self._clamp(over_probability, 0.0, 95.0),
            "under_probability": self._clamp(under_probability, 0.0, 95.0),
        }

    def _apply_field_vision_correction(
        self,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        minute: int,
        pressure: float,
        rhythm: float,
        context_state: str,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        field_vision_status: str,
        field_vision_score: float,
        is_late_game: bool,
        is_added_time: bool,
    ) -> Dict[str, Any]:
        adjustment = "NORMAL"
        advice = "Lectura IA estándar."

        if chaos_mode or field_vision_status == "CHAOS":
            ai_score += 7.0
            goal_probability += 9.0
            over_probability += 8.0
            under_probability -= 8.0
            adjustment = "CHAOS_BOOST"
            advice = "Partido volátil: la IA mantiene alerta de gol o ruptura tardía."

        elif late_reactivation or field_vision_status == "REACTIVATION":
            ai_score += 5.0
            goal_probability += 7.0
            over_probability += 6.0
            under_probability -= 6.0
            adjustment = "LATE_REACTIVATION_BOOST"
            advice = "Reactivación detectada: no castigar el tramo final automáticamente."

        if fake_pressure_detected or field_vision_status == "FAKE_PRESSURE":
            ai_score -= 8.0
            goal_probability -= 9.0
            over_probability -= 10.0
            under_probability += 8.0
            adjustment = "FAKE_PRESSURE_PENALTY"
            advice = "Presión falsa detectada: volumen sin precisión suficiente."

        if pressure_without_depth or field_vision_status == "PRESSURE_WITHOUT_DEPTH":
            ai_score -= 5.0
            goal_probability -= 6.0
            over_probability -= 7.0
            under_probability += 5.0
            adjustment = "PRESSURE_WITHOUT_DEPTH"
            advice = "Hay acercamientos, pero falta profundidad real."

        if retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            ai_score -= 4.0
            goal_probability -= 8.0
            over_probability -= 9.0
            under_probability += 10.0
            adjustment = "RETENTION_SHAPE"
            advice = "Perfil de retención: marcador con tendencia a mantenerse."

        if is_late_game and minute >= 80:
            if chaos_mode or late_reactivation:
                goal_probability += 3.0
                over_probability += 3.0
                adjustment = f"{adjustment}_LATE_ACTIVE"
            elif pressure < 18 and rhythm < 13:
                ai_score -= 4.0
                goal_probability -= 5.0
                over_probability -= 6.0
                under_probability += 5.0
                adjustment = "LATE_LOW_ACTIVITY"
                advice = "Minuto avanzado sin suficiente actividad real."

        if is_added_time:
            if chaos_mode or late_reactivation:
                goal_probability += 2.0
                over_probability += 2.0
                adjustment = f"{adjustment}_ADDED_TIME_DANGER"
            else:
                ai_score -= 3.0
                goal_probability -= 4.0
                over_probability -= 5.0
                under_probability += 4.0
                adjustment = "ADDED_TIME_NO_PRESSURE"
                advice = "Tiempo añadido sin presión suficiente."

        if field_vision_score >= 75 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
            ai_score += 3.0
            goal_probability += 3.0
            over_probability += 3.0

        if field_vision_score > 0 and field_vision_score <= 35:
            ai_score -= 3.0
            goal_probability -= 3.0
            over_probability -= 3.0
            under_probability += 3.0

        return {
            "ai_score": self._clamp(ai_score, 0.0, 96.0),
            "goal_probability": self._clamp(goal_probability, 0.0, 96.0),
            "over_probability": self._clamp(over_probability, 0.0, 95.0),
            "under_probability": self._clamp(under_probability, 0.0, 95.0),
            "ai_live_adjustment": adjustment,
            "ai_live_advice": advice,
        }

    def _calculate_risk_score(
        self,
        data_quality: str,
        context_state: str,
        pressure: float,
        rhythm: float,
        minute: int,
        red_alert: bool,
        ai_score: float,
        cooling_detected: bool,
        under_transition_score: float,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        is_added_time: bool,
    ) -> float:
        risk = 3.0

        if data_quality == "LOW":
            risk += 3.4
        elif data_quality == "MEDIUM":
            risk += 1.3
        elif data_quality == "HIGH":
            risk -= 0.4

        if context_state == "MUERTO":
            risk += 2.0
        elif context_state == "FRIO":
            risk += 1.0
        elif context_state == "MUY_CALIENTE":
            risk += 1.2

        if pressure >= 34 and rhythm >= 18:
            risk += 1.0

        if minute >= 80:
            risk += 1.0
        elif minute <= 12:
            risk += 1.0

        if is_added_time:
            risk += 0.5

        if red_alert:
            risk += 0.5

        if cooling_detected:
            risk += 1.0

        if under_transition_score >= 70:
            risk += 0.8
        elif under_transition_score >= 55:
            risk += 0.4

        if fake_pressure_detected:
            risk += 1.0

        if pressure_without_depth:
            risk += 0.7

        if retention_shape:
            risk += 0.5

        if chaos_mode:
            risk += 0.8

        if late_reactivation and data_quality in {"MEDIUM", "HIGH"}:
            risk -= 0.4

        if ai_score >= 78:
            risk -= 1.0
        elif ai_score >= 68:
            risk -= 0.6

        if context_state in {"CALIENTE", "MUY_CALIENTE"} and data_quality in {"MEDIUM", "HIGH"}:
            risk -= 0.3

        return self._clamp(risk, 0.0, 10.0)

    def _risk_level_from_score(self, risk_score: float) -> str:
        if risk_score <= 3.5:
            return "BAJO"
        if risk_score <= 6.5:
            return "MEDIO"
        return "ALTO"

    def _momentum_label(
        self,
        pressure: float,
        rhythm: float,
        context_state: str,
        red_alert: bool,
        cooling_detected: bool,
        under_transition_score: float,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        retention_shape: bool,
    ) -> str:
        if chaos_mode:
            return "CAOS"

        if late_reactivation:
            return "REACTIVACION"

        if fake_pressure_detected:
            return "PRESION_FALSA"

        if retention_shape or under_transition_score >= 70:
            return "UNDER_TRANSITION"

        if cooling_detected:
            return "ENFRIANDO"

        if red_alert:
            return "EXPLOSIVO"

        if context_state == "MUY_CALIENTE" and pressure >= 26:
            return "MUY_ALTO"

        if context_state == "CALIENTE":
            return "ALTO"

        if context_state == "TIBIO":
            return "MEDIO"

        if context_state in {"CONTROLADO", "FRIO"}:
            return "BAJO"

        return "ESTABLE"

    def _result_prediction(
        self,
        over_probability: float,
        under_probability: float,
        goal_probability: float,
        minute: int,
    ) -> str:
        if over_probability >= 72 and goal_probability >= 68:
            return "OVER_LEAN"

        if minute >= 60 and under_probability >= 68:
            return "UNDER_LEAN"

        return "NO_EDGE"

    def _winner_prediction(
        self,
        dominance: str,
        attack_side: str,
        ai_score: float,
        context_state: str,
    ) -> str:
        if ai_score < 56:
            return "DRAW_LEAN"

        if dominance == "HOME" and attack_side == "HOME":
            return "HOME_LEAN"

        if dominance == "AWAY" and attack_side == "AWAY":
            return "AWAY_LEAN"

        if dominance == "HOME":
            return "HOME_LEAN"

        if dominance == "AWAY":
            return "AWAY_LEAN"

        if context_state in {"MUERTO", "FRIO", "CONTROLADO"}:
            return "DRAW_LEAN"

        return "NO_EDGE"

    def _minute_bonus(self, minute: int) -> float:
        if 25 <= minute <= 45:
            return 8.0
        if 60 <= minute <= 75:
            return 10.0
        if 15 <= minute <= 24:
            return 4.0
        if 76 <= minute <= 85:
            return 4.0
        if 86 <= minute <= 97:
            return 0.0
        if minute < 10:
            return -4.0
        if minute > 97:
            return -3.0
        return 0.0

    def _goal_minute_adjustment(self, minute: int) -> float:
        if 25 <= minute <= 45:
            return 6.0
        if 60 <= minute <= 75:
            return 8.0
        if 76 <= minute <= 85:
            return 4.0
        if 86 <= minute <= 97:
            return 0.0
        if minute < 12:
            return -5.0
        return 0.0

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
