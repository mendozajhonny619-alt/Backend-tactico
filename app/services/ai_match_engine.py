from __future__ import annotations

from typing import Any, Dict


class AIMatchEngine:
    """
    Convierte contexto + datos del partido en lectura IA operativa.
    """

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

        home_pressure = self._safe_float(context.get("home_pressure"))
        away_pressure = self._safe_float(context.get("away_pressure"))

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
            return {
                "ai_score": 0.0,
                "goal_probability": 0.0,
                "over_probability": 0.0,
                "under_probability": 95.0,
                "risk_score": 9.0,
                "risk_level": "ALTO",
                "momentum_label": "ESTABLE",
                "result_prediction": "NO_EDGE",
                "winner_prediction": "DRAW_LEAN",
            }

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

        risk_score = self._calculate_risk_score(
            data_quality=data_quality,
            context_state=context_state,
            pressure=pressure,
            rhythm=rhythm,
            minute=minute,
            red_alert=red_alert,
            ai_score=ai_score,
        )

        risk_level = self._risk_level_from_score(risk_score)

        momentum_label = self._momentum_label(
            pressure=pressure,
            rhythm=rhythm,
            context_state=context_state,
            red_alert=red_alert,
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

        return {
            "ai_score": round(ai_score, 2),
            "goal_probability": round(goal_probability, 2),
            "over_probability": round(over_probability, 2),
            "under_probability": round(under_probability, 2),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "momentum_label": momentum_label,
            "result_prediction": result_prediction,
            "winner_prediction": winner_prediction,
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
            risk += 1.4
        elif minute <= 12:
            risk += 1.0

        if red_alert:
            risk += 0.5

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
    ) -> str:
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
        if minute < 10:
            return -4.0
        if minute > 85:
            return -3.0
        return 0.0

    def _goal_minute_adjustment(self, minute: int) -> float:
        if 25 <= minute <= 45:
            return 6.0
        if 60 <= minute <= 75:
            return 8.0
        if 76 <= minute <= 85:
            return 4.0
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
