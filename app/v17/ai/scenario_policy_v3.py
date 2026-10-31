"""V3 scenario policy: single modal FT score, optional evidence-backed alternative.

Does not alter Poisson's full distribution or MasterDecisionAI authority. The
second scenario is only a UI-facing *model hypothesis*, not a market signal.
All thresholds here are explicitly UNCALIBRATED development heuristics.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _n(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def choose_scenarios(match: Dict[str, Any], distribution: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = [s for s in distribution if isinstance(s, dict) and s.get('score') != 'OTROS']
    primary = dict(ranked[0]) if ranked else None
    alternative = dict(ranked[1]) if len(ranked) > 1 else None
    result = {
        'scenario_primary': primary,
        'scenario_secondary': None,
        'scenario_secondary_reason': None,
        'scenario_secondary_status': 'NOT_JUSTIFIED',
        'scenario_policy_version': 'V3_3_EXPERIMENTAL',
    }
    if not primary or not alternative:
        return result

    p1 = _n(primary.get('probability'))
    p2 = _n(alternative.get('probability'))
    minute = _n(match.get('effective_minute') or match.get('api_minute') or match.get('minute'))
    if p2 < 15 or p1 <= 0 or p2 / p1 < 0.58 or minute >= 96:
        return result

    available_windows = sum(
        1 for w in (5, 10, 15) if isinstance(match.get(f'window_{w}'), dict)
        and match[f'window_{w}'].get('available') is True
    )
    temporal = bool(match.get('temporal_memory_ready')) and available_windows >= 2
    recent_threat = _n(match.get('recent_threat_score'))
    regime = str(match.get('dynamic_match_state') or '').upper()
    material_event = bool(match.get('post_goal_reanalysis') or match.get('score_changed_since_last_scan')
                          or match.get('red_card_context_change') or match.get('lineup_impact_verified'))
    significant_regime = temporal and regime in {'OPENING', 'OPEN', 'CLOSING', 'CLOSED', 'REVERSING'}
    sustained = temporal and (recent_threat >= 65 or (recent_threat <= 20 and regime in {'CLOSING', 'CLOSED'}))
    near_tie = temporal and p2 >= 22 and p2 / p1 >= 0.82
    if material_event:
        reason = 'EVENTO_MATERIAL_REQUIERE_REANALISIS'
    elif significant_regime and sustained:
        reason = 'CAMBIO_TACTICO_RESPALDADO_POR_VENTANAS'
    elif near_tie:
        reason = 'INCERTIDUMBRE_MATERIAL_CON_MEMORIA_TEMPORAL'
    else:
        return result

    result['scenario_secondary'] = alternative
    result['scenario_secondary_reason'] = reason
    result['scenario_secondary_status'] = 'CONDITIONAL_EXPERIMENTAL'
    return result
