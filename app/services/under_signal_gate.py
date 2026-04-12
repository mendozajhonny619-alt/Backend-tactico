class UnderSignalGate:
    """
    Gate para detectar señales UNDER (partidos cerrados / sin gol probable)
    """

    @staticmethod
    def evaluar(match):
        minute = int(match.get("minute", 0) or 0)
        shots_on_target = float(match.get("shots_on_target", 0) or 0)
        dangerous_attacks = float(match.get("dangerous_attacks", 0) or 0)
        total_xg = float(match.get("xG", 0) or 0)
        goal_probability = float(match.get("goal_probability", 0) or 0)
        over_probability = float(match.get("over_probability", 0) or 0)
        risk_score = float(match.get("risk_score", 0) or 0)
        risk_level = str(match.get("risk_level", "MEDIO")).upper()
        match_state = str(match.get("match_state", "CONTROLADO")).upper()
        data_quality = str(match.get("data_quality", "LOW")).upper()

        reasons = []
        score = 0

        # =========================
        # BLOQUEOS CRÍTICOS
        # =========================
        if minute < 20:
            return {"publish": False, "reason": "MINUTO_TEMPRANO"}

        if match_state in ["EXPLOSIVO", "CALIENTE"]:
            return {"publish": False, "reason": "PARTIDO_CALIENTE"}

        if risk_level == "ALTO":
            return {"publish": False, "reason": "RIESGO_ALTO"}

        # =========================
        # LECTURA UNDER
        # =========================

        if shots_on_target <= 2:
            score += 15
            reasons.append("POCOS_TIROS_ARCO")

        if dangerous_attacks <= 18:
            score += 12
            reasons.append("POCO_ATAQUE_REAL")

        if total_xg <= 1.2:
            score += 18
            reasons.append("XG_BAJO")

        if goal_probability <= 55:
            score += 15
            reasons.append("PROB_GOL_BAJA")

        if over_probability <= 55:
            score += 10
            reasons.append("OVER_DEBIL")

        if match_state in ["CONTROLADO", "TIBIO", "ESTABLE"]:
            score += 12
            reasons.append("PARTIDO_CONTROLADO")

        if minute >= 60:
            score += 10
            reasons.append("MINUTO_AVANZADO")

        if risk_score <= 5:
            score += 8
            reasons.append("RIESGO_CONTROLADO")

        if data_quality == "HIGH":
            score += 5

        # =========================
        # DECISIÓN FINAL
        # =========================

        if score >= 60:
            return {
                "publish": True,
                "type": "UNDER",
                "gate_score": score,
                "reason": reasons
            }

        return {
            "publish": False,
            "gate_score": score,
            "reason": "UNDER_NO_CLARO"
      }
