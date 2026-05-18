from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List
import json


class TacticalMemoryService:
    """
    Memoria táctica basada en historial real del sistema.

    Lee data/history.json y permite consultar:
    - historial por liga
    - historial por equipo
    - señales ganadas/perdidas
    - comportamiento OVER/UNDER
    """

    HISTORY_FILE = Path("data/history.json")

    def get_all_history(self) -> List[Dict[str, Any]]:
        payload = self._load_payload()

        history = payload.get("history", []) if isinstance(payload, dict) else []

        if not isinstance(history, list):
            return []

        return [deepcopy(x) for x in history if isinstance(x, dict)]

    def get_league_history(
        self,
        league: str | None,
        country: str | None = None,
        limit: int = 80,
    ) -> List[Dict[str, Any]]:
        league_text = str(league or "").strip().lower()
        country_text = str(country or "").strip().lower()

        if not league_text:
            return []

        items = []

        for item in self.get_all_history():
            item_league = str(item.get("league") or item.get("liga") or "").strip().lower()
            item_country = str(item.get("country") or item.get("pais") or item.get("país") or "").strip().lower()

            league_match = league_text in item_league or item_league in league_text
            country_match = not country_text or country_text in item_country or item_country in country_text

            if league_match and country_match:
                items.append(item)

        return items[:limit]

    def get_team_history(
        self,
        team_name: str | None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        team_text = str(team_name or "").strip().lower()

        if not team_text:
            return []

        items = []

        for item in self.get_all_history():
            home = str(item.get("home_name") or item.get("home") or "").strip().lower()
            away = str(item.get("away_name") or item.get("away") or "").strip().lower()

            if team_text in home or home in team_text or team_text in away or away in team_text:
                items.append(self._normalize_match_for_team_memory(item, team_text))

        return items[:limit]

    def build_memory_context(
        self,
        match: Dict[str, Any],
    ) -> Dict[str, Any]:
        league = match.get("league")
        country = match.get("country")

        home = (
            match.get("home_name")
            or match.get("home_team")
            or match.get("home")
        )

        away = (
            match.get("away_name")
            or match.get("away_team")
            or match.get("away")
        )

        league_history = self.get_league_history(
            league=league,
            country=country,
        )

        home_history = self.get_team_history(home)
        away_history = self.get_team_history(away)

        return {
            "memory_enabled": True,
            "league_history": league_history,
            "home_history": home_history,
            "away_history": away_history,
            "memory_summary": {
                "league_items": len(league_history),
                "home_items": len(home_history),
                "away_items": len(away_history),
            },
        }

    def _normalize_match_for_team_memory(
        self,
        item: Dict[str, Any],
        team_text: str,
    ) -> Dict[str, Any]:
        score = str(
            item.get("final_score")
            or item.get("score")
            or "0-0"
        )

        home_goals, away_goals = self._split_score(score)

        home = str(item.get("home_name") or item.get("home") or "").strip().lower()

        if team_text in home or home in team_text:
            goals_for = home_goals
            goals_against = away_goals
        else:
            goals_for = away_goals
            goals_against = home_goals

        total = home_goals + away_goals

        return {
            **deepcopy(item),
            "goals_for": goals_for,
            "goals_against": goals_against,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "late_goal": self._has_late_goal(item),
            "comeback": False,
            "total_goals": total,
        }

    def _split_score(self, score: str) -> tuple[float, float]:
        try:
            parts = str(score).replace(" ", "").split("-")
            return float(parts[0]), float(parts[1])
        except Exception:
            return 0.0, 0.0

    def _has_late_goal(self, item: Dict[str, Any]) -> bool:
        events = item.get("events")

        if not isinstance(events, list):
            return False

        for event in events:
            if not isinstance(event, dict):
                continue

            event_type = str(event.get("type") or "").lower()
            detail = str(event.get("detail") or "").lower()
            time = event.get("time") if isinstance(event.get("time"), dict) else {}
            minute = self._safe_float(time.get("elapsed"))

            if minute >= 75 and ("goal" in event_type or "goal" in detail):
                return True

        return False

    def _load_payload(self) -> Dict[str, Any]:
        try:
            if not self.HISTORY_FILE.exists():
                return {"history": []}

            with self.HISTORY_FILE.open("r", encoding="utf-8") as file:
                payload = json.load(file)

            return payload if isinstance(payload, dict) else {"history": []}

        except Exception:
            return {"history": []}

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
