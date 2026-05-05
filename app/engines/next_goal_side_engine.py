from __future__ import annotations

from typing import Any, Dict


class NextGoalSideEngine:
    """
    Lee de qué lado podría venir el próximo gol.

    No apuesta.
    No bloquea.
    No decide señales.

    Solo devuelve lectura auxiliar para reforzar OVER/UNDER.
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

        dominance = str(context.get("dominance") or "BALANCED").upper()
        attack_side = str(context.get("attack_side") or "BALANCED").upper()
        context_state = str(context.get("context_state") or "MUERTO").upper()
        data_quality = str(context.get("data_quality") or "LOW").upper()

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
            confidence -= 18
        elif context_state == "CONTROLADO":
            confidence -= 8
        elif context_state == "CALIENTE":
            confidence += 6
        elif context_state == "MUY_CALIENTE":
            confidence += 10

        confidence = round(max(0.0, min(confidence, 95.0)), 2)

        score_hold_probability = self._score_hold_probability(
            minute=minute,
            pressure=pressure,
            rhythm=rhythm,
            goal_probability=goal_probability,
            context_state=context_state,
            data_quality=data_quality,
        )

        if score_hold_probability >= 70:
            status = "SCORE_HOLD"
        elif bias != "NEUTRAL" and confidence >= 65:
            status = "CONFIRMATION"
        elif bias != "NEUTRAL" and confidence >= 50:
            status = "LEAN"
        else:
            status = "UNCLEAR"

        warning = self._warning(
            bias=bias,
            confidence=confidence,
            score_hold_probability=score_hold_probability,
            context_state=context_state,
            data_quality=data_quality,
            pressure=pressure,
            rhythm=rhythm,
        )

        return {
            "next_goal_bias": bias,
            "next_goal_confidence": confidence,
            "score_hold_probability": score_hold_probability,
            "next_goal_status": status,
            "next_goal_warning": warning,
            "home_next_goal_pressure": round(home_score_pressure, 2),
            "away_next_goal_pressure": round(away_score_pressure, 2),
        }

    def _score_hold_probability(
        self,
        minute: int,
        pressure: float,
        rhythm: float,
        goal_probability: float,
        context_state: str,
        data_quality: str,
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

        if context_state in {"MUERTO", "FRIO"}:
            hold += 18
        elif context_state == "CONTROLADO":
            hold += 8
        elif context_state in {"CALIENTE", "MUY_CALIENTE"}:
            hold -= 16

        if data_quality == "LOW":
            hold += 6

        return round(max(0.0, min(hold, 95.0)), 2)

    def _warning(
        self,
        bias: str,
        confidence: float,
        score_hold_probability: float,
        context_state: str,
        data_quality: str,
        pressure: float,
        rhythm: float,
    ) -> str:
        if data_quality == "LOW":
            return "LOW_DATA_SIDE_READING"

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
