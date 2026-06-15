from typing import Any, Dict


class PressureQualityAI:
    """
    V17_PRESSURE_QUALITY_AI

    Este módulo no decide apuestas.
    Su función es interpretar la calidad real de la presión del partido.

    Distingue:
    - presión real de gol
    - presión falsa (volumen sin peligro)
    - dominio territorial sin profundidad
    - partidos controlados
    - partidos abiertos
    - baja actividad ofensiva real
    """

    VERSION = "V17_PRESSURE_QUALITY_AI_1"

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:

        shots = self._num(match.get("shots"))
        shots_on_target = self._num(match.get("shots_on_target"))
        corners = self._num(match.get("corners"))
        xg = self._num(match.get("xg") or match.get("xG"))
        dangerous_attacks = self._num(match.get("dangerous_attacks"))

        home_score = self._num(match.get("home_score"))
        away_score = self._num(match.get("away_score"))
        minute = self._num(match.get("api_minute") or match.get("minute"))

        pressure_score = self._calculate_pressure_score(
            shots,
            shots_on_target,
            corners,
            xg,
            dangerous_attacks
        )

        pressure_type = self._classify_pressure(
            shots,
            shots_on_target,
            corners,
            xg,
            dangerous_attacks
        )

        game_state = self._classify_game_state(
            minute,
            home_score,
            away_score,
            pressure_score
        )

        dominant_team = self._detect_dominance(match)

        real_goal_threat = self._goal_threat(
            shots_on_target,
            xg,
            dangerous_attacks
        )

        false_pressure_risk = self._false_pressure_risk(
            shots,
            shots_on_target,
            dangerous_attacks
        )

        return {
            "pressure_quality_version": self.VERSION,

            "pressure_type": pressure_type,
            "pressure_score": pressure_score,

            "game_state": game_state,

            "dominant_team": dominant_team,

            "real_goal_threat": real_goal_threat,
            "false_pressure_risk": false_pressure_risk,

            "shots": shots,
            "shots_on_target": shots_on_target,
            "corners": corners,
            "xg": xg,
            "dangerous_attacks": dangerous_attacks,

            "pressure_reading": self._final_reading(
                pressure_type,
                real_goal_threat,
                false_pressure_risk
            )
        }

    # -------------------------
    # CORE LOGIC
    # -------------------------

    def _calculate_pressure_score(self, shots, sot, corners, xg, da):
        return (
            shots * 1.0 +
            sot * 3.0 +
            corners * 1.5 +
            xg * 10 +
            da * 2.5
        )

    def _classify_pressure(self, shots, sot, corners, xg, da):

        if sot >= 3 and xg >= 1.0:
            return "REAL_PRESSURE"

        if shots >= 10 and sot == 0:
            return "FALSE_PRESSURE"

        if shots >= 8 and da == 0:
            return "LATERAL_PRESSURE"

        if corners >= 5 and sot <= 1:
            return "DOMINANCE_WITHOUT_DEPTH"

        if xg >= 1.2:
            return "HIGH_THREAT_PRESSURE"

        return "LOW_PRESSURE"

    def _classify_game_state(self, minute, home, away, pressure_score):

        if minute >= 75:
            return "CLOSING_GAME"

        if home != away and pressure_score > 18:
            return "BROKEN_GAME"

        if pressure_score >= 15:
            return "OPEN_GAME"

        if pressure_score >= 8:
            return "CONTROLLED_GAME"

        return "LOW_ACTIVITY_GAME"

    def _detect_dominance(self, match):

        home_pos = self._num(match.get("home_possession"))
        away_pos = self._num(match.get("away_possession"))

        if home_pos > away_pos + 10:
            return "HOME_DOMINANT"

        if away_pos > home_pos + 10:
            return "AWAY_DOMINANT"

        return "BALANCED"

    def _goal_threat(self, sot, xg, da):

        if sot >= 3 and xg >= 1:
            return "HIGH"

        if sot >= 1 and xg >= 0.6:
            return "MEDIUM"

        if da >= 5:
            return "MEDIUM_LOW"

        return "LOW"

    def _false_pressure_risk(self, shots, sot, da):

        if shots >= 10 and sot == 0:
            return "HIGH"

        if shots >= 8 and da == 0:
            return "MEDIUM_HIGH"

        return "LOW"

    def _final_reading(self, pressure_type, threat, false_risk):

        if pressure_type == "REAL_PRESSURE" and threat == "HIGH":
            return "PRESIÓN REAL DE GOL"

        if pressure_type == "FALSE_PRESSURE":
            return "PRESIÓN FALSA (SIN PELIGRO REAL)"

        if false_risk == "HIGH":
            return "DOMINIO SIN AMENAZA CLARA"

        if pressure_type == "LATERAL_PRESSURE":
            return "PRESIÓN LATERAL SIN PROFUNDIDAD"

        return "PRESIÓN NEUTRAL"

    # -------------------------
    # UTILS
    # -------------------------

    def _num(self, value: Any) -> float:
        try:
            if value is None or value == "":
                return 0.0
            return float(value)
        except Exception:
            return 0.0
