from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DashboardService:
    """Read-only facade for the JHONNY ELITE panel.

    Heavy analysis is done by the worker. API routes only read the latest
    immutable-ish snapshot so the panel remains fast on desktop and mobile.
    """

    VERSION = "JHONNY_ELITE_20.0"

    def __init__(self, runtime_state, dashboard_adapter) -> None:
        self.runtime_state = runtime_state
        self.dashboard_adapter = dashboard_adapter

    def _dashboard(self) -> Dict[str, Any]:
        data = self.dashboard_adapter.last_dashboard()
        return data if isinstance(data, dict) else {}

    def get_health(self) -> Dict[str, Any]:
        state = self.runtime_state.get_health_status()
        snap = self.runtime_state.snapshot()
        return {
            "ok": state.get("status") != "ERROR",
            "status": state.get("status", "STARTING"),
            "active": state.get("status") == "OK",
            "version": self.VERSION,
            "error": state.get("error"),
            "updated_at": (snap.get("meta") or {}).get("updated_at") or now_iso(),
            "protocol": "LIVE -> CANDIDATE -> PREMATCH/ODDS -> MATH -> MASTER -> TRACK",
        }

    def get_live(self) -> Dict[str, Any]:
        items = self.runtime_state.get_live_matches()
        return {"ok": True, "count": len(items), "items": items, "matches": items, "updated_at": now_iso()}

    def get_signals(self) -> Dict[str, Any]:
        items = self.runtime_state.get_active_signals()
        return {"ok": True, "count": len(items), "items": items, "signals": items, "updated_at": now_iso()}

    def get_opportunities(self) -> Dict[str, Any]:
        data = self._dashboard()

        # Protocol promotion stages are mutually exclusive.  Keep ``observe``
        # as a backwards-compatible combined view, but do not duplicate the same
        # item again under OVER/UNDER when building the API payload.
        strong_candidates = data.get("strong_candidates", []) or []
        opportunities = data.get("opportunities", []) or []
        observations = data.get("observations", []) or []
        observe = data.get("observe", []) or (strong_candidates + opportunities + observations)
        no_bet = data.get("no_bet", []) or []

        active_analysis = strong_candidates + opportunities + observations
        if not active_analysis:
            active_analysis = list(observe)

        over = [x for x in active_analysis if str(x.get("suggested_market") or x.get("market")).upper() == "OVER"]
        under = [x for x in active_analysis if str(x.get("suggested_market") or x.get("market")).upper() == "UNDER"]
        sections = {
            "strong_candidates": strong_candidates,
            "opportunities": opportunities,
            "observations": observations,
            "over_candidates": over,
            "under_candidates": under,
            "observe": active_analysis,
            "rejected": no_bet,
        }
        return {
            "ok": True,
            "summary": data.get("summary", {}),
            "sections": sections,
            "items": active_analysis + no_bet,
            "updated_at": now_iso(),
        }

    def get_blocked(self) -> Dict[str, Any]:
        items = self.runtime_state.get_blocked()
        return {"ok": True, "count": len(items), "items": items, "blocked": items, "updated_at": now_iso()}

    def get_history(self, limit: int = 100) -> Dict[str, Any]:
        data = self._dashboard()
        history = (data.get("history", []) or [])[:limit]
        pending = data.get("pending_signals", []) or []
        closed = data.get("closed_history", []) or []
        return {
            "ok": True,
            "count": len(history),
            "total_available": len(data.get("history", []) or []),
            "limit": limit,
            "items": history,
            "history": history,
            "tracking_items": history,
            "tracking_history": history,
            "tracking_count": len(history),
            "tracking_total_available": len(history),
            "tracking_summary": data.get("summary", {}),
            "performance_analysis": data.get("performance_analysis", {}),
            "pending_signals": pending,
            "closed_history": closed,
            "today_results": data.get("today_results", []),
            "history_groups": data.get("history_groups", {}),
            "daily_summary": data.get("daily_summary", {}),
            "learning": data.get("learning", {}),
            "updated_at": now_iso(),
        }

    def get_match_detail(self, fixture_id: Any, signal_key: Any = None) -> Dict[str, Any]:
        return self.dashboard_adapter.get_match_detail(fixture_id=fixture_id, signal_key=signal_key)

    def get_stats(self) -> Dict[str, Any]:
        data = self._dashboard()
        stats = {**(data.get("stats", {}) or {}), **(self.runtime_state.get_stats() or {})}
        stats["version"] = self.VERSION
        return {"ok": True, "stats": stats, "updated_at": now_iso()}
