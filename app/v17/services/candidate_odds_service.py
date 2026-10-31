from __future__ import annotations

import logging
import math
import re
import time
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from app.config.config import Config
from app.services.api_quota_monitor import api_quota_monitor
from app.v17.services.odds_market_validator import extract_match_goals_totals
from app.v17.ai.poisson_market_math import half_goal_line_probability
from app.v17.services.odds_observation_store import OddsObservationStore

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
    2) Pre-match quotes are optional and informational, NEVER verified live.
    3) Other-provider totals are optional and not interchangeable with LIVE.
    4) An attached quote is unverified unless the native provider confirms it.

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
        self._live_bet_catalog: Dict[str, str] = {}
        self._live_bet_catalog_checked_at = 0.0
        self.observation_store = OddsObservationStore()

    def enrich(
        self,
        match: Dict[str, Any],
        market: str,
        model_probability: float = 0.0,
        math_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "").strip()
        direction = str(market or "").upper()
        current_total = int(sf(match.get("home_score"))) + int(sf(match.get("away_score")))
        # UNDER needs at least one full goal of margin to avoid a one-goal
        # fragility trap (e.g. at 2-0 consider Under 3.5, not Under 2.5).
        target_line = current_total + (1.5 if direction == "UNDER" else 0.5)

        if direction not in {"OVER", "UNDER"}:
            return self._empty("INVALID_MARKET", direction, target_line)
        if not Config.CANDIDATE_ODDS_ENABLED:
            return self._empty("DISABLED", direction, target_line)

        # Score revisions, goals and red cards invalidate old live prices.
        # The same TOTAL does not imply the same match state (VAR correction).
        home = int(sf(match.get("home_score"), 0))
        away = int(sf(match.get("away_score"), 0))
        red = int(sf(match.get("red_cards"), 0))
        cache_key = f"{fixture_id}:{direction}:{home}:{away}:{red}"
        now = time.time()
        cached = self._cache.get(cache_key)
        material_event = bool(match.get("post_goal_reanalysis") or match.get("score_changed_since_last_scan"))
        if cached and not material_event and now - sf(cached.get("at")) < self.ttl_seconds:
            return self._value_for_exact_line(
                dict(cached.get("result") or self._empty("CACHE_EMPTY", direction, target_line)),
                match, direction, math_evidence,
            )

        # 1. API-Football live market.
        if fixture_id and self.api_key and now >= self._cooldown_until:
            raw, status = self._api_football_request("/odds/live", {"fixture": fixture_id}, "odds_live_candidate")
            result = self._result_from_api_football(raw, direction, target_line, model_probability,
                                                    "API_FOOTBALL_LIVE_ODDS", fixture_id=fixture_id)
            if result.get("odds_available"):
                self.observation_store.record(fixture_id, result)
                return self._value_for_exact_line(self._store(cache_key, result), match, direction, math_evidence)
            if status == 429:
                self._cooldown_until = now + 300

            # 2. Si el live no ofrece totals, reutilizamos la cuota pre-match real del mismo fixture.
            # Es mejor que inventar una linea y se consulta unicamente para un candidato real.
            if status != 429 and bool(getattr(Config, "ODDS_PREMATCH_FALLBACK_ENABLED", False)):
                raw_pre, _ = self._api_football_request("/odds", {"fixture": fixture_id}, "odds_prematch_candidate")
                result = self._result_from_api_football(raw_pre, direction, target_line,
                                                        model_probability, "API_FOOTBALL_PREMATCH_ODDS",
                                                        fixture_id=fixture_id)
                if result.get("odds_available"):
                    return self._value_for_exact_line(self._store(cache_key, result), match, direction, math_evidence)

        # 3. Fallback de mercado independiente. Solo una liga compatible y con cache.
        if bool(getattr(Config, "THE_ODDS_FALLBACK_ENABLED", True)) and self.the_odds_key:
            result = self._from_the_odds_api(match, direction, target_line, model_probability)
            if result.get("odds_available"):
                return self._value_for_exact_line(self._store(cache_key, result), match, direction, math_evidence)

        # 4. Arbitrary fixture-attached odds are not guaranteed to be goals
        # markets. They are disabled unless explicitly opted in and typed.
        if bool(getattr(Config, "ODDS_ALLOW_ATTACHED_QUOTE", False)):
            if match.get("market_type") == "MATCH_GOALS_TOTAL" and match.get("market_period") == "FT":
                result = self._from_existing_match(match, direction, target_line, model_probability, "MATCH_ATTACHED_NOT_VERIFIED")
                return self._value_for_exact_line(self._store(cache_key, result), match, direction, math_evidence)
        return self._value_for_exact_line(
            self._store(cache_key, self._empty("NO_CERTIFIED_LIVE_MATCH_GOALS_TOTAL", direction, target_line)),
            match, direction, math_evidence,
        )

    @staticmethod
    def _poisson_line_win_probability(
        expected_goals_remaining: float,
        current_total: int,
        line: float,
        direction: str,
    ) -> Optional[float]:
        """Backwards-compatible wrapper over shared conditional FT math."""
        return half_goal_line_probability(expected_goals_remaining, current_total, line, direction)

    def _value_for_exact_line(
        self,
        result: Dict[str, Any],
        match: Dict[str, Any],
        direction: str,
        math_evidence: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate an actual LIVE FT quote first, then price the EXACT line.

        Quoted prices and model probabilities have independent provenance.
        No positive EV is output from uncalibrated, stale, unverified, stale
        or already-settled quotes. Research-only math can still be examined.
        """
        valued = dict(result)
        valued.update({
            "model_probability_for_value": None,
            "value_edge": 0.0,
            "expected_value": 0.0,
            "has_positive_value": False,
            "valuation_status": "NOT_VALIDATED",
            "quote_validation_status": "NOT_VERIFIED",
            "market_value_authorized": False,
        })
        if not valued.get("odds_available"):
            valued["valuation_status"] = "NO_REAL_ODDS"
            return valued
        if valued.get("odds_source") != "API_FOOTBALL_LIVE_ODDS" or valued.get("quote_is_live") is not True:
            valued["valuation_status"] = "QUOTE_NOT_LIVE"
            return valued
        if (valued.get("market_verified") is not True
                or valued.get("market_type") != "MATCH_GOALS_TOTAL"
                or valued.get("market_period") != "FT"):
            valued["valuation_status"] = "MARKET_UNVERIFIED"
            return valued
        if valued.get("fixture_verified") is not True:
            valued["valuation_status"] = "FIXTURE_UNVERIFIED"
            return valued
        if str(valued.get("market_direction") or "").upper() != direction:
            valued["valuation_status"] = "MARKET_DIRECTION_MISMATCH"
            return valued

        stamp = valued.get("odds_timestamp")
        if not stamp:
            valued["valuation_status"] = "QUOTE_TIMESTAMP_NOT_AVAILABLE"
            return valued
        try:
            quote_at = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            if quote_at.tzinfo is None:
                valued["valuation_status"] = "QUOTE_TIMESTAMP_HAS_NO_TIMEZONE"
                return valued
            age = (datetime.now(timezone.utc) - quote_at).total_seconds()
            valued["odds_age_seconds"] = round(age, 1)
            if age < -30 or age > sf(getattr(Config, "MAX_ODDS_AGE_SECONDS", 120), 120):
                valued["valuation_status"] = "STALE_ODDS"
                return valued
        except (TypeError, ValueError, OverflowError):
            valued["valuation_status"] = "QUOTE_TIMESTAMP_INVALID"
            return valued

        price = sf(valued.get("odds"), 0.0)
        line = sf(valued.get("line"), 0.0)
        if (not math.isfinite(price) or price <= 1.0
                or not math.isfinite(line)):
            valued["valuation_status"] = "INVALID_PRICE_OR_LINE"
            return valued
        minimum = sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50)
        maximum = sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10)
        if not minimum <= price <= maximum:
            valued["valuation_status"] = "PRICE_OUT_OF_ALLOWED_RANGE"
            return valued
        total = int(sf(match.get("home_score"), 0)) + int(sf(match.get("away_score"), 0))
        if (direction == "OVER" and line < total
                or direction == "UNDER" and line < total + 1):
            valued["valuation_status"] = "LINE_ALREADY_SETTLED_OR_UNSAFE"
            return valued
        valued["quote_validation_status"] = "VERIFIED_FRESH_LIVE_GOALS_FT"

        evidence = math_evidence or {}
        lam = evidence.get("expected_goals_remaining")
        if not isinstance(lam, (int, float)) or isinstance(lam, bool):
            valued["valuation_status"] = "MISSING_REMAINING_GOALS_MODEL"
            return valued
        p = self._poisson_line_win_probability(lam, total, line, direction)
        if p is None:
            valued["valuation_status"] = "UNSUPPORTED_SETTLEMENT_LINE"
            return valued
        valued["model_probability_for_value"] = round(p * 100.0, 2)
        valued["model_probability_method"] = "POISSON_EXACT_HALF_GOAL_LINE"
        if evidence.get("calibration_status") != "VALIDATED_OUT_OF_SAMPLE":
            valued["valuation_status"] = "MODEL_NOT_CALIBRATED"
            return valued

        # Financial valuation is defined only after quote authenticity and
        # independently validated probability are established.
        implied = 100.0 / price
        edge = p * 100.0 - implied
        ev = p * price - 1.0
        valued["implied_probability"] = round(implied, 2)
        valued["value_edge"] = round(edge, 2)
        valued["expected_value"] = round(ev, 4)
        valued["valuation_status"] = "VERIFIED_FRESH_CALIBRATED"
        valued["market_value_authorized"] = True
        valued["has_positive_value"] = bool(
            edge >= sf(getattr(Config, "EDGE_MIN_PERCENT", 5.0), 5.0)
            and ev >= sf(getattr(Config, "MIN_EXPECTED_VALUE", 0.03), 0.03)
        )
        return valued

    def _api_football_request(self, path: str, params: Dict[str, Any], monitor_name: str) -> Tuple[List[Any], int]:
        if bool(getattr(Config, "API_ECONOMY_MODE", True)):
            reserve = int(getattr(Config, "API_DAILY_RESERVE", 300))
            if not api_quota_monitor.can_spend(required=1, reserve=reserve):
                return [], 429
            status = api_quota_monitor.snapshot()
            if status.get("minute_remaining") == 0:
                # A stale minute-limit snapshot must not pause this provider
                # indefinitely after the minute window has reset.
                try:
                    updated = datetime.fromisoformat(str(status.get("last_updated_at")))
                    if (datetime.now(timezone.utc) - updated).total_seconds() < 60:
                        return [], 0
                except (TypeError, ValueError):
                    pass
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
            if not isinstance(body, dict) or body.get("errors"):
                return [], response.status_code
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
        fixture_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        live = source == "API_FOOTBALL_LIVE_ODDS"
        candidates = self._extract_totals(raw, direction, live=live, fixture_id=fixture_id)
        if live and not candidates and self._has_unlabelled_live_bets(raw):
            catalog = self._get_live_bet_catalog()
            candidates = self._extract_totals(raw, direction, live=True, fixture_id=fixture_id,
                                              market_catalog=catalog)
        # Never choose a full-time line already settled by the live score.
        if direction == "OVER":
            candidates = [c for c in candidates if sf(c.get("line")) > target_line - 0.5]
        else:
            candidates = [c for c in candidates if sf(c.get("line")) >= target_line - 0.5]
        selected = self._select_candidate(candidates, target_line)
        if not selected:
            return self._empty(f"{source}_NO_VALID_MATCH_GOALS_TOTAL", direction, target_line)
        return self._make_result(selected, direction, target_line, model_probability, source)

    @staticmethod
    def _has_unlabelled_live_bets(raw: Any) -> bool:
        return any(
            isinstance(bet, dict) and bet.get("id") is not None and not bet.get("name")
            for event in (raw if isinstance(raw, list) else [])
            if isinstance(event, dict)
            for bet in event.get("bets") or []
        )

    def _get_live_bet_catalog(self) -> Dict[str, str]:
        # Called only when a LIVE bet has an ID without a market label.
        # In-play IDs must never be resolved using /odds/bets (pre-match).
        now = time.time()
        if now - self._live_bet_catalog_checked_at < 86400:
            return self._live_bet_catalog
        self._live_bet_catalog_checked_at = now
        if not bool(getattr(Config, "ODDS_LIVE_BET_CATALOG_ENABLED", True)):
            return self._live_bet_catalog
        data, _ = self._api_football_request("/odds/live/bets", {}, "odds_live_bet_catalog")
        if data:
            self._live_bet_catalog = {
                str(row.get("id")): str(row.get("name"))
                for row in data if isinstance(row, dict) and row.get("id") is not None and row.get("name")
            }
        return self._live_bet_catalog

    def _extract_totals(
        self, raw: Any, direction: str, *, live: bool = False,
        fixture_id: Optional[str] = None, market_catalog: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        return extract_match_goals_totals(
            raw, direction, live=live, fixture_id=fixture_id, market_catalog=market_catalog,
        )

    def _select_candidate(self, candidates: List[Dict[str, Any]], target_line: float) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        low = sf(getattr(Config, "CUOTA_MINIMA", 1.50), 1.50)
        high = sf(getattr(Config, "CUOTA_MAXIMA", 2.10), 2.10)
        in_range = [x for x in candidates if low <= sf(x.get("odds")) <= high]
        pool = in_range or candidates
        pool.sort(key=lambda x: (
            abs(sf(x.get("line"), target_line) - target_line),
            0 if x.get("main") is True else 1,
            0 if x.get("fixture_verified") else 1,
            abs(sf(x.get("odds"), 0) - 1.80),
        ))
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
        # P(any additional goal) is NOT the price probability of an arbitrary
        # line (Over 3.5 / Under 4.5 etc). Valuation happens exactly once in
        # _value_for_exact_line using λ and the precise bookmaker line.
        return {
            "odds_available": odds > 1.0,
            "odds_source": source,
            "odds_status": "MATCH_GOALS_TOTAL_RECOGNIZED" if odds > 1.0 else "INVALID_ODDS",
            "verification_required": True,
            "market_id": selected.get("market_id"),
            "market_name": selected.get("market_name"),
            "market_period": selected.get("market_period"),
            "market_type": selected.get("market_type"),
            "market_verified": bool(selected.get("market_verified")),
            "fixture_verified": bool(selected.get("fixture_verified")),
            "quote_is_live": bool(selected.get("quote_is_live")),
            "odds_fixture_id": selected.get("fixture_id"),
            "market_direction": direction,
            "line": line,
            "odds": odds,
            "bookmaker": selected.get("bookmaker"),
            "implied_probability": round(implied, 2),
            "model_probability_for_value": None,
            "value_edge": 0.0,
            "expected_value": 0.0,
            "has_positive_value": False,
            "valuation_status": "NOT_VALUED_EXACT_LINE",
            # HTTP receipt time is *not* proof of quote freshness.
            "odds_timestamp": selected.get("timestamp"),
            "odds_received_at": datetime.now(timezone.utc).isoformat(),
            "odds_age_seconds": selected.get("age_seconds"),
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
                        candidates.append({"line": line, "odds": odd, "bookmaker": bookmaker_name, "timestamp": stamp,
                                           "quote_is_live": False, "market_verified": True,
                                           "market_type": "MATCH_GOALS_TOTAL", "market_period": "FT"})

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
        selected = {"line": line, "odds": odds, "bookmaker": match.get("bookmaker") or "MATCH_ATTACHED",
                    "quote_is_live": False, "market_verified": False, "fixture_verified": False}
        result = self._make_result(selected, direction, target_line, model_probability, "MATCH_ATTACHED")
        result["odds_status"] = reason
        return result

    def _store(self, key: str, result: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        self._cache[key] = {"at": now, "result": dict(result)}
        # The HP has only 4 GB of RAM. Avoid growing an unbounded dictionary
        # over several days of continuous worldwide fixtures.
        if len(self._cache) > 1200:
            self._cache = {
                k: v for k, v in self._cache.items()
                if now - sf(v.get("at")) < max(self.ttl_seconds * 2, 180)
            }
        return result

    @staticmethod
    def _empty(reason: str, direction: str, target_line: float) -> Dict[str, Any]:
        return {
            "odds_available": False,
            "odds_source": "NONE",
            "odds_status": reason,
            "market_id": None,
            "market_name": None,
            "market_type": None,
            "market_period": None,
            "market_verified": False,
            "fixture_verified": False,
            "quote_is_live": False,
            "market_direction": direction,
            "line": target_line,
            "odds": 0.0,
            "bookmaker": None,
            "implied_probability": 0.0,
            "model_probability_for_value": 0.0,
            "value_edge": 0.0,
            "expected_value": 0.0,
            "has_positive_value": False,
            "verification_required": True,
            "odds_timestamp": None,
            "odds_age_seconds": None,
            "target_line": target_line,
        }
