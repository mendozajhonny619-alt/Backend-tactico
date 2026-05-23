from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.v17.core.constants import (
    MAX_CLOCK_FREEZE_SCANS,
    MAX_DATA_AGE_SECONDS_FOR_ENTER,
)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


class ClockGuard:
    """
    Controla sincronía del minuto.

    El reloj manda.
    Si el dato live está atrasado, congelado o viejo, no se permite ENTER.
    """

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        api_minute = safe_int(match.get("api_minute") or match.get("minute"), 0)
        same_minute_count = safe_int(match.get("same_minute_count"), 0)

        updated_at = match.get("updated_at") or match.get("_snapshot_at") or match.get("timestamp")
        data_age_seconds = self._calculate_age_seconds(updated_at)

        clock_frozen = same_minute_count >= MAX_CLOCK_FREEZE_SCANS
        data_too_old = data_age_seconds > MAX_DATA_AGE_SECONDS_FOR_ENTER
        invalid_minute = api_minute <= 0 or api_minute > 130

        minute_lag_detected = bool(match.get("minute_lag_detected", False))

        blockers = []
        warnings = []

        if invalid_minute:
            blockers.append("INVALID_MINUTE")

        if data_too_old:
            blockers.append("DATA_TOO_OLD")

        if clock_frozen:
            blockers.append("CLOCK_FROZEN")

        if minute_lag_detected:
            warnings.append("MINUTE_LAG_DETECTED")

        if data_age_seconds > 60 and not data_too_old:
            warnings.append("DATA_AGING")

        if same_minute_count >= 2 and not clock_frozen:
            warnings.append("CLOCK_STALE_WARNING")

        if blockers:
            status = "BLOCKED_CLOCK"
            action = "NO_OPERAR"
            can_enter = False
        elif warnings:
            status = "CLOCK_WARNING"
            action = "WAIT_CONFIRMATION"
            can_enter = False
        else:
            status = "CLOCK_OK"
            action = "CLOCK_CONFIRMED"
            can_enter = True

        estimated_minute = api_minute
        if data_age_seconds > 0 and data_age_seconds <= 600 and api_minute > 0:
            estimated_minute = min(130, api_minute + int(data_age_seconds // 60))

        return {
            "api_minute": api_minute,
            "display_minute": api_minute,
            "estimated_minute": estimated_minute,
            "data_age_seconds": data_age_seconds,
            "same_minute_count": same_minute_count,
            "clock_frozen": clock_frozen,
            "minute_lag_detected": minute_lag_detected,
            "clock_status": status,
            "clock_action": action,
            "clock_can_enter": can_enter,
            "clock_blockers": blockers,
            "clock_warnings": warnings,
        }

    def _calculate_age_seconds(self, updated_at: Any) -> int:
        parsed = parse_datetime(updated_at)
        if not parsed:
            return 9999

        now = datetime.now(timezone.utc)
        diff = now - parsed
        return max(0, int(diff.total_seconds()))
