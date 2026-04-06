from app.config.config import Config

class MarketEngine:

    def validar_mercado(self, match, odds_data):
        # versión simple
        cuota = 1.80  # simulada

        if Config.CUOTA_MINIMA <= cuota <= Config.CUOTA_MAXIMA:
            return {
                "valid": True,
                "cuota": cuota
            }

        return {
            "valid": False,
            "cuota": None
        }
