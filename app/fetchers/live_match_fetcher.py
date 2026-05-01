from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

import requests

from app.config.config import Config

logger = logging.getLogger(__name__)


class LiveMatchFetcher:
    API_BASE = "https://v3.football.api-sports.io"
    API_FOOTBALL_LIVE_URL = f"{API_BASE}/fixtures?live=all"
    API_FOOTBALL_STATISTICS_URL = f"{API_BASE}/fixtures/statistics"
    API_FOOTBALL_EVENTS_URL = f"{API_BASE}/fixtures/events"
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4/matches"

    # Escaneo recomendado:
    # - fixtures live cada 15s
    # - stats/events profundos cada 15s
    LIVE_CACHE_TTL_SECONDS = 60
    STATS_CACHE_TTL_SECONDS = 15
    EVENTS_CACHE_TTL_SECONDS = 15

    MAX_DEEP_SCAN_MATCHES = 12
    MAX_OPERABLE_MINUTE = 87

    API_429_COOLDOWN_SECONDS = 300
    BACKUP_TIMEOUT_SECONDS = 8
    PRIMARY_TIMEOUT_SECONDS = 10
    STATS_TIMEOUT_SECONDS = 8
    EVENTS_TIMEOUT_SECONDS = 8

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
        self._api_football_cooldown_until: float = 0.0

        self._allowed_league_ids = set(
            getattr(Config, "API_FOOTBALL_ALLOWED_LEAGUES", [])
            or getattr(Config, "LIVE_ALLOWED_LEAGUE_IDS", [])
            or []
        )

    def get_live_matches(self) -> List[Dict[str, Any]]:
        return self.fetch_live_data()

    def fetch_live_data(self) -> List[Dict[str, Any]]:
        now = time.time()

        if self._live_cache and (now - self._live_cache_at) < self.LIVE_CACHE_TTL_SECONDS:
            logger.info("LIVE_FETCHER: usando live cache (%s partidos).", len(self._live_cache))
            return self._clone_list(self._live_cache)

        if now < self._api_football_cooldown_until:
            remaining = int(self._api_football_cooldown_until - now)
            logger.warning(
                "LIVE_FETCHER: API-Football en cooldown por rate limit. Esperando %ss.",
                remaining,
            )

            backup_matches = self._fetch_from_football_data()
            if backup_matches:
                self._store_live_cache(backup_matches)
                return backup_matches

            if self._live_cache:
                logger.warning("LIVE_FETCHER: devolviendo última cache disponible por cooldown.")
                return self._clone_list(self._live_cache)

            return []

        primary_matches = self._fetch_from_api_football()
        if primary_matches:
            self._store_live_cache(primary_matches)
            return primary_matches

        logger.warning("LIVE_FETCHER: API-Football sin datos útiles. Probando backup football-data.org...")

        backup_matches = self._fetch_from_football_data()
        if backup_matches:
            self._store_live_cache(backup_matches)
            return backup_matches

        logger.warning("LIVE_FETCHER: ninguna fuente devolvió partidos válidos.")
        self._live_cache = []
        self._live_cache_at = time.time()
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

    def _fetch_fixture_statistics(self, fixture_id: Any, should_fetch: bool = True) -> List[Dict[str, Any]]:
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
            result = data.get("response", []) or []

            self._stats_cache[fixture_key] = {
                "at": now,
                "data": self._clone_list(result),
            }

            return result

        except Exception as exc:
            logger.warning("LIVE_FETCHER stats error fixture=%s: %s", fixture_id, exc)
            return self._clone_list(cached["data"]) if cached else []

    def _fetch_fixture_events(self, fixture_id: Any, should_fetch: bool = True) -> List[Dict[str, Any]]:
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
            result = data.get("response", []) or []

            self._events_cache[fixture_key] = {
                "at": now,
                "data": self._clone_list(result),
            }

            return result

        except Exception as exc:
            logger.warning("LIVE_FETCHER events error fixture=%s: %s", fixture_id, exc)
            return self._clone_list(cached["data"]) if cached else []

    def _normalize_api_football(self, raw_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized_list: List[Dict[str, Any]] = []
        deep_scan_used = 0

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

                league_id = league.get("id")
                if self._allowed_league_ids and league_id not in self._allowed_league_ids:
                    logger.info("LIVE_FETCHER: fixture=%s descartado por league_id=%s", fixture_id, league_id)
                    continue

                status_short = str(status.get("short") or "").upper()
                status_long = str(status.get("long") or "").upper()
                minute = self._safe_int(status.get("elapsed"))

                if status_short in self.BLOCKED_STATUS_SHORT:
                    logger.info("LIVE_FETCHER: fixture=%s descartado por status_short=%s", fixture_id, status_short)
                    continue

                if status_long in self.BLOCKED_STATUS_LONG:
                    logger.info("LIVE_FETCHER: fixture=%s descartado por status_long=%s", fixture_id, status_long)
                    continue

                if status_short not in {"1H", "2H", "ET", "LIVE"}:
                    logger.info("LIVE_FETCHER: fixture=%s descartado por status no vivo=%s", fixture_id, status_short)
                    continue

                if minute <= 0 or minute > self.MAX_OPERABLE_MINUTE:
                    logger.info("LIVE_FETCHER: fixture=%s descartado por minuto no operable=%s", fixture_id, minute)
                    continue

                should_fetch_deep = (
                    deep_scan_used < self.MAX_DEEP_SCAN_MATCHES
                    and self._should_fetch_detailed_stats(item, minute)
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
                    should_fetch=should_fetch_deep,
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

                home_logo = home_team.get("logo")
                away_logo = away_team.get("logo")
                league_logo = league.get("logo")
                country_flag = league.get("flag")

                normalized = {
                    "match_id": fixture_id,
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

                    "minute": minute,
                    "minuto": minute,
                    "status_short": status_short,
                    "status_long": status_long,

                    "home_score": home_score,
                    "away_score": away_score,
                    "local_score": home_score,
                    "visitante_score": away_score,
                    "score": f"{home_score}-{away_score}",
                    "marcador": f"{home_score}-{away_score}",

                    "dangerous_attacks": totals["dangerous_attacks"],
                    "shots": totals["shots"],
                    "shots_on_target": totals["shots_on_target"],
                    "corners": totals["corners"],
                    "xg": round(totals["xg"], 2),
                    "xG": round(totals["xg"], 2),
                    "red_cards": totals["red_cards"],

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

                    "data_quality": data_quality,
                    "calidad_datos": data_quality,
                    "has_live_stats": has_live_stats,
                    "tiene_estadísticas_en_vivo": has_live_stats,
                    "is_scannable": is_scannable,
                    "es_escaneable": is_scannable,

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
                    "confidence": self._estimate_confidence(data_quality, totals),
                    "prob_real": self._estimate_prob_real(data_quality, totals),
                    "source": "api_football",

                    "ai_score": 0.0,
                    "goal_probability": 0.0,
                    "over_probability": 0.0,
                    "under_probability": 0.0,
                    "momentum_label": "ESTABLE",
                    "risk_level": "MEDIO",
                    "dominance": "BALANCED",
                }

                normalized_list.append(normalized)

            except Exception as exc:
                logger.warning("NORMALIZATION_ERROR API-Football: %s", exc)
                continue

        return normalized_list

    def _extract_team_stats_api_football(
        self,
        stats_list: List[Dict[str, Any]],
        index: int,
    ) -> Dict[str, float]:
        default_stats = {
            "possession": 0.0,
            "shots": 0.0,
            "shots_on_target": 0.0,
            "corners": 0.0,
            "dangerous_attacks": 0.0,
            "red_cards": 0.0,
            "xG": 0.0,
        }

        if not isinstance(stats_list, list) or len(stats_list) <= index:
            return default_stats

        team_entry = stats_list[index] or {}
        team_stats = team_entry.get("statistics", []) or []

        return {
            "possession": self._find_stat_multi(team_stats, ["Ball Possession", "Possession", "Possession %"], True),
            "shots": self._find_stat_multi(team_stats, ["Total Shots", "Shots Total", "Attempts on Goal", "Shots"], True),
            "shots_on_target": self._find_stat_multi(team_stats, ["Shots on Goal", "Shots on Target", "On Target"], True),
            "corners": self._find_stat_multi(team_stats, ["Corner Kicks", "Corners", "Corner"], True),
            "dangerous_attacks": self._find_stat_multi(team_stats, ["Dangerous Attacks", "Danger Attacks", "Attacks Dangerous"], True),
            "red_cards": self._find_stat_multi(team_stats, ["Red Cards", "Red Card"], True),
            "xG": self._find_stat_multi(team_stats, ["Expected Goals", "xG"], True),
        }

    def _find_stat_multi(
        self,
        team_stats: List[Dict[str, Any]],
        names: List[str],
        as_float: bool = False,
    ) -> float:
        wanted = {self._normalize_stat_name(name) for name in names}

        for stat in team_stats:
            stat_type = self._normalize_stat_name(stat.get("type"))
            if stat_type not in wanted:
                continue

            value = self._parse_numeric(stat.get("value"))
            return float(value) if as_float else float(int(value))

        return 0.0

    def _fetch_from_football_data(self) -> List[Dict[str, Any]]:
        if not Config.FOOTBALL_DATA_KEY:
            logger.warning("LIVE_FETCHER: FOOTBALL_DATA_KEY no configurada.")
            return []

        try:
            logger.info("LIVE_FETCHER: solicitando partidos LIVE a football-data.org...")

            response = requests.get(
                self.FOOTBALL_DATA_URL,
                headers=self.football_data_headers,
                params={"status": "LIVE"},
                timeout=self.BACKUP_TIMEOUT_SECONDS,
            )

            if response.status_code != 200:
                logger.error(
                    "LIVE_FETCHER football-data.org status %s: %s",
                    response.status_code,
                    response.text,
                )
                return []

            data = response.json()
            raw_matches = data.get("matches", []) or []

            if not raw_matches:
                return []

            return self._normalize_football_data(raw_matches)

        except Exception as exc:
            logger.warning("LIVE_FETCHER football-data.org error: %s", exc)
            return []

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

                if minute <= 0 or minute > self.MAX_OPERABLE_MINUTE:
                    continue

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

                home_logo = home_team.get("crest")
                away_logo = away_team.get("crest")
                league_logo = competition.get("emblem")

                normalized_list.append(
                    {
                        "match_id": item.get("id"),
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

                        "minute": minute,
                        "minuto": minute,
                        "home_score": home_score,
                        "away_score": away_score,
                        "score": f"{home_score}-{away_score}",
                        "marcador": f"{home_score}-{away_score}",

                        "dangerous_attacks": 0.0,
                        "shots": 0.0,
                        "shots_on_target": 0.0,
                        "corners": 0.0,
                        "xg": 0.0,
                        "xG": 0.0,
                        "red_cards": 0.0,
                        "events": [],
                        "event_count": 0,

                        "home_stats": {**home_stats, "xg": home_stats["xG"]},
                        "away_stats": {**away_stats, "xg": away_stats["xG"]},

                        "data_quality": "LOW",
                        "calidad_datos": "LOW",
                        "has_live_stats": False,
                        "is_scannable": False,
                        "stats_source": "football_data_backup",
                        "confidence": 55.0,
                        "prob_real": 0.50,
                        "source": "football_data_backup",

                        "ai_score": 0.0,
                        "goal_probability": 0.0,
                        "over_probability": 0.0,
                        "under_probability": 0.0,
                        "momentum_label": "ESTABLE",
                        "risk_level": "MEDIO",
                        "dominance": "BALANCED",
                    }
                )

            except Exception as exc:
                logger.warning("NORMALIZATION_ERROR football-data.org: %s", exc)
                continue

        return normalized_list

    def _should_fetch_detailed_stats(self, raw_match: Dict[str, Any], minute: int) -> bool:
        return 10 <= minute <= self.MAX_OPERABLE_MINUTE

    def _build_totals(
        self,
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
    ) -> Dict[str, float]:
        return {
            "shots": float(home_stats["shots"] + away_stats["shots"]),
            "shots_on_target": float(home_stats["shots_on_target"] + away_stats["shots_on_target"]),
            "corners": float(home_stats["corners"] + away_stats["corners"]),
            "dangerous_attacks": float(home_stats["dangerous_attacks"] + away_stats["dangerous_attacks"]),
            "red_cards": float(home_stats["red_cards"] + away_stats["red_cards"]),
            "xg": float(home_stats["xG"] + away_stats["xG"]),
        }

    def _classify_data_quality(
        self,
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        totals: Dict[str, float],
    ) -> str:
        core_signals = 0
        advanced_signals = 0

        has_possession = home_stats["possession"] > 0 and away_stats["possession"] > 0

        if totals["shots"] > 0:
            core_signals += 1
        if totals["shots_on_target"] > 0:
            core_signals += 1
        if totals["corners"] > 0:
            core_signals += 1
        if has_possession:
            core_signals += 1
        if totals["xg"] > 0:
            advanced_signals += 1
        if totals["dangerous_attacks"] > 0:
            advanced_signals += 1

        if core_signals >= 3 and advanced_signals >= 1:
            return "HIGH"
        if core_signals >= 2:
            return "MEDIUM"
        return "LOW"

    def _has_real_live_stats(
        self,
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        totals: Dict[str, float],
    ) -> bool:
        return bool(
            totals["shots"] > 0
            or totals["shots_on_target"] > 0
            or totals["corners"] > 0
            or totals["dangerous_attacks"] > 0
            or totals["xg"] > 0
            or (home_stats["possession"] > 0 and away_stats["possession"] > 0)
        )

    def _is_scannable_match(
        self,
        minute: int,
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        totals: Dict[str, float],
    ) -> bool:
        possession_ok = home_stats["possession"] > 0 and away_stats["possession"] > 0

        if minute < 10:
            return False
        if minute > self.MAX_OPERABLE_MINUTE:
            return False
        if totals["shots_on_target"] > 0:
            return True
        if totals["shots"] >= 6:
            return True
        if totals["corners"] >= 4:
            return True
        if totals["dangerous_attacks"] >= 8:
            return True
        if totals["xg"] > 0:
            return True
        if possession_ok and (totals["shots"] > 0 or totals["corners"] > 0):
            return True

        return False

    def _estimate_confidence(self, data_quality: str, totals: Dict[str, float]) -> float:
        base = {
            "HIGH": 82.0,
            "MEDIUM": 68.0,
            "LOW": 56.0,
        }.get(data_quality, 56.0)

        if totals["shots_on_target"] >= 4:
            base += 4
        if totals["dangerous_attacks"] >= 20:
            base += 4
        if totals["xg"] >= 1.0:
            base += 4
        if totals["corners"] >= 6:
            base += 2

        return round(min(base, 95.0), 2)

    def _estimate_prob_real(self, data_quality: str, totals: Dict[str, float]) -> float:
        base = {
            "HIGH": 0.66,
            "MEDIUM": 0.58,
            "LOW": 0.50,
        }.get(data_quality, 0.50)

        if totals["shots_on_target"] >= 5:
            base += 0.03
        if totals["dangerous_attacks"] >= 25:
            base += 0.03
        if totals["corners"] >= 7:
            base += 0.01

        return round(min(base, 0.78), 4)

    def _activate_429_cooldown(self) -> None:
        self._api_football_cooldown_until = time.time() + self.API_429_COOLDOWN_SECONDS

    def _store_live_cache(self, matches: List[Dict[str, Any]]) -> None:
        self._live_cache = self._clone_list(matches)
        self._live_cache_at = time.time()

    def _clone_list(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(item) for item in data]

    def _normalize_stat_name(self, text: Any) -> str:
        return " ".join(str(text or "").strip().lower().replace("%", "").split())

    def _parse_numeric(self, value: Any) -> float:
        if value is None:
            return 0.0

        text = str(value).replace("%", "").strip()
        if not text:
            return 0.0

        try:
            return float(text)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _estimate_minute_from_status(self, match_obj: Dict[str, Any]) -> int:
        status = str(match_obj.get("status") or "").upper()

        if status == "PAUSED":
            return 45
        if status in {"IN_PLAY", "LIVE"}:
            return 60
        return 0
