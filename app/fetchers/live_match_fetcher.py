import requests
import logging
from app.config.config import Config

class LiveMatchFetcher:
    """
    JHONNY_ELITE V16 - Extractor de Datos en Vivo
    Extrae, normaliza y valida la calidad de datos.
    """

    def __init__(self):
        self.url = "https://v3.football.api-sports.io/fixtures?live=all"
        self.headers = {
            "x-rapidapi-key": Config.API_FOOTBALL_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }

    def fetch_live_data(self):
        if not Config.API_FOOTBALL_KEY:
            logging.warning("API_FOOTBALL_KEY no configurada.")
            return []

        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                logging.error(f"FETCH_ERROR API-Football status {response.status_code}: {response.text}")
                return []

            data = response.json()

            if not data.get("response"):
                logging.info("API-Football no devolvió partidos en vivo.")
                return []

            return self._normalize(data["response"])

        except Exception as e:
            logging.error(f"FETCH_ERROR en API-Football: {e}")
            return []

    def _normalize(self, raw_matches):
        normalized_list = []

        for m in raw_matches:
            try:
                fixture = m.get("fixture", {})
                goals = m.get("goals", {})
                teams = m.get("teams", {})
                league = m.get("league", {})
                statistics = m.get("statistics", [])

                if not fixture or goals.get("home") is None:
                    continue

                minuto = fixture.get("status", {}).get("elapsed") or 0

                match_map = {
                    "match_id": fixture.get("id"),
                    "home": teams.get("home", {}).get("name", "Desconocido"),
                    "away": teams.get("away", {}).get("name", "Desconocido"),
                    "league": league.get("name", "Desconocida"),
                    "country": league.get("country", "Desconocido"),
                    "minute": minuto,
                    "score": f"{goals.get('home', 0)}-{goals.get('away', 0)}",
                    "dangerous_attacks": self._get_stat(statistics, "Dangerous Attacks"),
                    "shots": self._get_stat(statistics, "Total Shots"),
                    "shots_on_target": self._get_stat(statistics, "Shots on Goal"),
                    "corners": self._get_stat(statistics, "Corner Kicks"),
                    "xG": float(self._get_stat(statistics, "expected_goals") or 0.0),
                    "red_cards": self._get_stat(statistics, "Red Cards"),
                    "confidence": 80.0,
                    "prob_real": 0.65
                }

                normalized_list.append(match_map)

            except Exception as e:
                logging.warning(f"NORMALIZATION_ERROR: {e}")
                continue

        return normalized_list

    def _get_stat(self, stats_list, type_name):
        total = 0

        for team_stat in stats_list:
            for s in team_stat.get("statistics", []):
                if s.get("type") == type_name and s.get("value") is not None:
                    val = str(s["value"]).replace("%", "")
                    try:
                        total += int(float(val))
                    except Exception:
                        continue

        return total
