from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


class MatchReadingEnhancer:
    """
    Ayudante de lectura del partido.

    No bloquea.
    No publica señales.
    No reemplaza ScanService.

    Solo agrega lectura extra:
    - reading_strength
    - reading_label
    - match_temperature
    - score_context
    - late_game_risk
    - resolved_match_risk
    - momentum_warning
    - reading_advice
    """

    def enhance(self, match: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(match or {})

        minute = self._minute(data)
        home_score = self._safe_int(
            data.get("home_score") or data.get("local_score") or data.get("marcador_local")
        )
        away_score = self._safe_int(
            data.get("away_score") or data.get("visitante_score") or data.get("marcador_visitante")
        )

        total_goals = home_score + away_score
        goal_diff = abs(home_score - away_score)

        shots = self._safe_float(data.get("shots"))
        shots_on_target = self._safe_float(data.get("shots_on_target"))
        corners = self._safe_float(data.get("corners"))
        dangerous_attacks = self._safe_float(data.get("dangerous_attacks"))
        xg = self._safe_float(data.get("xg") or data.get("xG"))

        pressure_score = (
            shots * 1.2
            + shots_on_target * 3.0
            + corners * 1.4
            + dangerous_attacks * 0.35
            + xg * 12.0
        )

        score_context = self._score_context(
            total_goals=total_goals,
            goal_diff=goal_diff,
            minute=minute,
        )

        match_temperature = self._temperature(
            pressure_score=pressure_score,
            minute=minute,
            total_goals=total_goals,
        )

        late_game_risk = minute >= 70
        resolved_match_risk = goal_diff >= 3 and minute >= 60
        overextended_risk = total_goals >= 4 and minute >= 65

        penalty = 0.0
        if late_game_risk:
            penalty += 8.0
        if resolved_match_risk:
            penalty += 18.0
        if overextended_risk:
            penalty += 14.0
        if xg <= 0 and shots_on_target <= 2 and minute >= 55:
            penalty += 10.0

        reading_strength = max(0.0, min(100.0, pressure_score - penalty))

        if resolved_match_risk:
            reading_label = "MATCH_RESOLVED"
            reading_advice = "Partido posiblemente resuelto. Evitar entrada tardía salvo presión nueva muy fuerte."
            momentum_warning = "RIESGO_DE_PARTIDO_MUERTO"
        elif overextended_risk:
            reading_label = "OVEREXTENDED"
            reading_advice = "Marcador muy movido y minuto avanzado. Puede no quedar valor real."
            momentum_warning = "RIESGO_DE_SOBREEXTENSION"
        elif reading_strength >= 70:
            reading_label = "STRONG_READING"
            reading_advice = "Lectura fuerte. El partido mantiene señales ofensivas válidas."
            momentum_warning = "OK"
        elif reading_strength >= 45:
            reading_label = "MEDIUM_READING"
            reading_advice = "Lectura media. Conviene esperar confirmación."
            momentum_warning = "CONFIRMAR"
        else:
            reading_label = "WEAK_READING"
            reading_advice = "Lectura débil o poco valor actual."
            momentum_warning = "NO_FORZAR"

        data["reading_strength"] = round(reading_strength, 2)
        data["reading_label"] = reading_label
        data["match_temperature"] = match_temperature
        data["score_context"] = score_context
        data["late_game_risk"] = late_game_risk
        data["resolved_match_risk"] = resolved_match_risk
        data["overextended_risk"] = overextended_risk
        data["momentum_warning"] = momentum_warning
        data["reading_advice"] = reading_advice

        return data

    def _score_context(self, total_goals: int, goal_diff: int, minute: int) -> str:
        if goal_diff >= 3 and minute >= 60:
            return "RESOLVED"
        if total_goals >= 4 and minute >= 65:
            return "OVEREXTENDED"
        if total_goals == 0:
            return "CLOSED_SCORE"
        if goal_diff <= 1:
            return "COMPETITIVE"
        return "CONTROLLED"

    def _temperature(self, pressure_score: float, minute: int, total_goals: int) -> str:
        if minute >= 70 and total_goals >= 4:
            return "SATURATED"
        if pressure_score >= 75:
            return "HOT"
        if pressure_score >= 45:
            return "WARM"
        if pressure_score >= 20:
            return "LOW"
        return "COLD"

    def _minute(self, item: Dict[str, Any]) -> int:
        return self._safe_int(
            item.get("minute")
            or item.get("minuto")
            or item.get("current_minute")
            or item.get("match_minute")
        )

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
