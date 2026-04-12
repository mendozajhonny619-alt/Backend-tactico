class EliteSignalGate:
    """
    Filtro final inteligente para señales OVER.
    Decide si publicar o no basado en score y contexto.
    """

    @staticmethod
    def evaluar(match, motores=None):
        gate_score = 0
        reasons = []

        signal_score = float(match.get("signal_score", 0) or 0)
        ai_score = float(match.get("ai_score", 0) or 0)
        goal_prob = float(match.get("goal_probability", 0) or 0)
        over_prob = float(match.get("over_probability", 0) or 0)
        risk_score = float(match.get("risk_score", 10) or 10)

        # 🔥 BASE
        gate_score += signal_score * 0.6
        gate_score += ai_score * 0.4

        # 🔥 PROBABILIDAD
        if goal_prob >= 60:
            gate_score += 8
            reasons.append("Alta prob gol")

        if over_prob >= 55:
            gate_score += 6
            reasons.append("Over fuerte")

        # 🔥 RIESGO
        if risk_score <= 4:
            gate_score += 6
            reasons.append("Riesgo bajo")
        elif risk_score >= 8:
            gate_score -= 10
            reasons.append("Riesgo alto")

        # 🔥 CONTEXTO IA (si viene)
        if motores:
            predictor = motores.get("predictor", {})
            tactica = motores.get("tactica", {})

            if predictor.get("gol_inminente"):
                gate_score += 6
                reasons.append("Gol inminente")

            if tactica.get("match_state") in ["EXPLOSIVO", "CALIENTE"]:
                gate_score += 5
                reasons.append("Momentum alto")

        # 🔥 DECISIÓN FINAL
        publish = False
        status = "OBSERVE"

        if gate_score >= 85:
            publish = True
            status = "ELITE"
        elif gate_score >= 70:
            publish = True
            status = "STRONG"
        elif gate_score >= 60:
            publish = False
            status = "OBSERVE"
        else:
            publish = False
            status = "BLOCKED"

        return {
            "publish": publish,
            "gate_score": round(gate_score, 2),
            "gate_status": status,
            "reasons": reasons,
            "mode": "ELITE_V1"
  }
