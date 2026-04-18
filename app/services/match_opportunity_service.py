class MatchOpportunityService:

    @staticmethod
    def evaluar(match, tactica, predictor, riesgo, window_data):
        """
        Clasifica el partido en:
        - OVER_CANDIDATE
        - UNDER_CANDIDATE
        - OBSERVE
        - REJECTED
        """

        ai_score = float(match.get("ai_score", 0) or 0)
        goal_prob = float(match.get("goal_probability", 0) or 0)
        over_prob = float(match.get("over_probability", 0) or 0)
        confidence = float(match.get("confidence", 0) or 0)

        shots_on_target = float(match.get("shots_on_target", 0) or 0)
        dangerous_attacks = float(match.get("dangerous_attacks", 0) or 0)
        total_xg = float(match.get("xG", 0) or 0)

        match_state = tactica.get("match_state", "ESTABLE")
        risk_score = float(riesgo.get("risk_score", 10) or 10)
        risk_level = match.get("risk_level", "MEDIO")

        data_quality = str(match.get("data_quality", "LOW")).upper()

        reasons = []

        # =========================
        # 1. BLOQUEO DURO
        # =========================
        if data_quality == "LOW" and total_xg == 0 and shots_on_target == 0:
            return {
                "type": "REJECTED",
                "side": None,
                "reasons": ["DATA_QUALITY_CRITICA"]
            }

        if risk_level == "ALTO" and risk_score >= 9:
            return {
                "type": "REJECTED",
                "side": None,
                "reasons": ["RIESGO_EXTREMO"]
            }

        # =========================
        # 2. DETECCIÓN OVER
        # =========================
        over_strength = 0

        if goal_prob >= 55:
            over_strength += 2
        elif goal_prob >= 45:
            over_strength += 1

        if over_prob >= 50:
            over_strength += 2
        elif over_prob >= 40:
            over_strength += 1

        if shots_on_target >= 2:
            over_strength += 1

        if dangerous_attacks >= 10:
            over_strength += 1

        if total_xg >= 0.6:
            over_strength += 1

        if match_state in ["CALIENTE", "EXPLOSIVO", "ACTIVO"]:
            over_strength += 2

        if predictor.get("gol_inminente"):
            over_strength += 2

        # =========================
        # 3. DETECCIÓN UNDER
        # =========================
        under_strength = 0

        if goal_prob <= 35:
            under_strength += 2

        if over_prob <= 35:
            under_strength += 2

        if shots_on_target == 0:
            under_strength += 1

        if dangerous_attacks <= 5:
            under_strength += 1

        if total_xg <= 0.4:
            under_strength += 1

        if match_state in ["MUERTO", "TIBIO", "CONTROLADO"]:
            under_strength += 2

        # =========================
        # 4. CLASIFICACIÓN FINAL
        # =========================

        if over_strength >= 5 and window_data.get("publish_over", False):
            return {
                "type": "OVER_CANDIDATE",
                "side": "OVER",
                "strength": over_strength,
                "reasons": ["OVER_POTENTE"]
            }

        if under_strength >= 5 and window_data.get("publish_under", False):
            return {
                "type": "UNDER_CANDIDATE",
                "side": "UNDER",
                "strength": under_strength,
                "reasons": ["UNDER_POTENTE"]
            }

        # =========================
        # 5. OBSERVACIÓN
        # =========================

        if over_strength >= 3 or under_strength >= 3:
            return {
                "type": "OBSERVE",
                "side": "OVER" if over_strength >= under_strength else "UNDER",
                "strength": max(over_strength, under_strength),
                "reasons": ["CERCA_PERO_NO_LISTO"]
            }

        return {
            "type": "REJECTED",
            "side": None,
            "reasons": ["SIN_VALOR_OPERATIVO"]
        }
