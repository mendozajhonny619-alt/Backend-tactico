import requests
import logging
from app.config.config import Config

class OddsFetcher:
    """
    JHONNY_ELITE V16 - Extractor de Cuotas de Mercado
    """

    def __init__(self):
        self.api_key = Config.THE_ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4/sports/soccer/odds"

    def get_live_odds(self, regions="eu"):
        params = {
            "api_key": self.api_key,
            "regions": regions,
            "markets": "h2h,totals",
            "oddsFormat": "decimal"
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)

            if response.status_code != 200:
                logging.error(f"ODDS_ERROR: Status {response.status_code}")
                return []

            return response.json()

        except Exception as e:
            logging.error(f"FETCH_ERROR en The Odds API: {e}")
            return []
