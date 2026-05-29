from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def utc_timestamp() -> int:
    return int(time.time())


class PreMatchDataService:
    """
    Servicio de memoria previa V17.

    Objetivo:
    - Obtener información previa del partido desde API-Football.
    - Evitar consultas repetidas durante el live.
    - Guardar cache local por fixture_id.
    - Entregar una ficha limpia para PreMatchProfileAI.

    Este archivo NO decide señales.
    Este archivo SOLO recolecta y guarda información previa.
    """

    def __init__(
        self,
        cache_path: str = "app/v17/storage/prematch_cache.json",
        cache_ttl_seconds: int = 60 * 60 * 24,
        api_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 12,
    ) -> None:
        self.cache_path = Path(cache_path)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.api_base_url = api_base_url or os.getenv(
            "API_FOOTBALL_BASE_URL",
            "https://v3.football.api-sports.io",
        )
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY") or os.getenv("APISPORTS_KEY")
        self.timeout_seconds = timeout_seconds

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def get_pre_match_package(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entrada principal.

        Recibe un partido vivo normalizado y devuelve un paquete previo:

        {
            ok,
            source,
            fixture_id,
            league,
            home_team,
            away_team,
            cache_status,
            package
        }
        """

        fixture_id = self._fixture_id(match)
        home_team_id = self._home_team_id(match)
        away_team_id = self._away_team_id(match)
        league_id = self._league_id(match)
        season = self._season(match)

        if not fixture_id:
            return self._empty_package(
                match=match,
                reason="NO_FIXTURE_ID",
            )

        cached = self._get_cached(fixture_id)
        if cached:
            return {
                **cached,
                "cache_status": "HIT",
                "cache_age_seconds": utc_timestamp() - safe_int(cached.get("cached_at"), 0),
            }

        if not self.api_key:
            fallback = self._fallback_package(
                match=match,
                reason="NO_API_KEY",
            )
            self._set_cached(fixture_id, fallback)
            return fallback

        try:
            package = self._build_package_from_api(
                match=match,
                fixture_id=fixture_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                league_id=league_id,
                season=season,
            )

            self._set_cached(fixture_id, package)
            return package

        except Exception as exc:
            fallback = self._fallback_package(
                match=match,
                reason=f"API_ERROR:{type(exc).__name__}",
            )
            self._set_cached(fixture_id, fallback)
            return fallback

    def _build_package_from_api(
        self,
        match: Dict[str, Any],
        fixture_id: str,
        home_team_id: Optional[int],
        away_team_id: Optional[int],
        league_id: Optional[int],
        season: Optional[int],
    ) -> Dict[str, Any]:
        fixture_info = self._get_fixture_info(fixture_id)

        if fixture_info:
            home_team_id = home_team_id or self._extract_team_id(fixture_info, "home")
            away_team_id = away_team_id or self._extract_team_id(fixture_info, "away")
            league_id = league_id or self._extract_league_id(fixture_info)
            season = season or self._extract_season(fixture_info)

        home_last_5 = self._get_last_matches(
            team_id=home_team_id,
            league_id=league_id,
            season=season,
            count=5,
        )

        away_last_5 = self._get_last_matches(
            team_id=away_team_id,
            league_id=league_id,
            season=season,
            count=5,
        )

        h2h = self._get_head_to_head(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            count=5,
        )

        standings = self._get_standings(
            league_id=league_id,
            season=season,
        )

        league_recent = self._get_league_recent_matches(
            league_id=league_id,
            season=season,
            count=20,
        )

        package = {
            "ok": True,
            "source": "API_FOOTBALL",
            "cache_status": "MISS",
            "cached_at": utc_timestamp(),
            "fixture_id": fixture_id,
            "league_id": league_id,
            "season": season,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "league": match.get("league") or self._deep_get(fixture_info, ["league", "name"], ""),
            "country": match.get("country") or self._deep_get(fixture_info, ["league", "country"], ""),
            "home_team": match.get("home_team") or self._deep_get(fixture_info, ["teams", "home", "name"], ""),
            "away_team": match.get("away_team") or self._deep_get(fixture_info, ["teams", "away", "name"], ""),
            "fixture_info": self._compact_fixture_info(fixture_info),
            "home_last_5": self._compact_match_list(home_last_5),
            "away_last_5": self._compact_match_list(away_last_5),
            "head_to_head_last_5": self._compact_match_list(h2h),
            "league_recent_sample": self._compact_match_list(league_recent),
            "standings_context": self._compact_standings(
                standings=standings,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
            "raw_counts": {
                "home_last_5": len(home_last_5),
                "away_last_5": len(away_last_5),
                "head_to_head_last_5": len(h2h),
                "league_recent_sample": len(league_recent),
            },
            "pre_match_summary": self._build_numeric_summary(
                home_last_5=home_last_5,
                away_last_5=away_last_5,
                h2h=h2h,
                league_recent=league_recent,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            ),
        }

        return package

    def _get_fixture_info(self, fixture_id: str) -> Dict[str, Any]:
        data = self._request(
            endpoint="/fixtures",
            params={"id": fixture_id},
        )
        response = data.get("response") or []
        return response[0] if response else {}

    def _get_last_matches(
        self,
        team_id: Optional[int],
        league_id: Optional[int],
        season: Optional[int],
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        if not team_id:
            return []

        params: Dict[str, Any] = {
            "team": team_id,
            "last": count,
        }

        if league_id:
            params["league"] = league_id

        if season:
            params["season"] = season

        data = self._request(
            endpoint="/fixtures",
            params=params,
        )

        return data.get("response") or []

    def _get_head_to_head(
        self,
        home_team_id: Optional[int],
        away_team_id: Optional[int],
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        if not home_team_id or not away_team_id:
            return []

        data = self._request(
            endpoint="/fixtures/headtohead",
            params={
                "h2h": f"{home_team_id}-{away_team_id}",
                "last": count,
            },
        )

        return data.get("response") or []

    def _get_standings(
        self,
        league_id: Optional[int],
        season: Optional[int],
    ) -> List[Dict[str, Any]]:
        if not league_id or not season:
            return []

        data = self._request(
            endpoint="/standings",
            params={
                "league": league_id,
                "season": season,
            },
        )

        return data.get("response") or []

    def _get_league_recent_matches(
        self,
        league_id: Optional[int],
        season: Optional[int],
        count: int = 20,
    ) -> List[Dict[str, Any]]:
        if not league_id or not season:
            return []

        data = self._request(
            endpoint="/fixtures",
            params={
                "league": league_id,
                "season": season,
                "last": count,
            },
        )

        return data.get("response") or []

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = {
            "x-apisports-key": self.api_key or "",
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()
        data = response.json()

        return data if isinstance(data, dict) else {}

    def _build_numeric_summary(
        self,
        home_last_5: List[Dict[str, Any]],
        away_last_5: List[Dict[str, Any]],
        h2h: List[Dict[str, Any]],
        league_recent: List[Dict[str, Any]],
        home_team_id: Optional[int],
        away_team_id: Optional[int],
    ) -> Dict[str, Any]:
        home_summary = self._summarize_team_matches(home_last_5, home_team_id)
        away_summary = self._summarize_team_matches(away_last_5, away_team_id)
        h2h_summary = self._summarize_general_matches(h2h)
        league_summary = self._summarize_general_matches(league_recent)

        combined_goals_avg = self._avg_clean(
            [
                home_summary.get("avg_total_goals"),
                away_summary.get("avg_total_goals"),
                league_summary.get("avg_total_goals"),
            ]
        )

        first_half_avg = self._avg_clean(
            [
                home_summary.get("avg_first_half_goals"),
                away_summary.get("avg_first_half_goals"),
                league_summary.get("avg_first_half_goals"),
            ]
        )

        second_half_avg = self._avg_clean(
            [
                home_summary.get("avg_second_half_goals"),
                away_summary.get("avg_second_half_goals"),
                league_summary.get("avg_second_half_goals"),
            ]
        )

        return {
            "home_recent": home_summary,
            "away_recent": away_summary,
            "head_to_head": h2h_summary,
            "league_recent": league_summary,
            "combined": {
                "avg_total_goals": combined_goals_avg,
                "avg_first_half_goals": first_half_avg,
                "avg_second_half_goals": second_half_avg,
                "goal_profile_hint": self._goal_profile_hint(combined_goals_avg),
                "first_half_profile_hint": self._first_half_profile_hint(first_half_avg),
                "second_half_profile_hint": self._second_half_profile_hint(second_half_avg),
            },
        }

    def _summarize_team_matches(
        self,
        matches: List[Dict[str, Any]],
        team_id: Optional[int],
    ) -> Dict[str, Any]:
        if not matches:
            return self._empty_summary()

        total_goals = []
        first_half_goals = []
        second_half_goals = []
        goals_for = []
        goals_against = []
        over_15 = 0
        over_25 = 0
        btts = 0
        valid = 0

        for item in matches:
            home_id = self._extract_team_id(item, "home")
            away_id = self._extract_team_id(item, "away")

            home_goals, away_goals = self._full_time_score(item)
            ht_home, ht_away = self._half_time_score(item)

            if home_goals is None or away_goals is None:
                continue

            total = home_goals + away_goals
            ht_total = (ht_home or 0) + (ht_away or 0)
            st_total = max(0, total - ht_total)

            valid += 1
            total_goals.append(total)
            first_half_goals.append(ht_total)
            second_half_goals.append(st_total)

            if team_id and team_id == home_id:
                goals_for.append(home_goals)
                goals_against.append(away_goals)
            elif team_id and team_id == away_id:
                goals_for.append(away_goals)
                goals_against.append(home_goals)

            if total >= 2:
                over_15 += 1

            if total >= 3:
                over_25 += 1

            if home_goals > 0 and away_goals > 0:
                btts += 1

        if valid == 0:
            return self._empty_summary()

        return {
            "matches": valid,
            "avg_total_goals": self._avg(total_goals),
            "avg_first_half_goals": self._avg(first_half_goals),
            "avg_second_half_goals": self._avg(second_half_goals),
            "avg_goals_for": self._avg(goals_for),
            "avg_goals_against": self._avg(goals_against),
            "over_15_rate": round(over_15 / valid, 3),
            "over_25_rate": round(over_25 / valid, 3),
            "btts_rate": round(btts / valid, 3),
            "goal_profile_hint": self._goal_profile_hint(self._avg(total_goals)),
            "first_half_profile_hint": self._first_half_profile_hint(self._avg(first_half_goals)),
        }

    def _summarize_general_matches(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not matches:
            return self._empty_summary()

        total_goals = []
        first_half_goals = []
        second_half_goals = []
        over_15 = 0
        over_25 = 0
        btts = 0
        valid = 0

        for item in matches:
            home_goals, away_goals = self._full_time_score(item)
            ht_home, ht_away = self._half_time_score(item)

            if home_goals is None or away_goals is None:
                continue

            total = home_goals + away_goals
            ht_total = (ht_home or 0) + (ht_away or 0)
            st_total = max(0, total - ht_total)

            valid += 1
            total_goals.append(total)
            first_half_goals.append(ht_total)
            second_half_goals.append(st_total)

            if total >= 2:
                over_15 += 1

            if total >= 3:
                over_25 += 1

            if home_goals > 0 and away_goals > 0:
                btts += 1

        if valid == 0:
            return self._empty_summary()

        return {
            "matches": valid,
            "avg_total_goals": self._avg(total_goals),
            "avg_first_half_goals": self._avg(first_half_goals),
            "avg_second_half_goals": self._avg(second_half_goals),
            "over_15_rate": round(over_15 / valid, 3),
            "over_25_rate": round(over_25 / valid, 3),
            "btts_rate": round(btts / valid, 3),
            "goal_profile_hint": self._goal_profile_hint(self._avg(total_goals)),
            "first_half_profile_hint": self._first_half_profile_hint(self._avg(first_half_goals)),
        }

    def _empty_summary(self) -> Dict[str, Any]:
        return {
            "matches": 0,
            "avg_total_goals": 0.0,
            "avg_first_half_goals": 0.0,
            "avg_second_half_goals": 0.0,
            "avg_goals_for": 0.0,
            "avg_goals_against": 0.0,
            "over_15_rate": 0.0,
            "over_25_rate": 0.0,
            "btts_rate": 0.0,
            "goal_profile_hint": "UNKNOWN",
            "first_half_profile_hint": "UNKNOWN",
        }

    def _compact_fixture_info(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not item:
            return {}

        return {
            "fixture_id": self._deep_get(item, ["fixture", "id"]),
            "date": self._deep_get(item, ["fixture", "date"]),
            "status": self._deep_get(item, ["fixture", "status", "long"]),
            "status_short": self._deep_get(item, ["fixture", "status", "short"]),
            "league_id": self._deep_get(item, ["league", "id"]),
            "league": self._deep_get(item, ["league", "name"]),
            "country": self._deep_get(item, ["league", "country"]),
            "season": self._deep_get(item, ["league", "season"]),
            "home_team_id": self._deep_get(item, ["teams", "home", "id"]),
            "home_team": self._deep_get(item, ["teams", "home", "name"]),
            "away_team_id": self._deep_get(item, ["teams", "away", "id"]),
            "away_team": self._deep_get(item, ["teams", "away", "name"]),
            "score": {
                "home": self._deep_get(item, ["goals", "home"]),
                "away": self._deep_get(item, ["goals", "away"]),
                "halftime_home": self._deep_get(item, ["score", "halftime", "home"]),
                "halftime_away": self._deep_get(item, ["score", "halftime", "away"]),
            },
        }

    def _compact_match_list(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted = []

        for item in matches[:20]:
            home_goals, away_goals = self._full_time_score(item)
            ht_home, ht_away = self._half_time_score(item)

            compacted.append(
                {
                    "fixture_id": self._deep_get(item, ["fixture", "id"]),
                    "date": self._deep_get(item, ["fixture", "date"]),
                    "league": self._deep_get(item, ["league", "name"]),
                    "country": self._deep_get(item, ["league", "country"]),
                    "home_team_id": self._deep_get(item, ["teams", "home", "id"]),
                    "home_team": self._deep_get(item, ["teams", "home", "name"]),
                    "away_team_id": self._deep_get(item, ["teams", "away", "id"]),
                    "away_team": self._deep_get(item, ["teams", "away", "name"]),
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "total_goals": None if home_goals is None or away_goals is None else home_goals + away_goals,
                    "halftime_home": ht_home,
                    "halftime_away": ht_away,
                    "halftime_total_goals": None if ht_home is None or ht_away is None else ht_home + ht_away,
                    "status": self._deep_get(item, ["fixture", "status", "short"]),
                }
            )

        return compacted

    def _compact_standings(
        self,
        standings: List[Dict[str, Any]],
        home_team_id: Optional[int],
        away_team_id: Optional[int],
    ) -> Dict[str, Any]:
        if not standings:
            return {}

        rows = []
        response_item = standings[0] if standings else {}
        league_data = response_item.get("league") or {}
        raw_standings = league_data.get("standings") or []

        for group in raw_standings:
            if not isinstance(group, list):
                continue

            for row in group:
                team_id = self._deep_get(row, ["team", "id"])

                if team_id not in {home_team_id, away_team_id}:
                    continue

                rows.append(
                    {
                        "team_id": team_id,
                        "team": self._deep_get(row, ["team", "name"]),
                        "rank": row.get("rank"),
                        "points": row.get("points"),
                        "goals_diff": row.get("goalsDiff"),
                        "form": row.get("form"),
                        "played": self._deep_get(row, ["all", "played"]),
                        "goals_for": self._deep_get(row, ["all", "goals", "for"]),
                        "goals_against": self._deep_get(row, ["all", "goals", "against"]),
                    }
                )

        return {
            "league": league_data.get("name"),
            "country": league_data.get("country"),
            "season": league_data.get("season"),
            "teams": rows,
        }

    def _full_time_score(self, item: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        home = self._deep_get(item, ["goals", "home"])
        away = self._deep_get(item, ["goals", "away"])

        if home is None or away is None:
            home = self._deep_get(item, ["score", "fulltime", "home"])
            away = self._deep_get(item, ["score", "fulltime", "away"])

        if home is None or away is None:
            return None, None

        return safe_int(home), safe_int(away)

    def _half_time_score(self, item: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        home = self._deep_get(item, ["score", "halftime", "home"])
        away = self._deep_get(item, ["score", "halftime", "away"])

        if home is None or away is None:
            return None, None

        return safe_int(home), safe_int(away)

    def _goal_profile_hint(self, avg_goals: float) -> str:
        if avg_goals >= 3.0:
            return "OPEN_HIGH_GOALS"

        if avg_goals >= 2.55:
            return "OPEN"

        if avg_goals >= 2.15:
            return "BALANCED"

        if avg_goals > 0:
            return "DEFENSIVE_LOW_GOALS"

        return "UNKNOWN"

    def _first_half_profile_hint(self, avg_first_half_goals: float) -> str:
        if avg_first_half_goals >= 1.25:
            return "OPEN_FIRST_HALF"

        if avg_first_half_goals >= 0.85:
            return "BALANCED_FIRST_HALF"

        if avg_first_half_goals > 0:
            return "CLOSED_FIRST_HALF"

        return "UNKNOWN"

    def _second_half_profile_hint(self, avg_second_half_goals: float) -> str:
        if avg_second_half_goals >= 1.55:
            return "OPEN_SECOND_HALF"

        if avg_second_half_goals >= 1.05:
            return "BALANCED_SECOND_HALF"

        if avg_second_half_goals > 0:
            return "CLOSED_SECOND_HALF"

        return "UNKNOWN"

    def _avg(self, values: List[Any]) -> float:
        clean = [safe_float(x) for x in values if x is not None]
        if not clean:
            return 0.0
        return round(sum(clean) / len(clean), 3)

    def _avg_clean(self, values: List[Any]) -> float:
        clean = [safe_float(x) for x in values if safe_float(x) > 0]
        if not clean:
            return 0.0
        return round(sum(clean) / len(clean), 3)

    def _fixture_id(self, match: Dict[str, Any]) -> str:
        return str(
            match.get("fixture_id")
            or match.get("match_id")
            or self._deep_get(match, ["fixture", "id"])
            or ""
        )

    def _home_team_id(self, match: Dict[str, Any]) -> Optional[int]:
        value = (
            match.get("home_team_id")
            or match.get("home_id")
            or self._deep_get(match, ["teams", "home", "id"])
        )
        return safe_int(value) if value else None

    def _away_team_id(self, match: Dict[str, Any]) -> Optional[int]:
        value = (
            match.get("away_team_id")
            or match.get("away_id")
            or self._deep_get(match, ["teams", "away", "id"])
        )
        return safe_int(value) if value else None

    def _league_id(self, match: Dict[str, Any]) -> Optional[int]:
        value = (
            match.get("league_id")
            or self._deep_get(match, ["league", "id"])
        )
        return safe_int(value) if value else None

    def _season(self, match: Dict[str, Any]) -> Optional[int]:
        value = (
            match.get("season")
            or self._deep_get(match, ["league", "season"])
        )
        return safe_int(value) if value else None

    def _extract_team_id(self, item: Dict[str, Any], side: str) -> Optional[int]:
        value = self._deep_get(item, ["teams", side, "id"])
        return safe_int(value) if value else None

    def _extract_league_id(self, item: Dict[str, Any]) -> Optional[int]:
        value = self._deep_get(item, ["league", "id"])
        return safe_int(value) if value else None

    def _extract_season(self, item: Dict[str, Any]) -> Optional[int]:
        value = self._deep_get(item, ["league", "season"])
        return safe_int(value) if value else None

    def _deep_get(self, data: Dict[str, Any], path: List[str], default: Any = None) -> Any:
        current: Any = data

        for key in path:
            if not isinstance(current, dict):
                return default
            current = current.get(key)

        return current if current is not None else default

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {}

        try:
            with self.cache_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        tmp_path = self.cache_path.with_suffix(".tmp")

        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)

        tmp_path.replace(self.cache_path)

    def _get_cached(self, fixture_id: str) -> Optional[Dict[str, Any]]:
        cache = self._load_cache()
        item = cache.get(str(fixture_id))

        if not isinstance(item, dict):
            return None

        cached_at = safe_int(item.get("cached_at"), 0)

        if cached_at <= 0:
            return None

        age = utc_timestamp() - cached_at

        if age > self.cache_ttl_seconds:
            return None

        return item

    def _set_cached(self, fixture_id: str, package: Dict[str, Any]) -> None:
        cache = self._load_cache()
        cache[str(fixture_id)] = package
        self._save_cache(cache)

    def _fallback_package(self, match: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "source": "LOCAL_FALLBACK",
            "cache_status": "FALLBACK",
            "cached_at": utc_timestamp(),
            "reason": reason,
            "fixture_id": self._fixture_id(match),
            "league_id": self._league_id(match),
            "season": self._season(match),
            "home_team_id": self._home_team_id(match),
            "away_team_id": self._away_team_id(match),
            "league": match.get("league") or "",
            "country": match.get("country") or "",
            "home_team": match.get("home_team") or "",
            "away_team": match.get("away_team") or "",
            "fixture_info": {},
            "home_last_5": [],
            "away_last_5": [],
            "head_to_head_last_5": [],
            "league_recent_sample": [],
            "standings_context": {},
            "raw_counts": {
                "home_last_5": 0,
                "away_last_5": 0,
                "head_to_head_last_5": 0,
                "league_recent_sample": 0,
            },
            "pre_match_summary": {
                "home_recent": self._empty_summary(),
                "away_recent": self._empty_summary(),
                "head_to_head": self._empty_summary(),
                "league_recent": self._empty_summary(),
                "combined": {
                    "avg_total_goals": 0.0,
                    "avg_first_half_goals": 0.0,
                    "avg_second_half_goals": 0.0,
                    "goal_profile_hint": "UNKNOWN",
                    "first_half_profile_hint": "UNKNOWN",
                    "second_half_profile_hint": "UNKNOWN",
                },
            },
        }

    def _empty_package(self, match: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return self._fallback_package(match=match, reason=reason)
