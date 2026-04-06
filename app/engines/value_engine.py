from app.config.config import Config

class ValueEngine:

    @staticmethod
    def calcular_edge(match, cuota):
        prob = match.get("prob_real", 0.5)

        edge = (prob * cuota) - 1

        if edge >= Config.EDGE_MINIMO:
            return {
                "status": "OK",
                "edge": edge,
                "value_category": "VALUE"
            }

        return {
            "status": "LOW_VALUE",
            "edge": edge,
            "value_category": "SIN_VALOR"
        }
