from __future__ import annotations

from typing import Any, Dict, List


class OpportunityContextValidator:
    """
    Validador auxiliar para MatchOpportunityService.

    No crea señales.
    No bloquea por sí solo.
    Solo detecta si una oportunidad tiene contexto peligroso.
    """

    def validate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        market: str,
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        positives: List[str] = []
        penalty = 0.0
        protection = 0.0

        minute = self._safe_int(match.get("minute") or context.get("minute"))
        home_score = self._safe_int(match.get("home_score"))
        away_score = self._safe_int(match.get("away_score"))
        total_goals = home_score + away_score
        goal_diff = abs(home_score - away_score)

        ai_score = self._safe_float(ai.get("ai_score"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))
        risk_score = self._safe_float(ai.get("risk_score"))
        risk_level = str(ai.get("risk_level") or "").upper()

        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        red_alert = bool(context.get("red_alert", False))

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        field_vision_score = self._safe_float(context.get("field_vision_score"))
        is_late_game = bool(
            context.get("is_late_game")
            or context.get("field_vision_is_late_game")
            or minute >= 75
        )
        is_added_time = bool(
            context.get("is_added_time")
            or context.get("field_vision_is_added_time")
            or minute >= 90
        )

        market = str(market or "").upper()

        live_read = self._context_live_read(
            minute=minute,
            market=market,
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
            under_transition_score=under_transition_score,
            field_vision_status=field_vision_status,
            field_vision_score=field_vision_score,
            is_late_game=is_late_game,
            is_added_time=is_added_time,
        )

        penalty += self._safe_float(live_read.get("penalty"))
        protection += self._safe_float(live_read.get("protection"))
        warnings.extend(live_read.get("warnings", []))
        positives.extend(live_read.get("positives", []))

        if data_quality == "LOW":
            penalty += 8
            warnings.append("OPP_LOW_DATA")

        if game_quality == "LOW":
            penalty += 5
            warnings.append("OPP_LOW_GAME_QUALITY")

        if risk_level == "ALTO" or risk_score >= 7.4:
            penalty += 10
            warnings.append("OPP_HIGH_RISK")

        if minute < 12:
            penalty += 8
            warnings.append("OPP_TOO_EARLY")

        if "OVER" in market:
            if minute >= 78:
                if late_reactivation or chaos_mode or red_alert or field_vision_status in {
                    "REACTIVATION",
                    "CHAOS",
                    "OVER_PRESSURE",
                }:
                    protection += 8
                    positives.append("OPP_OVER_LATE_PROTECTED_BY_LIVE_CONTEXT")
                elif pressure >= 24 and rhythm >= 14 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
                    protection += 5
                    positives.append("OPP_OVER_LATE_SUPPORTED_BY_PRESSURE")
                else:
                    penalty += 14
                    warnings.append("OPP_OVER_TOO_LATE_WITHOUT_CONFIRMATION")

            if goal_diff >= 3 and minute >= 60:
                penalty += 18
                warnings.append("OPP_OVER_MATCH_RESOLVED")

            if total_goals >= 4 and minute >= 65:
                penalty += 14
                warnings.append("OPP_OVER_SCORE_OVEREXTENDED")

            if context_state in {"MUERTO", "FRIO"}:
                if late_reactivation or chaos_mode or red_alert:
                    protection += 5
                    positives.append("OPP_OVER_COLD_CONTEXT_REACTIVATED")
                else:
                    penalty += 12
                    warnings.append("OPP_OVER_COLD_CONTEXT")

            if context_state == "CONTROLADO" and minute >= 65:
                if late_reactivation or chaos_mode:
                    protection += 4
                    positives.append("OPP_OVER_CONTROLLED_BUT_REACTIVATED")
                else:
                    penalty += 10
                    warnings.append("OPP_OVER_CONTROLLED_CONTEXT")

            if cooling_detected:
                if late_reactivation or chaos_mode:
                    protection += 4
                    positives.append("OPP_OVER_COOLING_CANCELLED_BY_REACTIVATION")
                else:
                    penalty += 14
                    warnings.append("OPP_OVER_COOLING_DETECTED")

            if under_transition_score >= 70:
                if late_reactivation or chaos_mode or red_alert:
                    penalty += 6
                    warnings.append("OPP_OVER_UNDER_TRANSITION_BUT_LIVE_DANGER")
                else:
                    penalty += 18
                    warnings.append("OPP_OVER_UNDER_TRANSITION_ACTIVE")
            elif under_transition_score >= 55:
                penalty += 10
                warnings.append("OPP_OVER_UNDER_TRANSITION_WARNING")

            if over_probability >= 62 and pressure < 9 and rhythm < 6:
                penalty += 10
                warnings.append("OPP_OVER_PROB_WITHOUT_PRESSURE")

            if fake_pressure_detected:
                penalty += 12
                warnings.append("OPP_OVER_FAKE_PRESSURE")

            if pressure_without_depth:
                penalty += 9
                warnings.append("OPP_OVER_PRESSURE_WITHOUT_DEPTH")

            if retention_shape:
                penalty += 12
                warnings.append("OPP_OVER_RETENTION_SHAPE")

            if is_added_time and not (late_reactivation or chaos_mode or red_alert):
                penalty += 6
                warnings.append("OPP_OVER_ADDED_TIME_WITHOUT_DANGER")

        if "UNDER" in market:
            if minute < 55:
                penalty += 10
                warnings.append("OPP_UNDER_TOO_EARLY")

            if context_state in {"CALIENTE", "MUY_CALIENTE"}:
                if retention_shape or cooling_detected or under_transition_score >= 70:
                    penalty += 5
                    warnings.append("OPP_UNDER_HOT_CONTEXT_BUT_RETENTION_SIGNALS")
                else:
                    penalty += 16
                    warnings.append("OPP_UNDER_HOT_CONTEXT")

            if goal_probability >= 60:
                if retention_shape or fake_pressure_detected or pressure_without_depth:
                    penalty += 5
                    warnings.append("OPP_UNDER_GOAL_PROB_HIGH_BUT_WEAK_DEPTH")
                else:
                    penalty += 12
                    warnings.append("OPP_UNDER_GOAL_PROB_HIGH")

            if pressure >= 24 or rhythm >= 16:
                if fake_pressure_detected or pressure_without_depth:
                    penalty += 4
                    positives.append("OPP_UNDER_ACTIVITY_APPEARS_LOW_DEPTH")
                else:
                    penalty += 10
                    warnings.append("OPP_UNDER_TOO_MUCH_ACTIVITY")

            if under_transition_score >= 70 and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
                protection += 8
                positives.append("OPP_UNDER_TRANSITION_CONFIRMED")

            if cooling_detected and minute >= 60:
                protection += 5
                positives.append("OPP_UNDER_COOLING_CONFIRMED")

            if retention_shape:
                protection += 8
                positives.append("OPP_UNDER_RETENTION_SHAPE_CONFIRMED")

            if fake_pressure_detected or pressure_without_depth:
                protection += 5
                positives.append("OPP_UNDER_SUPPORTED_BY_FAKE_PRESSURE")

            if is_added_time and under_probability >= 64 and not chaos_mode and not late_reactivation:
                protection += 4
                positives.append("OPP_UNDER_ADDED_TIME_RETENTION")

        effective_penalty = max(0.0, penalty - protection)
        score = max(0.0, min(100.0, 100.0 - effective_penalty))

        if score >= 80:
            status = "CLEAR"
        elif score >= 60:
            status = "CAUTION"
        elif score >= 40:
            status = "WARNING"
        else:
            status = "DANGER"

        return {
            "opportunity_context_status": status,
            "opportunity_context_score": round(score, 2),
            "opportunity_context_penalty": round(effective_penalty, 2),
            "opportunity_context_raw_penalty": round(penalty, 2),
            "opportunity_context_protection": round(protection, 2),
            "opportunity_context_warnings": warnings,
            "opportunity_context_positive_factors": positives,
            "opportunity_context_live_status": live_read.get("status"),
            "opportunity_context_live_advice": live_read.get("advice"),
            "suggested_alternative_market": live_read.get("suggested_alternative_market"),
        }

    def _context_live_read(
        self,
        minute: int,
        market: str,
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
        under_transition_score: float,
        field_vision_status: str,
        field_vision_score: float,
        is_late_game: bool,
        is_added_time: bool,
    ) -> Dict[str, Any]:
        status = "NORMAL"
        advice = "Contexto de oportunidad estable."
        suggested = None
        penalty = 0.0
        protection = 0.0
        warnings: List[str] = []
        positives: List[str] = []

        if chaos_mode or field_vision_status == "CHAOS" or red_alert:
            status = "CHAOS_LIVE_CONTEXT"
            advice = "Partido volátil; vigilar gol tardío o próximo gol."
            positives.append("CTX_CHAOS_LIVE")
            protection += 6.0
            suggested = "NEXT_GOAL_OR_OVER_WATCH"

        elif late_reactivation or field_vision_status == "REACTIVATION":
            status = "REACTIVATION_LIVE_CONTEXT"
            advice = "Reactivación ofensiva; no bloquear por minuto avanzado sin revisar presión real."
            positives.append("CTX_REACTIVATION_LIVE")
            protection += 5.0
            suggested = "OVER_WATCH_OR_NEXT_GOAL"

        elif retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            status = "RETENTION_LIVE_CONTEXT"
            advice = "Marcador con forma de retención; considerar UNDER o marcador se mantiene."
            warnings.append("CTX_RETENTION_LIVE")
            protection += 4.0
            suggested = "UNDER_OR_SCORE_HOLD"

        elif fake_pressure_detected or field_vision_status == "FAKE_PRESSURE":
            status = "FAKE_PRESSURE_CONTEXT"
            advice = "Presión aparente sin claridad; evitar OVER fuerte, mirar retención."
            warnings.append("CTX_FAKE_PRESSURE")
            penalty += 5.0
            suggested = "UNDER_WATCH"

        elif pressure_without_depth or field_vision_status == "PRESSURE_WITHOUT_DEPTH":
            status = "NO_DEPTH_CONTEXT"
            advice = "Hay actividad, pero poca profundidad; no confiar en OVER sin confirmación."
            warnings.append("CTX_PRESSURE_WITHOUT_DEPTH")
            penalty += 4.0
            suggested = "UNDER_WATCH"

        if is_late_game and minute >= 80:
            if status in {"CHAOS_LIVE_CONTEXT", "REACTIVATION_LIVE_CONTEXT"}:
                protection += 3.0
                positives.append("CTX_LATE_GAME_ACTIVE")
            elif pressure < 18 and rhythm < 13:
                penalty += 6.0
                warnings.append("CTX_LATE_GAME_LOW_ACTIVITY")
                suggested = suggested or "SCORE_HOLD"

        if is_added_time:
            if status in {"CHAOS_LIVE_CONTEXT", "REACTIVATION_LIVE_CONTEXT"}:
                protection += 2.0
                positives.append("CTX_ADDED_TIME_DANGER")
            else:
                penalty += 4.0
                warnings.append("CTX_ADDED_TIME_CAUTION")
                suggested = suggested or "SCORE_HOLD"

        if cooling_detected and status not in {"CHAOS_LIVE_CONTEXT", "REACTIVATION_LIVE_CONTEXT"}:
            penalty += 4.0
            warnings.append("CTX_COOLING_DETECTED")
            suggested = suggested or "UNDER_OR_SCORE_HOLD"

        if under_transition_score >= 70:
            protection += 4.0 if "UNDER" in market else 0.0
            if "OVER" in market:
                penalty += 6.0
                warnings.append("CTX_UNDER_TRANSITION_AGAINST_OVER")
            suggested = suggested or "UNDER_OR_SCORE_HOLD"

        if field_vision_score >= 75 and context_state in {"CALIENTE", "MUY_CALIENTE"}:
            protection += 3.0
            positives.append("CTX_FIELD_VISION_STRONG")

        if 0 < field_vision_score <= 35:
            penalty += 3.0
            warnings.append("CTX_FIELD_VISION_WEAK")

        return {
            "status": status,
            "advice": advice,
            "penalty": penalty,
            "protection": protection,
            "warnings": warnings,
            "positives": positives,
            "suggested_alternative_market": suggested,
        }

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
