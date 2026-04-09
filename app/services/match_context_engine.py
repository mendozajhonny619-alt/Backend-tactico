class MatchContextEngine:
    @staticmethod
    def analyze(match):
        home_stats = match.get("home_stats", {}) or {}
        away_stats = match.get("away_stats", {}) or {}

        home_shots = MatchContextEngine._to_int(home_stats.get("shots", 0))
        away_shots = MatchContextEngine._to_int(away_stats.get("shots", 0))

        home_sot = MatchContextEngine._to_int(home_stats.get("shots_on_target", 0))
        away_sot = MatchContextEngine._to_int(away_stats.get("shots_on_target", 0))

        home_corners = MatchContextEngine._to_int(home_stats.get("corners", 0))
        away_corners = MatchContextEngine._to_int(away_stats.get("corners", 0))

        home_danger = MatchContextEngine._to_int(home_stats.get("dangerous_attacks", 0))
        away_danger = MatchContextEngine._to_int(away_stats.get("dangerous_attacks", 0))

        home_xg = MatchContextEngine._to_float(home_stats.get("xG", 0))
        away_xg = MatchContextEngine._to_float(away_stats.get("xG", 0))

        home_red = MatchContextEngine._to_int(home_stats.get("red_cards", 0))
        away_red = MatchContextEngine._to_int(away_stats.get("red_cards", 0))

        minuto = MatchContextEngine._to_int(match.get("minute", 0))
        score = str(match.get("score", "0-0") or "0-0")

        home_goals, away_goals = MatchContextEngine._parse_score(score)

        total_goals = home_goals + away_goals
        total_shots = home_shots + away_shots
        total_sot = home_sot + away_sot
        total_corners = home_corners + away_corners
        total_danger = home_danger + away_danger
        total_xg = round(home_xg + away_xg, 2)
        total_red = home_red + away_red

        possession_home = MatchContextEngine._to_int(home_stats.get("possession", 50))
        possession_away = MatchContextEngine._to_int(away_stats.get("possession", 50))

        pressure_index = MatchContextEngine._calc_pressure_index(
            total_sot=total_sot,
            total_danger=total_danger,
            total_corners=total_corners,
            total_xg=total_xg,
            total_shots=total_shots
        )

        rhythm_index = MatchContextEngine._calc_rhythm_index(
            minute=minuto,
            total_shots=total_shots,
            total_sot=total_sot,
            total_danger=total_danger,
            total_corners=total_corners
        )

        dominance_delta = MatchContextEngine._calc_dominance_delta(
            home_sot=home_sot,
            away_sot=away_sot,
            home_danger=home_danger,
            away_danger=away_danger,
            home_xg=home_xg,
            away_xg=away_xg,
            home_corners=home_corners,
            away_corners=away_corners,
            home_possession=possession_home,
            away_possession=possession_away
        )

        dominance = MatchContextEngine._classify_dominance(dominance_delta)

        attack_side = MatchContextEngine._classify_attack_side(
            dominance_delta=dominance_delta,
            home_danger=home_danger,
            away_danger=away_danger,
            home_sot=home_sot,
            away_sot=away_sot
        )

        game_quality = MatchContextEngine._classify_game_quality(
            total_sot=total_sot,
            total_danger=total_danger,
            total_xg=total_xg,
            pressure_index=pressure_index,
            rhythm_index=rhythm_index
        )

        context_state, context_reason = MatchContextEngine._classify_context_state(
            minute=minuto,
            total_sot=total_sot,
            total_danger=total_danger,
            total_xg=total_xg,
            pressure_index=pressure_index,
            rhythm_index=rhythm_index,
            total_goals=total_goals
        )

        goal_window = MatchContextEngine._goal_window_score(
            minute=minuto,
            pressure_index=pressure_index,
            total_sot=total_sot,
            total_danger=total_danger,
            total_xg=total_xg,
            total_goals=total_goals
        )

        over_window = MatchContextEngine._over_window_score(
            minute=minuto,
            total_goals=total_goals,
            total_sot=total_sot,
            total_danger=total_danger,
            total_xg=total_xg
        )

        data_quality = MatchContextEngine._classify_data_quality(
            total_shots=total_shots,
            total_sot=total_sot,
            total_danger=total_danger,
            total_xg=total_xg,
            minute=minuto
        )

        red_alert = MatchContextEngine._classify_red_alert(
            total_red=total_red,
            minute=minuto,
            total_goals=total_goals
        )

        return {
            "pressure_index": pressure_index,
            "rhythm_index": rhythm_index,
            "dominance_delta": round(dominance_delta, 2),
            "dominance": dominance,
            "attack_side": attack_side,
            "game_quality": game_quality,
            "context_state": context_state,
            "context_reason": context_reason,
            "goal_window_score": goal_window,
            "over_window_score": over_window,
            "data_quality": data_quality,
            "red_alert": red_alert,
            "totals": {
                "goals": total_goals,
                "shots": total_shots,
                "shots_on_target": total_sot,
                "corners": total_corners,
                "dangerous_attacks": total_danger,
                "xg": total_xg,
                "red_cards": total_red
            }
        }

    @staticmethod
    def _calc_pressure_index(total_sot, total_danger, total_corners, total_xg, total_shots):
        score = 0
        score += min(total_sot * 10, 30)
        score += min(total_danger * 0.8, 26)
        score += min(total_corners * 2, 12)
        score += min(total_xg * 14, 22)
        score += min(total_shots * 1.2, 10)
        return round(min(score, 100), 1)

    @staticmethod
    def _calc_rhythm_index(minute, total_shots, total_sot, total_danger, total_corners):
        minute = max(minute, 1)

        score = 0
        score += min((total_shots / minute) * 130, 24)
        score += min((total_sot / minute) * 260, 24)
        score += min((total_danger / minute) * 125, 24)
        score += min((total_corners / minute) * 90, 10)

        if 20 <= minute <= 45:
            score += 8
        elif 55 <= minute <= 80:
            score += 10
        elif 81 <= minute <= 88:
            score += 6

        return round(min(score, 100), 1)

    @staticmethod
    def _calc_dominance_delta(
        home_sot,
        away_sot,
        home_danger,
        away_danger,
        home_xg,
        away_xg,
        home_corners,
        away_corners,
        home_possession,
        away_possession
    ):
        return (
            (home_sot - away_sot) * 2.2
            + (home_danger - away_danger) * 0.35
            + (home_xg - away_xg) * 9
            + (home_corners - away_corners) * 0.7
            + (home_possession - away_possession) * 0.12
        )

    @staticmethod
    def _classify_dominance(delta):
        if delta >= 10:
            return "LOCAL"
        if delta <= -10:
            return "VISITANTE"
        return "EQUILIBRADO"

    @staticmethod
    def _classify_attack_side(dominance_delta, home_danger, away_danger, home_sot, away_sot):
        if dominance_delta >= 8 or (home_danger > away_danger and home_sot >= away_sot):
            return "LOCAL"
        if dominance_delta <= -8 or (away_danger > home_danger and away_sot >= home_sot):
            return "VISITANTE"
        return "MIXTO"

    @staticmethod
    def _classify_game_quality(total_sot, total_danger, total_xg, pressure_index, rhythm_index):
        if total_sot >= 6 and total_danger >= 25 and total_xg >= 1.8:
            return "ALTA"
        if pressure_index >= 55 and rhythm_index >= 45:
            return "ALTA"
        if total_sot >= 3 and total_danger >= 12 and total_xg >= 0.8:
            return "MEDIA"
        return "BAJA"

    @staticmethod
    def _classify_context_state(minute, total_sot, total_danger, total_xg, pressure_index, rhythm_index, total_goals):
        if pressure_index >= 70 and rhythm_index >= 55 and total_sot >= 4:
            return "EXPLOSIVO", "Presión y ritmo muy altos con amenaza clara de gol"

        if pressure_index >= 55 and total_danger >= 16 and total_xg >= 1.0:
            return "CALIENTE", "El partido muestra presión sostenida y generación ofensiva real"

        if total_xg >= 1.0 and total_sot >= 2 and total_goals <= 2:
            return "ABIERTO", "Hay espacio y condiciones para más goles"

        if pressure_index >= 35 or rhythm_index >= 35:
            return "ACTIVO", "Partido vivo con señales ofensivas moderadas"

        if minute > 20 and total_sot == 0 and total_danger < 8 and total_xg < 0.45:
            return "MUERTO", "Baja producción ofensiva y poco ritmo"

        return "CONTROLADO", "Partido estable sin señales extremas"

    @staticmethod
    def _goal_window_score(minute, pressure_index, total_sot, total_danger, total_xg, total_goals):
        score = 0
        score += min(pressure_index * 0.45, 32)
        score += min(total_sot * 6, 24)
        score += min(total_danger * 0.5, 18)
        score += min(total_xg * 14, 18)

        if 25 <= minute <= 45:
            score += 8
        if 55 <= minute <= 80:
            score += 10
        if 75 <= minute <= 88:
            score += 8

        if total_goals >= 1:
            score += 5

        return round(min(score, 100), 1)

    @staticmethod
    def _over_window_score(minute, total_goals, total_sot, total_danger, total_xg):
        score = 0
        score += min(total_goals * 20, 40)
        score += min(total_sot * 5, 20)
        score += min(total_danger * 0.45, 18)
        score += min(total_xg * 13, 18)

        if minute >= 30:
            score += 6
        if minute >= 60:
            score += 8

        return round(min(score, 100), 1)

    @staticmethod
    def _classify_data_quality(total_shots, total_sot, total_danger, total_xg, minute):
        filled = 0

        if total_shots > 0:
            filled += 1
        if total_sot > 0:
            filled += 1
        if total_danger > 0:
            filled += 1
        if total_xg > 0:
            filled += 1
        if minute > 0:
            filled += 1

        if filled >= 5:
            return "ALTA"
        if filled >= 3:
            return "MEDIA"
        return "BAJA"

    @staticmethod
    def _classify_red_alert(total_red, minute, total_goals):
        if total_red >= 2:
            return "ALTA"
        if total_red == 1 and minute >= 60:
            return "MEDIA"
        if total_red == 1:
            return "BAJA"
        if total_goals >= 4:
            return "MEDIA"
        return "NINGUNA"

    @staticmethod
    def _parse_score(score):
        try:
            parts = score.split("-")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        except Exception:
            pass
        return 0, 0

    @staticmethod
    def _to_int(value, default=0):
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.replace("%", "").strip()
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _to_float(value, default=0.0):
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.replace("%", "").strip()
            return float(value)
        except Exception:
            return default
