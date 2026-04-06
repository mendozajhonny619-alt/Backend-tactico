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
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            data = response.json()

            if not data.get("response"):
                return []

            return self._normalize(data["response"])

        except Exception as e:
            logging.error(f"FETCH_ERROR en API-Football: {e}")
            return []

    def _normalize(self, raw_matches):
        normalized_list = []

        for m in raw_matches:
            try:
                fixture = m["fixture"]
                goals = m["goals"]

                if not fixture or goals["home"] is None:
                    continue

                match_map = {
                    "match_id": fixture["id"],
                    "home": m["teams"]["home"]["name"],
                    "away": m["teams"]["away"]["name"],
                    "league": m["league"]["name"],
                    "country": m["league"]["country"],
                    "minute": fixture["status"]["elapsed"],
                    "score": f"{goals['home']}-{goals['away']}",
                    "dangerous_attacks": self._get_stat(m.get("statistics", []), "Dangerous Attacks"),
                    "shots": self._get_stat(m.get("statistics", []), "Total Shots"),
                    "shots_on_target": self._get_stat(m.get("statistics", []), "Shots on Goal"),
                    "corners": self._get_stat(m.get("statistics", []), "Corner Kicks"),
                    "xG": float(self._get_stat(m.get("statistics", []), "expected_goals") or 0.0),
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
