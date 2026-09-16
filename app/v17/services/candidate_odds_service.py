from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from app.config.config import Config
from app.services.api_quota_monitor import api_quota_monitor

logger = logging.getLogger(__name__)


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return re.sub(r"\s+", " ", text)


class CandidateOddsService:
    """Obtiene linea/cuota real solo para candidatos ya detectados.

    Orden de fuentes, pensado para precision + ahorro:
    1) API-Football live odds del fixture.
    2) API-Football pre-match odds del mismo fixture si live no trae totals.
    3) The Odds API como fallback, solo si existe una liga/sport compatible.
    4) Cuota adjunta al partido como ultimo fallback.

    Nunca fabrica una cuota. Si ninguna fuente ofrece mercado real, devuelve
    odds_available=False y MasterDecisionAI no puede publicar la senal.
    """

    API_FOOTBALL_URL = "https://v3.football.api-sports.io"
    THE_ODDS_URL = "https://api.the-odds-api.com/v4"

    # Claves habituales. Se validan contra /sports (gratuito) antes de usarse.
    LEAGUE_TO_SPORT_KEY = {
        39: "soccer_epl",
        40: "soccer_efl_champ",
        140: "soccer_spain_la_liga",
        141: "soccer_spain_segunda_division",
        135: "soccer_italy_serie_a",
        136: "soccer_italy_serie_b",
        78: "soccer_germany_bundesliga",
        79: "soccer_germany_bundesliga2",
        61: "soccer_france_ligue_one",
        62: "soccer_france_ligue_two",
        94: "soccer_portugal_primeira_liga",
        88: "soccer_netherlands_eredivisie",
        144: "soccer_belgium_first_div",
        203: "soccer_turkey_super_league",
        71: "soccer_brazil_campeonato",
        128: "soccer_argentina_primera_division",
        262: "soccer_usa_mls",
        2: "soccer_uefa_champs_league",
        3: "soccer_uefa_europa_league",
        848: "soccer_uefa_europa_conference_league",
        13: "soccer_conmebol_copa_libertadores",
        11: "soccer_conmebol_copa_sudamericana",
    }

    def __init__(self, ttl_seconds: int | None = None) -> None:
        self.api_key = Config.API_FOOTBALL_KEY
        self.the_odds_key = Config.ODDS_API_KEY
        self.ttl_seconds = int(ttl_seconds or getattr(Config, "ODDS_CACHE_TTL_SECONDS", 180))
        self.the_odds_ttl = int(getattr(Config, "THE_ODDS_CACHE_TTL_SECONDS", 300))
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._the_odds_sport_cache: Dict[str, Dict[str, Any]] = {}
        self._sports_cache: Tuple[float, List[Dict[str, Any]]] = (0.0, [])
        self._cooldown_until = 0.0

    def enrich(self, match: Dict[str, Any], market: str, model_probability: float = 0.0) -> Dict[str, Any]:
        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "").strip()
        direction = str(market or "").upper()
        current_total = int(sf(match.get("home_score"))) + int(sf(match.get("away_score")))
        target_line = current_total + 0.5

        if direction not in {"OVER", "UNDER"}:
            return self._empty("INVALID_MARKET", direction, target_line)
        if not Config.CANDIDATE_ODDS_ENABLED:
            return self._empty("DISABLED", direction, target_line)

        cache_key = f"{fixture_id}:{direction}"
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - sf(cached.get("at")) < self.ttl_seconds:
            return dict(cached.get("result") or self._empty("CACHE_EMPTY", direction, target_line))

        # 1. API-Football live market.
        if fixture_id and self.api_key and now >= self._cooldown_until:
            raw, status = self._api_football_request("/odds/live", {"fixture": fixture_id}, "odds_live_candidate")
            result = self._result_from_api_football(raw, direction, target_line, model_probability, "API_FOOTBALL_LIVE_ODDS")
            if result.get("odds_available"):
                return self._store(cache_key, result)
            if status == 429:
                self._cooldown_until = now + 300

            # 2. Si el live no ofrece totals, reutilizamos la cuota pre-match real del mismo fixture.
            # Es mejor que inventar una linea y se consulta unicamente para un candidato real.
            if status != 429:
                raw_pre, _ = self._api_football_request("/odds", {"fixture": fixture_id}, "odds_prematch_candidate")
                result = self._result_from_api_football(raw_pre, direction, target_line, model_probability, "API_FOOTBALL_PREMATCH_ODDS")
                if result.get("odds_available"):
                    return self._store(cache_key, result)

        # 3. Fallback de mercado independiente. Solo una liga compatible y con cache.
        if bool(getattr(Config, "THE_ODDS_FALLBACK_ENABLED", True)) and self.the_odds_key:
            result = self._from_the_odds_api(match, direction, target_line, model_probability)
            if result.get("odds_available"):
                return self._store(cache_key, result)

        # 4. Ultimo fallback: solo si el match ya trae una cuota real adjunta.
        result = self._from_existing_match(match, direction, target_line, model_probability, "NO_PROVIDER_TOTALS")
        return self._store(cache_key, result)

    def _api_football_request(self, path: str, params: Dict[str, Any], monitor_name: str) -> Tuple[List[Any], int]:
        try:
            response = requests.get(
                f"{self.API_FOOTBALL_URL}{path}",
                headers={"x-apisports-key": self.api_key},
                params=params,
                timeout=7,
            )
            api_quota_monitor.record_response(response, monitor_name)
            if response.status_code != 200:
                return [], response.status_code
            body = response.json() if response.content else {}
            return list(body.get("response") or []), response.status_code
        except Exception as exc:
            logger.debug("odds provider error %s: %s", path, exc)
            return [], 0

    def _result_from_api_football(
        self,
        raw: Any,
        direction: str,
        target_line: float,
        model_probability: float,
        source: str,
    ) -> Dict[str, Any]:
        candidates = self._extract_totals(raw, direction)
        selected = self._select_candidate(candidates, target_line)
        if not selected:
            return self._empty(f"{source}_NO_TOTALS", direction, target_line)
        return self._make_result(selected, direction, target_line, model_probability, source)

    def _extract_totals(self, raw: Any, direction: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        def walk(value: Any, bookmaker: Optional[str] = None, market_name: Optional[str] = None) -> None:
            if isinstance(value, dict):
                local_bookmaker = bookmaker
                local_market = market_name

                # API-Football commonly nests bookmaker -> bets -> values.
                if isinstance(value.get("name"), str) and ("bookmaker" in str(value).lower() or "bets" in value):
                    local_bookmaker = value.get("name") or bookmaker
                if "values" in value and isinstance(value.get("name"), str):
                    local_market = value.get("name") or market_name

                text = " ".join(str(value.get(k) or "") for k in ("name", "value", "label", "bet", "market", "title")).upper()
                market_text = str(local_market or "").upper()
                is_total_context = any(x in market_text for x in ("OVER/UNDER", "TOTAL", "GOALS OVER", "GOALS UNDER"))
                direction_match = direction in text
                odd = sf(value.get("odd") or value.get("odds") or value.get("price"), 0.0)
                line = self._parse_line(text)
                if line is None:
                    line = sf(value.get("handicap") or value.get("point") or value.get("line"), 0.0)

                if odd > 1.0 and line and line > 0 and (direction_match or (is_total_context and direction in text)):
                    rows.append({
                        "line": line,
                        "odds": odd,
                        "bookmaker": local_bookmaker or value.get("bookmaker") or value.get("provider"),
                        "raw_text": text[:180],
                    })

                for child in value.values():
                    walk(child, local_bookmaker, local_market)
            elif isinstance(value, list):
                for item in value:
                    walk(item, bookmaker, market_name)

        walk(raw)
        return rows

    def _select_candidate(self, candidates: List[Dict[str, Any]], target_line: float) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        low = sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50)
        high = sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10)
        in_range = [x for x in candidates if low <= sf(x.get("odds")) <= high]
        pool = in_range or candidates
        pool.sort(key=lambda x: (abs(sf(x.get("line"), target_line) - target_line), abs(sf(x.get("odds"), 0) - 1.80)))
        return pool[0]

    def _make_result(
        self,
        selected: Dict[str, Any],
        direction: str,
        target_line: float,
        model_probability: float,
        source: str,
    ) -> Dict[str, Any]:
        odds = sf(selected.get("odds"), 0.0)
        line = sf(selected.get("line"), target_line)
        implied = (100.0 / odds) if odds > 1.0 else 0.0
        edge = model_probability - implied if model_probability > 0 and implied > 0 else 0.0
        expected_value = ((model_probability / 100.0) * odds) - 1.0 if model_probability > 0 and odds > 1.0 else 0.0
        return {
            "odds_available": odds > 1.0,
            "odds_source": source,
            "odds_status": "OK" if odds > 1.0 else "INVALID_ODDS",
            "market_direction": direction,
            "line": line,
            "odds": odds,
            "bookmaker": selected.get("bookmaker"),
            "implied_probability": round(implied, 2),
            "model_probability_for_value": round(model_probability, 2),
            "value_edge": round(edge, 2),
            "expected_value": round(expected_value, 4),
            "has_positive_value": bool(edge >= sf(getattr(Config, "EDGE_MIN_PERCENT", 5.0), 5.0) and expected_value >= sf(getattr(Config, "MIN_EXPECTED_VALUE", 0.03), 0.03)),
            "odds_timestamp": selected.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "odds_age_seconds": sf(selected.get("age_seconds"), 0.0),
            "target_line": target_line,
        }

    # ---------------- The Odds API fallback ----------------
    def _from_the_odds_api(self, match: Dict[str, Any], direction: str, target_line: float, model_probability: float) -> Dict[str, Any]:
        sport_key = self._resolve_sport_key(match)
        if not sport_key:
            return self._empty("THE_ODDS_NO_SPORT_KEY", direction, target_line)

        now = time.time()
        cache = self._the_odds_sport_cache.get(sport_key)
        if cache and now - sf(cache.get("at")) < self.the_odds_ttl:
            events = cache.get("events") or []
        else:
            try:
                response = requests.get(
                    f"{self.THE_ODDS_URL}/sports/{sport_key}/odds",
                    params={
                        "apiKey": self.the_odds_key,
                        "regions": getattr(Config, "THE_ODDS_REGION", "eu"),
                        "markets": "totals",
                        "oddsFormat": "decimal",
                        "dateFormat": "iso",
                    },
                    timeout=8,
                )
                if response.status_code != 200:
                    return self._empty(f"THE_ODDS_HTTP_{response.status_code}", direction, target_line)
                events = response.json() if isinstance(response.json(), list) else []
                self._the_odds_sport_cache[sport_key] = {"at": now, "events": events}
            except Exception as exc:
                logger.debug("The Odds API fallback unavailable: %s", exc)
                return self._empty("THE_ODDS_ERROR", direction, target_line)

        event = self._match_event(events, match)
        if not event:
            return self._empty("THE_ODDS_EVENT_NOT_FOUND", direction, target_line)

        candidates: List[Dict[str, Any]] = []
        for bookmaker in event.get("bookmakers") or []:
            bookmaker_name = bookmaker.get("title") or bookmaker.get("key")
            for market in bookmaker.get("markets") or []:
                if str(market.get("key") or "").lower() != "totals":
                    continue
                stamp = market.get("last_update") or bookmaker.get("last_update")
                for outcome in market.get("outcomes") or []:
                    if direction not in str(outcome.get("name") or "").upper():
                        continue
                    line = sf(outcome.get("point"), 0.0)
                    odd = sf(outcome.get("price"), 0.0)
                    if line > 0 and odd > 1.0:
                        candidates.append({"line": line, "odds": odd, "bookmaker": bookmaker_name, "timestamp": stamp})

        selected = self._select_candidate(candidates, target_line)
        if not selected:
            return self._empty("THE_ODDS_NO_TOTALS", direction, target_line)
        return self._make_result(selected, direction, target_line, model_probability, "THE_ODDS_API")

    def _resolve_sport_key(self, match: Dict[str, Any]) -> Optional[str]:
        direct = str(match.get("sport_key") or "").strip()
        if direct.startswith("soccer_"):
            return direct

        league_id = int(sf(match.get("league_id"), 0.0))
        expected = self.LEAGUE_TO_SPORT_KEY.get(league_id)
        sports = self._get_active_soccer_sports()
        keys = {str(x.get("key")): x for x in sports}
        if expected and (not sports or expected in keys):
            return expected

        if not sports:
            return None

        wanted = _norm(f"{match.get('country')} {match.get('league')}")
        best: Tuple[float, Optional[str]] = (0.0, None)
        for sport in sports:
            key = str(sport.get("key") or "")
            if not key.startswith("soccer_"):
                continue
            text = _norm(f"{sport.get('title')} {sport.get('description')} {key.replace('_', ' ')}")
            ratio = SequenceMatcher(None, wanted, text).ratio()
            wanted_tokens = set(wanted.split())
            text_tokens = set(text.split())
            overlap = len(wanted_tokens & text_tokens) / max(1, len(wanted_tokens))
            score = ratio * 0.55 + overlap * 0.45
            if score > best[0]:
                best = (score, key)
        return best[1] if best[0] >= 0.45 else None

    def _get_active_soccer_sports(self) -> List[Dict[str, Any]]:
        at, cached = self._sports_cache
        if cached and time.time() - at < 21600:
            return cached
        try:
            response = requests.get(f"{self.THE_ODDS_URL}/sports/", params={"apiKey": self.the_odds_key}, timeout=7)
            if response.status_code != 200:
                return cached
            data = response.json() if isinstance(response.json(), list) else []
            soccer = [x for x in data if str(x.get("key") or "").startswith("soccer_") and x.get("active", True)]
            self._sports_cache = (time.time(), soccer)
            return soccer
        except Exception:
            return cached

    def _match_event(self, events: List[Dict[str, Any]], match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        home = _norm(match.get("home_team"))
        away = _norm(match.get("away_team"))
        if not home or not away:
            return None
        best: Tuple[float, Optional[Dict[str, Any]]] = (0.0, None)
        for event in events or []:
            eh = _norm(event.get("home_team"))
            ea = _norm(event.get("away_team"))
            direct = (SequenceMatcher(None, home, eh).ratio() + SequenceMatcher(None, away, ea).ratio()) / 2.0
            swapped = (SequenceMatcher(None, home, ea).ratio() + SequenceMatcher(None, away, eh).ratio()) / 2.0
            score = max(direct, swapped)
            if score > best[0]:
                best = (score, event)
        return best[1] if best[0] >= 0.72 else None

    # ---------------- Generic helpers ----------------
    @staticmethod
    def _parse_line(text: str) -> Optional[float]:
        match = re.search(r"(?:OVER|UNDER)\s*([0-9]+(?:[\.,][0-9]+)?)", text, flags=re.I)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", "."))
        except Exception:
            return None

    def _from_existing_match(self, match: Dict[str, Any], direction: str, target_line: float, model_probability: float, reason: str = "MATCH_FALLBACK") -> Dict[str, Any]:
        odds = sf(match.get("odds") or match.get("odd") or match.get("cuota"), 0.0)
        line = sf(match.get("line") or match.get("market_line"), target_line)
        if odds <= 1.0:
            return self._empty(reason, direction, target_line)
        selected = {"line": line, "odds": odds, "bookmaker": match.get("bookmaker") or "MATCH_ATTACHED"}
        result = self._make_result(selected, direction, target_line, model_probability, "MATCH_ATTACHED")
        result["odds_status"] = reason
        return result

    def _store(self, key: str, result: Dict[str, Any]) -> Dict[str, Any]:
        self._cache[key] = {"at": time.time(), "result": dict(result)}
        return result

    @staticmethod
    def _empty(reason: str, direction: str, target_line: float) -> Dict[str, Any]:
        return {
            "odds_available": False,
            "odds_source": "NONE",
            "odds_status": reason,
            "market_direction": direction,
            "line": target_line,
            "odds": 0.0,
            "bookmaker": None,
            "implied_probability": 0.0,
            "model_probability_for_value": 0.0,
            "value_edge": 0.0,
            "expected_value": 0.0,
            "has_positive_value": False,
            "odds_timestamp": None,
            "odds_age_seconds": None,
            "target_line": target_line,
        }
