from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
from typing import Any, Dict, List


class MatchOddsMapper:
    """
    Une partidos live con cuotas reales.

    No bloquea.
    No modifica lógica de señal.
    Solo agrega bookmakers al partido si encuentra coincidencia.
    """

    MIN_MATCH_SCORE = 0.72

    def attach_odds(
        self,
        live_matches: List[Dict[str, Any]],
        odds_events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        mapped: List[Dict[str, Any]] = []

        for match in live_matches or []:
            item = deepcopy(match)

            best_event = self._find_best_odds_event(item, odds_events)

            if best_event:
                item["bookmakers"] = deepcopy(best_event.get("bookmakers") or [])
                item["odds_event_id"] = best_event.get("event_id")
                item["odds_source"] = best_event.get("source")
                item["odds_match_name"] = best_event.get("match_name")
                item["odds_attached"] = True
            else:
                item["odds_attached"] = False

            mapped.append(item)

        return mapped

    def _find_best_odds_event(
        self,
        match: Dict[str, Any],
        odds_events: List[Dict[str, Any]],
    ) -> Dict[str, Any] | None:
        live_home = self._team_text(
            match.get("home_name") or match.get("home_team") or match.get("home")
        )
        live_away = self._team_text(
            match.get("away_name") or match.get("away_team") or match.get("away")
        )
        live_name = self._team_text(
            match.get("match_name") or f"{live_home} vs {live_away}"
        )

        best_score = 0.0
        best_event = None

        for event in odds_events or []:
            odds_home = self._team_text(event.get("home_name") or event.get("home_team"))
            odds_away = self._team_text(event.get("away_name") or event.get("away_team"))
            odds_name = self._team_text(event.get("match_name"))

            direct_score = (
                self._similarity(live_home, odds_home) * 0.45
                + self._similarity(live_away, odds_away) * 0.45
                + self._similarity(live_name, odds_name) * 0.10
            )

            reversed_score = (
                self._similarity(live_home, odds_away) * 0.45
                + self._similarity(live_away, odds_home) * 0.45
                + self._similarity(live_name, odds_name) * 0.10
            )

            score = max(direct_score, reversed_score)

            if score > best_score:
                best_score = score
                best_event = event

        if best_event and best_score >= self.MIN_MATCH_SCORE:
            return best_event

        return None

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0

        if a == b:
            return 1.0

        if a in b or b in a:
            return 0.88

        return SequenceMatcher(None, a, b).ratio()

    def _team_text(self, value: Any) -> str:
        text = str(value or "").lower().strip()

        replacements = {
            " fc": "",
            " cf": "",
            " club": "",
            "deportivo": "",
            "cd ": "",
            "sc ": "",
            " afc": "",
            " united": " utd",
            "timbers": "portland",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return " ".join(text.split())
