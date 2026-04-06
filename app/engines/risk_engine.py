from app.config.config import Config

class RiskEngine:

    @staticmethod
    def evaluar_riesgo(match, market):
        minuto = match.get("minute", 0)
        shots_on_target = match.get("shots_on_target", 0)
        red_cards = match.get("red_cards", 0)

        risk_score = 0
        is_blocked = False
        block_reason = ""

        # Fuera de ventanas prioritarias = más riesgo
        en_ventana = any(inicio <= minuto <= fin for inicio, fin in Config.VENTANAS_PRIORITARIAS)
        if not en_ventana:
            risk_score += 3

        # Bloqueo temprano
        if minuto < 10:
            is_blocked = True
            block_reason = "MINUTO_MUY_TEMPRANO"
            risk_score += 5

        # Riesgo por roja
        if red_cards > 0:
            risk_score += 4

        # Regla básica para UNDER
        if "UNDER" in str(market).upper():
            if minuto < 60:
                is_blocked = True
                block_reason = "UNDER_ANTES_DEL_MINUTO_60"
            elif shots_on_target > 4:
                is_blocked = True
                block_reason = "UNDER_CON_MUCHO_PELIGRO"

        return {
            "is_blocked": is_blocked,
            "risk_score": risk_score,
            "block_reason": block_reason
        }
