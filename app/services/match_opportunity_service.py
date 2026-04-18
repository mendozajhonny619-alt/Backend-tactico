class MatchOpportunityService:
    """
    Detecta si un partido:
    - Tiene oportunidad OVER
    - Tiene oportunidad UNDER
    - Solo es OBSERVACIÓN
    - Debe ser RECHAZADO

    Este módulo evita perder oportunidades ocultas.
    """

    @staticmethod
    def evaluar(match, tactica, predictor, riesgo, window):
        minuto = int(match.get("minute", 0) or 0)
        shots_on_target = float(match.get("shots_on_target", 0) or 0)
        dangerous_attacks = float(match.get("dangerous_attacks", 0) or 0)
        corners = float(match.get("corners", 0) or 0)
        xg = float(match.get("xG", 0) or 0)

        match_state = tactica.get("match_state", "CONTROLADO")
        intensidad = float(tactica.get("intensity_score", 0) or 0)

        gol_inminente = predictor.get("gol_inminente", False)
        confianza_gol = float(predictor.get("confianza_ventana", 0) or 0)

        risk_score = float(riesgo.get("risk_score", 0) or 0)

        reasons = []
        strength = 0

        # =========================
        # 1. DETECCIÓN OVER
        # =========================
        over_signals = 0

        if gol_inminente:
            over_signals += 2
            strength += 12
            reasons.append("Gol inminente detectado")

        if shots_on_target >= 3:
            over_signals += 2
            strength += 10
            reasons.append("Remates a puerta altos")

        if dangerous_attacks >= 18:
            over_signals += 2
            strength += 8
            reasons.append("Alta presión ofensiva")

        if xg >= 1.0:
            over_signals += 2
            strength += 10
            reasons.append("xG elevado")

        if intensidad >= 30:
            over_signals += 1
            strength += 6
            reasons.append("Intensidad alta")

        if corners >= 4:
            over_signals += 1
            strength += 4
            reasons.append("Corners acumulados")

        if 25 <= minuto <= 80:
            strength += 4

        # =========================
        # 2. DETECCIÓN UNDER
        # =========================
        under_signals = 0

        if shots_on_target == 0:
            under_signals += 2
            strength += 6
            reasons.append("Sin remates a puerta")

        if dangerous_attacks <= 6:
            under_signals += 2
            strength += 6
            reasons.append("Poca presión ofensiva")

        if xg < 0.5:
            under_signals += 2
            strength += 6
            reasons.append("xG bajo")

        if match_state in ["MUERTO", "CONTROLADO"]:
            under_signals += 2
            strength += 8
            reasons.append("Partido cerrado")

        if minuto >= 60:
            strength += 6

        # =========================
        # 3. DECISIÓN FINAL
        # =========================

        # 🔥 OVER CLARO
        if over_signals >= 4 and risk_score <= 8:
            return {
                "type": "OVER_CANDIDATE",
                "side": "OVER",
                "strength": strength,
                "reasons": reasons,
            }

        # 🧊 UNDER CLARO
        if under_signals >= 4 and minuto >= 55 and risk_score <= 7:
            return {
                "type": "UNDER_CANDIDATE",
                "side": "UNDER",
                "strength": strength,
                "reasons": reasons,
            }

        # 👁️ OBSERVACIÓN (MUY IMPORTANTE)
        if (
            over_signals >= 2
            or under_signals >= 2
            or gol_inminente
            or intensidad >= 20
        ):
            return {
                "type": "OBSERVE",
                "side": "MIXTO",
                "strength": strength,
                "reasons": reasons if reasons else ["Partido con señales débiles pero observables"],
            }

        # ❌ RECHAZADO
        return {
            "type": "REJECTED",
            "side": "NONE",
            "strength": 0,
            "reasons": ["Sin señales suficientes"],
        }
