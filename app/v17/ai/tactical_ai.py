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


class TacticalAI:
    """
    Lee el comportamiento táctico del partido.

    No decide ENTER.
    Solo interpreta:
    - presión real
    - profundidad ofensiva
    - ritmo
    - tiros
    - corners
    - xG
    - necesidad ofensiva
    """

    def evaluate(self, match: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        minute = safe_int(match.get("api_minute"), 0)

        total_dangerous = safe_int(match.get("total_dangerous_attacks"), 0)
        total_shots = safe_int(match.get("total_shots"), 0)
        total_shots_on = safe_int(match.get("total_shots_on"), 0)
        total_corners = safe_int(match.get("total_corners"), 0)
        total_xg = safe_float(match.get("total_xg"), 0.0)

        pressure_score = safe_float(context.get("pressure_score"), 0.0)
        rhythm_score = safe_float(context.get("rhythm_score"), 0.0)
        goal_need_score = safe_float(context.get("goal_need_score"), 0.0)

        tactical_warnings: List[str] = []
        tactical_strengths: List[str] = []

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
        )

        recent_attack_proxy = self._recent_attack_proxy(
            minute=minute,
            total_dangerous=total_dangerous,
            total_shots=total_shots,
            total_corners=total_corners,
        )

        false_pressure_risk = self._false_pressure_risk(
            pressure_score=pressure_score,
            total_shots_on=total_shots_on,
            total_xg=total_xg,
            offensive_depth_score=offensive_depth_score,
        )

        tactical_score = (
            deep_pressure_score * 0.30
            + offensive_depth_score * 0.25
            + rhythm_score * 0.20
            + goal_need_score * 0.15
            + recent_attack_proxy * 0.10
        )

        tactical_score = max(0, min(100, tactical_score))

        if deep_pressure_score >= 70:
            tactical_strengths.append("DEEP_PRESSURE")

        if offensive_depth_score >= 70:
            tactical_strengths.append("OFFENSIVE_DEPTH")

        if rhythm_score >= 65:
            tactical_strengths.append("RHYTHM_ALIVE")

        if goal_need_score >= 60:
            tactical_strengths.append("SCORE_NEED")

        if recent_attack_proxy >= 65:
            tactical_strengths.append("RECENT_ACTIVITY")

        if false_pressure_risk >= 70:
            tactical_warnings.append("FALSE_PRESSURE_RISK")

        if total_shots_on <= 1 and minute >= 55:
            tactical_warnings.append("LOW_SHOTS_ON_TARGET")

        if offensive_depth_score < 40 and minute >= 60:
            tactical_warnings.append("NO_OFFENSIVE_DEPTH")

        if rhythm_score < 35 and minute >= 65:
            tactical_warnings.append("LOW_RHYTHM")

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
            "recent_attack_proxy": round(recent_attack_proxy, 2),
            "false_pressure_risk": round(false_pressure_risk, 2),
            "tactical_strengths": tactical_strengths,
            "tactical_warnings": tactical_warnings,
        }

    def _deep_pressure_score(
        self,
        minute: int,
        total_dangerous: int,
        total_shots: int,
        total_shots_on: int,
        total_corners: int,
        total_xg: float,
    ) -> float:
        if minute <= 0:
            return 0.0

        dangerous_rate = total_dangerous / max(1, minute) * 90
        shot_rate = total_shots / max(1, minute) * 90
        shot_on_rate = total_shots_on / max(1, minute) * 90
        corner_rate = total_corners / max(1, minute) * 90

        score = (
            dangerous_rate * 0.45
            + shot_rate * 4.0
            + shot_on_rate * 8.0
            + corner_rate * 3.0
            + total_xg * 18.0
        )

        return max(0, min(100, score))

    def _offensive_depth_score(
        self,
        total_shots: int,
        total_shots_on: int,
        total_xg: float,
        total_dangerous: int,
    ) -> float:
        score = 0.0

        score += min(35, total_shots * 4)
        score += min(35, total_shots_on * 10)
        score += min(20, total_xg * 18)
        score += min(10, total_dangerous * 0.2)

        return max(0, min(100, score))

    def _recent_attack_proxy(
        self,
        minute: int,
        total_dangerous: int,
        total_shots: int,
        total_corners: int,
    ) -> float:
        if minute <= 0:
            return 0.0

        activity_rate = (
            total_dangerous * 0.5
            + total_shots * 4
            + total_corners * 3
        ) / max(1, minute) * 90

        return max(0, min(100, activity_rate))

    def _false_pressure_risk(
        self,
        pressure_score: float,
        total_shots_on: int,
        total_xg: float,
        offensive_depth_score: float,
    ) -> float:
        risk = 0.0

        if pressure_score >= 65 and total_shots_on <= 1:
            risk += 35

        if pressure_score >= 65 and total_xg < 0.8:
            risk += 25

        if offensive_depth_score < 45:
            risk += 25

        if total_shots_on == 0:
            risk += 15

        return max(0, min(100, risk))
