from __future__ import annotations

from typing import Any, Dict


class MatchStateGuard:
    """
    Guardia de estado real del partido.

    Objetivo:
    - Evitar OVER tardíos en partidos muertos/fríos.
    - Detectar retención de marcador.
    - Sugerir UNDER cuando el partido ya no tiene ritmo real.
    - Separar probabilidad de gol vs calidad de entrada.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
        opportunity: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}
        opportunity = opportunity or {}

        minute = self._extract_minute(match, context)
        home_score = self._safe_int(match.get("home_score"))
        away_score = self._safe_int(match.get("away_score"))
        total_goals = home_score + away_score

        market = str(opportunity.get("market") or "").upper()
        rank = str(opportunity.get("rank") or "").upper()

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_window = self._safe_float(context.get("goal_window_score"))
        over_window = self._safe_float(context.get("over_window_score"))
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        context_state = str(context.get("context_state") or "").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()
        game_quality = str(context.get("game_quality") or "LOW").upper()

        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        is_late = minute >= 70
        is_very_late = minute >= 80
        is_dead_context = context_state in {"MUERTO", "FRIO"}
        is_low_rhythm = rhythm <= 7
        is_low_pressure = pressure <= 10
        is_weak_window = goal_window <= 12 and over_window <= 12
        is_under_transition = under_transition_score >= 70
        is_live_cooling = cooling_detected or live_decay_factor <= 0.70
        is_score_retention = (
            minute >= 60
            and total_goals <= 2
            and is_low_rhythm
            and pressure <= 14
            and context_state in {"MUERTO", "FRIO", "CONTROLADO", "TIBIO"}
        )

        hold_probability = self._calculate_hold_probability(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_window=goal_window,
            over_window=over_window,
            context_state=context_state,
            data_quality=data_quality,
            total_goals=total_goals,
        )

        status = "LIVE"
        reason = "MATCH_STATE_LIVE"
        suggested_market = None
        force_action = None
        downgraded_rank = None
        entry_quality = "VALID"

        # =========================
        # RETENCIÓN / PARTIDO MUERTO
        # =========================
        if is_score_retention or hold_probability >= 78:
            status = "SCORE_RETENTION"
            reason = "MATCH_STATE_SCORE_RETENTION"
            suggested_market = "UNDER"
            entry_quality = "UNDER_LEAN"

        if (
            minute >= 65
            and is_dead_context
            and is_low_rhythm
            and is_low_pressure
        ):
            status = "DEAD_MATCH"
            reason = "MATCH_STATE_DEAD_LOW_ACTIVITY"
            suggested_market = "UNDER"
            entry_quality = "NO_OVER"

        if is_under_transition or is_live_cooling:
            status = "LIVE_COOLING"
            reason = "MATCH_STATE_LIVE_COOLING_UNDER_TRANSITION"
            suggested_market = "UNDER"
            entry_quality = "UNDER_LEAN"

        # =========================
        # BLOQUEO DE OVER TARDÍO
        # =========================
        if "OVER" in market:
            if is_under_transition:
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_BLOCKED_UNDER_TRANSITION"
                suggested_market = "UNDER"
                entry_quality = "NO_REENTRY"

            elif is_live_cooling:
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_BLOCKED_LIVE_COOLING"
                suggested_market = "UNDER"
                entry_quality = "NO_REENTRY"

            elif is_very_late and not self._has_extreme_pressure(
                pressure=pressure,
                rhythm=rhythm,
                goal_window=goal_window,
                over_window=over_window,
                context_state=context_state,
            ):
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_TOO_LATE_NO_EXTREME_PRESSURE"
                entry_quality = "NO_REENTRY"

            elif (
                is_late
                and total_goals <= 2
                and is_low_rhythm
                and pressure <= 14
            ):
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_LATE_SCORE_RETENTION"
                suggested_market = "UNDER"
                entry_quality = "NO_REENTRY"

            elif (
                minute >= 60
                and hold_probability >= 72
                and over_probability < 82
            ):
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_BLOCKED_BY_HOLD_PROBABILITY"
                suggested_market = "UNDER"
                entry_quality = "NO_REENTRY"

            elif (
                minute >= 65
                and data_quality in {"LOW", "MEDIUM"}
                and game_quality in {"LOW", "MEDIUM"}
                and pressure <= 16
                and rhythm <= 10
            ):
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_OVER_WEAK_DATA_LATE"
                entry_quality = "WAIT"

        # =========================
        # UNDER CUANDO EL PARTIDO SE CIERRA
        # =========================
        if "UNDER" in market:
            if minute < 58:
                force_action = "OBSERVE"
                downgraded_rank = "OBSERVACION"
                reason = "MATCH_STATE_UNDER_TOO_EARLY"

            elif context_state in {"CALIENTE", "MUY_CALIENTE"} and pressure >= 22:
                force_action = "REJECT"
                downgraded_rank = "NO_BET"
                reason = "MATCH_STATE_UNDER_BLOCKED_HOT_CONTEXT"

            elif is_under_transition and context_state in {"CONTROLADO", "FRIO", "MUERTO"}:
                status = "UNDER_VALID_CONTEXT"
                reason = "MATCH_STATE_UNDER_VALID_TRANSITION"
                suggested_market = "UNDER"
                entry_quality = "VALID"

            elif is_live_cooling and minute >= 60:
                status = "UNDER_VALID_CONTEXT"
                reason = "MATCH_STATE_UNDER_VALID_LIVE_COOLING"
                suggested_market = "UNDER"
                entry_quality = "VALID"

            elif hold_probability >= 72 and pressure <= 16 and rhythm <= 12:
                status = "UNDER_VALID_CONTEXT"
                reason = "MATCH_STATE_UNDER_VALID_SCORE_RETENTION"
                suggested_market = "UNDER"
                entry_quality = "VALID"

        return {
            "match_state_status": status,
            "match_state_reason": reason,
            "suggested_market": suggested_market,
            "force_action": force_action,
            "downgraded_rank": downgraded_rank,
            "entry_quality": entry_quality,
            "hold_probability": round(hold_probability, 2),
            "is_score_retention": status in {"SCORE_RETENTION", "DEAD_MATCH", "UNDER_VALID_CONTEXT"},
            "should_block_over": force_action in {"OBSERVE", "REJECT"} and "OVER" in market,
            "should_suggest_under": suggested_market == "UNDER",
            "debug": {
                "minute": minute,
                "total_goals": total_goals,
                "pressure": pressure,
                "rhythm": rhythm,
                "goal_window": goal_window,
                "over_window": over_window,
                "context_state": context_state,
                "data_quality": data_quality,
                "game_quality": game_quality,
                "goal_probability": goal_probability,
                "over_probability": over_probability,
                "under_probability": under_probability,
                "cooling_detected": cooling_detected,
                "under_transition_score": under_transition_score,
                "live_decay_factor": live_decay_factor,
                "rank": rank,
                "market": market,
            },
        }

    def _calculate_hold_probability(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_window: float,
        over_window: float,
        context_state: str,
        data_quality: str,
        total_goals: int,
    ) -> float:
        hold = 35.0

        if minute >= 60:
            hold += 12.0
        if minute >= 70:
            hold += 10.0
        if minute >= 80:
            hold += 12.0

        if pressure <= 10:
            hold += 14.0
        elif pressure <= 16:
            hold += 8.0

        if rhythm <= 7:
            hold += 14.0
        elif rhythm <= 12:
            hold += 7.0

        if goal_window <= 10:
            hold += 9.0
        if over_window <= 10:
            hold += 9.0

        if context_state == "MUERTO":
            hold += 18.0
        elif context_state == "FRIO":
            hold += 14.0
        elif context_state == "CONTROLADO":
            hold += 8.0
        elif context_state == "TIBIO":
            hold += 2.0
        elif context_state in {"CALIENTE", "MUY_CALIENTE"}:
            hold -= 18.0

        if data_quality == "LOW":
            hold += 6.0
        elif data_quality == "HIGH":
            hold -= 4.0

        if total_goals <= 1 and minute >= 65:
            hold += 6.0

        return self._clamp(hold, 0.0, 96.0)

    def _has_extreme_pressure(
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

    def _extract_minute(self, match: Dict[str, Any], context: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or context.get("minute")
            or 0
        )
        return self._safe_int(raw)

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
