import logging
from typing import Any, Dict, List

import requests

from app.config.config import Config


class OddsFetcher:
    """
    JHONNY_ELITE V16 - Extractor de Cuotas de Mercado

    Fuente:
    - The Odds API

    Devuelve eventos de cuotas normalizados para facilitar el matching
    con los partidos live del sistema.
    """

    def __init__(self):
        self.api_key = Config.ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4/sports/soccer"

    def get_live_odds(self, regions: str = "eu") -> List[Dict[str, Any]]:
        if not self.api_key:
            logging.warning("ODDS_API_KEY no configurada.")
            return []

        raw_odds = self._fetch_raw_odds(regions=regions)
        if not raw_odds:
            return []

        normalized = self._normalize_odds_events(raw_odds)
        logging.info(f"ODDS_FETCHER: odds normalizadas = {len(normalized)}")
        return normalized

    def _fetch_raw_odds(self, regions: str = "eu") -> List[Dict[str, Any]]:
        url = f"{self.base_url}/odds"

        params = {
            "api_key": self.api_key,
            "regions": regions,
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
        }

        try:
            logging.info(f"ODDS_FETCHER: consultando {url}")
            logging.info(f"ODDS_FETCHER: key cargada = {'SI' if self.api_key else 'NO'}")

            response = requests.get(url, params=params, timeout=10)

            logging.info(f"ODDS_FETCHER: status = {response.status_code}")

            if response.status_code != 200:
                logging.error(f"ODDS_ERROR: Status {response.status_code} - {response.text}")
                return []

            data = response.json()

            if not isinstance(data, list):
                logging.warning(f"The Odds API devolvió formato inesperado: {type(data)}")
                return []

            logging.info(f"ODDS_FETCHER: odds recibidas = {len(data)}")
            return data

        except Exception as e:
            logging.error(f"FETCH_ERROR en The Odds API: {e}")
            return []

    def _normalize_odds_events(self, raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_events: List[Dict[str, Any]] = []

        for event in raw_events:
            try:
                if not isinstance(event, dict):
                    continue

                home_name = event.get("home_team")
                away_name = event.get("away_team")

                if not home_name or not away_name:
                    continue

                bookmakers = event.get("bookmakers", [])
                normalized_bookmakers = self._normalize_bookmakers(bookmakers)

                normalized_event = {
                    "event_id": event.get("id"),
                    "match_name": f"{home_name} vs {away_name}",
                    "home_name": home_name,
                    "away_name": away_name,
                    "home_team": home_name,
                    "away_team": away_name,
                    "sport_key": event.get("sport_key"),
                    "sport_title": event.get("sport_title"),
                    "commence_time": event.get("commence_time"),
                    "bookmakers": normalized_bookmakers,
                    "source": "the_odds_api",
                    "raw_event": event,
                }

                normalized_events.append(normalized_event)

            except Exception as e:
                logging.warning(f"ODDS_NORMALIZATION_ERROR: {e}")
                continue

        return normalized_events

    def _normalize_bookmakers(self, bookmakers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for bookmaker in bookmakers or []:
            try:
                if not isinstance(bookmaker, dict):
                    continue

                bookmaker_name = bookmaker.get("title") or bookmaker.get("key") or "UNKNOWN"
                markets = bookmaker.get("markets", [])

                normalized_markets: List[Dict[str, Any]] = []

                for market in markets or []:
                    if not isinstance(market, dict):
                        continue

                    market_key = str(market.get("key") or "").lower()
                    outcomes = market.get("outcomes", []) or []

                    # Solo totals le sirve directamente al market_engine para OVER/UNDER
                    if market_key == "totals":
                        normalized_outcomes = []

                        for outcome in outcomes:
                            if not isinstance(outcome, dict):
                                continue

                            normalized_outcomes.append({
                                "name": outcome.get("name"),
                                "label": outcome.get("name"),
                                "odds": outcome.get("price"),
                                "price": outcome.get("price"),
                                "point": outcome.get("point"),
                                "line": outcome.get("point"),
                                "bookmaker": bookmaker_name,
                            })

                        normalized_markets.append({
                            "key": "TOTALS",
                            "name": "TOTALS",
                            "bookmaker": bookmaker_name,
                            "outcomes": normalized_outcomes,
                        })

                if normalized_markets:
                    normalized.append({
                        "title": bookmaker_name,
                        "name": bookmaker_name,
                        "markets": normalized_markets,
                    })

            except Exception as e:
                logging.warning(f"ODDS_BOOKMAKER_NORMALIZATION_ERROR: {e}")
                continue

        return normalized
