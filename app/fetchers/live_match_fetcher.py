# app/fetchers/live_match_fetcher.py
import requests
import logging
from app.config.config import Config

class LiveMatchFetcher:
    """
    JHONNY_ELITE V16 - Extractor de Datos en Vivo
    Extrae, normaliza y valida la calidad de datos (M7).
    """
    def __init__(self):
        self.url = "https://v3.football.api-sports.io/fixtures?live=all"
        self.headers = {
            'x-rapidapi-key': Config.API_FOOTBALL_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }

    def fetch_live_data(self):
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            data = response.json()
            
            if not data.get('response'):
                return []
                
            return self._normalize(data['response'])
        except Exception as e:
            logging.error(f"FETCH_ERROR en API-Football: {e}")
            return []

    def _normalize(self, raw_matches):
        normalized_list = []
        for m in raw_matches:
            try:
                fixture = m['fixture']
                goals = m['goals']
                stats = m['statistics'] # Requiere lógica extra para aplanar
                
                # M7: Validación de Calidad Mínima
                if not fixture or goals['home'] is None:
                    continue

                match_map = {
                    "match_id": fixture['id'],
                    "home": m['teams']['home']['name'],
                    "away": m['teams']['away']['name'],
                    "league": m['league']['name'],
                    "country": m['league']['country'],
                    "minute": fixture['status']['elapsed'],
                    "score": f"{goals['home']}-{goals['away']}",
                    "dangerous_attacks": self._get_stat(m['statistics'], "Dangerous Attacks"),
                    "shots": self._get_stat(m['statistics'], "Total Shots"),
                    "shots_on_target": self._get_stat(m['statistics'], "Shots on Goal"),
                    "corners": self._get_stat(m['statistics'], "Corner Kicks"),
                    "xG": float(self._get_stat(m['statistics'], "expected_goals") or 0.0),
                    "confidence": 80.0, # Valor base inicial
                    "prob_real": 0.65    # Valor base que el ValueEngine ajustará
                }
                normalized_list.append(match_map)
            except Exception as e:
                continue
        return normalized_list

    def _get_stat(self, stats_list, type_name):
        # API-Football devuelve stats como lista de diccionarios por equipo
        # Esta función suma ambos equipos para tener el total del partido
        total = 0
        for team_stat in stats_list:
            for s in team_stat['statistics']:
                if s['type'] == type_name and s['value']:
                    val = str(s['value']).replace('%', '')
                    total += int(float(val))
        return total
