from __future__ import annotations

from app.fetchers.live_match_fetcher import LiveMatchFetcher
from app.services.runtime_state import RuntimeState
from app.services.dashboard_service import DashboardService
from app.v17.dashboard.dashboard_adapter import V17DashboardAdapter


class AppContainer:
    """Single dependency container for the JHONNY ELITE runtime."""

    def __init__(self) -> None:
        self.runtime_state = RuntimeState()
        self.live_fetcher = LiveMatchFetcher()
        self.v17_dashboard_adapter = V17DashboardAdapter()
        self.dashboard_service = DashboardService(
            runtime_state=self.runtime_state,
            dashboard_adapter=self.v17_dashboard_adapter,
        )


app_container = AppContainer()
