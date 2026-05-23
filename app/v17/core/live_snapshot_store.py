from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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

        league = pick_first(data, ["league", "league_name", "competition"], "")
        country = pick_first(data, ["country", "country_name"], "")

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
