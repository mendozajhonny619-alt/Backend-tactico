from __future__ import annotations

from typing import Any, Dict, List


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


class TacticalAI:
    """
    Inteligencia táctica V17.

    No decide ENTER.
    Interpreta:
    - presión real
    - profundidad ofensiva
    - ritmo
    - tiros
    - tiros al arco
    - corners
    - xG
    - ataques peligrosos
    - necesidad ofensiva
    - riesgo de falsa presión

    Objetivo:
    - no regalar OVER por presión falsa
    - no castigar OVER cuando sí hay volumen ofensivo real
    - ayudar a que UNDER salga solo cuando el partido realmente está cerrado
    """

    def evaluate(self, match: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        minute = safe_int(
            match.get("api_minute")
            or match.get("display_minute")
            or match.get("minute")
            or match.get("minuto"),
            0,
        )

        total_dangerous = safe_float(
            match.get("total_dangerous_attacks")
            or match.get("dangerous_attacks")
            or match.get("attacks_dangerous")
            or match.get("ataques_peligrosos"),
            0.0,
        )

        total_shots = safe_float(
            match.get("total_shots")
            or match.get("shots")
            or match.get("tiros")
            or match.get("disparos"),
            0.0,
        )

        total_shots_on = safe_float(
            match.get("total_shots_on")
            or match.get("shots_on_target")
            or match.get("sot")
            or match.get("tiros_al_arco")
            or match.get("remates_al_arco"),
            0.0,
        )

        total_corners = safe_float(
            match.get("total_corners")
            or match.get("corners")
            or match.get("corner_kicks"),
            0.0,
        )

        total_xg = safe_float(
            match.get("total_xg")
            or match.get("xg")
            or match.get("xG"),
            0.0,
        )

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score
        score_diff = abs(home_score - away_score)

        data_quality = str(
            match.get("data_quality")
            or match.get("calidad_datos")
            or "LOW"
        ).upper()

        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)

        tactical_warnings: List[str] = []
        tactical_strengths: List[str] = []

        offensive_volume_score = self._offensive_volume_score(
            total_dangerous=total_dangerous,
            total_shots=total_shots,
            total_shots_on=total_shots_on,
            total_corners=total_corners,
            total_xg=total_xg,
            minute=minute,
        )

        deep_pressure_score = self._deep_pressure_score(
            minute=minute,
            total_dangerous=total_dangerous,
            total_shots=total_shots,
            total_shots_on=total_shots_on,
            total_corners=total_corners,
            total_xg=total_xg,
        )

        offensive_depth_score = self._offensive_depth_score(
            total_shots=total_shots,
            total_shots_on=total_shots_on,
            total_xg=total_xg,
            total_dangerous=total_dangerous,
            total_corners=total_corners,
        )

        recent_attack_proxy = self._recent_attack_proxy(
            minute=minute,
            total_dangerous=total_dangerous,
            total_shots=total_shots,
            total_corners=total_corners,
            total_shots_on=total_shots_on,
        )

        false_pressure_risk = self._false_pressure_risk(
            pressure_score=pressure_score,
            total_shots=total_shots,
            total_shots_on=total_shots_on,
            total_xg=total_xg,
            offensive_depth_score=offensive_depth_score,
            offensive_volume_score=offensive_volume_score,
        )

        data_quality_bonus = self._data_quality_bonus(data_quality)

        tactical_score = (
            deep_pressure_score * 0.24
            + offensive_depth_score * 0.24
            + offensive_volume_score * 0.18
            + rhythm_score * 0.14
            + goal_need_score * 0.12
            + recent_attack_proxy * 0.08
            + data_quality_bonus
        )

        # Ajuste por marcador abierto.
        if total_goals >= 2 and minute <= 80:
            tactical_score += 3
            tactical_strengths.append("OPEN_SCORELINE_CONTEXT")

        if score_diff <= 1 and minute >= 55 and goal_need_score >= 60:
            tactical_score += 4
            tactical_strengths.append("CLOSE_SCORE_WITH_GOAL_NEED")

        tactical_score = clamp(tactical_score)

        # Fortalezas tácticas.
        if deep_pressure_score >= 68:
            tactical_strengths.append("DEEP_PRESSURE")

        if offensive_depth_score >= 65:
            tactical_strengths.append("OFFENSIVE_DEPTH")

        if offensive_volume_score >= 65:
            tactical_strengths.append("REAL_OFFENSIVE_VOLUME")

        if rhythm_score >= 65:
            tactical_strengths.append("RHYTHM_ALIVE")

        if goal_need_score >= 60:
            tactical_strengths.append("SCORE_NEED")

        if recent_attack_proxy >= 60:
            tactical_strengths.append("RECENT_ACTIVITY")

        if total_shots_on >= 4:
            tactical_strengths.append("CLEAR_SHOTS_ON_TARGET")

        if total_shots >= 14:
            tactical_strengths.append("HIGH_TOTAL_SHOTS")

        if total_corners >= 6:
            tactical_strengths.append("CORNER_PRESSURE")

        if total_xg >= 1.2:
            tactical_strengths.append("XG_DANGER")

        # Advertencias tácticas.
        if false_pressure_risk >= 70:
            tactical_warnings.append("FALSE_PRESSURE_RISK")

        if total_shots_on <= 1 and minute >= 55:
            tactical_warnings.append("LOW_SHOTS_ON_TARGET")

        if offensive_depth_score < 40 and minute >= 60:
            tactical_warnings.append("NO_OFFENSIVE_DEPTH")

        if offensive_volume_score < 38 and minute >= 60:
            tactical_warnings.append("LOW_OFFENSIVE_VOLUME")

        if rhythm_score < 35 and minute >= 65:
            tactical_warnings.append("LOW_RHYTHM")

        if data_quality == "LOW":
            tactical_warnings.append("LOW_DATA_QUALITY")

        if minute >= 85 and recent_attack_proxy < 45:
            tactical_warnings.append("VERY_LATE_LOW_REACTIVATION")

        if tactical_score >= 75:
            tactical_status = "TACTICAL_STRONG"
        elif tactical_score >= 62:
            tactical_status = "TACTICAL_GOOD"
        elif tactical_score >= 48:
            tactical_status = "TACTICAL_OBSERVE"
        else:
            tactical_status = "TACTICAL_WEAK"

        return {
            "tactical_status": tactical_status,
            "tactical_score": round(tactical_score, 2),
            "deep_pressure_score": round(deep_pressure_score, 2),
            "offensive_depth_score": round(offensive_depth_score, 2),
            "offensive_volume_score": round(offensive_volume_score, 2),
            "recent_attack_proxy": round(recent_attack_proxy, 2),
            "false_pressure_risk": round(false_pressure_risk, 2),

            # Se devuelven también para que market_ai.py no trabaje con ceros.
            "pressure_score": round(pressure_score, 2),
            "rhythm_score": round(rhythm_score, 2),
            "goal_need_score": round(goal_need_score, 2),

            "total_dangerous_attacks": round(total_dangerous, 2),
            "total_shots": round(total_shots, 2),
            "total_shots_on": round(total_shots_on, 2),
            "total_corners": round(total_corners, 2),
            "total_xg": round(total_xg, 2),

            "tactical_strengths": tactical_strengths,
            "tactical_warnings": tactical_warnings,
            "tactical_reading": self._build_tactical_reading(
                tactical_status=tactical_status,
                tactical_score=tactical_score,
                offensive_volume_score=offensive_volume_score,
                offensive_depth_score=offensive_depth_score,
                false_pressure_risk=false_pressure_risk,
                minute=minute,
            ),
        }

    def _offensive_volume_score(
        self,
        total_dangerous: float,
        total_shots: float,
        total_shots_on: float,
        total_corners: float,
        total_xg: float,
        minute: int,
    ) -> float:
        """
        Mide volumen ofensivo real.

        No basta con posesión o presión genérica. Se combinan tiros, tiros al arco,
        corners, xG y ataques peligrosos.
        """

        if minute <= 0:
            return 0.0

        minute_factor = min(1.15, max(0.75, 90 / max(45, minute)))

        shots_score = min(100.0, total_shots * 4.2)
        sot_score = min(100.0, total_shots_on * 15.5)
        corner_score = min(100.0, total_corners * 9.0)
        xg_score = min(100.0, total_xg * 55.0)
        danger_score = min(100.0, total_dangerous * 2.1)

        score = (
            shots_score * 0.24
            + sot_score * 0.28
            + corner_score * 0.13
            + xg_score * 0.22
            + danger_score * 0.13
        )

        return clamp(score * minute_factor)

    def _deep_pressure_score(
        self,
        minute: int,
        total_dangerous: float,
        total_shots: float,
        total_shots_on: float,
        total_corners: float,
        total_xg: float,
    ) -> float:
        if minute <= 0:
            return 0.0

        dangerous_rate = total_dangerous / max(1, minute) * 90
        shot_rate = total_shots / max(1, minute) * 90
        shot_on_rate = total_shots_on / max(1, minute) * 90
        corner_rate = total_corners / max(1, minute) * 90

        score = (
            dangerous_rate * 0.35
            + shot_rate * 3.5
            + shot_on_rate * 7.5
            + corner_rate * 2.7
            + total_xg * 16.0
        )

        return clamp(score)

    def _offensive_depth_score(
        self,
        total_shots: float,
        total_shots_on: float,
        total_xg: float,
        total_dangerous: float,
        total_corners: float,
    ) -> float:
        """
        Profundidad ofensiva.

        Da más peso a tiros al arco y xG, porque son mejores señales de gol que
        ataques genéricos.
        """

        score = 0.0

        score += min(30.0, total_shots * 3.5)
        score += min(36.0, total_shots_on * 11.5)
        score += min(22.0, total_xg * 20.0)
        score += min(7.0, total_dangerous * 0.18)
        score += min(5.0, total_corners * 0.9)

        return clamp(score)

    def _recent_attack_proxy(
        self,
        minute: int,
        total_dangerous: float,
        total_shots: float,
        total_corners: float,
        total_shots_on: float,
    ) -> float:
        """
        Proxy de actividad reciente.

        No tenemos siempre eventos minuto a minuto, por eso se usa una tasa
        acumulada ajustada al minuto.
        """

        if minute <= 0:
            return 0.0

        activity_rate = (
            total_dangerous * 0.42
            + total_shots * 3.6
            + total_shots_on * 8.0
            + total_corners * 2.8
        ) / max(1, minute) * 90

        return clamp(activity_rate)

    def _false_pressure_risk(
        self,
        pressure_score: float,
        total_shots: float,
        total_shots_on: float,
        total_xg: float,
        offensive_depth_score: float,
        offensive_volume_score: float,
    ) -> float:
        """
        Detecta presión falsa.

        Ejemplo: mucho dominio territorial, pero sin tiros claros, sin xG,
        sin tiros al arco y sin profundidad.
        """

        risk = 0.0

        if pressure_score >= 65 and total_shots_on <= 1:
            risk += 28

        if pressure_score >= 65 and total_xg < 0.75:
            risk += 22

        if pressure_score >= 65 and total_shots < 7:
            risk += 15

        if offensive_depth_score < 42:
            risk += 18

        if offensive_volume_score < 38:
            risk += 17

        if total_shots_on == 0:
            risk += 12

        # Si sí hay volumen ofensivo real, reducimos el riesgo de falsa presión.
        if total_shots_on >= 3:
            risk -= 15

        if total_xg >= 1.0:
            risk -= 12

        if total_shots >= 12:
            risk -= 8

        return clamp(risk)

    def _data_quality_bonus(self, data_quality: str) -> float:
        if data_quality == "HIGH":
            return 4.0

        if data_quality == "MEDIUM":
            return 1.5

        return -3.0

    def _build_tactical_reading(
        self,
        tactical_status: str,
        tactical_score: float,
        offensive_volume_score: float,
        offensive_depth_score: float,
        false_pressure_risk: float,
        minute: int,
    ) -> str:
        return (
            f"{tactical_status} con score táctico {tactical_score:.0f}/100, "
            f"volumen ofensivo {offensive_volume_score:.0f}/100, "
            f"profundidad {offensive_depth_score:.0f}/100, "
            f"riesgo de presión falsa {false_pressure_risk:.0f}/100, "
            f"minuto {minute}."
        )
