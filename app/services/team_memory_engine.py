from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class TeamMemoryEngine:
    """
    Memoria táctica de equipos.

    El sistema comienza a:
    - recordar patrones
    - detectar tendencias
    - entender comportamientos
    - identificar equipos over/under
    """

    def __init__(self) -> None:
        self.memory = defaultdict(dict)

    def analyze_team(
        self,
        team_name: str,
        matches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not matches:
            return self._empty(team_name)

        total_matches = len(matches)

        total_goals = 0
        over_hits = 0
        under_hits = 0
        scored_matches = 0
        conceded_matches = 0
        late_goals = 0
        comebacks = 0

        for match in matches:
            home = float(match.get("home_goals", 0))
            away = float(match.get("away_goals", 0))

            total = home + away

            total_goals += total

            if total >= 3:
                over_hits += 1

            if total <= 2:
                under_hits += 1

            if home > 0 or away > 0:
                scored_matches += 1

            if total >= 1:
                conceded_matches += 1

            if match.get("late_goal"):
                late_goals += 1

            if match.get("comeback"):
                comebacks += 1

        avg_goals = total_goals / total_matches

        over_rate = (over_hits / total_matches) * 100
        under_rate = (under_hits / total_matches) * 100

        attack_profile = self._attack_profile(avg_goals)
        rhythm_profile = self._rhythm_profile(over_rate)
        danger_profile = self._danger_profile(
            late_goals,
            comebacks,
            total_matches,
        )

        memory_score = self._memory_score(
            avg_goals,
            over_rate,
            late_goals,
        )

        result = {
            "team": team_name,
            "matches_analyzed": total_matches,
            "average_goals": round(avg_goals, 2),
            "over_rate": round(over_rate, 2),
            "under_rate": round(under_rate, 2),
            "late_goal_rate": round(
                (late_goals / total_matches) * 100,
                2,
            ),
            "comeback_rate": round(
                (comebacks / total_matches) * 100,
                2,
            ),
            "attack_profile": attack_profile,
            "rhythm_profile": rhythm_profile,
            "danger_profile": danger_profile,
            "memory_score": round(memory_score, 2),
            "summary": self._summary(
                team_name,
                attack_profile,
                rhythm_profile,
                danger_profile,
            ),
        }

        self.memory[team_name] = result

        return result

    def get_memory(
        self,
        team_name: str,
    ) -> Dict[str, Any]:

        return self.memory.get(
            team_name,
            self._empty(team_name),
        )

    def _attack_profile(
        self,
        avg_goals: float,
    ) -> str:

        if avg_goals >= 4:
            return "ULTRA_OFENSIVO"

        if avg_goals >= 3:
            return "OFENSIVO"

        if avg_goals >= 2:
            return "BALANCEADO"

        if avg_goals >= 1:
            return "DEFENSIVO"

        return "ULTRA_DEFENSIVO"

    def _rhythm_profile(
        self,
        over_rate: float,
    ) -> str:

        if over_rate >= 80:
            return "OVER_EXTREMO"

        if over_rate >= 65:
            return "OVER_FUERTE"

        if over_rate >= 50:
            return "MIXTO"

        if over_rate >= 35:
            return "UNDER_FUERTE"

        return "UNDER_EXTREMO"

    def _danger_profile(
        self,
        late_goals: int,
        comebacks: int,
        total_matches: int,
    ) -> str:

        chaos = (
            (late_goals * 1.4)
            + (comebacks * 1.8)
        ) / total_matches

        if chaos >= 1.5:
            return "CAOTICO"

        if chaos >= 1.0:
            return "PELIGROSO"

        if chaos >= 0.5:
            return "VARIABLE"

        return "ESTABLE"

    def _memory_score(
        self,
        avg_goals: float,
        over_rate: float,
        late_goals: int,
    ) -> float:

        score = (
            avg_goals * 15
            + over_rate * 0.5
            + late_goals * 3
        )

        return min(100.0, score)

    def _summary(
        self,
        team: str,
        attack: str,
        rhythm: str,
        danger: str,
    ) -> str:

        return (
            f"{team} perfil={attack}, "
            f"ritmo={rhythm}, "
            f"riesgo={danger}."
        )

    def _empty(
        self,
        team_name: str,
    ) -> Dict[str, Any]:

        return {
            "team": team_name,
            "matches_analyzed": 0,
            "average_goals": 0.0,
            "over_rate": 0.0,
            "under_rate": 0.0,
            "late_goal_rate": 0.0,
            "comeback_rate": 0.0,
            "attack_profile": "UNKNOWN",
            "rhythm_profile": "UNKNOWN",
            "danger_profile": "UNKNOWN",
            "memory_score": 0.0,
            "summary": "Sin memoria táctica.",
  }
