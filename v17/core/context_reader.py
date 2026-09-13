from __future__ import annotations

from typing import Any, Dict, List

from app.v17.core.constants import CONMEBOL_KEYWORDS, LEAGUE_EXTRA_CONFIRMATION_MINUTE


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


class ContextReader:
    """
    Lectura contextual inicial.

    Define:
    - necesidad del marcador
    - posible OVER
    - posible UNDER
    - liga sensible
    - contexto CONMEBOL
    - tendencia de cierre
    """

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        minute = safe_int(match.get("api_minute"), 0)
        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score

        league = str(match.get("league") or "").upper()
        country = str(match.get("country") or "").upper()
        league_text = f"{league} {country}"

        is_conmebol = any(keyword in league_text for keyword in CONMEBOL_KEYWORDS)
        conmebol_late = is_conmebol and minute >= LEAGUE_EXTRA_CONFIRMATION_MINUTE

        score_diff = abs(home_score - away_score)
        is_draw = home_score == away_score
        one_goal_game = score_diff == 1
        comfortable_score = score_diff >= 2

        total_dangerous = safe_int(match.get("total_dangerous_attacks"), 0)
        total_shots = safe_int(match.get("total_shots"), 0)
        total_shots_on = safe_int(match.get("total_shots_on"), 0)
        total_corners = safe_int(match.get("total_corners"), 0)
        total_xg = safe_float(match.get("total_xg"), 0.0)

        offensive_activity = (
            total_dangerous * 0.35
            + total_shots * 2.0
            + total_shots_on * 3.0
            + total_corners * 1.2
            + total_xg * 10.0
        )

        goal_need_score = 0

        if is_draw:
            goal_need_score += 20

        if one_goal_game:
            goal_need_score += 15

        if minute >= 60 and (is_draw or one_goal_game):
            goal_need_score += 15

        if minute >= 75 and (is_draw or one_goal_game):
            goal_need_score += 10

        if comfortable_score:
            goal_need_score -= 15

        if total_goals >= 3:
            goal_need_score += 10

        if total_goals == 0 and minute >= 60:
            goal_need_score -= 5

        goal_need_score = max(0, min(100, goal_need_score))

        pressure_score = max(0, min(100, offensive_activity))
        rhythm_score = self._estimate_rhythm(minute, total_shots, total_dangerous, total_corners)

        score_hold_probability = self._estimate_score_hold(
            minute=minute,
            score_diff=score_diff,
            total_shots_on=total_shots_on,
            total_xg=total_xg,
            pressure_score=pressure_score,
        )

        under_transition_score = self._estimate_under_transition(
            minute=minute,
            pressure_score=pressure_score,
            rhythm_score=rhythm_score,
            total_shots_on=total_shots_on,
            score_hold_probability=score_hold_probability,
        )

        over_context_score = (
            pressure_score * 0.35
            + rhythm_score * 0.25
            + goal_need_score * 0.25
            + min(100, total_shots_on * 15) * 0.15
        )

        under_context_score = (
            score_hold_probability * 0.45
            + under_transition_score * 0.35
            + max(0, 100 - pressure_score) * 0.20
        )

        context_warnings: List[str] = []

        if conmebol_late:
            context_warnings.append("CONMEBOL_EXTRA_CONFIRMATION")

        if comfortable_score and minute >= 60:
            context_warnings.append("SCORE_HOLD_RISK")

        if total_shots_on <= 1 and minute >= 55:
            context_warnings.append("LOW_SHOTS_ON_TARGET")

        if pressure_score < 35 and minute >= 60:
            context_warnings.append("LOW_REAL_PRESSURE")

        if under_transition_score >= 70:
            context_warnings.append("UNDER_TRANSITION_ACTIVE")

        if over_context_score >= 70:
            main_category = "OVER_CANDIDATE"
        elif under_context_score >= 65:
            main_category = "UNDER_CANDIDATE"
        elif pressure_score >= 45 or rhythm_score >= 45:
            main_category = "OBSERVE"
        else:
            main_category = "NO_BET"

        probable_score = self._estimate_probable_score(
            home_score=home_score,
            away_score=away_score,
            over_context_score=over_context_score,
            under_context_score=under_context_score,
            minute=minute,
        )

        return {
            "context_category": main_category,
            "is_conmebol": is_conmebol,
            "conmebol_late": conmebol_late,
            "goal_need_score": round(goal_need_score, 2),
            "pressure_score": round(pressure_score, 2),
            "rhythm_score": round(rhythm_score, 2),
            "over_context_score": round(over_context_score, 2),
            "under_context_score": round(under_context_score, 2),
            "score_hold_probability": round(score_hold_probability, 2),
            "under_transition_score": round(under_transition_score, 2),
            "context_warnings": context_warnings,
            "probable_score": probable_score,
        }

    def _estimate_rhythm(
        self,
        minute: int,
        total_shots: int,
        total_dangerous: int,
        total_corners: int,
    ) -> float:
        if minute <= 0:
            return 0.0

        shots_rate = total_shots / max(1, minute) * 90
        dangerous_rate = total_dangerous / max(1, minute) * 90
        corners_rate = total_corners / max(1, minute) * 90

        rhythm = shots_rate * 3.0 + dangerous_rate * 0.6 + corners_rate * 2.0
        return max(0, min(100, rhythm))

    def _estimate_score_hold(
        self,
        minute: int,
        score_diff: int,
        total_shots_on: int,
        total_xg: float,
        pressure_score: float,
    ) -> float:
        score = 20.0

        if minute >= 60:
            score += 15

        if minute >= 75:
            score += 15

        if score_diff >= 1:
            score += 15

        if score_diff >= 2:
            score += 15

        if total_shots_on <= 2:
            score += 10

        if total_xg < 1.0:
            score += 10

        if pressure_score < 40:
            score += 15

        return max(0, min(100, score))

    def _estimate_under_transition(
        self,
        minute: int,
        pressure_score: float,
        rhythm_score: float,
        total_shots_on: int,
        score_hold_probability: float,
    ) -> float:
        score = 0.0

        if minute >= 55:
            score += 15

        if minute >= 70:
            score += 15

        if pressure_score < 45:
            score += 20

        if rhythm_score < 45:
            score += 20

        if total_shots_on <= 2:
            score += 15

        if score_hold_probability >= 65:
            score += 20

        return max(0, min(100, score))

    def _estimate_probable_score(
        self,
        home_score: int,
        away_score: int,
        over_context_score: float,
        under_context_score: float,
        minute: int,
    ) -> Dict[str, Any]:
        current = f"{home_score}-{away_score}"

        if over_context_score >= 75 and minute < 85:
            if home_score >= away_score:
                offensive = f"{home_score + 1}-{away_score}"
            else:
                offensive = f"{home_score}-{away_score + 1}"
        elif over_context_score >= 65 and minute < 80:
            offensive = "1 gol más posible"
        else:
            offensive = current

        if under_context_score >= 70:
            probable = current
            reading = "riesgo de conservación del marcador"
        elif over_context_score >= 70:
            probable = offensive
            reading = "posible gol adicional si se confirma presión"
        else:
            probable = current
            reading = "sin ventaja clara para forzar entrada"

        return {
            "current_score": current,
            "probable_score": probable,
            "offensive_alternative": offensive,
            "reading": reading,
      }
