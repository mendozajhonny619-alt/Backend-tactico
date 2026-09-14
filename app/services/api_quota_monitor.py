from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict


def _as_int(value: Any):
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiQuotaMonitor:
    """In-memory quota telemetry from API-SPORTS response headers.

    It does not make extra API calls. It only reads headers from responses the
    system was already going to make, so quota monitoring itself costs zero.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._state: Dict[str, Any] = {
            "observed_requests": 0,
            "daily_limit": None,
            "daily_remaining": None,
            "minute_limit": None,
            "minute_remaining": None,
            "last_endpoint": None,
            "last_status_code": None,
            "last_updated_at": None,
        }

    def record_response(self, response: Any, endpoint: str = "") -> None:
        if response is None:
            return
        headers = getattr(response, "headers", {}) or {}
        with self._lock:
            self._state["observed_requests"] = int(self._state.get("observed_requests") or 0) + 1
            self._state["daily_limit"] = _as_int(
                headers.get("x-ratelimit-requests-limit")
                or headers.get("X-RateLimit-Requests-Limit")
            ) or self._state.get("daily_limit")
            self._state["daily_remaining"] = _as_int(
                headers.get("x-ratelimit-requests-remaining")
                or headers.get("X-RateLimit-Requests-Remaining")
            )
            if self._state["daily_remaining"] is None:
                self._state["daily_remaining"] = _as_int(headers.get("x-ratelimit-remaining")) or self._state.get("daily_remaining")
            self._state["minute_limit"] = _as_int(headers.get("X-RateLimit-Limit")) or self._state.get("minute_limit")
            self._state["minute_remaining"] = _as_int(headers.get("X-RateLimit-Remaining")) or self._state.get("minute_remaining")
            self._state["last_endpoint"] = endpoint
            self._state["last_status_code"] = getattr(response, "status_code", None)
            self._state["last_updated_at"] = _now()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            state = dict(self._state)
        limit = state.get("daily_limit")
        remaining = state.get("daily_remaining")
        if isinstance(limit, int) and limit > 0 and isinstance(remaining, int):
            used = max(0, limit - remaining)
            state["daily_used"] = used
            state["daily_used_percent"] = round((used / limit) * 100, 2)
        else:
            state["daily_used"] = None
            state["daily_used_percent"] = None
        return state

    def can_spend(self, required: int = 1, reserve: int = 0) -> bool:
        """Return False when known daily quota is too close to the protected reserve.

        Unknown header state is treated as spendable so a provider that omits quota
        headers does not disable the system. This method never performs network I/O.
        """
        state = self.snapshot()
        remaining = state.get("daily_remaining")
        if not isinstance(remaining, int):
            return True
        return remaining - max(0, int(required)) >= max(0, int(reserve))

    def pressure_level(self, high_percent: float = 82.0, critical_percent: float = 92.0, critical_remaining: int = 100) -> str:
        state = self.snapshot()
        used = state.get("daily_used_percent")
        remaining = state.get("daily_remaining")
        if isinstance(remaining, int) and remaining <= max(0, int(critical_remaining)):
            return "CRITICAL"
        if isinstance(used, (int, float)) and used >= float(critical_percent):
            return "CRITICAL"
        if isinstance(used, (int, float)) and used >= float(high_percent):
            return "HIGH"
        return "NORMAL"


api_quota_monitor = ApiQuotaMonitor()
