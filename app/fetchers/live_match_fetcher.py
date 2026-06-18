from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List

import requests

from app.config.config import Config
from app.v17.core.league_filter import LeagueFilter

logger = logging.getLogger(__name__)


class LiveMatchFetcher:
    API_BASE = "https://v3.football.api-sports.io"
    API_FOOTBALL_LIVE_URL = f"{API_BASE}/fixtures?live=all"
    API_FOOTBALL_STATISTICS_URL = f"{API_BASE}/fixtures/statistics"
    API_FOOTBALL_EVENTS_URL = f"{API_BASE}/fixtures/events"
    API_FOOTBALL_PLAYERS_URL = f"{API_BASE}/fixtures/players"
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4/matches"

    LIVE_CACHE_TTL_SECONDS = 30
    STATS_CACHE_TTL_SECONDS = 60
    EVENTS_CACHE_TTL_SECONDS = 60
    PLAYERS_CACHE_TTL_SECONDS = 300

    # V17 DEBUG RAW API
    # Guarda respuestas crudas de API-Football para auditar qué datos reales
    # entrega cada endpoint antes de tocar la lógica de predicción.
    # Se puede desactivar con variable de entorno JHONNY_DEBUG_API_RAW=0.
    DEBUG_RAW_ENV = "JHONNY_DEBUG_API_RAW"
    DEBUG_RAW_DIR_ENV = "JHONNY_DEBUG_API_RAW_DIR"
    DEBUG_RAW_DEFAULT_DIR = "debug_api_football"

    MAX_DEEP_SCAN_MATCHES = 6

    MAX_OPERABLE_MINUTE = 97
    MAX_TRACKING_MINUTE = 130

    API_429_COOLDOWN_SECONDS = 300
    BACKUP_TIMEOUT_SECONDS = 8
    PRIMARY_TIMEOUT_SECONDS = 10
    STATS_TIMEOUT_SECONDS = 8
    EVENTS_TIMEOUT_SECONDS = 8
    PLAYERS_TIMEOUT_SECONDS = 10

    CLOCK_STALE_SECONDS = 90
    CLOCK_FROZEN_SECONDS = 120

    BLOCKED_STATUS_SHORT = {
        "HT", "FT", "AET", "PEN", "PST", "CANC",
        "ABD", "AWD", "WO", "SUSP", "INT",
    }

    BLOCKED_STATUS_LONG = {
        "HALFTIME",
        "MATCH FINISHED",
        "FINISHED",
        "AFTER EXTRA TIME",
        "PENALTY IN PROGRESS",
        "POSTPONED",
        "CANCELLED",
        "ABANDONED",
        "SUSPENDED",
        "INTERRUPTED",
    }

    LIVE_STATUS_SHORT = {"1H", "2H", "ET", "LIVE"}
    LIVE_STATUS_LONG_HINTS = {
        "FIRST HALF",
        "SECOND HALF",
        "EXTRA TIME",
        "LIVE",
        "IN PLAY",
    }

    def __init__(self) -> None:
        self.api_football_headers = {
            "x-apisports-key": Config.API_FOOTBALL_KEY,
        }

        self.football_data_headers = {
            "X-Auth-Token": Config.FOOTBALL_DATA_KEY,
        }

        self._live_cache: List[Dict[str, Any]] = []
        self._live_cache_at: float = 0.0
        self._stats_cache: Dict[str, Dict[str, Any]] = {}
        self._events_cache: Dict[str, Dict[str, Any]] = {}
        self._players_cache: Dict[str, Dict[str, Any]] = {}
        self._api_football_cooldown_until: float = 0.0

        self._clock_memory: Dict[str, Dict[str, Any]] = {}

        self._allowed_league_ids = set(
            getattr(Config, "API_FOOTBALL_ALLOWED_LEAGUES", [])
            or getattr(Config, "LIVE_ALLOWED_LEAGUE_IDS", [])
            or []
        )

        # V17.1: IDs internacionales que nunca deben perderse por lista cerrada.
        # Esto protege Mundial, eliminatorias y torneos FIFA/selecciones cuando
        # API-Football devuelve league_id fuera de la lista principal.
        self._force_allow_international_league_ids = set(
            getattr(Config, "FORCE_ALLOW_INTERNATIONAL_LEAGUE_IDS", [])
            or []
        )

        self.league_filter = LeagueFilter()

        self.debug_raw_enabled = self._debug_raw_enabled()
        self.debug_raw_dir = self._debug_raw_dir()
        if self.debug_raw_enabled:
            try:
                self.debug_raw_dir.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "LIVE_FETCHER DEBUG RAW activo. Carpeta=%s",
                    self.debug_raw_dir,
                )
            except Exception as exc:
                logger.warning(
                    "LIVE_FETCHER DEBUG RAW no pudo crear carpeta=%s | error=%s",
                    self.debug_raw_dir,
                    exc,
                )

    def _debug_raw_enabled(self) -> bool:
        """
        Activa/desactiva el guardado de respuestas RAW.

        Prioridad:
        1) Config.API_FOOTBALL_DEBUG_RAW, si existe.
        2) Variable de entorno JHONNY_DEBUG_API_RAW.
        3) Activo por defecto para esta versión de auditoría.
        """
        try:
            config_value = getattr(Config, "API_FOOTBALL_DEBUG_RAW", None)
            if config_value is not None:
                return bool(config_value)

            env_value = os.getenv(self.DEBUG_RAW_ENV, "1").strip().lower()
            return env_value not in {"0", "false", "no", "off", "disabled"}
        except Exception:
            return True

    def _debug_raw_dir(self) -> Path:
        try:
            config_dir = getattr(Config, "API_FOOTBALL_DEBUG_RAW_DIR", None)
            raw_dir = config_dir or os.getenv(self.DEBUG_RAW_DIR_ENV) or self.DEBUG_RAW_DEFAULT_DIR
            return Path(raw_dir).resolve()
        except Exception:
            return Path(self.DEBUG_RAW_DEFAULT_DIR).resolve()

    def _save_api_raw_debug(
        self,
        *,
        endpoint: str,
        payload: Any,
        fixture_id: Any = None,
        extra: Dict[str, Any] | None = None,
    ) -> None:
        """
        Guarda respuestas crudas de API-Football sin modificar la lógica V17.

        Objetivo:
        - Saber qué campos reales entrega la API por endpoint.
        - Diferenciar dato real en cero vs dato no disponible.
        - Comparar RAW API-Football vs snapshot normalizado de V17.
        """
        if not self.debug_raw_enabled:
            return

        try:
            self.debug_raw_dir.mkdir(parents=True, exist_ok=True)

            safe_endpoint = str(endpoint or "unknown").replace("/", "_").replace("?", "_")
            fixture_part = str(fixture_id) if fixture_id is not None else "all_live"
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            filename = f"{timestamp}_{fixture_part}_{safe_endpoint}.json"
            output_path = self.debug_raw_dir / filename

            body = {
                "debug_type": "API_FOOTBALL_RAW_RESPONSE",
                "endpoint": endpoint,
                "fixture_id": fixture_id,
                "saved_at_utc": timestamp,
                "extra": extra or {},
                "payload": payload,
            }

            with output_path.open("w", encoding="utf-8") as fh:
                json.dump(body, fh, ensure_ascii=False, indent=2, default=str)

            logger.info(
                "LIVE_FETCHER DEBUG RAW guardado | endpoint=%s | fixture=%s | file=%s",
                endpoint,
                fixture_id,
                output_path,
            )
        except Exception as exc:
            logger.warning(
                "LIVE_FETCHER DEBUG RAW error guardando endpoint=%s fixture=%s | error=%s",
                endpoint,
                fixture_id,
                exc,
            )

    def get_live_matches(self) -> List[Dict[str, Any]]:
        return self.fetch_live_data()

    def fetch_live_data(self) -> List[Dict[str, Any]]:
        now = time.time()

        if self._live_cache and (now - self._live_cache_at) < self.LIVE_CACHE_TTL_SECONDS:
            logger.info(
                "LIVE_FETCHER: usando live cache (%s partidos).",
                len(self._live_cache),
            )
            return self._clone_list_with_age(self._live_cache)

        if now < self._api_football_cooldown_until:
            remaining = int(self._api_football_cooldown_until - now)
            logger.warning(
                "LIVE_FETCHER: API-Football en cooldown por rate limit. Esperando %ss.",
                remaining,
            )

            backup_matches = self._fetch_from_football_data()
            if backup_matches:
                self._store_live_cache(backup_matches)
                return self._clone_list_with_age(backup_matches)

            if self._live_cache:
                logger.warning(
                    "LIVE_FETCHER: devolviendo última cache disponible por cooldown."
                )
                return self._clone_list_with_age(self._live_cache)

            return []

        primary_matches = self._fetch_from_api_football()
        if primary_matches:
            self._store_live_cache(primary_matches)
            return self._clone_list_with_age(primary_matches)

        logger.warning(
            "LIVE_FETCHER: API-Football sin datos útiles. Probando backup football-data.org..."
        )

        backup_matches = self._fetch_from_football_data()
        if backup_matches:
            self._store_live_cache(backup_matches)
            return self._clone_list_with_age(backup_matches)

        if self._live_cache:
            logger.warning(
                "LIVE_FETCHER: ninguna fuente devolvió datos válidos. Devolviendo última cache disponible."
            )
            return self._clone_list_with_age(self._live_cache)

        logger.warning(
            "LIVE_FETCHER: ninguna fuente devolvió partidos válidos y no existe cache previa."
        )
        return []

    def _fetch_from_api_football(self) -> List[Dict[str, Any]]:
        if not Config.API_FOOTBALL_KEY:
            logger.warning("LIVE_FETCHER: API_FOOTBALL_KEY no configurada.")
            return []

        try:
            logger.info("LIVE_FETCHER: solicitando partidos en vivo a API-Football...")

            response = requests.get(
                self.API_FOOTBALL_LIVE_URL,
                headers=self.api_football_headers,
                timeout=self.PRIMARY_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                self._activate_429_cooldown()
                logger.error("LIVE_FETCHER: API-Football respondió 429 Too Many Requests.")
                return []

            if response.status_code != 200:
                logger.error(
                    "LIVE_FETCHER API-Football status %s: %s",
                    response.status_code,
                    response.text,
                )
                return []

            data = response.json()
            self._save_api_raw_debug(
                endpoint="fixtures_live",
                payload=data,
                extra={"url": self.API_FOOTBALL_LIVE_URL},
            )
            raw_matches = data.get("response", []) or []

            logger.info(
                "LIVE_FETCHER: partidos crudos recibidos=%s | results=%s",
                len(raw_matches),
                data.get("results", 0),
            )

            if not raw_matches:
                return []

            normalized = self._normalize_api_football(raw_matches)
            logger.info("LIVE_FETCHER: partidos normalizados válidos=%s", len(normalized))
            return normalized

        except Exception as exc:
            logger.exception("LIVE_FETCHER API-Football error: %s", exc)
            return []

    def _fetch_fixture_statistics(
        self,
        fixture_id: Any,
        should_fetch: bool = True,
    ) -> List[Dict[str, Any]]:
        if not fixture_id:
            return []

        fixture_key = str(fixture_id)
        now = time.time()

        cached = self._stats_cache.get(fixture_key)
        if cached and (now - cached["at"]) < self.STATS_CACHE_TTL_SECONDS:
            return self._clone_list(cached["data"])

        if not should_fetch:
            return self._clone_list(cached["data"]) if cached else []

        if now < self._api_football_cooldown_until:
            return self._clone_list(cached["data"]) if cached else []

        try:
            response = requests.get(
                self.API_FOOTBALL_STATISTICS_URL,
                headers=self.api_football_headers,
                params={"fixture": fixture_id},
                timeout=self.STATS_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                self._activate_429_cooldown()
                logger.warning("LIVE_FETCHER stats fixture=%s -> 429", fixture_id)
                return self._clone_list(cached["data"]) if cached else []

            if response.status_code != 200:
                logger.warning(
                    "LIVE_FETCHER stats fixture=%s status=%s",
                    fixture_id,
                    response.status_code,
                )
                return self._clone_list(cached["data"]) if cached else []

            data = response.json()
            self._save_api_raw_debug(
                endpoint="fixtures_statistics",
                fixture_id=fixture_id,
                payload=data,
                extra={"params": {"fixture": fixture_id}},
            )
            result = data.get("response", []) or []

            self._stats_cache[fixture_key] = {
                "at": now,
                "data": self._clone_list(result),
            }

            return self._clone_list(result)

        except Exception as exc:
            logger.warning("LIVE_FETCHER stats error fixture=%s: %s", fixture_id, exc)
            return self._clone_list(cached["data"]) if cached else []

    def _fetch_fixture_events(
        self,
        fixture_id: Any,
        should_fetch: bool = True,
    ) -> List[Dict[str, Any]]:
        if not fixture_id:
            return []

        fixture_key = str(fixture_id)
        now = time.time()

        cached = self._events_cache.get(fixture_key)
        if cached and (now - cached["at"]) < self.EVENTS_CACHE_TTL_SECONDS:
            return self._clone_list(cached["data"])

        if not should_fetch:
            return self._clone_list(cached["data"]) if cached else []

        if now < self._api_football_cooldown_until:
            return self._clone_list(cached["data"]) if cached else []

        try:
            response = requests.get(
                self.API_FOOTBALL_EVENTS_URL,
                headers=self.api_football_headers,
                params={"fixture": fixture_id},
                timeout=self.EVENTS_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                self._activate_429_cooldown()
                logger.warning("LIVE_FETCHER events fixture=%s -> 429", fixture_id)
                return self._clone_list(cached["data"]) if cached else []

            if response.status_code != 200:
                logger.warning(
                    "LIVE_FETCHER events fixture=%s status=%s",
                    fixture_id,
                    response.status_code,
                )
                return self._clone_list(cached["data"]) if cached else []

            data = response.json()
            self._save_api_raw_debug(
                endpoint="fixtures_events",
                fixture_id=fixture_id,
                payload=data,
                extra={"params": {"fixture": fixture_id}},
            )
            result = data.get("response", []) or []

            self._events_cache[fixture_key] = {
                "at": now,
                "data": self._clone_list(result),
            }

            return self._clone_list(result)

        except Exception as exc:
            logger.warning("LIVE_FETCHER events error fixture=%s: %s", fixture_id, exc)
            return self._clone_list(cached["data"]) if cached else []

    def _fetch_fixture_players(
        self,
        fixture_id: Any,
        should_fetch: bool = True,
    ) -> List[Dict[str, Any]]:
        if not fixture_id:
            return []

        fixture_key = str(fixture_id)
        now = time.time()

        cached = self._players_cache.get(fixture_key)
        if cached and (now - cached["at"]) < self.PLAYERS_CACHE_TTL_SECONDS:
            return self._clone_list(cached["data"])

        if not should_fetch:
            return self._clone_list(cached["data"]) if cached else []

        if now < self._api_football_cooldown_until:
            return self._clone_list(cached["data"]) if cached else []

        try:
            response = requests.get(
                self.API_FOOTBALL_PLAYERS_URL,
                headers=self.api_football_headers,
                params={"fixture": fixture_id},
                timeout=self.PLAYERS_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                self._activate_429_cooldown()
                logger.warning("LIVE_FETCHER players fixture=%s -> 429", fixture_id)
                return self._clone_list(cached["data"]) if cached else []

            if response.status_code != 200:
                logger.warning(
                    "LIVE_FETCHER players fixture=%s status=%s",
                    fixture_id,
                    response.status_code,
                )
                return self._clone_list(cached["data"]) if cached else []

            data = response.json()
            self._save_api_raw_debug(
                endpoint="fixtures_players",
                fixture_id=fixture_id,
                payload=data,
                extra={"params": {"fixture": fixture_id}},
            )
            result = data.get("response", []) or []

            self._players_cache[fixture_key] = {
                "at": now,
                "data": self._clone_list(result),
            }

            return self._clone_list(result)

        except Exception as exc:
            logger.warning("LIVE_FETCHER players error fixture=%s: %s", fixture_id, exc)
            return self._clone_list(cached["data"]) if cached else []

    def _should_bypass_allowed_league_ids(self, item: Dict[str, Any], league_id: Any) -> bool:
        """
        Permite que competiciones internacionales prioritarias pasen aunque
        API_FOOTBALL_ALLOWED_LEAGUES sea una lista cerrada.

        Motivo:
        - El filtro por league_id ocurre antes del motor V17.
        - Si el Mundial/FIFA/selecciones no está en la lista cerrada, el partido
          desaparece aunque LeagueFilter lo considere permitido.
        - Esta excepción solo aplica a competiciones internacionales claramente
          prioritarias o IDs forzados desde Config.
        """
        try:
            if league_id in self._force_allow_international_league_ids:
                return True

            league = item.get("league", {}) if isinstance(item, dict) else {}
            if not isinstance(league, dict):
                league = {}

            league_name = str(league.get("name") or "").upper()
            country = str(league.get("country") or "").upper()
            combined = f"{league_name} {country}"

            international_terms = {
                "WORLD CUP",
                "FIFA WORLD CUP",
                "COPA MUNDIAL",
                "MUNDIAL",
                "WORLD CUP QUALIFICATION",
                "WORLD CUP QUALIFIERS",
                "QUALIFIERS",
                "UEFA NATIONS LEAGUE",
                "NATIONS LEAGUE",
                "EURO",
                "COPA AMERICA",
                "COPA AMÉRICA",
                "AFRICA CUP",
                "ASIAN CUP",
                "GOLD CUP",
                "CONCACAF",
                "INTERNATIONAL",
                "FIFA",
            }

            return any(term in combined for term in international_terms)

        except Exception as exc:
            logger.warning(
                "LIVE_FETCHER: error evaluando bypass internacional league_id=%s | error=%s",
                league_id,
                exc,
            )
            return False

    def _is_priority_league(self, raw_match: Dict[str, Any]) -> bool:
        try:
            if not isinstance(raw_match, dict):
                return False

            result = self.league_filter.evaluate(raw_match)

            if result.get("league_allowed"):
                return True

            fixture = raw_match.get("fixture", {}) or {}
            league = raw_match.get("league", {}) or {}
            teams = raw_match.get("teams", {}) or {}

            home = (teams.get("home") or {}).get("name")
            away = (teams.get("away") or {}).get("name")

            logger.info(
                "LIVE_FETCHER: fixture=%s descartado por filtro de liga | %s vs %s | liga=%s | país=%s | motivo=%s",
                fixture.get("id"),
                home,
                away,
                league.get("name"),
                league.get("country"),
                result.get("league_filter_reason"),
            )

            return False

        except Exception as exc:
            logger.warning(
                "LIVE_FETCHER: error evaluando filtro de liga. Se permite por seguridad | error=%s",
                exc,
            )
            return True

    def _normalize_api_football(self, raw_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_list: List[Dict[str, Any]] = []
        deep_scan_used = 0
        blocked_by_league = 0

        for item in raw_matches:
            try:
                fixture = item.get("fixture", {}) or {}
                league = item.get("league", {}) or {}
                teams = item.get("teams", {}) or {}
                goals = item.get("goals", {}) or {}
                status = fixture.get("status", {}) or {}

                fixture_id = fixture.get("id")
                if not fixture_id:
                    continue

                if not self._is_priority_league(item):
                    blocked_by_league += 1
                    continue

                league_id = league.get("id")
                if (
                    self._allowed_league_ids
                    and league_id not in self._allowed_league_ids
                    and not self._should_bypass_allowed_league_ids(item=item, league_id=league_id)
                ):
                    logger.info(
                        "LIVE_FETCHER: fixture=%s descartado por league_id=%s",
                        fixture_id,
                        league_id,
                    )
                    continue

                status_short = str(status.get("short") or "").upper()
                status_long = str(status.get("long") or "").upper()
                minute = self._safe_int(status.get("elapsed"))
                elapsed_plus = self._safe_int(status.get("extra"))

                if status_short in self.BLOCKED_STATUS_SHORT:
                    logger.info(
                        "LIVE_FETCHER: fixture=%s descartado por status_short=%s",
                        fixture_id,
                        status_short,
                    )
                    continue

                if status_long in self.BLOCKED_STATUS_LONG:
                    logger.info(
                        "LIVE_FETCHER: fixture=%s descartado por status_long=%s",
                        fixture_id,
                        status_long,
                    )
                    continue

                if status_short not in self.LIVE_STATUS_SHORT:
                    logger.info(
                        "LIVE_FETCHER: fixture=%s descartado por status no vivo=%s",
                        fixture_id,
                        status_short,
                    )
                    continue

                if minute <= 0 or minute > self.MAX_TRACKING_MINUTE:
                    logger.info(
                        "LIVE_FETCHER: fixture=%s descartado por minuto inválido=%s",
                        fixture_id,
                        minute,
                    )
                    continue

                tracking_only = minute > self.MAX_OPERABLE_MINUTE
                is_late_game = minute >= 75
                is_added_time = elapsed_plus > 0

                should_fetch_deep = (
                    deep_scan_used < self.MAX_DEEP_SCAN_MATCHES
                    and self._should_fetch_detailed_stats(item, minute)
                    and not tracking_only
                )

                should_fetch_players = (
                    deep_scan_used < self.MAX_DEEP_SCAN_MATCHES
                    and self._should_fetch_player_stats(minute)
                    and not tracking_only
                )

                if should_fetch_deep:
                    deep_scan_used += 1

                home_team = teams.get("home", {}) or {}
                away_team = teams.get("away", {}) or {}

                home_name = home_team.get("name") or "HOME"
                away_name = away_team.get("name") or "AWAY"

                statistics = self._fetch_fixture_statistics(
                    fixture_id=fixture_id,
                    should_fetch=should_fetch_deep,
                )

                events = self._fetch_fixture_events(
                    fixture_id=fixture_id,
                    should_fetch=should_fetch_deep or tracking_only or is_late_game,
                )

                players = self._fetch_fixture_players(
                    fixture_id=fixture_id,
                    should_fetch=should_fetch_players,
                )

                home_stats = self._extract_team_stats_api_football(statistics, 0)
                away_stats = self._extract_team_stats_api_football(statistics, 1)

                totals = self._build_totals(home_stats, away_stats)
                data_quality = self._classify_data_quality(home_stats, away_stats, totals)
                has_live_stats = self._has_real_live_stats(home_stats, away_stats, totals)

                home_score = self._safe_int(goals.get("home"))
                away_score = self._safe_int(goals.get("away"))

                is_scannable = self._is_scannable_match(
                    minute=minute,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    totals=totals,
                )

                scan_phase = self._scan_phase(
                    minute=minute,
                    is_scannable=is_scannable,
                    has_live_stats=has_live_stats,
                    totals=totals,
                )

                home_logo = home_team.get("logo")
                away_logo = away_team.get("logo")
                league_logo = league.get("logo")
                country_flag = league.get("flag")

                now_ts = time.time()
                now_iso = datetime.now().isoformat(timespec="seconds")
                score_text = f"{home_score}-{away_score}"

                clock_fields = self._build_live_clock_fields(
                    fixture_id=fixture_id,
                    minute=minute,
                    score=score_text,
                    status_short=status_short,
                    status_long=status_long,
                    fetched_at=now_ts,
                    source="api_football",
                )

                # Ejecutar cálculos avanzados analíticos propios del sistema JHONNY_ELITE
                analytics = self._calculate_advanced_analytics(minute, home_score, away_score, home_stats, away_stats, totals)

                normalized = {
                    "match_id": fixture_id,
                    "fixture_id": fixture_id,
                    "id": fixture_id,
                    "match_name": f"{home_name} vs {away_name}",
                    "partido": f"{home_name} vs {away_name}",
                    "home_name": home_name,
                    "away_name": away_name,
                    "home_team": home_name,
                    "away_team": away_name,
                    "home": home_name,
                    "away": away_name,
                    "home_id": home_team.get("id"),
                    "away_id": away_team.get("id"),
                    "league_id": league_id,

                    "home_logo": home_logo,
                    "away_logo": away_logo,
                    "league_logo": league_logo,
                    "country_flag": country_flag,
                    "home_team_logo": home_logo,
                    "away_team_logo": away_logo,
                    "local_logo": home_logo,
                    "visitor_logo": away_logo,
                    "competition_logo": league_logo,
                    "league_flag": country_flag,
                    "flag": country_flag,

                    "league": league.get("name") or "Desconocida",
                    "liga": league.get("name") or "Desconocida",
                    "country": league.get("country") or "Desconocido",
                    "país": league.get("country") or "Desconocido",

                    "league_allowed": True,
                    "league_filter_status": "ALLOWED_PRIORITY_LEAGUE",
                    "league_filter_source": "live_fetcher",

                    "minute": minute,
                    "minuto": minute,
                    "source_minute": minute,
                    "api_elapsed": minute,
                    "elapsed_plus": elapsed_plus,
                    "added_time": elapsed_plus,
                    "is_added_time": is_added_time,
                    "is_late_game": is_late_game,
                    "status_short": status_short,
                    "status_long": status_long,

                    "home_score": home_score,
                    "away_score": away_score,
                    "local_score": home_score,
                    "visitante_score": away_score,
                    "score": score_text,
                    "marcador": score_text,

                    "dangerous_attacks": totals["dangerous_attacks"],
                    "shots": totals["shots"],
                    "shots_on_target": totals["shots_on_target"],
                    "shots_off_goal": totals.get("shots_off_goal", 0.0),
                    "blocked_shots": totals.get("blocked_shots", 0.0),
                    "shots_inside_box": totals.get("shots_inside_box", 0.0),
                    "shots_outside_box": totals.get("shots_outside_box", 0.0),
                    "corners": totals["corners"],
                    "xg": round(totals["xg"], 2),
                    "xG": round(totals["xg"], 2),
                    "xg_available": totals.get("xg_available", False),
                    "red_cards": totals["red_cards"],
                    "yellow_cards": totals.get("yellow_cards", 0.0),
                    "fouls": totals.get("fouls", 0.0),
                    "offsides": totals.get("offsides", 0.0),
                    "goalkeeper_saves": totals.get("goalkeeper_saves", 0.0),
                    "total_passes": totals.get("total_passes", 0.0),
                    "passes_accurate": totals.get("passes_accurate", 0.0),
                    "goals_prevented": totals.get("goals_prevented", 0.0),
                    "goals_prevented_available": totals.get("goals_prevented_available", False),
                    "available_stat_fields_count": totals.get("available_stat_fields_count", 0),
                    "missing_stat_fields_count": totals.get("missing_stat_fields_count", 0),

                    "possession_home": home_stats["possession"],
                    "possession_away": away_stats["possession"],
                    "posesión_local": home_stats["possession"],
                    "posesión_visitante": away_stats["possession"],

                    "home_stats": {
                        **home_stats,
                        "xg": home_stats["xG"],
                    },
                    "away_stats": {
                        **away_stats,
                        "xg": away_stats["xG"],
                    },

                    "events": events,
                    "event_count": len(events),
                    "players": players,
                    "player_count": sum(
                        len(team.get("players", []))
                        for team in players
                        if isinstance(team, dict)
                    ),

                    "data_quality": data_quality,
                    "calidad_datos": data_quality,
                    "has_live_stats": has_live_stats,
                    "tiene_estadísticas_en_vivo": has_live_stats,
                    "is_scannable": is_scannable,
                    "es_escaneable": is_scannable,

                    "scan_phase": scan_phase["scan_phase"],
                    "scan_reason": scan_phase["scan_reason"],
                    "can_publish_signal": scan_phase["can_publish_signal"],
                    "can_observe_signal": scan_phase["can_observe_signal"],

                    "stats_source": (
                        "api_football_fixture_statistics"
                        if has_live_stats
                        else "api_football_fixture_only"
                    ),
                    "fuente_estadísticas": (
                        "api_football_fixture_statistics"
                        if has_live_stats
                        else "api_football_fixture_only"
                    ),

                    "deep_scan_enabled": should_fetch_deep,
                    "players_scan_enabled": should_fetch_players,
                    "tracking_only": tracking_only,
                    "operable": not tracking_only,
                    "confidence": self._estimate_confidence(data_quality, totals),
                    "prob_real": self._estimate_prob_real(data_quality, totals),
                    "source": "api_football",

                    # Asignación de variables analíticas avanzadas calculadas
                    "ai_score": analytics["ai_score"],
                    "goal_probability": analytics["goal_probability"],
                    "over_probability": analytics["over_probability"],
                    "under_probability": analytics["under_probability"],
                    "momentum_label": analytics["momentum_label"],
                    "risk_level": analytics["risk_level"],
                    "dominance": analytics["dominance"],
                    "goal_evidence_score": analytics.get("goal_evidence_score", 0.0),
                    "volume_score": analytics.get("volume_score", 0.0),

                    "sync_updated_at": now_ts,
                    "sync_updated_at_iso": now_iso,
                    "fetched_at": now_ts,
                    "fetched_at_iso": now_iso,

                    **clock_fields,
                }

                normalized_list.append(normalized)

            except Exception as exc:
                logger.warning("NORMALIZATION_ERROR API-Football: %s", exc)
                continue

        logger.info(
            "LIVE_FETCHER: filtro profundo aplicado | recibidos=%s | normalizados=%s | bloqueados_por_liga=%s | deep_scan_usados=%s/%s",
            len(raw_matches or []),
            len(normalized_list),
            blocked_by_league,
            deep_scan_used,
            self.MAX_DEEP_SCAN_MATCHES,
        )

        return normalized_list

    def _normalize_football_data(self, raw_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_list: List[Dict[str, Any]] = []

        for item in raw_matches:
            try:
                status_text = str(item.get("status") or "").upper()

                if status_text not in {"IN_PLAY", "LIVE"}:
                    continue

                home_team = item.get("homeTeam", {}) or {}
                away_team = item.get("awayTeam", {}) or {}
                competition = item.get("competition", {}) or {}
                score_data = item.get("score", {}) or {}
                full_time = score_data.get("fullTime", {}) or {}

                home_name = home_team.get("name") or "HOME"
                away_name = away_team.get("name") or "AWAY"

                home_score = self._safe_int(full_time.get("home"))
                away_score = self._safe_int(full_time.get("away"))
                minute = self._estimate_minute_from_status(item)

                if minute <= 0 or minute > self.MAX_TRACKING_MINUTE:
                    continue

                backup_probe = {
                    "league": competition.get("name"),
                    "country": ((competition.get("area") or {}).get("name")) or "",
                    "home_team": home_name,
                    "away_team": away_name,
                }

                league_result = self.league_filter.evaluate(backup_probe)
                if not league_result.get("league_allowed"):
                    logger.info(
                        "LIVE_FETCHER backup: descartado por filtro de liga | %s vs %s | liga=%s | país=%s | motivo=%s",
                        home_name,
                        away_name,
                        competition.get("name"),
                        ((competition.get("area") or {}).get("name")) or "",
                        league_result.get("league_filter_reason"),
                    )
                    continue

                tracking_only = minute > self.MAX_OPERABLE_MINUTE
                is_late_game = minute >= 75

                # Al ser canal de respaldo secundario sin estadísticas vivas nativas, inicializamos la matriz base
                home_stats = {
                    "possession": 50.0,
                    "shots": 0.0,
                    "shots_on_target": 0.0,
                    "corners": 0.0,
                    "dangerous_attacks": 0.0,
                    "red_cards": 0.0,
                    "xG": 0.0,
                }

                away_stats = {
                    "possession": 50.0,
                    "shots": 0.0,
                    "shots_on_target": 0.0,
                    "corners": 0.0,
                    "dangerous_attacks": 0.0,
                    "red_cards": 0.0,
                    "xG": 0.0,
                }

                totals = self._build_totals(home_stats, away_stats)
                data_quality = "LOW_BACKUP"
                has_live_stats = False
                is_scannable = False

                scan_phase = self._scan_phase(
                    minute=minute,
                    is_scannable=is_scannable,
                    has_live_stats=has_live_stats,
                    totals=totals,
                )

                home_logo = home_team.get("crest")
                away_logo = away_team.get("crest")
                league_logo = competition.get("emblem")
                now_ts = time.time()
                now_iso = datetime.now().isoformat(timespec="seconds")
                score_text = f"{home_score}-{away_score}"

                clock_fields = self._build_live_clock_fields(
                    fixture_id=item.get("id"),
                    minute=minute,
                    score=score_text,
                    status_short=status_text,
                    status_long=status_text,
                    fetched_at=now_ts,
                    source="football_data_backup",
                    low_confidence=True,
                )

                # Ejecutar estimaciones analíticas adaptativas para canales de respaldo de baja calidad
                analytics = self._calculate_advanced_analytics(minute, home_score, away_score, home_stats, away_stats, totals)

                normalized_list.append(
                    {
                        "match_id": item.get("id"),
                        "fixture_id": item.get("id"),
                        "id": item.get("id"),
                        "match_name": f"{home_name} vs {away_name}",
                        "partido": f"{home_name} vs {away_name}",
                        "home_name": home_name,
                        "away_name": away_name,
                        "home_team": home_name,
                        "away_team": away_name,
                        "home": home_name,
                        "away": away_name,

                        "home_logo": home_logo,
                        "away_logo": away_logo,
                        "league_logo": league_logo,
                        "country_flag": None,
                        "home_team_logo": home_logo,
                        "away_team_logo": away_logo,
                        "local_logo": home_logo,
                        "visitor_logo": away_logo,
                        "competition_logo": league_logo,
                        "league_flag": None,
                        "flag": None,

                        "league": competition.get("name") or "Desconocida",
                        "liga": competition.get("name") or "Desconocida",
                        "country": ((competition.get("area") or {}).get("name")) or "Desconocido",
                        "país": ((competition.get("area") or {}).get("name")) or "Desconocido",

                        "league_allowed": True,
                        "league_filter_status": league_result.get("league_filter_status"),
                        "league_filter_source": "football_data_backup",

                        "minute": minute,
                        "minuto": minute,
                        "source_minute": minute,
                        "api_elapsed": minute,
                        "elapsed_plus": 0,
                        "added_time": 0,
                        "is_added_time": False,
                        "is_late_game": is_late_game,
                        "status_short": status_text,
                        "status_long": status_text,

                        "home_score": home_score,
                        "away_score": away_score,
                        "local_score": home_score,
                        "visitante_score": away_score,
                        "score": score_text,
                        "marcador": score_text,

                        "dangerous_attacks": 0.0,
                        "shots": 0.0,
                        "shots_on_target": 0.0,
                        "corners": 0.0,
                        "xg": 0.0,
                        "xG": 0.0,
                        "red_cards": 0.0,

                        "possession_home": 50.0,
                        "possession_away": 50.0,
                        "posesión_local": 50.0,
                        "posesión_visitante": 50.0,

                        "home_stats": {
                            **home_stats,
                            "xg": 0.0,
                        },
                        "away_stats": {
                            **away_stats,
                            "xg": 0.0,
                        },

                        "events": [],
                        "event_count": 0,
                        "players": [],
                        "player_count": 0,

                        "data_quality": data_quality,
                        "calidad_datos": data_quality,
                        "has_live_stats": has_live_stats,
                        "tiene_estadísticas_en_vivo": has_live_stats,
                        "is_scannable": is_scannable,
                        "es_escaneable": is_scannable,

                        "scan_phase": scan_phase["scan_phase"],
                        "scan_reason": scan_phase["scan_reason"],
                        "can_publish_signal": scan_phase["can_publish_signal"],
                        "can_observe_signal": scan_phase["can_observe_signal"],

                        "stats_source": "football_data_backup",
                        "fuente_estadísticas": "football_data_backup",

                        "deep_scan_enabled": False,
                        "players_scan_enabled": False,
                        "tracking_only": tracking_only,
                        "operable": not tracking_only,
                        "confidence": self._estimate_confidence(data_quality, totals),
                        "prob_real": self._estimate_prob_real(data_quality, totals),
                        "source": "football_data",

                        "ai_score": analytics["ai_score"],
                        "goal_probability": analytics["goal_probability"],
                        "over_probability": analytics["over_probability"],
                        "under_probability": analytics["under_probability"],
                        "momentum_label": analytics["momentum_label"],
                        "risk_level": analytics["risk_level"],
                        "dominance": analytics["dominance"],

                        "sync_updated_at": now_ts,
                        "sync_updated_at_iso": now_iso,
                        "fetched_at": now_ts,
                        "fetched_at_iso": now_iso,

                        **clock_fields,
                    }
                )
            except Exception as exc:
                logger.warning("NORMALIZATION_ERROR Football-Data Backup: %s", exc)
                continue

        return normalized_list

    def _calculate_advanced_analytics(
        self,
        minute: int,
        home_score: int,
        away_score: int,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any],
        totals: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analytics livianos del fetcher.

        V17: este fetcher NO debe ser el cerebro predictivo principal.
        Solo entrega una lectura base más rica para que las IAs posteriores
        trabajen con mejor información y no dependan de una regla simple por minuto.
        """
        try:
            factor_min = max(minute, 1)

            def team_threat(stats: Dict[str, Any]) -> float:
                return (
                    stats.get("shots_on_target", 0.0) * 4.0
                    + stats.get("shots_inside_box", 0.0) * 2.2
                    + stats.get("blocked_shots", 0.0) * 1.4
                    + stats.get("corners", 0.0) * 0.8
                    + stats.get("goalkeeper_saves", 0.0) * 1.2
                    + stats.get("xG", 0.0) * 8.0
                )

            home_threat_raw = team_threat(home_stats)
            away_threat_raw = team_threat(away_stats)
            home_pressure = home_threat_raw / factor_min
            away_pressure = away_threat_raw / factor_min
            total_pressure = home_pressure + away_pressure

            # Evidencia real de gol: no confundir volumen con amenaza.
            total_shots = totals.get("shots", 0.0)
            total_sot = totals.get("shots_on_target", 0.0)
            inside_box = totals.get("shots_inside_box", 0.0)
            blocked = totals.get("blocked_shots", 0.0)
            saves = totals.get("goalkeeper_saves", 0.0)
            xg = totals.get("xg", 0.0) if totals.get("xg_available") else 0.0

            goal_evidence_score = min(
                100.0,
                (total_sot * 16.0)
                + (inside_box * 9.0)
                + (blocked * 5.0)
                + (saves * 7.0)
                + (xg * 28.0)
                + (totals.get("corners", 0.0) * 2.0),
            )
            volume_score = min(100.0, total_shots * 5.0)

            if goal_evidence_score >= 55:
                momentum_label = "AMENAZA_REAL"
            elif volume_score >= 45 and goal_evidence_score < 25:
                momentum_label = "VOLUMEN_SIN_PROFUNDIDAD"
            elif goal_evidence_score >= 28:
                momentum_label = "AMENAZA_MEDIA"
            else:
                momentum_label = "ESTABLE"

            if home_threat_raw > away_threat_raw * 1.6 and home_threat_raw >= 2:
                dominance = "DOMINANT_HOME"
            elif away_threat_raw > home_threat_raw * 1.6 and away_threat_raw >= 2:
                dominance = "DOMINANT_AWAY"
            else:
                dominance = "BALANCED"

            total_goals = home_score + away_score
            score_pressure = 12.0 if abs(home_score - away_score) <= 1 else 4.0
            late_need_bonus = 8.0 if minute >= 65 and abs(home_score - away_score) <= 1 else 0.0

            goal_probability = min(95.0, max(5.0, goal_evidence_score * 0.68 + volume_score * 0.12 + score_pressure + late_need_bonus))

            # Probabilidad Over base del fetcher: suave, no decisiva.
            if total_goals >= 3:
                over_probability = min(92.0, 62.0 + goal_evidence_score * 0.25)
            elif total_goals == 2:
                over_probability = min(88.0, 48.0 + goal_evidence_score * 0.32 + late_need_bonus)
            elif total_goals == 1:
                over_probability = min(82.0, 38.0 + goal_evidence_score * 0.35 + late_need_bonus)
            else:
                over_probability = min(78.0, 28.0 + goal_evidence_score * 0.42 + late_need_bonus)

            under_probability = max(100.0 - over_probability, 0.0)
            ai_score = round((goal_probability * 0.55) + (goal_evidence_score * 0.35) + (volume_score * 0.10), 2)

            if minute >= 88:
                risk_level = "CRÍTICO"
            elif minute >= 75 or totals.get("red_cards", 0) > 0:
                risk_level = "ALTO"
            elif momentum_label == "VOLUMEN_SIN_PROFUNDIDAD":
                risk_level = "MEDIO"
            else:
                risk_level = "CONTROLADO"

            return {
                "ai_score": min(ai_score, 100.0),
                "goal_probability": round(goal_probability, 2),
                "over_probability": round(over_probability, 2),
                "under_probability": round(under_probability, 2),
                "momentum_label": momentum_label,
                "risk_level": risk_level,
                "dominance": dominance,
                "goal_evidence_score": round(goal_evidence_score, 2),
                "volume_score": round(volume_score, 2),
            }
        except Exception as exc:
            logger.warning("ANALYTICS_CALCULATION_ERROR: %s. Aplicando fallback seguro.", exc)
            return {
                "ai_score": 0.0,
                "goal_probability": 0.0,
                "over_probability": 0.0,
                "under_probability": 0.0,
                "momentum_label": "ESTABLE",
                "risk_level": "MEDIO",
                "dominance": "BALANCED",
                "goal_evidence_score": 0.0,
                "volume_score": 0.0,
            }

    def _fetch_from_football_data(self) -> List[Dict[str, Any]]:
        if not Config.FOOTBALL_DATA_KEY:
            logger.warning("LIVE_FETCHER: FOOTBALL_DATA_KEY no configurada en entorno.")
            return []
        try:
            logger.info("LIVE_FETCHER: Solicitando datos de respaldo a Football-Data.org...")
            response = requests.get(
                self.FOOTBALL_DATA_URL,
                headers=self.football_data_headers,
                timeout=self.BACKUP_TIMEOUT_SECONDS,
            )
            if response.status_code != 200:
                logger.error("LIVE_FETCHER Backup status %s: %s", response.status_code, response.text)
                return []
            data = response.json()
            raw_matches = data.get("matches", []) or []
            return self._normalize_football_data(raw_matches)
        except Exception as exc:
            logger.exception("LIVE_FETCHER Backup Exception: %s", exc)
            return []

    def _should_fetch_detailed_stats(self, raw_match: Dict[str, Any], minute: int) -> bool:
        if minute < 5:
            return False
        fixture = raw_match.get("fixture", {}) or {}
        status_short = str(fixture.get("status", {}).get("short") or "").upper()
        return status_short in self.LIVE_STATUS_SHORT

    def _should_fetch_player_stats(self, minute: int) -> bool:
        return minute >= 15 and minute <= 90

    def _extract_team_stats_api_football(self, statistics: List[Dict[str, Any]], team_index: int) -> Dict[str, Any]:
        """
        Extrae y normaliza estadísticas reales de API-Football.

        Mejora V17:
        - Aprovecha más campos de /fixtures/statistics.
        - Diferencia dato faltante de dato real en cero mediante flags *_available.
        - Mantiene compatibilidad con los nombres antiguos usados por V17.
        """
        default_stats = {
            "possession": 50.0,
            "shots": 0.0,
            "shots_on_target": 0.0,
            "shots_off_goal": 0.0,
            "blocked_shots": 0.0,
            "shots_inside_box": 0.0,
            "shots_outside_box": 0.0,
            "corners": 0.0,
            "dangerous_attacks": 0.0,
            "fouls": 0.0,
            "offsides": 0.0,
            "yellow_cards": 0.0,
            "red_cards": 0.0,
            "goalkeeper_saves": 0.0,
            "total_passes": 0.0,
            "passes_accurate": 0.0,
            "pass_accuracy": 0.0,
            "goals_prevented": 0.0,
            "xG": 0.0,
            "xg_available": False,
            "goals_prevented_available": False,
            "stats_available_fields": [],
            "stats_missing_fields": [],
        }
        if not statistics or len(statistics) <= team_index:
            return default_stats
        try:
            team_data = statistics[team_index]
            stats_list = team_data.get("statistics", []) or []
            stats_map = {
                str(s.get("type") or "").strip().lower(): s.get("value")
                for s in stats_list
                if s.get("type")
            }

            def has_value(*names: str) -> bool:
                for name in names:
                    key = str(name).strip().lower()
                    if key in stats_map and stats_map.get(key) is not None:
                        return True
                return False

            def first_value(*names: str) -> Any:
                for name in names:
                    key = str(name).strip().lower()
                    if key in stats_map:
                        return stats_map.get(key)
                return None

            def parse_pct(v: Any, default: float = 50.0) -> float:
                if v is None or v == "":
                    return default
                try:
                    return float(str(v).replace("%", "").strip())
                except Exception:
                    return default

            def parse_flt(v: Any, default: float = 0.0) -> float:
                if v is None or v == "":
                    return default
                try:
                    return float(str(v).replace("%", "").strip())
                except Exception:
                    return default

            possession = parse_pct(first_value("Ball Possession", "Possession"))
            shots = parse_flt(first_value("Total Shots", "Shots Total", "Total shots"))
            sot = parse_flt(first_value("Shots on Goal", "Shots on Target", "Shots on target"))
            shots_off = parse_flt(first_value("Shots off Goal", "Shots off Target", "Shots off target"))
            blocked = parse_flt(first_value("Blocked Shots", "Shots Blocked"))
            inside_box = parse_flt(first_value("Shots insidebox", "Shots inside box"))
            outside_box = parse_flt(first_value("Shots outsidebox", "Shots outside box"))
            corners = parse_flt(first_value("Corner Kicks", "Corners"))
            da = parse_flt(first_value("Dangerous Attacks", "dangerous attacks"))
            fouls = parse_flt(first_value("Fouls"))
            offsides = parse_flt(first_value("Offsides"))
            yellow_cards = parse_flt(first_value("Yellow Cards", "Yellow cards"))
            red_cards = parse_flt(first_value("Red Cards", "Red cards"))
            saves = parse_flt(first_value("Goalkeeper Saves", "Goals Saves", "goals.saves"))
            total_passes = parse_flt(first_value("Total passes", "Total Passes"))
            passes_accurate = parse_flt(first_value("Passes accurate", "Accurate Passes"))
            pass_accuracy = parse_pct(first_value("Passes %", "Pass Accuracy", "Pass Accuracy %"), default=0.0)
            xg_raw = first_value("expected_goals", "Expected Goals", "xG")
            xg_available = xg_raw is not None and xg_raw != ""
            xg = parse_flt(xg_raw)
            goals_prevented_raw = first_value("goals_prevented", "Goals Prevented")
            goals_prevented_available = goals_prevented_raw is not None and goals_prevented_raw != ""
            goals_prevented = parse_flt(goals_prevented_raw)

            expected_fields = [
                "Ball Possession", "Total Shots", "Shots on Goal", "Shots off Goal",
                "Blocked Shots", "Shots insidebox", "Shots outsidebox", "Corner Kicks",
                "Fouls", "Offsides", "Yellow Cards", "Red Cards", "Goalkeeper Saves",
                "Total passes", "Passes accurate", "Passes %", "expected_goals", "goals_prevented",
            ]
            available_fields = [field for field in expected_fields if has_value(field)]
            missing_fields = [field for field in expected_fields if not has_value(field)]

            return {
                "possession": possession,
                "shots": shots,
                "shots_on_target": sot,
                "shots_off_goal": shots_off,
                "blocked_shots": blocked,
                "shots_inside_box": inside_box,
                "shots_outside_box": outside_box,
                "corners": corners,
                "dangerous_attacks": da,
                "fouls": fouls,
                "offsides": offsides,
                "yellow_cards": yellow_cards,
                "red_cards": red_cards,
                "goalkeeper_saves": saves,
                "total_passes": total_passes,
                "passes_accurate": passes_accurate,
                "pass_accuracy": pass_accuracy,
                "goals_prevented": goals_prevented,
                "xG": xg,
                "xg_available": xg_available,
                "goals_prevented_available": goals_prevented_available,
                "stats_available_fields": available_fields,
                "stats_missing_fields": missing_fields,
            }
        except Exception as exc:
            logger.warning("Error parseando estadísticas de equipo API-Football: %s", exc)
            return default_stats

    def _build_totals(self, home_stats: Dict[str, Any], away_stats: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dangerous_attacks": home_stats.get("dangerous_attacks", 0.0) + away_stats.get("dangerous_attacks", 0.0),
            "shots": home_stats.get("shots", 0.0) + away_stats.get("shots", 0.0),
            "shots_on_target": home_stats.get("shots_on_target", 0.0) + away_stats.get("shots_on_target", 0.0),
            "shots_off_goal": home_stats.get("shots_off_goal", 0.0) + away_stats.get("shots_off_goal", 0.0),
            "blocked_shots": home_stats.get("blocked_shots", 0.0) + away_stats.get("blocked_shots", 0.0),
            "shots_inside_box": home_stats.get("shots_inside_box", 0.0) + away_stats.get("shots_inside_box", 0.0),
            "shots_outside_box": home_stats.get("shots_outside_box", 0.0) + away_stats.get("shots_outside_box", 0.0),
            "corners": home_stats.get("corners", 0.0) + away_stats.get("corners", 0.0),
            "xg": home_stats.get("xG", 0.0) + away_stats.get("xG", 0.0),
            "xg_available": bool(home_stats.get("xg_available") or away_stats.get("xg_available")),
            "red_cards": home_stats.get("red_cards", 0.0) + away_stats.get("red_cards", 0.0),
            "yellow_cards": home_stats.get("yellow_cards", 0.0) + away_stats.get("yellow_cards", 0.0),
            "fouls": home_stats.get("fouls", 0.0) + away_stats.get("fouls", 0.0),
            "offsides": home_stats.get("offsides", 0.0) + away_stats.get("offsides", 0.0),
            "goalkeeper_saves": home_stats.get("goalkeeper_saves", 0.0) + away_stats.get("goalkeeper_saves", 0.0),
            "total_passes": home_stats.get("total_passes", 0.0) + away_stats.get("total_passes", 0.0),
            "passes_accurate": home_stats.get("passes_accurate", 0.0) + away_stats.get("passes_accurate", 0.0),
            "goals_prevented": home_stats.get("goals_prevented", 0.0) + away_stats.get("goals_prevented", 0.0),
            "goals_prevented_available": bool(home_stats.get("goals_prevented_available") or away_stats.get("goals_prevented_available")),
            "available_stat_fields_count": len(set((home_stats.get("stats_available_fields") or []) + (away_stats.get("stats_available_fields") or []))),
            "missing_stat_fields_count": len(set((home_stats.get("stats_missing_fields") or []) + (away_stats.get("stats_missing_fields") or []))),
        }

    def _classify_data_quality(self, home_stats: Dict[str, Any], away_stats: Dict[str, Any], totals: Dict[str, Any]) -> str:
        available_count = totals.get("available_stat_fields_count", 0)
        has_core_stats = totals.get("shots", 0) > 0 or totals.get("corners", 0) > 0 or totals.get("total_passes", 0) > 0
        has_threat_stats = totals.get("shots_on_target", 0) > 0 or totals.get("shots_inside_box", 0) > 0 or totals.get("blocked_shots", 0) > 0
        has_extended_stats = available_count >= 8

        if has_extended_stats and has_core_stats and has_threat_stats:
            return "HIGH"
        if has_extended_stats and has_core_stats:
            return "MEDIUM_HIGH"
        if has_core_stats:
            return "MEDIUM"
        if available_count > 0:
            return "LOW_DATA_AVAILABLE"
        return "LOW_FIXTURE_ONLY"

    def _has_real_live_stats(self, home_stats: Dict[str, Any], away_stats: Dict[str, Any], totals: Dict[str, Any]) -> bool:
        return (
            totals.get("shots", 0) > 0
            or totals.get("corners", 0) > 0
            or totals.get("total_passes", 0) > 0
            or totals.get("available_stat_fields_count", 0) >= 4
        )

    def _is_scannable_match(self, minute: int, home_stats: Dict[str, Any], away_stats: Dict[str, Any], totals: Dict[str, Any]) -> bool:
        if minute < 5 or minute > self.MAX_OPERABLE_MINUTE:
            return False
        return self._has_real_live_stats(home_stats, away_stats, totals)

    def _scan_phase(self, minute: int, is_scannable: bool, has_live_stats: bool, totals: Dict[str, Any]) -> Dict[str, Any]:
        if minute > self.MAX_OPERABLE_MINUTE:
            return {"scan_phase": "TRACKING_ONLY", "scan_reason": "MINUTE_EXCEEDED", "can_publish_signal": False, "can_observe_signal": True}
        if not is_scannable:
            return {"scan_phase": "INITIALIZING", "scan_reason": "NO_LIVE_STATS", "can_publish_signal": False, "can_observe_signal": False}
        return {"scan_phase": "FULL_SCAN", "scan_reason": "OPERABLE_LIVE_MATCH", "can_publish_signal": True, "can_observe_signal": True}

    def _build_live_clock_fields(
        self, fixture_id: Any, minute: int, score: str, status_short: str,
        status_long: str, fetched_at: float, source: str, low_confidence: bool = False
    ) -> Dict[str, Any]:
        key = str(fixture_id)
        prev = self._clock_memory.get(key)
        now_system = time.time()
        
        if not prev:
            self._clock_memory[key] = {
                "first_seen_at": now_system, "last_seen_at": now_system, "api_minute": minute,
                "calculated_minute": minute, "frozen_since": None, "score": score, "stale_notified": False
            }
            return {"clock_calculated_minute": minute, "clock_status": "SYNCHRONIZED", "clock_frozen": False}
        
        time_delta = now_system - prev["last_seen_at"]
        prev["last_seen_at"] = now_system
        
        if prev["api_minute"] == minute and status_short in ["1H", "2H", "LIVE", "IN_PLAY"]:
            if not prev["frozen_since"]:
                prev["frozen_since"] = now_system
            frozen_duration = now_system - prev["frozen_since"]
            if frozen_duration > self.CLOCK_FROZEN_SECONDS:
                clock_status = "FROZEN"
                is_frozen = True
            elif frozen_duration > self.CLOCK_STALE_SECONDS:
                clock_status = "STALE"
                is_frozen = False
            else:
                clock_status = "STUCK_DELAY"
                is_frozen = False
        else:
            prev["api_minute"] = minute
            prev["frozen_since"] = None
            clock_status = "SYNCHRONIZED"
            is_frozen = False

        return {"clock_calculated_minute": minute, "clock_status": clock_status, "clock_frozen": is_frozen}

    def _estimate_minute_from_status(self, item: Dict[str, Any]) -> int:
        try:
            # Estrategia adaptativa para estimación de tiempo por Football-Data
            last_updated_str = item.get("lastUpdated")
            if last_updated_str:
                dt = datetime.strptime(last_updated_str.split("T")[0], "%Y-%m-%d")
                return 45 if item.get("stage") == "HALF_TIME" else 70
            return 50
        except:
            return 50

    def _estimate_confidence(self, quality: str, totals: Dict[str, Any]) -> float:
        if quality == "HIGH": return 0.95
        if quality == "LOW_BACKUP": return 0.40
        return 0.60

    def _estimate_prob_real(self, quality: str, totals: Dict[str, Any]) -> float:
        return 0.98 if quality == "HIGH" else 0.50

    def _activate_429_cooldown(self) -> None:
        self._api_football_cooldown_until = time.time() + self.API_429_COOLDOWN_SECONDS

    def _safe_int(self, value: Any, default: int = 0) -> int:
        if value is None: return default
        try: return int(value)
        except: return default

    def _clone_list(self, data: List[Any]) -> List[Any]:
        return deepcopy(data)

    def _clone_list_with_age(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        cloned = deepcopy(data)
        for item in cloned:
            if isinstance(item, dict) and "fetched_at" in item:
                item["cache_age_seconds"] = max(0, int(now - item["fetched_at"]))
        return cloned

    def _store_live_cache(self, matches: List[Dict[str, Any]]) -> None:
        self._live_cache = deepcopy(matches)
        self._live_cache_at = time.time()
