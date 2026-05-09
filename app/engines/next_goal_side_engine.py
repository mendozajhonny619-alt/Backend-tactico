from __future__ import annotations

from typing import Any, Dict


class NextGoalSideEngine:
    """
    Lee de qué lado podría venir el próximo gol.

    No apuesta.
    No bloquea.
    No decide señales.

    Solo devuelve lectura auxiliar para reforzar OVER/UNDER,
    próximo gol, retención y resultado probable.
    """

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        ai: Dict[str, Any],
    ) -> Dict[str, Any]:
        match = match or {}
        context = context or {}
        ai = ai or {}

        minute = self._safe_int(match.get("minute") or context.get("minute"))

        home_score = self._safe_int(match.get("home_score") or match.get("local_score"))
        away_score = self._safe_int(match.get("away_score") or match.get("visitante_score"))

        home_pressure = self._safe_float(context.get("home_pressure"))
        away_pressure = self._safe_float(context.get("away_pressure"))

        pressure = self._safe_float(context.get("pressure_index"))
        rhythm = self._safe_float(context.get("rhythm_index"))
        goal_probability = self._safe_float(ai.get("goal_probability"))
        over_probability = self._safe_float(ai.get("over_probability"))
        under_probability = self._safe_float(ai.get("under_probability"))

        dominance = str(context.get("dominance") or "BALANCED").upper()
        attack_side = str(context.get("attack_side") or "BALANCED").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()
        cooling_detected = bool(context.get("cooling_detected", False))
        under_transition_score = self._safe_float(context.get("under_transition_score"))
        live_decay_factor = self._safe_float(context.get("live_decay_factor") or 1.0)

        late_reactivation = bool(context.get("late_reactivation", False))
        chaos_mode = bool(context.get("chaos_mode", False))
        fake_pressure_detected = bool(context.get("fake_pressure_detected", False))
        pressure_without_depth = bool(context.get("pressure_without_depth", False))
        retention_shape = bool(context.get("retention_shape", False))
        red_alert = bool(context.get("red_alert", False))

        field_vision_status = str(context.get("field_vision_status") or "").upper()
        field_vision_score = self._safe_float(context.get("field_vision_score"))
        is_added_time = bool(
            context.get("is_added_time")
            or context.get("field_vision_is_added_time")
            or minute >= 90
        )

        home_score_pressure = home_pressure
        away_score_pressure = away_pressure

        if dominance == "HOME":
            home_score_pressure += 6
        elif dominance == "AWAY":
            away_score_pressure += 6

        if attack_side == "HOME":
            home_score_pressure += 5
        elif attack_side == "AWAY":
            away_score_pressure += 5

        if home_score < away_score:
            home_score_pressure += 3
        elif away_score < home_score:
            away_score_pressure += 3

        if chaos_mode or red_alert:
            home_score_pressure += 2 if home_pressure >= away_pressure else 0
            away_score_pressure += 2 if away_pressure > home_pressure else 0

        if fake_pressure_detected or pressure_without_depth:
            home_score_pressure *= 0.90
            away_score_pressure *= 0.90

        diff = abs(home_score_pressure - away_score_pressure)

        if diff < 5:
            bias = "NEUTRAL"
        elif home_score_pressure > away_score_pressure:
            bias = "HOME"
        else:
            bias = "AWAY"

        confidence = min(
            95.0,
            max(
                0.0,
                35.0
                + diff * 2.2
                + min(pressure, 35) * 0.45
                + min(rhythm, 25) * 0.35
                + max(0.0, goal_probability - 50) * 0.25
                + max(0.0, over_probability - 50) * 0.20
            ),
        )

        if data_quality == "LOW":
            confidence -= 14
        elif data_quality == "MEDIUM":
            confidence -= 5

        if context_state in {"MUERTO", "FRIO"}:
            if late_reactivation or chaos_mode or red_alert:
                confidence -= 5
            else:
                confidence -= 18
        elif context_state == "CONTROLADO":
            confidence -= 8
        elif context_state == "CALIENTE":
            confidence += 6
        elif context_state == "MUY_CALIENTE":
            confidence += 10

        if cooling_detected and not (late_reactivation or chaos_mode):
            confidence -= 12

        if under_transition_score >= 70 and not (late_reactivation or chaos_mode):
            confidence -= 16
        elif under_transition_score >= 55:
            confidence -= 8

        if live_decay_factor <= 0.70 and not (late_reactivation or chaos_mode):
            confidence -= 8

        if late_reactivation or field_vision_status == "REACTIVATION":
            confidence += 7

        if chaos_mode or field_vision_status == "CHAOS" or red_alert:
            confidence += 9

        if fake_pressure_detected or pressure_without_depth:
            confidence -= 10

        if retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            confidence -= 8

        if is_added_time:
            if late_reactivation or chaos_mode or red_alert:
                confidence += 3
            else:
                confidence -= 5

        confidence = round(max(0.0, min(confidence, 95.0)), 2)

        score_hold_probability = self._score_hold_probability(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_probability=goal_probability,
            under_probability=under_probability,
            context_state=context_state,
            data_quality=data_quality,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            live_decay_factor=live_decay_factor,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
            field_vision_status=field_vision_status,
            is_added_time=is_added_time,
        )

        chances = self._side_chances(
            bias=bias,
            confidence=confidence,
            score_hold_probability=score_hold_probability,
            home_pressure=home_score_pressure,
            away_pressure=away_score_pressure,
            goal_probability=goal_probability,
        )

        home_goal_chance = chances["home_goal_chance"]
        away_goal_chance = chances["away_goal_chance"]
        no_goal_chance = chances["no_goal_chance"]

        if score_hold_probability >= 70:
            status = "SCORE_HOLD"
        elif bias != "NEUTRAL" and confidence >= 65:
            status = "CONFIRMATION"
        elif bias != "NEUTRAL" and confidence >= 50:
            status = "LEAN"
        else:
            status = "UNCLEAR"

        market_suggestion = self._market_suggestion(
            bias=bias,
            confidence=confidence,
            score_hold_probability=score_hold_probability,
            goal_probability=goal_probability,
            over_probability=over_probability,
            under_probability=under_probability,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            retention_shape=retention_shape,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            is_added_time=is_added_time,
        )

        projected_outcome = self._projected_outcome(
            home_score=home_score,
            away_score=away_score,
            bias=bias,
            score_hold_probability=score_hold_probability,
            home_goal_chance=home_goal_chance,
            away_goal_chance=away_goal_chance,
            no_goal_chance=no_goal_chance,
        )

        warning = self._warning(
            bias=bias,
            confidence=confidence,
            score_hold_probability=score_hold_probability,
            context_state=context_state,
            data_quality=data_quality,
            pressure=pressure,
            rhythm=rhythm,
            cooling_detected=cooling_detected,
            under_transition_score=under_transition_score,
            late_reactivation=late_reactivation,
            chaos_mode=chaos_mode,
            fake_pressure_detected=fake_pressure_detected,
            pressure_without_depth=pressure_without_depth,
            retention_shape=retention_shape,
        )

        return {
            "next_goal_bias": bias,
            "next_goal_confidence": confidence,
            "score_hold_probability": score_hold_probability,
            "next_goal_status": status,
            "next_goal_warning": warning,
            "home_next_goal_pressure": round(home_score_pressure, 2),
            "away_next_goal_pressure": round(away_score_pressure, 2),

            "home_goal_chance": home_goal_chance,
            "away_goal_chance": away_goal_chance,
            "no_goal_chance": no_goal_chance,
            "score_hold_label": self._hold_label(score_hold_probability),
            "next_goal_market_suggestion": market_suggestion,
            "projected_match_outcome": projected_outcome,
        }

    def _score_hold_probability(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_probability: float,
        under_probability: float,
        context_state: str,
        data_quality: str,
        cooling_detected: bool,
        under_transition_score: float,
        live_decay_factor: float,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
        field_vision_status: str,
        is_added_time: bool,
    ) -> float:
        hold = 45.0

        if minute >= 60:
            hold += 8
        if minute >= 75:
            hold += 10

        if pressure <= 8:
            hold += 12
        elif pressure >= 18:
            hold -= 12

        if rhythm <= 6:
            hold += 10
        elif rhythm >= 14:
            hold -= 10

        if goal_probability >= 65:
            hold -= 18
        elif goal_probability <= 45:
            hold += 10

        if under_probability >= 68:
            hold += 7

        if context_state in {"MUERTO", "FRIO"}:
            hold += 18
        elif context_state == "CONTROLADO":
            hold += 8
        elif context_state in {"CALIENTE", "MUY_CALIENTE"}:
            hold -= 16

        if cooling_detected:
            hold += 10

        if under_transition_score >= 70:
            hold += 14
        elif under_transition_score >= 55:
            hold += 8

        if live_decay_factor <= 0.70:
            hold += 6

        if data_quality == "LOW":
            hold += 6

        if late_reactivation or field_vision_status == "REACTIVATION":
            hold -= 14

        if chaos_mode or field_vision_status == "CHAOS":
            hold -= 16

        if fake_pressure_detected or pressure_without_depth:
            hold += 8

        if retention_shape or field_vision_status in {"RETENTION", "UNDER_CONTROL"}:
            hold += 14

        if is_added_time:
            if late_reactivation or chaos_mode:
                hold -= 5
            else:
                hold += 5

        return round(max(0.0, min(hold, 95.0)), 2)

    def _side_chances(
        self,
        bias: str,
        confidence: float,
        score_hold_probability: float,
        home_pressure: float,
        away_pressure: float,
        goal_probability: float,
    ) -> Dict[str, float]:
        no_goal = max(score_hold_probability, 100.0 - goal_probability)
        no_goal = max(0.0, min(no_goal, 95.0))

        available_goal_space = max(0.0, 100.0 - no_goal)

        total_side_pressure = max(home_pressure + away_pressure, 1.0)
        home_share = home_pressure / total_side_pressure
        away_share = away_pressure / total_side_pressure

        if bias == "HOME":
            home_share += min(confidence / 400.0, 0.20)
            away_share = max(0.0, 1.0 - home_share)
        elif bias == "AWAY":
            away_share += min(confidence / 400.0, 0.20)
            home_share = max(0.0, 1.0 - away_share)

        total_share = max(home_share + away_share, 1.0)
        home_share /= total_share
        away_share /= total_share

        home_chance = available_goal_space * home_share
        away_chance = available_goal_space * away_share

        return {
            "home_goal_chance": round(max(0.0, min(home_chance, 95.0)), 2),
            "away_goal_chance": round(max(0.0, min(away_chance, 95.0)), 2),
            "no_goal_chance": round(max(0.0, min(no_goal, 95.0)), 2),
        }

    def _market_suggestion(
        self,
        bias: str,
        confidence: float,
        score_hold_probability: float,
        goal_probability: float,
        over_probability: float,
        under_probability: float,
        late_reactivation: bool,
        chaos_mode: bool,
        retention_shape: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        is_added_time: bool,
    ) -> str:
        if score_hold_probability >= 72 and under_probability >= 62:
            return "SCORE_HOLD_OR_UNDER"

        if retention_shape or fake_pressure_detected or pressure_without_depth:
            return "UNDER_OR_SCORE_HOLD"

        if bias in {"HOME", "AWAY"} and confidence >= 68 and goal_probability >= 62:
            return f"NEXT_GOAL_{bias}"

        if chaos_mode and over_probability >= 60:
            return "OVER_OR_NEXT_GOAL"

        if late_reactivation and over_probability >= 58:
            return "OVER_WATCH_OR_NEXT_GOAL"

        if is_added_time and score_hold_probability >= 65:
            return "SCORE_HOLD"

        return "NO_CLEAR_MARKET"

    def _projected_outcome(
        self,
        home_score: int,
        away_score: int,
        bias: str,
        score_hold_probability: float,
        home_goal_chance: float,
        away_goal_chance: float,
        no_goal_chance: float,
    ) -> str:
        if score_hold_probability >= 72 or no_goal_chance >= 70:
            return f"{home_score}-{away_score}"

        if bias == "HOME" and home_goal_chance >= away_goal_chance:
            return f"{home_score + 1}-{away_score}"

        if bias == "AWAY" and away_goal_chance >= home_goal_chance:
            return f"{home_score}-{away_score + 1}"

        return f"{home_score}-{away_score}"

    def _hold_label(self, score_hold_probability: float) -> str:
        if score_hold_probability >= 75:
            return "ALTA_RETENCION"
        if score_hold_probability >= 60:
            return "RETENCION_MEDIA"
        return "BAJA_RETENCION"

    def _warning(
        self,
        bias: str,
        confidence: float,
        score_hold_probability: float,
        context_state: str,
        data_quality: str,
        pressure: float,
        rhythm: float,
        cooling_detected: bool,
        under_transition_score: float,
        late_reactivation: bool,
        chaos_mode: bool,
        fake_pressure_detected: bool,
        pressure_without_depth: bool,
        retention_shape: bool,
    ) -> str:
        if data_quality == "LOW":
            return "LOW_DATA_SIDE_READING"

        if chaos_mode:
            return "CHAOS_SIDE_READING"

        if late_reactivation:
            return "REACTIVATION_SIDE_READING"

        if fake_pressure_detected:
            return "FAKE_PRESSURE_SIDE_READING"

        if pressure_without_depth:
            return "PRESSURE_WITHOUT_DEPTH_SIDE_READING"

        if retention_shape:
            return "RETENTION_SIDE_READING"

        if under_transition_score >= 70:
            return "UNDER_TRANSITION_SIDE_READING"

        if cooling_detected:
            return "COOLING_SIDE_READING"

        if score_hold_probability >= 70:
            return "RESULT_MAY_HOLD"

        if bias == "NEUTRAL":
            return "NO_CLEAR_SIDE_ADVANTAGE"

        if context_state in {"MUERTO", "FRIO"}:
            return "SIDE_BIAS_BUT_COLD_MATCH"

        if confidence >= 70 and pressure >= 12 and rhythm >= 7:
            return "SIDE_PRESSURE_CONFIRMED"

        return "SIDE_READING_NEEDS_CONFIRMATION"

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
