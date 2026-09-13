from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import unicodedata
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def pick_first(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return default


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def bool_from_any(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().upper()
    return text in {"1", "TRUE", "YES", "Y", "SI", "SÍ"}


def pick_from_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)

        if isinstance(value, dict):
            nested = pick_first(
                value,
                ["name", "league", "country", "short", "long", "id", "logo", "flag"],
                None,
            )
            if nested is not None and nested != "":
                return nested

        if value is not None and value != "":
            return value

    return default


class LiveSnapshotStore:
    """
    Guarda el último estado conocido de cada partido.

    Esta clase no decide señales.
    Esta clase no rankea.
    Esta clase no cierra resultados.

    Solo normaliza y conserva el estado vivo del partido.
    """

    def __init__(self) -> None:
        self._matches: Dict[str, Dict[str, Any]] = {}
        self._minute_memory: Dict[str, int] = {}
        self._same_minute_count: Dict[str, int] = {}

    def update_many(self, raw_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for raw in raw_matches or []:
            item = self.update_one(raw)
            if item:
                normalized.append(item)

        return normalized

    def update_one(self, raw_match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_match, dict):
            return None

        item = self._normalize_match(raw_match)
        match_id = item.get("match_id")

        if not match_id:
            return None

        previous_minute = self._minute_memory.get(match_id)
        current_minute = safe_int(item.get("api_minute"), 0)

        if previous_minute is not None and current_minute == previous_minute:
            self._same_minute_count[match_id] = self._same_minute_count.get(match_id, 0) + 1
        else:
            self._same_minute_count[match_id] = 0

        self._minute_memory[match_id] = current_minute

        item["same_minute_count"] = self._same_minute_count.get(match_id, 0)
        item["updated_at"] = item.get("updated_at") or utc_now_iso()

        previous = self._matches.get(match_id)
        if previous:
            merged = self._merge_fresh(previous, item)
        else:
            merged = item

        self._matches[match_id] = merged
        return deepcopy(merged)

    def all(self) -> List[Dict[str, Any]]:
        return [deepcopy(x) for x in self._matches.values()]

    def get(self, match_id: str) -> Optional[Dict[str, Any]]:
        item = self._matches.get(str(match_id))
        return deepcopy(item) if item else None

    def clear_finished(self) -> None:
        active: Dict[str, Dict[str, Any]] = {}

        for match_id, item in self._matches.items():
            status = str(item.get("status") or "").upper()
            elapsed = safe_int(item.get("api_minute"), 0)

            if status in {"FT", "AET", "PEN", "FINISHED"}:
                continue

            if elapsed >= 130:
                continue

            active[match_id] = item

        self._matches = active

    def _normalize_match(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(raw)

        match_id = str(
            pick_first(
                data,
                [
                    "match_id",
                    "fixture_id",
                    "fixture",
                    "id",
                    "game_id",
                ],
                "",
            )
        )

        home = pick_first(data, ["home_team", "home", "team_home", "local_team"], "")
        away = pick_first(data, ["away_team", "away", "team_away", "visitor_team"], "")

        league = self._extract_league_name(data)
        country = self._extract_country_name(data)
        competition_metadata = self._extract_competition_metadata(
            data=data,
            league=league,
            country=country,
        )

        api_minute = safe_int(
            pick_first(
                data,
                [
                    "api_minute",
                    "minute",
                    "elapsed",
                    "current_minute",
                    "match_minute",
                    "display_minute",
                    "source_minute",
                ],
                0,
            )
        )

        home_score = safe_int(
            pick_first(
                data,
                [
                    "home_score",
                    "goals_home",
                    "score_home",
                    "home_goals",
                ],
                0,
            )
        )

        away_score = safe_int(
            pick_first(
                data,
                [
                    "away_score",
                    "goals_away",
                    "score_away",
                    "away_goals",
                ],
                0,
            )
        )

        status = str(pick_first(data, ["status", "match_status", "short_status"], "LIVE")).upper()

        updated_at = pick_first(
            data,
            [
                "updated_at",
                "last_update",
                "timestamp",
                "_snapshot_at",
                "created_at",
            ],
            utc_now_iso(),
        )

        attacks_home = safe_int(pick_first(data, ["attacks_home", "home_attacks"], 0))
        attacks_away = safe_int(pick_first(data, ["attacks_away", "away_attacks"], 0))
        dangerous_home = safe_int(pick_first(data, ["dangerous_attacks_home", "home_dangerous_attacks"], 0))
        dangerous_away = safe_int(pick_first(data, ["dangerous_attacks_away", "away_dangerous_attacks"], 0))

        shots_home = safe_int(pick_first(data, ["shots_home", "home_shots"], 0))
        shots_away = safe_int(pick_first(data, ["shots_away", "away_shots"], 0))
        shots_on_home = safe_int(pick_first(data, ["shots_on_home", "home_shots_on"], 0))
        shots_on_away = safe_int(pick_first(data, ["shots_on_away", "away_shots_on"], 0))

        corners_home = safe_int(pick_first(data, ["corners_home", "home_corners"], 0))
        corners_away = safe_int(pick_first(data, ["corners_away", "away_corners"], 0))

        xg_home = safe_float(pick_first(data, ["xg_home", "home_xg"], 0.0))
        xg_away = safe_float(pick_first(data, ["xg_away", "away_xg"], 0.0))

        total_goals = home_score + away_score
        scoreline = f"{home_score}-{away_score}"

        normalized = {
            **data,
            "match_id": match_id,
            "fixture_id": match_id,
            "home_team": home,
            "away_team": away,
            "league": league,
            "country": country,

            # Competición / filtro de ligas.
            # Estos campos vienen desde LeagueFilter o se infieren aquí como fallback
            # para que viajen hacia Engine, ML, historial y panel.
            "league_id": competition_metadata.get("league_id"),
            "league_filter_status": competition_metadata.get("league_filter_status"),
            "league_filter_reason": competition_metadata.get("league_filter_reason"),
            "competition_tier": competition_metadata.get("competition_tier"),
            "competition_weight": competition_metadata.get("competition_weight"),
            "world_cup_flag": competition_metadata.get("world_cup_flag"),
            "national_team_flag": competition_metadata.get("national_team_flag"),
            "major_tournament_flag": competition_metadata.get("major_tournament_flag"),
            "api_minute": api_minute,
            "display_minute": api_minute,
            "home_score": home_score,
            "away_score": away_score,
            "scoreline": scoreline,
            "total_goals": total_goals,
            "status": status,
            "updated_at": updated_at,
            "attacks_home": attacks_home,
            "attacks_away": attacks_away,
            "dangerous_attacks_home": dangerous_home,
            "dangerous_attacks_away": dangerous_away,
            "shots_home": shots_home,
            "shots_away": shots_away,
            "shots_on_home": shots_on_home,
            "shots_on_away": shots_on_away,
            "corners_home": corners_home,
            "corners_away": corners_away,
            "xg_home": xg_home,
            "xg_away": xg_away,
            "total_attacks": attacks_home + attacks_away,
            "total_dangerous_attacks": dangerous_home + dangerous_away,
            "total_shots": shots_home + shots_away,
            "total_shots_on": shots_on_home + shots_on_away,
            "total_corners": corners_home + corners_away,
            "total_xg": round(xg_home + xg_away, 3),
        }

        return normalized


    def _extract_league_name(self, data: Dict[str, Any]) -> str:
        league_obj = data.get("league") if isinstance(data.get("league"), dict) else {}

        value = (
            data.get("league") if not isinstance(data.get("league"), dict) else None
            or data.get("league_name")
            or data.get("competition")
            or data.get("tournament")
            or league_obj.get("name")
        )

        return str(value or "").strip()

    def _extract_country_name(self, data: Dict[str, Any]) -> str:
        league_obj = data.get("league") if isinstance(data.get("league"), dict) else {}

        value = (
            data.get("country")
            or data.get("country_name")
            or data.get("pais")
            or league_obj.get("country")
        )

        return str(value or "").strip()

    def _extract_league_id(self, data: Dict[str, Any]) -> Optional[int]:
        league_obj = data.get("league") if isinstance(data.get("league"), dict) else {}

        raw_id = pick_first(
            data,
            ["league_id", "competition_id", "tournament_id"],
            league_obj.get("id"),
        )

        parsed = safe_int(raw_id, 0)
        return parsed if parsed > 0 else None

    def _extract_competition_metadata(
        self,
        data: Dict[str, Any],
        league: str,
        country: str,
    ) -> Dict[str, Any]:
        """
        Propaga y normaliza metadatos competitivos.

        No decide si una liga entra o no. Esa decisión sigue siendo de LeagueFilter.
        Esta capa solo garantiza que competition_tier, competition_weight y flags
        lleguen al motor, al feature builder, al historial y al panel.
        """

        league_id = self._extract_league_id(data)
        league_filter_status = str(data.get("league_filter_status") or "").strip()
        league_filter_reason = str(data.get("league_filter_reason") or "").strip()

        text = normalize_text(
            f"{league} {country} "
            f"{data.get('league_filter_reason') or ''} "
            f"{data.get('competition_tier') or ''}"
        )

        raw_tier = str(data.get("competition_tier") or "").strip().upper()
        competition_tier = raw_tier or self._infer_competition_tier(text)

        raw_weight = safe_int(data.get("competition_weight"), -1)
        competition_weight = raw_weight if raw_weight >= 0 else self._competition_weight(competition_tier)

        world_cup_flag = (
            bool_from_any(data.get("world_cup_flag"))
            or competition_tier == "WORLD_CUP_ELITE"
            or any(token in text for token in ["WORLD CUP", "COPA MUNDIAL", "MUNDIAL"])
        )

        national_team_flag = (
            bool_from_any(data.get("national_team_flag"))
            or world_cup_flag
            or competition_tier in {
                "NATIONAL_TEAM_ELITE",
                "WORLD_CUP_QUALIFIERS",
                "INTERNATIONAL_FRIENDLY",
            }
            or any(
                token in text
                for token in [
                    "EURO",
                    "COPA AMERICA",
                    "AFRICA CUP",
                    "ASIAN CUP",
                    "GOLD CUP",
                    "NATIONS LEAGUE",
                    "QUALIFIERS",
                    "QUALIFICATION",
                    "FRIENDLY",
                ]
            )
        )

        major_tournament_flag = (
            bool_from_any(data.get("major_tournament_flag"))
            or competition_weight >= 85
            or competition_tier in {
                "WORLD_CUP_ELITE",
                "WORLD_CUP_QUALIFIERS",
                "NATIONAL_TEAM_ELITE",
                "INTERNATIONAL_CLUB_ELITE",
            }
        )

        if not league_filter_status:
            league_filter_status = "SNAPSHOT_METADATA_INFERRED"

        if not league_filter_reason:
            league_filter_reason = "Metadatos competitivos propagados por LiveSnapshotStore."

        return {
            "league_id": league_id,
            "league_filter_status": league_filter_status,
            "league_filter_reason": league_filter_reason,
            "competition_tier": competition_tier,
            "competition_weight": competition_weight,
            "world_cup_flag": world_cup_flag,
            "national_team_flag": national_team_flag,
            "major_tournament_flag": major_tournament_flag,
        }

    def _infer_competition_tier(self, text: str) -> str:
        if any(token in text for token in ["WORLD CUP", "COPA MUNDIAL", "MUNDIAL"]):
            if "QUALIF" in text or "ELIMINATOR" in text:
                return "WORLD_CUP_QUALIFIERS"
            return "WORLD_CUP_ELITE"

        if any(token in text for token in ["CHAMPIONS LEAGUE", "EUROPA LEAGUE", "LIBERTADORES", "SUDAMERICANA"]):
            return "INTERNATIONAL_CLUB_ELITE"

        if any(token in text for token in ["COPA AMERICA", "UEFA EURO", "AFRICA CUP", "ASIAN CUP", "GOLD CUP", "NATIONS LEAGUE"]):
            return "NATIONAL_TEAM_ELITE"

        if "INTERNATIONAL FRIEND" in text or "FIFA FRIEND" in text:
            return "INTERNATIONAL_FRIENDLY"

        if "COUNTRY_REVIEW" in text:
            return "COUNTRY_REVIEW"

        return "PRIORITY_LEAGUE"

    def _competition_weight(self, tier: str) -> int:
        weights = {
            "WORLD_CUP_ELITE": 100,
            "WORLD_CUP_QUALIFIERS": 92,
            "INTERNATIONAL_CLUB_ELITE": 90,
            "NATIONAL_TEAM_ELITE": 88,
            "PRIORITY_LEAGUE": 75,
            "INTERNATIONAL_FRIENDLY": 55,
            "COUNTRY_REVIEW": 45,
            "UNKNOWN": 0,
            "BLOCKED": 0,
        }
        return weights.get(str(tier or "").upper(), 75)

    def _merge_fresh(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(old)

        old_minute = safe_int(old.get("api_minute"), 0)
        new_minute = safe_int(new.get("api_minute"), 0)

        if new_minute >= old_minute:
            merged.update(new)
        else:
            for key, value in new.items():
                if key not in merged or merged.get(key) in (None, "", 0):
                    merged[key] = value

        merged["api_minute"] = max(old_minute, new_minute)
        merged["display_minute"] = merged["api_minute"]

        merged["home_score"] = max(safe_int(old.get("home_score"), 0), safe_int(new.get("home_score"), 0))
        merged["away_score"] = max(safe_int(old.get("away_score"), 0), safe_int(new.get("away_score"), 0))
        merged["scoreline"] = f"{merged['home_score']}-{merged['away_score']}"
        merged["total_goals"] = merged["home_score"] + merged["away_score"]

        return merged
