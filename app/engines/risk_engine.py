# app/engines/risk_engine.py
from app.config.config import Config

class RiskEngine:
    """
    JHONNY_ELITE V16 - Motor de Riesgo y Fragilidad de Línea
    Implementa M6 (Caos) y M8 (Fragilidad de Línea)
    """

    @staticmethod
    def evaluar_riesgo(stats, mercado):
        """
        Punto 12 y 15: Filtros de descarte y reglas especiales.
        """
        riesgo_score = 0 # 0 a 10 (10 es riesgo extremo)
        bloqueado = False
        motivo_bloqueo = ""

        minuto = stats.get('minute', 0)
        remates_arco = stats.get('shots_on_target', 0)

        # 1. Validación de Ventanas Óptimas (Regla #13)
        en_ventana = any(v[0] <= minuto <= v[1] for v in Config.VENTANAS_PRIORITARIAS)
        if not en_ventana:
            riesgo_score += 3 # Fuera de ventana prioritaria aumenta el riesgo

        # 2. Regla Maestra para UNDER (Regla #15)
        if "UNDER" in mercado:
            if minuto < 60:
                bloqueado = True
                motivo_bloqueo = "UNDER_BEFORE_60_MIN"
            if remates_arco > 4:
                bloqueado = True
                motivo_bloqueo = "UNDER_HIGH_DANGER"

        # 3. Detección de Caos (M6)
        # Si hay tarjetas rojas o eventos disruptivos (ej. marcador se mueve rápido)
        if stats.get('red_cards', 0) > 0:
            riesgo_score += 4
            
        return {
            "risk_score": riesgo_score,
            "is_blocked": bloqueado,
            "block_reason": motivo_bloqueo,
            "staked_allowed": "1-3%" if riesgo_score < 5 else "0.5-1%"
        }
