from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


class PreMatchProfileAI:
    """
    Interpreta la memoria previa del partido.

    Este módulo NO decide una entrada directa.
    Este módulo NO reemplaza la lectura live.
    Este módulo entrega contexto previo para que V17 no sea necio con UNDER u OVER.

    Usa:
    - últimos 5 partidos del local
    - últimos 5 partidos del visitante
    - muestra reciente de liga
    - head to head si existe
    - promedios de goles
    - tendencia de primer tiempo y segundo tiempo
    """

    VERSION = "V17_PRE_MATCH_PROFILE_AI_1"

    def analyze(self, pre_match_package: Dict[str, Any], live_match: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        live_match = live_match or {}

        summary = pre_match_package.get("pre_match_summary") or {}
        combined = summary.get("combined") or {}
        home_recent = summary.get("home_recent") or {}
        away_recent = summary.get("away_recent") or {}
        league_recent = summary.get("league_recent") or {}
        h2h = summary.get("head_to_head") or {}

        league = pre_match_package.get("league") or live_match.get("league") or ""
        country = pre_match_package.get("country") or live_match.get("country") or ""
        home_team = pre_match_package.get("home_team") or live_match.get("home_team") or ""
        away_team = pre_match_package.get("away_team") or live_match.get("away_team") or ""

        avg_total_goals = safe_float(combined.get("avg_total_goals"))
        avg_first_half_goals = safe_float(combined.get("avg_first_half_goals"))
        avg_second_half_goals = safe_float(combined.get("avg_second_half_goals"))

        home_avg_goals_for = safe_float(home_recent.get("avg_goals_for"))
        home_avg_goals_against = safe_float(home_recent.get("avg_goals_against"))
        away_avg_goals_for = safe_float(away_recent.get("avg_goals_for"))
        away_avg_goals_against = safe_float(away_recent.get("avg_goals_against"))

        home_over_15 = safe_float(home_recent.get("over_15_rate"))
        away_over_15 = safe_float(away_recent.get("over_15_rate"))
        home_over_25 = safe_float(home_recent.get("over_25_rate"))
        away_over_25 = safe_float(away_recent.get("over_25_rate"))
        home_btts = safe_float(home_recent.get("btts_rate"))
        away_btts = safe_float(away_recent.get("btts_rate"))

        league_over_15 = safe_float(league_recent.get("over_15_rate"))
        league_over_25 = safe_float(league_recent.get("over_25_rate"))
        league_btts = safe_float(league_recent.get("btts_rate"))

        h2h_avg_goals = safe_float(h2h.get("avg_total_goals"))
        h2h_over_25 = safe_float(h2h.get("over_25_rate"))
        h2h_btts = safe_float(h2h.get("btts_rate"))

        league_goal_profile = self._league_goal_profile(avg_total_goals, league_over_25, league_btts, league, country)
        first_half_profile = self._first_half_profile(avg_first_half_goals)
        second_half_profile = self._second_half_profile(avg_second_half_goals)

        team_goal_profile = self._team_goal_profile(
            home_avg_goals_for=home_avg_goals_for,
            home_avg_goals_against=home_avg_goals_against,
            away_avg_goals_for=away_avg_goals_for,
            away_avg_goals_against=away_avg_goals_against,
            home_over_25=home_over_25,
            away_over_25=away_over_25,
            home_btts=home_btts,
            away_btts=away_btts,
        )

        over_pre_match_score = self._over_pre_match_score(
            avg_total_goals=avg_total_goals,
            avg_first_half_goals=avg_first_half_goals,
            avg_second_half_goals=avg_second_half_goals,
            home_over_15=home_over_15,
            away_over_15=away_over_15,
            home_over_25=home_over_25,
            away_over_25=away_over_25,
            home_btts=home_btts,
            away_btts=away_btts,
            league_over_15=league_over_15,
            league_over_25=league_over_25,
            league_btts=league_btts,
            h2h_avg_goals=h2h_avg_goals,
            h2h_over_25=h2h_over_25,
            h2h_btts=h2h_btts,
            league_goal_profile=league_goal_profile,
        )

        under_pre_match_score = self._under_pre_match_score(
            avg_total_goals=avg_total_goals,
            avg_first_half_goals=avg_first_half_goals,
            home_over_25=home_over_25,
            away_over_25=away_over_25,
            home_btts=home_btts,
            away_btts=away_btts,
            league_over_25=league_over_25,
            league_btts=league_btts,
            h2h_avg_goals=h2h_avg_goals,
            h2h_over_25=h2h_over_25,
            league_goal_profile=league_goal_profile,
        )

        first_half_goal_risk = self._first_half_goal_risk(
            avg_first_half_goals=avg_first_half_goals,
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            over_pre_match_score=over_pre_match_score,
        )

        second_half_goal_risk = self._second_half_goal_risk(
            avg_second_half_goals=avg_second_half_goals,
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            over_pre_match_score=over_pre_match_score,
        )

        under_early_risk = self._under_early_risk(
            league_goal_profile=league_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            over_pre_match_score=over_pre_match_score,
            avg_first_half_goals=avg_first_half_goals,
        )

        over_support_pre_match = self._support_level(over_pre_match_score)
        under_support_pre_match = self._support_level(under_pre_match_score)

        caution_points = self._build_caution_points(
            league_goal_profile=league_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            over_pre_match_score=over_pre_match_score,
            under_pre_match_score=under_pre_match_score,
            avg_total_goals=avg_total_goals,
            avg_first_half_goals=avg_first_half_goals,
            home_btts=home_btts,
            away_btts=away_btts,
            league_btts=league_btts,
        )

        support_points = self._build_support_points(
            league_goal_profile=league_goal_profile,
            team_goal_profile=team_goal_profile,
            first_half_profile=first_half_profile,
            second_half_profile=second_half_profile,
            over_support_pre_match=over_support_pre_match,
            under_support_pre_match=under_support_pre_match,
            avg_total_goals=avg_total_goals,
            avg_first_half_goals=avg_first_half_goals,
            avg_second_half_goals=avg_second_half_goals,
        )

        recommended_behavior = self._recommended_behavior(
            league_goal_profile=league_goal_profile,
            first_half_goal_risk=first_half_goal_risk,
            second_half_goal_risk=second_half_goal_risk,
            under_early_risk=under_early_risk,
            over_pre_match_score=over_pre_match_score,
            under_pre_match_score=under_pre_match_score,
        )

        return {
            "pre_match_profile_version": self.VERSION,
            "pre_match_available": bool(pre_match_package),
            "pre_match_source": pre_match_package.get("source") or "UNKNOWN",
            "pre_match_ok": bool(pre_match_package.get("ok")),
            "pre_match_cache_status": pre_match_package.get("cache_status") or "UNKNOWN",
            "pre_match_fixture_id": pre_match_package.get("fixture_id"),
            "pre_match_league": league,
            "pre_match_country": country,
            "pre_match_home_team": home_team,
            "pre_match_away_team": away_team,

            "league_goal_profile": league_goal_profile,
            "team_goal_profile": team_goal_profile,
            "first_half_profile": first_half_profile,
            "second_half_profile": second_half_profile,

            "first_half_goal_risk": first_half_goal_risk,
            "second_half_goal_risk": second_half_goal_risk,
            "under_early_risk": under_early_risk,

            "over_support_pre_match": over_support_pre_match,
            "under_support_pre_match": under_support_pre_match,
            "over_pre_match_score": round(over_pre_match_score, 2),
            "under_pre_match_score": round(under_pre_match_score, 2),

            "pre_match_avg_total_goals": avg_total_goals,
            "pre_match_avg_first_half_goals": avg_first_half_goals,
            "pre_match_avg_second_half_goals": avg_second_half_goals,

            "home_recent_goal_profile": home_recent.get("goal_profile_hint") or "UNKNOWN",
            "away_recent_goal_profile": away_recent.get("goal_profile_hint") or "UNKNOWN",
            "league_recent_goal_profile": league_recent.get("goal_profile_hint") or "UNKNOWN",

            "home_recent_over_15_rate": home_over_15,
            "away_recent_over_15_rate": away_over_15,
            "home_recent_over_25_rate": home_over_25,
            "away_recent_over_25_rate": away_over_25,
            "home_recent_btts_rate": home_btts,
            "away_recent_btts_rate": away_btts,
            "league_recent_over_25_rate": league_over_25,
            "league_recent_btts_rate": league_btts,

            "pre_match_support_points": support_points,
            "pre_match_caution_points": caution_points,
            "pre_match_recommended_behavior": recommended_behavior,
            "pre_match_panel_note": self._panel_note(
                league_goal_profile=league_goal_profile,
                first_half_goal_risk=first_half_goal_risk,
                under_early_risk=under_early_risk,
                over_support_pre_match=over_support_pre_match,
                under_support_pre_match=under_support_pre_match,
            ),
        }

    def _league_goal_profile(
        self,
        avg_total_goals: float,
        league_over_25: float,
        league_btts: float,
        league: str,
        country: str,
    ) -> str:
        text = f"{league} {country}".lower()

        known_open_markers = [
            "norway",
            "noruega",
            "eliteserien",
            "obos",
            "netherlands",
            "países bajos",
            "eredivisie",
            "sweden",
            "suecia",
            "allsvenskan",
            "denmark",
            "dinamarca",
            "belgium",
            "bélgica",
            "iceland",
            "islandia",
        ]

        if any(marker in text for marker in known_open_markers):
            if avg_total_goals >= 2.3 or league_over_25 >= 0.45:
                return "OPEN_LEAGUE"

        if avg_total_goals >= 3.0 or league_over_25 >= 0.58 or league_btts >= 0.62:
            return "VERY_OPEN_LEAGUE"

        if avg_total_goals >= 2.55 or league_over_25 >= 0.48 or league_btts >= 0.52:
            return "OPEN_LEAGUE"

        if avg_total_goals >= 2.15:
            return "BALANCED_LEAGUE"

        if avg_total_goals > 0:
            return "DEFENSIVE_LEAGUE"

        return "UNKNOWN_LEAGUE"

    def _first_half_profile(self, avg_first_half_goals: float) -> str:
        if avg_first_half_goals >= 1.25:
            return "OPEN_FIRST_HALF"
        if avg_first_half_goals >= 0.85:
            return "BALANCED_FIRST_HALF"
        if avg_first_half_goals > 0:
            return "CLOSED_FIRST_HALF"
        return "UNKNOWN_FIRST_HALF"

    def _second_half_profile(self, avg_second_half_goals: float) -> str:
        if avg_second_half_goals >= 1.55:
            return "OPEN_SECOND_HALF"
        if avg_second_half_goals >= 1.05:
            return "BALANCED_SECOND_HALF"
        if avg_second_half_goals > 0:
            return "CLOSED_SECOND_HALF"
        return "UNKNOWN_SECOND_HALF"

    def _team_goal_profile(
        self,
        home_avg_goals_for: float,
        home_avg_goals_against: float,
        away_avg_goals_for: float,
        away_avg_goals_against: float,
        home_over_25: float,
        away_over_25: float,
        home_btts: float,
        away_btts: float,
    ) -> str:
        attacking_index = (
            home_avg_goals_for
            + away_avg_goals_for
            + home_avg_goals_against * 0.55
            + away_avg_goals_against * 0.55
        )

        over_index = (home_over_25 + away_over_25 + home_btts + away_btts) / 4 if any(
            [home_over_25, away_over_25, home_btts, away_btts]
        ) else 0.0

        if attacking_index >= 4.0 or over_index >= 0.62:
            return "HIGH_GOAL_TEAMS"

        if attacking_index >= 3.0 or over_index >= 0.48:
            return "OPEN_TEAMS"

        if attacking_index >= 2.0 or over_index >= 0.32:
            return "BALANCED_TEAMS"

        if attacking_index > 0:
            return "LOW_GOAL_TEAMS"

        return "UNKNOWN_TEAMS"

    def _over_pre_match_score(
        self,
        avg_total_goals: float,
        avg_first_half_goals: float,
        avg_second_half_goals: float,
        home_over_15: float,
        away_over_15: float,
        home_over_25: float,
        away_over_25: float,
        home_btts: float,
        away_btts: float,
        league_over_15: float,
        league_over_25: float,
        league_btts: float,
        h2h_avg_goals: float,
        h2h_over_25: float,
        h2h_btts: float,
        league_goal_profile: str,
    ) -> float:
        score = 0.0

        score += clamp(avg_total_goals / 3.2 * 24, 0, 24)
        score += clamp(avg_first_half_goals / 1.25 * 12, 0, 12)
        score += clamp(avg_second_half_goals / 1.55 * 12, 0, 12)

        score += clamp(((home_over_15 + away_over_15) / 2) * 10, 0, 10)
        score += clamp(((home_over_25 + away_over_25) / 2) * 16, 0, 16)
        score += clamp(((home_btts + away_btts) / 2) * 10, 0, 10)

        score += clamp(league_over_25 * 8, 0, 8)
        score += clamp(league_btts * 5, 0, 5)

        if h2h_avg_goals > 0:
            score += clamp(h2h_avg_goals / 3.0 * 6, 0, 6)
            score += clamp(h2h_over_25 * 4, 0, 4)
            score += clamp(h2h_btts * 3, 0, 3)

        if league_goal_profile == "VERY_OPEN_LEAGUE":
            score += 8
        elif league_goal_profile == "OPEN_LEAGUE":
            score += 5
        elif league_goal_profile == "DEFENSIVE_LEAGUE":
            score -= 6

        return clamp(score, 0, 100)

    def _under_pre_match_score(
        self,
        avg_total_goals: float,
        avg_first_half_goals: float,
        home_over_25: float,
        away_over_25: float,
        home_btts: float,
        away_btts: float,
        league_over_25: float,
        league_btts: float,
        h2h_avg_goals: float,
        h2h_over_25: float,
        league_goal_profile: str,
    ) -> float:
        score = 50.0

        if avg_total_goals > 0:
            score += clamp((2.4 - avg_total_goals) * 18, -20, 20)

        if avg_first_half_goals > 0:
            score += clamp((0.85 - avg_first_half_goals) * 14, -12, 12)

        team_over_25 = (home_over_25 + away_over_25) / 2 if any([home_over_25, away_over_25]) else 0.0
        team_btts = (home_btts + away_btts) / 2 if any([home_btts, away_btts]) else 0.0

        score += clamp((0.45 - team_over_25) * 22, -18, 18)
        score += clamp((0.45 - team_btts) * 14, -12, 12)
        score += clamp((0.45 - league_over_25) * 14, -12, 12)
        score += clamp((0.48 - league_btts) * 10, -8, 8)

        if h2h_avg_goals > 0:
            score += clamp((2.35 - h2h_avg_goals) * 8, -8, 8)
            score += clamp((0.45 - h2h_over_25) * 8, -6, 6)

        if league_goal_profile == "VERY_OPEN_LEAGUE":
            score -= 14
        elif league_goal_profile == "OPEN_LEAGUE":
            score -= 9
        elif league_goal_profile == "DEFENSIVE_LEAGUE":
            score += 10

        return clamp(score, 0, 100)

    def _first_half_goal_risk(
        self,
        avg_first_half_goals: float,
        league_goal_profile: str,
        team_goal_profile: str,
        over_pre_match_score: float,
    ) -> str:
        risk_score = 0.0

        risk_score += clamp(avg_first_half_goals / 1.25 * 45, 0, 45)
        risk_score += clamp(over_pre_match_score * 0.35, 0, 35)

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            risk_score += 12

        if team_goal_profile in {"HIGH_GOAL_TEAMS", "OPEN_TEAMS"}:
            risk_score += 10

        if risk_score >= 72:
            return "HIGH_FIRST_HALF_GOAL_RISK"

        if risk_score >= 52:
            return "MEDIUM_FIRST_HALF_GOAL_RISK"

        if risk_score > 0:
            return "LOW_FIRST_HALF_GOAL_RISK"

        return "UNKNOWN_FIRST_HALF_GOAL_RISK"

    def _second_half_goal_risk(
        self,
        avg_second_half_goals: float,
        league_goal_profile: str,
        team_goal_profile: str,
        over_pre_match_score: float,
    ) -> str:
        risk_score = 0.0

        risk_score += clamp(avg_second_half_goals / 1.55 * 45, 0, 45)
        risk_score += clamp(over_pre_match_score * 0.35, 0, 35)

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            risk_score += 10

        if team_goal_profile in {"HIGH_GOAL_TEAMS", "OPEN_TEAMS"}:
            risk_score += 10

        if risk_score >= 72:
            return "HIGH_SECOND_HALF_GOAL_RISK"

        if risk_score >= 52:
            return "MEDIUM_SECOND_HALF_GOAL_RISK"

        if risk_score > 0:
            return "LOW_SECOND_HALF_GOAL_RISK"

        return "UNKNOWN_SECOND_HALF_GOAL_RISK"

    def _under_early_risk(
        self,
        league_goal_profile: str,
        first_half_goal_risk: str,
        over_pre_match_score: float,
        avg_first_half_goals: float,
    ) -> str:
        risk = 0

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            risk += 30

        if first_half_goal_risk == "HIGH_FIRST_HALF_GOAL_RISK":
            risk += 35
        elif first_half_goal_risk == "MEDIUM_FIRST_HALF_GOAL_RISK":
            risk += 20

        if over_pre_match_score >= 70:
            risk += 25
        elif over_pre_match_score >= 55:
            risk += 15

        if avg_first_half_goals >= 1.1:
            risk += 15
        elif avg_first_half_goals >= 0.85:
            risk += 8

        if risk >= 70:
            return "HIGH_UNDER_EARLY_RISK"

        if risk >= 45:
            return "MEDIUM_UNDER_EARLY_RISK"

        if risk > 0:
            return "LOW_UNDER_EARLY_RISK"

        return "UNKNOWN_UNDER_EARLY_RISK"

    def _support_level(self, score: float) -> str:
        if score >= 75:
            return "VERY_STRONG"
        if score >= 62:
            return "STRONG"
        if score >= 48:
            return "MEDIUM"
        if score > 0:
            return "LOW"
        return "UNKNOWN"

    def _build_caution_points(
        self,
        league_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        over_pre_match_score: float,
        under_pre_match_score: float,
        avg_total_goals: float,
        avg_first_half_goals: float,
        home_btts: float,
        away_btts: float,
        league_btts: float,
    ) -> List[str]:
        points: List[str] = []

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            points.append("Liga con perfil abierto. No conviene confiar temprano en UNDER sin revalidación live.")

        if first_half_goal_risk == "HIGH_FIRST_HALF_GOAL_RISK":
            points.append("Riesgo alto de gol en primer tiempo según memoria previa.")

        if second_half_goal_risk == "HIGH_SECOND_HALF_GOAL_RISK":
            points.append("Riesgo alto de gol en segundo tiempo según memoria previa.")

        if under_early_risk == "HIGH_UNDER_EARLY_RISK":
            points.append("UNDER temprano peligroso. Requiere confirmación fuerte antes de subir a candidato.")

        if over_pre_match_score >= 70 and under_pre_match_score >= 55:
            points.append("Lectura previa mixta. El live debe decidir, no el marcador por sí solo.")

        if avg_total_goals >= 3.0:
            points.append("Promedio previo alto de goles. Cuidado con líneas UNDER ajustadas.")

        if avg_first_half_goals >= 1.15:
            points.append("La memoria previa muestra primer tiempo con tendencia a gol.")

        avg_btts = self._avg_values([home_btts, away_btts, league_btts])
        if avg_btts >= 0.58:
            points.append("Tendencia elevada de ambos equipos anotando.")

        if not points:
            points.append("Sin alertas previas fuertes. La lectura live puede tener mayor peso.")

        return points

    def _build_support_points(
        self,
        league_goal_profile: str,
        team_goal_profile: str,
        first_half_profile: str,
        second_half_profile: str,
        over_support_pre_match: str,
        under_support_pre_match: str,
        avg_total_goals: float,
        avg_first_half_goals: float,
        avg_second_half_goals: float,
    ) -> List[str]:
        points: List[str] = []

        points.append(f"Perfil de liga previo: {league_goal_profile}.")
        points.append(f"Perfil de equipos previo: {team_goal_profile}.")
        points.append(f"Perfil de primer tiempo: {first_half_profile}.")
        points.append(f"Perfil de segundo tiempo: {second_half_profile}.")

        if avg_total_goals > 0:
            points.append(f"Promedio combinado de goles previo: {avg_total_goals}.")

        if avg_first_half_goals > 0:
            points.append(f"Promedio previo de goles en primer tiempo: {avg_first_half_goals}.")

        if avg_second_half_goals > 0:
            points.append(f"Promedio previo de goles en segundo tiempo: {avg_second_half_goals}.")

        points.append(f"Soporte previo OVER: {over_support_pre_match}.")
        points.append(f"Soporte previo UNDER: {under_support_pre_match}.")

        return points

    def _recommended_behavior(
        self,
        league_goal_profile: str,
        first_half_goal_risk: str,
        second_half_goal_risk: str,
        under_early_risk: str,
        over_pre_match_score: float,
        under_pre_match_score: float,
    ) -> str:
        if under_early_risk == "HIGH_UNDER_EARLY_RISK":
            return "DO_NOT_PROMOTE_EARLY_UNDER_WITHOUT_LIVE_CONFIRMATION"

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"} and over_pre_match_score >= 62:
            return "OPEN_MATCH_CONTEXT_REQUIRE_REVALIDATION"

        if under_pre_match_score >= 70 and over_pre_match_score < 50:
            return "PRE_MATCH_SUPPORTS_UNDER_IF_LIVE_CONFIRMS"

        if over_pre_match_score >= 70 and under_pre_match_score < 50:
            return "PRE_MATCH_SUPPORTS_OVER_IF_LIVE_CONFIRMS"

        if first_half_goal_risk == "HIGH_FIRST_HALF_GOAL_RISK":
            return "FIRST_HALF_CAUTION_REQUIRED"

        if second_half_goal_risk == "HIGH_SECOND_HALF_GOAL_RISK":
            return "SECOND_HALF_GOAL_RISK_ACTIVE"

        return "BALANCED_CONTEXT_LIVE_DECIDES"

    def _panel_note(
        self,
        league_goal_profile: str,
        first_half_goal_risk: str,
        under_early_risk: str,
        over_support_pre_match: str,
        under_support_pre_match: str,
    ) -> str:
        if under_early_risk == "HIGH_UNDER_EARLY_RISK":
            return "Memoria previa advierte riesgo para UNDER temprano. Revalidar con datos live."

        if league_goal_profile in {"VERY_OPEN_LEAGUE", "OPEN_LEAGUE"}:
            return "Liga de perfil abierto. La señal necesita confirmación live antes de subir."

        if first_half_goal_risk == "HIGH_FIRST_HALF_GOAL_RISK":
            return "Primer tiempo con riesgo de gol según historial reciente."

        if under_support_pre_match in {"STRONG", "VERY_STRONG"} and over_support_pre_match in {"LOW", "MEDIUM"}:
            return "La memoria previa respalda UNDER si el live confirma bajo ritmo."

        if over_support_pre_match in {"STRONG", "VERY_STRONG"} and under_support_pre_match in {"LOW", "MEDIUM"}:
            return "La memoria previa respalda OVER si el live confirma presión real."

        return "Contexto previo equilibrado. La lectura live debe mandar."

    def _avg_values(self, values: List[float]) -> float:
        clean = [safe_float(v) for v in values if safe_float(v) > 0]
        if not clean:
            return 0.0
        return sum(clean) / len(clean)
