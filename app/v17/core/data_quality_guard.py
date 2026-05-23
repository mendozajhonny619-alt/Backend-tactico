from __future__ import annotations

from typing import Any, Dict, List


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


class DataQualityGuard:
    """
    Revisa si el partido tiene datos mínimos para ser analizado.

    No decide si la señal entra.
    Solo indica si los datos son suficientes, débiles o inválidos.
    """

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []

        match_id = match.get("match_id") or match.get("fixture_id")
        home = match.get("home_team")
        away = match.get("away_team")
        minute = safe_int(match.get("api_minute"), 0)

        home_score = safe_int(match.get("home_score"), 0)
        away_score = safe_int(match.get("away_score"), 0)

        total_attacks = safe_int(match.get("total_attacks"), 0)
        total_dangerous = safe_int(match.get("total_dangerous_attacks"), 0)
        total_shots = safe_int(match.get("total_shots"), 0)
        total_shots_on = safe_int(match.get("total_shots_on"), 0)

        if not match_id:
            issues.append("MISSING_MATCH_ID")

        if not home or not away:
            issues.append("MISSING_TEAMS")

        if minute <= 0 or minute > 130:
            issues.append("INVALID_MINUTE")

        if home_score < 0 or away_score < 0:
            issues.append("INVALID_SCORE")

        if total_attacks <= 0 and total_dangerous <= 0 and total_shots <= 0:
            warnings.append("LOW_STATS_DATA")

        if minute >= 15 and total_shots <= 0:
            warnings.append("NO_SHOTS_DATA")

        if minute >= 25 and total_dangerous <= 0:
            warnings.append("NO_DANGEROUS_ATTACKS_DATA")

        is_valid = len(issues) == 0
        is_weak = is_valid and len(warnings) > 0

        if not is_valid:
            status = "INVALID_DATA"
        elif is_weak:
            status = "WEAK_DATA"
        else:
            status = "DATA_OK"

        return {
            "data_quality_status": status,
            "data_valid": is_valid,
            "data_weak": is_weak,
            "data_issues": issues,
            "data_warnings": warnings,
        }
