from __future__ import annotations

from typing import Any, Dict


class NextGoalIntelligenceEngine:
    """
    Motor IA para estimar qué equipo tiene mayor posibilidad
    de anotar el siguiente gol.

    No crea señales.
    No reemplaza al motor principal.
    Solo entrega lectura auxiliar avanzada.
    """

    def analyze(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any] | None = None,
        ai: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        match = match or {}
        context = context or {}
        ai = ai or {}

        home_pressure = self._side_pressure(match, "home")
        away_pressure = self._side_pressure(match, "away")

        home_momentum = self._side_momentum(match, "home")
        away_momentum = self._side_momentum(match, "away")

        home_score = self._safe_float(
            match.get("home_score")
            or match.get("local_score")
            or match.get("marcador_local")
        )

        away_score = self._safe_float(
            match.get("away_score")
            or match.get("visitante_score")
            or match.get("marcador_visitante")
        )

        minute = self._safe_float(
            match.get("minute")
            or match.get("minuto")
            or match.get("current_minute")
        )

        home_need = self._need_factor(
            side_score=home_score,
            opponent_score=away_score,
            minute=minute,
        )

        away_need = self._need_factor(
            side_score=away_score,
            opponent_score=home_score,
            minute=minute,
        )

        home_total = (
            home_pressure * 0.45
            + home_momentum * 0.35
            + home_need * 0.20
        )

        away_total = (
            away_pressure * 0.45
            + away_momentum * 0.35
            + away_need * 0.20
        )

        diff = home_total - away_total

        if diff >= 12:
            bias = "HOME"
        elif diff <= -12:
            bias = "AWAY"
        else:
            bias = "BALANCED"

        confidence = min(100.0, abs(diff) + max(home_total, away_total) * 0.45)

        fake_pressure = self._fake_pressure_detected(
            home_pressure=home_pressure,
            away_pressure=away_pressure,
            match=match,
        )

        goal_window = self._goal_window(
            confidence=confidence,
            minute=minute,
            fake_pressure=fake_pressure,
        )

        return {
            "next_goal_ai_enabled": True,
            "next_goal_bias_ai": bias,
            "next_goal_confidence_ai": round(confidence, 2),
            "home_next_goal_power": round(home_total, 2),
            "away_next_goal_power": round(away_total, 2),
            "home_pressure_power": round(home_pressure, 2),
            "away_pressure_power": round(away_pressure, 2),
            "home_momentum_power": round(home_momentum, 2),
            "away_momentum_power": round(away_momentum, 2),
            "home_need_factor": round(home_need, 2),
            "away_need_factor": round(away_need, 2),
            "next_goal_fake_pressure": fake_pressure,
            "next_goal_window_ai": goal_window,
            "next_goal_advice_ai": self._advice(
                bias=bias,
                confidence=confidence,
                fake_pressure=fake_pressure,
            ),
            "next_goal_summary_ai": self._summary(
                bias=bias,
                confidence=confidence,
                home_total=home_total,
                away_total=away_total,
                fake_pressure=fake_pressure,
            ),
        }

    def _side_pressure(
        self,
        match: Dict[str, Any],
        side: str,
    ) -> float:

        stats = match.get(f"{side}_stats")
        if not isinstance(stats, dict):
            stats = {}

        shots = self._safe_float(
            stats.get("shots")
            or match.get(f"{side}_shots")
        )

        shots_on_target = self._safe_float(
            stats.get("shots_on_target")
            or match.get(f"{side}_shots_on_target")
        )

        corners = self._safe_float(
            stats.get("corners")
            or match.get(f"{side}_corners")
        )

        dangerous_attacks = self._safe_float(
            stats.get("dangerous_attacks")
            or match.get(f"{side}_dangerous_attacks")
        )

        xg = self._safe_float(
            stats.get("xg")
            or stats.get("xG")
            or match.get(f"{side}_xg")
        )

        pressure = (
            shots * 3.0
            + shots_on_target * 8.0
            + corners * 3.5
            + dangerous_attacks * 0.5
            + xg * 18.0
        )

        return min(100.0, pressure)

    def _side_momentum(
        self,
        match: Dict[str, Any],
        side: str,
    ) -> float:

        recent = match.get(f"{side}_recent")
        if not isinstance(recent, dict):
            recent = {}

        recent_shots = self._safe_float(recent.get("shots"))
        recent_sot = self._safe_float(recent.get("shots_on_target"))
        recent_corners = self._safe_float(recent.get("corners"))
        recent_attacks = self._safe_float(recent.get("dangerous_attacks"))

        if recent:
            momentum = (
                recent_shots * 5.0
                + recent_sot * 12.0
                + recent_corners * 5.0
                + recent_attacks * 0.8
            )

            return min(100.0, momentum)

        pressure_index = self._safe_float(match.get("pressure_index"))
        rhythm_index = self._safe_float(match.get("rhythm_index"))

        if side == "home":
            side_boost = self._safe_float(match.get("home_next_goal_pressure"))
        else:
            side_boost = self._safe_float(match.get("away_next_goal_pressure"))

        return min(
            100.0,
            pressure_index * 1.2
            + rhythm_index * 1.1
            + side_boost,
        )

    def _need_factor(
        self,
        side_score: float,
        opponent_score: float,
        minute: float,
    ) -> float:

        if minute < 1:
            return 30.0

        if side_score < opponent_score:
            if minute >= 75:
                return 85.0
            if minute >= 60:
                return 72.0
            return 55.0

        if side_score == opponent_score:
            if minute >= 70:
                return 58.0
            return 45.0

        if side_score > opponent_score:
            if minute >= 75:
                return 25.0
            return 35.0

        return 40.0

    def _fake_pressure_detected(
        self,
        home_pressure: float,
        away_pressure: float,
        match: Dict[str, Any],
    ) -> bool:

        total_pressure = home_pressure + away_pressure

        shots_on_target = self._safe_float(match.get("shots_on_target"))
        xg = self._safe_float(match.get("xg") or match.get("xG"))

        if total_pressure >= 65 and shots_on_target <= 1 and xg <= 0.25:
            return True

        return False

    def _goal_window(
        self,
        confidence: float,
        minute: float,
        fake_pressure: bool,
    ) -> str:

        if fake_pressure:
            return "SIN_CONFIRMACION"

        if confidence >= 80:
            if minute >= 80:
                return "1-3_MIN"
            return "2-5_MIN"

        if confidence >= 65:
            return "3-7_MIN"

        if confidence >= 50:
            return "OBSERVAR"

        return "SIN_VENTANA"

    def _advice(
        self,
        bias: str,
        confidence: float,
        fake_pressure: bool,
    ) -> str:

        if fake_pressure:
            return "Presión sospechosa. No confiar sin tiro claro o xG real."

        if bias == "BALANCED":
            return "No hay lado dominante para próximo gol."

        if confidence >= 75:
            return f"Bias fuerte hacia {bias}. Confirmar con evento ofensivo reciente."

        if confidence >= 55:
            return f"Bias moderado hacia {bias}. Mantener observación."

        return "Lectura débil. No usar para entrada."

    def _summary(
        self,
        bias: str,
        confidence: float,
        home_total: float,
        away_total: float,
        fake_pressure: bool,
    ) -> str:

        if fake_pressure:
            return "Próximo gol sin confirmación: presión posible pero sin profundidad real."

        return (
            f"Next Goal IA: {bias} "
            f"con confianza {round(confidence, 1)}%. "
            f"Home power={round(home_total, 1)}, "
            f"Away power={round(away_total, 1)}."
        )

    def _safe_float(
        self,
        value: Any,
    ) -> float:

        try:
            return float(value or 0)
        except Exception:
            return 0.0
