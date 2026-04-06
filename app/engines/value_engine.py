from app.config.config import Config

class ValueEngine:

    @staticmethod
    def calcular_edge(match, cuota):
        prob_real = match.get("prob_real", 0.5)

        if cuota <= 0:
            return {
                "status": "LOW_VALUE",
                "edge": 0,
                "value_category": "SIN_VALOR",
                "prob_real": prob_real,
                "prob_implicita": 0
            }

        prob_implicita = 1 / cuota
        edge = prob_real - prob_implicita

        if edge >= 0.15:
            categoria = "VALUE_PREMIUM"
            status = "OK"
        elif edge >= Config.EDGE_MINIMO:
            categoria = "VALUE"
            status = "OK"
        else:
            categoria = "SIN_VALOR"
            status = "LOW_VALUE"

        return {
            "status": status,
            "edge": round(edge, 4),
            "value_category": categoria,
            "prob_real": round(prob_real, 4),
            "prob_implicita": round(prob_implicita, 4)
        }
