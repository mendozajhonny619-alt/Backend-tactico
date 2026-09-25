from __future__ import annotations

from collections import deque
from copy import deepcopy
import time
from typing import Any, Deque, Dict


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def si(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


class LiveDynamicsMemory:
    """Rolling live memory used to detect *change*, not only accumulated totals.

    The original project mostly interpreted cumulative match statistics. This
    memory layer compares consecutive snapshots so JHONNY ELITE can distinguish
    a match that is opening now from one that merely accumulated activity much
    earlier in the game.
    """

    VERSION = "JE_LIVE_DYNAMICS_20.0"

    def __init__(self, max_snapshots: int = 8, expiry_seconds: int = 4 * 60 * 60) -> None:
        self.max_snapshots = max(3, int(max_snapshots))
        self.expiry_seconds = max(600, int(expiry_seconds))
        self._history: Dict[str, Deque[Dict[str, Any]]] = {}
        self._last_cleanup = 0.0

    def enrich(self, match: Dict[str, Any]) -> Dict[str, Any]:
        item = deepcopy(match or {})
        fixture_id = str(item.get("match_id") or item.get("fixture_id") or "").strip()
        if not fixture_id:
            return self._with_empty_dynamics(item)

        now = sf(item.get("fetched_at") or item.get("sync_updated_at"), time.time())
        if now <= 0:
            now = time.time()

        self._cleanup(now)
        history = self._history.setdefault(fixture_id, deque(maxlen=self.max_snapshots))
        current = self._snapshot(item, now)
        previous = history[-1] if history else None

        dynamics = self._calculate(previous, current, item)
        current["recent_threat_score"] = dynamics["recent_threat_score"]
        history.append(current)
        return {**item, **dynamics}

    def _calculate(
        self,
        previous: Dict[str, Any] | None,
        current: Dict[str, Any],
        match: Dict[str, Any],
    ) -> Dict[str, Any]:
        if previous is None:
            return self._empty_dynamics()

        elapsed_seconds = max(1.0, current["at"] - previous["at"])
        elapsed_minutes = max(0.25, elapsed_seconds / 60.0)

        def delta(key: str) -> float:
            return max(0.0, sf(current.get(key)) - sf(previous.get(key)))

        d_shots = delta("shots")
        d_sot = delta("sot")
        d_danger = delta("dangerous")
        d_corners = delta("corners")
        d_xg = delta("xg")

        home = current.get("home", {})
        prev_home = previous.get("home", {})
        away = current.get("away", {})
        prev_away = previous.get("away", {})

        home_threat = self._side_delta_threat(home, prev_home, elapsed_minutes)
        away_threat = self._side_delta_threat(away, prev_away, elapsed_minutes)

        # Total short-window pressure, normalized around a 90-second window.
        raw_threat = (
            d_sot * 23.0
            + d_shots * 6.0
            + d_danger * 1.15
            + d_corners * 8.0
            + d_xg * 38.0
        )
        window_normalizer = clamp(1.5 / elapsed_minutes, 0.45, 2.25)
        recent_threat = clamp(raw_threat * window_normalizer)

        score_changed = (
            current["home_score"] != previous["home_score"]
            or current["away_score"] != previous["away_score"]
        )
        total_goal_delta = max(
            0,
            current["home_score"] + current["away_score"]
            - previous["home_score"] - previous["away_score"],
        )

        previous_threat = sf(previous.get("recent_threat_score"), 0.0)
        if recent_threat >= 58 and recent_threat >= previous_threat + 10:
            trend = "RISING"
            dynamic_state = "OPENING"
        elif recent_threat <= 24 and previous_threat >= 42:
            trend = "FALLING"
            dynamic_state = "CLOSING"
        elif recent_threat >= 52:
            trend = "HIGH"
            dynamic_state = "OPEN"
        elif recent_threat <= 20:
            trend = "LOW"
            dynamic_state = "CLOSED"
        else:
            trend = "STABLE"
            dynamic_state = "BALANCED"

        instability = clamp(
            recent_threat * 0.60
            + (25.0 if score_changed else 0.0)
            + min(18.0, total_goal_delta * 12.0)
            + min(12.0, abs(home_threat - away_threat) * 0.12),
        )

        if home_threat > away_threat + 10:
            dominant = "HOME"
        elif away_threat > home_threat + 10:
            dominant = "AWAY"
        else:
            dominant = "BALANCED"

        return {
            "live_dynamics_version": self.VERSION,
            "dynamics_available": True,
            "snapshot_gap_seconds": round(elapsed_seconds, 1),
            "delta_shots": round(d_shots, 2),
            "delta_shots_on_target": round(d_sot, 2),
            "delta_dangerous_attacks": round(d_danger, 2),
            "delta_corners": round(d_corners, 2),
            "delta_xg": round(d_xg, 3),
            "recent_threat_score": round(recent_threat, 2),
            "recent_home_threat_score": round(home_threat, 2),
            "recent_away_threat_score": round(away_threat, 2),
            "recent_dominant_team": dominant,
            "dynamic_trend": trend,
            "dynamic_match_state": dynamic_state,
            "dynamic_instability_score": round(instability, 2),
            "score_changed_since_last_scan": score_changed,
            "post_goal_reanalysis": score_changed,
            "goals_since_last_scan": total_goal_delta,
        }

    def _snapshot(self, match: Dict[str, Any], at: float) -> Dict[str, Any]:
        hs = match.get("home_stats") if isinstance(match.get("home_stats"), dict) else {}
        aw = match.get("away_stats") if isinstance(match.get("away_stats"), dict) else {}
        return {
            "at": at,
            "minute": si(match.get("effective_minute") or match.get("api_minute") or match.get("minute"), 0),
            "home_score": si(match.get("home_score"), 0),
            "away_score": si(match.get("away_score"), 0),
            "shots": sf(match.get("shots") or match.get("total_shots")),
            "sot": sf(match.get("shots_on_target") or match.get("total_shots_on")),
            "dangerous": sf(match.get("dangerous_attacks") or match.get("total_dangerous_attacks")),
            "corners": sf(match.get("corners") or match.get("total_corners")),
            "xg": sf(match.get("xg") or match.get("xG") or match.get("total_xg")),
            "home": self._side_snapshot(hs),
            "away": self._side_snapshot(aw),
        }

    @staticmethod
    def _side_snapshot(stats: Dict[str, Any]) -> Dict[str, float]:
        return {
            "shots": sf(stats.get("shots")),
            "sot": sf(stats.get("shots_on_target")),
            "dangerous": sf(stats.get("dangerous_attacks")),
            "corners": sf(stats.get("corners")),
            "xg": sf(stats.get("xG") or stats.get("xg")),
        }

    @staticmethod
    def _side_delta_threat(current: Dict[str, Any], previous: Dict[str, Any], elapsed_minutes: float) -> float:
        def d(key: str) -> float:
            return max(0.0, sf(current.get(key)) - sf(previous.get(key)))

        raw = d("sot") * 25.0 + d("shots") * 6.0 + d("dangerous") * 1.2 + d("corners") * 8.0 + d("xg") * 40.0
        return clamp(raw * clamp(1.5 / elapsed_minutes, 0.45, 2.25))

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 900:
            return
        self._last_cleanup = now
        stale = []
        for fixture_id, history in self._history.items():
            if not history or now - sf(history[-1].get("at"), now) > self.expiry_seconds:
                stale.append(fixture_id)
        for fixture_id in stale:
            self._history.pop(fixture_id, None)

    @staticmethod
    def _empty_dynamics() -> Dict[str, Any]:
        return {
            "live_dynamics_version": LiveDynamicsMemory.VERSION,
            "dynamics_available": False,
            "snapshot_gap_seconds": 0.0,
            "delta_shots": 0.0,
            "delta_shots_on_target": 0.0,
            "delta_dangerous_attacks": 0.0,
            "delta_corners": 0.0,
            "delta_xg": 0.0,
            "recent_threat_score": 0.0,
            "recent_home_threat_score": 0.0,
            "recent_away_threat_score": 0.0,
            "recent_dominant_team": "UNKNOWN",
            "dynamic_trend": "WARMING_UP",
            "dynamic_match_state": "UNKNOWN",
            "dynamic_instability_score": 0.0,
            "score_changed_since_last_scan": False,
            "post_goal_reanalysis": False,
            "goals_since_last_scan": 0,
        }

    def _with_empty_dynamics(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {**item, **self._empty_dynamics()}
