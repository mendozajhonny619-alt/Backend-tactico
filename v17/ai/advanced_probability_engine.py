from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def si(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class AdvancedProbabilityEngine:
    """Modelo matemático live ligero basado en hazard + Poisson.

    No pretende "garantizar" un resultado. Convierte la evidencia disponible
    en probabilidades calibrables y escenarios de marcador que luego son
    revisados por MasterDecisionAI.
    """

    VERSION = "JE_POISSON_HAZARD_19.0"

    def evaluate(
        self,
        match: Dict[str, Any],
        context: Dict[str, Any],
        tactical: Dict[str, Any],
        pre_match: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        pre = pre_match or {}
        minute = max(1, si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 1))
        home = si(match.get("home_score"), 0)
        away = si(match.get("away_score"), 0)
        current_total = home + away
        remaining_minutes = clamp(96.0 - minute, 1.0, 96.0)

        xg = max(0.0, sf(match.get("xg") or match.get("xG")))
        shots = max(0.0, sf(match.get("shots")))
        sot = max(0.0, sf(match.get("shots_on_target")))
        dangerous = max(0.0, sf(match.get("dangerous_attacks")))

        # Cuando xG no existe, estimamos una amenaza esperada conservadora.
        xg_proxy = max(xg, sot * 0.24 + max(0.0, shots - sot) * 0.055 + dangerous * 0.004)
        live_rate_per_min = xg_proxy / max(12.0, float(minute))

        prematch_avg = sf(pre.get("pre_match_avg_total_goals"), 0.0)
        if prematch_avg <= 0:
            prematch_avg = 2.45
        prematch_rate_per_min = prematch_avg / 96.0

        pressure = sf(context.get("pressure_score"), 45.0)
        rhythm = sf(context.get("rhythm_score"), 45.0)
        goal_need = sf(context.get("goal_need_score"), 45.0)
        tactical_score = sf(tactical.get("tactical_score"), 45.0)
        recent_attack = max(sf(tactical.get("recent_attack_proxy"), 35.0), sf(match.get("recent_threat_score"), 0.0))
        dynamic_instability = sf(match.get("dynamic_instability_score"), 0.0)

        rate = live_rate_per_min * 0.58 + prematch_rate_per_min * 0.42
        intensity_multiplier = clamp(
            0.55
            + pressure / 230.0
            + rhythm / 300.0
            + goal_need / 420.0
            + tactical_score / 520.0
            + recent_attack / 700.0
            + dynamic_instability / 900.0,
            0.55,
            1.85,
        )

        # Marcadores amplios pueden provocar cierre; empates/margen mínimo suelen
        # sostener necesidad de gol. La capa táctica aún puede contradecirlo.
        score_diff = abs(home - away)
        if score_diff >= 2 and minute >= 65:
            intensity_multiplier *= 0.86
        elif score_diff <= 1 and minute >= 55:
            intensity_multiplier *= 1.08

        remaining_lambda = clamp(rate * remaining_minutes * intensity_multiplier, 0.03, 4.20)
        p_no_more_goal = math.exp(-remaining_lambda)
        p_goal = 1.0 - p_no_more_goal
        p_two_plus = 1.0 - math.exp(-remaining_lambda) * (1.0 + remaining_lambda)

        home_share = self._home_attack_share(match)
        if match.get("dynamics_available"):
            recent_home = sf(match.get("recent_home_threat_score"), 0.0)
            recent_away = sf(match.get("recent_away_threat_score"), 0.0)
            if recent_home + recent_away > 5:
                recent_share = recent_home / (recent_home + recent_away)
                home_share = clamp(home_share * 0.75 + recent_share * 0.25, 0.15, 0.85)
        home_lambda = remaining_lambda * home_share
        away_lambda = remaining_lambda * (1.0 - home_share)

        scenarios = self._score_scenarios(home, away, home_lambda, away_lambda)
        primary = scenarios[0] if scenarios else {"score": f"{home}-{away}", "probability": p_no_more_goal * 100}

        instability = clamp(
            rhythm * 0.30
            + pressure * 0.28
            + recent_attack * 0.18
            + sf(context.get("over_context_score"), 0.0) * 0.14
            + min(100.0, remaining_lambda * 35.0) * 0.08
            + dynamic_instability * 0.12,
            0.0,
            100.0,
        )

        alternatives: List[Dict[str, Any]] = []
        if instability >= 48:
            alternatives = scenarios[1:3]
        elif scenarios[1:2] and scenarios[1]["probability"] >= 18:
            alternatives = scenarios[1:2]

        return {
            "math_engine_version": self.VERSION,
            "expected_goals_remaining": round(remaining_lambda, 3),
            "probability_next_goal": round(p_goal * 100, 2),
            "probability_no_more_goals": round(p_no_more_goal * 100, 2),
            "probability_two_plus_goals": round(p_two_plus * 100, 2),
            "home_next_goal_probability": round(p_goal * home_share * 100, 2),
            "away_next_goal_probability": round(p_goal * (1.0 - home_share) * 100, 2),
            "home_attack_share": round(home_share * 100, 2),
            "instability_score": round(instability, 2),
            "primary_final_score": primary.get("score"),
            "primary_score_probability": round(sf(primary.get("probability")), 2),
            "alternative_scores": alternatives,
            "score_scenarios": scenarios[:6],
            "math_support_over": round(p_goal * 100, 2),
            "math_support_under": round(p_no_more_goal * 100, 2),
            "current_total_goals": current_total,
            "remaining_minutes_model": round(remaining_minutes, 1),
        }

    def _home_attack_share(self, match: Dict[str, Any]) -> float:
        hs = match.get("home_stats") if isinstance(match.get("home_stats"), dict) else {}
        aw = match.get("away_stats") if isinstance(match.get("away_stats"), dict) else {}

        home_threat = (
            sf(hs.get("xG") or hs.get("xg")) * 5.0
            + sf(hs.get("shots_on_target")) * 1.8
            + sf(hs.get("shots")) * 0.45
            + sf(hs.get("dangerous_attacks")) * 0.08
        )
        away_threat = (
            sf(aw.get("xG") or aw.get("xg")) * 5.0
            + sf(aw.get("shots_on_target")) * 1.8
            + sf(aw.get("shots")) * 0.45
            + sf(aw.get("dangerous_attacks")) * 0.08
        )

        if home_threat + away_threat <= 0.1:
            possession_home = sf(match.get("possession_home"), 50.0)
            return clamp(possession_home / 100.0, 0.32, 0.68)

        return clamp(home_threat / (home_threat + away_threat), 0.18, 0.82)

    def _score_scenarios(
        self,
        current_home: int,
        current_away: int,
        home_lambda: float,
        away_lambda: float,
    ) -> List[Dict[str, Any]]:
        rows: List[Tuple[float, int, int]] = []
        for hg in range(0, 5):
            ph = self._poisson(hg, home_lambda)
            for ag in range(0, 5):
                pa = self._poisson(ag, away_lambda)
                rows.append((ph * pa, current_home + hg, current_away + ag))
        rows.sort(reverse=True, key=lambda x: x[0])
        return [
            {
                "score": f"{h}-{a}",
                "probability": round(p * 100, 2),
                "additional_home_goals": h - current_home,
                "additional_away_goals": a - current_away,
            }
            for p, h, a in rows
        ]

    @staticmethod
    def _poisson(k: int, lam: float) -> float:
        return math.exp(-lam) * (lam ** k) / math.factorial(k)
