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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        text = str(value).strip()
        if not text:
            return None

        text = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def normalize_text(value: Any) -> str:
    return str(value or "").strip().upper()


class ClockGuard:
    """
    Controla sincronía del minuto.

    Regla V17:
    - Si el reloj está bloqueado, no se permite ENTER.
    - Si el dato es viejo, no se permite ENTER.
    - Si falta timestamp, no se asume dato fresco automáticamente.
    - Si falta timestamp PERO hay estadísticas live reales, se permite análisis controlado.
    - Minuto 45/46 puede ser descanso real y se manda a HALFTIME_WAIT.
    """

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        api_minute = safe_int(
            match.get("api_minute")
            or match.get("minute")
            or match.get("display_minute")
            or match.get("current_minute")
            or match.get("match_minute"),
            0,
        )

        same_minute_count = safe_int(match.get("same_minute_count"), 0)

        updated_at = (
            match.get("updated_at")
            or match.get("_snapshot_at")
            or match.get("timestamp")
            or match.get("last_update")
            or match.get("sync_updated_at")
            or match.get("created_at")
        )

        timestamp_missing = updated_at is None or parse_datetime(updated_at) is None
        data_age_seconds = self._calculate_age_seconds(updated_at)

        if data_age_seconds >= 9999:
            fallback_age = match.get("data_age_seconds")
            try:
                if fallback_age is not None:
                    data_age_seconds = int(float(fallback_age))
                    timestamp_missing = False
            except Exception:
                pass

        match_status = self._extract_match_status(match)

        is_halftime_status = self._is_halftime_status(match_status)
        is_possible_halftime_pause = self._is_possible_halftime_pause(
            api_minute=api_minute,
            same_minute_count=same_minute_count,
            data_age_seconds=data_age_seconds,
            match_status=match_status,
        )

        halftime_wait = is_halftime_status or is_possible_halftime_pause

        raw_clock_frozen = same_minute_count >= MAX_CLOCK_FREEZE_SCANS
        clock_frozen = raw_clock_frozen and not halftime_wait

        data_too_old = (
            data_age_seconds > MAX_DATA_AGE_SECONDS_FOR_ENTER
            and not timestamp_missing
        )

        invalid_minute = api_minute <= 0 or api_minute > 130
        minute_lag_detected = bool(match.get("minute_lag_detected", False))

        stats_confirmed = self._has_confirmed_live_stats(match)

        blockers = []
        warnings = []

        if invalid_minute:
            blockers.append("INVALID_MINUTE")

        if data_too_old:
            blockers.append("DATA_TOO_OLD")

        if clock_frozen:
            blockers.append("CLOCK_FROZEN")

        if halftime_wait:
            warnings.append("HALFTIME_WAIT")
            if is_halftime_status:
                warnings.append("HALFTIME_STATUS_CONFIRMED")
            else:
                warnings.append("POSSIBLE_HALFTIME_PAUSE")

        if minute_lag_detected:
            warnings.append("MINUTE_LAG_DETECTED")

        if timestamp_missing and not data_too_old:
            if stats_confirmed and api_minute > 0 and not halftime_wait and not clock_frozen:
                warnings.append("DATA_TIMESTAMP_MISSING_BUT_STATS_CONFIRMED")
            else:
                warnings.append("DATA_TIMESTAMP_MISSING")

        if data_age_seconds > 60 and not data_too_old and not timestamp_missing:
            warnings.append("DATA_AGING")

        if same_minute_count >= 2 and not clock_frozen and not halftime_wait:
            warnings.append("CLOCK_STALE_WARNING")

        if blockers:
            status = "BLOCKED_CLOCK"
            action = "NO_OPERAR"
            can_enter = False

        elif halftime_wait:
            status = "HALFTIME_WAIT"
            action = "WAIT_SECOND_HALF_CONFIRMATION"
            can_enter = False

        elif warnings:
            only_soft_clock_warning = (
                len(warnings) == 1
                and "DATA_TIMESTAMP_MISSING_BUT_STATS_CONFIRMED" in warnings
            )

            if only_soft_clock_warning:
                status = "CLOCK_STATS_CONFIRMED"
                action = "CLOCK_CONFIRMED_BY_STATS"
                can_enter = True
            else:
                status = "CLOCK_WARNING"
                action = "WAIT_CONFIRMATION"
                can_enter = False

        else:
            status = "CLOCK_OK"
            action = "CLOCK_CONFIRMED"
            can_enter = True

        estimated_minute = api_minute

        if (
            data_age_seconds > 0
            and data_age_seconds <= 600
            and api_minute > 0
            and not halftime_wait
            and not timestamp_missing
        ):
            estimated_minute = min(130, api_minute + int(data_age_seconds // 60))

        return {
            "api_minute": api_minute,
            "display_minute": api_minute,
            "estimated_minute": estimated_minute,
            "data_age_seconds": data_age_seconds,
            "same_minute_count": same_minute_count,
            "timestamp_missing": timestamp_missing,
            "stats_confirmed": stats_confirmed,

            "match_status_raw": match_status,
            "halftime_wait": halftime_wait,
            "halftime_status_confirmed": is_halftime_status,
            "possible_halftime_pause": is_possible_halftime_pause,

            "clock_frozen": clock_frozen,
            "raw_clock_frozen": raw_clock_frozen,
            "minute_lag_detected": minute_lag_detected,

            "clock_status": status,
            "clock_action": action,
            "clock_can_enter": can_enter,
            "clock_blockers": blockers,
            "clock_warnings": warnings,
        }

    def _has_confirmed_live_stats(self, match: Dict[str, Any]) -> bool:
        shots = safe_float(match.get("shots"), 0.0)
        shots_on_target = safe_float(match.get("shots_on_target"), 0.0)
        corners = safe_float(match.get("corners"), 0.0)
        xg = safe_float(match.get("xg") or match.get("xG"), 0.0)
        dangerous_attacks = safe_float(match.get("dangerous_attacks"), 0.0)

        home_shots = safe_float(match.get("home_shots") or match.get("shots_home"), 0.0)
        away_shots = safe_float(match.get("away_shots") or match.get("shots_away"), 0.0)
        home_sot = safe_float(match.get("home_shots_on_target") or match.get("sot_home"), 0.0)
        away_sot = safe_float(match.get("away_shots_on_target") or match.get("sot_away"), 0.0)

        return (
            shots > 0
            or shots_on_target > 0
            or corners > 0
            or xg > 0.05
            or dangerous_attacks > 0
            or home_shots > 0
            or away_shots > 0
            or home_sot > 0
            or away_sot > 0
        )

    def _extract_match_status(self, match: Dict[str, Any]) -> str:
        status_candidates = [
            match.get("status"),
            match.get("match_status"),
            match.get("fixture_status"),
            match.get("short_status"),
            match.get("long_status"),
            match.get("status_short"),
            match.get("status_long"),
            match.get("elapsed_status"),
            match.get("period"),
            match.get("game_status"),
        ]

        fixture = match.get("fixture")
        if isinstance(fixture, dict):
            fixture_status = fixture.get("status")
            if isinstance(fixture_status, dict):
                status_candidates.extend([
                    fixture_status.get("short"),
                    fixture_status.get("long"),
                    fixture_status.get("elapsed"),
                ])
            else:
                status_candidates.append(fixture_status)

        status_obj = match.get("status_obj")
        if isinstance(status_obj, dict):
            status_candidates.extend([
                status_obj.get("short"),
                status_obj.get("long"),
                status_obj.get("elapsed"),
            ])

        for candidate in status_candidates:
            text = normalize_text(candidate)
            if text:
                return text

        return ""

    def _is_halftime_status(self, status: str) -> bool:
        if not status:
            return False

        halftime_terms = {
            "HT",
            "HALFTIME",
            "HALF TIME",
            "HALF-TIME",
            "DESCANSO",
            "INTERVALO",
            "BREAK",
            "FIRST HALF ENDED",
            "1H_END",
            "FIRST_HALF_END",
            "HALF",
        }

        if status in halftime_terms:
            return True

        if "HALF" in status and "TIME" in status:
            return True

        if "DESCANSO" in status:
            return True

        if "INTERVAL" in status:
            return True

        return False

    def _is_possible_halftime_pause(
        self,
        api_minute: int,
        same_minute_count: int,
        data_age_seconds: int,
        match_status: str,
    ) -> bool:
        if api_minute not in {45, 46}:
            return False

        if self._is_live_second_half_status(match_status):
            return False

        if same_minute_count >= MAX_CLOCK_FREEZE_SCANS:
            return True

        if same_minute_count >= 2 and data_age_seconds <= 180:
            return True

        return False

    def _is_live_second_half_status(self, status: str) -> bool:
        if not status:
            return False

        second_half_terms = {
            "2H",
            "SECOND HALF",
            "SECOND_HALF",
            "LIVE_2H",
        }

        if status in second_half_terms:
            return True

        if "SECOND" in status and "HALF" in status:
            return True

        return False

    def _calculate_age_seconds(self, updated_at: Any) -> int:
        parsed = parse_datetime(updated_at)

        if not parsed:
            return 9999

        now = datetime.now(timezone.utc)
        diff = now - parsed

        return max(0, int(diff.total_seconds()))
