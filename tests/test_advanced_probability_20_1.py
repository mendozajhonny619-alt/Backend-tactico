from app.v17.ai.advanced_probability_engine import AdvancedProbabilityEngine


def base_match():
    return {
        "api_minute": 75, "effective_minute": 75, "home_score": 1, "away_score": 0,
        "shots": 12, "shots_on_target": 4, "dangerous_attacks": 38, "xg": 1.20,
        "home_stats": {"shots": 7, "shots_on_target": 3, "dangerous_attacks": 23, "xG": 0.75},
        "away_stats": {"shots": 5, "shots_on_target": 1, "dangerous_attacks": 15, "xG": 0.45},
        "temporal_memory_ready": True,
    }


def test_recent_closed_phase_increases_under_support_at_75():
    engine = AdvancedProbabilityEngine()
    closed = base_match()
    closed.update({
        "window_5": {"available": True, "observed_minutes": 5, "delta_xg": 0.02, "delta_sot": 0, "delta_shots": 1, "delta_dangerous_attacks": 2, "threat_score": 8},
        "window_10": {"available": True, "observed_minutes": 10, "delta_xg": 0.05, "delta_sot": 0, "delta_shots": 1, "delta_dangerous_attacks": 4, "threat_score": 12},
        "window_15": {"available": True, "observed_minutes": 15, "delta_xg": 0.08, "delta_sot": 0, "delta_shots": 2, "delta_dangerous_attacks": 6, "threat_score": 18},
    })
    opened = base_match()
    opened.update({
        "window_5": {"available": True, "observed_minutes": 5, "delta_xg": 0.42, "delta_sot": 2, "delta_shots": 4, "delta_dangerous_attacks": 10, "threat_score": 82},
        "window_10": {"available": True, "observed_minutes": 10, "delta_xg": 0.65, "delta_sot": 3, "delta_shots": 7, "delta_dangerous_attacks": 18, "threat_score": 86},
        "window_15": {"available": True, "observed_minutes": 15, "delta_xg": 0.82, "delta_sot": 4, "delta_shots": 9, "delta_dangerous_attacks": 24, "threat_score": 88},
    })
    low_context = {"pressure_score": 25, "rhythm_score": 25, "goal_need_score": 35, "over_context_score": 20}
    high_context = {"pressure_score": 80, "rhythm_score": 82, "goal_need_score": 70, "over_context_score": 85}
    tactical = {"tactical_score": 60, "recent_attack_proxy": 20}
    a = engine.evaluate(closed, low_context, tactical, {"pre_match_avg_total_goals": 2.4})
    b = engine.evaluate(opened, high_context, {**tactical, "recent_attack_proxy": 80}, {"pre_match_avg_total_goals": 2.4})
    assert a["math_support_under"] > b["math_support_under"]
    assert a["expected_goals_remaining"] < b["expected_goals_remaining"]
