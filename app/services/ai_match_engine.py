from typing import Dict, Any


class AIMatchEngine:
    """
    Motor IA V1
    Lee el estado del partido usando datos en vivo
    y devuelve una interpretación táctica + predictiva.
    """

    @staticmethod
    def analyze(match: Dict[str, Any]) -> Dict[str, Any]:
        minute = int(match.get("minute") or 0)

        home_score, away_score = AIMatchEngine._parse_score(match.get("score", "0-0"))

        home_stats = match.get("home_stats", {}) or {}
        away_stats = match.get("away_stats", {}) or {}

        home_possession = AIMatchEngine._safe_int(home_stats.get("possession"))
        away_possession = AIMatchEngine._safe_int(away_stats.get("possession"))

        home_shots = AIMatchEngine._safe_int(home_stats.get("shots"))
        away_shots = AIMatchEngine._safe_int(away_stats.get("shots"))

        home_shots_on_target = AIMatchEngine._safe_int(home_stats.get("shots_on_target"))
        away_shots_on_target = AIMatchEngine._safe_int(away_stats.get("shots_on_target"))

        home_corners = AIMatchEngine._safe_int(home_stats.get("corners"))
        away_corners = AIMatchEngine._safe_int(away_stats.get("corners"))

        home_dangerous = AIMatchEngine._safe_int(home_stats.get("dangerous_attacks"))
        away_dangerous = AIMatchEngine._safe_int(away_stats.get("dangerous_attacks"))

        home_red = AIMatchEngine._safe_int(home_stats.get("red_cards"))
        away_red = AIMatchEngine._safe_int(away_stats.get("red_cards"))

        home_xg = AIMatchEngine._safe_float(home_stats.get("xG"))
        away_xg = AIMatchEngine._safe_float(away_stats.get("xG"))

        total_goals = home_score + away_score
        total_shots = home_shots + away_shots
        total_shots_on_target = home_shots_on_target + away_shots_on_target
        total_corners = home_corners + away_corners
        total_dangerous = home_dangerous + away_dangerous
        total_xg = round(home_xg + away_xg, 2)
        total_red = home_red + away_red

        pressure_score = (
            total_shots_on_target * 3
            + total_dangerous * 0.8
            + total_corners * 1.2
            + total_xg * 12
        )

        rhythm_score = (
            total_shots * 0.8
            + total_shots_on_target * 2
            + total_dangerous * 0.5
            + total_corners
        )

        dominance = AIMatchEngine._detect_dominance(
            home_possession,
            away_possession,
            home_shots_on_target,
            away_shots_on_target,
            home_dangerous,
            away_dangerous,
            home_xg,
            away_xg
        )

        momentum_label = AIMatchEngine._detect_momentum(
            minute=minute,
            total_shots_on_target=total_shots_on_target,
            total_dangerous=total_dangerous,
            total_xg=total_xg,
            total_goals=total_goals
        )

        match_state, match_state_reason = AIMatchEngine._detect_match_state(
            minute=minute,
            total_goals=total_goals,
            total_shots_on_target=total_shots_on_target,
            total_dangerous=total_dangerous,
            total_xg=total_xg,
            total_red=total_red,
            momentum_label=momentum_label
        )

        goal_probability = AIMatchEngine._goal_probability(
            minute=minute,
            pressure_score=pressure_score,
            total_goals=total_goals,
            total_shots_on_target=total_shots_on_target,
            total_dangerous=total_dangerous,
            total_xg=total_xg
        )

        over_probability = AIMatchEngine._over_probability(
            minute=minute,
            total_goals=total_goals,
            pressure_score=pressure_score,
            total_xg=total_xg
        )

        result_prediction = AIMatchEngine._predict_result(
            home_score=home_score,
            away_score=away_score,
            home_xg=home_xg,
            away_xg=away_xg,
            home_dangerous=home_dangerous,
            away_dangerous=away_dangerous
        )

        winner_prediction = AIMatchEngine._predict_winner(
            home_score=home_score,
            away_score=away_score,
            dominance=dominance,
            home_xg=home_xg,
            away_xg=away_xg
        )

        risk_level = AIMatchEngine._risk_level(
            minute=minute,
            total_shots_on_target=total_shots_on_target,
            total_dangerous=total_dangerous,
            total_xg=total_xg,
            total_red=total_red,
            match_state=match_state
        )

        ai_score = AIMatchEngine._ai_score(
            minute=minute,
            total_goals=total_goals,
            total_shots_on_target=total_shots_on_target,
            total_dangerous=total_dangerous,
            total_xg=total_xg,
            momentum_label=momentum_label,
            match_state=match_state,
            total_red=total_red
        )

        return {
            "match_state": match_state,
            "match_state_reason": match_state_reason,
            "momentum_label": momentum_label,
            "dominance": dominance,
            "goal_probability": goal_probability,
            "over_probability": over_probability,
            "result_prediction": result_prediction,
            "winner_prediction": winner_prediction,
            "risk_level": risk_level,
            "ai_score": ai_score,
            "pressure_score": round(pressure_score, 2),
            "rhythm_score": round(rhythm_score, 2),
            "totals": {
                "goals": total_goals,
                "shots": total_shots,
                "shots_on_target": total_shots_on_target,
                "corners": total_corners,
                "dangerous_attacks": total_dangerous,
                "xg": total_xg,
                "red_cards": total_red,
            }
        }

    @staticmethod
    def _parse_score(score: str):
        try:
            clean = str(score).replace(" ", "").replace(":", "-")
            home, away = clean.split("-")
            return int(home), int(away)
        except Exception:
            return 0, 0

    @staticmethod
    def _safe_int(value):
        try:
            return int(float(value or 0))
        except Exception:
            return 0

    @staticmethod
    def _safe_float(value):
        try:
            return round(float(value or 0), 2)
        except Exception:
            return 0.0

    @staticmethod
    def _detect_dominance(home_possession, away_possession, home_sot, away_sot, home_dang, away_dang, home_xg, away_xg):
        home_power = home_possession * 0.2 + home_sot * 3 + home_dang * 0.8 + home_xg * 10
        away_power = away_possession * 0.2 + away_sot * 3 + away_dang * 0.8 + away_xg * 10

        if abs(home_power - away_power) < 4:
            return "EQUILIBRADO"
        return "LOCAL" if home_power > away_power else "VISITANTE"

    @staticmethod
    def _detect_momentum(minute, total_shots_on_target, total_dangerous, total_xg, total_goals):
        score = (
            total_shots_on_target * 3
            + total_dangerous * 0.7
            + total_xg * 10
            + total_goals * 2
        )

        if minute < 10 and score < 8:
            return "BAJO"
        if score >= 28:
            return "EXPLOSIVO"
        if score >= 20:
            return "ALTO"
        if score >= 12:
            return "ESTABLE"
        if score >= 7:
            return "BAJO"
        return "APAGADO"

    @staticmethod
    def _detect_match_state(minute, total_goals, total_shots_on_target, total_dangerous, total_xg, total_red, momentum_label):
        if total_red > 0 and minute < 75:
            return "INESTABLE", "Hay tarjeta roja y el partido puede romperse de forma impredecible"

        if minute >= 70 and total_goals >= 3 and total_shots_on_target >= 7:
            return "ABIERTO", "Marcador abierto con suficiente producción ofensiva"

        if total_xg >= 1.6 and total_dangerous >= 24:
            return "CALIENTE", "Hay presión ofensiva real y peligro constante"

        if momentum_label in ["EXPLOSIVO", "ALTO"]:
            return "ACTIVO", "El ritmo ofensivo es favorable"

        if total_shots_on_target <= 2 and total_dangerous <= 10 and minute >= 25:
            return "APAGADO", "Falta profundidad y ritmo"

        return "ESTABLE", "Partido relativamente controlado"

    @staticmethod
    def _goal_probability(minute, pressure_score, total_goals, total_shots_on_target, total_dangerous, total_xg):
        raw = (
            pressure_score
            + total_shots_on_target * 2
            + total_dangerous * 0.4
            + total_xg * 8
            + total_goals
        )

        if 20 <= minute <= 35:
            raw += 4
        if 55 <= minute <= 78:
            raw += 6
        if minute > 80:
            raw += 3

        return AIMatchEngine._clamp_percentage(raw)

    @staticmethod
    def _over_probability(minute, total_goals, pressure_score, total_xg):
        raw = total_goals * 18 + pressure_score * 0.9 + total_xg * 10

        if minute >= 55:
            raw += 8
        if minute >= 70:
            raw += 6

        return AIMatchEngine._clamp_percentage(raw)

    @staticmethod
    def _predict_result(home_score, away_score, home_xg, away_xg, home_dangerous, away_dangerous):
        predicted_home = home_score
        predicted_away = away_score

        if home_xg > away_xg + 0.35 or home_dangerous > away_dangerous + 6:
            predicted_home += 1

        if away_xg > home_xg + 0.35 or away_dangerous > home_dangerous + 6:
            predicted_away += 1

        return f"{predicted_home}-{predicted_away}"

    @staticmethod
    def _predict_winner(home_score, away_score, dominance, home_xg, away_xg):
        if home_score > away_score:
            if dominance == "VISITANTE" and abs(home_xg - away_xg) < 0.25:
                return "LOCAL AJUSTADO"
            return "LOCAL"

        if away_score > home_score:
            if dominance == "LOCAL" and abs(home_xg - away_xg) < 0.25:
                return "VISITANTE AJUSTADO"
            return "VISITANTE"

        if dominance == "LOCAL" and home_xg >= away_xg:
            return "LOCAL"
        if dominance == "VISITANTE" and away_xg >= home_xg:
            return "VISITANTE"
        return "EMPATE"

    @staticmethod
    def _risk_level(minute, total_shots_on_target, total_dangerous, total_xg, total_red, match_state):
        risk = 0

        if total_shots_on_target <= 2:
            risk += 3
        if total_dangerous <= 10:
            risk += 2
        if total_xg < 0.8:
            risk += 2
        if total_red > 0:
            risk += 2
        if minute < 15:
            risk += 1
        if match_state in ["APAGADO", "INESTABLE"]:
            risk += 2

        if risk >= 7:
            return "ALTO"
        if risk >= 4:
            return "MEDIO"
        return "BAJO"

    @staticmethod
    def _ai_score(minute, total_goals, total_shots_on_target, total_dangerous, total_xg, momentum_label, match_state, total_red):
        score = 40

        score += min(total_shots_on_target * 3, 18)
        score += min(int(total_dangerous * 0.4), 16)
        score += min(int(total_xg * 12), 14)
        score += min(total_goals * 3, 9)

        if 20 <= minute <= 35:
            score += 4
        if 55 <= minute <= 75:
            score += 6

        if momentum_label == "EXPLOSIVO":
            score += 10
        elif momentum_label == "ALTO":
            score += 6
        elif momentum_label == "ESTABLE":
            score += 2
        elif momentum_label == "APAGADO":
            score -= 8

        if match_state == "CALIENTE":
            score += 8
        elif match_state == "ACTIVO":
            score += 5
        elif match_state == "APAGADO":
            score -= 7
        elif match_state == "INESTABLE":
            score -= 10

        if total_red > 0:
            score -= 5

        return max(0, min(100, score))

    @staticmethod
    def _clamp_percentage(value):
        return max(1, min(99, int(round(value))))
