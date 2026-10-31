"""Consistent conditional Poisson probabilities for FULL-TIME half-goal lines.

Pure math, no provider calls.  This is an experimental pricing kernel, NOT a
calibration certificate or permission to publish bets.  Integer/Asian lines
have pushes/partial settlement and are deliberately unsupported.
"""
from __future__ import annotations

import math
from typing import Dict, Optional


def half_goal_line_probability(
    remaining_lambda: float,
    current_goals: int,
    line: float,
    direction: str,
) -> Optional[float]:
    """Conditional P(binary OVER/UNDER half-goal total on final 90-min score).

    Returns ``None`` for malformed input, non-FT/Asian lines or infeasible
    parameters. A valid returned 0.0 is not an unknown value.
    """
    if isinstance(remaining_lambda, bool) or isinstance(current_goals, bool) or isinstance(line, bool):
        return None
    try:
        lam = float(remaining_lambda)
        goals = int(current_goals)
        threshold = float(line)
    except (TypeError, ValueError, OverflowError):
        return None
    if (not all(math.isfinite(v) for v in (lam, float(goals), threshold))
            or not 0.0 <= lam <= 20.0
            or goals < 0 or float(current_goals) != goals
            or not 0.0 < threshold <= 25.5
            or not math.isclose(threshold % 1, 0.5, rel_tol=0, abs_tol=1e-8)
            or direction not in {"OVER", "UNDER"}):
        return None
    needed = int(math.floor(threshold)) + 1 - goals
    if needed <= 0:
        p_over = 1.0
    else:
        # CDF of the additional goal count, evaluated by stable recurrence.
        term = math.exp(-lam)
        cdf = term
        for k in range(1, needed):
            term *= lam / k
            cdf += term
        p_over = max(0.0, min(1.0, 1.0 - cdf))
    return p_over if direction == "OVER" else 1.0 - p_over


def preview_full_time_lines(lam: float, current_goals: int, *, max_line: float = 6.5) -> Dict[str, Dict[str, float]]:
    """Research-only exact-line probabilities derived from ONE distribution.

    Different lines remain distinct.  Outputs do not imply available prices.
    """
    rows: Dict[str, Dict[str, float]] = {}
    for line_tenths in range(5, int(max_line * 10) + 1, 10):
        line = line_tenths / 10.0
        over = half_goal_line_probability(lam, current_goals, line, "OVER")
        under = half_goal_line_probability(lam, current_goals, line, "UNDER")
        if over is not None and under is not None:
            rows[f"{line:.1f}"] = {
                "over_probability": round(over * 100.0, 4),
                "under_probability": round(under * 100.0, 4),
            }
    return rows
