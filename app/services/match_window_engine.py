class MatchWindowEngine:
    """
    Motor de ventanas inteligentes por minuto.

    Objetivo:
    - No leer todos los minutos igual
    - Cambiar exigencia según fase del partido
    - Dar preferencia distinta a OVER y UNDER
    """

    @staticmethod
    def evaluar(match):
        minute = int(match.get("minute", 0) or 0)
        score = str(match.get("score", "0-0") or "0-0")
        goal_probability = float(match.get("goal_probability", 0) or 0)
        over_probability = float(match.get("over_probability", 0) or 0)
        shots_on_target = float(match.get("shots_on_target", 0) or 0)
        dangerous_attacks = float(match.get("dangerous_attacks", 0) or 0)
        total_xg = float(match.get("xG", 0) or 0)

        total_goals = MatchWindowEngine._parse_total_goals(score)

        phase = "OBSERVE"
        reason = "Fuera de ventana útil"
        over_bias = 0
        under_bias = 0
        over_min_gate = 0
        under_min_gate = 0
        publish_over = False
        publish_under = False

        # 1-17 -> solo observar
        if 1 <= minute <= 17:
            phase = "EARLY_OBSERVE"
            reason = "Inicio de partido, solo observación"
            over_min_gate = 78
            under_min_gate = 82

        # 18-35 -> buena ventana over temprana
        elif 18 <= minute <= 35:
            phase = "OVER_EARLY_WINDOW"
            reason = "Ventana temprana útil para OVER"
            over_bias = 8
            under_bias = -3
            over_min_gate = 66
            under_min_gate = 78
            publish_over = True

        # 36-45 -> cautela antes del descanso
        elif 36 <= minute <= 45:
            phase = "HALFTIME_CAUTION"
            reason = "Tramo previo al descanso"
            over_bias = 2
            under_bias = 4
            over_min_gate = 72
            under_min_gate = 70
            publish_over = True
            publish_under = True

        # 46-54 -> transición
        elif 46 <= minute <= 54:
            phase = "SECOND_HALF_TRANSITION"
            reason = "Inicio segundo tiempo, lectura intermedia"
            over_bias = 3
            under_bias = 2
            over_min_gate = 70
            under_min_gate = 72
            publish_over = True
            publish_under = True

        # 55-72 -> ventana premium over
        elif 55 <= minute <= 72:
            phase = "OVER_PREMIUM_WINDOW"
            reason = "Ventana premium para OVER"
            over_bias = 12
            under_bias = -2
            over_min_gate = 64
            under_min_gate = 76
            publish_over = True
            publish_under = True

        # 73-78 -> mixta, pero más exigente
        elif 73 <= minute <= 78:
            phase = "MIXED_DECISION_WINDOW"
            reason = "Ventana mixta, requiere confirmación fuerte"
            over_bias = 4
            under_bias = 6
            over_min_gate = 72
            under_min_gate = 70
            publish_over = True
            publish_under = True

        # 79-86 -> fuerte para under controlado, over solo muy claro
        elif 79 <= minute <= 86:
            phase = "LATE_CONTROL_WINDOW"
            reason = "Tramo final, UNDER favorecido si el partido está cerrado"
            over_bias = -4
            under_bias = 10
            over_min_gate = 80
            under_min_gate = 66
            publish_over = True
            publish_under = True

        # 87+ -> ultra selectivo
        elif minute >= 87:
            phase = "ULTRA_LATE"
            reason = "Tramo ultra tardío, máxima exigencia"
            over_bias = -8
            under_bias = 4
            over_min_gate = 86
            under_min_gate = 78
            publish_over = False
            publish_under = True

        # Ajuste por marcador
        if total_goals >= 3:
            under_bias -= 8
            over_bias += 3

        if total_goals == 0 and minute >= 55:
            under_bias += 5

        if total_goals == 1 and minute >= 65:
            under_bias += 3

        # Ajuste por producción ofensiva
        if shots_on_target >= 4:
            over_bias += 5

        if dangerous_attacks >= 18:
            over_bias += 4

        if total_xg >= 1.4:
            over_bias += 5

        if shots_on_target == 0 and dangerous_attacks <= 8 and total_xg <= 0.45:
            under_bias += 8

        # Ajuste por probabilidades del propio sistema
        if goal_probability >= 65:
            over_bias += 4

        if over_probability <= 42:
            under_bias += 4

        return {
            "phase": phase,
            "reason": reason,
            "over_bias": round(over_bias, 2),
            "under_bias": round(under_bias, 2),
            "over_min_gate": over_min_gate,
            "under_min_gate": under_min_gate,
            "publish_over": publish_over,
            "publish_under": publish_under,
        }

    @staticmethod
    def _parse_total_goals(score):
        try:
            home, away = str(score).split("-")
            return int(home) + int(away)
        except Exception:
            return 0
