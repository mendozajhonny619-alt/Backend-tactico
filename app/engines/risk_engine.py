class RiskEngine:

    @staticmethod
    def evaluar_riesgo(match, market):
        minuto = match.get("minute", 0)

        # lógica básica
        if minuto < 10:
            return {"is_blocked": True, "risk_score": 100}

        return {
            "is_blocked": False,
            "risk_score": 20
        }
