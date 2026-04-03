# app/engines/value_engine.py
from app.config.config import Config

class ValueEngine:
    """
    JHONNY_ELITE V16 - Motor de Valor y Ventaja Matemática (Edge)
    Implementa M5: Medición de Edge y Categoría de Value.
    """

    @staticmethod
    def calcular_edge(stats, cuota_mercado):
        """
        Punto 9: Calcula si la cuota ofrece una ventaja real.
        """
        # 1. Obtener nuestra Probabilidad Real (Basada en xG y Momentum)
        # Lógica V16: Ajustamos la probabilidad base por el estado del partido
        prob_base = stats.get('prob_real', 0.50)
        
        # Ajuste por Momentum (Si es EXPLOSIVO, subimos nuestra confianza)
        if stats.get('match_state') == "EXPLOSIVO":
            prob_ajustada = min(prob_base + 0.15, 0.95)
        elif stats.get('match_state') == "CALIENTE":
            prob_ajustada = min(prob_base + 0.08, 0.90)
        else:
            prob_ajustada = prob_base

        # 2. Calcular Probabilidad Implícita de la Casa (1 / Cuota)
        if cuota_mercado <= 0: return {"status": "BLOCK", "edge": 0}
        prob_implicita = 1 / cuota_mercado

        # 3. Calcular el EDGE (Ventaja)
        edge = prob_ajustada - prob_implicita
        
        # Clasificación de Value (Punto 5 del Protocolo)
        categoria = "SIN_VALOR"
        if edge >= 0.20: categoria = "VALUE_EXTREMO"
        elif edge >= 0.10: categoria = "VALUE_ALTO"
        elif edge >= 0.05: categoria = "VALUE_ESTANDAR"

        return {
            "status": "OK" if edge >= Config.EDGE_MINIMO else "LOW_VALUE",
            "prob_real_ajustada": round(prob_ajustada, 2),
            "prob_implicita": round(prob_implicita, 2),
            "edge": round(edge, 3),
            "value_category": categoria,
            "score": round(edge * 100, 1)
        }
