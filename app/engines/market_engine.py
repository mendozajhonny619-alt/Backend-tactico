from app.config.config import Config
from app.utils.normalizer import Normalizer

class MarketEngine:
    def __init__(self):
        self.config = Config()

    def validar_mercado(self, match_internal, odds_raw_list):
        """
        Valida cuota, línea y valor real.
        match_internal: datos procesados por tu fetcher
        odds_raw_list: lista de partidos de The Odds API
        """
        # 1. Intentar encontrar el partido con Fuzzy Match
        match_odds = Normalizer.match_profesional(
            match_internal['home'], 
            match_internal['away'], 
            odds_raw_list
        )

        if not match_odds:
            return {"status": "BLOCK", "reason": "ODDS_NOT_FOUND", "valid": False}

        # 2. Extraer cuota del mercado principal (H2H o Totals)
        # Nota: Aquí deberías implementar la lógica para buscar en tu bookie favorita
        cuota_mercado = self._obtener_mejor_cuota(match_odds)

        if not cuota_mercado:
            return {"status": "BLOCK", "reason": "NO_ODDS_AVAILABLE", "valid": False}

        # 3. Validar rango de cuota (Regla #14)
        if not (self.config.CUOTA_MINIMA <= cuota_mercado <= self.config.CUOTA_MAXIMA):
            return {"status": "BLOCK", "reason": "CUOTA_OUT_OF_RANGE", "valid": False}

        # 4. Cálculo de EDGE (Punto 9)
        prob_implicita = 1 / cuota_mercado
        edge = match_internal['prob_real'] - prob_implicita

        if edge < self.config.EDGE_MINIMO:
            return {"status": "BLOCK", "reason": "LOW_VALUE_EDGE", "valid": False}

        return {
            "status": "OK",
            "valid": True,
            "cuota": cuota_mercado,
            "edge": round(edge, 3),
            "bookmaker": match_odds.get('bookmaker', 'Desconocido')
        }

    def _obtener_mejor_cuota(self, match_odds):
        # Lógica simplificada: extrae la primera cuota disponible
        try:
            return match_odds['bookmakers'][0]['markets'][0]['outcomes'][0]['price']
        except:
            return None
