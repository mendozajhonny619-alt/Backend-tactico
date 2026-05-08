from __future__ import annotations

from typing import Any, Dict, List


class DeepLiveMatchAnalyzer:
    """
    Analizador profundo auxiliar del partido.

    No bloquea.
    No crea señales.
    No modifica probabilidades.
    No reemplaza al ScanService.

    Usa:
    - match
    - context
    - ai
    - timeline

    Para generar:
    - proyección próxima fase
    - estado de vida de la señal
    - lectura de presión reciente
    - riesgo de gol tardío
    - riesgo de retención
    - resumen humano-operativo
    """

    def analyze(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        timeline: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}
        timeline = timeline or {}

        minute = self._safe_int(match.get("minute") or context.get("minute"))
        home_score = self._safe_int(match.get("home_score"))
        away_score = self._safe_int(match.get("away_score"))
        total_goals = home_score + away_score
        score_diff = abs(home_score - away_score)

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        under_transition = self._safe_float(context.get("under_transition_score"))
        live_decay = self._safe_float(context.get("live_decay_factor") or 1.0)

        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))
        ai_score = self._safe_float(ai.get("ai_score"))

        context_state = str(context.get("context_state") or "MUERTO").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()
        dominance = str(context.get("dominance") or "BALANCED").upper()
        attack_side = str(context.get("attack_side") or "BALANCED").upper()

        cooling_detected = bool(context.get("cooling_detected", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        red_alert = bool(context.get("red_alert", False))

        pressure_trend = str(timeline.get("pressure_trend") or "UNKNOWN").upper()
        rhythm_trend = str(timeline.get("rhythm_trend") or "UNKNOWN").upper()
        goal_threat_trend = str(timeline.get("goal_threat_trend") or "UNKNOWN").upper()
        signal_life_status = str(timeline.get("signal_life_status") or "UNKNOWN").upper()
        late_reactivation = bool(timeline.get("late_reactivation", False))
        chaos_mode = bool(timeline.get("chaos_mode", False))

        delta_5 = timeline.get("delta_5m") if isinstance(timeline.get("delta_5m"), dict) else {}
        delta_10 = timeline.get("delta_10m") if isinstance(timeline.get("delta_10m"), dict) else {}

        events = match.get("events") if isinstance(match.get("events"), list) else []
        event_profile = self._event_profile(events=events, minute=minute)

        projection_bias = self._projection_bias(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            under_transition=under_transition,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            context_state=context_state,
            cooling_detected=cooling_detected,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            red_alert=red_alert,
            pressure_trend=pressure_trend,
            rhythm_trend=rhythm_trend,
            goal_threat_trend=goal_threat_trend,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            event_profile=event_profile,
        )

        projection_confidence = self._projection_confidence(
            projection_bias=projection_bias,
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            under_transition=under_transition,
            live_decay=live_decay,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            ai_score=ai_score,
            data_quality=data_quality,
            game_quality=game_quality,
            cooling_detected=cooling_detected,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            red_alert=red_alert,
            pressure_trend=pressure_trend,
            rhythm_trend=rhythm_trend,
            goal_threat_trend=goal_threat_trend,
            signal_life_status=signal_life_status,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            event_profile=event_profile,
        )

        projection_window = self._projection_window(
            minute=minute,
            projection_bias=projection_bias,
            signal_life_status=signal_life_status,
        )

        late_goal_risk = self._late_goal_risk(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            red_alert=red_alert,
            pressure_trend=pressure_trend,
            goal_threat_trend=goal_threat_trend,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            event_profile=event_profile,
        )

        retention_risk = self._retention_risk(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            under_transition=under_transition,
            cooling_detected=cooling_detected,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            context_state=context_state,
            live_decay=live_decay,
        )
        retention_risk_label = self._risk_label(retention_risk)

        tactical_alerts = self._tactical_alerts(
            minute=minute,
            score_diff=score_diff,
            total_goals=total_goals,
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            dominance=dominance,
            attack_side=attack_side,
            cooling_detected=cooling_detected,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            red_alert=red_alert,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            event_profile=event_profile,
            delta_5=delta_5,
            delta_10=delta_10,
        )

        summary = self._summary(
            projection_bias=projection_bias,
            projection_confidence=projection_confidence,
            projection_window=projection_window,
            late_goal_risk=late_goal_risk,
            retention_risk=retention_risk,
            retention_risk_label=retention_risk_label,
            signal_life_status=signal_life_status,
            pressure_trend=pressure_trend,
            rhythm_trend=rhythm_trend,
            goal_threat_trend=goal_threat_trend,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            tactical_alerts=tactical_alerts,
        )

        return {
            "deep_analysis_enabled": True,
            "deep_projection_bias": projection_bias,
            "deep_projection_confidence": round(projection_confidence, 2),
            "deep_projection_window": projection_window,

            "late_goal_risk": late_goal_risk,
            "retention_risk": round(retention_risk, 2),
            "retention_risk_label": retention_risk_label,

            "deep_pressure_trend": pressure_trend,
            "deep_rhythm_trend": rhythm_trend,
            "deep_goal_threat_trend": goal_threat_trend,
            "deep_signal_life_status": signal_life_status,

            "deep_late_reactivation": late_reactivation,
            "deep_chaos_mode": chaos_mode,
            "deep_fake_pressure_detected": fake_pressure_detected,
            "deep_pressure_without_depth": pressure_without_depth,

            "deep_event_profile": event_profile,
            "deep_tactical_alerts": tactical_alerts,
            "deep_analysis_summary": summary,
        }

    def _projection_bias(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        under_transition: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        context_state: str,
        cooling_detected: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        red_alert: bool,
        pressure_trend: str,
        rhythm_trend: str,
        goal_threat_trend: str,
        late_reactivation: bool,
        chaos_mode: bool,
        event_profile: Dict[str, Any],
    ) -> str:
        recent_goal = bool(event_profile.get("recent_goal", False))
        recent_red = bool(event_profile.get("recent_red_card", False))
        recent_subs = self._safe_int(event_profile.get("recent_substitutions"))

        if chaos_mode:
            return "VOLATILE"

        if late_reactivation:
            return "OVER_WATCH"

        if fake_pressure_detected or pressure_without_depth:
            if minute >= 60 and under_transition >= 60:
                return "UNDER"
            return "NEUTRAL"

        if red_alert or recent_red:
            return "OVER"

        if (
            under_transition >= 72
            and cooling_detected
            and pressure <= 18
            and rhythm <= 12
            and context_state in {"CONTROLADO", "FRIO", "MUERTO"}
        ):
            return "UNDER"

        if (
            pressure >= 20
            and rhythm >= 13
            and goal_window >= 20
            and over_window >= 18
            and goal_probability >= 62
            and pressure_trend in {"RISING", "STABLE"}
            and goal_threat_trend in {"RISING", "STABLE"}
            and not cooling_detected
        ):
            return "OVER"

        if (
            minute >= 70
            and pressure <= 16
            and rhythm <= 10
            and under_probability >= 62
            and under_transition >= 60
        ):
            return "UNDER"

        if recent_goal and minute >= 65 and pressure >= 16:
            return "VOLATILE"

        if recent_subs >= 2 and minute >= 60 and pressure_trend == "RISING":
            return "OVER_WATCH"

        return "NEUTRAL"

    def _projection_confidence(
        self,
        projection_bias: str,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        under_transition: float,
        live_decay: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        ai_score: float,
        data_quality: str,
        game_quality: str,
        cooling_detected: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        red_alert: bool,
        pressure_trend: str,
        rhythm_trend: str,
        goal_threat_trend: str,
        signal_life_status: str,
        late_reactivation: bool,
        chaos_mode: bool,
        event_profile: Dict[str, Any],
    ) -> float:
        confidence = 45.0

        if data_quality == "HIGH":
            confidence += 10.0
        elif data_quality == "MEDIUM":
            confidence += 5.0
        else:
            confidence -= 8.0

        if game_quality == "HIGH":
            confidence += 6.0
        elif game_quality == "LOW":
            confidence -= 5.0

        if projection_bias in {"OVER", "OVER_WATCH"}:
            confidence += min(pressure, 35) * 0.35
            confidence += min(rhythm, 25) * 0.25
            confidence += min(goal_window, 35) * 0.25
            confidence += max(0.0, goal_probability - 50.0) * 0.20
            confidence += max(0.0, over_probability - 50.0) * 0.18

            if pressure_trend == "RISING":
                confidence += 6
            if goal_threat_trend == "RISING":
                confidence += 6
            if red_alert:
                confidence += 8
            if late_reactivation:
                confidence += 8
            if chaos_mode:
                confidence += 6
            if cooling_detected and not late_reactivation:
                confidence -= 14
            if live_decay <= 0.70 and not late_reactivation:
                confidence -= 8
            if fake_pressure_detected or pressure_without_depth:
                confidence -= 18

        elif projection_bias == "UNDER":
            confidence += max(0.0, under_probability - 50.0) * 0.35
            confidence += min(under_transition, 100) * 0.25
            confidence += max(0.0, 20.0 - min(pressure, 20.0)) * 0.45
            confidence += max(0.0, 15.0 - min(rhythm, 15.0)) * 0.35

            if cooling_detected:
                confidence += 8
            if fake_pressure_detected or pressure_without_depth:
                confidence += 8
            if pressure_trend == "FALLING":
                confidence += 6
            if rhythm_trend == "FALLING":
                confidence += 6
            if late_reactivation or chaos_mode:
                confidence -= 14
            if red_alert:
                confidence -= 14

        elif projection_bias == "VOLATILE":
            confidence += 12
            if chaos_mode:
                confidence += 10
            if late_reactivation:
                confidence += 6
            if self._safe_int(event_profile.get("recent_goals_count")) >= 2:
                confidence += 8

        else:
            confidence -= 8
            if fake_pressure_detected or pressure_without_depth:
                confidence += 4

        if signal_life_status == "VALID":
            confidence += 5
        elif signal_life_status == "ACTIVE_DANGER":
            confidence += 8
        elif signal_life_status in {"LATE_REACTIVATION", "CHAOS_ACTIVE"}:
            confidence += 10
        elif signal_life_status in {"WEAKENING", "NO_REENTRY"}:
            confidence -= 10
        elif signal_life_status == "AGING":
            confidence -= 5

        if minute >= 80 and projection_bias in {"OVER", "OVER_WATCH"} and not late_reactivation:
            confidence -= 8

        if minute < 15:
            confidence -= 10

        return max(0.0, min(confidence, 95.0))

    def _projection_window(
        self,
        minute: int,
        projection_bias: str,
        signal_life_status: str,
    ) -> str:
        if projection_bias == "NEUTRAL":
            return "SIN_VENTANA"

        if signal_life_status in {"NO_REENTRY", "WEAKENING"}:
            return "REVALIDAR"

        if minute >= 85:
            return "1-3_MIN"
        if minute >= 75:
            return "2-4_MIN"
        if minute >= 60:
            return "3-6_MIN"
        return "5-8_MIN"

    def _late_goal_risk(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        red_alert: bool,
        pressure_trend: str,
        goal_threat_trend: str,
        late_reactivation: bool,
        chaos_mode: bool,
        event_profile: Dict[str, Any],
    ) -> str:
        if minute < 70:
            return "NORMAL"

        if chaos_mode or late_reactivation:
            return "ALTO"

        if red_alert:
            return "ALTO"

        if (
            pressure >= 22
            and rhythm >= 14
            and goal_window >= 20
            and pressure_trend in {"RISING", "STABLE"}
            and goal_threat_trend in {"RISING", "STABLE"}
        ):
            return "ALTO"

        if bool(event_profile.get("recent_red_card", False)):
            return "ALTO"

        if pressure >= 16 and rhythm >= 10:
            return "MEDIO"

        return "BAJO"

    def _retention_risk(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        under_transition: float,
        cooling_detected: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        context_state: str,
        live_decay: float,
    ) -> float:
        risk = 20.0

        if minute >= 55:
            risk += 10.0
        if minute >= 65:
            risk += 10.0
        if minute >= 75:
            risk += 10.0

        if context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
            risk += 18.0

        if pressure <= 16:
            risk += 14.0
        elif pressure <= 22:
            risk += 8.0

        if rhythm <= 10:
            risk += 14.0
        elif rhythm <= 16:
            risk += 8.0

        if under_transition >= 75:
            risk += 18.0
        elif under_transition >= 60:
            risk += 10.0

        if cooling_detected:
            risk += 10.0

        if fake_pressure_detected or pressure_without_depth:
            risk += 12.0

        if live_decay <= 0.70:
            risk += 10.0

        if minute < 55:
            risk = min(risk, 45.0)

        return max(0.0, min(risk, 100.0))

    def _risk_label(self, risk: float) -> str:
        if risk >= 70:
            return "ALTO"
        if risk >= 45:
            return "MEDIO"
        return "BAJO"

    def _event_profile(self, events: List[Dict[str, Any]], minute: int) -> Dict[str, Any]:
        recent_events = []
        recent_goals = 0
        recent_cards = 0
        recent_red_cards = 0
        recent_substitutions = 0
        recent_var = 0

        for event in events:
            event_time = event.get("time") if isinstance(event.get("time"), dict) else {}
            event_minute = self._safe_int(event_time.get("elapsed"))
            if event_minute <= 0:
                continue

            if minute - event_minute > 10:
                continue

            event_type = str(event.get("type") or "").lower()
            event_detail = str(event.get("detail") or "").lower()

            recent_events.append(event)

            if "goal" in event_type or "goal" in event_detail:
                recent_goals += 1

            if "card" in event_type or "card" in event_detail:
                recent_cards += 1

            if "red" in event_detail:
                recent_red_cards += 1

            if "subst" in event_type or "subst" in event_detail:
                recent_substitutions += 1

            if "var" in event_type or "var" in event_detail:
                recent_var += 1

        return {
            "recent_events_count": len(recent_events),
            "recent_goal": recent_goals > 0,
            "recent_goals_count": recent_goals,
            "recent_cards_count": recent_cards,
            "recent_red_card": recent_red_cards > 0,
            "recent_red_cards_count": recent_red_cards,
            "recent_substitutions": recent_substitutions,
            "recent_var_events": recent_var,
        }

    def _tactical_alerts(
        self,
        minute: int,
        score_diff: int,
        total_goals: int,
        pressure: float,
        rhythm: float,
        context_state: str,
        dominance: str,
        attack_side: str,
        cooling_detected: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        red_alert: bool,
        late_reactivation: bool,
        chaos_mode: bool,
        event_profile: Dict[str, Any],
        delta_5: Dict[str, Any],
        delta_10: Dict[str, Any],
    ) -> List[str]:
        alerts: List[str] = []

        if red_alert:
            alerts.append("RED_ALERT_ACTIVE")

        if late_reactivation:
            alerts.append("LATE_REACTIVATION")

        if chaos_mode:
            alerts.append("CHAOS_MODE_ACTIVE")

        if fake_pressure_detected:
            alerts.append("FAKE_PRESSURE_DETECTED")

        if pressure_without_depth:
            alerts.append("PRESSURE_WITHOUT_DEPTH")

        if bool(event_profile.get("recent_red_card", False)):
            alerts.append("RECENT_RED_CARD_VOLATILITY")

        if self._safe_int(event_profile.get("recent_substitutions")) >= 2:
            alerts.append("RECENT_SUBSTITUTIONS_TACTICAL_SHIFT")

        if minute >= 75 and pressure >= 20 and rhythm >= 12:
            alerts.append("LATE_PRESSURE_STILL_ACTIVE")

        if minute >= 75 and cooling_detected and not late_reactivation:
            alerts.append("LATE_COOLING_DETECTED")

        if score_diff >= 2 and minute >= 65:
            alerts.append("MATCH_MAY_BE_RESOLVED")

        if total_goals >= 4 and minute >= 65:
            alerts.append("SCORE_OVEREXTENDED")

        if dominance in {"HOME", "AWAY"} and attack_side == dominance:
            alerts.append("DOMINANT_SIDE_ALIGNED")

        if self._safe_float(delta_5.get("shots_on_target")) > 0:
            alerts.append("RECENT_SHOT_ON_TARGET")

        if self._safe_float(delta_5.get("corners")) > 0:
            alerts.append("RECENT_CORNER_PRESSURE")

        if self._safe_float(delta_10.get("dangerous_attacks")) >= 8:
            alerts.append("DANGEROUS_ATTACKS_ACCUMULATING")

        if context_state in {"FRIO", "MUERTO"} and pressure < 14 and rhythm < 10:
            alerts.append("LOW_ACTIVITY_CONTEXT")

        return alerts

    def _summary(
        self,
        projection_bias: str,
        projection_confidence: float,
        projection_window: str,
        late_goal_risk: str,
        retention_risk: float,
        retention_risk_label: str,
        signal_life_status: str,
        pressure_trend: str,
        rhythm_trend: str,
        goal_threat_trend: str,
        late_reactivation: bool,
        chaos_mode: bool,
        tactical_alerts: List[str],
    ) -> str:
        if chaos_mode:
            return (
                f"Caos ofensivo detectado ({projection_confidence:.0f}%). "
                f"Ventana estimada: {projection_window}. "
                "El partido está abierto y puede romperse en cualquier momento."
            )

        if late_reactivation:
            return (
                f"Reactivación tardía detectada ({projection_confidence:.0f}%). "
                f"Ventana estimada: {projection_window}. "
                f"Riesgo de gol tardío: {late_goal_risk}."
            )

        if projection_bias == "OVER":
            return (
                f"Proyección OVER activa ({projection_confidence:.0f}%). "
                f"Ventana estimada: {projection_window}. "
                f"Riesgo de gol tardío: {late_goal_risk}. "
                f"Estado señal: {signal_life_status}."
            )

        if projection_bias == "OVER_WATCH":
            return (
                f"Vigilancia OVER ({projection_confidence:.0f}%). "
                f"Hay señales de posible reactivación, pero requiere confirmación. "
                f"Ventana: {projection_window}."
            )

        if projection_bias == "UNDER":
            return (
                f"Proyección UNDER/retención ({projection_confidence:.0f}%). "
                f"Riesgo de retención: {retention_risk_label} ({retention_risk:.0f}%). "
                f"Estado señal: {signal_life_status}."
            )

        if projection_bias == "VOLATILE":
            return (
                f"Partido volátil ({projection_confidence:.0f}%). "
                "Eventos recientes pueden alterar la lectura normal."
            )

        if "FAKE_PRESSURE_DETECTED" in tactical_alerts:
            return "Lectura neutral: presión detectada, pero sin profundidad real."

        if "RECENT_SUBSTITUTIONS_TACTICAL_SHIFT" in tactical_alerts:
            return "Lectura neutral con posible cambio táctico reciente; esperar nueva confirmación."

        if pressure_trend == "FALLING" and rhythm_trend == "FALLING":
            return "Lectura neutral: presión y ritmo vienen cayendo."

        if pressure_trend == "RISING" or goal_threat_trend == "RISING":
            return "Lectura neutral con señales tempranas de activación ofensiva."

        return "Sin proyección fuerte confirmada; mantener observación."

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
