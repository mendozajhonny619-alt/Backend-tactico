from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def bool01(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    return 1 if str(value or "").strip().upper() in {"1", "TRUE", "YES", "SI", "SÍ", "ON"} else 0


def quality_score(value: Any) -> float:
    text = str(value or "").upper()
    if text in {"HIGH", "EXCELLENT", "FULL", "A"}:
        return 100.0
    if text in {"MEDIUM", "GOOD", "B"}:
        return 72.0
    if text in {"LOW", "PARTIAL", "C"}:
        return 45.0
    if "BACKUP" in text:
        return 35.0
    return 55.0


class PredictionFeatureBuilder:
    """Construye el vector numérico que alimenta el aprendizaje V17/JHONNY ELITE.

    La clase no decide señales. Solo transforma el estado live + prepartido +
    lectura táctica en un snapshot reproducible para entrenamiento y auditoría.
    """

    VERSION = "JHONNY_ELITE_FEATURES_20.0"

    def build(
        self,
        *,
        match: Dict[str, Any],
        pre_match_profile: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
        tactical: Dict[str, Any] | None = None,
        market: Dict[str, Any] | None = None,
        risk: Dict[str, Any] | None = None,
        clock: Dict[str, Any] | None = None,
        data_quality: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        match = match or {}
        pre = pre_match_profile or {}
        context = context or {}
        tactical = tactical or {}
        market = market or {}
        risk = risk or {}
        clock = clock or {}
        data_quality = data_quality or {}

        fixture_id = str(match.get("fixture_id") or match.get("match_id") or "").strip()
        minute = safe_int(
            clock.get("api_minute")
            or match.get("effective_minute")
            or match.get("api_minute")
            or match.get("minute"),
            0,
        )
        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)
        total_goals = home_score + away_score

        possession_home = safe_float(match.get("possession_home"), 50.0)
        possession_away = safe_float(match.get("possession_away"), 50.0)
        suggested_market = str(
            market.get("suggested_market") or market.get("market") or match.get("market") or ""
        ).upper()

        tier = str(match.get("competition_tier") or pre.get("competition_tier") or "UNKNOWN").upper()
        odds = safe_float(match.get("odds") or match.get("odd") or match.get("cuota"), 0.0)
        implied_probability = (100.0 / odds) if odds > 1.0 else 0.0

        feature_vector = {
            # reloj / marcador
            "api_minute": float(minute),
            "minute_remaining": float(max(0, 100 - minute)),
            "home_score": float(home_score),
            "away_score": float(away_score),
            "total_goals": float(total_goals),
            "score_diff": float(abs(home_score - away_score)),
            "is_draw": 1.0 if home_score == away_score else 0.0,
            "is_added_time": float(bool01(match.get("is_added_time"))),

            # producción live
            "shots": safe_float(match.get("shots")),
            "shots_on_target": safe_float(match.get("shots_on_target")),
            "corners": safe_float(match.get("corners")),
            "xg": safe_float(match.get("xg") or match.get("xG")),
            "dangerous_attacks": safe_float(match.get("dangerous_attacks")),
            "red_cards": safe_float(match.get("red_cards")),
            "yellow_cards": safe_float(match.get("yellow_cards")),
            "possession_gap": abs(possession_home - possession_away),
            "goal_evidence_score": safe_float(match.get("goal_evidence_score")),
            "volume_score": safe_float(match.get("volume_score")),

            # contexto
            "pressure_score": safe_float(context.get("pressure_score")),
            "rhythm_score": safe_float(context.get("rhythm_score")),
            "goal_need_score": safe_float(context.get("goal_need_score")),
            "over_context_score": safe_float(context.get("over_context_score")),
            "under_context_score": safe_float(context.get("under_context_score")),
            "score_hold_probability": safe_float(context.get("score_hold_probability")),
            "under_transition_score": safe_float(context.get("under_transition_score")),

            # táctica
            "tactical_score": safe_float(tactical.get("tactical_score")),
            "offensive_volume_score": safe_float(tactical.get("offensive_volume_score")),
            "offensive_depth_score": safe_float(tactical.get("offensive_depth_score")),
            "recent_attack_proxy": safe_float(tactical.get("recent_attack_proxy")),

            # mercado interno
            "market_confidence": safe_float(market.get("market_confidence")),
            "over_score": safe_float(market.get("over_score")),
            "under_score": safe_float(market.get("under_score")),
            "market_is_over": 1.0 if suggested_market == "OVER" else 0.0,
            "market_is_under": 1.0 if suggested_market == "UNDER" else 0.0,
            "odds": odds,
            "implied_probability": implied_probability,
            "value_edge": safe_float(match.get("value_edge") or market.get("value_edge")),

            # riesgo/calidad
            "risk_score": safe_float(risk.get("risk_score")),
            "data_quality_score": quality_score(
                data_quality.get("data_quality") or match.get("data_quality")
            ),
            "clock_can_enter": float(bool01(clock.get("clock_can_enter"))),

            # prepartido — queda en 0 si todavía no se activó el candidato
            "prematch_available": float(bool01(pre.get("pre_match_available"))),
            "prematch_over_score": safe_float(pre.get("over_pre_match_score")),
            "prematch_under_score": safe_float(pre.get("under_pre_match_score")),
            "prematch_avg_goals": safe_float(pre.get("pre_match_avg_total_goals")),
            "prematch_avg_1h_goals": safe_float(pre.get("pre_match_avg_first_half_goals")),
            "prematch_avg_2h_goals": safe_float(pre.get("pre_match_avg_second_half_goals")),
            "home_over15_rate": safe_float(pre.get("home_recent_over_15_rate")),
            "away_over15_rate": safe_float(pre.get("away_recent_over_15_rate")),
            "home_over25_rate": safe_float(pre.get("home_recent_over_25_rate")),
            "away_over25_rate": safe_float(pre.get("away_recent_over_25_rate")),
            "home_btts_rate": safe_float(pre.get("home_recent_btts_rate")),
            "away_btts_rate": safe_float(pre.get("away_recent_btts_rate")),
            "league_over25_rate": safe_float(pre.get("league_recent_over_25_rate")),
            "league_btts_rate": safe_float(pre.get("league_recent_btts_rate")),

            # competencia
            "competition_weight": safe_float(match.get("competition_weight")),
            "world_cup_flag": float(bool01(match.get("world_cup_flag"))),
            "national_team_flag": float(bool01(match.get("national_team_flag"))),
            "major_tournament_flag": float(bool01(match.get("major_tournament_flag"))),
            "competition_tier_world_cup_elite": 1.0 if "WORLD_CUP" in tier else 0.0,
            "competition_tier_international_club_elite": 1.0 if "INTERNATIONAL_CLUB" in tier else 0.0,
            "competition_tier_national_team_elite": 1.0 if "NATIONAL_TEAM" in tier else 0.0,
            "competition_tier_priority_league": 1.0 if "PRIORITY" in tier or "TIER" in tier else 0.0,
            "competition_tier_country_review": 1.0 if "COUNTRY_REVIEW" in tier else 0.0,
        }

        signal_key = str(match.get("signal_key") or match.get("signal_id") or "")
        event_time = utc_now_iso()

        return {
            "feature_builder_version": self.VERSION,
            "fixture_id": fixture_id,
            "api_minute": minute,
            "signal_key": signal_key,
            "event_time": event_time,
            "feature_vector": feature_vector,
            "match_snapshot": dict(match),
            "pre_match_snapshot": dict(pre),
            "context_snapshot": dict(context),
            "tactical_snapshot": dict(tactical),
            "market_snapshot": dict(market),
            "risk_snapshot": dict(risk),
            "prediction_snapshot": {},
            "metadata": {
                "competition_tier": tier,
                "competition_weight": safe_float(match.get("competition_weight")),
                "world_cup_flag": bool01(match.get("world_cup_flag")),
                "national_team_flag": bool01(match.get("national_team_flag")),
                "major_tournament_flag": bool01(match.get("major_tournament_flag")),
                "league_filter_status": str(match.get("league_filter_status") or ""),
                "league": str(match.get("league") or ""),
                "country": str(match.get("country") or ""),
            },
        }
