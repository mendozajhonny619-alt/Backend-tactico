from __future__ import annotations

from typing import Any, Dict


class MatchContextEngine:
    """
    Convierte stats crudos del partido en contexto táctico-operativo.
    """

    def build(self, match: Dict[str, Any]) -> Dict[str, Any]:
        stats = self._extract_stats(match)

        home_shots = stats["home_shots"]
        away_shots = stats["away_shots"]
        home_sot = stats["home_shots_on_target"]
        away_sot = stats["away_shots_on_target"]
        home_xg = stats["home_xg"]
        away_xg = stats["away_xg"]
        home_danger = stats["home_dangerous_attacks"]
        away_danger = stats["away_dangerous_attacks"]
        home_poss = stats["home_possession"]
        away_poss = stats["away_possession"]
        home_corners = stats["home_corners"]
        away_corners = stats["away_corners"]

        total_shots = home_shots + away_shots
        total_sot = home_sot + away_sot
        total_xg = home_xg + away_xg
        total_danger = home_danger + away_danger
        total_corners = home_corners + away_corners
        possession_diff = home_poss - away_poss

        minute = self._extract_minute(match)
        home_score = self._extract_score(match, side="home")
        away_score = self._extract_score(match, side="away")
        score_diff = home_score - away_score

        data_quality = self._calculate_data_quality(
            shots=total_shots,
            shots_on_target=total_sot,
            xg=total_xg,
            dangerous_attacks=total_danger,
            corners=total_corners,
            home_possession=home_poss,
            away_possession=away_poss,
        )

        pressure_index = self._calculate_pressure_index(
            shots_on_target=total_sot,
            dangerous_attacks=total_danger,
            xg=total_xg,
            shots=total_shots,
            corners=total_corners,
            possession_home=home_poss,
            possession_away=away_poss,
        )

        rhythm_index = self._calculate_rhythm_index(
            shots=total_shots,
            dangerous_attacks=total_danger,
            shots_on_target=total_sot,
            corners=total_corners,
        )

        # Ayuda a detectar partidos cargados, pero sin inflar señales muy tarde.
        recent_pressure_boost = 0.0

        if total_sot >= 4 and 25 <= minute <= 72:
            recent_pressure_boost += 2.5

        if total_danger >= 25 and 25 <= minute <= 72:
            recent_pressure_boost += 2.0

        if total_xg >= 1.2 and minute <= 72:
            recent_pressure_boost += 2.5

        pressure_index += recent_pressure_boost

        dominance = self._calculate_dominance(
            possession_diff=possession_diff,
            home_danger=home_danger,
            away_danger=away_danger,
            home_xg=home_xg,
            away_xg=away_xg,
            home_sot=home_sot,
            away_sot=away_sot,
            home_shots=home_shots,
            away_shots=away_shots,
        )

        attack_side = self._calculate_attack_side(
            home_danger=home_danger,
            away_danger=away_danger,
            home_sot=home_sot,
            away_sot=away_sot,
            home_corners=home_corners,
            away_corners=away_corners,
        )

        game_quality = self._calculate_game_quality(
            shots=total_shots,
            shots_on_target=total_sot,
            xg=total_xg,
            dangerous_attacks=total_danger,
            corners=total_corners,
            home_possession=home_poss,
            away_possession=away_poss,
        )

        context_state = self._calculate_context_state(
            pressure=pressure_index,
            rhythm=rhythm_index,
            quality=game_quality,
        )

        goal_window_score = self._calculate_goal_window_score(
            pressure=pressure_index,
            rhythm=rhythm_index,
            xg=total_xg,
            shots_on_target=total_sot,
            corners=total_corners,
        )

        over_window_score = self._calculate_over_window_score(
            shots_on_target=total_sot,
            dangerous_attacks=total_danger,
            xg=total_xg,
            shots=total_shots,
            corners=total_corners,
        )

        goal_window_score += recent_pressure_boost * 1.2
        over_window_score += recent_pressure_boost

        red_alert = self._calculate_red_alert(
            data_quality=data_quality,
            pressure=pressure_index,
            rhythm=rhythm_index,
            xg=total_xg,
            context_state=context_state,
            shots_on_target=total_sot,
        )

        return {
            "pressure_index": round(pressure_index, 2),
            "rhythm_index": round(rhythm_index, 2),
            "dominance": dominance,
            "attack_side": attack_side,
            "game_quality": game_quality,
            "context_state": context_state,
            "goal_window_score": round(goal_window_score, 2),
            "over_window_score": round(over_window_score, 2),
            "data_quality": data_quality,
            "red_alert": red_alert,

            "home_pressure": round(
                self._side_pressure(home_sot, home_danger, home_xg, home_shots, home_corners), 2
            ),
            "away_pressure": round(
                self._side_pressure(away_sot, away_danger, away_xg, away_shots, away_corners), 2
            ),

            "shots": round(total_shots, 2),
            "shots_on_target": round(total_sot, 2),
            "xg": round(total_xg, 2),
            "dangerous_attacks": round(total_danger, 2),
            "corners": round(total_corners, 2),

            "home_shots": round(home_shots, 2),
            "away_shots": round(away_shots, 2),
            "home_shots_on_target": round(home_sot, 2),
            "away_shots_on_target": round(away_sot, 2),
            "home_xg": round(home_xg, 2),
            "away_xg": round(away_xg, 2),

            "home_score": home_score,
            "away_score": away_score,
            "score_diff": score_diff,

            "minute": minute,
        }

    def _calculate_pressure_index(
        self,
        shots_on_target: float,
        dangerous_attacks: float,
        xg: float,
        shots: float,
        corners: float,
        possession_home: float,
        possession_away: float,
    ) -> float:
        possession_factor = 0.0
        if possession_home > 0 and possession_away > 0:
            possession_factor = ((possession_home + possession_away) / 100.0) * 2.0

        return (
            (shots_on_target * 2.5)
            + (dangerous_attacks * 0.22)
            + (xg * 11.5)
            + (shots * 0.36)
            + (corners * 0.80)
            + possession_factor
        )

    def _calculate_rhythm_index(
        self,
        shots: float,
        dangerous_attacks: float,
        shots_on_target: float,
        corners: float,
    ) -> float:
        return (
            (shots * 0.85)
            + (dangerous_attacks * 0.14)
            + (shots_on_target * 1.25)
            + (corners * 0.65)
        )

    def _calculate_goal_window_score(
        self,
        pressure: float,
        rhythm: float,
        xg: float,
        shots_on_target: float,
        corners: float,
    ) -> float:
        return (
            (pressure * 0.42)
            + (rhythm * 0.28)
            + (xg * 9.5)
            + (shots_on_target * 1.55)
            + (corners * 0.50)
        )

    def _calculate_over_window_score(
        self,
        shots_on_target: float,
        dangerous_attacks: float,
        xg: float,
        shots: float,
        corners: float,
    ) -> float:
        return (
            (shots_on_target * 2.85)
            + (dangerous_attacks * 0.30)
            + (xg * 10.5)
            + (shots * 0.30)
            + (corners * 0.70)
        )

    def _calculate_data_quality(
        self,
        shots: float,
        shots_on_target: float,
        xg: float,
        dangerous_attacks: float,
        corners: float,
        home_possession: float,
        away_possession: float,
    ) -> str:
        has_possession = home_possession > 0 and away_possession > 0
        signals = 0

        if shots > 0:
            signals += 1
        if shots_on_target > 0:
            signals += 1
        if xg > 0:
            signals += 1
        if dangerous_attacks > 0:
            signals += 1
        if corners > 0:
            signals += 1
        if has_possession:
            signals += 1

        if signals >= 4:
            return "HIGH"
        if signals >= 2:
            return "MEDIUM"
        return "LOW"

    def _calculate_game_quality(
        self,
        shots: float,
        shots_on_target: float,
        xg: float,
        dangerous_attacks: float,
        corners: float,
        home_possession: float,
        away_possession: float,
    ) -> str:
        possession_bonus = 2.0 if (home_possession > 0 and away_possession > 0) else 0.0

        score = (
            shots
            + (shots_on_target * 2.25)
            + (dangerous_attacks * 0.14)
            + (xg * 8.5)
            + (corners * 0.75)
            + possession_bonus
        )

        if score < 14:
            return "LOW"
        if score < 30:
            return "MEDIUM"
        return "HIGH"

    def _calculate_context_state(
        self,
        pressure: float,
        rhythm: float,
        quality: str,
    ) -> str:
        if quality == "LOW" and pressure < 6 and rhythm < 6:
            return "MUERTO"

        if pressure < 8 and rhythm < 7:
            return "FRIO"

        if pressure < 14 and rhythm < 10:
            return "CONTROLADO"

        if pressure < 16:
            return "TIBIO"

        if pressure < 25:
            return "CALIENTE"

        return "MUY_CALIENTE"

    def _calculate_dominance(
        self,
        possession_diff: float,
        home_danger: float,
        away_danger: float,
        home_xg: float,
        away_xg: float,
        home_sot: float,
        away_sot: float,
        home_shots: float,
        away_shots: float,
    ) -> str:
        home_score = (
            (home_danger * 0.28)
            + (home_xg * 10.0)
            + (home_sot * 2.2)
            + (home_shots * 0.25)
        )
        away_score = (
            (away_danger * 0.28)
            + (away_xg * 10.0)
            + (away_sot * 2.2)
            + (away_shots * 0.25)
        )

        home_score += max(possession_diff, 0) * 0.12
        away_score += max(-possession_diff, 0) * 0.12

        diff = home_score - away_score

        if diff > 5:
            return "HOME"
        if diff < -5:
            return "AWAY"
        return "BALANCED"

    def _calculate_attack_side(
        self,
        home_danger: float,
        away_danger: float,
        home_sot: float,
        away_sot: float,
        home_corners: float,
        away_corners: float,
    ) -> str:
        home_attack = (home_danger * 0.42) + (home_sot * 2.0) + (home_corners * 0.65)
        away_attack = (away_danger * 0.42) + (away_sot * 2.0) + (away_corners * 0.65)

        diff = home_attack - away_attack

        if diff > 4:
            return "HOME"
        if diff < -4:
            return "AWAY"
        return "BALANCED"

    def _calculate_red_alert(
        self,
        data_quality: str,
        pressure: float,
        rhythm: float,
        xg: float,
        context_state: str,
        shots_on_target: float,
    ) -> bool:
        if data_quality == "LOW":
            return False

        if context_state == "MUY_CALIENTE" and pressure >= 34 and rhythm >= 16:
            return True

        if pressure >= 38 and xg >= 1.1:
            return True

        if shots_on_target >= 6 and pressure >= 28:
            return True

        return False

    def _side_pressure(
        self,
        shots_on_target: float,
        dangerous_attacks: float,
        xg: float,
        shots: float,
        corners: float,
    ) -> float:
        return (
            (shots_on_target * 2.2)
            + (dangerous_attacks * 0.22)
            + (xg * 10.0)
            + (shots * 0.25)
            + (corners * 0.55)
        )

    def _extract_stats(self, match: Dict[str, Any]) -> Dict[str, float]:
        home = match.get("home_stats", {}) if isinstance(match.get("home_stats"), dict) else {}
        away = match.get("away_stats", {}) if isinstance(match.get("away_stats"), dict) else {}

        if home or away:
            return {
                "home_shots": self._pick_stat(home, ["shots", "total_shots", "attempts_on_goal", "tiros"]),
                "away_shots": self._pick_stat(away, ["shots", "total_shots", "attempts_on_goal", "tiros"]),
                "home_shots_on_target": self._pick_stat(home, ["shots_on_target", "on_target", "shots_target", "tiros_a_target", "tiros_a_puerta"]),
                "away_shots_on_target": self._pick_stat(away, ["shots_on_target", "on_target", "shots_target", "tiros_a_target", "tiros_a_puerta"]),
                "home_xg": self._pick_stat(home, ["xg", "xG", "expected_goals"]),
                "away_xg": self._pick_stat(away, ["xg", "xG", "expected_goals"]),
                "home_dangerous_attacks": self._pick_stat(home, ["dangerous_attacks", "danger_attacks", "attacks_dangerous", "ataques_peligrosos"]),
                "away_dangerous_attacks": self._pick_stat(away, ["dangerous_attacks", "danger_attacks", "attacks_dangerous", "ataques_peligrosos"]),
                "home_possession": self._pick_stat(home, ["possession", "ball_possession", "posesion"]),
                "away_possession": self._pick_stat(away, ["possession", "ball_possession", "posesion"]),
                "home_corners": self._pick_stat(home, ["corners", "corner_kicks", "corners_kicks", "saques_de_esquina"]),
                "away_corners": self._pick_stat(away, ["corners", "corner_kicks", "corners_kicks", "saques_de_esquina"]),
            }

        return {
            "home_shots": self._pick_stat(match, ["home_shots", "shots_home", "tiros_local"]),
            "away_shots": self._pick_stat(match, ["away_shots", "shots_away", "tiros_visitante"]),
            "home_shots_on_target": self._pick_stat(match, ["home_shots_on_target", "shots_on_target_home", "tiros_a_puerta_local"]),
            "away_shots_on_target": self._pick_stat(match, ["away_shots_on_target", "shots_on_target_away", "tiros_a_puerta_visitante"]),
            "home_xg": self._pick_stat(match, ["home_xg", "xg_home", "xG_home"]),
            "away_xg": self._pick_stat(match, ["away_xg", "xg_away", "xG_away"]),
            "home_dangerous_attacks": self._pick_stat(match, ["home_dangerous_attacks", "dangerous_attacks_home", "ataques_peligrosos_local"]),
            "away_dangerous_attacks": self._pick_stat(match, ["away_dangerous_attacks", "dangerous_attacks_away", "ataques_peligrosos_visitante"]),
            "home_possession": self._pick_stat(match, ["home_possession", "possession_home", "posesion_local"]),
            "away_possession": self._pick_stat(match, ["away_possession", "possession_away", "posesion_visitante"]),
            "home_corners": self._pick_stat(match, ["home_corners", "corners_home", "corners_local"]),
            "away_corners": self._pick_stat(match, ["away_corners", "corners_away", "corners_visitante"]),
        }

    def _pick_stat(self, source: Dict[str, Any], keys: list[str]) -> float:
        for key in keys:
            if key in source:
                return self._safe_float(source.get(key))
        return 0.0

    def _extract_score(self, match: Dict[str, Any], side: str) -> int:
        if side == "home":
            raw = (
                match.get("home_score")
                or match.get("marcador_local")
                or match.get("score_home")
                or 0
            )
        else:
            raw = (
                match.get("away_score")
                or match.get("marcador_visitante")
                or match.get("score_away")
                or 0
            )

        try:
            return int(float(raw or 0))
        except (TypeError, ValueError):
            return 0

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or match.get("minuto")
            or 0
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
