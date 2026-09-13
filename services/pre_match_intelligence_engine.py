from __future__ import annotations

from typing import Any, Dict, List

from app.services.league_stability_engine import LeagueStabilityEngine


class PreMatchIntelligenceEngine:
    """
    Motor de inteligencia prepartido.

    Objetivo:
    - analizar contexto antes del inicio
    - detectar tendencias OVER / UNDER
    - calcular riesgo
    - preparar lectura live
    - NO generar señales finales todavía
    """

    def __init__(self) -> None:
        self.league_engine = LeagueStabilityEngine()

    def analyze(
        self,
        fixture_data: Dict[str, Any],
        home_recent_matches: List[Dict[str, Any]] | None = None,
        away_recent_matches: List[Dict[str, Any]] | None = None,
        league_history: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:

        home_recent_matches = home_recent_matches or []
        away_recent_matches = away_recent_matches or []
        league_history = league_history or []

        league = fixture_data.get("league")
        country = fixture_data.get("country")
        data_quality = fixture_data.get("data_quality", "MEDIUM")

        stability = self.league_engine.evaluate(
            league=league,
            country=country,
            data_quality=data_quality,
            history_items=league_history,
        )

        home_profile = self._team_profile(home_recent_matches)
        away_profile = self._team_profile(away_recent_matches)

        combined_attack = (
            home_profile["avg_goals_scored"]
            + away_profile["avg_goals_scored"]
        )

        combined_defense = (
            home_profile["avg_goals_conceded"]
            + away_profile["avg_goals_conceded"]
        )

        over_score = (
            combined_attack * 12
            + combined_defense * 8
        )

        under_score = (
            100
            - over_score
        )

        over_score = max(0.0, min(100.0, over_score))
        under_score = max(0.0, min(100.0, under_score))

        tactical_temperature = self._temperature(over_score)

        projected_market = (
            "OVER"
            if over_score >= under_score
            else "UNDER"
        )

        next_goal_bias = self._next_goal_bias(
            home_profile,
            away_profile,
        )

        confidence = (
            over_score
            if projected_market == "OVER"
            else under_score
        )

        recommendation = self._recommendation(
            confidence=confidence,
            stability=stability["league_stability_level"],
        )

        return {
            "pre_match_enabled": True,
            "projected_market": projected_market,
            "projected_confidence": round(confidence, 2),
            "over_probability": round(over_score, 2),
            "under_probability": round(under_score, 2),
            "tactical_temperature": tactical_temperature,
            "next_goal_bias": next_goal_bias,
            "recommendation": recommendation,
            "home_profile": home_profile,
            "away_profile": away_profile,
            "league_stability": stability,
            "pre_match_summary": self._summary(
                projected_market,
                confidence,
                tactical_temperature,
                next_goal_bias,
                stability["league_stability_level"],
            ),
        }

    def _team_profile(
        self,
        matches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not matches:
            return {
                "matches": 0,
                "avg_goals_scored": 0.0,
                "avg_goals_conceded": 0.0,
                "over_rate": 0.0,
                "under_rate": 0.0,
                "form": "UNKNOWN",
            }

        scored = 0
        conceded = 0
        over = 0
        under = 0

        for match in matches:
            gf = float(match.get("goals_for", 0))
            ga = float(match.get("goals_against", 0))

            scored += gf
            conceded += ga

            total = gf + ga

            if total >= 3:
                over += 1
            else:
                under += 1

        total_matches = len(matches)

        avg_scored = scored / total_matches
        avg_conceded = conceded / total_matches

        over_rate = (over / total_matches) * 100
        under_rate = (under / total_matches) * 100

        form = self._form(avg_scored, avg_conceded)

        return {
            "matches": total_matches,
            "avg_goals_scored": round(avg_scored, 2),
            "avg_goals_conceded": round(avg_conceded, 2),
            "over_rate": round(over_rate, 2),
            "under_rate": round(under_rate, 2),
            "form": form,
        }

    def _form(
        self,
        scored: float,
        conceded: float,
    ) -> str:

        balance = scored - conceded

        if balance >= 1.2:
            return "STRONG"

        if balance >= 0.4:
            return "GOOD"

        if balance >= -0.4:
            return "BALANCED"

        return "WEAK"

    def _temperature(self, over_score: float) -> str:
        if over_score >= 82:
            return "EXTREMA"

        if over_score >= 68:
            return "ALTA"

        if over_score >= 52:
            return "MEDIA"

        return "BAJA"

    def _next_goal_bias(
        self,
        home: Dict[str, Any],
        away: Dict[str, Any],
    ) -> str:

        home_power = (
            home["avg_goals_scored"]
            - home["avg_goals_conceded"]
        )

        away_power = (
            away["avg_goals_scored"]
            - away["avg_goals_conceded"]
        )

        diff = home_power - away_power

        if diff >= 0.6:
            return "HOME"

        if diff <= -0.6:
            return "AWAY"

        return "BALANCED"

    def _recommendation(
        self,
        confidence: float,
        stability: str,
    ) -> str:

        if stability == "PELIGROSA":
            return "NO_OPERAR"

        if confidence >= 80:
            return "SEGUIR_PARTIDO"

        if confidence >= 65:
            return "OBSERVAR_LIVE"

        return "ESPERAR"

    def _summary(
        self,
        market: str,
        confidence: float,
        temperature: str,
        next_goal_bias: str,
        stability: str,
    ) -> str:

        return (
            f"Prepartido detecta tendencia {market} "
            f"con confianza {round(confidence, 1)}%. "
            f"Temperatura táctica {temperature}. "
            f"Bias próximo gol: {next_goal_bias}. "
            f"Estabilidad liga: {stability}."
      )
