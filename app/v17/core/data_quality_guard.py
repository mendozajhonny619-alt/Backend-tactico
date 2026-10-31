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

        # API-Football normalizes these as `shots`/`dangerous_attacks` and
        # `shots_on_target`. The previous guard read ONLY older flat aliases,
        # labelling populated fixtures WEAK_DATA or NO_SHOTS_DATA.
        def first_present(*names: str) -> Any:
            for name in names:
                value = match.get(name)
                if value is not None and value != "":
                    return value
            return None

        total_attacks = safe_int(first_present("total_attacks"), 0)
        total_dangerous = safe_int(first_present("dangerous_attacks", "total_dangerous_attacks"), 0)
        total_shots = safe_int(first_present("shots", "total_shots"), 0)
        total_shots_on = safe_int(first_present("shots_on_target", "total_shots_on"), 0)

        side_rows = [match.get("home_stats"), match.get("away_stats")]
        known_fields = set()
        for row in side_rows:
            if isinstance(row, dict):
                known_fields.update(row.get("stats_available_fields") or [])
        dangerous_stat_available = "Dangerous Attacks" in known_fields

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

        # Dangerous Attacks is not a standard field in every API-Football
        # competition. Missing *optional* data must not weaken a fixture that
        # has independently verified finishing statistics.
        if minute >= 25 and total_dangerous <= 0 and (
            dangerous_stat_available or (not known_fields and total_shots <= 0)
        ):
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
